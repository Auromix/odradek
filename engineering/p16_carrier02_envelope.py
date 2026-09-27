#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Analytic per-part AABB z support bound over every independent finger angle."""
import math,json,hashlib,itertools
from pathlib import Path
import numpy as np
import p16_carrier02_study as c2
OUT,ROOT=c2.OUT,c2.ROOT

def extrema(s,lo_deg,hi_deg,offset_z):
 lo,hi=math.radians(lo_deg),math.radians(hi_deg);bb=np.array(c2.st.bb(s));rows=[]
 for x,z in itertools.product(bb[:,0],bb[:,2]):
  ts=[lo,hi]+[math.atan2(x,z)+k*math.pi for k in range(-2,3) if lo<math.atan2(x,z)+k*math.pi<hi]
  rows.extend(dict(z_head_mm=float(x*math.sin(t)+z*math.cos(t)+offset_z),q_deg=math.degrees(t),bounding_corner_xz_mm=[float(x),float(z)]) for t in ts)
 a=min(rows,key=lambda x:x['z_head_mm']);b=max(rows,key=lambda x:x['z_head_mm'])
 # Dense sample checks catch unit/sign mistakes, not establish the bound.
 for t in np.linspace(lo,hi,123):
  vals=[x*math.sin(t)+z*math.cos(t)+offset_z for x,z in itertools.product(bb[:,0],bb[:,2])]
  assert min(vals)>=a['z_head_mm']-1e-7 and max(vals)<=b['z_head_mm']+1e-7
 return dict(z_lower_bound_mm=a['z_head_mm'],z_upper_bound_mm=b['z_head_mm'],lower_bound_witness=a,upper_bound_witness=b,bbox_local_mm=[x.tolist() for x in bb])

def main():
 ct=ROOT/'engineering/generated/contact02-study/study.json';f=json.loads(ct.read_text())['fingers'];out=[];stock=[]
 for ff in f:
  p,m=c2.root_parts(ff);rows=[]
  for name,s in p.items():rows.append(dict(part=name,**extrema(s,0,ff['closure_study_deg'],ff['root_z_mm'])))
  worst=min(rows,key=lambda x:x['z_lower_bound_mm']);upper=max(rows,key=lambda x:x['z_upper_bound_mm'])
  out.append(dict(finger=ff['id'],range_deg=[0,ff['closure_study_deg']],root_head_z_mm=ff['root_z_mm'],z_lower_bound_mm=worst['z_lower_bound_mm'],z_upper_bound_mm=upper['z_upper_bound_mm'],limiting_lower_part=worst['part'],parts=rows))
  steel=p['integral_steel_crank_spindle'];blank=c2.C(40,80,(0,-33,0),(0,1,0));outside=steel.Volume()-steel.intersect(blank).Volume();assert abs(outside)<1e-5
  stock.append(dict(finger=ff['id'],candidate_original_blank='Ovako6082/MoC410M 42CrMo4 +QT round D80 x L80',blank_axis='local u',blank_u_range_mm=[-33,47],blank_diameter_mm=80,steel_outside_blank_mm3=outside,finished_nominal_steel_volume_mm3=steel.Volume(),stock_nominal_volume_mm3=blank.Volume(),guarantee_dimension_basis='Original D80 bar, in supplier40<D<100 mm band; not finished7mm ligament',candidate_Rel_min_MPa=650.,release='Not selected for procurement/manufacture; require exact supplier heat/condition certificate and surface/heat-treatment/finish machining plan.'))
 sources=[Path(__file__),ROOT/'engineering/p16_carrier02_study.py',ct,ROOT/'engineering/generated/p16-carrier-02/geometry.json',ROOT/'engineering/generated/p16-carrier-02/UR_integral_steel_crank_spindle.step',ROOT/'engineering/generated/p16-carrier-02/LL_integral_steel_crank_spindle.step']
 result=dict(revision='P16-CARRIER-02',method='Each actual part BREP axis-aligned bounding box contains that part; z(q)=x sin(q)+z cos(q)+root_z. Evaluate endpoints and all derivative-zero angles per xz corner. Union min/max bounds every point at every independent q. Conservative lower/upper bounds, NOT asserted actual surface extrema.',root_rotor_envelopes=out,steel_stock_candidate=stock,sources_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},exclusions='P16 body, stationary carrier/base and original optic module unchanged, excluded from rotor bounds; no parent24mm extension or distal later lamp/pad/connector integration.',coordinate_reference='head face z0, J7 contact z-140; current worldfacez780, or plus24 only if root extension explicitly integrated.',selfchecks='Analytic bounds crosschecked against123 angles per part; cylinder80x80 contains actual revised steel; no q7 dependence of z under rotation about head z.')
 (OUT/'root-z-envelope.json').write_text(json.dumps(result,indent=2)+'\n');print([(r['finger'],r['z_lower_bound_mm'],r['z_upper_bound_mm'],r['limiting_lower_part']) for r in out])
def finalize():
 assert hashlib.sha256((ROOT/'engineering/parameters/r4-layout.json').read_bytes()).hexdigest()==c2.st.EXPECTED
 paths={n:OUT/(n+'.json') for n in ['geometry','motion','loads','qa-mass','root-z-envelope']};data={n:json.loads(p.read_text()) for n,p in paths.items()}
 mot=data['motion'];assert all(v['certified'] for v in mot.values() if isinstance(v,dict) and 'certified' in v);assert mot['four_independent_modules']['all_independent_pairs_certified']
 assert all(v['certified'] for v in mot['unchanged_interfaces']['added_bridge_vs_native_containing_envelopes'].values())
 assert all(x['own_rotationally_invariant_shell_gap_mm']>=1-1e-6 and not x['internal_intersections'] for x in data['geometry']['geometry'])
 assert all(q['valid'] and q['solid_count']==236 for q in data['qa-mass']['exports'])
 refs=list(paths.values())+[ROOT/'docs/engineering/p16-carrier02-study.md',ROOT/'docs/engineering/sources/p16-carrier02.json']+list((ROOT/'engineering').glob('*p16_carrier02*.py'))
 result=dict(revision='P16-CARRIER-02',manufacturing_release=False,whole_wrist_available=False,local_nominal_finger_motion_passed=True,minimum_nominal_root_clearance_mm=1.,mass=data['qa-mass']['mass'],root_rotor_z_bounds=[{k:r[k] for k in ['finger','range_deg','z_lower_bound_mm','z_upper_bound_mm']} for r in data['root-z-envelope']['root_rotor_envelopes']],proof_files={n:str(p.relative_to(ROOT)) for n,p in paths.items()},sources_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in refs},warnings=['CARRIER01 wrist collision remains; parent24mm extension not integrated.','Material+QT and original stock certificate, fits, local notch/fatigue, clamp preload, bearing pressure centers and P16 duty/holding remain open.','CONTACT02 distal placeholders retained; parent later lamp and pad-retention are not integrated.'])
 (OUT/'study.json').write_text(json.dumps(result,indent=2)+'\n');print('Study index finalized')
if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--finalize',action='store_true');a=ap.parse_args()
 finalize() if a.finalize else main()
