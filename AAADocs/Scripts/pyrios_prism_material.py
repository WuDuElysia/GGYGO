"""为佩洛伊斯三段普攻制作棱彩刀面、延迟外弦和收刀镶金材质。"""
from pathlib import Path

import unreal as ue

from zzz_fx_material_ue import configure_native_custom


# 同一套 UV 跟随实际挥刀曲面。分色由笔触控制，延迟外弦由粒子寿命控制。
SHADER = """
float u = saturate(UV.x);
float v = saturate(UV.y);
float fade = saturate(Life);
float envelope = fade;
float sweep = smoothstep(0.5, 1.0, Tier);
float crown = smoothstep(2.0, 3.0, Tier);
float3 sapphire = float3(0.028, 0.14, 1.15);
float3 amethyst = float3(0.57, 0.027, 1.03);
float3 turquoise = float3(0.04, 1.15, 1.85);
float3 amber = float3(3.10, 0.69, 0.095);
float3 rim = lerp(turquoise, float3(0.62, 0.95, 2.4), u);
float3 pane = lerp(sapphire, amethyst, smoothstep(0.2, 0.85, u + 0.12 * (1.0 - fade)));
float3 rgb = Ink.a * float3(0.019, 0.008, 0.089);
float wave = saturate(1.0 - abs(u - (0.12 + 0.8 * fade)) * 4.0);
float foil = Ink.b * lerp(0.62, 1.40, wave);
rgb += Ink.g * pane * (0.74 + 0.3 * sweep);
rgb += Ink.r * rim * (1.10 + 0.46 * wave);
rgb += foil * lerp(float3(0.31, 0.45, 1.42), amber, 0.12 + 0.36*sweep + 0.52*crown);
float opacity = max(Ink.a * lerp(0.70, 0.85, sweep), max(Ink.r, Ink.b));
if (Tier < 1.5)
{
    envelope = smoothstep(0.02 + 0.15*sweep, 0.68, fade);
}
if (Tier > 4.5)
{
    // 折光仅在一个已采样的刃面位置短暂出现，斜向亮线和中心棱面共用寿命。
    float2 p = (UV - 0.5) * 2.0;
    float2 q = abs(float2(0.90*p.x+0.435*p.y, -0.435*p.x+0.90*p.y));
    float diamond = saturate(1.0 - q.x*5.4 - q.y*8.5);
    float shaft = saturate(1.0 - q.x) * saturate(1.0 - q.y*(16.0 + 76.0*q.x));
    float shortRay = saturate(1.0 - q.y*1.42) * saturate(1.0 - q.x*(20.0 + 72.0*q.y));
    float halo = pow(saturate(1.0 - length(p)*1.85), 3.0);
    rgb = float3(0.30,0.045,0.85)*halo + amber*shaft*shaft + turquoise*shortRay*shortRay + float3(4.0,3.2,2.5)*diamond;
    opacity = saturate(halo*0.3 + shaft*shaft + shortRay*shortRay + diamond);
    envelope = smoothstep(0.40,0.74,fade) * (1.0 - smoothstep(0.81,0.99,fade));
}
else if (Tier > 3.5)
{
    // 外弦在主刀之后显色，薄金线围着紫色的余辉逐渐散去。
    float edge = 1.0 - smoothstep(0.05, 0.21, abs(v - 0.62));
    float glass = 1.0 - smoothstep(0.12, 0.47, abs(v - 0.53));
    float taper = smoothstep(0.0, 0.17, u) * (1.0 - smoothstep(0.87, 1.0, u));
    rgb = taper * (glass * amethyst * 0.67 + edge * lerp(amber, turquoise, u * u));
    opacity = taper * max(0.62 * glass, edge);
    envelope = smoothstep(0.035, 0.38, fade) * (1.0 - smoothstep(0.65, 0.94, fade));
}
else if (Tier > 2.5)
{
    // 收刀有一束沿刃面的金白掠光，只点亮镶纹和外缘。
    float glint = pow(saturate(1.0 - abs(u - 0.64 + 0.16 * (v - 0.5)) * 5.4), 2);
    rgb += (Ink.r + Ink.b) * glint * float3(2.6, 1.46, 0.70);
}
if (Tier < 3.5)
{
    float tip = saturate(min(u,1.0-u) * 7.0);
    float halfWidth = lerp(0.018,0.87,tip);
    float taper = 1.0-smoothstep(halfWidth,halfWidth+0.04,abs(v-0.79));
    envelope *= taper * smoothstep(0.0,0.24,tip);
}
Coverage = saturate(opacity * envelope);
return rgb * envelope;
"""


