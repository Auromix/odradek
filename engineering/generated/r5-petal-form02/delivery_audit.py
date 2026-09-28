#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Independent SI/STL and rigid-transform audit of FORM02 delivered geometry."""
import ast,hashlib,itertools,json,math,re
from pathlib import Path
import numpy as np
import trimesh
from pypdf import PdfReader
D=Path(__file__).resolve().parent;ROOT=D.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
s=json.loads((D/'study.json').read_text());q=json.loads((D/'qa.json').read_text());rad=json.loads((D/'radial-study.json').read_text())
for rel,h in s['source_hashes'].items():assert sha(ROOT/rel)==h,rel
assert sha(D/'parameters.json')==s['parameters_sha256']
assert sha(D/'radial-study.json')==s['radial_study_sha256']
assert sha(D/'interface-checks.json')==s['hardware_interface_checks_sha256']
ast.parse((ROOT/'engineering/r5_petal_form02.py').read_text());ast.parse(Path(__file__).read_text())
parts={};meshrows=[];unknown=0
for family in q['export_checks']['per_family']:
 for r in family['parts']:
  assert sha(D/r['file'])==r['sha256'];parts[(r['kind'],r['hand'],r['id'])]=r
  if r['mass_kg'] is None:unknown+=1;continue
  assert sha(D/r['STL'])==r['STL_sha256'];m=trimesh.load(D/r['STL'],force='mesh',process=True)
  assert m.is_watertight and m.is_winding_consistent and m.volume>0
  # Trimesh operates in mm and density 1; explicitly restore SI dimensions.
  rho=r['assumed_density_kg_m3'];mass=m.volume*rho*1e-9;I=m.moment_inertia*rho*1e-15;expected=np.array(r['inertia_COM_hand_local_axes_kg_m2']);masserr=abs(mass-r['mass_kg'])/r['mass_kg'];Ierr=np.linalg.norm(I-expected)/np.linalg.norm(expected);ce=np.max(abs(m.center_mass*.001-r['COM_hand_local_m']))
  assert masserr<.005 and Ierr<.006 and ce<3e-5
  assert np.linalg.eigvalsh(expected).min()>0
  meshrows.append(dict(part=r['file'],mass_relative_error=masserr,inertia_Frobenius_relative_error=Ierr,COM_max_error_m=float(ce)))
assert len(parts)==28 and len(meshrows)==16 and unknown==12
assert abs(sum(x['mass_kg'] or 0 for x in parts.values())-s['four_petal_known_material_subtotal_kg'])<1e-12
poses=[]
for assembly in rad['radial_assemblies']:
 a=json.loads((D/assembly['manifest']).read_text());assert sha(D/assembly['manifest'])==assembly['manifest_sha256'];assert sha(D/assembly['STEP'])==assembly['sha256'];cs=[];Is=[];ms=[];errs=[]
 for row in a['parts']:
  src=parts[(row['kind'],row['hand'],row['id'].split('_',1)[1])];phi=math.radians(a['phi_deg'][row['finger']]);er=np.array([math.cos(phi),math.sin(phi),0.]);et=np.array([-math.sin(phi),math.cos(phi),0.]);Q0=np.column_stack([er,et,[0.,0.,1.]])
  axis=-et;K=np.array([[0,-axis[2],axis[1]],[axis[2],0,-axis[0]],[-axis[1],axis[0],0.]])
  # Rodrigues independent from the builder's direct column matrix.
  U=np.eye(3)+K+K@K;Q=U@Q0;t=a['R_mm']*er+[0,0,20]-Q@np.array([0,0,3.5]);T=np.eye(4);T[:3,:3]=Q;T[:3,3]=t
  assert np.max(abs(T-np.array(row['transform_from_hand_local_mm'])))<1e-10
  if src['mass_kg'] is None:
   assert row['mass_kg'] is None and row['COM_head_m'] is None;continue
  c=Q@np.array(src['COM_hand_local_m'])+t*.001;I=Q@np.array(src['inertia_COM_hand_local_axes_kg_m2'])@Q.T
  ce=np.max(abs(c-row['COM_head_m']));ie=np.max(abs(I-np.array(row['inertia_COM_head_axes_kg_m2'])));assert ce<1e-8 and ie<1e-10
  ms.append(src['mass_kg']);cs.append(c);Is.append(I);errs.append([ce,ie])
 M=sum(ms);C=sum(m*c for m,c in zip(ms,cs))/M;J=np.zeros((3,3))
 for m,c,I in zip(ms,cs,Is):
  d=c-C;J+=I+m*((d@d)*np.eye(3)-np.outer(d,d))
 agg=a['known_material_subtotal'];assert abs(M-agg['mass_kg'])<1e-10 and np.max(abs(C-agg['COM_head_m']))<1e-8 and np.max(abs(J-np.array(agg['inertia_COM_head_axes_kg_m2'])))<1e-10
 assert np.max(abs(J-J.T))<1e-12 and min(np.linalg.eigvalsh(J))>0
 poses.append(dict(R_mm=a['R_mm'],known_mass_kg=M,COM_head_m=C.tolist(),max_part_COM_error_m=float(np.max(np.array(errs)[:,0])),max_part_inertia_error_kg_m2=float(np.max(np.array(errs)[:,1])),aggregate_inertia_eigenvalues_kg_m2=np.linalg.eigvalsh(J).tolist()))
assert len(rad['containment'])==28 and all(x['outside_convex_prism_mm3']<1e-4 for x in rad['containment'])
assert len(rad['continuous_radius_certificate']['pairs'])==6
assert abs(rad['continuous_radius_certificate']['minimum_gap_lower_bound_mm']-4/math.sqrt(2))<1e-10
assert len(rad['sampled_BREP_distances'])==18 and rad['finite_object_body_query_count']==168
for row in rad['finite_object_checks']:
 for x in row['parts']:
  assert x['overlap_mm3']<1e-5
  assert x['distance_mm']<1e-6 if x['part']=='compliant_skin' else x['distance_mm']>.499999
pdfs=[]
for name,pages in [('R5-PETAL-FORM02-dimensions-and-sections.pdf',3),('radial-contact-orthographic.pdf',1)]:
 p=PdfReader(D/name);assert len(p.pages)==pages;assert all(len(x.extract_text())>100 for x in p.pages);pdfs.append(dict(file=name,pages=pages))
doc=ROOT/'docs/engineering/r5-petal-form02.md';links=[]
for target in re.findall(r'\]\(([^)]+)\)',doc.read_text()):
 if not target.startswith(('http:','https:','#')):
  assert (doc.parent/target.split('#')[0]).exists(),target;links.append(target)
res=dict(revision='R5-PETAL-FORM02-delivery-audit',status='PASS',source_hashes_checked=len(s['source_hashes']),nominal_material_parts=16,unknown_electronic_reservations=12,STL_independent_mass_inertia_checks=meshrows,independent_Rodrigues_pose_checks=poses,continuous_proof_contained_part_count=28,continuous_minimum_gap_mm=4/math.sqrt(2),finite_object_body_queries=168,PDF_checks=pdfs,document_local_link_count=len(links),script_sha256=sha(Path(__file__)),builder_sha256=sha(ROOT/'engineering/r5_petal_form02.py'),study_sha256=sha(D/'study.json'),doc_sha256=sha(doc),qualification='Delivered nominal geometry and declared mass assumptions only. Not strength, real contact, drive, speed or manufacturing release.')
(D/'delivery-audit.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({k:v for k,v in res.items() if k not in ['STL_independent_mass_inertia_checks','independent_Rodrigues_pose_checks']},indent=2))
