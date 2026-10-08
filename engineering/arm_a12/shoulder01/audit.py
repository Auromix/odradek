# SPDX-License-Identifier: CC-BY-NC-4.0
"""New A12 covers vs unchanged A11 hardware and exact local supplier solids.
Only reports new-component checks: never inherits a whole-arm pass.
"""
from pathlib import Path
import json,hashlib,sys,math
import cadquery as cq,numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'engineering/arm_a11'))
import collision as old
OUT=Path(__file__).parent/'build'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 d=json.loads((OUT/'manifest.json').read_text());baseline,parts=old.items(True,True)
 assert baseline['_audit_sha256']==d['baseline_manifest_sha256']
 assert all(sha(ROOT/'work/arm-a10/vendor'/n)==s for n,s in d['supplier_partition_sha256'].items())
 parts=[(p,s) for p,s in parts if p['id'] not in d['replaced_parts']]
 new=[]
 for p in d['parts']:
  path=OUT/(p['id']+'.step');assert sha(path)==p['step_sha256']
  new.append((p,cq.importers.importStep(str(path)).val()))
 cases=dict(baseline['layout']['poses'])
 for value in [-60,0,45,110]:
  q=baseline['layout']['poses']['attention'].copy();q[1]=value;cases['J2_'+str(value)]=q
 checks={}
 for name,q in cases.items():
  world=old.placed(parts,q);moving=old.placed(new,q);hits=[];count=0
  for i,(p,s,bb,_,_) in enumerate(moving):
   for a,t,cb,_,_ in world+moving[i+1:]:
    if any(getattr(bb,k+'max')<=getattr(cb,k+'min')+1e-5 or getattr(cb,k+'max')<=getattr(bb,k+'min')+1e-5 for k in ['x','y','z']):continue
    count+=1;v=old.volume(old.common_solids(s,t))
    if v>.05:hits.append(dict(cover=p['id'],other=a['id'],volume_mm3=v))
  checks[name]=dict(q_deg=q,narrow_phase_checks=count,overlaps=hits)
  print(name,'new_component_overlaps',len(hits),flush=True)
 # Separate reservation: sampled D10 spheres along the static U arc.
 # This is not a continuous-tube bound or a moving-harness/lifetime proof.
 routes=d['wire_reservation']['centreline_mm'];r=d['wire_reservation']['reservation_diameter_mm']/2
 bundle=None
 for point in routes:
  s=cq.Solid.makeSphere(r,old.c.legacy.V(point),angleDegrees1=-90,angleDegrees2=90)
  bundle=s if bundle is None else bundle.fuse(s).fix()
 local=[(p,s) for p,s in new]
 for kind in ['stator','external-output']:
  # The output partition has the same J2 local translation; q affects its rotation,
  # but these points lie behind the stationary casing. This is static reference only.
  local.append((dict(id='J2-'+kind),cq.importers.importStep(str(ROOT/'work/arm-a10/vendor'/('J2-'+kind+'.step'))).val()))
 wire=[]
 for p,s in local:
  v=old.volume(old.common_solids(bundle,s));wire.append(dict(other=p['id'],intersection_mm3=v))
 report=dict(manifest_sha256=sha(OUT/'manifest.json'),baseline_manifest_sha256=baseline['_audit_sha256'],scope='New J2 shields against existing exact geometry at seven discrete poses. Not full-arm/domain clearance.',checks=checks,wire_reservation=dict(status='stationary unconnected D10 U-space only',intersection_checks=wire,sampled_sphere_spacing_mm=float(np.linalg.norm(np.array(routes[1])-routes[0])),bend_radius_target_mm=36,cable_selected=False,endpoints_connected=False),limitations=d['limitations'])
 (OUT/'fit-audit.json').write_text(json.dumps(report,indent=2)+'\n')
 assert all(not x['overlaps'] for x in checks.values()),'New shield interference; see report'
 assert all(x['intersection_mm3']<=.05 for x in wire),'Reserved wire space is obstructed'
 print('A12_NEW_GEOMETRY_CHECKS_PASS',flush=True)
if __name__=='__main__':main()
