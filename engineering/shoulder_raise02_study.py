#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""SHOULDER-RAISE02: rearward ribs and remote steel thread blocks. Research only."""
from pathlib import Path
import sys, json, math, argparse, itertools
import numpy as np
import cadquery as cq
import shoulder_raise_study as r1
import shoulder_raise_strength as strength
from shoulder_raise_study import ROOT,WORK,NOTICE,sha,frame,moved,ring,bores,cylinder,bbox,comp,check,cache,properties,aggregate
OUT=ROOT/'engineering/generated/shoulder-raise02'
REV='SHOULDER-RAISE02';Z2=205.;T2=frame([0,0,Z2],[0,1,0])
def dump(n,d):OUT.mkdir(parents=True,exist_ok=True);(OUT/n).write_text(json.dumps(d,indent=2)+'\n')
def radial_box(r0,r1,t,y0,y1,angle):
 s=bbox(r1-r0,2*t,y1-y0,[(r0+r1)/2,0,(y0+y1)/2])
 return moved(s.rotate((0,0,0),(0,0,1),angle),T2)
def rounded_prism(r0,r1,t,y0,y1,radius):
 s=bbox(r1-r0,2*t,y1-y0,[(r0+r1)/2,0,(y0+y1)/2]);edges=[e for e in s.Edges() if abs(e.BoundingBox().zlen-(y1-y0))<1e-6]
 return s.fillet(radius,edges)
def make_parts(iface):
 fp=np.array([q['xy_mm'] for q in iface['fixed_through_holes']['points']]);rear=moved(ring(64,47.7,-69.7,24).val(),T2).intersect(bbox(220,240,200,[0,-45,248.2]))
 for x in [-57,57]:
  rear=rear.fuse(bbox(16,51.7,49,[x,-43.85,151.7]))
  rear=rear.fuse(bbox(16,24,77.8,[x,-57.7,166.1]))
 rear=rear.clean()
 # The concave front-leg / taller rear-column transitions are real R2 fillets.
 edges=[e for e in rear.Edges() if e.geomType()=='LINE' and abs(e.Center().y+45.7)<1e-5 and abs(e.Center().z-176.2)<1e-5 and abs(e.Length()-16)<1e-5]
 assert len(edges)==2,[(e.Center().toTuple(),e.Length()) for e in rear.Edges() if e.geomType()=='LINE']
 rear=rear.fillet(2,edges).clean()
 axial_ring=moved(ring(64,47.7,-104.5,34.8).val(),T2)
 blocks={};keys={};ribs=[]
 for i,(x,y) in enumerate(fp):
  a=math.degrees(math.atan2(y,x));rib=axial_ring.intersect(radial_box(40,67,7,-104.5,-69.7,a));rear=rear.fuse(rib);ribs.append(rib)
  # Rounded rectangular custom nut block, axis radial / tangential / J2 axial.
  s=bbox(30,14,8,[49,0,-108.5]);vertical=[e for e in s.Edges() if abs(e.BoundingBox().zlen-8)<1e-6];s=s.fillet(2,vertical)
  s=s.fuse(rounded_prism(55,64,5,-104.5,-102.5,1))
  s=s.cut(cylinder([51,0,-113],[0,0,1],1.65,12)).clean()
  block=moved(s.rotate((0,0,0),(0,0,1),a),T2);blocks[f'STEEL_THREAD_BLOCK_{i+1}']=block
  # Rear-open pocket: tab supplies antirotation only; preload/contact not solved.
  cut=moved(rounded_prism(54.8,65.2,5.2,-104.6,-102.3,1.2).rotate((0,0,0),(0,0,1),a),T2);rear=rear.cut(cut)
  keys[f'STEEL_THREAD_BLOCK_{i+1}']=cut
 rear=rear.clean();ribroots=[e for e in rear.Edges() if e.geomType()=='LINE' and abs(e.Center().y+69.7)<1e-5 and 15<e.Length()<19 and 51<math.hypot(e.Center().x,e.Center().z-205)<60]
 assert len(ribroots)==14,len(ribroots)
 rear=rear.fillet(.8,ribroots).clean()
 rear=rear.cut(moved(bores(fp.tolist(),2.25,-105,61).val(),T2))
 rear=rear.cut(bores(r1.l12.POST_XY.tolist(),2.5,126.2,16).val()).clean()
 assert rear.isValid() and len(rear.Solids())==1
 for n,s in blocks.items():assert s.isValid() and len(s.Solids())==1,n
 return rear,blocks,fp,dict(real_front_leg_transition_radius_mm=2,real_axial_rib_root_radius_mm=.8,real_rib_root_fillets=14,key_radius_mm=1,key_pocket_radius_mm=1.2,rear_collar_thickness_mm=24,rear_columns_mm=[16,24,77.8],front_legs_mm=[16,51.7,49],axial_compression_rib_length_mm=34.8,radial_OD_mm=128,maximum_X_width_mm=130,thread_block_envelope_radial_tangent_axial_mm=[30,14,10],thread_block_main_Y_mm=[-112.5,-104.5],thread_block_outer_key_Y_mm=[-104.5,-102.5],nominal_thread_engagement_mm=7,thread_major_min_ligament_mm=5,aluminum_clearance_bore_inner_ligament_mm=1.05)
