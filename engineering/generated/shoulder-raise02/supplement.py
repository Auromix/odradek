#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Independent nonFIX fastener and mass-delta check. No frozen files changed."""
from pathlib import Path
import sys,json,numpy as np,cadquery as cq
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from shoulder_raise_study import *
from mount_interface_study import load_vendor
from build_link56_study import selected_faces
OUT=Path(__file__).resolve().parent
new=json.loads((OUT/'part-placements.json').read_text());old=json.loads((ROOT/'engineering/generated/shoulder-raise-01/part-placements.json').read_text())
assert all(sha(ROOT/n)==h for n,h in new['source_hashes'].items())
assert all(sha(OUT/r['file'])==r['sha256'] for r in new['instances'].values())
sources={'engineering/generated/shoulder-raise02/part-placements.json':sha(OUT/'part-placements.json'),'engineering/generated/shoulder-raise-01/part-placements.json':sha(ROOT/'engineering/generated/shoulder-raise-01/part-placements.json'),'docs/engineering/sources/rh-interface-extraction.json':sha(ROOT/'docs/engineering/sources/rh-interface-extraction.json')}
m=next(x for x in json.loads((ROOT/'docs/engineering/sources/rh-interface-extraction.json').read_text())['models'] if x['id']=='RH25-B');iface=m['unified_joint_interface'];vendor=load_vendor(default_paths()['RH25-B'],m);op=np.array([p['xy_mm'] for p in iface['output_holes']['points']]);fp=np.array([p['xy_mm'] for p in iface['fixed_through_holes']['points']])
h=l12.make_hardware(op,fp,frame([0,0,105.2],[0,0,1]),frame([0,0,205],[0,1,0]))
shapes={n:cq.importers.importStep(str(OUT/r['file'])).val() for n,r in new['instances'].items()};shapes['J1']=moved(vendor,frame([0,0,105.2],[0,0,1]));shapes['J2']=moved(vendor,frame([0,0,205],[0,1,0]))
checks={}
for row in h[3]:
 n=row['id']
 if n.startswith('FIX_'):continue
 owner='L12_'+row['thread_owner'] if row['thread_owner'] in ['rear_fork','output_adapter'] else row['thread_owner']
 for target,s in shapes.items():checks[n+'__'+target]=check(h[1][n] if target==owner else h[0][n],s)
assert not any(r['events'] for r in checks.values())
# Positive force below denotes the support required to hold gravity.
a=new['aggregate_original_metal'];b=old['new_L12_original_aggregate'];dm=a['mass_kg']-b['mass_kg'];dF=np.array([0,0,dm*9.80665]);ds={}
for n,p in [('foot',[0,-.039,.1272]),('J1',[0,0,.1052])]:
 dM=np.cross(np.array(a['com_world_m'])-p,[0,0,a['mass_kg']*9.80665])-np.cross(np.array(b['com_world_m'])-p,[0,0,b['mass_kg']*9.80665]);ds[n]=dict(delta_support_force_N=dF.tolist(),delta_moment_Nm=dM.tolist())
contacts=[]
for i,p in enumerate(fp):
 n=f'STEEL_THREAD_BLOCK_{i+1}';axis=np.array([0,1,0]);o=(frame([0,0,205],[0,1,0])@np.r_[p,-104.5,1])[:3];fs=[a.intersect(b) for a in selected_faces(shapes[n],o,axis) for b in selected_faces(shapes['L12_rear_fork'],o,axis)];fs=[f for f in fs if f.Area()>1e-8];A=sum(f.Area() for f in fs);c=sum(f.Area()*np.array(f.Center().toTuple()) for f in fs)/A;e=float(np.linalg.norm(c-o));P=22322/8
 contacts.append(dict(id=n,nominal_coplanar_area_mm2=A,area_centroid_world_mm=c.tolist(),uniform_pressure_reaction_eccentricity_to_bolt_mm=e,conditional_per_bolt_preload_N=P,conditional_block_bending_moment_Nmm=P*e,nominal_rectangular_net_strip_width_mm=10,nominal_block_axial_thickness_mm=8,conditional_rectangular_net_strip_bending_MPa=P*e/(10*8**2/6),scope='Equal uniform pressure and straight10x8mm net strip reference only; actual pressure/key/bolt load path and threadroot/notch unqualified.'))
interfaces={}
for an,bn,o,axis in [('J1','L12_output_adapter',[0,0,105.2],[0,0,1]),('L12_output_adapter','L12_rear_fork',[0,0,127.2],[0,0,1]),('L12_rear_fork','J2',[0,-45.7,205],[0,1,0]),('L12_front_ring','J2',[0,-15.5,205],[0,1,0])]:
 q=face_contact(shapes[an],shapes[bn],o,axis);assert q['shared_planar_face_area_mm2']>10;interfaces[an+'__'+bn]=q
blank=bbox(134,90,146,[0,-61.25,198.1]);outside=sum(abs(q.Volume()) for q in shapes['L12_rear_fork'].cut(blank).Solids());assert outside<1e-4
r=dict(revision='SHOULDER-RAISE02',source_hashes=sources,source_integrity={p:sha(ROOT/p)==q for p,q in sources.items()},nonFIX_full_geometry_checks=checks,selfweight_delta_wrenches=ds,conditional_steel_block_preload_paths=contacts,interface_contact_areas=interfaces,aluminum_blank_candidate=dict(stock_box_XYZ_mm=[134,90,146],centre_world_mm=[0,-61.25,198.1],outside_actual_part_volume_mm3=outside,material='6061-T6 billet only,90mm stock thickness requires actual product-specific guarantee; no yield applied'),long_screw_reference=dict(assumed_E_MPa=210000,assumed_M4_stress_area_mm2=8.78,fully_threaded100mm_compliance_mm_per_N=100/(210000*8.78),elongation_at2790_25N_mm=2790.25*100/(210000*8.78),preload_plus_external521_167N_nominal_axial_MPa=(2790.25+521.167)/8.78,scope='Conditional elementary all-threaded100mm bar; actual selected shank/thread length, member stiffness and tightening torsion unverified. No capacity decision.'),limits='Exactly nominal original-metal gravity change. No newfastener mass change allocated, no dynamic inertia/whole-arm model updated. J2-side downstream load remains unchanged. Only actual threaded engagement segments removed against named owner for geometry; effective threads/load rating unqualified.',generator_sha256=sha(__file__))
assert all(r['source_integrity'].values());(OUT/'supplement.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(ds))
