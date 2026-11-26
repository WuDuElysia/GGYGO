"""制作 Kevin 火刃入场时的材质准备组件，沿用项目已有 Niagara 资源准备机制。"""
import unreal as ue

from wire_pawn_input_resource_preparation import PREPARATION, SYSTEM, _connect, _pin


def build_preparation(folder, system):
    assets = ue.EditorAssetLibrary
    bp_lib = ue.BlueprintEditorLibrary
    path = folder + '/BP_Kevin_FlamePreparation'
    if assets.does_asset_exist(path):
        bp = ue.load_asset(path)
        if list(ue.get_default_object(bp.generated_class()).get_editor_property('FlameSystems')) != [system]:
            raise RuntimeError('Kevin 火刃预加载资源不匹配')
        return bp
    bp = bp_lib.create_blueprint_asset_with_parent(path, ue.ActorComponent.static_class())
    graph = ue.BlueprintGraphEditor.get_graph_editor(bp_lib.find_event_graph(bp))
    ns_type = bp_lib.get_array_type(bp_lib.get_object_reference_type(ue.NiagaraSystem.static_class()))
    request_type = bp_lib.get_object_reference_type(ue.GGYGONiagaraMaterialPreparation.static_class())
    if not graph.add_member_variable('FlameSystems',ns_type,'("' + system.get_path_name() + '")'):
        raise RuntimeError('无法设置火刃预加载列表')
    if not graph.add_member_variable('FlamePreparation',request_type,'None'):
        raise RuntimeError('无法设置火刃预加载请求')

    def place(node,x,y):
        node.set_node_pos(ue.IntPoint(x,y))
        return node

    def event(name,y):
        node = graph.find_event_node(name) or bp_lib.add_event_override(bp,name,ue.IntPoint(0,y))
        return place(node,0,y)

    def call(path,name,x,y):
        return place(graph.add_call_function_node(path+'.'+name),x,y)

    def link(a,output,b,input_name):
        _connect(_pin(a,output),_pin(b,input_name))

    begin = event('ReceiveBeginPlay',0)
    owner = call('/Script/Engine.ActorComponent','GetOwner',-150,240)
    dedicated = call(SYSTEM,'IsDedicatedServer',60,140)
    render = place(graph.add_branch_node(),380,0)
    systems = place(graph.add_get_member_variable_node('FlameSystems',''),410,250)
    create = call(PREPARATION,'CreateForSystemAssets',670,0)
    hold = place(graph.add_set_member_variable_node('FlamePreparation',''),1020,0)
    start = call(PREPARATION,'Start',1320,0)
    for node in (dedicated,create):
        result = ue.GGYGOAnimationGraphEditorLibrary.connect_blueprint_call_world_context(bp,node,'WorldContextObject',owner,'ReturnValue')
        if not result.succeeded:
            raise RuntimeError(result.error)
    link(begin,'then',render,'execute')
    link(dedicated,'ReturnValue',render,'Condition')
    link(render,'else',create,'execute')
    link(owner,'ReturnValue',create,'Owner')
    link(systems,'FlameSystems',create,'Systems')
    link(create,'then',hold,'execute')
    link(create,'ReturnValue',hold,'FlamePreparation')
    link(hold,'then',start,'execute')
    link(create,'ReturnValue',start,'self')

    end = event('ReceiveEndPlay',560)
    request = place(graph.add_get_member_variable_node('FlamePreparation',''),0,800)
    valid = call(SYSTEM,'IsValid',300,800)
    cleanup = place(graph.add_branch_node(),580,560)
    cancel = call(PREPARATION,'Cancel',880,560)
    link(end,'then',cleanup,'execute')
    link(request,'FlamePreparation',valid,'Object')
    link(valid,'ReturnValue',cleanup,'Condition')
    link(cleanup,'then',cancel,'execute')
    link(request,'FlamePreparation',cancel,'self')
    bp_lib.compile_blueprint(bp)
    if bp.get_editor_property('Status') != ue.BlueprintStatus.BS_UP_TO_DATE or not assets.save_loaded_asset(bp,False):
        raise RuntimeError('火刃预加载组件编译或保存失败')
    return bp


def install(folder, system):
    cls = build_preparation(folder,system).generated_class()
    boss = ue.load_asset('/Game/Characters/Boss/Kevin/DemonBattle/Blueprints/BP_Kevin_DemonBattle')
    subsystem = ue.get_engine_subsystem(ue.SubobjectDataSubsystem)
    lib = ue.SubobjectDataBlueprintFunctionLibrary
    handles = subsystem.k2_gather_subobject_data_for_blueprint(boss)
    templates = [lib.get_object(lib.get_data(h)) for h in handles]
    count = sum(obj.get_class() == cls for obj in templates if obj)
    if count == 1:
        return
    if count > 1:
        raise RuntimeError('Kevin 已装配多个火刃预加载组件')
    handle,reason = subsystem.add_new_subobject(ue.AddNewSubobjectParams(parent_handle=handles[0],
        new_class=cls,blueprint_context=boss))
    if not lib.is_handle_valid(handle):
        raise RuntimeError('Kevin 无法装配火刃预加载组件 '+str(reason))
    ue.BlueprintEditorLibrary.compile_blueprint(boss)
    if boss.get_editor_property('Status') != ue.BlueprintStatus.BS_UP_TO_DATE or not ue.EditorAssetLibrary.save_loaded_asset(boss,False):
        raise RuntimeError('Kevin 装配火刃预加载组件后编译或保存失败')
