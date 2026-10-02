# SPDX-License-Identifier: CC-BY-NC-4.0
"""Discrete, exact CAD per-joint sweeps; not continuous collision qualification."""
from pathlib import Path
import json,sys,hashlib
import numpy as np
import cadquery as cq
from OCP.gp import gp_Trsf
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'engineering/arm_a07'));import loads as ld
def run(variant='slim'):
 out=ROOT/'engineering/arm_a09/build'/variant;path=out/'manifest.json';d=json.loads(path.read_text());ld.LAYOUT=d['layout'];parts=[]
 for p in d['parts']:
  parts.append((p,cq.importers.importStep(str(out/'step'/f'{p["id"]}.step')).val()))
 results=[]
 for axis,angles in [(0,list(range(-120,121,10))),(1,list(range(-70,111,10))),(2,list(range(-100,101,10))),(3,list(range(-155,136,10))),(4,list(range(-90,131,10))),(5,list(range(-60,61,10))),(6,list(range(-90,91,10)))]:
  for angle in angles:
   q=list(d['layout']['poses']['reference']);q[axis]=angle;f,_=ld.fk(q);placed=[]
   for p,s in parts:
    pos,r=f[p['frame']];t=gp_Trsf();t.SetValues(*map(float,np.column_stack((r,pos)).flatten()));w=s.transformShape(cq.Matrix(t));placed.append((p,w,w.BoundingBox()))
   overlaps=[]
   for i,(p,s,b) in enumerate(placed):
    for a,t,c in placed[i+1:]:
     if any(getattr(b,k+'max')<=getattr(c,k+'min')+1e-5 or getattr(c,k+'max')<=getattr(b,k+'min')+1e-5 for k in ['x','y','z']):continue
     v=s.intersect(t).Volume()
     if v>.05:overlaps.append(dict(a=p['id'],b=a['id'],intersection_mm3=v))
   results.append(dict(joint='J'+str(axis+1),angle_deg=angle,overlaps=overlaps))
 report=dict(manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),variant=variant,scope='All41 arm solids, excluding base context; J1-J7 one at a time in reference pose',step_deg=10,checks=results,status='discrete_local_geometry_only',limits=['No simultaneous-axis combinations or continuous sweep.','No cable/bolt/tool or table clearance qualification.'])
 (out/'local-wrist-sweep.json').write_text(json.dumps(report,indent=2)+'\n');print('SWEEP',variant,len(results),sum(bool(r['overlaps']) for r in results),'conflicting samples',flush=True)
if __name__=='__main__':run(sys.argv[1] if len(sys.argv)>1 else 'slim')
