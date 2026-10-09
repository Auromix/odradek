# SPDX-License-Identifier: CC-BY-NC-4.0
"""Integrated nominal BREP screening; cable chords are rejected probes, not routes."""
from pathlib import Path
import sys,json,hashlib,math,importlib.util,time
import numpy as np,cadquery as cq
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=HERE/'build';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'engineering/arm_a11'));import collision as co
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common,BRepAlgoAPI_Cut
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths={n:ROOT/p for n,p in dict(arm='engineering/arm_a11/build',wrist='engineering/arm_a12/wrist02/build',core='engineering/arm_a13/j7-fit01/build',if01='engineering/arm_a13/tool-if01/build',if02='engineering/arm_a13/tool-if02/build').items()}
D={n:json.loads((p/'manifest.json').read_text()) for n,p in paths.items()};source_hashes={str((p/'manifest.json').relative_to(ROOT)):sha(p/'manifest.json') for p in paths.values()}
L=D['arm']['layout'];co.ld.LAYOUT=L;co.ld.TARGET['flange_frame']={'parent':'J7.rotor','translation_mm':[110,0,0]}
def load(p,id):
 f=p/'step'/(id+'.step');source_hashes[str(f.relative_to(ROOT))]=sha(f);return cq.importers.importStep(str(f)).val()
def rigid(fr):return 0 if fr=='world' else int(fr[1])-(fr.endswith('.fixed'))
def ov(s,t):
 op=BRepAlgoAPI_Common(s.wrapped,t.wrapped)
 if op.IsDone():
  if op.Shape().IsNull():return 0,'common_empty'
  r=cq.Shape.cast(op.Shape());assert r.isValid();return sum(q.Volume() for q in r.Solids()),'common'
 diffs=[]
 for a,b in [(s,t),(t,s)]:
  cut=BRepAlgoAPI_Cut(a.wrapped,b.wrapped);assert cut.IsDone();r=cq.Shape.cast(cut.Shape());assert r.isValid();diffs.append(sum(z.Volume() for z in a.Solids())-sum(z.Volume() for z in r.Solids()))
 assert min(diffs)>-.001 and abs(diffs[0]-diffs[1])<.001;return max(0,*diffs),'bidirectional_cut'
def disjoint(bb,cb):return any(getattr(bb,k+'max')<=getattr(cb,k+'min')+1e-5 or getattr(cb,k+'max')<=getattr(bb,k+'min')+1e-5 for k in ['x','y','z'])
# Compare changed J7 module against retained upstream hardware and ALL six wrist shields.
others=[]
for p in D['arm']['parts']:
 if p['role'] in ['fit_coupon','motor_envelope','printed_cover']:continue
 if p['frame'].startswith('J7') and not p['id'].startswith('J7-armour-'):continue
 if p['id']=='P06-yaw-to-roll':continue
 others.append((p,load(paths['arm'],p['id'])))
for p in D['wrist']['parts']:others.append((p,load(paths['wrist'],p['id'])))
for j in L['joints']:
 for tag,fr in [('stator','fixed'),('external-output','rotor')]:
  f=ROOT/'work/arm-a10/vendor'/(j['id']+'-'+tag+'.step');source_hashes[str(f.relative_to(ROOT))]=sha(f)
  if j['id']=='J7':continue # J7 new-vs-actual motor was independently checked in IF02.
  others.append((dict(id=j['id']+'-supplier-'+tag,frame=j['id']+'.'+fr),cq.importers.importStep(str(f)).val()))
new=[]
for n,ids in [('core',['A13-J7-101-bearing-housing','A13-J7-102-bearing-retainer','A13-J7-103-output-journal','A13-J7-104-inner-spacer','A13-J7-105-carrier']),('if01',['A13-IF-107-piloted-flange'])]:
 for id in ids:
  p=next(p for p in D[n]['parts'] if p['id']==id)
  if id=='A13-J7-105-carrier' and '--baseline' not in sys.argv:
   f=OUT/'carrier-manifest.json';p=json.loads(f.read_text());source_hashes[str(f.relative_to(ROOT))]=sha(f);new.append((p,load(OUT,p['id'])))
  else:new.append((p,load(paths[n],id)))
for p in D['if02']['parts']:
 if p['role']!='fit_coupon':new.append((p,load(paths['if02'],p['id'])))
# Nominal IF02 hardware contributes only its new cross-interface checks; inherited threads remain FIT01 scope.
# Local IF02 audit already binds hardware vs module. Cross-upstream hardware screen uses conservative bounding boxes,
# retained as a separate false-positive-capable screen, never as exact bolt collision proof.
hwboxes=[]
for p in D['if02']['hardware']:
 v=np.asarray(p['vertices_mm']);lo=v.min(axis=0);hi=v.max(axis=0);sz=hi-lo
 sh=cq.Solid.makeBox(*map(float,sz),cq.Vector(*map(float,lo)));hwboxes.append((dict(p,id=p['id']+'-bbox'),sh))
basecases=json.loads((paths['wrist']/'fit-audit.json').read_text())['checks'];cases={n:c['q_deg'] for n,c in basecases.items()}
for j6 in [-60,-40,-20,0,20,40,60]:
 for j7 in [-90,-60,-30,0,30,60,90]:
  q=list(L['poses']['attention']);q[5:]=[j6,j7];cases[f'grid_J6_{j6}_J7_{j7}']=q
