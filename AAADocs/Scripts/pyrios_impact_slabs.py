"""佩洛伊斯砸地中心翘起的岩板。全部断板共用一个 Niagara 网格和落点。"""
from math import cos, radians, sin

import unreal as ue


def broken_slabs(directory):
    editor = ue.EditorAssetLibrary
    mesh_path = directory + '/SM_Pyrios_UpliftedSlabs'
    if editor.does_asset_exist(mesh_path):
        return ue.load_asset(mesh_path)

    mesh = ue.DynamicMesh()
    edits = ue.GeometryScript_MeshEdits

    def face(points):
        # 各个断面保留自己的顶点，重新计算法向时保留石板的硬棱。
        ids = [edits.add_vertex_to_mesh(mesh, ue.Vector(*p), True)[1] for p in points]
        for i in range(1, len(ids)-1):
            _, triangle = edits.add_triangle_to_mesh(mesh, ue.IntVector(ids[0], ids[i], ids[i+1]), 0, True)
            if triangle < 0:
                raise RuntimeError('无法创建砸地断面的三角形')

    # 角度、内缘半径、径向长度、板宽、翘起高度，单位为厘米。几处断口留空。
    plates = [(8,45,62,50,32),(38,91,43,32,14),(78,46,53,42,28),(121,84,57,51,34),
              (150,32,35,27,16),(185,67,74,54,42),(228,45,48,32,19),(254,100,51,35,12),
              (292,53,67,46,38),(325,102,50,33,18)]
    for angle, start, length, width, lift in plates:
        c, s = cos(radians(angle)), sin(radians(angle))
        def point(u, v, height):
            along, across = start+u*length, v*width
            return (-height, c*along-s*across, s*along+c*across)
        outline = [(.02,-.28,.84),(.17,-.56,.92),(.71,-.39,.29),(1,.06,.06),
                   (.78,.47,.23),(.26,.39,.68),(0,.08,1)]
        top = [point(u,v,lift*h) for u,v,h in outline]
        bottom = [point(u,v,-3) for u,v,_ in outline]
        crest = point(.35,-.02,lift*.81)
        for i,p in enumerate(top):
            j=(i+1)%len(top)
            face([crest,p,top[j]])
            face([p,bottom[i],bottom[j],top[j]])
    options = ue.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=True,
        enable_recompute_tangents=False, enable_nanite=False, enable_collision=False)
    asset, outcome = ue.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(mesh, mesh_path, options)
    if not asset or outcome != ue.GeometryScriptOutcomePins.SUCCESS or not editor.save_loaded_asset(asset, False):
        raise RuntimeError('无法生成砸地断板网格')
    return asset


def cut_rock_material(directory):
    editor = ue.EditorAssetLibrary
    name = 'M_Pyrios_FracturedStone'
    if editor.does_asset_exist(directory+'/'+name):
        return ue.load_asset(directory+'/'+name)
    mat = ue.AssetToolsHelpers.get_asset_tools().create_asset(name, directory, ue.Material, ue.MaterialFactoryNew())
    mat.set_editor_properties(dict(two_sided=True, used_with_niagara_mesh_particles=True))
    edit = ue.MaterialEditingLibrary
    color = edit.create_material_expression(mat, ue.MaterialExpressionConstant3Vector, -230, 0)
    color.set_editor_property('constant', ue.LinearColor(.19,.18,.205,1))
    rough = edit.create_material_expression(mat, ue.MaterialExpressionConstant, -230, 120)
    rough.set_editor_property('r', .93)
    if (not edit.connect_material_property(color,'',ue.MaterialProperty.MP_BASE_COLOR)
            or not edit.connect_material_property(rough,'',ue.MaterialProperty.MP_ROUGHNESS)
            or edit.recompile_material(mat) or not editor.save_loaded_asset(mat,False)):
        raise RuntimeError('砸地断板材质创建失败')
    return mat
