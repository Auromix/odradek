#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Read-only FORM01 inspection. Query solids are gauges, not new deliverable CAD."""
import hashlib,json,math,sys
from pathlib import Path
import cadquery as cq
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
FORM=ROOT/'engineering/generated/r5-petal-form01'
sys.path.insert(0,str(ROOT/'engineering'))
from build_link56_study import face_contact

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def volume(s):return sum(abs(x.Volume()) for x in s.Solids())
def cyl(x,y,r,z0,z1):return cq.Solid.makeCylinder(r,z1-z0,cq.Vector(x,y,z0))
def annulus(x,y,ro,ri,z0,z1):return cyl(x,y,ro,z0,z1).cut(cyl(x,y,ri,z0,z1))
def put(o): (OUT/'stack-check.json').write_text(json.dumps(o,indent=2)+'\n')

def main():
 p=json.loads((FORM/'parameters.json').read_text());assert sha(FORM/'study.json')=='6239375fadc6c43a9e538674af1f0bf620ba53a4962bd5320f33bd06474869e9'
 sources={str(x.relative_to(ROOT)):sha(x) for x in [FORM/'parameters.json',FORM/'study.json',Path(__file__),ROOT/'engineering/build_link56_study.py']}
 rows=[]
 for kind in ['upper','lower']:
  parts={n:cq.importers.importStep(str(FORM/f'{kind}-right/{n}.step')).val() for n in ['frame','retainer','bearing_cover','compliant_skin','PCB_blank_reservation','back_electronics_reservation','LED_front_reservation']}
  for n in parts:sources[f'engineering/generated/r5-petal-form01/{kind}-right/{n}.step']=sha(FORM/f'{kind}-right/{n}.step')
  for i,(x,y) in enumerate(p[kind]['retainer_holes_mm']):
   washer=annulus(x,y,2.5,1.1,-.3,0)
   area=face_contact(parts['frame'],washer,[0,0,0],[0,0,1])['shared_planar_face_area_mm2']
   expected=math.pi*(2.5**2-1.1**2)
   assert abs(area-expected)<1e-5,(kind,i,area,expected)
   # Fixed half-space proof: bare-petal solids all have Z>=0; nut and
   # tool travel below the rear washer. Future root/rod is not present.
   rear=cyl(x,y,4,-25,-.31)
   rear_v=sum(volume(rear.intersect(s)) for s in parts.values())
   assert rear_v<1e-6
   # An ideal 90-degree cone, no edge land. It is not an actual vendor solid.
   ht=8.8;tip=ht-12
   head=cq.Solid.makeCone(1.0,1.9,.9,cq.Vector(x,y,ht-.9))
   shaft=cyl(x,y,1,tip,ht-.9)
   iv=sum(volume(head.fuse(shaft).intersect(s)) for s in parts.values())
   assert iv<1e-5
   # PH driver allocations only: no selected tool silhouette is claimed.
   front=cyl(x,y,1.5,8.81,30)
   front_v=sum(volume(front.intersect(s)) for s in parts.values())
   other_centers=[a for j,a in enumerate(p[kind]['retainer_holes_mm']) if j!=i]
   tool_to_other_nut=min(math.hypot(x-a,y-b)-4-4/math.sqrt(3) for a,b in other_centers)
   rows.append(dict(kind=kind,index=i,xy_mm=[x,y],washer_contact_area_mm2=area,washer_entire_annulus_supported=True,ideal_cone_overlap_mm3=iv,ideal_head_top_z_mm=ht,real_vendor_head_top_qualified=False,front_D3_gauge_overlap_mm3=front_v,rear_D8_gauge_overlap_mm3=rear_v,rear_tool_to_other_nut_circumscribed_gap_mm=tool_to_other_nut))
  for i,(x,y) in enumerate(p['root_interface_holes_mm']):
   h=cyl(x,y,3,7,8.3)
   support=face_contact(parts['frame'],h,[0,0,7],[0,0,1])['shared_planar_face_area_mm2']
   expected=math.pi*(3**2-1.6**2)
   assert abs(support-expected)<1e-5
   front=cyl(x,y,1.5,8.31,30);v=sum(volume(front.intersect(s)) for s in parts.values());assert v<1e-6
   rows.append(dict(kind=kind,root_index=i,xy_mm=[x,y],root_head_D_mm=6,root_head_height_mm=1.3,root_head_top_z_mm=8.3,head_full_annulus_supported=True,support_area_mm2=support,front_D3_driver_gauge_overlap_mm3=v,root_interface_qualified=False))
 # The 3 mm backing plate is a bench fixture requirement, not part of a new robot hub.
 rootstack=dict(bolt='NBK SSHS-M3-16-FT',frame_z_mm=[0,7],head_z_mm=[7,8.3],proposed_bench_backing_plate_z_mm=[-3,0],washer_z_mm=[-3.5,-3],nut_z_mm=[-5.9,-3.5],tip_z_mm=-9,nominal_tail_beyond_nut_mm=3.1,backing_plate_is_installed_CAD=False,backing_plate_hole_pattern_mm=p['root_interface_holes_mm'],backing_plate_plan_extent_mm=[[0,-9],[24,9]],robot_hub_interface_released=False)
 # Measurement examples, not asserted supplier tolerances.
 stack=[]
 for cover in [2.4,2.5,2.6]:
  for flange in [.35,.4,.45]:
   gap=8.4-(5.5+cover);delta=flange-gap
   stack.append(dict(cover_mm=cover,flange_mm=flange,retainer_gap_mm=gap,compression_if_retainer_metal_seated_mm=delta,interpretation='zero preload' if abs(delta)<1e-9 else 'loose gap' if delta<0 else 'requires compression / unknown stress'))
 # Sensitivity model: a simply supported strip and central point load.
 # Actual plate support, load patch, creep and material lower bound remain unknown.
 flex=[]
 for kind,force,span in [('upper',27.07,35.6),('upper-wing',27.07,22.6),('lower',21.96,30.6)]:
  for width in [5,10,20]:
   E=2350.;t=2.5;I=width*t**3/12;delta=force*span**3/(48*E*I)
   # Independent SI calculation checks N/mm^2, mm -> N/m^2, m.
   delta_si=force*(span*.001)**3/(48*(E*1e6)*(width*.001)*(t*.001)**3/12)*1000
   assert abs(delta-delta_si)<1e-12
   flex.append(dict(kind=kind,force_N=force,span_mm=span,effective_strip_width_mm=width,E_typical_reference_MPa=E,t_mm=t,deflection_mm=delta,nominal_LED_gap_mm=.3,residual_gap_mm=.3-delta,not_a_plate_solution_or_bound=True))
 r=dict(revision='R5-PETAL-HW01',license='CC-BY-NC-4.0',source_hashes=sources,geometry_units='mm',inspection_scope='Frozen right-hand isolated petals; left-hand reflects Y. No new CAD exported. Tool cylinders are allocations, not selected real tools. No assembled linkage clearance inferred.',fastener_probes=rows,root_bench_stack=rootstack,M2_stack=dict(screw_catalogue='Accu SIK-M2-12-A2 / separate Wurth 004802 12 alternative',head_D_mm=[3.5,3.8],catalogue_H_mm=1.2,ideal_cone_head_top_z_mm=8.8,hypothetical_edge_land_mm=[0,.3],hypothetical_head_top_z_mm=[8.8,9.1],hypothetical_profile_is_not_vendor_geometry=True,washer_z_mm=[-.3,0],nut_z_mm=[-1.9,-.3],tip_z_mm_under_hypothetical_head_range=[-3.2,-2.9],tail_beyond_nut_mm=[1.,1.3],final_head_top_qualified=False,thread_effective_tip_runout_unknown=True),flange_stack_sensitivity_not_supplier_tolerances=stack,strip_bending_sensitivity=flex,load_reference=dict(upper_normal_N=27.07,lower_normal_N=21.96,lever_mm=65,upper_moment_Nm=27.07*.065,lower_moment_Nm=21.96*.065,conditional_mu=.4,actual_friction=None,upper_tangential_reference_N=.4*27.07,lower_tangential_reference_N=.4*21.96),qualified=dict(procurement_stock=False,real_fastener_tolerance_stack=False,skin_retention=False,material_wear=False,cover_load_deflection=False,payload=False,one_second_cycle=False,manufacturing=False))
 put(r);print(json.dumps({'probe_count':len(rows),'min_rear_tool_to_nut_gap_mm':min(r['rear_tool_to_other_nut_circumscribed_gap_mm'] for r in rows if 'index' in r),'strip_deflection_mm':[round(x['deflection_mm'],4) for x in flex]},indent=2))
if __name__=='__main__':main()