def setup_candidate():
 p,rows,hashes,vendor,iface,h12,h23,rebuild=r1.setup(r1.default_paths());moving,fixed,own=r1.candidate(35,rows,iface,h12,h23)
 rear,blocks,fp,dimensions=make_parts(iface);fixed['L12_rear_fork']=rear;fixed.update(blocks)
 for n in list(fixed):
  if n.startswith('L12_HW_FIX_'):del fixed[n]
 for i,(x,y) in enumerate(fp):
  seat=(T2@np.array([x,y,-11.5,1]))[:3];head=cylinder(seat,[0,1,0],3.61,4);shaft=cylinder(seat,[0,-1,0],2,100)
  fixed[f'L12_HW_FIX_M4x100_PROVISIONAL_{i+1}']=head.fuse(shaft)
 return p,rows,hashes,vendor,iface,h12,h23,moving,fixed,own,dimensions

def quick(p,rows,hashes,vendor,iface,h12,h23,moving,fixed,own,dimensions):
 targets={n:s for n,s in fixed.items() if n in ['L12_output_adapter','L12_rear_fork','L12_front_ring','J1'] or n.startswith('STEEL_')};targets['J2']=own
 qs={a+'__'+b:check(s,targets[b],minimum=True) for a,s in targets.items() for b in targets if a<b}
 # Thread-owner contact is excluded only by removing exactly the engagement segment.
 for n,s in fixed.items():
  if n.startswith('L12_HW_FIX_'):
   i=int(n.rsplit('_',1)[1]);owner=f'STEEL_THREAD_BLOCK_{i}';fp=np.array(iface['fixed_through_holes']['points'][i-1]['xy_mm']);seat=(T2@np.r_[fp,-11.5,1])[:3];free=cylinder(seat,[0,1,0],3.61,4).fuse(cylinder(seat,[0,-1,0],2,93))
   for b,t in targets.items():qs[n+'__'+b]=check(free if b==owner else s,t)
 for row in h12[3]:
  n=row['id']
  if n.startswith('FIX_'):continue
  owner='L12_'+row['thread_owner'] if row['thread_owner'] in ['rear_fork','output_adapter'] else row['thread_owner']
  for b,t in targets.items():qs['L12_HW_'+n+'__'+b]=check(h12[1][n] if b==owner else h12[0][n],t)
 dump('geometry-first.json',dict(revision=REV,dimensions=dimensions,static=qs,events={n:q for n,q in qs.items() if q['events']},candidate_only=True));print('static events',[(n,q['solid_pair_intersection_sum_mm3']) for n,q in qs.items() if q['events']],flush=True)
 return qs

