# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Original J6-to-J7 load-path candidate; native vendor CAD remains private."""
from pathlib import Path
import argparse, hashlib, itertools, json
import cadquery as cq
import numpy as np
from build_layout import frame, moved
from mount_interface_study import load_vendor, ring, bores
from build_link56_study import cylinder, face_contact
from studies.link_interface_tools import check, cache

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/link67-study'
REV='R4-LINK67-01'
PARAM_SHA='4349d1797b906b67a7bc396fcb84bc439c2d70dd0b337659e552cee293d2dd81'
POST=np.array([[44,16],[-44,16],[-44,-16],[44,-16]],float)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def box(x,y,z,c):return cq.Workplane('XY').box(x,y,z).translate(tuple(c)).val()

def make_parts(i17,i14):
    op=np.array([p['xy_mm'] for p in i17['output_holes']['points']])
    fp=np.array([p['xy_mm'] for p in i14['fixed_through_holes']['points']])
    T6=frame([0,0,605],[0,1,0]);T7=frame([0,55,640],[0,0,1])
    out=ring(36,22,0,6).union(cq.Workplane('XY').rect(104,48).extrude(6))
    out=out.cut(bores([[0,0]],22,-1,8)).cut(bores([[0,0]],23.8,-1,3.5))
    out=out.union(bores(POST.tolist(),7,6,16))
    for x,v in POST:
        r=np.hypot(x,v);direction=np.array([x/r,v/r,0.])
        rib=cq.Workplane('XZ').polyline([(27.5,6),(r,6),(r,22),(27.5,12)]).close().extrude(6,both=True).val()
        out=out.union(moved(rib,frame([0,0,0],[0,0,1],direction)))
    out=out.cut(bores(op.tolist(),1.75,-1,25)).cut(bores(op.tolist(),3.2,4,22))
    out=out.cut(bores(POST.tolist(),2.1,3,20)).val().clean()
    rear=ring(38,29.3,595.5,14).translate((0,55,0)).val()
    for x in [-44,44]:
        rear=rear.fuse(box(14,12,48,[x,28,605]))
        rear=rear.fuse(box(24,24,14,[np.sign(x)*37,34,602.5]))
    rear=rear.cut(cylinder([0,55,550],[0,0,1],29.3,100)).clean()
    rear=rear.cut(moved(bores(fp.tolist(),1.25,-45.5,16).val(),T7)).clean()
    for x,v in POST:rear=rear.cut(cylinder([x,21,605-v],[0,1,0],2.75,14))
    front=ring(38,29.6,-10,3).cut(bores(fp.tolist(),1.75,-11,5))
    front=front.cut(bores([[32,0],[-32,0],[0,32],[0,-32]],3.1,-11,5)).val()
    assembled={'output_adapter':moved(out,T6),'rear_carrier':rear,'front_ring':moved(front,T7)}
    for n,s in assembled.items():assert s.isValid() and len(s.Solids())==1,(n,s.isValid(),len(s.Solids()))
    return assembled,op,fp,T6,T7

def make_hardware(op,fp,T6,T7):
    hw={};free={};tools={};rows=[]
    def bolt(name,seat,axis,d,L,H,D,grip,engage,owner,stage,selected=True):
        seat=np.asarray(seat,float);axis=np.asarray(axis,float)
        head=cylinder(seat,axis,D/2,H)
        hw[name]=head.fuse(cylinder(seat,-axis,d/2,L))
        free[name]=head.fuse(cylinder(seat,-axis,d/2,grip))
        tools[name]=cylinder(seat+axis*H,axis,2.5 if d==5 else 2,60)
        rows.append({'id':name,'thread':f'M{d}','selected_length_mm':L if selected else None,
          'modeled_length_mm':L,'seat_world_mm':seat.tolist(),'head_outward_axis':axis.tolist(),
          'head_D_H_mm':[D,H],'free_grip_mm':grip,'nominal_geometric_engagement_mm':engage,
          'thread_owner':owner,'stage':stage,'length_selected':selected})
    for i,(x,v) in enumerate(op):
        bolt(f'OUT_M3_unknown_{i+1}',(T6@np.array([x,v,4,1]))[:3],[0,1,0],3,7,3,5.68,7,None,'J6',1,False)
    for i,(x,v) in enumerate(POST):
        bolt(f'POST_M5x25_{i+1}',[x,34,605-v],[0,1,0],5,25,5,8.72,12,13,'output_adapter',2)
    for i,(x,y) in enumerate(fp):
        bolt(f'FIX_M3x40_{i+1}',(T7@np.array([x,y,-7,1]))[:3],[0,0,1],3,40,3,5.68,23.5,14,'rear_carrier',4)
    return hw,free,tools,rows

