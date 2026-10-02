# SPDX-License-Identifier: CC-BY-NC-4.0
"""Independent STEP and STL checks for printable assembly fit; no load approval."""
from pathlib import Path
import json,sys,hashlib
import cadquery as cq
import numpy as np
import trimesh
from OCP.gp import gp_Trsf
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'engineering/arm_a08/build'
sys.path.insert(0,str(ROOT/'engineering/arm_a07'))
from loads import fk,LAYOUT

def main():
 d=json.loads((OUT/'manifest.json').read_text()); report={'revision':d['revision'],'manifest_sha256':hashlib.sha256((OUT/'manifest.json').read_bytes()).hexdigest(),'parts':[],'poses':{},'limits':['Nominal solid overlap only; no continuous sweep, tool insertion or physical tolerance proof.']}
 parts=[]
 for p in d['parts']:
  s=cq.importers.importStep(str(OUT/'step'/f'{p["id"]}.step')).val()
  row=dict(id=p['id'],valid_brep=s.isValid(),solid_count=len(s.Solids()))
  if p['role'].startswith('printed') or p['role']=='fit_coupon':
   m=trimesh.load_mesh(OUT/'stl'/f'{p["id"]}.stl');row.update(watertight=bool(m.is_watertight),positive_volume=bool(m.volume>0),fits_256mm_bed=bool(max(m.extents)<=256))
   assert row['watertight'] and row['positive_volume'] and row['fits_256mm_bed'],row
  assert row['valid_brep'] and row['solid_count']==1,row
  report['parts'].append(row)
  if p['role']!='fit_coupon':parts.append((p,s))
 for name,q in LAYOUT['poses'].items():
  frames,_=fk(q);placed=[]
  for p,s in parts:
   pos,rot=frames[p['frame']];t=np.eye(4);t[:3,:3]=rot;t[:3,3]=pos
   tr=gp_Trsf();tr.SetValues(*[float(v) for row in t[:3,:] for v in row])
   ss=s.transformShape(cq.Matrix(tr));placed.append((p,ss,ss.BoundingBox()))
  conflicts=[];checked=0
  for i,(p,s,b) in enumerate(placed):
   for z,t,c in placed[i+1:]:
    if p.get('intentional_thread_motor')==z['id'] or z.get('intentional_thread_motor')==p['id']:continue
    if any(getattr(b,a+'max')<=getattr(c,a+'min')+1e-6 or getattr(c,a+'max')<=getattr(b,a+'min')+1e-6 for a in ['x','y','z']):continue
    checked+=1
    try:vol=s.intersect(t).Volume()
    except Exception as e:conflicts.append(dict(a=p['id'],b=z['id'],error=str(e)));continue
    if vol>.01:conflicts.append(dict(a=p['id'],b=z['id'],volume_mm3=vol,owners=[p['owner'],z['owner']]))
  report['poses'][name]=dict(q_deg=q,pair_intersections_tested=checked,conflicts=conflicts)
  print(name,checked,'conflicts',len(conflicts),flush=True)
  for c in conflicts:print(c,flush=True)
 (OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 assert all(not r['conflicts'] for r in report['poses'].values()),'Assembly conflicts remain; see verification.json'
 print('VERIFY_COMPLETE',len(report['parts']),flush=True)

if __name__=='__main__':main()