def remote_block_paths(fixed,own,iface):
 fp=np.array([q['xy_mm'] for q in iface['fixed_through_holes']['points']]);results={};contain=[]
 present={n:s for n,s in fixed.items() if not n.startswith('L12_HW_FIX_')};present['J2']=own
 for i,(x,y) in enumerate(fp):
  n=f'STEEL_THREAD_BLOCK_{i+1}';a=math.degrees(math.atan2(y,x))
  # Filled-hole bounding prism is conservative for a rearward 60 mm translation.
  sweep=moved(rounded_prism(34,64,7,-172.5,-104.5,2).fuse(rounded_prism(55,64,5,-164.5,-102.5,1)).rotate((0,0,0),(0,0,1),a),T2)
  for s in fixed[n].Solids():assert sum(abs(t.Volume()) for t in s.cut(sweep).Solids())<1e-4
  for target,s in present.items():
   if target!=n:results[n+'__'+target]=check(sweep,s)
  contain.append(dict(id=n,translation_axis_world=[0,-1,0],travel_mm=[0,60],filled_hole_prism_contains_source=True))
 return dict(block_paths=contain,checks=results,events={n:q for n,q in results.items() if q['events']},scope='Continuous conservative union for each one-at-a-time rearward block insertion. Other blocks, OEM motor, all originals and nonFIX hardware present. Block must be held until its screw starts; no self-retaining claim.')

def mass_export(fixed,hashes):
 instances={};assembly=cq.Assembly(name=REV+'-original-only');originals=[n for n in fixed if n in ['L12_output_adapter','L12_rear_fork','L12_front_ring'] or n.startswith('STEEL_')]
 for n in originals:
  s=fixed[n];steel=n.startswith('STEEL_');q=properties(s,material='42CrMo4+QT_round_bar_candidate' if steel else '6061-T6_billet_candidate',rho=7.85e-6 if steel else 2.7e-6)
  file=n+'.step';cq.exporters.export(s,str(OUT/file));rt=cq.importers.importStep(str(OUT/file)).val();assert rt.isValid() and len(rt.Solids())==1;assert abs(rt.Volume()-s.Volume())<1e-4
  q.update(file=file,sha256=sha(OUT/file),T_world_from_part_mm=np.eye(4).tolist(),source_frame='World-home mm, preceding_joints1; no extra translation or rotation',STEP_reimport_volume_error_mm3=abs(rt.Volume()-s.Volume()));instances[n]=q;assembly.add(s,name=n)
 for n,s in fixed.items():
  if n.startswith('L12_HW_'):assembly.add(s,name=n)
 assembly.save(str(OUT/'SHOULDER-RAISE02-original-assembly.step'))
 total=aggregate(list(instances.values()));total['mass_basis']='Mixed uniform original6061 and steel CAD; excludes all screws and OEM.'
 old=json.loads((ROOT/'engineering/generated/shoulder-raise-01/part-placements.json').read_text())
 screwproxy=sum(properties(s,'uniform_steel_envelope_proxy',7.85e-6)['mass_kg'] for n,s in fixed.items() if n.startswith('L12_HW_FIX_'))
 result=dict(revision=REV,instances=instances,aggregate_original_metal=total,previous_RAISE01_original_metal=old['new_L12_original_aggregate'],delta_original_metal_kg=total['mass_kg']-old['L12_original_metal_mass_kg'],M4x100_eight_smooth_envelope_mass_proxy_kg=screwproxy,hardware_budget_policy='New steel thread blocks are original parts counted exactly once in metal aggregate. Existing0.20kg fastener reserve is NOT recomputed or approved; new100mm screw catalog mass/grade/PN unverified. Do not add this smooth-envelope estimate on top of a reserve without replacing its allocated screws.',all_other_local_geometry_unchanged=True,J2_origin_world_mm=[0,0,205],source_hashes=hashes,manufacturing_release=False)
 dump('part-placements.json',result);return result

