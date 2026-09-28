#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Independent algebra/readback checks; no manufacturing or installed safety approval."""
from pathlib import Path
import json,csv,math,hashlib,re
import numpy as np
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
B=json.loads((P/'budget.json').read_text());D=json.loads((P/'layout-parameters.json').read_text());S=json.loads((ROOT/'docs/engineering/sources/r5-folded-drive01.json').read_text());A=json.loads((P/'msu-reference-audit.json').read_text())
checks=[]
def check(name,value,detail=None):
 checks.append(dict(name=name,pass_=bool(value),detail=detail));assert value,name
def close(a,b,tol=1e-9):return abs(a-b)<=tol
check('calculator source hash',B['script_sha256']==sha(P/'calculate.py'))
for f,h in B['input_hashes'].items():check('frozen input '+f,sha(ROOT/f)==h)
check('one candidate, not manufacturing released',not B['manufacturing_release'] and not B['full_head_fit_confirmed'] and not B['static_hold_0140Nm_guaranteed'])
check('catalogue belt teeth-length',B['belt']['teeth']*B['belt']['pitch_mm']==B['belt']['length_mm'])
check('equal pulley centre relation',close(2*D['axis_distance_mm']+30*3,180))
check('exact pitch diameter',close(B['pulley']['pitch_diameter_exact_mm'],90/math.pi))
check('belt speed from pitch length',close(B['tension']['pitch_speed_m_s'],3200/60*.090))
q=B['tension'];lbf=4.4482216152605
check('Gates tension via explicit imperial conversion',close(q['formula_span_N'],(1.21*(.28/(.0254*lbf))/((90/math.pi)/25.4)+.078*(4.8/.3048*60/1000)**2)*lbf,1e-9))
rows=list(csv.DictReader((P/'tension-and-bearing-loads.csv').open()))
for r in rows:
 for k in r:
  try:r[k]=float(r[k])
  except ValueError:pass
