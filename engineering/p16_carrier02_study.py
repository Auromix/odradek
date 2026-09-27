#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""P16-CARRIER-02: bounded near-root transition and net-section study.
No carrier01/baseline/vendor CAD is modified or republished.
"""
from pathlib import Path
import argparse,hashlib,itertools,json,math
import numpy as np
import cadquery as cq
import p16_carrier_study as c01
import p16_packaging_study as p16
import gripper_root_support_study as st
ROOT=c01.ROOT;OUT=ROOT/'engineering/generated/p16-carrier-02';B,C,union=c01.B,c01.C,c01.union
P=dict(revision='P16-CARRIER-02',immutable_distal_x_greater_than_mm=25.,neck_full_width_mm=18.,neck_thickness_mm=6.,transition_R_mm=1.,
       bridge_x_mm=[10.,17.],bridge_z_mm=[-8.,0.],bridge_u_mm=[-29.1,5.],bridge_inside_hub_z_mm=[-7.4,0.],bearing_centers_u_mm=[19.,29.],actuator_offset_u_mm=-18.,drive_force_screen_N=300.,head_face_shift_mm=0.)

def root_parts(f):
 p,m=c01.root_parts(f);old=p['metal_blade_with_narrow_tongue']
 r=math.sqrt(.5)
 neck=cq.Workplane('XY').moveTo(15,-9).lineTo(24,-9).threePointArc((24+r,-10+r),(25,-10)).lineTo(25,10).threePointArc((24+r,10-r),(24,9)).lineTo(15,9).close().extrude(6).val()
 for u in [-4.5,4.5]:neck=neck.cut(C(1.7,8,(21,u,-1),(0,0,1)))
 p['metal_blade_with_narrow_tongue']=old.intersect(B(25,200,-100,100,-1,20)).fuse(neck)
 # Strengthen rather than shave the negative-u bridge. End x17 avoids all existing nut pockets.
 p['integral_steel_crank_spindle']=p['integral_steel_crank_spindle'].fuse(B(10,17,-29.1,-5,-8,0)).fuse(B(10,17,-5,5,-7.4,0))
 assert all(s.isValid() and len(s.Solids())==1 for s in p.values())
 return p,m

def shell():
 return union([C(24,2,(0,12,0),(0,1,0),28),C(24,20,(0,14,0),(0,1,0),32),C(24,2,(0,34,0),(0,1,0),27.5),C(24,5.5,(0,36,0),(0,1,0),30)])

def geometry():
 f=json.loads((ROOT/'engineering/generated/contact02-study/study.json').read_text())['fingers'];rr=[];rows=[]
 for i,ff in enumerate(f):
  p,m=root_parts(ff);old,_=c01.root_parts(ff);rr.append((p,m));delta=[]
  for n in p:
   gate=B(25+1e-5,300,-300,300,-300,300);a=p[n].intersect(gate);b=old[n].intersect(gate);v=0. if a.Volume()<1e-10 and b.Volume()<1e-10 else a.Volume()+b.Volume()-2*a.intersect(b).Volume()
   assert v<1e-5;delta.append(dict(part=n,distal_symmetric_difference_mm3=v))
  clear=st.comp(p.values()).distance(shell());assert clear>=1-1e-6
  own=[]
  for n,s in p.items():
   d=s.distance(shell())
   if d<2:own.append(dict(part=n,coaxial_shell_gap_mm=d))
  hits=[]
  for (a,sa),(b,sb) in itertools.combinations(p.items(),2):
   if st.gap_bounds(st.bb(sa),st.bb(sb))>1e-6:continue
   v=sa.intersect(sb).Volume()
   if v>1e-4:hits.append(dict(a=a,b=b,volume_mm3=v))
  rows.append(dict(finger=ff['id'],own_rotationally_invariant_shell_gap_mm=clear,near_parts=own,distal_checks=delta,internal_intersections=hits,mass_change_g=sum((p[n].Volume()-old[n].Volume())*st.DENSITY[m[n]] for n in p if m[n]!='optical_placeholder')))
  assert not hits, str(hits)
  outside=p['metal_blade_with_narrow_tongue'].Volume()-p['metal_blade_with_narrow_tongue'].intersect(old['metal_blade_with_narrow_tongue']).Volume();assert abs(outside)<1e-5
  rows[-1]['new_blade_outside_old_mm3']=outside
 OUT.mkdir(parents=True,exist_ok=True)
 data=dict(parameters=P,geometry=rows,scope='No x>25 material changed. Root axis/4DOF and carrier01 face remain. No wrist-extension integration. Nominal clearance only; tolerances/deflection and supplier limits still apply.')
 (OUT/'geometry.json').write_text(json.dumps(data,indent=2)+'\n')
 for i in [0,2]:
  for n in ['metal_blade_with_narrow_tongue','integral_steel_crank_spindle']:
   cq.exporters.export(rr[i][0][n],str(OUT/(f[i]['id']+'_'+n+'.step')))
 print(json.dumps([(x['finger'],x['own_rotationally_invariant_shell_gap_mm'],x['mass_change_g']) for x in rows]),flush=True)
 return f,rr,data
def motion():
 f,rr,g=geometry();_,_,base,fixed,mods,om=c01.nominal()
 beta=26*(123+26)/p16.kin(0)[2]**2;V=26+160*beta
 bridge=union([B(10,17,-29.1,-5,-8,0),B(10,17,-5,5,-7.4,0)]);rot=lambda q:bridge.rotate((0,0,0),(0,1,0),-q)
 added={}
 for i in [0,2]:
  added[f[i]['id']]=p16.certificate(lambda q:st.comp(p16.envelopes(q).values()),rot,V+p16.radius(bridge),f[i]['closure_study_deg'],step=2)
  print('bridge',f[i]['id'],added[f[i]['id']],flush=True)
 (OUT/'added-bridge-motion.json').write_text(json.dumps(added,indent=2)+'\n')
 assert all(r['certified'] for r in added.values())
 result=c01.run_motion(f,rr,base,fixed)
 result['unchanged_interfaces']={'source':'engineering/generated/p16-carrier-01/study.json','source_sha256':hashlib.sha256((c01.OUT/'study.json').read_bytes()).hexdigest(),'retained':'Old integral spindle, pin/clevis, base and bearing interfaces unchanged. Modified blade is a subset of old blade. Added bridge checked independently against all four conservative native-contained P16 envelopes.','added_bridge_vs_native_containing_envelopes':added,'limitations':'Distal LED/connector and retained pad hardware not merged; wrist range still blocked by carrier01 J6 collision. No 24 mm extension integrated.'}
 (OUT/'motion.json').write_text(json.dumps(result,indent=2)+'\n')
 return result
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--motion',action='store_true');args=ap.parse_args()
 motion() if args.motion else geometry()
