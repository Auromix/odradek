#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""SHOULDER-RAISE01. Original fork rebuild; frozen baseline/OEM inputs read-only."""
from pathlib import Path
import argparse,csv,hashlib,json,itertools,math
import numpy as np
import cadquery as cq
from build_layout import frame,moved
from mount_interface_study import ring,bores
from build_link56_study import cylinder,face_contact
import build_link12_study as l12
import build_link23_study as l23
from screen_integrated_collisions import load_structure,box
from studies.link_interface_tools import check,cache
from head_mass04_study import geometry_properties,unit_checks
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'engineering/generated/shoulder-raise-01'
WORK=ROOT.parents[1]/'work';NOTICE='Odradek — Auromix contributors (https://github.com/Auromix/odradek)'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(n,d):OUT.mkdir(parents=True,exist_ok=True);(OUT/n).write_text(json.dumps(d,indent=2)+'\n')
def default_paths():
 d=WORK/'r4-joints';return {'RH25-B':d/'cad25/RH-25-100-E-B-D/RH-25-100-E-B-D 3D-A0.STEP','RH20-B':d/'cad20/RH-20-100-E-B-D/RH-20-100-E-B-D 3D A.STEP','RH17-B':d/'cad17/RH-17-100-E-B-D/RH-17-100-E-B-D 3D-A.STEP','RH14-N':d/'cad14/RH-14-100-E-N-D/RH-14-100-E-N-D 3D-A0.STEP'}
def comp(ss):return cq.Compound.makeCompound(list(ss))
def bbox(x,y,z,centre):return l12.shape_box(x,y,z,centre)

def new_fork(dz,iface):
 """Rebuild analytic collar and legs, never scale/warp the old BREP."""
 fp=np.array([q['xy_mm'] for q in iface['fixed_through_holes']['points']]);T=frame([0,0,170+dz],[0,1,0])
 rear=moved(ring(64,47.7,-59.7,14).val(),T)
 rear=rear.intersect(bbox(200,200,200,[0,-45,213.2+dz]))
 for x in [-57,57]:rear=rear.fuse(bbox(16,42,14+dz,[x,-39,134.2+dz/2]))
 rear=rear.cut(moved(bores(fp.tolist(),1.65,-60,15).val(),T))
 rear=rear.cut(bores(l12.POST_XY.tolist(),2.5,126.2,16).val()).clean()
 assert rear.isValid() and len(rear.Solids())==1
 return rear

def setup(paths):
 p,rows,hashes,vendor=load_structure(paths);interfaces=json.loads((ROOT/'docs/engineering/sources/rh-interface-extraction.json').read_text());models={m['id']:m for m in interfaces['models']};i25=models['RH25-B']['unified_joint_interface'];i20=models['RH20-B']['unified_joint_interface']
 op25=np.array([q['xy_mm'] for q in i25['output_holes']['points']]);fp25=np.array([q['xy_mm'] for q in i25['fixed_through_holes']['points']]);fp20=np.array([q['xy_mm'] for q in i20['fixed_through_holes']['points']])
 h12=l12.make_hardware(op25,fp25,frame([0,0,105.2],[0,0,1]),frame([0,0,170],[0,1,0]));h23=l23.make_hardware(op25,fp20,frame([0,0,170],[0,1,0]),frame([0,55,220],[0,0,1]))
 original=new_fork(0,i25);old=rows['L12_rear_fork']['shape'];diff=original.Volume()+old.Volume()-2*original.intersect(old).Volume();assert abs(diff)<1e-3
 return p,rows,hashes,vendor,i25,h12,h23,dict(rebuilt_delta0_vs_frozen_rear_fork_symmetric_difference_mm3=diff)

