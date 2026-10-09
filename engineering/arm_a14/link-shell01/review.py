# SPDX-License-Identifier: CC-BY-NC-4.0
"""New link covers vs retained actual motors, structure and hardware; sampled only."""
from pathlib import Path
import sys,json,hashlib,math,time
import numpy as np,cadquery as cq
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=HERE/'build'
sys.path.insert(0,str(ROOT/'engineering/arm_a11'));import collision as co
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
D=json.loads((OUT/'parts.json').read_text());base=ROOT/'engineering/arm_a11/build';A=json.loads((base/'manifest.json').read_text())
co.ld.LAYOUT=D['layout'];co.ld.TARGET['flange_frame']['translation_mm']=[110,0,0]
sources={str((OUT/'parts.json').relative_to(ROOT)):sha(OUT/'parts.json')};new=[];others=[]
def load(p,id):
 f=p/'step'/(id+'.step')
 if not f.exists():f=p/(id+'.step')
 sources[str(f.relative_to(ROOT))]=sha(f);return cq.importers.importStep(str(f)).val()
for p in D['parts']:new.append((p,load(OUT,p['id'])))
for p in A['parts']:
 if p['role'] in ['fit_coupon','motor_envelope','printed_cover']:continue
 if p['id'] in ['P06-yaw-to-roll','B7-output-flange','J7-bearing-cage','J7-bearing-retainer','J7-inner-spacer','J7-inner-centre-spacer'] or p['id'].startswith('J7-tool-M4-nut-'):continue
 others.append((p,load(base,p['id'])))
for j in D['layout']['joints']:
 for tag,fr in [('stator','fixed'),('external-output','rotor')]:
  f=ROOT/'work/arm-a10/vendor'/(j['id']+'-'+tag+'.step');sources[str(f.relative_to(ROOT))]=sha(f)
  others.append((dict(id=j['id']+'-supplier-'+tag,frame=j['id']+'.'+fr),cq.importers.importStep(str(f)).val()))
# Include current J2 and all wrist CAD shields; other style-only surfaces are
# explicitly outside this BREP scope, never called manufacturing parts.
for module in ['shoulder01','wrist02']:
 folder=ROOT/'engineering/arm_a12'/module/'build';M=json.loads((folder/'manifest.json').read_text())
 for p in M['parts']:others.append((p,load(folder,p['id'])))
F=ROOT/'engineering/arm_a13/wrist-route01/build';W=json.loads((F/'integration-parts.json').read_text())
for p in W['new_parts']:others.append((p,load(F,p['id'])))
for p in W['hardware']:
 # Every nominal hardware mesh has its exact BREP in the upstream module,
 # IF02 hardware has no saved STEP; it stays an explicit separate gap here.
 pass
poses={n:list(q) for n,q in D['layout']['poses'].items()}
for k,angles in [(2,[-45,0,45,90,110]),(3,[-120,-60,60,120]),(4,[-145,-100,-45,0,60,120,135]),(5,[-90,0,60,130])]:
 for a in angles:
  q=list(D['layout']['poses']['attention']);q[k-1]=a;poses[f'J{k}_{a}']=q
poses['coupled']=[15,45,50,-100,70,35,-45]
path_names=[]
for a,b in [('idle','attention'),('attention','reference')]:
 for i in range(1,17):
  name=f'path_{a}_{b}_{i:02d}';poses[name]=((1-i/17)*np.array(D['layout']['poses'][a])+i/17*np.array(D['layout']['poses'][b])).tolist();path_names.append(name)
cache={};report={}
for name,q in poses.items():
 t0=time.time();targets=co.placed(others,q);owned=co.placed(new,q);hits=[];calls=0
 # Same-rigid geometry can be reused without treating collisions as exempt.
 for p,s,bb,pos,R in owned:
  for a,t,cb,ap,AR in targets:
   if any(getattr(bb,k+'max')<=getattr(cb,k+'min')+1e-6 or getattr(cb,k+'max')<=getattr(bb,k+'min')+1e-6 for k in ['x','y','z']):continue
   key=(p['id'],a['id'],tuple(np.round(np.r_[R.T@(ap-pos),(R.T@AR).ravel()],7)))
   if key not in cache:
    op=BRepAlgoAPI_Common(s.wrapped,t.wrapped)
    assert op.IsDone()
    z=cq.Shape.cast(op.Shape());assert z.isValid()
    cache[key]=sum(x.Volume() for x in z.Solids());calls+=1
   v=cache[key]
   if v>.05:hits.append(dict(cover=p['id'],obstacle=a['id'],volume_mm3=v))
 for i,(p,s,bb,_,_) in enumerate(owned):
  for a,t,cb,_,_ in owned[i+1:]:
   if any(getattr(bb,k+'max')<=getattr(cb,k+'min')+1e-6 or getattr(cb,k+'max')<=getattr(bb,k+'min')+1e-6 for k in ['x','y','z']):continue
   op=BRepAlgoAPI_Common(s.wrapped,t.wrapped);assert op.IsDone();z=cq.Shape.cast(op.Shape());assert z.isValid();v=sum(x.Volume() for x in z.Solids())
   if v>.05:hits.append(dict(cover=p['id'],obstacle=a['id'],volume_mm3=v))
 report[name]=dict(q_deg=q,hits=hits,new_exact_pairs=calls)
 print('POSE',name,len(hits),round(time.time()-t0,1),flush=True)
 for h in hits:print('HIT',h,flush=True)
out=dict(revision=D['revision'],source_hashes=sources,cover_count=4,obstacle_count=len(others),checks=report,
 named_pose_cover_checks_clear=all(not report[n]['hits'] for n in ['idle','attention','reference']),
 interpolation_cover_checks_clear=all(not report[n]['hits'] for n in path_names),path_sample_names=path_names,
 sampled_geometry_clear=all(not x['hits'] for x in report.values()),production_release=False,
 scope='New detachable link skins vs retained nominal actual motors, structure, old CAD hardware, current J2/wrist CAD covers and J7 core. Plus cover-to-cover. No intentional overlap suppressed.',
 limitations=['Discrete joint-domain samples, not continuous or collision-qualified paths.',
 'Other Blender-only style shells, canonical base/desk, IF02 new hardware, connected harness, manufacturing deviations and tool access volumes are not in this BREP scope.',
 'The current motor configuration is not load-qualified by A14-QUAL01. No material/printer/slicer or operating-load release.'])
(OUT/'geometry-review.json').write_text(json.dumps(out,indent=2)+'\n')
print('REVIEW_COMPLETE',out['sampled_geometry_clear'],len(report),flush=True)