cache={};checks={};hwchecks={}
for name,q in cases.items():
 start=time.time();F,_=co.ld.fk(q);targets=co.placed(others,q);hits=[];tested=0;reused=0;clear=0
 for p,s,bb,pos,R in co.placed(new,q):
  for a,t,cb,ap,AR in targets:
   if disjoint(bb,cb):clear+=1;continue
   relative=np.linalg.inv(np.block([[R,pos[:,None]],[np.zeros((1,3)),np.ones((1,1))]]))@np.block([[AR,ap[:,None]],[np.zeros((1,3)),np.ones((1,1))]])
   key=(p['id'],a['id'],tuple(np.round(relative.ravel(),7)))
   if key in cache:v,method=cache[key];reused+=1
   else:v,method=ov(s,t);cache[key]=(v,method);tested+=1
   if v>.05:hits.append(dict(a=p['id'],b=a['id'],volume_mm3=v,method=method))
 # Hardware box screen is scoped separately and never causes geometry cuts without real-solid confirmation.
 hwhits=[]
 for p,s,bb,pos,R in co.placed(hwboxes,q):
  for a,t,cb,_,_ in targets:
   if disjoint(bb,cb):continue
   v,method=ov(s,t)
   if v>.05:hwhits.append(dict(a=p['id'],b=a['id'],box_overlap_mm3=v,exact_hardware_confirmation=False))
 checks[name]=dict(q_deg=q,overlaps=hits,exact_new_checks=tested,reused_relative_transform_pairs=reused,disjoint_bbox_pairs=clear)
 hwchecks[name]=hwhits
 print('INTEGRATION',name,len(hits),'hits',len(hwhits),'hardware-box flags',round(time.time()-start,1),'s',flush=True)
 for h in hits:print('HIT',h,flush=True)
# Rejected direct side chord: nominal fixed/rotating anchors chosen only for geometric diagnosis.
fixed=np.array([-18.,-40.,0.]);moving=np.array([77.5,-36.,0.]);chords=[]
obstacles=[(p,s) for p,s in new if p['frame']=='J7.fixed']
f=ROOT/'work/arm-a10/vendor/J7-stator.step';obstacles.append((dict(id='actual-J7-stator'),cq.importers.importStep(str(f)).val()))
for angle in [-90,-60,-30,0,30,60,90]:
 end=co.ld.rotation([1,0,0],angle)@moving;delta=end-fixed;length=np.linalg.norm(delta)
 probe=co.c.legacy.cyl(fixed,delta/length,1.55,length);hits=[]
 for p,s in obstacles:
  v,method=ov(probe,s)
  if v>.05:hits.append(dict(obstacle=p['id'],volume_mm3=v))
 chords.append(dict(J7_deg=angle,start_fixed_mm=fixed.tolist(),end_rotor_mm=end.tolist(),length_mm=float(length),obstacle_hits=hits,
  geometric_chord_only=True,physical_constant_length_route=False))
# Changes in payload gravity moment due ONLY to moved flange origin, same 3 kg lumped point load.
loads={}
for name in ['reference','attention','idle']:
 q=cases[name];F,joints=co.ld.fk(q);p,R=F['J7.rotor'];p_old=(p+R@np.array([65.7,0,0]))/1000;p_new=(p+R@np.array([110,0,0]))/1000;force=np.array([0,0,-3*9.80665])
 old=[float(np.dot(axis,np.cross(p_old-origin,force))) for origin,axis in joints];updated=[float(np.dot(axis,np.cross(p_new-origin,force))) for origin,axis in joints]
 loads[name]=dict(q_deg=q,old_flange_world_mm=(p_old*1000).tolist(),new_flange_world_mm=(p_new*1000).tolist(),old_payload_gravity_Nm=old,new_payload_gravity_Nm=updated,delta_payload_gravity_Nm=(np.array(updated)-old).tolist())
report=dict(revision='WRIST-ROUTE01',source_hashes=source_hashes,new_module_parts=len(new),target_parts=len(others),checks=checks,hardware_box_screen=hwchecks,
 all_sampled_owned_geometry_clear=all(not e['overlaps'] for e in checks.values()),hardware_box_screen_clear=all(not e for e in hwchecks.values()),direct_chord_probes=chords,
 payload_shift_only=loads,nominal_tool_plane_J7_mm=[110,0,0],old_tool_plane_J7_mm=[65.7,0,0],
 scope='Integrated owned J7 core and IF02 vs retained upstream BREP and six wrist shields; discrete samples. Hardware additions: conservative box screen only.',
 limitations=['No full arm qualification, continuous sweep or physical print trial','No assembled electrical/dynamic harness route','CG03 500 mm pure twist length is a necessary screen for chosen independent anchors, not a universal minimum','Payload shift excludes all added structure/connector masses, inertia, friction and thermal capacity'])
(OUT/('integration-before.json' if '--baseline' in sys.argv else 'integration-review.json')).write_text(json.dumps(report,indent=2)+'\n')
(OUT/'integration-parts.json').write_text(json.dumps(dict(layout=L,new_parts=[p for p,s in new],hardware=D['if02']['hardware'],allocations=D['if02']['allocations'],source_hashes=source_hashes),separators=(',',':'))+'\n')
print('INTEGRATION_DONE',len(cases),report['all_sampled_owned_geometry_clear'],flush=True)