def candidate(dz,rows,i25,h12,h23):
 fixed={n:r['shape'] for n,r in rows.items() if n=='J1' or n.startswith('BASE_')}
 fixed['L12_output_adapter']=rows['L12_output_adapter']['shape'];fixed['L12_rear_fork']=new_fork(dz,i25);fixed['L12_front_ring']=rows['L12_front_ring']['shape'].translate((0,0,dz))
 for n,s in h12[0].items():fixed['L12_HW_'+n]=s.translate((0,0,dz)) if n.startswith('FIX_') else s
 moving={n:r['shape'].translate((0,0,dz)) for n,r in rows.items() if n=='J3' or n.startswith('L23_')}
 moving.update({'L23_HW_'+n:s.translate((0,0,dz)) for n,s in h23[0].items()})
 own=rows['J2']['shape'].translate((0,0,dz));return moving,fixed,own

def invariant_proof(dz,moving,fixed,own):
 # Full rotating external obstacle test retains every modeled screw segment.
 z=170+dz;full=cylinder([0,-3.5,z],[0,1,0],85,113.5)
 exposed=moved(ring(85,34.8,0,2.5).val().fuse(cylinder([0,0,2.5],[0,0,1],85,107.5)),frame([0,0,z],[0,1,0]))
 positive_half=bbox(1000,1000,1000,[0,500,z]);contains=[];negative=[]
 for n,s in moving.items():
  vol=0
  for k,solid in enumerate(s.Solids()):
   out=solid.cut(full);v=abs(out.Volume()) if out.Solids() else 0;assert v<1e-4,(n,k,v)
   contains.append(dict(part=n,solid=k,outside_full_invariant_mm3=v))
   pos=solid.intersect(positive_half)
   for j,piece in enumerate(pos.Solids()):
    out=piece.cut(exposed);v=abs(out.Volume()) if out.Solids() else 0;assert v<1e-4,(n,k,j,v)
    contains.append(dict(part=n,solid=k,exposed_solid=j,outside_exposed_invariant_mm3=v))
   neg=solid.cut(positive_half);vol+=sum(abs(piece.Volume()) for piece in neg.Solids())
  if vol>1e-4:assert n.startswith('L23_HW_OUT_'),(n,vol);negative.append(dict(part=n,negative_Y_volume_mm3=vol,scope='Known partial output-screw channel modeled3.5mm behind output. Remains in external collision set; ownOEM internal rotating ownership not qualified.'))
 q={n:check(full,s,minimum=True) for n,s in fixed.items()};ownq=check(exposed,own,minimum=True)
 return dict(dz_mm=dz,J2_height_mm=z,range_deg=[-90,90],full_invariant_envelope=dict(axis=[0,1,0],axis_origin_mm=[0,0,z],radius_mm=85,axial_Y_mm=[-3.5,110]),exposed_envelope=dict(radius_mm=85,axial_Y_mm=[0,110],central_void_radius_Y_mm=[34.8,0,2.5]),moving_count=len(moving),fixed_external_count=len(fixed),containment=contains,external_checks=q,exposed_to_entire_actual_J2=ownq,negative_output_segments=negative,all_full_moving_external_certified=not any(x['events'] for x in q.values()),minimum_external_envelope_gap_mm=min(x['minimum_BREP_surface_distance_mm'] for x in q.values()),own_J2_exposed_no_positive_volume=not ownq['events'],proof='Actual per-solid Boolean containment in an axisymmetric envelope, which is invariant for every q2 including+-90deg. Exact envelope-to-static per-solid Boolean/distance checks. No sampling inference.',limits='OwnJ2 negative output screw segments cannot be tested as rotating screws in frozen output bores; no official rotor/stator solid assignment. Only external-interface/exposed proof. No OEM internal certification, no cables or downstream L34+ swept interaction.'),full,exposed

