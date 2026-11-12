"""@file build_projected_fx_materials.py
@brief 在原FX create-only Session制作Native投影材质，不连接/启动UE或保存包。

调用方提供同一Editor原生unreal宿主；本文件的编译/读回只在整批制作窗执行。
"""
from build_nap_avatar_simple_materials import NapAvatarSimpleBuilder
from projected_fx_material_plan import validate_plan
from zzz_fx_material_ue import ref


class ProjectedFXMaterialBuilder(NapAvatarSimpleBuilder):
    """复用既有AssetSession与材质图作者基础操作，FX独占批次/保存和运行宿主。"""
    validate_plan = staticmethod(validate_plan)

    def __init__(self, session, *, unreal=None, uv_author=None, verified_readonly_dependencies=None):
        super().__init__(session, unreal=unreal, verified_readonly_dependencies=verified_readonly_dependencies)
        # UV模块由原FX helper唯一实现；只在制作期间调用，不持有运行时状态。
        self.uv_author = uv_author

    def _custom(self, mat, inputs, code, output_type, sources, y, *, additional_outputs=None):
        node = self.add(mat, 'MaterialExpressionCustom', 0, y)
        self.configure_custom(node, inputs, code, output_type, '源Decal表面/遮罩与显式Native投影',
                              additional_outputs=additional_outputs)
        for name in inputs:
            self.connect(*sources[name], node, name)
        return node

    def build(self, plan):
        """准入完整计划后创建；只返回绑定，包仍由原FX批次唯一保存者处理。"""
        self.validate_plan(plan)
        self._require_native()
        self._require_build_targets(plan)
        if any(spec.get('mesh_uv', {}).get('mode') == 'FXAnimatedMeshUV0' for spec in plan['materials']) and not callable(self.uv_author):
            raise ValueError('本批Prop需要原FX动画UV作者，尚未开始创建材质')
        self._verify_textures(plan)
        for spec in plan['materials']:
            self._build_master(spec, plan)
            self._build_instance(spec)
        return plan['bindings']

    def verify(self, plan):
        result = super().verify(plan)
        result['native_renderer_contract'] = plan['native_renderer_contract']
        result['required_source_inputs_verified'] = False
        return result

    def _relative(self, material, position, origin, y):
        # 图上的WS减法保UE LWC高低位；不能先把绝对位置转成Custom float再相减。
        subtract = self.add(material, 'MaterialExpressionSubtract', -1700, y)
        self.connect(position, '', subtract, 'A')
        self.connect(origin, '', subtract, 'B')
        return subtract, ''

    def _verify_master(self, spec):
        material = self.native.load_asset(spec['master'])
        if not isinstance(material, self.native.Material) or material.get_path_name() != ref(spec['master'])['refPath']:
            raise RuntimeError('投影/Prop Master类型或路径不符')
        self._check_properties(material, spec['properties'])
        library = self.native.MaterialEditingLibrary
        statistics = library.get_statistics(material)  # 原生函数完成现有编译任务，不创建另一编译路径。
        state = self.native.GGYGOProjectedDecalRendererProperties.read_material_compilation_for_authoring(material)
        # UE Python 将 C++ bool 成功返回值移除；失败为 None，成功仅返回三个 out 参数。
        if not isinstance(state, tuple) or len(state) != 3:
            raise RuntimeError('真实MaterialResource/ShaderMap未准入或返回ABI未核实：' + repr(state))
        shader_map_complete, compile_errors, error = state
        if shader_map_complete is not True or len(compile_errors) != 0 or error:
            raise RuntimeError('真实MaterialResource/ShaderMap未准入或返回ABI未核实：' + repr(state))
        # Surface代表性指令统计不枚举DeferredDecal shader，不能用0制造假失败或成功。
        scalar_names = {str(name) for name in library.get_scalar_parameter_names(material)}
        vector_names = {str(name) for name in library.get_vector_parameter_names(material)}
        texture_names = {str(name) for name in library.get_texture_parameter_names(material)}
        for name, parameter in spec['params'].items():
            if name not in (scalar_names if parameter['dim'] == 1 else vector_names):
                raise RuntimeError('源材质没有注册必需参数：' + name)
        if set(spec['textures']) - texture_names:
            raise RuntimeError('源材质没有注册必需纹理参数')
        return dict(pixel_shader_instructions=statistics.num_pixel_shader_instructions,
                    vertex_shader_instructions=statistics.num_vertex_shader_instructions,
                    native_shader_map_complete=True, native_shader_map_valid_for_rendering=True,
                    native_draw_verified=False, visual_verified=False)

    def _verify_additional_outputs(self, node, outputs):
        actual = node.get_editor_property('additional_outputs')
        if ([str(entry.get_editor_property('output_name')) for entry in actual] != list(outputs)
                or any(entry.get_editor_property('output_type') != self._enum('CustomMaterialOutputType', 'CMOT_Float' + str(dim))
                       for entry, dim in zip(actual, outputs.values()))):
            raise RuntimeError('源材质Custom附加输出读回不符')

    def _build_master(self, spec, plan=None):
        if spec['role'] in ('prop_surface', 'prop_forward_color'):
            return self._build_prop_master(spec, plan)
        material = self._create(spec['master'], 'Material', 'MaterialFactoryNew')
        self.set(material, spec['properties'])
        sources = {}
        for index, (name, parameter) in enumerate(spec['params'].items()):
            scalar = parameter['dim'] == 1
            default = parameter['value'] if scalar else dict(zip('rgba', parameter['value']))
            node = self.add(material, 'MaterialExpressionScalarParameter' if scalar else 'MaterialExpressionVectorParameter',
                -1400, index * 75, {'ParameterName': name, 'DefaultValue': default})
            sources[name] = node, '' if scalar else 'RGBA'
        for index, (name, path) in enumerate(spec['textures'].items()):
            node = self.add(material, 'MaterialExpressionTextureObjectParameter', -1100, index * 110,
                {'ParameterName': name, 'Texture': path, 'SamplerType': self.sampler_type(path)})
            sources[name] = node, ''
        origin = self.add(material, 'MaterialExpressionActorPositionWS', -2200, -400)
        receiver = self.add(material, 'MaterialExpressionWorldPosition', -2200, -250)
        camera = self.add(material, 'MaterialExpressionCameraPositionWS', -2200, -100)
        sources['ReceiverRelativeWS'] = self._relative(material, receiver, origin, -250)
        sources['CameraRelativeWS'] = self._relative(material, camera, origin, -100)
        shader = spec['shader']
        inputs = list(shader['builtins']) + list(shader['parameters']) + list(shader['material_params']) + list(shader['textures'])
        if len(inputs) != len(set(inputs)) or set(inputs) - set(sources):
            raise ValueError('投影Custom输入重复或缺真实图提供者')
        outputs = [(name, 'CMOT_Float' + str(dimension)) for name, dimension in shader['outputs'].items()]
        main = self._custom(material, inputs, shader['code'], 'CMOT_Float3', sources, 0, additional_outputs=outputs)
        self._verify_additional_outputs(main, shader['outputs'])
        self._output(main, 'OpacityOut', 'MP_Opacity')
        if shader['surface'] == 'native_pbr':
            for name, prop in (('BaseColorOut', 'MP_BaseColor'), ('MetallicOut', 'MP_Metallic'),
                               ('RoughnessOut', 'MP_Roughness'), ('NormalOut', 'MP_Normal')):
                self._output(main, name, prop)
        scale = self.add(material, 'MaterialExpressionMultiply', 350, 0)
        self.connect(main, '', scale, 'A')
        self.connect(*sources['UE_EmissiveOutputScale'], scale, 'B')
        inverse = self.add(material, 'MaterialExpressionEyeAdaptationInverse', 650, 0)
        self.connect(scale, '', inverse, 'LightValueInput')
        self.connect(*sources['UE_ExposureCompensationWeight'], inverse, 'AlphaInput')
        self._output(inverse, '', 'MP_EmissiveColor')
        errors = self.native.MaterialEditingLibrary.recompile_material(material)
        if errors is None or errors:
            raise RuntimeError('投影材质编译失败或没有诊断：' + spec['master'] + ' ' + repr(errors))
        self._verify_master(spec)

    def _constant_vector(self, material, value, y):
        return self.add(material, 'MaterialExpressionConstant3Vector', -2200, y,
                        {'Constant': self.native.LinearColor(*value, 0.0)})

    def _transform_vector(self, material, value, source, target, y):
        vector = self._constant_vector(material, value, y)
        node = self.add(material, 'MaterialExpressionTransform', -1900, y,
                        {'TransformSourceType': source, 'TransformType': target})
        self.connect(vector, '', node, '')
        return node, ''

    def _build_prop_master(self, spec, plan):
        material = self._create(spec['master'], 'Material', 'MaterialFactoryNew')
        self.set(material, spec['properties'])
        sources = {}
        for index, (name, parameter) in enumerate(spec['params'].items()):
            scalar = parameter['dim'] == 1
            node = self.add(material, 'MaterialExpressionScalarParameter' if scalar else 'MaterialExpressionVectorParameter',
                -1400, index * 80, {'ParameterName': name, 'DefaultValue': parameter['value'] if scalar
                                 else dict(zip('rgba', parameter['value']))})
            sources[name] = node, '' if scalar else 'RGBA'
        for index, (name, path) in enumerate(spec['textures'].items()):
            sources[name] = self.add(material, 'MaterialExpressionTextureObjectParameter', -1100, index * 110,
                {'ParameterName': name, 'Texture': path, 'SamplerType': self.sampler_type(path)}), ''
        world = self.add(material, 'MaterialExpressionWorldPosition', -2200, -200)
        camera = self.add(material, 'MaterialExpressionCameraPositionWS', -2200, -100)
        sources['CameraVectorWS'] = self._relative(material, camera, world, -100)
        sources['FaceSign'] = self.add(material, 'MaterialExpressionTwoSidedSign', -1900, 100), ''
        screen = self.add(material, 'MaterialExpressionScreenPosition', -1900, 200)
        sources['PixelPosition'] = screen, 'PixelPosition'
        mesh_color = self.add(material, 'MaterialExpressionVertexColor', -2200, 300)
        rgba = self.add(material, 'MaterialExpressionAppendVector', -1900, 300)
        self.connect(mesh_color, '', rgba, 'A')
        self.connect(mesh_color, 'A', rgba, 'B')
        particle_color = self.add(material, 'MaterialExpressionParticleColor', -2200, 400)
        color = self.add(material, 'MaterialExpressionMultiply', -1600, 350)
        self.connect(rgba, '', color, 'A')
        self.connect(particle_color, 'RGBA', color, 'B')
        sources['VCol'] = color, ''
        uv = spec['mesh_uv']
        if uv['mode'] == 'FXAnimatedMeshUV0':
            if not callable(self.uv_author):
                raise ValueError('Prop启用源动画UV，需要原FX helper的uv_author')
            result = self.uv_author(material, plan, self)
            if (not isinstance(result, tuple) or len(result) != 2
                    or not isinstance(result[0], self.native.MaterialExpression) or result[0].get_outer() != material):
                raise ValueError('Prop UV作者没有返回同一新Master的实际表达式/输出')
            sources['UV0'] = result
        else:
            # 原helper已证明UV模块关闭或mask未作用UV0。
            sources['UV0'] = self.add(material, 'MaterialExpressionTextureCoordinate', -1900, 500,
                                      {'CoordinateIndex': 0}), ''
        for name, axis in (('UEFX_TangentWS', (1.0, 0.0, 0.0)),
                           ('UEFX_BitangentWS', (0.0, 1.0, 0.0)), ('UEFX_NormalWS', (0.0, 0.0, 1.0))):
            # 用真实Transform图激活Native VF tangent需求；不在Custom偷读未声明的TBN。
            sources[name] = self._transform_vector(material, axis, 'TRANSFORMSOURCE_Tangent', 'TRANSFORM_World', 650 + len(sources) * 60)
        shader = spec['shader']
        if 'UEFX_SystemAge' in shader['builtins']:
            age = spec['age_transport']
            dynamic = self.add(material, 'MaterialExpressionDynamicParameter', -2200, 1000,
                               {'ParameterIndex': age['slot'], 'DefaultValue': dict(r=0.0, g=0.0, b=0.0, a=0.0)})
            sources['UEFX_SystemAge'] = dynamic, ('Param1', 'Param2', 'Param3', 'Param4')[age['component']]
        if 'UEFX_MeshLocalPosition' in shader['builtins']:
            position = self.add(material, 'MaterialExpressionTransformPosition', -1900, 1150,
                {'TransformSourceType': 'TRANSFORMPOSSOURCE_World', 'TransformType': 'TRANSFORMPOSSOURCE_Instance'})
            self.connect(world, '', position, '')
            sources['InstancePoint'] = position, ''
            local = self._custom(material, ['InstancePoint'],
                'return float3(-InstancePoint.x,InstancePoint.z,InstancePoint.y)*0.01;', 'CMOT_Float3', sources, 1150)
            sources['UEFX_MeshLocalPosition'] = local, ''
            # C=(-X,Z,Y)，WorldToInstance列按源Unity世界基向量逐一变换；保实际非均匀缩放。
            for index, axis in enumerate(((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0))):
                sources['InstanceVector'] = self._transform_vector(material, axis,
                    'TRANSFORMSOURCE_World', 'TRANSFORM_Instance', 1300 + index * 120)
                column = self._custom(material, ['InstanceVector'],
                    'return float3(-InstanceVector.x,InstanceVector.z,InstanceVector.y);', 'CMOT_Float3', sources, 1300 + index * 120)
                sources['UEFX_WorldToObjectColumn' + str(index)] = column, ''
        inputs = list(shader['builtins']) + list(shader['parameters']) + list(shader['material_params']) + list(shader['textures'])
        if len(inputs) != len(set(inputs)) or set(inputs) - set(sources):
            raise ValueError('Prop Custom输入重复或缺真实图提供者')
        outputs = [(name, 'CMOT_Float' + str(dimension)) for name, dimension in shader['outputs'].items()]
        main = self._custom(material, inputs, shader['code'], 'CMOT_Float3', sources, 0, additional_outputs=outputs)
        self._verify_additional_outputs(main, shader['outputs'])
        if spec['role'] == 'prop_surface':
            self._output(main, '', 'MP_BaseColor')
            for name, prop in (('MetallicOut', 'MP_Metallic'), ('RoughnessOut', 'MP_Roughness'),
                               ('NormalOut', 'MP_Normal'), ('CoverageOut', 'MP_OpacityMask')):
                self._output(main, name, prop)
        else:
            sources['SourceColor'] = main, ''
            emission = self._custom(material, ['SourceColor', 'UE_EmissiveOutputScale'],
                'return SourceColor*UE_EmissiveOutputScale;', 'CMOT_Float3', sources, 700)
            inverse = self.add(material, 'MaterialExpressionEyeAdaptationInverse', 700, 700)
            self.connect(emission, '', inverse, 'LightValueInput')
            self.connect(*sources['UE_ExposureCompensationWeight'], inverse, 'AlphaInput')
            self._output(inverse, '', 'MP_EmissiveColor')
            opacity = self.add(material, 'MaterialExpressionConstant', 500, 850, {'R': 1.0})
            self._output(opacity, '', 'MP_Opacity')
        errors = self.native.MaterialEditingLibrary.recompile_material(material)
        if errors is None or errors:
            raise RuntimeError('Prop材质编译失败或没有诊断：' + spec['master'] + ' ' + repr(errors))
        self._verify_master(spec)