def build_prism_materials(directory):
    editor = ue.EditorAssetLibrary
    edit = ue.MaterialEditingLibrary
    tools = ue.AssetToolsHelpers.get_asset_tools()
    name = 'T_Pyrios_PrismInlay'
    texture_path = directory + '/' + name
    if not editor.does_asset_exist(texture_path):
        project = Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir()))
        task = ue.AssetImportTask()
        task.set_editor_properties(dict(filename=str(project/'AAADocs/Assets/Pyrios/FX'/(name+'.png')),
                                        destination_path=directory, destination_name=name, automated=True, save=False))
        tools.import_asset_tasks([task])
    texture = ue.load_asset(texture_path)
    if not isinstance(texture, ue.Texture2D):
        raise ValueError('缺普攻棱彩镶纹贴图')
    material_name = 'M_Pyrios_PrismInlay'
    path = directory + '/' + material_name
    master = ue.load_asset(path) if editor.does_asset_exist(path) else None
    if not master or editor.get_metadata_tag(master, 'Pyrios.PrismArt') != 'facet-2':
        texture.set_editor_properties(dict(srgb=False, compression_settings=ue.TextureCompressionSettings.TC_MASKS,
            address_x=ue.TextureAddress.TA_CLAMP, address_y=ue.TextureAddress.TA_CLAMP))
        if not editor.save_loaded_asset(texture, False):
            raise RuntimeError('棱纹贴图保存失败')
        if master:
            edit.delete_all_material_expressions(master)
        else:
            master = tools.create_asset(material_name, directory, ue.Material, ue.MaterialFactoryNew())
        master.set_editor_properties(dict(blend_mode=ue.BlendMode.BLEND_ALPHA_COMPOSITE,
            shading_model=ue.MaterialShadingModel.MSM_UNLIT, two_sided=True, used_with_niagara_sprites=True,
            used_with_niagara_mesh_particles=True, used_with_niagara_ribbons=True))
        uv = edit.create_material_expression(master, ue.MaterialExpressionTextureCoordinate, -650, -130)
        sampler = edit.create_material_expression(master, ue.MaterialExpressionTextureSample, -650, 0)
        sampler.set_editor_properties(dict(texture=texture, sampler_type=ue.MaterialSamplerType.SAMPLERTYPE_MASKS))
        life = edit.create_material_expression(master, ue.MaterialExpressionParticleColor, -650, 180)
        tier = edit.create_material_expression(master, ue.MaterialExpressionScalarParameter, -650, 340)
        tier.set_editor_property('parameter_name', 'PrismTier')
        shader = edit.create_material_expression(master, ue.MaterialExpressionCustom, -200, 40)
        configure_native_custom(ue, shader, ['UV','Ink','Life','Tier'], SHADER, 'CMOT_Float3', '刃面镶纹和分段掠光',
                                native_sync=lambda _,call:call(), additional_outputs=[('Coverage','CMOT_Float1')])
        for source, pin, target in [(uv,'','UV'),(sampler,'RGBA','Ink'),(life,'A','Life'),(tier,'','Tier')]:
            if not edit.connect_material_expressions(source, pin, shader, target):
                raise RuntimeError('棱彩接线失败 '+target)
        if not edit.connect_material_property(shader,'',ue.MaterialProperty.MP_EMISSIVE_COLOR):
            raise RuntimeError('棱彩自发光未连接')
        if not edit.connect_material_property(shader,'Coverage',ue.MaterialProperty.MP_OPACITY):
            raise RuntimeError('棱彩透明度未连接')
        if edit.recompile_material(master):
            raise RuntimeError('棱彩母材质编译失败')
        editor.set_metadata_tag(master, 'Pyrios.PrismArt', 'facet-2')
        if not editor.save_loaded_asset(master, False):
            raise RuntimeError('棱彩母材质保存失败')
    variants = {}
    for tier, label in enumerate(('Draw','Crescent','Cross','Crown','Echo','Flare')):
        name = 'MI_Pyrios_Prism_' + label
        path = directory + '/' + name
        instance = ue.load_asset(path) if editor.does_asset_exist(path) else None
        if not instance:
            instance = tools.create_asset(name, directory, ue.MaterialInstanceConstant, ue.MaterialInstanceConstantFactoryNew())
        if instance.get_editor_property('parent') != master or edit.get_material_instance_scalar_parameter_value(instance, 'PrismTier') != tier:
            edit.set_material_instance_parent(instance, master)
            edit.set_material_instance_scalar_parameter_value(instance, 'PrismTier', tier)
            edit.update_material_instance(instance)
            if not editor.save_loaded_asset(instance, False):
                raise RuntimeError('分段材质保存失败 '+name)
        if instance.get_editor_property('parent') != master or edit.get_material_instance_scalar_parameter_value(instance,'PrismTier') != tier:
            raise RuntimeError('分段材质参数未生效 '+name)
        variants[label] = instance
    return variants