def static_interfaces(dz,fixed,own,h12):
 a={k:v for k,v in fixed.items() if k in ['L12_output_adapter','L12_rear_fork','L12_front_ring','J1']};a['J2']=own
 results={};contacts={}
 for x,y in itertools.combinations(a,2):results[x+'__'+y]=check(a[x],a[y])
 free={};table=[]
 for row in h12[3]:
  n='L12_HW_'+row['id'];r=dict(row);r['id']=n;shift=np.array([0,0,dz if row['id'].startswith('FIX_') else 0]);r['seat_world_mm']=(np.array(r['seat_world_mm'])+shift).tolist();table.append(r);free[n]=h12[1][row['id']].translate(tuple(shift))
 for row in table:
  n=row['id'];owner='L12_'+row['thread_owner'] if row['thread_owner'] in ['rear_fork','output_adapter'] else row['thread_owner']
  for other,s in a.items():results[n+'__'+other]=check(free[n] if other==owner else fixed[n],s)
 for x,y,o,normal in [('L12_output_adapter','L12_rear_fork',[0,0,127.2],[0,0,1]),('L12_rear_fork','J2',[0,-45.7,170+dz],[0,1,0]),('L12_front_ring','J2',[0,-15.5,170+dz],[0,1,0]),('J1','L12_output_adapter',[0,0,105.2],[0,0,1])]:
  c=face_contact(a[x],a[y],o,normal);assert c['shared_planar_face_area_mm2']>10;contacts[x+'__'+y]=c
 return dict(checks=results,contacts=contacts,events={k:v for k,v in results.items() if v['events']},hardware_table=table)

def assembly_paths(dz,fixed,own,h12):
 """Known fasteners and a staged, explicitly bounded assembly sequence."""
 hardware={n:s for n,s in fixed.items() if n.startswith('L12_HW_')}
 structure={n:s for n,s in fixed.items() if not n.startswith('L12_HW_')};structure['J2']=own
 hardware_checks={};tool_checks={}
 for a,b in itertools.combinations(hardware,2):hardware_checks[a+'__'+b]=check(hardware[a],hardware[b])
 for n,s in hardware.items():
  for b,t in structure.items():
   if b.startswith('BASE_'):hardware_checks[n+'__'+b]=check(s,t)
 for row in h12[3]:
  name=row['id'];tool=h12[2][name].translate((0,0,dz)) if name.startswith('FIX_') else h12[2][name]
  present={1:['L12_output_adapter','L12_rear_fork'],3:['L12_output_adapter','L12_rear_fork','J1',*[x for x in fixed if x.startswith('BASE_')]],5:list(structure)}[row['stage']]
  for other in present:tool_checks[name+'__'+other]=check(tool,structure[other])
 # J2 enters from +Y. The larger front cylinder also encloses the translated
 # rear cylinder at every t in [0,180]; containment is checked on every solid.
 T=frame([0,0,170+dz],[0,1,0]);rear=cylinder([0,0,-104],[0,0,1],47.45,58.3)
 envelope=moved(rear.fuse(cylinder([0,0,-45.7],[0,0,1],55.05,47.8)),T)
 sweep=moved(rear.fuse(cylinder([0,0,-45.7],[0,0,1],55.05,227.8)),T)
 contained=[]
 for i,s in enumerate(own.Solids()):
  cut=s.cut(envelope);v=sum(abs(x.Volume()) for x in cut.Solids());assert v<1e-4
  contained.append(dict(solid=i,outside_mm3=v))
 j2_stationary={n:s for n,s in fixed.items() if n!='L12_front_ring' and not n.startswith('L12_HW_FIX_')}
 j2_checks={n:check(sweep,s) for n,s in j2_stationary.items()}
 bench=comp([fixed['L12_output_adapter'],fixed['L12_rear_fork'],*[s for n,s in hardware.items() if n.startswith('L12_HW_FOOT_')]])
 stages=[('rear_fork',fixed['L12_rear_fork'],[0,0,1],120,{'L12_output_adapter':fixed['L12_output_adapter']}),
         ('bracket_preassembled',bench,[0,0,1],120,{n:s for n,s in fixed.items() if n=='J1' or n.startswith('BASE_')}),
         ('front_ring',fixed['L12_front_ring'],[0,1,0],140,{**j2_stationary,'J2':own})]
 insertions=[]
 for name,shape,axis,travel,stationary in stages:
  print('assembly path',name,flush=True);results=[];targets={n:cache(s) for n,s in stationary.items()}
  steps=sorted(set([0.,.1,.5,1.,2.,*range(5,travel+1,5)]))
  for t in steps:
   probe=cache(shape.translate(tuple(np.array(axis)*t)))
   for n,s in targets.items():
    q=check(probe,s)
    if q['events']:results.append(dict(translation_mm=t,other=n,**q))
  insertions.append(dict(moving=name,direction_from_final=axis,travel_mm=[0,travel],sampled_positions_mm=steps,collisions=results,proof_type='Discrete actual-solid checks only; not a continuous insertion certificate.'))
 events={category+'__'+n:q for category,qs in [('hardware',hardware_checks),('tool',tool_checks),('J2_insertion',j2_checks)] for n,q in qs.items() if q['events']}
 return dict(hardware_checks=hardware_checks,staged_straight_tool_checks=tool_checks,continuous_J2_insertion=dict(axis_origin_world_mm=[0,0,170+dz],direction_from_final=[0,1,0],travel_mm=[0,180],per_solid_containment=contained,checks=j2_checks,envelope_joint_local_mm=dict(rear_radius=47.45,rear_z=[-104,-45.7],front_radius=55.05,front_z=[-45.7,182.1]),proof='Every actual OEM solid lies in the two-cylinder starting enclosure; its full translational union over180mm lies in the stated swept enclosure.'),other_insertions=insertions,events=events,scope='J3 and downstream links absent while L12 is assembled. Known straight driver shafts only; handles, cables, motor connectors, tolerances and installed-system service removal are not qualified.')

