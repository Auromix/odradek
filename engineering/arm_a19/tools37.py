# SPDX-License-Identifier: CC-BY-NC-4.0
"""109 actual motor fasteners, conventional staged straight hex access."""
from pathlib import Path
import json,sys,math
import numpy as np
import cadquery as cq
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/assembly25'
sys.path.insert(0,str(HERE));import full_review35 as full
w=full.w;c=w.c;g=c.cad;r=w.r

def main():
 path=OUT/'manifest.json';d=json.loads(path.read_text());F=w.f.frames(d['layout'],d['layout']['poses']['reference']);rows=d['parts'];items=[(p,r.load(ROOT/p['step_path']))for p in rows];vendor=json.loads((c.OUT/'vendor-audit.json').read_text());native_sources={}
 for m in vendor['motors']:
  if m['joint']=='J5':
   from vendor import interfaces
   parent=next(x for x in vendor['motors']if x['joint']=='J1');T=np.array(w.interface()['T_joint_from_raw_mm'])@np.linalg.inv(np.array(interfaces()[0]['T_joint_from_raw_mm']))
   for tag,fr in [('stator','fixed'),('external-output','rotor')]:
    p=c.CACHE/'vendor'/('J1-'+tag+'.step');assert c.sha(p)==parent['cache_step_sha256'][tag];items.append((dict(id='J5-supplier-'+tag,frame='J5.'+fr),c.transform(r.load(p),T)));native_sources['J5-'+tag]=dict(source=str(p.relative_to(ROOT)),sha256=c.sha(p),T_from_source=T.tolist())
   continue
  for tag,fr in [('stator','fixed'),('external-output','rotor')]:
   p=c.CACHE/'vendor'/(m['joint']+'-'+tag+'.step');assert c.sha(p)==m['cache_step_sha256'][tag];items.append((dict(id=m['joint']+'-supplier-'+tag,frame=m['joint']+'.'+fr),r.load(p)));native_sources[m['joint']+'-'+tag]=dict(source=str(p.relative_to(ROOT)),sha256=c.sha(p))
 core=json.loads((HERE/'build/wrist-core19/manifest.json').read_text());stacks={p['id']:p for p in core['screw_stacks']};old=json.loads((c.OUT/'hardware01/manifest.json').read_text());bolts={p['id']:p for p in old['bolts']};results=[]
 for row in rows:
  j=row.get('intentional_thread_motor','')
  if not j.startswith('J'):continue
  idx=int(j[1]);fixed=row['frame'].endswith('fixed')
  if row['id'] in stacks:
   s=stacks[row['id']];n=np.array(s['normal']);q=np.array(s['mount_origin_mm']);face=q+n*(s['grip_mm']+s['washer_mm']+4);AF=3;engagement=1.3
  else:
   s=bolts[row['id']];n=np.array(s['n']);q=np.array(s['p_mm']);face=q+n*(s['plate_grip_mm']+s['washer_mm']+s['head_height_mm']);AF=2 if idx==7 and fixed else {3:2.5,4:3,5:4,6:5}[s['diameter_mm']];engagement=min(s['head_height_mm']-.3,AF/2)-.1
  special=set()
  if idx==1 and not fixed:
   special={p['id']for p in rows if p['id']=='A19-S22-shoulder-foot-12mm-R6' or p['id'].startswith('A16-H-shoulder-foot-')}
  if idx==3 and not fixed:
   special={p['id']for p in rows if p['id']=='A16-S105-upper-stock-tube' or p['id'].startswith(('A16-H-tube-3-','A16-C06-upper-saddle-','A16-C06-H-saddle-'))}
  if idx==7 and fixed:
   special={p['id']for p in rows if p['id']in ['A13-J7-102-bearing-retainer','A16-C05-J7-bearing-housing'] or p['id'].startswith(('A16-H-J7-cage-','A16-H-J7-6807-','A16-C05-H-J7-'))}
  if idx==7 and not fixed:
   special={p['id']for p in rows if p['id'].startswith(('A13-IF-301','A13-IF-302','A18-IF09','A16-H-IF-')) and p['id']!='A16-H-IF-core-dowel'}
  origin=face-n*engagement;shape=cq.Workplane(g.plane(origin,n)).polygon(6,(AF-.05)/math.cos(math.pi/6)).extrude(80).val();tool=c.transform(shape,F[row['frame']]);exclusions=[];hits=[]
  for p,local in items:
   future=p['frame'].startswith('J')and int(p['frame'][1])>idx
   downstream=p.get('owner',0)>=(idx if fixed else idx+1) and not p['id'].startswith(j+'-supplier-')
   if p.get('role')=='printed_cover' or future or downstream or p['id']in special:
    exclusions.append(p['id']);continue
   s=c.transform(local,F[p['frame']])
   if r.overlap(tool,s):
    vol=r.common_volume(tool,s)
    if vol>.08:hits.append(dict(target=p['id'],volume_mm3=vol))
  rec=dict(id=row['id'],joint=j,frame=row['frame'],pose=d['layout']['poses']['reference'],stage='fixed bracket/motor before own output coupler' if fixed else 'own output coupler before next motor/subassembly',origin_mm=origin.tolist(),axis=n.tolist(),nominal_AF_mm=AF,probe_AF_mm=AF-.05,engagement_mm=engagement,shaft_length_mm=80,removed_at_stage=exclusions,special_install_later=sorted(special),hits=hits);results.append(rec);print('TOOLS37',row['id'],hits,flush=True)
 report=dict(revision='A19-NATIVE-TOOLS37',source_assembly_sha256=c.sha(path),native_sources=native_sources,source_checker_sha256=c.sha(Path(__file__)),tools=results,nominal_staged_all_clear=not any(p['hits']for p in results),production_release=False,scope='109 nominal native motor screw hex shafts, all covers removed, explicitly listed downstream assembly absent. Straight80mm shaft, no real hand/handle/nut hold/torque/tolerances/base internal. Does not establish total body assembly qualification.')
 assert len(results)==109
 (OUT/'tools37.json').write_text(json.dumps(report,indent=2)+'\n');print('TOOLS37_DONE',len(results),sum(len(p['hits'])for p in results),flush=True)
if __name__=='__main__':main()
