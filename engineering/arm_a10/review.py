# SPDX-License-Identifier: CC-BY-NC-4.0
"""Reverse wrench calculation, dynamic screen and manufacturing consistency checks."""
from pathlib import Path
import sys,json,math,hashlib,numpy as np
import interfaces as c
sys.path.insert(0,str(c.ROOT/'engineering/arm_a07'));import loads as ld

def run():
 path=c.OUT/'manifest.json';d=json.loads(path.read_text());ld.LAYOUT=d['layout'];ld.TARGET['flange_frame']['translation_mm']=d['flange_from_J7_mm']
 fields=['id','frame','owner','mass_kg','com_mm','inertia_kg_mm2','role'];bodies=[{k:p[k] for k in fields} for p in d['parts'] if p['role'] not in ['fit_coupon','motor_envelope']]
 for owner in range(2,8):bodies.append(dict(id=f'pending_harness_B{owner}',frame=f'J{owner}.rotor',owner=owner,mass_kg=.04,com_mm=[0,0,0],inertia_kg_mm2=np.zeros((3,3)).tolist(),role='harness_budget'))
 ld.structure_entries=lambda:bodies
 cases={str(payload):{name:ld.evaluate(q,payload) for name,q in d['layout']['poses'].items()} for payload in [0,.5,3]}
 errs=[]
 for q in list(d['layout']['poses'].values())+[[23,55,35,-85,68,24,42]]:
  result=ld.evaluate(q,3,[50,25,10]);h=1e-4
  for idx,axis in enumerate(result['axes']):
   plus=q.copy();minus=q.copy();plus[idx]+=h;minus[idx]-=h
   value=(ld.potential(plus,3,[50,25,10])-ld.potential(minus,3,[50,25,10]))/(2*np.radians(h));errs.append(abs(value-axis['holding_Nm']))
 assert max(errs)<1e-6
 dynamics={name:ld.dynamic_screen(q) for name,q in d['layout']['poses'].items()}
 # Full nominal screw stack, actual blind-hole maxima (not thread strength approval).
 limits={'RS03':{'fixed':8,'output':6},'RS04':{'fixed':5,'output':6.5},'RS06':{'fixed':8.5,'output':6},'RS00':{'fixed':None,'output':5}}
 screws=[]
 for h in d['hardware']:
  if h['type']!='screw' or not h.get('motor'):continue
  mid=h['motor'];kind='fixed' if '-fixed-' in h['id'] else 'output'
  if mid.startswith('J'):
   j=next(j for j in d['layout']['joints'] if j['id']==mid);depth=limits[j['model']][kind];geometry_depth=5.5 if depth is None else depth;eng=h['engagement_mm'];screws.append(dict(id=h['id'],diameter_mm=h['d'],length_mm=h['length'],grip_mm=h['grip_mm'],washer_mm=h['washer_mm'],engagement_mm=eng,source_min_blind_depth_mm=depth,bottom_clearance_mm=geometry_depth-eng,front_thread_depth_verified=depth is not None,pass_nominal_stack=eng>0 and eng<=geometry_depth-.25,qualification_note='Front M3 usable thread depth must be measured; CAD axial span is not thread specification.' if depth is None else 'Nominal source blind-hole stack, physical measurement required.'))
 assert all(s['pass_nominal_stack'] for s in screws)
 # Elastic tube-only idealization. Does not include sockets/printed joints or fatigue.
 outer=[20,40];inner=[16,36];iy=(20*40**3-16*36**3)/12;iz=(40*20**3-36*16**3)/12
 tubes=[]
 for p in d['parts']:
  if p['role']!='stock_tube':continue
  length=p['tube_drawing']['cut_length_mm'];force=3*9.81;E=69000;I=min(iy,iz)
  tubes.append(dict(id=p['id'],length_mm=length,weak_I_mm4=I,isolated_3kg_tip_sigma_MPa=force*length*10/I,isolated_3kg_tip_deflection_mm=force*length**3/(3*E*I),scope='Tube alone, clamped boundary, nominal3kg point load. Not full-arm stiffness or allowable load.'))
 nominal={j['id']:{'RS03':21,'RS04':35,'RS06':11,'RS00':5}[j['model']] for j in d['layout']['joints']}
 ref=cases['3']['reference']['axes'];dynamic=dynamics['reference']['additional_torque_bound_Nm']
 margin=[dict(joint=a['joint'],hold_Nm=a['abs_holding_Nm'],dynamic_bound_Nm=dynamic[i],catalog_condition_Nm=nominal[a['joint']],sum_demand_Nm=a['abs_holding_Nm']+dynamic[i],catalog_margin_Nm=nominal[a['joint']]-a['abs_holding_Nm']-dynamic[i],status='catalog heat-sink condition only; no enclosed holding qualification') for i,a in enumerate(ref)]
 out=dict(manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bare_arm_solid_estimate_kg=cases['0']['reference']['total_mass_kg'],harness_budget_kg=.24,cases=cases,dynamics=dynamics,catalog_margin_reference=margin,motor_screw_stacks=screws,virtual_work_error_Nm=max(errs),tube_screen=tubes,assembly_readiness='Digital fit/nominal fastening only; no physical3kg validation',limits=['All motors use catalog mass at casing centre; true rotor inertia not known.','0.24kg unfinished harness budget is not a routed BOM.','Screw stack geometry does not prove printed bearing stress, thread pullout or preload.','SLS/FDM density and solid CAD masses differ from measured sliced parts.','Output bearing ratings and real compact-assembly thermal curves unavailable.'])
 (c.OUT/'feasibility.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print('MASS',out['bare_arm_solid_estimate_kg'],'J2',ref[1]['abs_holding_Nm'],'dynamic',dynamic[1],flush=True)
if __name__=='__main__':run()