def load_prior(models):
    import build_link56_study as l56
    path=ROOT/'engineering/generated/link56-study/part-placements.json'
    data=json.loads(path.read_text());prior={}
    for n,r in data['instances'].items():
        s=cq.importers.importStep(str(path.parent/(r['part_id']+'.step'))).val()
        prior['L56_'+n]=moved(s,np.array(r['T_world_from_part_mm']))
    iface=models['RH17-B']['unified_joint_interface']
    op=np.array([p['xy_mm'] for p in iface['output_holes']['points']]);fp=np.array([p['xy_mm'] for p in iface['fixed_through_holes']['points']])
    hw=l56.make_hardware(op,fp,frame([0,-55,450],[0,0,1]),frame([0,0,605],[0,1,0]))[0]
    prior.update({'L56_HW_'+n:s for n,s in hw.items()})
    return prior

def validate(a,v,prior,hw,free,tools,rows,head):
    shapes={**a,**v,**prior,**head};cached={n:cache(s) for n,s in shapes.items()}
    checks={'static':{},'hardware':{},'tools':{},'contacts':{}}
    for x,y in itertools.combinations(cached,2):
        if x not in a and y not in a:continue
        checks['static'][x+'__'+y]=check(cached[x],cached[y])
    for row in rows:
        n=row['id']
        for target,s in cached.items():checks['hardware'][n+'__'+target]=check(free[n] if target==row['thread_owner'] else hw[n],s)
        present={1:['output_adapter','J5','J6',*prior],2:['output_adapter','rear_carrier','J5','J6',*prior],4:[*a,*v,*prior]}[row['stage']]
        for target in present:checks['tools'][n+'__'+target]=check(tools[n],cached[target])
        installed={k:s for k,s in hw.items() if next(x['stage'] for x in rows if x['id']==k)<=row['stage'] and k!=n}
        for target,s in installed.items():checks['tools'][n+'__'+target]=check(tools[n],s)
    for x,y in itertools.combinations(hw,2):checks['hardware'][x+'__'+y]=check(hw[x],hw[y])
    for x,y,o,z in [('J6','output_adapter',[0,0,605],[0,1,0]),('output_adapter','rear_carrier',[0,22,605],[0,1,0]),('rear_carrier','J7',[0,55,609.5],[0,0,1]),('front_ring','J7',[0,55,630],[0,0,1])]:
        checks['contacts'][x+'__'+y]=face_contact(shapes[x],shapes[y],o,z)
    return checks