def section_comparison(fixed):
 prior=json.loads((ROOT/'engineering/generated/shoulder-raise-strength01/sections.json').read_text());study=json.loads((ROOT/'engineering/generated/shoulder-raise-strength01/study.json').read_text());zs=[x['z_mm'] for x in prior['slices']['raised77_8']];new=[]
 for i,z in enumerate(zs):
  new.append(net_section(fixed['L12_rear_fork'],z))
  if i%30==0:print('actual net slice',i,len(zs),flush=True)
 rows={};end=[0,-45.7,205]
 for name,ss in [('RAISE01',prior['slices']['raised77_8']),('RAISE02',new)]:
  rows[name]={}
  for kind in ['composite','uncoupled']:
   C=strength.beam_compliance(ss,end,kind=kind);coarse=strength.beam_compliance(ss[::2],end,kind=kind);active=abs(C)>1e-6
   q=dict(compliance_mm_rad_per_N_Nmm=C.tolist(),coarse_refinement_max_active_relative_difference=float(np.max(abs((C-coarse)[active]/C[active]))),examples={})
   for j,axis in enumerate('XY'):
    W=np.zeros(6);W[3+j]=100000;q['examples']['100Nm_'+axis]=(C@W).tolist()
   for k in ['nominal','expanded']:
    b=study['gravity_bounds']['interfaces']['J2_rear'];F=b['nominal_vertical_force_N'] if k=='nominal' else b['expanded_force_N'];M=b['nominal_moment_norm_bound_Nm'] if k=='nominal' else b['expanded_moment_bound_Nm'];q[k]=strength.exact_direction_stress_bound(ss,F,M,end,kind)
   rows[name][kind]=q
  cc=np.array(rows[name]['composite']['compliance_mm_rad_per_N_Nmm']);cu=np.array(rows[name]['uncoupled']['compliance_mm_rad_per_N_Nmm']);assert min(np.linalg.eigvalsh(cu-cc))>-1e-8
 # Same elementary verification as strength01, independently evaluated here.
 E=70000.;I=100000.;L=77.8;uniform=[dict(z_mm=z,area_mm2=1000.,centroid_world_mm=[0,0,z],Q_composite_mm4=[[I,0],[0,I]]) for z in np.linspace(0,L,1001)];C=strength.beam_compliance(uniform,[0,0,L]);assert abs(C[0,0]/(L**3/(3*E*I))-1)<1e-6
 result=dict(revision=REV,actual_span_mm=77.8,actual_net_slices=new,comparison=rows,J2_side_load_unchanged=study['gravity_bounds']['interfaces']['J2_rear'],scope='Same frozenJ2 side loads and same157 heights. New fork/steel-block selfweight not distributed into beam. Global foot/J1 forces must be updated separately. Two beam references, not true3D bounds or FEA; no torsional/shear/contact compliance.',yield_applied_MPa=None,unit_check=True)
 dump('section-comparison.json',result);return result

def net_section(shape,z):
 """Compute per-island area tensors first; independently check the whole slice.

 Summing positive parallel-axis contributions avoids subtracting two nearly
 equal large global tensors to establish the energy order of a one-island slice.
 """
 t=.001;slab=shape.intersect(bbox(300,300,t,[0,0,z]));assert slab.Solids();islands=[];Qu=np.zeros((2,2))
 for s in slab.Solids():
  q=strength.GProp_GProps();strength.BRepGProp.VolumeProperties_s(s.wrapped,q);A=q.Mass()/t;c=np.array(q.CentreOfMass().Coord());I=q.MatrixOfInertia();Q=np.array([[I.Value(2,2),-I.Value(1,2)],[-I.Value(1,2),I.Value(1,1)]])/t-np.eye(2)*A*t*t/12;bb=s.BoundingBox();assert A>0 and min(np.linalg.eigvalsh(Q))>0;Qu+=Q
  islands.append(dict(area_mm2=A,centroid_world_mm=c.tolist(),Q_area_mm4=Q.tolist(),relative_bbox_xy_mm=[[bb.xmin-c[0],bb.ymin-c[1]],[bb.xmax-c[0],bb.ymax-c[1]]]))
 A=sum(q['area_mm2'] for q in islands);c=sum(q['area_mm2']*np.array(q['centroid_world_mm']) for q in islands)/A;D=sum((q['area_mm2']*np.outer(np.array(q['centroid_world_mm'])[:2]-c[:2],np.array(q['centroid_world_mm'])[:2]-c[:2]) for q in islands),np.zeros((2,2)));Q=Qu+D
 g=strength.GProp_GProps();strength.BRepGProp.VolumeProperties_s(slab.wrapped,g);I=g.MatrixOfInertia();direct=np.array([[I.Value(2,2),-I.Value(1,2)],[-I.Value(1,2),I.Value(1,1)]])/t-np.eye(2)*g.Mass()/t*t*t/12
 error=float(np.max(abs(Q-direct)));relative=error/max(float(np.max(abs(direct))),1.);area_error=abs(g.Mass()/t-A)/A;assert relative<1e-6,(z,error,relative);assert area_error<1e-7,(z,area_error);assert np.linalg.norm(c-np.array(g.CentreOfMass().Coord()))<1e-5;assert min(np.linalg.eigvalsh(D))>-1e-8*max(float(np.max(abs(D))),1.)
 bb=slab.BoundingBox();return dict(z_mm=float(z),area_mm2=A,centroid_world_mm=c.tolist(),Q_composite_mm4=Q.tolist(),Q_no_axial_couple_mm4=Qu.tolist(),bbox_relative_xy_mm=[[bb.xmin-c[0],bb.ymin-c[1]],[bb.xmax-c[0],bb.ymax-c[1]]],islands=islands,parallel_axis_reconstruction_vs_whole_slice_absolute_mm4=error,relative_tensor_difference=relative,relative_area_reconstruction_difference=area_error)

