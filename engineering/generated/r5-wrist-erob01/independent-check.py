# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
from pathlib import Path
import cadquery as cq,numpy as np,json,math,hashlib
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder
root=Path(__file__).resolve().parent;results={}
for name in ['adapter','mate']:
 s=cq.importers.importStep(str(root/'STEP'/(name+'.step'))).val();cyl=[]
 for f in s.Faces():
  a=BRepAdaptor_Surface(f.wrapped)
  if a.GetType()==GeomAbs_Cylinder:
   c=a.Cylinder();p=c.Location();d=c.Axis().Direction();b=f.BoundingBox()
   if abs(d.Z())>.99999:cyl.append(dict(radius=c.Radius(),xy=[p.X(),p.Y()],z=[b.zmin,b.zmax]))
 want=[(1.7,8),(3.1,8),(2,4)] if name=='adapter' else [(2.25,4)]
 cnt={str(r):len([a for a in cyl if abs(a['radius']-r)<1e-6]) for r,n in want}
 for r,n in want:assert cnt[str(r)]==n,(name,cnt)
 if name=='adapter':
  xy=np.array([a['xy'] for a in cyl if abs(a['radius']-1.7)<1e-6]);assert np.allclose(np.linalg.norm(xy,axis=1),22,atol=1e-6)
  angles=np.degrees(np.arctan2(xy[:,1],xy[:,0]))%360
  for t in [0,30,90,120,180,210,270,300]:assert min(abs((angles-t+180)%360-180))<1e-7
  P=xy-xy.mean(axis=0);S=P.T@P;Fmax=5393.6575*np.max(np.linalg.norm(P@np.linalg.inv(S),axis=1));assert abs(Fmax-61.2915625)<1e-6
 results[name]={'face_cylinder_counts':cnt,'valid':s.isValid(),'solids':len(s.Solids()),'volume_mm3':s.Volume()}
# Independent group equilibrium for a nonspecial 33deg azimuth.
xy=np.array([[22*math.cos(math.radians(t)),22*math.sin(math.radians(t))] for t in [0,30,90,120,180,210,270,300]])
M=np.array([5393.6575*math.cos(math.radians(33)),5393.6575*math.sin(math.radians(33))]);q=np.array([-M[1],M[0]])
f=xy@np.linalg.solve(xy.T@xy,q);recover=np.array([np.sum(xy[:,1]*f),-np.sum(xy[:,0]*f)])
assert np.max(abs(recover-M))<1e-10 and abs(f.sum())<1e-10
results['group_equilibrium']={'test_azimuth_deg':33,'moment_Nmm':M.tolist(),'residual_Nmm':(recover-M).tolist(),'axial_force_sum_N':float(f.sum())}
(root/'independent-check.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
