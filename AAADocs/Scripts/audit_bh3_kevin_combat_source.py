"""Read-only audit of BH3 DemonBattle combat authoring evidence. No Unreal needed.

Run with Python 3 from any directory; source FBX/JSON are never changed.
Outputs detailed evidence in Saved/Codex and a proposed action manifest in AAADocs.
All suggested roles are design proposals, never recovered game damage events.
"""
import collections
import hashlib
import json
import math
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fbx_bin_reader import FbxReader, decode_placeholder
from fbx_anim_extract import build_index, resolve_take_curvenodes, get_curve_arrays, FBXTIME
from import_bh3_kevin_demonbattle import SOURCE, BASE, string, properties

PROJECT = Path(__file__).resolve().parents[2]
OUT = PROJECT / 'Saved/Codex'
EXACT = {'BOSS_411','Root','Bip001','Bip001 Prop1','PushZone','HitBox','CounterHitBox',
         'Weapon','Weapon_Effect','LanceThrowAttach','ExecuteThrowRoot','Charge_Follow',
         'Ice_Column_Spawn','GroundCrack','FireExecuteCounterPoint','FireExecuteCounterPoint1',
         'FireExecuteCounterPoint2','Fire_Down_Follow_Point','ForceKillThrowPoint','LeftHandThrowPoint',
         'HitArrowWeakness_Head','BattleYLink'}
EVENT = re.compile(r'event|notify|damage|collid|trigger|hitwindow|hitbox|attackwindow|active|enabled|visibility', re.I)

def json_paths(value, prefix=''):
    if isinstance(value,dict):
        for k,v in value.items():
            p=prefix+'.'+k if prefix else k
            yield p,v
            yield from json_paths(v,p)
    elif isinstance(value,list):
        for v in value:
            yield from json_paths(v,prefix+'[]')

def summary(times,values,rate):
    if not values: return {'keys':0}
    delta=[i for i in range(1,len(values)) if abs(values[i]-values[i-1])>1e-5]
    intervals=[]
    for i in delta:
        start,end=times[i-1]/FBXTIME,times[i]/FBXTIME
        if intervals and start<=intervals[-1][1]+1e-7: intervals[-1][1]=end
        else: intervals.append([start,end])
    return {'keys':len(values),'first':values[0],'last':values[-1], 'min':min(values),'max':max(values),
            'range':max(values)-min(values),'changed_intervals_seconds':intervals,
            'changed_intervals_frames':[[round(a*rate,4),round(b*rate,4)] for a,b in intervals]}