def connections(fixed,own,iface,mass):
 contacts={};stock=[];lig=[];fps=np.array([q['xy_mm'] for q in iface['fixed_through_holes']['points']]);Ntotal=22322.0;P=Ntotal/8
 for i,(x,y) in enumerate(fps):
  n=f'STEEL_THREAD_BLOCK_{i+1}';a=math.degrees(math.atan2(y,x));normal=[0,1,0];o=(T2@np.r_[x,y,-104.5,1])[:3];contact=r1.face_contact(fixed[n],fixed['L12_rear_fork'],o.tolist(),normal);assert contact['shared_planar_face_area_mm2']>20;area=contact['shared_planar_face_area_mm2'];contacts[n]=dict(**contact,conditional_equal_share_preload_N=P,conditional_average_contact_pressure_MPa=P/area,preload_is_not_selected=True)
  # Entire custom part lies in a certified-size-band raw round bar, not the final8mm thickness.
  blank=radial_box(24,74,25,-114,-100,a) # enclosing box only for inspection; real cylindrical blank below
  b=moved(cylinder([49,0,-114],[0,0,1],25,14).rotate((0,0,0),(0,0,1),a),T2);outside=sum(abs(q.Volume()) for q in fixed[n].cut(b).Solids());assert outside<1e-4;stock.append(dict(id=n,round_blank_diameter_mm=50,length_mm=14,axis_world=[0,1,0],outside_blank_volume_mm3=outside))
  s=fixed[n];motor=check(s,own,minimum=True);lig.append(dict(id=n,thread='M4x0.7',pilot_diameter_mm=3.3,major_diameter_mm=4,nominal_entered_length_mm=7,first_last_full_thread_TBD=True,minimum_rectangular_side_major_ligament_mm=5,motor_clearance_mm=motor['minimum_BREP_surface_distance_mm']))
 # Actual compression-rib cross sections at Y=-85 include real clearance holes.
 ribslice=fixed['L12_rear_fork'].intersect(bbox(180,.001,180,[0,-85,205]));A=ribslice.Volume()/.001
 result=dict(steel_block_contacts=contacts,steel_raw_stock_containment=stock,thread_geometry=lig,aluminum_rib_combined_net_area_mm2=A,conditional_uniform_axial_compression_MPa=Ntotal/A,clamp_condition=dict(total_N=Ntotal,source='STRENGTH01 rounded independent157NmY+expandedverticalF case; mu=.15 and effectiveR51 assumed',equal_per_bolt_N=P,not_selected=True),anti_rotation_key=dict(tab_radial_mm=[55,64],tangential_width_mm=10,engagement_mm=2,pocket_side_clearance_mm=.2,approximate_torque_arm_mm=8.5,example_at4_6Nm_N=4600/8.5,example_side_bearing_MPa=(4600/8.5)/20,limits='4.6Nm is sourcecatalog plainM4 torque, NOT approved torque here. Contact location, root/notch and tightening load distribution unqualified.'),fastener=dict(M4_length_mm=100,pitch_mm=.7,head_envelope_mm=[7.22,4],length_exact_PN_and_grade_evidence=False,nominal_free_grip_mm=93,nominal_steel_engagement_mm=7,nominal_tip_to_block_rear_mm=1.0,original_catalog_M4x50_cannot_be_reused=True,thread_engagement_effective_TBD=True),material=dict(aluminum='6061-T6 billet candidate; minimum bounding stock thickness inY86.5mm plus machining allowance. No controlled thick-billet yield guarantee available, none applied.',steel='Ovako42CrMo4 M(6082)/MoC410M +QT round bar40<D<100; use originalD50 bar, storedprimarysource Rel>=650MPa conditional on batch certificate. Not generic4140 guarantee.',steel_source='docs/engineering/sources/p16-carrier02.json',steel_density_used_kg_m3=7850),scope='Geometric bearing surfaces and nominal equal-share compression, not preload distribution/thread stripping/contact stiffness/fatigue qualification.')
 dump('connections.json',result);return result