def properties(s,material='6061_uniform_candidate',rho=2.7e-6):
 g=geometry_properties(s);m=g['volume_mm3']*rho;return dict(material=material,mass_kg=m,com_world_m=g['com_m'].tolist(),inertia_about_COM_world_axes_kg_m2=(m*g['inertia_per_mass_m2']).tolist(),density_kg_mm3=rho,volume_mm3=g['volume_mm3'],mass_measured=False)

def aggregate(rows):
 mass=sum(r['mass_kg'] for r in rows);centre=sum(r['mass_kg']*np.array(r['com_world_m']) for r in rows)/mass
 tensor=np.zeros((3,3))
 for r in rows:
  d=np.array(r['com_world_m'])-centre;tensor+=np.array(r['inertia_about_COM_world_axes_kg_m2'])+r['mass_kg']*(np.dot(d,d)*np.eye(3)-np.outer(d,d))
 assert np.max(abs(tensor-tensor.T))<1e-12 and min(np.linalg.eigvalsh(tensor))>0
 return dict(mass_kg=mass,com_world_m=centre.tolist(),inertia_about_COM_world_axes_kg_m2=tensor.tolist(),mass_basis='Uniform nominal6061 CAD; no fasteners or OEM mass in this aggregate.')

def section_study(dz,fixed):
 # Actual net horizontal slices are reproducible geometric inputs. They do not
 # constitute a load-distribution or curved-collar stress/deflection solution.
 rear=fixed['L12_rear_fork'];stations=sorted(set([128.,134.,140.,142.3,148.1,150.,160.,170.,176.,185.,195.,170+dz]))
 sections=[l12.section_at_world_z(rear,z) for z in stations if z<170+dz+.001]
 for r in sections:assert r['area_mm2']>0 and min(r['Ixx_mm4'],r['Iyy_mm4'])>0
 A=2*16*42-4*math.pi*2.5**2;Ixx=2*16*42**3/12-4*(math.pi*2.5**4/4+math.pi*2.5**2*13**2);Iyy=2*(42*16**3/12+16*42*57**2)-4*(math.pi*2.5**4/4+math.pi*2.5**2*57**2)
 bottom=next(r for r in sections if r['world_z_mm']==134.)
 errors=dict(area_mm2=abs(bottom['area_mm2']-A),Ixx_mm4=abs(bottom['Ixx_mm4']-Ixx),Iyy_mm4=abs(bottom['Iyy_mm4']-Iyy))
 assert errors['area_mm2']<1e-4 and max(errors['Ixx_mm4'],errors['Iyy_mm4'])<.01
 return dict(actual_net_horizontal_slices=sections,lower_two_leg_analytic_crosscheck=dict(z_mm=134,area_mm2=A,Ixx_mm4=Ixx,Iyy_mm4=Iyy,errors=errors),old_foot_to_shoulder_axis_mm=42.8,new_foot_to_shoulder_axis_mm=42.8+dz,added_force_lever_arm_m=dz*.001,added_moment_formula_Nm='deltaM=(-dz_m*Fy, dz_m*Fx,0); vertical Fz alone adds zero moment from this vertical translation.',fixed_output_connection_reused=True,method='0.001mm actual-solid slice volume/thickness and central area inertia; analytic rectangle-minus-four-circle unit/geometry crosscheck at134mm.',limits='Disconnected cross-section islands are not automatically a composite beam; shear transfer through the collar and feet is unproved. No torsional J inferred from Ixx+Iyy. No load rating, stiffness, material yield, preload, contact or fatigue pass from these section values.')