def check_insertions(a,v,prior,hw):
    preceding={'J5':v['J5'],'J6':v['J6'],**prior}
    outbolts={n:s for n,s in hw.items() if n.startswith('OUT_')}
    postbolts={n:s for n,s in hw.items() if n.startswith('POST_')}
    result={'sampled':[]}
    stages=[('output_adapter',[0,1,0],100,preceding),
      ('rear_carrier',[0,1,0],100,{**preceding,'output_adapter':a['output_adapter'],**outbolts}),
      ('front_ring',[0,0,1],100,{**preceding,'output_adapter':a['output_adapter'],'rear_carrier':a['rear_carrier'],'J7':v['J7'],**outbolts,**postbolts})]
    for name,axis,length,targets in stages:
        print('Insertion',name,flush=True);target={k:cache(s) for k,s in targets.items()};bad=[]
        distances=sorted(set([0,.1,.5,1,2,*range(5,length+1,5)]))
        for d in distances:
            probe=a[name].translate(tuple(np.asarray(axis)*d))
            for n,s in target.items():
                c=check(probe,s)
                if c['events']:bad.append({'distance_mm':d,'other':n,**c})
        result['sampled'].append({'part':name,'world_axis':axis,'distances_mm':distances,'collisions':bad,
           'stationary':list(targets),'scope':'Discrete straight insertion stations; not continuous or tolerance proof.'})
    T7=frame([0,55,640],[0,0,1])
    rear=cylinder([0,0,-79.8],[0,0,1],29.05,49.3)
    front=cylinder([0,0,-30.5],[0,0,1],35.05,32.6)
    envelope=moved(rear.fuse(front),T7)
    outside=[]
    for i,s in enumerate(v['J7'].Solids()):
        d=s.cut(envelope);outside.append({'solid':i,'outside_envelope_mm3':abs(d.Volume()) if d.Solids() else 0})
    assert sum(x['outside_envelope_mm3'] for x in outside)<1e-4, outside
    sweep=moved(rear.fuse(cylinder([0,0,-30.5],[0,0,1],35.05,172.6)),T7)
    targets={**preceding,'output_adapter':a['output_adapter'],'rear_carrier':a['rear_carrier'],**outbolts,**postbolts}
    result['J7_continuous']={'translation_world_mm':[0,0,140],'source_solid_containment':outside,
      'joint_frame_envelope_mm':{'rear_R':29.05,'rear_Z':[-79.8,-30.5],'front_R':35.05,'front_Z':[-30.5,2.1]},
      'sweep_front_Z_mm':[-30.5,142.1],'checks':{n:check(sweep,s) for n,s in targets.items()},
      'method':'Each actual vendor solid is contained by Boolean difference. Larger front radius encloses every translated rear cylinder over the whole 0..140mm insertion interval. Nominal only; no cable/tool/hand volume.'}
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rh17-step',required=True,type=Path);ap.add_argument('--rh14-step',required=True,type=Path)
    ap.add_argument('--out',type=Path,default=OUT);ap.add_argument('--private-assembly',type=Path)
    ap.add_argument('--insertions',action='store_true')
    args=ap.parse_args();assert sha(ROOT/'engineering/parameters/r4-layout.json')==PARAM_SHA
    models={m['id']:m for m in json.loads((ROOT/'docs/engineering/sources/rh-interface-extraction.json').read_text())['models']}
    a,op,fp,T6,T7=make_parts(models['RH17-B']['unified_joint_interface'],models['RH14-N']['unified_joint_interface'])
    v17=load_vendor(args.rh17_step,models['RH17-B']);v14=load_vendor(args.rh14_step,models['RH14-N'])
    v={'J5':moved(v17,frame([0,-55,450],[0,0,1])),'J6':moved(v17,T6),'J7':moved(v14,T7)}
    prior=load_prior(models);hw,free,tools,rows=make_hardware(op,fp,T6,T7)
    headpath=ROOT/'engineering/generated/p16-carrier-01/main-carrier.step'
    head={'head_main_carrier':cq.importers.importStep(str(headpath)).val().translate((0,55,780))} if headpath.exists() else {}
    checks=validate(a,v,prior,hw,free,tools,rows,head)
    errors={c+'__'+n:r for c in ['static','hardware','tools'] for n,r in checks[c].items() if r['events']}
    if args.insertions and not errors:
        ins=check_insertions(a,v,prior,hw);checks['insertions']=ins
        for r in ins['sampled']:
            if r['collisions']:errors['insertion__'+r['part']]=r
        for n,r in ins['J7_continuous']['checks'].items():
            if r['events']:errors['J7_continuous__'+n]=r
    data={'revision':REV,'parameters_sha256':PARAM_SHA,'generator_sha256':sha(Path(__file__)),
      'source_vendor_sha256':{'RH17-B':sha(args.rh17_step),'RH14-N':sha(args.rh14_step)},
      'head_main_carrier_sha256':sha(headpath) if head else None,'checks':checks,'errors':errors,'hardware':rows,
      'original_mass_kg':sum(s.Volume()*2.7e-6 for s in a.values()),'manufacturing_release':False}
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'geometry-probe.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({'original_mass_kg':data['original_mass_kg'],'contacts':checks['contacts'],'errors':errors},indent=2),flush=True)
    if args.private_assembly:
        assert ROOT not in args.private_assembly.resolve().parents
        args.private_assembly.parent.mkdir(parents=True,exist_ok=True)
        cq.exporters.export(cq.Compound.makeCompound(list({**a,**v,**prior,**hw,**head}.values())),str(args.private_assembly))

if __name__=='__main__':main()