def draw(fixed,sections,mass):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.collections import PolyCollection
 from matplotlib.patches import Circle,Rectangle
 colors={'L12_output_adapter':'#427a9b','L12_rear_fork':'#63a496','L12_front_ring':'#e0ad5f'}
 fig,axes=plt.subplots(1,3,figsize=(16,7));projections=[np.array([[1,0,0],[0,0,1]]),np.array([[0,1,0],[0,0,1]]),np.array([[.78,-.63,0],[.30,.37,.88]])]
 for ai,(ax,P) in enumerate(zip(axes,projections)):
  for n,s in fixed.items():
   if n not in colors and not n.startswith('STEEL_'):continue
   vv,ff=s.tessellate(.15,.14);v=np.array([q.toTuple() for q in vv]);v[:,2]-=100;tri=(v@P.T)[np.array(ff)]
   ax.add_collection(PolyCollection(tri,facecolors=colors.get(n,'#45515e'),edgecolors='none',alpha=.88,rasterized=True))
  ax.autoscale();ax.set_aspect('equal');ax.grid(alpha=.15);ax.set(xlabel=['X / mm','Y / mm','Projected mm'][ai],ylabel=['Z - 100 / mm','Z - 100 / mm','Projected mm'][ai],title=['FRONT | unchanged130mm width','SIDE | extra rearward structure','AXONOMETRIC | original solids only'][ai])
 axes[0].add_patch(Circle((0,105),85,fill=False,ls='--',color='#bd5339'));axes[0].set_ylim(0,198);axes[0].text(-84,187,'R85 invariant moving enclosure',fontsize=8,color='#bd5339');axes[0].annotate('J2 Z205 unchanged',xy=(0,105),xytext=(-80,160),arrowprops=dict(arrowstyle='-'),fontsize=9)
 axes[1].set_xlim(-125,10);axes[1].set_ylim(0,198);axes[1].axvline(-3.5,color='#bd5339',ls='--');axes[1].annotate('Steel thread blocks\nY -112.5...-104.5',xy=(-109,134),xytext=(-121,184),arrowprops=dict(arrowstyle='-'),fontsize=9)
 axes[1].annotate('Rear collar24mm\n2 rear columns77.8mm',xy=(-59,72),xytext=(-119,16),arrowprops=dict(arrowstyle='-'),fontsize=9);axes[1].annotate('Front side retained\nminimum gap4.000mm',xy=(-7.5,147),xytext=(-85,170),arrowprops=dict(arrowstyle='-'),fontsize=9)
 axes[2].text(.02,.02,f"Original metal {mass['aggregate_original_metal']['mass_kg']:.3f}kg\nChange +{mass['delta_original_metal_kg']:.3f}kg vsRAISE01",transform=axes[2].transAxes,fontsize=10)
 fig.suptitle('SHOULDER-RAISE02 | thicker rear load path + remote steel thread blocks',fontsize=15);fig.text(.04,.018,'Nominal CAD / local motion evidence. M4x100 procurement, preload, thick-billet properties and whole-part strength remain open. No FEA.',fontsize=10);fig.tight_layout(rect=[0,.075,1,.95]);fig.savefig(OUT/'shoulder-raise02.png',dpi=165);fig.savefig(OUT/'shoulder-raise02.svg');plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(11,4.5))
 for kind,color in [('composite','#518e83'),('uncoupled','#c08b48')]:
  labels=['RAISE01','RAISE02'];axes[0].plot(labels,[sections['comparison'][n][kind]['expanded']['nominal_stress_MPa'] for n in labels],'-o',label=kind,color=color)
  axes[1].plot(labels,[abs(sections['comparison'][n][kind]['examples']['100Nm_X'][1]) for n in labels],'-o',label=kind,color=color)
 axes[0].set(ylabel='Nominal stress / MPa',title='Same conditional expanded gravity input');axes[1].set(ylabel='Reference lateral displacement / mm',title='Same100Nm aboutX input')
 for a in axes:a.grid(alpha=.2);a.legend()
 fig.suptitle('Conditional beam references / real net sections /77.8mm span');fig.tight_layout();fig.savefig(OUT/'section-comparison.png',dpi=160);plt.close(fig)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--quick',action='store_true');args=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True)
 data=setup_candidate();qs=quick(*data)
 p,rows,hashes,vendor,iface,h12,h23,moving,fixed,own,dimensions=data
 for n in ['L12_rear_fork',*[q for q in fixed if q.startswith('STEEL_')]]:cq.exporters.export(fixed[n],str(OUT/(n+'.step')))
 if args.quick:return
 assert not any(q['events'] for q in qs.values())
 for rel in ['engineering/shoulder_raise02_study.py','engineering/shoulder_raise_study.py','engineering/shoulder_raise_strength.py','engineering/generated/shoulder-raise-01/qa.json','engineering/generated/shoulder-raise-01/part-placements.json','engineering/generated/shoulder-raise-strength01/study.json','engineering/generated/shoulder-raise-strength01/sections.json','engineering/generated/raised-arm-integration01/model.json','docs/engineering/sources/p16-carrier02.json','docs/engineering/sources/gripper-root-support.json']:
  hashes[rel]=sha(ROOT/rel)
 print('full invariant domain',flush=True);proof,full,exposed=r1.invariant_proof(35,moving,fixed,own);dump('continuous-motion.json',proof);assert proof['all_full_moving_external_certified'] and proof['own_J2_exposed_no_positive_volume'];assert proof['minimum_external_envelope_gap_mm']>3.9999
 print('assembly',flush=True);paths=r1.assembly_paths(35,fixed,own,h12);dump('assembly-paths.json',paths);assert not paths['events'] and not any(p['collisions'] for p in paths['other_insertions'])
 bp=remote_block_paths(fixed,own,iface);dump('steel-block-paths.json',bp);assert not bp['events']
 mass=mass_export(fixed,hashes);con=connections(fixed,own,iface,mass);sec=section_comparison(fixed);draw(fixed,sec,mass)
 # Capture the rejected nearby washer/socket route against each actual OEM solid.
 rejected={}
 for i,p in enumerate(iface['fixed_through_holes']['points']):
  x,y=p['xy_mm'];s=moved(cylinder([x,y,-65],[0,0,1],4.6,13),T2);rejected[str(i+1)]=check(s,own,minimum=True)
 result=dict(revision=REV,license='CC-BY-NC-4.0',required_notice=NOTICE,source_hashes=hashes,vendor_sources=vendor,dimensions=dimensions,original_metal=mass['aggregate_original_metal'],delta_original_metal_kg=mass['delta_original_metal_kg'],continuous_local_q2_deg=[-90,90],minimum_external_envelope_gap_mm=proof['minimum_external_envelope_gap_mm'],rejected_nearby9_2mm_diameter_probe=rejected,selected_geometry='Rear24mm collar +2straight rearcolumns +8axial compression ribs +8remote custom steel thread blocks. Forward existing flange, hole positions, J1 contact and all downstream geometry unchanged.',fastener_procurement_closed=False,manufacturing_release=False,physical_payload_qualified=False,FEA_performed=False,exclusions=['Cables/connectors/internalOEM ownership','Thick-billet strength guarantee','M4x100 precise approvedPN/grade and tolerances','Actual clamp/contact/friction/settlement and bolt fatigue','OEMoutputM4 effective threads and length','Full-arm dynamics and complete newselfweight force-flow','Continuous disassembly with downstreamJ3 installed'])
 dump('study.json',result);unchanged={n:sha(ROOT/n)==h for n,h in hashes.items()};assert all(unchanged.values())
 dump('qa.json',dict(revision=REV,generator_sha256=sha(__file__),source_integrity=unchanged,geometry_static_no_positive_volume=True,continuous_local_motion_preserved=True,minimum_external_gap_mm=proof['minimum_external_envelope_gap_mm'],continuous_motor_insertion=True,continuous_steel_block_insertions=True,other_three_insertions_discrete_only=True,all_exported_originals_STEP_reimport_passed=True,actual_net_slice_unit_check=True,full_manufacturing_or_strength_release=False,artifacts={p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name not in ['qa.json','run.log','probe.py']}));print('READY',mass['aggregate_original_metal'],flush=True)
if __name__=='__main__':main()