def export(dz,p,rows,moving,fixed,proof,full,exposed,hashes):
 local={'output_adapter':(fixed['L12_output_adapter'],frame([0,0,105.2],[0,0,1])),'rear_fork':(fixed['L12_rear_fork'],frame([0,-59.7,113.2],[0,0,1])),'front_ring':(fixed['L12_front_ring'],frame([0,-15.5,170+dz],[0,1,0]))};instances={};a=cq.Assembly(name='SHOULDER-RAISE01-original-only')
 for n,(s,T) in local.items():
  file='RAISE01-L12-'+n+'.step';q=moved(s,np.linalg.inv(T));cq.exporters.export(q,str(OUT/file));rt=cq.importers.importStep(str(OUT/file)).val();assert rt.isValid() and len(rt.Solids())==1
  vdelta=abs(rt.Volume()-q.Volume());assert vdelta<1e-4
  instances[n]=dict(file=file,sha256=sha(OUT/file),T_world_from_part_mm=T.tolist(),STEP_reimport_volume_difference_mm3=vdelta,preceding_joints=1,**properties(s));a.add(s,name='L12_'+n)
 for n,s in fixed.items():
  if n.startswith('L12_HW_'):a.add(s,name=n)
 a.save(str(OUT/'SHOULDER-RAISE01-original-L12-assembly.step'))
 cq.exporters.export(full,str(OUT/'full-rotation-envelope.step'));cq.exporters.export(exposed,str(OUT/'exposed-J2-interface-envelope.step'))
 orig={n:properties(rows['L12_'+n]['shape']) for n in local};masssum=sum(x['mass_kg'] for x in instances.values());oldsum=sum(x['mass_kg'] for x in orig.values())
 massaggregate=aggregate(list(instances.values()));direct=properties(comp([s for s,T in local.values()]));assert np.allclose(massaggregate['com_world_m'],direct['com_world_m'],atol=1e-12);assert np.allclose(massaggregate['inertia_about_COM_world_axes_kg_m2'],direct['inertia_about_COM_world_axes_kg_m2'],atol=1e-12)
 manifest=dict(revision='SHOULDER-RAISE01',candidate_raise_mm=dz,not_baseline=True,original_L12_instances=instances,old_L12_properties=orig,L12_original_metal_mass_kg=masssum,old_L12_original_metal_mass_kg=oldsum,added_original_metal_mass_kg=masssum-oldsum,new_L12_original_aggregate=massaggregate,old_L12_original_aggregate=aggregate(list(orig.values())),fasteners=dict(unchanged_catalog_selected_mass_kg=.0852,unchanged_whole_L12_hardware_planning_budget_kg=.20,caution='0.0852kg is12 selected screws only; do not add it to the0.20kg whole-fastener budget.16 outputM4 remain unselected. No measured fastener inertia.'),all_other_local_geometry_unchanged=True,derived_joint_home_origins_mm={j['id']:(np.array(j['origin_mm'])+([0,0,0] if j['id']=='J1' else [0,0,dz])).tolist() for j in p['joints']},derived_head_face_world_mm=[0,55,804+dz],source_hashes=hashes,shift_contract='J1 andBASE and L12output adapter stay. L12rear fork is rebuilt and front ring translated. All L23..L67 local STEP geometry and J2..J7 OEM rigid geometry remain unchanged, homeworld transforms shift+dzZ. Entire HEAD03 homeface also+dz; no shared parameter edits.',manufacturing_release=False)
 dump('part-placements.json',manifest);return manifest

