#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Nominal section demands, not strength/life qualification. Units N, mm, MPa."""
import json,math,hashlib
from pathlib import Path
import numpy as np
import cadquery as cq
import p16_carrier02_study as c2
st,p16,c01=c2.st,c2.p16,c2.c01
OUT,ROOT=c2.OUT,c2.ROOT

def section(shape,axis,position,h=.002):
 lo=[-250.]*3;hi=[250.]*3;lo[axis]=position-h/2;hi[axis]=position+h/2
 slab=shape.intersect(c2.B(lo[0],hi[0],lo[1],hi[1],lo[2],hi[2]));A=slab.Volume()/h;I=np.array(cq.Shape.matrixOfInertia(slab))/h;Q=np.eye(3)*np.trace(I)/2-I
 cen=np.array(slab.Center().toTuple());bb=st.bb(slab)
 return dict(area_mm2=A,centroid_mm=cen.tolist(),second_moment_tensor_mm4=I.tolist(),coordinate_second_moments_mm4=Q.tolist(),bbox_mm=[x.tolist() for x in bb],slice_solids=len(slab.Solids()),slice_h_mm=h)

def demand(sec,axis,forces,points):
 F=np.sum(forces,axis=0);M=np.sum(np.cross(np.array(points)-np.array(sec['centroid_mm']),forces),axis=0);ab=[i for i in range(3) if i!=axis];Q=np.array(sec['coordinate_second_moments_mm4'])[np.ix_(ab,ab)]
 # Solve linear axial stress from its exact force and bending moments.
 E=np.eye(3);H=np.column_stack([np.cross(E[a],E[axis]) for a in ab]);target=H.T@M;coef=np.linalg.solve(Q,target)
 corners=np.array(list(__import__('itertools').product(*zip(*np.array(sec['bbox_mm'])[:,ab]))));sig=F[axis]/sec['area_mm2']+(corners-np.array(sec['centroid_mm'])[ab])@coef
 return dict(force_N=F.tolist(),moment_about_section_centroid_Nmm=M.tolist(),normal_stress_bbox_upper_MPa=float(max(abs(sig))),average_transverse_shear_MPa=float(np.linalg.norm(F[ab])/sec['area_mm2']),torsion_Nmm=float(M[axis]),note='Linear nominal bending over exact net area/inertia; bounding-box corners overbound stresses. Hole/fillet concentrations, shear-lag, clamp contact and local warping excluded.')

def rot(q):
 t=math.radians(q);return np.array([[math.cos(t),0,-math.sin(t)],[0,1,0],[math.sin(t),0,math.cos(t)]])

def reactions(forces,points,couple=None):
 S=np.sum(forces,axis=0);M=np.sum(np.cross(points,forces),axis=0)+(np.array(couple) if couple is not None else 0);a,b=19.,29.;d=b-a
 A=np.array([-(b*S[0]+M[2])/d,0.,(M[0]-b*S[2])/d]);B=np.array([(a*S[0]+M[2])/d,0.,(a*S[2]-M[0])/d]);rf=A+B+S;rm=np.cross([0,a,0],A)+np.cross([0,b,0],B)+M
 assert np.max(abs(rf[[0,2]]))<1e-8 and np.max(abs(rm[[0,2]]))<1e-7
 return dict(bearing_u19_radial_vector_N=A.tolist(),bearing_u29_radial_vector_N=B.tolist(),radial_magnitudes_N=[float(np.linalg.norm(A)),float(np.linalg.norm(B))],axial_sum_required_N=float(-S[1]),axial_sharing='Unresolved: either bearing may have to take full axial magnitude. Geometric centers are not 40deg pressure centers.',residual_force_after_radial_N=rf.tolist(),residual_moment_after_radial_Nmm=rm.tolist())

