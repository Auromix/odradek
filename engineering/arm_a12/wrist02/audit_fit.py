# SPDX-License-Identifier: CC-BY-NC-4.0
"""New wrist BREP vs unchanged actual motors/structure/hardware; discrete poses."""
from pathlib import Path
import sys,json,hashlib,time
import cadquery as cq
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent/'build'
sys.path.insert(0,str(ROOT/'engineering/arm_a11'));import collision as old
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def rigid(frame):
 if frame=='world':return 0
 return int(frame[1])-(frame.endswith('.fixed'))
def main():
 d=json.loads((OUT/'manifest.json').read_text());baseline,parts=old.items(True,True);assert baseline['_audit_sha256']==d['baseline_manifest_sha256']
 for name,h in d['supplier_partition_sha256'].items():assert sha(ROOT/'work/arm-a10/vendor'/name)==h
 # Existing decorative covers are replaced/pending in A12, not relevant A11 neighbours.
 parts=[(p,s) for p,s in parts if p['role']!='printed_cover']
 shoulder=ROOT/'engineering/arm_a12/shoulder01/build';sd=json.loads((shoulder/'manifest.json').read_text())
 parts.extend((p,cq.importers.importStep(str(shoulder/(p['id']+'.step'))).val()) for p in sd['parts'])
 new=[]
 for p in d['parts']:
  path=OUT/'step'/(p['id']+'.step');assert sha(path)==p['step_sha256'];new.append((p,cq.importers.importStep(str(path)).val()))
 cases=dict(baseline['layout']['poses'])
 for j,values in [(5,[-90,0,130]),(6,[-60,60]),(7,[-90,90])]:
  for a in values:
   q=list(cases['attention']);q[j-1]=a;cases[f'J{j}_{a}']=q
 # Intermediate/coupled samples also informed explicit local recess refinement;
 # they are regression checks, not an independent held-out validation set.
 for joint,values in [(5,[-60,-30,30,60,90,110]),(6,[-40,-20,20,40]),(7,[-45,45])]:
  for angle in values:
   q=list(cases['attention']);q[joint-1]=angle;cases[f'intermediate_J{joint}_{angle}']=q
 for name,q in [('coupled_low',[0,75,0,-65,-30,-30,45]),('coupled_high',[0,75,0,-65,90,30,-45])]:cases[name]=q
 cache={};checks={}
 for name,q in cases.items():
  start=time.time();others=old.placed(parts,q);moving=old.placed(new,q);hits=[];tested=0;reused=0
  for i,(p,s,bb,_,_) in enumerate(moving):
   for a,t,cb,_,_ in others+moving[i+1:]:
    key=tuple(sorted((p['id'],a['id'])));fixed=rigid(p['frame'])==rigid(a['frame'])
    if fixed and key in cache:
     reused+=1
     if cache[key]:hits.append(cache[key])
     continue
    if any(getattr(bb,k+'max')<=getattr(cb,k+'min')+1e-5 or getattr(cb,k+'max')<=getattr(bb,k+'min')+1e-5 for k in ['x','y','z']):continue
    tested+=1;v=old.volume(old.common_solids(s,t));hit=dict(cover=p['id'],other=a['id'],volume_mm3=v) if v>.05 else None
    if fixed:cache[key]=hit
    if hit:hits.append(hit)
  checks[name]=dict(q_deg=q,overlaps=hits,narrow_phase_checks=tested,reused_identical_rigid_pairs=reused)
  print('FIT',name,len(hits),'overlaps',round(time.time()-start,1),'s',flush=True)
  for hit in hits:print('HIT',hit,flush=True)
 report=dict(manifest_sha256=sha(OUT/'manifest.json'),baseline_manifest_sha256=baseline['_audit_sha256'],scope='Six new wrist shields vs A11 exact supplier motors/structures/nominal hardware and prior J2 shields at 24 discrete poses (10 initial design samples plus 14 intermediate/coupled refinement and regression samples). Other A12 style meshes, base, cables and continuous paths excluded.',checks=checks,new_parts=6,all_sampled_checks_passed=all(not v['overlaps'] for v in checks.values()),tolerance_volume_mm3=.05,limitations=d['limitations'])
 (OUT/'fit-audit.json').write_text(json.dumps(report,indent=2)+'\n');print('FIT_COMPLETE',report['all_sampled_checks_passed'],flush=True)
if __name__=='__main__':main()