def role(name,loop,empty):
    short=re.sub(r'^BOSS?_\d+_Ani_', '',name)
    if empty: return 'source_empty','skip','源FBX无曲线；不能恢复HitBox开关或武器显隐语义'
    if short in ('StandBy','Fly_Loop','Move_L_Loop','Move_R_Loop','Stun'):
        return 'state_loop','sequence_state','用于待机/移动/眩晕持续状态；默认不建攻击Montage'
    if short.startswith('Move_'): return 'locomotion_transition','sequence_state','移动起止素材；BS/AS先后需预览确认'
    if short in ('Dash_B','Dash_F','Fly_Evade'): return 'evade','single_montage','无伤害通知；位移由玩法另定'
    if short=='Die': return 'death','single_montage','单次死亡表现；末姿保持由玩法控制'
    if short.startswith(('Hit_','ThrowUp_','ThrowFall_','ThrowBlow','ThrowDown','KnockDown','StandUp')):
        return 'reaction','sequence_state' if loop or short.endswith('_Y') else 'single_montage','受击/抛飞/倒地恢复，不作为攻击判定源'
    if short.startswith('Be_Executed'): return 'execution_victim','paired_montage','被处决配对表现；不能当Boss主动伤害动作'
    if short.startswith('Force_Kill_ThrowSkill'): return 'execution_attacker','paired_montage','抓取/处决候选；需对齐受害者与取消策略'
    if short.startswith('ThrowSkill_DragLoop_'): return 'pose_helper','sequence_pose','极短拖拽方向姿势素材；名称Loop不等于源loopTime'
    if short=='Fire_Execute_BS_Test': return 'test_clip','defer','源名含Test，先隔离，不默认接战斗'
    if short.startswith('Fire_Execute_Defence_'): return 'defence_reaction','single_montage','防御/处决反应候选；无源伤害时间'
    if short.startswith('Fire_Execute_Wing_Defence_'): return 'defence_phase','section_family','防御阶段候选，循环显式退出；无默认伤害'
    if short.startswith('Wing_Defence_') and 'ThrowSkill' not in short:
        return 'defence_phase','section_family' if short.endswith(('_BS','_Loop')) else 'single_montage','防御/破防表现候选；CounterHitBox运动不等于有效判定'
    if 'ThrowSkill' in short: return 'grab_attack','paired_montage','抓取候选；动作与受害者配对未确认'
    if short=='Counter': return 'counter_attack','single_montage','反击候选；判定窗口待预览/人工标定'
    if short.startswith('Fire_Attack_04_') and short.endswith(('_Wait','_Loop','_Spline','_Charge')):
        return 'attack_hold','section_family','空中/下落/蓄力保持阶段；不得默认全段伤害'
    if short.startswith(('Fire_Attack_03','Fire_Attack_04','Ice_Attack_03','Fly_Attack_03')):
        return 'attack_phase','section_family','攻击族分段候选；次序/伤害类型需预览确认'
    if 'Attack' in short: return 'attack','single_montage','主动攻击候选；仅建立待标定窗口，不捏造源判定'
    raise ValueError('Unclassified '+name)

def family(name):
    s=re.sub(r'^BOSS?_\d+_Ani_', '',name)
    for f in ['Fire_Execute_Wing_Defence','Force_Kill_ThrowSkill','Be_Executed','Fire_Attack_03','Fire_Attack_04',
              'Ice_Attack_03','Fly_Attack_03','Move_L','Move_R','ThrowSkill_DragLoop','Fire_Execute_Defence']:
        if s.startswith(f): return f
    if s.startswith('Wing_') and 'ThrowSkill' in s: return 'Wing_ThrowSkill'
    if s.startswith('Wing_Defence'): return 'Wing_Defence'
    return s

def inspect(path,rate):
    reader=FbxReader(str(path))
    try:
        assert reader.read_header()<7500
        roots=reader.parse(); idx=build_index(roots)
        assert len(idx['stacks'])==1
        tracks=resolve_take_curvenodes(idx,next(iter(idx['stacks'])))
        counts=collections.Counter(); candidates={}; endpoints={}; keylo=None; keyhi=None
        for bone,props in tracks.items():
            for prop,channels in props.items():
                counts[prop]+=len(channels)
                for axis,ident in channels.items():
                    times,values=get_curve_arrays(reader.f,idx['curves'][ident])
                    if times:
                        keylo=min(times) if keylo is None else min(keylo,min(times))
                        keyhi=max(times) if keyhi is None else max(keyhi,max(times))
                    if bone in EXACT:
                        candidates.setdefault(bone,{}).setdefault(prop,{})[axis]=summary(times,values,rate)
                    if bone.startswith('Bip001') and values:
                        endpoints.setdefault(bone,{}).setdefault(prop,{})[axis]=[values[0],values[-1]]
        model_props={}; customs=[]
        for n in idx['id2node'].values():
            if n.name=='Model':
                name=string(n.props[1]); p=properties(n)
                if name in EXACT: model_props[name]=p
                for pn,pv in p.items():
                    if EVENT.search(pn): customs.append({'node':name,'property':pn,'value':pv})
        all_node_names=collections.Counter()
        def walk(n):
            all_node_names[n.name]+=1
            for c in n.children: walk(c)
        for n in roots: walk(n)
        semantic_nodes={k:v for k,v in all_node_names.items() if EVENT.search(k)}
        source=path.read_bytes()
        return {'curve_objects':len(idx['curves']),'animated_nodes':len(tracks),'animated_properties':dict(counts),
                'key_range_seconds':None if keylo is None else [keylo/FBXTIME,keyhi/FBXTIME],
                'candidate_local_tracks':candidates,'candidate_reference_properties':model_props,
                'event_like_model_properties':customs,'event_like_node_names':semantic_nodes,
                'sha256':hashlib.sha256(source).hexdigest()}, endpoints
    finally: reader.close()