def main():
 OUT.mkdir(parents=True,exist_ok=True);contact_path=ROOT/'engineering/generated/contact02-study/study.json';linear_path=ROOT/'engineering/generated/linear-drive-study/study.json';ct=json.loads(contact_path.read_text());f=ct['fingers'];parts,mat=c2.root_parts(f[0]);old,_=c01.root_parts(f[0]);sec={}
 specs=[('bridge_u_minus15','integral_steel_crank_spindle',1,-15.),('bridge_u_minus5p1','integral_steel_crank_spindle',1,-5.1),('bridge_overlap_u_minus4p9','integral_steel_crank_spindle',1,-4.9),('shaft_u5p1','integral_steel_crank_spindle',1,5.1),('shaft_u11p9','integral_steel_crank_spindle',1,11.9),('steel_fork_x17p1','integral_steel_crank_spindle',0,17.1),('steel_fork_M2_x18p5','integral_steel_crank_spindle',0,18.5),('steel_fork_M3_x21','integral_steel_crank_spindle',0,21.),('blade_M3_x21','metal_blade_with_narrow_tongue',0,21.),('blade_neck_x24','metal_blade_with_narrow_tongue',0,24.),('upper_cap_M3_x21','removable_upper_fork',0,21.)]
 # Resolve actual inherited upper cap name without assuming a previous nickname.
 cap=next(k for k in parts if 'upper' in k and 'fork' in k);specs[-1]=(specs[-1][0],cap,0,21.)
 for name,p,ax,pos in specs:
  s=section(parts[p],ax,pos);half=section(parts[p],ax,pos,.001);delta=abs(s['area_mm2']-half['area_mm2'])
  assert delta/max(s['area_mm2'],1)<1e-4
  sec[name]=dict(part=p,normal_axis='xuz'[ax],position_mm=pos,**s,half_step_area_relative_change=delta/s['area_mm2'])
 # Reverse/unit tests: rectangle and circular shaft; no polar-I torsion substitution for rectangles.
 assert abs(sec['bridge_u_minus15']['area_mm2']-56)<1e-6
 assert abs(sec['bridge_u_minus15']['second_moment_tensor_mm4'][0][0]-7*8**3/12)<1e-4
 assert abs(sec['shaft_u11p9']['area_mm2']-math.pi*6**2)<1e-6
 assert abs(sec['blade_M3_x21']['area_mm2']-(18-2*3.4)*6)<1e-5
 lc=next(c for c in json.loads(linear_path.read_text())['grasp_cases'] if c['diameter_mm']==80 and c['z_limits_mm'] is None);w=next(x for x in lc['cases'] if x['axial_force_cap_N']==300 and x['mu']==.4);cc=next(c for c in ct['contact_cases'] if c['diameter_mm']==80 and c['z_limits_mm'] is None)
 cases=[];steel=[]
 for i,ff in enumerate(f):
  pp,mm=c2.root_parts(ff);q=lc['q_deg'][i];Rq=rot(q);a=math.radians(ff['phi_deg']);er=np.array([math.cos(a),math.sin(a),0]);et=np.array([-math.sin(a),math.cos(a),0])*st.SIGNS[i];Z=np.array([0,0,1]);H=np.vstack([er,et,Z]);root=np.array([70*math.cos(a),70*math.sin(a),ff['root_z_mm']]);pts=[];forces=[]
  for j,name in enumerate(['pad_minus','pad_plus']):
   pts.append(H@(np.array(cc['fingers'][i]['components'][name]['point_head_mm'])-root));forces.append(H@(-np.array(w['forces_on_object_N'][2*i+j])))
  # Rotating original metal mass only; fixed bearings/actuator excluded. Distal LED/pad additions still absent.
  massrows=[]
  for k,s in pp.items():
   if mm[k]=='optical_placeholder':continue
   mass=3.5 if k=='tip_SBSM_pin' else 2. if k=='MB1' else 6. if k=='KM1' else s.Volume()*st.DENSITY[mm[k]]
   massrows.append((mass,np.array(s.Center().toTuple())))
  mass=sum(m for m,p in massrows);cog=sum(m*p for m,p in massrows)/mass;gforce=np.array([0,0,-mass/1000*9.80665]);gpt=Rq@cog
  externalF=np.array(forces+[gforce]);externalP=np.array(pts+[gpt]);A,B,L,_=p16.kin(q);v=(B-A)/L;unitmoment=np.cross(B,v)[1];need=sum(np.cross(externalP,externalF))[1];ideal=-need/unitmoment;eta=.85;F=ideal/eta;loss=[0,-(1-eta)*F*unitmoment,0]
  assert ideal>0
  for typ,Fuse,lossuse in [('witness_eta85',F,loss),('300N_plus_same_contacts',300.,None)]:
   ffload=np.vstack([externalF,Fuse*v]);ppload=np.vstack([externalP,B]);rx=reactions(ffload,ppload,lossuse)
   if lossuse is not None:assert abs(rx['residual_moment_after_radial_Nmm'][1])<1e-7
   rootF=ffload@Rq;rootP=ppload@Rq
   # For a cut before the near bearing, use only the actual negative-u side.
   belowF=[];belowP=[]
   for k,s in pp.items():
    if mm[k]=='optical_placeholder':continue
    piece=s.intersect(c2.B(-250,250,-250,11.9,-250,250))
    if piece.Volume()<1e-9:continue
    catalog=3.5 if k=='tip_SBSM_pin' else 2. if k=='MB1' else 6. if k=='KM1' else None
    mg=piece.Volume()*st.DENSITY[mm[k]] if catalog is None else catalog*piece.Volume()/s.Volume()
    belowF.append(np.array([0,0,-mg/1000*9.80665])@Rq);belowP.append(np.array(piece.Center().toTuple()))
   shaftF=np.vstack([rootF[:2],rootF[-1],belowF]);shaftP=np.vstack([rootP[:2],rootP[-1],belowP])
   dshaft={name:demand(sec[name],1,shaftF,shaftP) for name in ['shaft_u11p9']}
   for name,d in dshaft.items():
    bending=np.linalg.norm(np.array(d['moment_about_section_centroid_Nmm'])[[0,2]]);T=abs(d['torsion_Nmm']);N=abs(d['force_N'][1]);sigma=32*bending/(math.pi*12**3)+N/(math.pi*12**2/4);tau=16*T/(math.pi*12**3)+4/3*d['average_transverse_shear_MPa'];d.update(circular_shaft_nominal_normal_MPa=sigma,circular_shaft_combined_shear_upper_MPa=tau,nominal_von_mises_upper_MPa=math.sqrt(sigma*sigma+3*tau*tau),required_yield_MPa_for_factor2=2*math.sqrt(sigma*sigma+3*tau*tau))
   # Distal tongue carries contacts. Body mass beyond the cut is neglected here and separately flagged.
   cp=np.array(pts)@Rq;cf=np.array(forces)@Rq
   dblade={name:demand(sec[name],0,cf,cp) for name in ['blade_M3_x21','blade_neck_x24']}
   clampSensitivity={name:demand(sec[name],0,cf,cp) for name in ['steel_fork_M3_x21','upper_cap_M3_x21']}
   # Inscribed through-path at the overlap: no thin end-plane contact is credited.
   prism=c2.B(10,17,-29.1,5,-7.4,0)
   missing=prism.Volume()-prism.intersect(pp['integral_steel_crank_spindle']).Volume();assert abs(missing)<1e-5
   # Actual clamp edge at x25 versus bolt row x21 gives a short 4mm couple arm.
   medge=np.sum(np.cross(cp-np.array([25,0,3]),cf),axis=0);hold=abs(medge[1])/4
   cases.append(dict(finger=ff['id'],q_deg=q,case=typ,axial_actuator_force_N=Fuse,actuator_lever_mm=-unitmoment,bare_rotating_mass_g=mass,bare_rotating_COM_local_mm=cog.tolist(),gravity_scope='Current nominal rotating root/blade and modeled pins/lock hardware only. New LED stack/pad retainers not included.',witness_contact_force_local_N=forces,witness_contact_points_local_mm=pts,loss_torque_couple_Nmm=lossuse,reactions=rx,shaft_sections=dshaft,blade_sections=dblade,clamp_component_full_contact_wrench_sensitivity=clampSensitivity,minimum_bridge_inscribed_prism=dict(width_mm=7.,height_mm=7.4,u_range_mm=[-29.1,5.],volume_outside_steel_mm3=missing),clamp_screen=dict(contact_moment_about_x25_edge_Nmm=medge.tolist(),total_M3_hold_down_for_4mm_arm_N=hold,each_of_two_M3_equal_share_N=hold/2,note='Ideal contact/bolt couple only, no preload/thread/pull-through/fatigue qualification. Distal gravity omitted in tongue screen.')))
 # Continuous conservative force-direction upper bounds for the modified rectangular bridge.
 # Inscribed 7x7.4 path continues 10 mm into the hub; full load conservatively evaluated at its entry.
 # A nominal half-load from the far clevis cheek crosses u=-15.
 pin0=p16.kin(0)[1];rectdata=[]
 for label,load,uplane in [('near_full_300N',300.,-5.1),('far_half_150N',150.,-15.)]:
  sn=sec['bridge_u_minus5p1' if load==300 else 'bridge_u_minus15'];width=7.;height=7.4 if load==300 else 8.;center=np.array([13.5,uplane,-height/2]);point=pin0.copy();point[1]=-18 if load==300 else -27.1;lever=point-center;Ix=width*height**3/12;Iz=height*width**3/12
  # Max bending over arbitrary radial force direction, from corner stress coefficients.
  sigma=load*abs(lever[1])*math.sqrt((height/2/Ix)**2+(width/2/Iz)**2);Tmax=load*math.hypot(lever[0],lever[2]);k2=.208 # lower tabulated coefficient at square; conservative vs interpolated 8/7 ratio
  tauT=Tmax/(k2*width**2*height);tauV=1.5*load/(width*height);vm=math.sqrt(sigma**2+3*(tauT+tauV)**2)
  rectdata.append(dict(section=label,F_N=load,force_plane_u_mm=point[1],section_u_mm=uplane,section_width_height_mm=[width,height],net_area_mm2=width*height,bending_stress_any_radial_direction_upper_MPa=sigma,torsion_any_radial_direction_Nmm=Tmax,rectangular_torsion_k2_lower_bound=.208,torsional_shear_upper_MPa=tauT,transverse_shear_upper_MPa=tauV,nominal_von_mises_combined_upper_MPa=vm,required_yield_factor2_MPa=2*vm,limitations='Conservative inscribed rectangular prism only. Fillet/entry throat into hub/fork and warping restraint not resolved by beam formulas. This directional upper bound covers all q, not a load rating.'))
 result=dict(revision='P16-CARRIER-02',manufacturing_release=False,sources_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [contact_path,linear_path,Path(__file__)]},sections=sec,grip_witness_cases=cases,bridge_300N_continuous_force_direction_bound=rectdata,actuator_only_bearing_300N=dict(centers_u_mm=[19,29],load_u_mm=-18,radial_reaction_magnitudes_N=[1410,1110],offset_only_moment_Nm=5.4,offset_added_opposed_pair_N=540,max_unbalanced_hinge_torque_Nm=7.8),section_limits='Not all sections define a statically determinate load split: lower fork nut pockets, keeper and cap depend on bolt preload/contact. Their true net geometry is measured, not certified. No constant-section formula establishes fillet/hole fatigue or material selection.',unit_tests='7x8 area/I, D12 area, 18x6 minus two D3.4 holes, h/2 convergence, three-dimensional force and non-hinge moment residuals checked.',sources=dict(rectangle_torsion='https://live.ocw.mit.edu/courses/1-050-solid-mechanics-fall-2004/8c30fdf15d9d50c02f4215903c847d7f_emech8_04.pdf',rectangle_torsion_location='Chapter 8, printed p230, section8.5; k2 square .208 used conservatively for ratio8/7'))
 def default(o):
  if isinstance(o,np.ndarray):return o.tolist()
  if isinstance(o,np.generic):return o.item()
  raise TypeError(type(o).__name__)
 (OUT/'loads.json').write_text(json.dumps(result,indent=2,default=default)+'\n');print(json.dumps(dict(bridge=rectdata,grip=[dict(finger=x['finger'],case=x['case'],F=x['axial_actuator_force_N'],bearing=x['reactions']['radial_magnitudes_N']) for x in cases]),indent=2,default=default))
if __name__=='__main__':
 from pathlib import Path
 main()