check('span differences satisfy torque',all(close(r['tight_span_N']-r['slack_span_N'],r['torque_Nm']/(.090/math.pi/2)) for r in rows))
check('span force sum',all(close(r['tight_span_N']+r['slack_span_N'],r['radial_resultant_N']) for r in rows))
check('bearing force equilibrium',all(close(r['bearing_rear_radial_N']+r['bearing_front_radial_N'],r['radial_resultant_N']) for r in rows))
check('bearing moment equilibrium',all(close(r['bearing_front_radial_N']*32,r['radial_resultant_N']*19.55) for r in rows))
check('selected tension keeps positive slack',all(r['slack_span_N']>0 for r in rows if r['static_tension_per_span_N']>=q['formula_span_N']))
check('direct motor equal moment exceeds catalogue point',B['motor_direct_rejection']['equal_moment_equivalent_at5mm_N']>50)
check('motor catalogue rpm not misrepresented',B['motor_direct_rejection']['catalogue_rpm']==3000 and not B['motor_direct_rejection']['actual3200rpm_allowance_verified'])
check('catalogue running belt capacity',close(B['belt_capacity_screen']['corrected_Nm'],1.96*.85) and B['belt_capacity_screen']['corrected_Nm']>.28)
check('shaft and coupling nominal tip gap',close(23-2*6.5,58.5-48.5))
check('motor flange and rear length',close(D['motor']['mounting_face_z_mm']-D['motor']['shaft_tip_z_mm'],13) and close(D['motor']['body_rear_z_mm']-D['motor']['mounting_face_z_mm'],90.8))
check('MSU source is surface reference not solids',A['faces']==130 and A['solids']==0)
check('MSU source script hash',A['script_sha256']==sha(P/'audit_msu_reference.py'))
check('MSU native total and gap',close(7.5-(-14.5),22) and close(30-22-6.5,1.5))
check('MSU local face transformation',close(74-7.5,D['screw']['locknut_outer_face_z_mm']) and close(74-(-14.5),D['screw']['bearing_diameter6_shoulder_z_mm']))
check('nominal coupling nut gap',close(D['screw']['locknut_outer_face_z_mm']-65,1.5))
check('folded/inline length',close(D['screw']['shaft_tip_z_mm']+130-(-5),193.5) and close(90.8+13+10+130,243.8))
check('nominal width and motor separation',close(45+16+17.5,78.5) and 45-17.5-16>0)
check('mass incomplete is explicit',B['mass']['whole_head_mass_kg'] is None and len(B['mass']['excluded'])>=5)
check('mixed inertia not disguised as bound',B['extra_inertia']['not_an_actual_or_guaranteed_upper_bound'])
cycle=list(csv.DictReader((ROOT/'engineering/generated/r5-motion02/seven_segment-cycle.csv').open()))
t=np.array([float(r['t_s']) for r in cycle]);n=np.array([float(r['motor_rpm']) for r in cycle]);acc=np.array([float(r['slider_accel_m_s2']) for r in cycle]);base=np.array([float(r['minus_Z_motor_torque_friction_Nm']) for r in cycle]);ideal=np.array([float(r['minus_Z_motor_torque_ideal_Nm']) for r in cycle]);J=B['extra_inertia']['mixed_proxy_total_kg_m2'];tor=base+J*acc*2*math.pi/.0025;w=n*math.pi/30
ref=B['inertia_sensitivity'][-1]
check('cycle duration and speed',close(t[-1]-t[0],1) and close(max(abs(n)),3200,1e-5))
check('added inertia peak',close(ref['peak_torque_plus_motor_friction_Nm'],max(abs(tor))))
check('added inertia RMS',close(ref['RMS_torque_plus_motor_friction_Nm'],math.sqrt(np.trapezoid(tor**2,t)/(t[-1]-t[0]))))
check('additional peak KE',close(ref['additional_peak_kinetic_energy_J'],.5*J*max(w*w)))
check('mechanical braking audit',close(ref['ideal_braking_energy_J'],np.trapezoid(np.maximum(-(ideal+J*acc*2*math.pi/.0025)*w,0),t)))
check('rotor added cycle net energy zero',abs(np.trapezoid(J*acc*2*math.pi/.0025*w,t))<1e-6)
check('source IDs unique and primary HTTPS',len({s['id'] for s in S['sources']})==len(S['sources']) and all(s['url'].startswith('https://') for s in S['sources']))
# Check third-party source files only if locally present; public rebuild does not need their downloads.
local_sources=[]
for s in S['sources']:
 if 'local_reference' in s:
  p=ROOT.parents[1]/'work'/s['local_reference']
  local_sources.append(dict(id=s['id'],available=p.exists(),hash_matches=sha(p)==s['sha256'] if p.exists() else None))
check('present local source hashes unchanged',all(s['hash_matches'] for s in local_sources if s['available']))
bom=list(csv.DictReader((P/'bom.csv').open()))
check('BOM quantities and stage',len(bom)==15 and all(int(r['qty'])>0 and r['selection_status'] in ['candidate','blocked','TBD'] for r in bom))
check('BOM no fabricated price',all(r['budget_price']=='TBD' for r in bom))
check('no vendor binary redistributed',not any(p.suffix.lower() in ['.pdf','.igs','.iges','.stp','.step','.zip'] for p in P.iterdir()))
doc=ROOT/'docs/engineering/hardware/r5-folded-drive01.md';bad=[]
for link in re.findall(r'\]\(([^)]+)\)',doc.read_text()):
 if not link.startswith(('http:','https:','#')) and not (doc.parent/link).exists():bad.append(link)
check('document relative links resolve',not bad,bad)
check('artifacts contain no personal absolute paths',all('/Users/' not in p.read_text() for p in [P/'budget.json',P/'layout-parameters.json',doc,ROOT/'docs/engineering/sources/r5-folded-drive01.json']))
files=sorted([p for p in P.iterdir() if p.is_file() and p.name!='verification.json']+[doc,ROOT/'docs/engineering/sources/r5-folded-drive01.json'])
result=dict(revision='R5-FOLDED-DRIVE01',status='PASS calculation/source/interface-requirement checks only',checks=checks,local_source_hash_audit=local_sources,artifact_hashes={str(p.relative_to(ROOT)):sha(p) for p in files},figures_visual_review='Both original PNG figures inspected; no manufacturer CAD redistributed; diagrams label unresolved supports/tolerances',manufacturing_release=False,head_fit_confirmed=False,hardware_test_performed=False)
(P/'verification.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n');print(f'{len(checks)} checks PASS; {len(files)} artifact hashes')