def draw_candidate(dz,fixed):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.collections import PolyCollection
 from matplotlib.patches import Circle,Rectangle
 fig,axes=plt.subplots(1,2,figsize=(13,7));colors={'L12_output_adapter':'#497da0','L12_rear_fork':'#57a394','L12_front_ring':'#dbac61'}
 for ax,indices,label in zip(axes,[(0,2),(1,2)],['FRONT | X-Z','SIDE | Y-Z']):
  for n,color in colors.items():
   vv,ff=fixed[n].tessellate(.12,.12);v=np.array([q.toTuple() for q in vv]);tri=v[np.array(ff)][:,:,indices]
   ax.add_collection(PolyCollection(tri,facecolors=color,edgecolors='none',alpha=.9,rasterized=True))
  if indices==(0,2):ax.add_patch(Circle((0,170+dz),85,fill=False,color='#bd5339',lw=1.8,ls='--'))
  else:ax.add_patch(Rectangle((-3.5,85+dz),113.5,170,fill=False,color='#bd5339',lw=1.8,ls='--'))
  ax.axhline(170,color='#888',ls=':',lw=1);ax.axhline(170+dz,color='#444',ls=':',lw=1)
  ax.plot(0,170+dz,'+',color='#a63122',ms=10);ax.plot(0,105.2,'+',color='#222',ms=10)
  ax.set(xlim=(-110,125),ylim=(87,315),xlabel='World '+('X' if indices[0]==0 else 'Y')+' / mm',ylabel='World Z / mm',title=label);ax.set_aspect('equal');ax.grid(alpha=.13)
 axes[0].annotate(f'J2 +{dz:g} mm: 170 -> {170+dz:g}',xy=(0,170+dz),xytext=(-103,306),arrowprops=dict(arrowstyle='-',color='#333'),fontsize=10)
 axes[0].annotate('J1 unchanged: 105.2',xy=(0,105.2),xytext=(-103,90),arrowprops=dict(arrowstyle='-',color='#333'),fontsize=10)
 axes[0].text(-102,278,'Dashed: R85 invariant moving enclosure',fontsize=9,color='#ad462e')
 axes[1].annotate(f'2 legs: 16 x 42 x {14+dz:g}\nFoot plane Z127.2 unchanged',xy=(-38,144),xytext=(5,95),arrowprops=dict(arrowstyle='-',color='#333'),fontsize=10)
 axes[1].annotate('4.000 mm minimum\nto fixed screw heads',xy=(-5.5,245),xytext=(6,276),arrowprops=dict(arrowstyle='-',color='#333'),fontsize=10)
 axes[1].text(-105,307,'Original solids only; OEM CAD not redistributed',fontsize=8)
 fig.suptitle(f'SHOULDER-RAISE01 | +{dz:g} mm candidate / local q2 motion clearance',fontsize=15,y=.98)
 fig.text(.05,.018,'Nominal BREP / envelope evidence; not strength, full-arm motion or manufacturing approval. All dimensions mm.',fontsize=10)
 fig.tight_layout(rect=[0,.12,1,.95]);fig.savefig(OUT/'shoulder-raise-01.png',dpi=160);fig.savefig(OUT/'shoulder-raise-01.svg');plt.close(fig)

