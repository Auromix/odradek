#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
import ast,gzip,json,hashlib,sys,re,math
from pathlib import Path
import numpy as np
import cadquery as cq
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'engineering'))
from head_mass04_study import geometry_properties,tensor_check
from screen_integrated_collisions import named_step
O=ROOT/'engineering/generated/r5-carrier01';W=ROOT.parents[1]/'work/r5-carrier01';W.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
ast.parse((ROOT/'engineering/r5_carrier01.py').read_text())
manifest=json.loads((O/'parts-manifest.json').read_text());checks=[]
for r in manifest['parts']:
 p=O/r['source_step'];assert sha(p)==r['sha256'];s=cq.importers.importStep(str(p)).val();assert s.isValid() and len(s.Solids())==1
 g=geometry_properties(s);vrel=abs(g['volume_mm3']-r['volume_mm3'])/r['volume_mm3'];assert vrel<1e-7, (r["id"],vrel)
 err=float(np.max(abs(g['com_m']-r['COM_part_m'])));assert err<1e-8
 I=np.array(r['inertia_COM_part_axes_kg_m2']);expected=r['mass_kg']*g['inertia_per_mass_m2'];ie=float(np.max(abs(expected-I)));assert ie<1e-9
 ck=tensor_check(I);assert ck['minimum_eigenvalue_kg_m2']>0
 checks.append(dict(id=r['id'],STEP_valid=True,volume_relative_error=vrel,COM_error_m=err,inertia_error_kg_m2=ie))
plain=W/'delivery-four-C4.step';plain.write_bytes(gzip.decompress((O/'four-C4-minimum-aperture.step.gz').read_bytes()))
open_n=len(named_step(O/'open.step'));four_n=len(named_step(plain));assert open_n==len(checks)+7;assert four_n==4*open_n
geom=json.loads((O/'geometry-checks.json').read_text());assert len(geom['own_branch_5deg_samples'])==19;assert all(not r['violations'] for r in geom['own_branch_5deg_samples']);assert len(geom['four_branch_independent_state_samples'])==96;assert all(r['overlap_mm3']<1e-5 for r in geom['four_branch_independent_state_samples'])
cert=json.loads((O/'continuous-certificate.json').read_text());assert min(r['lower_bound_mm'] for r in cert['radial_q90_all_independent_R31_to66']['pair_bounds'])>.499999;assert cert['follower_in_nominal_polygonized_groove']['radial_clearance_lower_mm']>.148
h=json.loads((O/'source-hashes.json').read_text());assert all(sha(ROOT/p)==v for p,v in h.items())
pdf=PdfReader(str(O/'R5-CARRIER01-dimensions-and-assembly.pdf'));assert len(pdf.pages)==2;assert all(len(p.extract_text())>500 for p in pdf.pages)
mass=json.loads((O/'mass-summary.json').read_text());assert np.ptp([r['known_mass_kg'] for r in mass['states']])<1e-12;assert mass['whole_head_mass_kg'] is None
cf=[r for r in manifest['parts'] if r['id']=='IKO_CFS4'][0];assert cf['outer_ring_spin_inertia_kg_m2'] is None;assert cf['mass_kg']==.004
broken=[];doc=ROOT/'docs/engineering/r5-carrier01.md'
for target in re.findall(r'\]\(([^)]+)\)',doc.read_text()):
 if not target.startswith('http') and not (doc.parent/target.split('#')[0]).resolve().exists():broken.append(target)
assert not broken,broken
out=dict(status='PASS',scope='Independent native STEP mass/inertia/assembly readback plus report assertions; no physical test or manufacturing release',source_sha256=sha(ROOT/'engineering/r5_carrier01.py'),native_single_part_count=len(checks),open_named_object_count=open_n,four_named_object_count=four_n,part_checks=checks,PDF_pages=2,PDF_render_visual_review='Separately rendered and inspected page PNGs after layout correction',local_links_broken=broken,all_source_hashes_match=True,cross_branch_cases=96,own_branch_angles=19,known_subtotal_kg=mass['states'][0]['known_mass_kg'],included_files_total_bytes=sum(p.stat().st_size for p in O.rglob('*') if p.is_file() and p.name not in ['delivery-audit.json','ready-manifest.json']))
(O/'delivery-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='part_checks'},indent=2))

files=[ROOT/'engineering/r5_carrier01.py',ROOT/'docs/engineering/r5-carrier01.md']+[p for p in sorted(O.rglob('*')) if p.is_file() and p.name!='ready-manifest.json']
ready=dict(revision='R5-CARRIER01',status='READY for review as nominal packaging study; not selected hardware or manufacture release',source_sha256=sha(ROOT/'engineering/r5_carrier01.py'),doc_sha256=sha(ROOT/'docs/engineering/r5-carrier01.md'),files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in files],file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),input_hash_file='source-hashes.json',verification='delivery-audit.json',geometry_scope='Continuous nominal cross-branch q(R) envelopes and finite-state actual-solid checks; no tolerance/deflection or q>90 guarantee',unknowns=['hard stops and pin retention','rail and load-closed palm','fastener/fit/preload','curved track contact and hardening','differential/return/1second dynamics','visible C4 asymmetry and enclosure','electronic payload and complete head mass'],no_prior_baseline_files_changed=True,no_commit_by_agent=True)
(O/'ready-manifest.json').write_text(json.dumps(ready,indent=2)+'\n')
print('READY',sha(O/'ready-manifest.json'))