def seam(a,b):
    # Local scalar endpoint comparison, not an evaluated/global skeleton pose.
    # Euler components are wrapped to [-180,180]; this is a ranking heuristic.
    errors=[]
    for bone in a.keys() & b.keys():
        for prop in a[bone].keys() & b[bone].keys():
            v=[]
            for axis in a[bone][prop].keys() & b[bone][prop].keys():
                diff=b[bone][prop][axis][0]-a[bone][prop][axis][1]
                if prop=='Lcl Rotation': diff=(diff+180)%360-180
                v.append(diff)
            if v: errors.append((prop,math.sqrt(sum(x*x for x in v))))
    result={}
    for prop in ['Lcl Translation','Lcl Rotation','Lcl Scaling']:
        vals=sorted(v for p,v in errors if p==prop)
        if vals: result[prop]={'bones':len(vals),'median':vals[len(vals)//2],'max':max(vals)}
    return result

def weapon_skin_evidence():
    reader=FbxReader(str(SOURCE/'BOSS_411.fbx'))
    try:
        idx=build_index(reader.parse()); result=[]
        for ident,node in idx['id2node'].items():
            if node.name!='Geometry' or string(node.props[1])!='Weapon': continue
            vertices=next(c.props[0] for c in node.children if c.name=='Vertices')
            points=decode_placeholder(reader.f,vertices)
            for skin,_ in idx['child_conns'][ident]:
                if idx['id2type'].get(skin)!='Deformer':continue
                for cluster,_ in idx['child_conns'][skin]:
                    if idx['id2type'].get(cluster)!='Deformer':continue
                    cnode=idx['id2node'][cluster]
                    arrays={c.name:decode_placeholder(reader.f,c.props[0]) for c in cnode.children if c.name in ['Indexes','Weights','Transform','TransformLink']}
                    result.append({'cluster':string(cnode.props[1]),'bones':[idx['model_id2name'][b] for b,_ in idx['child_conns'][cluster] if b in idx['model_id2name']],
                                   'vertex_count':len(points)//3,'weighted_vertices':len(arrays['Indexes']),
                                   'weights_min':min(arrays['Weights']),'weights_max':max(arrays['Weights']),
                                   'geometry_bounds_min':[min(points[i::3]) for i in range(3)],
                                   'geometry_bounds_max':[max(points[i::3]) for i in range(3)],
                                   'mesh_bind_matrix':arrays['Transform'],'bone_bind_matrix':arrays['TransformLink']})
        return result
    finally:reader.close()

def main():
    settings=json.loads((SOURCE/'anim_settings.json').read_text(encoding='utf-8-sig'))
    schema=collections.Counter(); event_hits=[]; details=[]; actions=[]; endpoints={}
    for entry in settings['clips']:
        meta=json.loads((SOURCE/entry['json']).read_text(encoding='utf-8-sig')); c=meta['clip']; muscle=c['muscleClip']; rate=c['sampleRate']
        for p,v in json_paths(meta):
            schema[p]+=1
            if EVENT.search(p): event_hits.append({'clip':entry['name'],'path':p,'value':v})
        fbx,end=inspect(SOURCE/entry['fbx'],rate); endpoints[entry['name']]=end
        empty=fbx['curve_objects']==0; category,use,why=role(entry['name'],muscle['loopTime'],empty)
        moving={}
        for n,props in fbx['candidate_local_tracks'].items():
            channels={p+'.'+a:s['range'] for p,chans in props.items() for a,s in chans.items() if s.get('range',0)>1e-5}
            if channels:moving[n]=channels
        root_json=[{'attribute':x['attribute'],**summary([k['t']*FBXTIME for k in x['keys']],[k['v'] for k in x['keys']],rate)} for x in (c['rootMotionCurves'] or [])]
        row={'name':entry['name'],'source_json':entry['json'],'source_fbx':entry['fbx'], 'sample_rate':rate,
             'json_start':muscle['startTime'],'json_stop':muscle['stopTime'],'loop_time':muscle['loopTime'],
             'loop_settings':{k:v for k,v in muscle.items() if k.startswith('loop') or k in ['startAtOrigin','keepOriginalOrientation','keepOriginalPositionY','keepOriginalPositionXZ','orientationOffsetY','cycleOffset','level','mirror']},
             'apply_root_motion':meta['animator']['applyRootMotion'],'root_motion_bone':meta['avatar']['rootMotionBoneName'],
             'json_root_motion_curves':root_json,'fbx':fbx}
        details.append(row)
        actions.append({'name':entry['name'],'source_json':entry['json'],'source_fbx':entry['fbx'],
                        'sequence':None if empty else BASE+'/Animation/AS_'+re.sub('[^a-zA-Z0-9_]', '_',entry['name']),
                        'source_empty':empty,'family':family(entry['name']),'category_proposal':category,'use_proposal':use,'rationale':why,
                        'sample_rate':rate,'source_loop_time':muscle['loopTime'],'json_range_seconds':[muscle['startTime'],muscle['stopTime']],
                        'fbx_key_range_seconds':fbx['key_range_seconds'],'moving_candidate_local_tracks':moving,
                        'damage_windows':[], 'damage_window_evidence':'none_in_export; requires gameplay specification and visual annotation',
                        'montage_status':'proposal_only; not created','family_order_status':'not established by source metadata'})
    schemas=set()
    for p,v in json_paths(settings):
        schemas.add(p)
        if EVENT.search(p):event_hits.append({'clip':'anim_settings','path':p,'value':v})
    families=collections.defaultdict(list)
    for a in actions:
        if not a['source_empty']:families[a['family']].append(a['name'])
    seams={f:[{'from':a,'to':b,'local_endpoint_error':seam(endpoints[a],endpoints[b])} for a in names for b in names if a!=b]
           for f,names in families.items() if len(names)>1}
    report={'source':str(SOURCE),'clip_count':len(actions),'json_schema_paths':sorted(schema),
            'settings_schema_paths':sorted(schemas),'json_event_like_keys':event_hits,
            'weapon_skin':weapon_skin_evidence(),
            'candidate_nodes':sorted(EXACT),'clips':details,'family_seam_rank_evidence':seams,
            'limitations':['No Unity gameplay scripts/controller graph/collider components/events supplied by this export.',
                           'Local helper transforms are not collision volumes or activation windows; parent chains affect global motion.',
                           'Local Euler endpoint comparison is only a continuity clue, not verified montage section order.']}
    manifest={'status':'proposal_only_pending_root_contract','source':str(SOURCE),'source_clips':79,'importable_sequences':75,
              'all_damage_windows_unset':True,'actions':actions}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'bh3_kevin_combat_source_evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    (PROJECT/'AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Action_Manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'clips':len(actions),'event_like_json_keys':len(event_hits),'categories':dict(collections.Counter(a['category_proposal'] for a in actions)),
                      'uses':dict(collections.Counter(a['use_proposal'] for a in actions)),
                      'animated_properties':dict(sum((collections.Counter(c['fbx']['animated_properties']) for c in details),collections.Counter()))},ensure_ascii=False))

if __name__=='__main__': main()
