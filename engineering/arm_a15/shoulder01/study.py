# SPDX-License-Identifier: CC-BY-NC-4.0
"""Conventional eye/eye gas spring geometry and conditional force screening."""
from pathlib import Path
import json,sys,copy,math
import numpy as np
from scipy.optimize import minimize_scalar
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'engineering/arm_a15/robstride01'))
import study as rs
L=copy.deepcopy(rs.D['layout'])
models=['RS03','RS04','RS04','RS04','RS10P','RS10P','RS00']
for j,m in zip(L['joints'],models):
 j.update(model=m,mass_kg=rs.SPECS[m]['mass_kg'])
L['joints'][1]['offset']=[0,0,110]
L['joints'][1]['motor_center']=[0,91.35,0]
L['joints'][2]['offset']=[0,-10,0]
L['joints'][5]['motor_center']=[0,0,72.3]
L['joints'][4].update(diameter_mm=57,length_mm=60.6)
L['joints'][5].update(diameter_mm=57,length_mm=60.6)
L['joints'][2].update(diameter_mm=120,length_mm=55.7)
L['joints'][3].update(diameter_mm=120,length_mm=55.7)
L['id']='A15-SHOULDER01-study-not-assembly'
L['flange_from_J7_mm']=[110,0,0]
a,b=.065,.185
def dimensions(q2):
 t=np.radians(q2);length=np.sqrt(a*a+b*b+2*a*b*np.cos(t))
 return length,a*b*np.sin(t)/length
def main():
 q=np.array(list(L['poses'].values())+[[j['limits_deg'][0]+rs.halton(k,base)*(j['limits_deg'][1]-j['limits_deg'][0]) for j,base in zip(L['joints'],[2,3,5,7,11,13,17])] for k in range(1,4097)],float)
 budget=copy.deepcopy(rs.BUDGET);budget[-1]['mass_kg']=.25
 raw=[rs.batch_gravity(L,q,p,budget) for p in [0,3]]
 length,lever=dimensions(q[:,1]);compression=np.clip((.264-length)/.100,0,1)
 # Progression/friction/tolerance bounds are proposed purchase/test conditions,
 # NOT manufacturer-guaranteed values of this catalogue item.
 slopes=[1.,1.3,1.6];temps=[0,50];tolerances=[.9,1.1];frictions=[-30,30]
 def force(f1,progression,temp,tol,friction):
  return f1*(1+(progression-1)*compression)*(1+.0035*(temp-20))*tol+friction
 def objective(f1):
  values=[]
  for prog in [1,1.6]:
   for temp in temps:
    for tol in tolerances:
     for friction in frictions:
      assist=force(f1,prog,temp,tol,friction)*lever
      values.append(max(float(np.max(abs(t[:,1]+assist))) for t in raw))
  return max(values)
 opt=minimize_scalar(objective,bounds=(50,420),method='bounded')
 f1=float(opt.x);cases=[]
 for prog in slopes:
  for temp in temps:
   for tol in tolerances:
    for friction in frictions:
     assist=force(f1,prog,temp,tol,friction)*lever
     cases.append(dict(progression=prog,temperature_C=temp,F1_multiplier=tol,friction_N=friction,
       empty_max_Nm=float(np.max(abs(raw[0][:,1]+assist))),loaded_max_Nm=float(np.max(abs(raw[1][:,1]+assist)))))
 qdense=np.linspace(-60,110,17001);ldense,_=dimensions(qdense)
 # Independent full-range endpoint/tolerance check. Casing +/-2 shifts both
 # compressed and extended lengths; retain 3mm stop reserve at either end.
 minimum_allowed_mm=264+2-100+3;maximum_allowed_mm=264-2-3
 valid=ldense.min()*1000>=minimum_allowed_mm and ldense.max()*1000<=maximum_allowed_mm
 max_i=max(cases,key=lambda c:max(c['empty_max_Nm'],c['loaded_max_Nm']))
 # Unit force generalised moment must match potential derivative.
 errors=[]
 for theta in [-60,0,75,90,110]:
  h=1e-4;energy=lambda x:-float(dimensions(np.array([x]))[0][0])
  derivative=(energy(theta+h)-energy(theta-h))/(2*math.radians(h));errors.append(abs(derivative-dimensions(np.array([theta]))[1][0]))
 assert max(errors)<1e-8 and valid
 result=dict(revision='A15-SHOULDER01',models=models,layout=L,structure_budget=budget,
  conventional_mechanism='One catalogue eye/eye gas spring, two pins; no secondary transmission or cam.',
  supplier=dict(name='SUSPA',catalogue_url='https://www.suspa.com/downloads/SUSPA_General_product_catalog_EN.pdf',catalogue_sha256='fcc5611a662d7db25ac5809071a4866bbe0a311aa6e270f1f59d0d0336bcf3d4',pdf_page=10,
   order_number='01625011',description='16-1-131-110-A17-B17',nominal_extended_eye_distance_mm=264,length_tolerance_mm=2,stroke_mm=100,tube_diameter_mm=15,rod_diameter_mm=6,eye_diameter_mm=6.1,eye_thickness_mm=3,eye_end_radius_mm=6.5,F1_order_range_N=[50,420],F1_not_yet_ordered=True),
  anchor_geometry=dict(fixed_frame='J1.rotor',fixed_anchor_mm=[0,-80,-75],moving_frame='J2.rotor',moving_anchor_mm=[65,-80,0],anchor_joint_yaw_axis=[0,1,0],a_mm=65,b_mm=185),
  full_range_geometry=dict(min_eye_distance_mm=float(ldense.min()*1000),max_eye_distance_mm=float(ldense.max()*1000),min_allowed_with_tolerance_and_reserve_mm=minimum_allowed_mm,max_allowed_with_tolerance_and_reserve_mm=maximum_allowed_mm,required_travel_mm=float((ldense.max()-ldense.min())*1000),within_catalogue_stroke=True),
  sampled_ideal_order_force_N=f1,uncompensated_empty_max_Nm=[float(x) for x in np.max(abs(raw[0]),axis=0)],uncompensated_loaded_max_Nm=[float(x) for x in np.max(abs(raw[1]),axis=0)],
  proposed_force_envelope_cases=cases,worst_proposed_force_envelope=max_i,worst_shoulder_sample_Nm=float(objective(f1)),sample_count=len(q),
  verification=dict(max_spring_virtual_work_error_Nm=max(errors)),selection_frozen=False,production_release=False,
  limitations=['Force envelope is a stated procurement/test assumption, not a supplier guarantee. Real force/length/temperature/friction curves are still required.',
   'Joint-domain samples are not collision-qualified or global extrema. Model uses provisional structural mass and motor centres, not completed CAD.',
   '+20mm shoulder elevation and -10mm J3 lateral shift are pending physical packaging checks against the canonical base.',
   'Gas spring must be cylinder up/rod down; baseline includes radius/eye envelopes only, not an exact supplier STEP.',
   'No spring in plastic supported fit. Catalogue spring failure does not provide holding redundancy; metal assembly needs independent loss-of-power/failure assessment.'])
 out=HERE/'build';out.mkdir(exist_ok=True);(out/'study.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print('STANDARD_STROKE',result['full_range_geometry']);print('F1',f1,'WORST',result['worst_shoulder_sample_Nm']);print('RAW3',result['uncompensated_loaded_max_Nm'])
if __name__=='__main__':main()
