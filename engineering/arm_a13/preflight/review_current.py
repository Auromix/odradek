# SPDX-License-Identifier: CC-BY-NC-4.0
"""Read-only A12 mass/load review before manufacturing redesign.

No geometry, motor selection, actuator rating or manufacturing release changes.
Mesh volume/density and conservative dynamic bounds are estimates, not tests.
"""
from pathlib import Path
import sys,json,hashlib,csv
import numpy as np,trimesh
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent/'build'
sys.path.insert(0,str(ROOT/'engineering/arm_a07'));import loads as ld
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 paths={
  'baseline':'engineering/arm_a11/build/manifest.json',
  'baseline_review':'engineering/arm_a11/build/feasibility.json',
  'style':'engineering/arm_a12/wrist02/build/style-surfaces.json',
  'shoulder':'engineering/arm_a12/shoulder01/build/manifest.json',
  'wrist':'engineering/arm_a12/wrist02/build/manifest.json',
  'native_audit':'engineering/arm_a12/wrist02/build/audit.json',
  'base_context':'engineering/arm_a12/wrist02/build/base-context.json',
  'actual_native':'work/arm-a12/wrist02/actual-motors.blend',
  'calculation_source':'engineering/arm_a07/loads.py'}
 sources={k:dict(path=p,sha256=sha(ROOT/p)) for k,p in paths.items()}
 data={k:json.loads((ROOT/p).read_text()) for k,p in paths.items() if p.endswith('.json')}
 base=data['baseline'];style=data['style'];shoulder=data['shoulder'];audit=data['native_audit']
 assert audit['actual_native_sha256']==sources['actual_native']['sha256']
 assert style['baseline_manifest_sha256']==sources['baseline']['sha256']
 assert data['baseline_review']['manifest_sha256']==sources['baseline']['sha256']
 ld.LAYOUT=base['layout'];ld.TARGET['flange_frame']['translation_mm']=base['flange_from_J7_mm']
 fields=['id','frame','owner','mass_kg','com_mm','inertia_kg_mm2','role']
 baseline_bodies=[{k:p[k] for k in fields} for p in base['parts'] if p['role'] not in ['fit_coupon','motor_envelope']]
 remaining=[p for p in baseline_bodies if p['role']!='printed_cover']
 covers=[]
 for p in style['style_surfaces']+shoulder['parts']:
  mesh=trimesh.Trimesh(p['vertices_mm'],p['triangles'],process=False)
  assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
  frame=p['frame'];owner=0 if frame=='world' else int(frame[1])-(frame.endswith('.fixed'))
  covers.append(dict(id=p['id'],frame=frame,owner=owner,mass_kg=float(mesh.volume)*1.27e-6,com_mm=mesh.center_mass.tolist(),inertia_kg_mm2=(mesh.moment_inertia*1.27e-6).tolist(),role='cosmetic_mesh_solid_mass_estimate'))
 assert len(covers)==22 and len({p['id'] for p in covers})==22
 harness=[dict(id=f'pending_harness_B{j}',frame=f'J{j}.rotor',owner=j,mass_kg=.04,com_mm=[0,0,0],inertia_kg_mm2=np.zeros((3,3)).tolist(),role='harness_budget') for j in range(2,8)]
 ledgers={'A11_existing':baseline_bodies+harness,'A12_existing':remaining+covers+harness,'A12_without_cosmetic_covers_diagnostic':remaining+harness}
 cases={};rows=[]
 for name,bodies in ledgers.items():
  ld.structure_entries=lambda:bodies
  named={pose:ld.evaluate(q,3) for pose,q in base['layout']['poses'].items()}
  reference=named['reference'];dynamic=ld.dynamic_screen(base['layout']['poses']['reference'])
  cases[name]=dict(named_static=named,reference_dynamic_bound=dynamic)
  rows.append(dict(case=name,bare_arm_mass_kg=ld.evaluate(base['layout']['poses']['reference'],0)['total_mass_kg'],static_J2_Nm=reference['axes'][1]['abs_holding_Nm'],dynamic_J2_bound_Nm=dynamic['additional_torque_bound_Nm'][1],sum_J2_screen_Nm=reference['axes'][1]['abs_holding_Nm']+dynamic['additional_torque_bound_Nm'][1]))
 assert abs(rows[0]['static_J2_Nm']-data['baseline_review']['cases']['3']['reference']['axes'][1]['abs_holding_Nm'])<1e-9
 bodies=ledgers['A12_existing'];ld.structure_entries=lambda:bodies
 errors=[]
 for q in list(base['layout']['poses'].values())+[[23,55,35,-85,68,24,42]]:
  result=ld.evaluate(q,3,[50,25,10]);h=1e-4
  for idx,axis in enumerate(result['axes']):
   plus=list(q);minus=list(q);plus[idx]+=h;minus[idx]-=h
   derivative=(ld.potential(plus,3,[50,25,10])-ld.potential(minus,3,[50,25,10]))/(2*np.radians(h))
   errors.append(abs(derivative-axis['holding_Nm']))
 assert max(errors)<1e-6
 def halton(n,b):
  v=0;f=1
  while n:f/=b;v+=f*(n%b);n//=b
  return v
 maxima=[dict(abs_holding_Nm=-1) for _ in range(7)]
 for k in range(1,257):
  q=[j['limits_deg'][0]+halton(k,b)*(j['limits_deg'][1]-j['limits_deg'][0]) for j,b in zip(base['layout']['joints'],[2,3,5,7,11,13,17])]
  for i,axis in enumerate(ld.evaluate(q,3)['axes']):
   if axis['abs_holding_Nm']>maxima[i]['abs_holding_Nm']:maxima[i]=dict(**axis,q_deg=q)
 for entry in cases['A12_existing']['named_static'].values():
  for i,axis in enumerate(entry['axes']):
   if axis['abs_holding_Nm']>maxima[i]['abs_holding_Nm']:maxima[i]=dict(**axis,q_deg=entry['q_deg'])
 com_cases=[dict(com_mm=list(com),reference=ld.evaluate(base['layout']['poses']['reference'],3,com)) for com in [(0,0,0),(50,0,0),(100,0,0),(50,25,10)]]
 report=dict(status='manufacturing_redesign_preflight_only',sources=sources,rows=rows,cases=cases,mesh_cover_ledger=covers,cover_mass_estimate_kg=sum(p['mass_kg'] for p in covers),motor_mass_kg=sum(j['mass_kg'] for j in base['layout']['joints']),sampled_static_maxima=maxima,COM_demand_cases=com_cases,verification=dict(A11_reference_reproduced=True,max_virtual_work_error_Nm=max(errors)),thermal_reference=dict(source_url='https://github.com/RobStride/Product_Information#产品选型--product-selection',source_version='Manufacturer README citing 2026-07-13 specification; not a delivered-unit thermal qualification',RS04_Nm35_heatsink_mm=[220,200],RS04_Nm40_heatsink_mm=[345,345],enclosed_zero_speed_capacity_verified=False),limitations=['22 cover volumes are summed individually at assumed PETG 1.27g/cm3; surfaces are not released parts and may overlap. No sliced or measured masses.','Baseline nominal hardware retained, including provisional cosmetic fasteners; final hardware and liners may change.','0.24kg harness budget is not a connected harness or selected BOM.','256 Halton samples plus named poses are unfiltered by collision; neither global maxima nor usable workspace.','Dynamic screening is a conservative bound with envelope rotor inertia and 25deg/s,30deg/s2 assumptions. It is not actual duty-cycle RMS or continuous holding capacity.','Case without cosmetic covers is a diagnostic, not a proposed manufactured robot.','Thermal, bearing, metal-section strength, braking, connectors and actual assembly unresolved.','No new motor or structural geometry is frozen; no manufacturing/load release.'])
 OUT.mkdir(exist_ok=True);(OUT/'current-load-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 with (OUT/'current-load-comparison.csv').open('w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
 print(json.dumps(dict(rows=rows,cover_mass_estimate_kg=report['cover_mass_estimate_kg'],sampled_static_maxima=[(p['joint'],p['abs_holding_Nm']) for p in maxima],max_virtual_work_error_Nm=max(errors)),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
