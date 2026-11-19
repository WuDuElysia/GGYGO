"""在 UE 5.9 中制作月坑环站。新建目录 /Game/Map/LunarStation，独立保存各资产。"""
import math
import os
import unreal as ue

ROOT = "/Game/Map/LunarStation"
MAP = ROOT + "/L_LunarStation"
DEST = "/Game/Map/BH3/L_KevinBoss_P3"
PLATE = ROOT + "/BP_InsidePlate"
EXIT = ROOT + "/BP_ArenaPassage"
BP = ue.BlueprintEditorLibrary
ASSETS = ue.EditorAssetLibrary


def check(value, reason):
    if not value:
        raise RuntimeError(reason)
    return value


def make_trigger(path, opens_gate):
    existing = ue.load_asset(path) if ASSETS.does_asset_exist(path) else None
    if existing:
        return existing.generated_class()
    bp = check(BP.create_blueprint_asset_with_parent(path, ue.TriggerBox.static_class()), path)
    if opens_gate:
        check(BP.add_member_variable(bp, "GateLeaf", BP.get_object_reference_type(ue.StaticMeshActor.static_class())), "GateLeaf")
        BP.set_blueprint_variable_instance_editable(bp, "GateLeaf", True)
        check(BP.compile_blueprint(bp), path)
    graph = ue.BlueprintGraphEditor.get_graph_editor(BP.find_event_graph(bp))
    event = graph.find_event_node("ReceiveActorBeginOverlap")
    if not event:
        event = BP.add_event_override(bp, "ReceiveActorBeginOverlap", ue.IntPoint(0, 0))
    check(event, "ReceiveActorBeginOverlap")
    event.set_node_pos(ue.IntPoint(0, 0))

    def node(function, x, y):
        result = check(graph.add_call_function_node("/Script/Engine." + function), function)
        result.set_node_pos(ue.IntPoint(x, y))
        return result

    def join(a, source, b, dest):
        output = check(a.find_output_pin(source), source)
        target = check(b.find_input_pin(dest), dest)
        check(output.try_create_connection(target), source + " → " + dest)

    def literal(n, pin, value):
        check(n.find_input_pin(pin).set_pin_value(value), pin + " = " + value)

    pawn = node("GameplayStatics.GetPlayerPawn", 0, 250)
    equal = node("KismetMathLibrary.EqualEqual_ObjectObject", 330, 170)
    join(event, "OtherActor", equal, "A")
    join(pawn, "ReturnValue", equal, "B")
    branch = graph.add_branch_node()
    branch.set_node_pos(ue.IntPoint(650, 0))
    join(event, "then", branch, "execute")
    join(equal, "ReturnValue", branch, "Condition")
    once = node("Actor.SetActorEnableCollision", 910, 0)
    literal(once, "bNewActorEnableCollision", "false")
    join(branch, "then", once, "execute")
    if opens_gate:
        gate = check(graph.add_get_member_variable_node("GateLeaf"), "GateLeaf getter")
        gate.set_node_pos(ue.IntPoint(925, 250))
        move = node("Actor.K2_AddActorWorldOffset", 1280, 0)
        literal(move, "DeltaLocation", "(X=0,Y=480,Z=0)")
        join(gate, "GateLeaf", move, "self")
        join(once, "then", move, "execute")
    else:
        travel = node("GameplayStatics.OpenLevelBySoftObjectPtr", 1280, 0)
        literal(travel, "Level", DEST + ".L_KevinBoss_P3")
        join(once, "then", travel, "execute")
    check(BP.compile_blueprint(bp), "蓝图编译失败 " + path)
    check(ASSETS.save_loaded_asset(bp, False), "蓝图保存失败 " + path)
    return bp.generated_class()


def material(name, color, unlit=False):
    path = ROOT + "/Materials/M_" + name
    if ASSETS.does_asset_exist(path):
        return check(ue.load_asset(path), path)
    directory, name = path.rsplit("/", 1)
    mat = ue.AssetToolsHelpers.get_asset_tools().create_asset(name, directory, ue.Material, ue.MaterialFactoryNew())
    edit = ue.MaterialEditingLibrary
    rgb = edit.create_material_expression(mat, ue.MaterialExpressionConstant3Vector, -250, 0)
    rgb.set_editor_property("constant", ue.LinearColor(*color, 1))
    prop = ue.MaterialProperty.MP_BASE_COLOR
    if unlit:
        mat.set_editor_property("two_sided", True)
        mat.set_editor_property("shading_model", ue.MaterialShadingModel.MSM_UNLIT)
        prop = ue.MaterialProperty.MP_EMISSIVE_COLOR
    check(edit.connect_material_property(rgb, "", prop), path)
    edit.recompile_material(mat)
    check(ASSETS.save_loaded_asset(mat, False), path)
    return mat


