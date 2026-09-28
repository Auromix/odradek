#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Recompute evidence checks without changing frozen sources or hiding failed hardware margins."""
from pathlib import Path
import json,hashlib,csv,math,re,xml.etree.ElementTree as ET
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
b=json.loads((P/'budget.json').read_text());i=json.loads((P/'mechanical-interface.json').read_text());sources=json.loads((ROOT/'docs/engineering/sources/r5-cam-hardware01.json').read_text());checks=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(name,ok,value=None):
 checks.append(dict(name=name,passed=bool(ok),observed=value));assert ok,name
for p,h in b['input_hashes'].items():check('input '+p,sha(ROOT/p)==h)
check('calculate script hash',sha(P/'calculate.py')==b['script_sha256'])
check('no manufacturing release',b['manufacturing_release'] is False)
check('component source IDs resolvable',set(i['source_ids'])<=set(s['id'] for s in sources['sources']))
for s in sources['sources']:
 if s.get('cache_path'):
  p=ROOT.parents[1]/s['cache_path']
  if p.exists():check('cached primary source hash '+s['id'],sha(p)==s['sha256'])
  else:check('retained primary reference hash format '+s['id'],bool(re.fullmatch('[0-9a-f]{64}',s['sha256'])))
for d in b['dynamics']:
 prefix=d['timing']+'/'+d.get('kind','system')
 if 'kind' in d:
  check(prefix+' rated relative speed screen',d['peak_both_wall_relative_rpm_bound']<2100,d['peak_both_wall_relative_rpm_bound'])
  check(prefix+' actual relative <= both-wall bound',d['peak_loaded_wall_relative_rpm']<=d['peak_both_wall_relative_rpm_bound']+1e-8)
  check(prefix+' force changes wall (not suppressed)',d['signed_total_range_N'][0]<0<d['signed_total_range_N'][1])
  check(prefix+' contains moving-root inertia', 'radial-hinge translation acceleration coupling' in d['includes'])
 else:
  check(prefix+' independent path force reconstruction',abs(d['peak_path_force_N']-d['source_peak_path_force_N'])<1e-8)
  check(prefix+' work-energy residual',d['work_energy_residual_J']<1e-5,d['work_energy_residual_J'])
  for kind,v in d['independent_COM_acceleration_FD'].items():check(prefix+'/'+kind+' independent acceleration FD',v['max_abs_error_m_s2']/v['peak_analytic_acceleration_m_s2']<.0005,v)
check('exactly48 static cases',len(b['static_grip_cases'])==48)
for r in b['static_grip_cases']:
 tau=.001*r['contact_local_x_mm']*r['object_normal_N']-.006*r['object_on_finger_downward_friction_N']+r['gravity_drive_moment_Nm']
 assert abs(tau-r['follower_force_N']*.008/math.sqrt(2))<1e-12
 assert r['vertical_equilibrium_case']==bool(r['object_on_finger_downward_friction_N'])
check('static torque equilibrium and separated normal-only cases',True)
nominal=[r for r in b['static_grip_cases'] if r['mu_assumed']==.4 and r['contact_local_x_mm']==65 and r['vertical_equilibrium_case']]
check('two nominal contact cases',len(nominal)==2)
check('nominal CFS C0 screen>=3',min(r['CFS4_C0_safety_ratio'] for r in nominal)>3)
failed=[r for r in b['static_grip_cases'] if r['mu_assumed']==.4 and r['contact_local_x_mm']==95 and r['vertical_equilibrium_case']]
check('x95 failure retained, not declared passing',max(r['CFS4_C0_safety_ratio'] for r in failed)<3)
failedtrack=[r for r in b['static_grip_cases'] if r['mu_assumed']==.2 and r['contact_local_x_mm']==95 and r['vertical_equilibrium_case']]
check('low-mu track failure retained',max(r['flat_track_catalogue_ratio_40HRC'] for r in failedtrack)<1)
check('root-bearing moment balance',max(abs(r['moment_balance_residual_Nm']) for r in b['root_reaction_sensitivity'])<1e-12)
newroot=[r for r in b['root_reaction_sensitivity'] if r['bearing_center_span_mm']==32 and r['cam_center_lateral_y_mm']==32]
check('root overhang effect retained',len(newroot)==2 and min(r['near_resultant_N'] for r in newroot)>400)
check('root C0 margin below3 explicitly retained',max(r['SKF607slash8_C0_ratio'] for r in newroot)<3)
c=i['CFS4'];a=c['nominal_axial_intervals'];s=c['dimensions']
check('outer ring width and center',a['rolling_outer_ring'][1]-a['rolling_outer_ring'][0]==s['C'] and sum(a['rolling_outer_ring'])/2==a['rolling_center'])
check('B1=B+B2',s['B1']==s['B']+s['B2'])
check('stock nut thread engagement nominal',c['mounting_candidate']['nut_interval']==[4,7.2] and s['G1']==4)
check('correct root bearing, not same-size substitute',i['root_support_candidate']['exact_designation']=='607/8-2Z' and i['root_support_candidate']['ratings']['C0_N']==950)
check('matched SKF abutment record',i['root_support_candidate']['abutment']['shaft_shoulder_diameter_min']==10 and i['root_support_candidate']['abutment']['shaft_shoulder_diameter_max']==11)
check('no invented trunnion or positive torque SKU',i['root_support_candidate']['trunnion_material_fit_retention'] is None and i['root_support_candidate']['positive_torque_transfer'] is None)
check('slot candidate locally regular',0<b['geometry']['local_offset_regularity_margin']<1,b['geometry']['local_offset_regularity_margin'])
check('slot remains unreleased',b['geometry']['slot_width_is_not_released'])
for p in P.glob('*.svg'):ET.parse(p);check('valid SVG '+p.name,True)
rows=list(csv.DictReader((P/'bom.csv').open()));check('8 BOM rows with candidate/TBD boundaries',len(rows)==8 and all(r['selection_status'] in ['candidate','included-accessory','TBD'] for r in rows))
check('catalogue pieces reference mass subtotal',abs(sum(float(r['qty_four_petals'])*float(r['unit_reference_mass_kg']) for r in rows if r['unit_reference_mass_kg'])-.0736)<1e-12)
doc=ROOT/'docs/engineering/hardware/r5-cam-hardware01.md'
for link in re.findall(r'\]\(([^)]+)\)',doc.read_text()):
 if not link.startswith('http') and not link.endswith('verification.json'):check('document link '+link,(doc.parent/link).resolve().exists())
files=[p for p in sorted(P.iterdir()) if p.is_file() and p.name!='verification.json']+[doc,ROOT/'docs/engineering/sources/r5-cam-hardware01.json']
report=dict(revision='R5-CAM-HARDWARE01',result='PASS evidence-consistency checks; not hardware acceptance',check_count=len(checks),checks=checks,artifact_sha256={str(p.relative_to(ROOT)):sha(p) for p in files},visual_review=dict(status='rendered PNGs inspected; labels, axes, source notes and candidate scope readable',files=['follower-interface.png','single-petal-loads.png']),unpassed_engineering_requirements=['full four-petal carrier collision and tolerance proof','root-bearing static target3 not met in current span32/Y32 example','x95/mu.4 CFS static target3 not met;mu.2/x95 flat-track capacity exceeded','shaft/pin/bracket/fastener strength, fits, positive torque path and locking','curved-track material/finish/contact fatigue and reversal impacts','completed assemblies and2kg object tests'],manufacturing_release=False)
(P/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(f'{len(checks)} evidence checks PASS; {len(files)} artifact hashes; hardware exclusions retained')
