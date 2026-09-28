#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Read back the existing research snapshot; no new geometry/physics solve."""
from pathlib import Path
import ast,hashlib,json,re
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda n:json.loads((O/n).read_text())
for p in [R/'engineering/r5_limit01.py',*O.glob('*.py')]:ast.parse(p.read_text())
checks={}
for n in ['source-hashes.json','supplement-sources.json']:
 for p,h in load(n).items():assert sha(R/p)==h,(n,p)
cont=load('continuous-new-interfaces.json')
for p,h in cont['source_hashes'].items():assert sha(R/p)==h,p
assert len(cont['rows'])==6 and all(not r['unproven_cover_pairs'] for r in cont['rows'])
assert min(r['distance_lower_bound_mm'] for r in cont['rows'])>0
assert max(r['outside_cover_home_mm3'] for r in cont['containment'])<1e-4
m=load('parts-manifest.json');assert len(m['parts'])==13
for r in m['parts']:assert sha(O/r['source_step'])==r['sha256']
x=load('cross-branch-samples.json')['samples'];assert len(x)==96 and all(not r['violations'] for r in x)
y=load('own-branch-checks.json');assert len(y)==9 and all(not r['violations'] for r in y)
a=load('mass-and-envelope.json');assert abs(a['mass']['increment_per_branch_kg']-m['increment_per_branch_kg'])<1e-12
assert len(load('contact-checks.json'))==2
D=R/'docs/engineering/r5-limit01.md';broken=[]
for link in re.findall(r'\]\(([^)]+)\)',D.read_text()):
 if '://' in link or link.startswith('#'):continue
 target=(D.parent/link.split('#')[0]).resolve()
 if target.name=='ready-manifest.json':continue
 if not target.exists():broken.append(str(target))
assert not broken,broken
checks=dict(status='PASS_EXISTING_RESEARCH_SNAPSHOT',new_part_count=13,single_branch_expected_part_count=58,own_pose_count=9,cross_state_count=96,new_interface_continuous_minimum_bound_mm=min(r['distance_lower_bound_mm'] for r in cont['rows']),
 native_individual_step_export_roundtrip='Builder asserted valid one-solid exports and volume error<1e-4 mm3. Full assembly named STEP reimport audit not separately completed before requested freeze.',
 remaining=['Tolerance and deflection budget','Stop impact torque/energy/fatigue','Material/heat treatment/manufacturing process','Original cap screw preload/peeling and interface stiffness','Real in-place four-branch service','q89.5 guard cannot inherit q90 face-contact proof','No integrated SYNC01 review started'],
 completed_scope='Existing nominal geometry and analytic/static screening only; user requested archive without further expansion',source_sha256=sha(R/'engineering/r5_limit01.py'))
(O/'delivery-audit.json').write_text(json.dumps(checks,indent=2)+'\n')
paths=[R/'engineering/r5_limit01.py',D]+[p for p in O.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='ready-manifest.json']
ready=dict(revision='R5-LIMIT01',status='READY_FOR_RESEARCH_ARCHIVE_NOT_MANUFACTURING_RELEASE',files=[dict(path=str(p.relative_to(R)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(paths)],do_not_merge_as_main_q90_working_stop=True,full_head_mass_kg=None,committed_by_this_agent=False)
(O/'ready-manifest.json').write_text(json.dumps(ready,indent=2)+'\n')
print(json.dumps({'files':len(paths),'bytes':sum(p.stat().st_size for p in paths),'ready_sha256':sha(O/'ready-manifest.json'),'audit':checks},indent=2))