class Station:
    def __init__(self, world):
        self.world = world
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.cube = check(ue.load_asset("/Engine/BasicShapes/Cube"), "Cube")
        self.palette = {name: material(name, rgb, name == "Sky") for name, rgb in {
            "Deck": (.39, .43, .44), "Frame": (.12, .24, .27), "Chalk": (.75, .68, .53),
            "Amber": (.78, .31, .065), "Basalt": (.13, .16, .19), "Sky": (.25, .46, .65)
        }.items()}

    def actor(self, cls, name, xyz, pitch=0, yaw=0, folder="月坑环站"):
        position = ue.Vector(*(n * 100 for n in xyz))
        actor = check(self.actors.spawn_actor_from_class(cls, position, ue.Rotator(pitch=pitch, yaw=yaw, roll=0)), name)
        actor.set_actor_label(name)
        actor.set_folder_path(folder)
        return actor

    def solid(self, name, xyz, size, tone="Deck", pitch=0, yaw=0, collide=True, movable=False, mesh=None):
        actor = self.actor(ue.StaticMeshActor, name, xyz, pitch, yaw)
        comp = actor.static_mesh_component
        comp.set_mobility(ue.ComponentMobility.MOVABLE if movable else ue.ComponentMobility.STATIC)
        comp.set_static_mesh(mesh or self.cube)
        comp.set_material(0, self.palette[tone])
        comp.set_collision_profile_name("BlockAllDynamic" if movable else "BlockAll")
        if not collide:
            comp.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION)
        actor.set_actor_scale3d(ue.Vector(*size))
        return actor

    def deck(self, name, x0, x1, y0, y1, z):
        return self.solid(name, ((x1+x0)/2, (y1+y0)/2, z-.55), (x1-x0, y1-y0, 1.1))

    def run(self, name, a, b, width, edge=True):
        dx, dy, dz = [v-u for u,v in zip(a,b)]
        flat = math.hypot(dx,dy)
        angle = math.atan2(dz,flat)
        yaw = math.atan2(dy,dx)
        length = math.hypot(flat,dz)
        center = [(u+v)/2 for u,v in zip(a,b)]

        def beam(label, side, up, depth, breadth, tone, blocks):
            # 沿坡面法线偏移，使箱体上表面经过实测端点。
            cx = center[0] - math.sin(yaw)*side - math.cos(yaw)*math.sin(angle)*up
            cy = center[1] + math.cos(yaw)*side - math.sin(yaw)*math.sin(angle)*up
            pos = (cx,cy,center[2]+math.cos(angle)*up)
            return self.solid(label, pos, (length, breadth, depth), tone,
                              math.degrees(angle), math.degrees(yaw), blocks)

        beam(name,0,-.45,.9,width,"Deck",True)
        if edge:
            for sign in (-1,1):
                beam(name + " 路缘 " + str(sign), sign*(width/2-.13), .012,.022,.21,"Chalk",False)

    def layout(self, plate_cls, passage_cls):
        d, r, s = self.deck, self.run, self.solid
        d("A 南站月台", -8,5,-5,5,4)
        d("南站引道", 5,16,-3.5,3.5,4)
        d("B 外院",16,24,-5,5,4)
        d("外院至闸门",24,33,-2.6,2.6,4)
        d("西廊",17,23,-24,-5,4)
        d("W1 下廊分路",16,22,-32,-24,4)
        d("支路入口",18,22,-50,-32,4)
        d("Q 坑沿坡脚",16,20,-55,-50,4)
        r("Q–O 看台长坡",(20,-52,4),(56,-52,10),4)
        d("O 上看台",56,63,-56,-48,10)
        d("坑沿上廊",55.9,60,-48,-32,10)
        d("V 上层折点",56,61,-32,-25,10)
        r("V–W2 回落坡",(36,-28,6),(56,-28,10),4)
        r("W1–W2 检修短坡",(22,-28,4),(32,-28,6),6)
        d("W2 检修台",32,36,-32,-24,6)
        r("W2–I 内院廊",(34.5,-24,6),(36,-4,4),5.8)
        d("I 闸内院",33,40,-4,4,4)
        r("I–H 前庭坡",(40,0,4),(62,0,8),7)
        d("H 双拱前庭",62,72,-8,8,8)
        d("竞技场门前",72,80,-4.5,4.5,8)
        d("T 过门短廊",80,87,-3.3,3.3,8)
        for y in (-3.6,3.6):
            s("短廊侧墙", (83.5,y,11), (7,.8,6), "Frame")
        s("T 前庭门楣",(80,0,14.5),(1.6,8,1),"Chalk")
        s("短廊顶",(84,0,14.5),(6.4,8,1),"Frame")
        # 闸外挡墙在西廊前收头；门扇连同横栓向东收入侧墙。
        for y0,y1 in [(-22,-2),(2,19)]:
            s("内外院挡墙", (32,(y0+y1)/2,4),(.85,y1-y0,8),"Frame")
        s("闸门横楣",(32,0,8.35),(1.2,6.8,.7),"Chalk")
        leaf = s("K 活动闸门",(32,0,5.85),(.34,4,3.7),"Basalt",movable=True)
        bolt = s("闸内黄铜横栓",(32.24,0,5.55),(.24,3.75,.32),"Amber",movable=True)
        rule = ue.AttachmentRule.KEEP_WORLD
        check(bolt.attach_to_actor(leaf, "", rule, rule, rule, False), "横栓附着")
        s("检修踏板",(34.3,0,4.04),(1.6,3.4,.08),"Amber")
        plate = self.actor(plate_cls,"I 内侧踏板",(34.3,0,4.8))
        plate.get_component_by_class(ue.BoxComponent).set_box_extent(ue.Vector(74,166,76))
        plate.set_editor_property("GateLeaf",leaf)
        portal = self.actor(passage_cls,"T 竞技场入口",(84.8,0,10))
        portal.get_component_by_class(ue.BoxComponent).set_box_extent(ue.Vector(32,310,200))
        for x in (-6,-1.5):
            for y in (-4.4,4.4):
                s("南站立柱",(x,y,6.8),(.45,.45,5.6),"Frame")
        s("南站水平顶棚",(-4.6,0,9.8),(7,13,.6),"Chalk")
        s("南站檐口",(-1.15,0,9.7),(.25,13,.65),"Amber")
        for y in (-11.7,0,11.7):
            s("竞技场拱脚",(96,y,9.5),(4,2.25,19),"Frame")
        # 东拱完整，西外肩在上部留一段天空缺口。
        for label,y,z,span,pitch in [
            ("西外断肩",-10.6,19.3,3.3,46),("西拱冠",-4.6,24.65,4.2,0),
            ("西内肩",-1.9,21.9,7,-53),("东内肩",2.3,21.6,7.3,54),
            ("东拱冠",5.9,24.8,4,0),("东外肩",9.55,21.6,7.3,-54)]:
            s(label,(96,y,z),(span,4.1,2.25),"Chalk",pitch,90)
        for x,y,z in [(55,-54,9.7),(58,-53,10),(60,-49,10),(59,-38,10),
                      (19,-46,4),(20,-37,4),(67,7.5,8)]:
            s("坑沿护栏立柱",(x,y,z+.63),(.32,.32,1.26),"Frame")
        s("看台后护栏",(60,-55.6,10.85),(6.2,.22,.3),"Chalk")
        for x in (15,27,39,51,63):
            s("东侧远景屋顶",(x,30+((x//12)%2)*7,2.5+(x%4)),(8,12,6),"Basalt",collide=False)
        # 桥墩使玩家能从上层辨认下方路面和两种标高。
        for x,y,top in [(8,0,3),(20,-14,3),(26,-28,4),(35,-15,4),
                        (32,-52,5),(46,-52,7),(57,-42,9),(48,-28,7),(52,0,5)]:
            s("桥墩",(x,y,(top-9)/2),(1.6,2,top+9),"Frame")
        # 防止从路径边缘跌落后困在下方；正常两条路线都在上方桥面。
        self.world.get_world_settings().set_editor_property("kill_z",-1600)
        dome = s("天空背景",(40,-10,0),(430,430,430),"Sky",collide=False,mesh=ue.load_asset("/Engine/BasicShapes/Sphere"))
        dome.static_mesh_component.set_cast_shadow(False)
        sun = self.actor(ue.DirectionalLight,"月坑主光",(20,-16,42),-48,-42)
        sun.tags = ["GGYGO.KeyLight"]
        light = sun.get_component_by_class(ue.DirectionalLightComponent)
        light.set_mobility(ue.ComponentMobility.MOVABLE)
        light.set_intensity(3.0)
        sky = self.actor(ue.SkyLight,"天空补光",(0,0,18))
        sky.light_component.set_mobility(ue.ComponentMobility.MOVABLE)
        lamp = self.actor(ue.PointLight,"闸门检修灯",(34.4,1.8,6.3))
        self.actor(ue.PlayerStart,"南站出生点",(0,0,5.0))

    def finish_environment(self):
        by_label = {a.get_actor_label(): a for a in self.actors.get_all_level_actors()}
        fill = by_label["天空补光"].light_component
        cube = check(ue.load_asset("/Engine/MapTemplates/Sky/DaylightAmbientCubemap"), "日光环境贴图")
        fill.set_editor_property("source_type",ue.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
        fill.set_cubemap(cube)
        fill.set_editor_property("lower_hemisphere_is_black",False)
        fill.set_intensity(.45)
        sun = by_label["月坑主光"]
        sun.set_actor_rotation(ue.Rotator(pitch=-52,yaw=134,roll=0),False)
        sun.get_component_by_class(ue.DirectionalLightComponent).set_intensity(2.0)
        lamp = by_label["闸门检修灯"]
        lamp.set_actor_location(ue.Vector(3300,235,605),False,False)
        lamp.light_component.set_light_color(ue.LinearColor(1,.79,.57,1))
        lamp.light_component.set_intensity(1.1)
        lamp.light_component.set_attenuation_radius(230)

        def insert(name,xyz,size,tone,**kw):
            if name not in by_label:
                self.solid(name,xyz,size,tone,**kw)

        insert("坑底岩床",(37,-10,-10.5),(260,260,3),"Basalt",collide=False)
        for i,(x,y,sx,sy,height) in enumerate([
                (-19,-54,22,83,8),(15,-79,52,24,8),(70,-84,43,40,12),
                (105,-65,28,48,16),(116,22,40,92,14),(38,47,100,40,11),(-31,14,36,65,10)]):
            insert("坑壁台地 "+str(i),(x,y,-9+height/2),(sx,sy,height),"Frame",collide=False)
        # 看台转弯时的制动距离延伸到桥面。护槛沿桥外边缘一直通到折点。
        for name,xyz,size in [("看台转弯拓宽",(61.5,-40,9.45),(3,16,1.1)),
                              ("折点平台外角",(62,-28.5,9.45),(2,7,1.1))]:
            if name in by_label:
                by_label[name].set_actor_location(ue.Vector(*(v*100 for v in xyz)),False,False)
                by_label[name].set_actor_scale3d(ue.Vector(*size))
            else:
                self.solid(name,xyz,size,"Deck")
        insert("看台外护槛",(63.1,-44,10.6),(.22,24,.76),"Frame")
        insert("折点外护槛",(63.1,-28.5,10.6),(.22,7,.76),"Frame")
        insert("折点东护槛",(59.6,-24.8,10.6),(7,.22,.76),"Frame")
        insert("W1 检修台南护槛",(15.95,-28,4.6),(.22,8,.76),"Frame")
        for deck_name in ("Q–O 看台长坡","V–W2 回落坡","W1–W2 检修短坡","W2–I 内院廊","I–H 前庭坡"):
            deck = by_label[deck_name]
            scale = deck.get_actor_scale3d()
            rot = deck.get_actor_rotation()
            for side in (-1,1):
                delta = deck.get_actor_right_vector()*(side*(scale.y/2+.05)*100)
                pos = deck.get_actor_location()+delta+deck.get_actor_up_vector()*104
                insert(deck_name+" 护槛 "+str(side),(pos.x/100,pos.y/100,pos.z/100),
                       (scale.x-.9,.16,.76),"Frame",pitch=rot.pitch,yaw=rot.yaw)
        # 旧版上廊外栏已由连到折点的外护槛覆盖。只清理本生成器的旧件。
        if "外廊护槛 2" in by_label:
            check(self.actors.destroy_actor(by_label["外廊护槛 2"]), "移除旧上廊外栏")
        for idx,x,y,h,sx,sy in [(0,9.7,-3.55,4,9,.18),(1,9.7,3.55,4,9,.18),(3,55.8,-42,10,.16,18)]:
            insert("外廊护槛 "+str(idx),(x,y,h+.60),(sx,sy,.76),"Frame")


def build():
    if os.environ.get("GGYGO_STATION_ROUTE") == "Lighting":
        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        check(levels.load_level(MAP), MAP)
        world = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
        Station(world).finish_environment()
        check(levels.save_current_level(), MAP)
        ue.log("LUNAR_LIGHTING_OK "+MAP)
        return
    check(not ASSETS.does_asset_exist(MAP), "目标地图已存在，请保留原图")
    check(ASSETS.does_asset_exist(DEST), DEST)
    mode = check(ue.load_class(None, "/Game/BP/GamePlay/BP_GameMode.BP_GameMode_C"), "BP_GameMode")
    plate = make_trigger(PLATE,True)
    passage = make_trigger(EXIT,False)
    world = check(ue.EditorLoadingAndSavingUtils.new_blank_map(False), "新空图")
    world.get_world_settings().set_editor_property("default_game_mode",mode)
    station = Station(world)
    station.layout(plate,passage)
    station.finish_environment()
    check(ue.EditorLoadingAndSavingUtils.save_map(world,MAP), MAP)
    ue.log("LUNAR_BUILD_OK " + MAP)


if __name__ == "__main__":
    build()