def transform_contract(dz,rows):
 records=[]
 for n,r in rows.items():
  shift=[0,0,0] if n=='J1' or n.startswith('BASE_') or n=='L12_output_adapter' else [0,0,dz]
  q=dict(id=n,source=r['source'],preceding_joints=r['pre'],delta_world_translation_mm=shift,local_geometry_unchanged=n!='L12_rear_fork')
  if n=='L12_rear_fork':q.update(delta_world_translation_mm=None,replacement='RAISE01-L12-rear_fork.step',replacement_pose='part-placements.json#original_L12_instances.rear_fork')
  records.append(q)
 return dict(revision='SHOULDER-RAISE01',objects=records,HEAD03=dict(complete_head_translation_mm=[0,0,dz],new_face_world_mm=[0,55,804+dz],all_local_geometry_unchanged=True),scope='Home transforms only, not automatic application to the baseline. Update joint origins and each rigid home pose together before kinematics. L12 fixed-side parts stay preceding_joints1; all other ownership unchanged.')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--raise-mm',type=float,default=35);ap.add_argument('--export',action='store_true');ap.add_argument('--model',action='append',help='Override controlled OEM input as RH25-B=/private/path/part.step, etc.');args=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True)
 paths=default_paths()
 if args.model:paths.update({n:Path(q) for n,q in (s.split('=',1) for s in args.model)})
 p,rows,hashes,vendor,iface,h12,h23,rebuild=setup(paths);dz=args.raise_mm;assert dz>=14,'Study onlysupports a raised fork with the stated bottom thread form.'
 for n in ['engineering/shoulder_raise_study.py','engineering/build_layout.py','engineering/build_link12_study.py','engineering/build_link23_study.py','engineering/build_link56_study.py','engineering/mount_interface_study.py','engineering/screen_integrated_collisions.py','engineering/studies/link_interface_tools.py','engineering/head_mass04_study.py','engineering/generated/head-integrated-03/blender-parts-manifest.json']:
  pp=ROOT/n
  assert pp.exists(),pp;hashes[n]=sha(pp)
 start_hashes=dict(hashes);moving,fixed,own=candidate(dz,rows,iface,h12,h23);print('candidate built',dz,flush=True);proof,full,exposed=invariant_proof(dz,moving,fixed,own)
 evidence=dict(revision='SHOULDER-RAISE01',license='CC-BY-NC-4.0',required_notice=NOTICE,source_hashes=hashes,vendor_sources=vendor,rebuild_check=rebuild,nominal_leg_section_mm=[16,42],old_leg_height_mm=14,new_leg_height_mm=14+dz,foot_contact_world_Z_mm=127.2,old_foot_to_J2_axis_span_mm=42.8,new_foot_to_J2_axis_span_mm=42.8+dz,proof=proof,baseline_unchanged=True,hardware_release=False);dump('geometry-decision.json',evidence);print('proof',proof['all_full_moving_external_certified'],proof['minimum_external_envelope_gap_mm'],proof['own_J2_exposed_no_positive_volume'],flush=True)
 if not(proof['all_full_moving_external_certified'] and proof['own_J2_exposed_no_positive_volume']):return
 q=static_interfaces(dz,fixed,own,h12);dump('static-interfaces.json',q);print('static events',list(q['events']),flush=True);assert not q['events']
 a=assembly_paths(dz,fixed,own,h12);dump('assembly-paths.json',a);assert not a['events'] and not any(x['collisions'] for x in a['other_insertions'])
 sections=section_study(dz,fixed);dump('net-sections.json',sections);dump('assembly-transform-contract.json',transform_contract(dz,rows))
 if args.export:export(dz,p,rows,moving,fixed,proof,full,exposed,hashes);draw_candidate(dz,fixed)
 unchanged={n:sha(ROOT/n)==h for n,h in start_hashes.items()};assert all(unchanged.values())
 dump('qa.json',dict(generator_sha256=sha(__file__),unit_checks=unit_checks(),source_integrity=unchanged,nominal_continuous_local_q2_domain_passed=proof['all_full_moving_external_certified'] and proof['own_J2_exposed_no_positive_volume'],all_static_interfaces_and_known_hardware_checked=True,continuous_J2_assembly_envelope_passed=True,other_three_insertions_are_discrete_only=True,net_slice_reverse_check_passed=True,baseline_files_unchanged=True,manufacturing_release=False,full_arm_trajectory_qualified=False,artifacts={p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='qa.json'}))
 print('READY local geometry +35 candidate; source inputs unchanged',flush=True)
if __name__=='__main__':main()
