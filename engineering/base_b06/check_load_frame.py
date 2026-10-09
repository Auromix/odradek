# SPDX-License-Identifier: CC-BY-NC-4.0
"""Exact BREP static intersections and desk-thickness envelope checks.
No stiffness, friction, weld quality or physical proof is implied.
"""
import json,math,hashlib,itertools
from pathlib import Path
import load_frame as cad
OUT=cad.OUT
results=[]
for desk in (15,30,60):
 parts=cad.make(desk);pairs=[];threads=[]
 for a,b in itertools.combinations(parts,2):
  if a['category']=='environment' and b['category']=='environment':continue
  aa=a['shape'].BoundingBox();bb=b['shape'].BoundingBox()
  if any(getattr(aa,k+'max')<=getattr(bb,k+'min')+1e-6 or getattr(bb,k+'max')<=getattr(aa,k+'min')+1e-6 for k in 'xyz'):continue
  v=a['shape'].intersect(b['shape']).Volume()
  if v>.001:
   record={'a':a['id'],'b':b['id'],'intersection_mm3':v}
   metal=next((p for p in (a,b) if p['category']=='metal'),None)
   hw=next((p for p in (a,b) if p['category']=='hardware'),None)
   intended=False
   if metal and hw:
    mid,hid=metal['id'],hw['id']
    intended=(mid=='B06-103-LOWER-JAW' and hid.startswith('HW-DIN6332'))
    intended|=(mid.startswith('B06-105-POST-') and hid in ('HW-M8-TOP-'+mid.rsplit('-',1)[1],'HW-M8-BOTTOM-'+mid.rsplit('-',1)[1]))
    intended|=(mid=='B06-104-LOAD-FLANGE' and hid.startswith('HW-ROOT-M6-'))
    intended|=(mid=='B06-102-REAR-WEB' and hid.startswith('HW-HANGER-M6-'))
    intended|=(mid.startswith('B06-201-HANGER-') and hid.startswith('HW-TRAY-M4-'))
    intended|=(mid=='B06-202-TRAY' and hid.startswith('HW-STOP-M4-'))
   if intended:
    record['interpretation']='Declared threaded member and corresponding bolt: minor bore vs maximum major thread envelope; no helical threads';threads.append(record)
   else:pairs.append(record)
 # Thread portion extends from pin end-100 to pin end-10 (vendor envelope).
 pinend=-desk-13.3
 overlap=max(0,min(-90,pinend-10)-max(-104,pinend-100))
 foot_bottom=-desk-23
 results.append({'desk_mm':desk,'interferences':pairs,'intended_thread_envelope_overlaps':threads,'thread_engagement_in_jaw_mm':overlap,'foot_to_jaw_gap_mm':foot_bottom-(-90)})
 parts=cad.make(30)
rho={'S355':7.85e-6,'6061-T651':2.70e-6,'silicone':1.15e-6,'steel':7.85e-6,'PETG':1.27e-6}
masses=[{'id':p['id'],'mass_kg':p['shape'].Volume()*rho[p['material']]} for p in parts if p['material'] in rho]
# Deliberately conservative hand bounds. These are screening assumptions, not ratings.
M=150000+3000*109+500*120
screen={'assumed_loads':{'overturning_Nm':150,'vertical_N':500,'lateral_N':100,'yaw_Nm':40,'preload_each_screw_N':1500},
 'deck_simple_beam_sigma_MPa':6*M/(84*15**2),'jaw_leg_sigma_MPa':6*(1500*110)/(45*14**2),
 'table_pressure_MPa':3000/(2*70*90),'estimated_screw_torque_Nm_at_K_0_2':.2*1500*.012,
 'shelf_3kg_each_side_force_N':3*9.81/2,'shelf_cantilever_assumed_mm':315,
 'shelf_simple_beam_deflection_mm':(3*9.81/2)*315**3/(3*69000*(8*20**3/12)),
 'status':'Screen only; no certified material, actual weld/desk strength, friction, deflection model or operating-load qualification'}
report={'revision':'B06-LOAD-01','cad_source_sha256':hashlib.sha256(Path(cad.__file__).read_bytes()).hexdigest(),
 'desk_samples':results,'masses':masses,'total_modeled_mass_kg':sum(m['mass_kg'] for m in masses),
 'screening':screen,'exact_static_clearance_pass':all(not p['interferences'] for p in results),
 'limits':['Exact nominal BREP only; threads, supplier swivels and weld beads simplified/omitted.',
 'Bolts/washers included as purchase envelopes; root mesh and plug/tool actuation remain separate integration tests.',
 '15/30/60mm sampled; continuous installation, assembly and table-load tests pending.']}
(OUT/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
print('LOAD_CHECK',report['exact_static_clearance_pass'],'MASS_KG',round(report['total_modeled_mass_kg'],3))
for r in results:
 for p in r['interferences']:print(r['desk_mm'],p)
