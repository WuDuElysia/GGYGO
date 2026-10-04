"""Run with UnrealEditor-Cmd -run=pythonscript -script=<this file> -AllowCommandletRendering -dpcvars=Editor.AsyncTextureCompilation=0.

空关卡里用 SceneCapture2D 拍 Pyrios 骨骼网格（资产默认材质，组件不运行）的正面全身、胸口近景、背面，
手动曝光 0。输出到 AAADocs/References/Captures/PyriosToon/<日期>_toon_<PYRIOS_CAP_TAG>_<视角>.png，
结论写进同目录 INDEX.md。贴图未编译完会拍成灰色占位，所以必须关闭异步贴图编译并强制 mip 常驻。
"""
import math
import os
import time
import unreal
EAL = unreal.EditorAssetLibrary
for p in EAL.list_assets("/Game/Characters/Player/Pyrios/Materials/Texture", recursive=False):
    t = EAL.load_asset(p)
    if isinstance(t, unreal.Texture2D):
        t.set_force_mip_levels_to_be_resident(60.0)
world = unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
mesh = EAL.load_asset("/Game/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model")
actor = sub.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
actor.get_editor_property("skeletal_mesh_component").set_skeletal_mesh_asset(mesh)
rt = unreal.RenderingLibrary.create_render_target2d(world, 768, 1024, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
out = "F:/ue_project/GGYGO/AAADocs/References/Captures/PyriosToon"
os.makedirs(out, exist_ok=True)
tag = os.environ.get("PYRIOS_CAP_TAG", "cap")
for name, yaw, z, dist, fov in (("front", 0, 95, 330, 40.0), ("chest", 0, 150, 160, 40.0), ("back", 180, 120, 260, 40.0)):
    center = unreal.Vector(0, 0, z)
    rad = math.radians(yaw)
    loc = unreal.Vector(dist * math.sin(rad), dist * math.cos(rad), z + 10)
    cap = sub.spawn_actor_from_class(unreal.SceneCapture2D, loc, unreal.MathLibrary.find_look_at_rotation(loc, center))
    cc = cap.get_editor_property("capture_component2d")
    cc.set_editor_property("texture_target", rt)
    cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    cc.set_editor_property("fov_angle", fov)
    pp = cc.get_editor_property("post_process_settings")
    for k, v in (("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL), ("auto_exposure_bias", 0.0),
                 ("auto_exposure_apply_physical_camera_exposure", False)):
        pp.set_editor_property("override_" + k, True)
        pp.set_editor_property(k, v)
    cc.set_editor_property("post_process_settings", pp)
    for _ in range(3):
        cc.capture_scene()
    unreal.RenderingLibrary.export_render_target(world, rt, out, "%s_toon_%s_%s.png" % (time.strftime("%Y%m%d"), tag, name))
    unreal.log("CAP_DONE " + name)
