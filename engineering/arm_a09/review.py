# SPDX-License-Identifier: CC-BY-NC-4.0
"""A09 proposal screening. No implied assembly or load release."""
from pathlib import Path
import json,sys,hashlib
import numpy as np
import cadquery as cq
from OCP.gp import gp_Trsf
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'engineering/arm_a07'));import loads as ld
FIELDS=['id','frame','owner','mass_kg','com_mm','inertia_kg_mm2','role']
def review(variant):
 out=ROOT/'engineering/arm_a09/build'/variant;d=json.loads((out/'manifest.json').read_text());ld.LAYOUT=d['layout'];ld.TARGET['flange_frame']['translation_mm']=d['flange_from_J7_mm']
 bodies=[{k:p[k] for k in FIELDS} for p in d['parts'] if p['role']!='motor_envelope']
 # Reserve unmodelled fasteners, tube crush sleeves, liner and harness, not zero mass.
 for owner in range(2,8):bodies.append(dict(id=f'assembly_budget_B{owner}',frame=f'J{owner}.rotor',owner=owner,mass_kg=.10,com_mm=[0,0,0],inertia_kg_mm2=np.zeros((3,3)).tolist(),role='hardware_budget'))
 ld.structure_entries=lambda:bodies
 presets={name:ld.evaluate(q) for name,q in d['layout']['poses'].items()}
 maxima=[0.]*7
 for k in range(1,513):
  def halton(n,b):
   v=0;f=1
   while n:f/=b;v+=f*(n%b);n//=b
   return v
  q=[j['limits_deg'][0]+halton(k,b)*(j['limits_deg'][1]-j['limits_deg'][0]) for j,b in zip(d['layout']['joints'],[2,3,5,7,11,13,17])]
  for i,a in enumerate(ld.evaluate(q)['axes']):maxima[i]=max(maxima[i],a['abs_holding_Nm'])
 solids=[];brep=[]
 for p in d['parts']:
  s=cq.importers.importStep(str(out/'step'/f'{p["id"]}.step')).val();brep.append(dict(id=p['id'],valid=s.isValid(),solids=len(s.Solids())))
  solids.append((p,s))
 conflicts={}
 for name,q in d['layout']['poses'].items():
  f,_=ld.fk(q);placed=[]
  for p,s in solids:
   pos,r=f[p['frame']];t=np.column_stack((r,pos));tr=gp_Trsf();tr.SetValues(*map(float,t.flatten()));s=s.transformShape(cq.Matrix(tr));placed.append((p,s,s.BoundingBox()))
  cs=[]
  for i,(p,s,b) in enumerate(placed):
   for a,t,c in placed[i+1:]:
    if any(getattr(b,k+'max')<=getattr(c,k+'min')+1e-5 or getattr(c,k+'max')<=getattr(b,k+'min')+1e-5 for k in ['x','y','z']):continue
    v=s.intersect(t).Volume()
    if v>.05:cs.append(dict(a=p['id'],b=a['id'],volume_mm3=v,owners=[p['owner'],a['owner']]))
  conflicts[name]=cs
 errors=[]
 for q in list(d['layout']['poses'].values())+[[23,55,35,-85,68,24,42]]:
  result=ld.evaluate(q,3,[50,25,10]);h=1e-4
  for i,axis in enumerate(result['axes']):
   plus=q.copy();minus=q.copy();plus[i]+=h;minus[i]-=h
   derivative=(ld.potential(plus,3,[50,25,10])-ld.potential(minus,3,[50,25,10]))/(2*np.radians(h));errors.append(abs(derivative-axis['holding_Nm']))
 assert max(errors)<1e-6
 data=dict(verification={'recursive_direct_agree':True,'max_virtual_work_error_Nm':max(errors)},variant=variant,status='proposal_screening_not_assembly_release',source_sha256=hashlib.sha256((out/'manifest.json').read_bytes()).hexdigest(),presets=presets,sampled_static_max_Nm=maxima,sampling='512 unfiltered Halton samples, not collision-qualified maxima',reserve_mass_kg=.6,reserve_note='0.1kg each B2-B7 for missing fasteners, fixtures and harness; not a completed BOM',brep=brep,pose_overlaps=conflicts,limits=['End-seat fasteners and cable ports not complete.','No thermal or output bearing qualification.','All overlap pairs retained; proposal must not be described as collision-free.'])
 (out/'screening.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 print(variant,'reference holding',[round(a['abs_holding_Nm'],2) for a in presets['reference']['axes']], 'mass',presets['reference']['total_mass_kg']-3,'overlaps',{k:len(v) for k,v in conflicts.items()},flush=True)
if __name__=='__main__':review(sys.argv[1] if len(sys.argv)>1 else 'slim')
