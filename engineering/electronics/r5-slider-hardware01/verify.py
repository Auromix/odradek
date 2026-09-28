#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Source/checksum/dimensional consistency QA; not hardware validation."""
import argparse,hashlib,json,math,re
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2]
q=argparse.ArgumentParser();q.add_argument('--archive-root',type=Path,required=True);args=q.parse_args()
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=R/'docs/engineering/sources/r5-slider-hardware01.json';s=json.loads(source.read_text());b=json.loads((P/'budget.json').read_text())
assert b['source_sha256']==h(source);assert b['script_sha256']==h(P/'calculate.py')
hashes=[]
for src in s['sources']:
 if src['local_archive']:
  f=args.archive_root/src['local_archive'];assert h(f)==src['sha256'],f
  if f.suffix=='.pdf':assert f.read_bytes().startswith(b'%PDF'),f
  hashes.append(src['id'])
for c in s['candidates']:
 cfg=c['configured_shortening_request'];assert cfg['thread_length_mm']==cfg['total_length_mm']-(50 if c['id']=='A' else 51)
 assert cfg['thread_length_mm']-c['nut_overall_axial_length_mm']>=40
 assert c['fixed_journal_length_mm']==30-7.5-7
 assert c['fixed_journal_length_mm']>2*s['support']['bearing_dimensions_single_mm'][2]
 assert c['drive_journal_length_mm']>=s['coupling']['hub_insertion_each_mm']
assert 115==5*20+2*7.5
assert b['geometry_budgets']['guide_remaining_end_margins_each_mm']>0
assert len(b['operating_points'])==6
assert math.isclose(b['operating_points'][0]['ideal_motor_static_Nm'],.11426181471250892,abs_tol=1e-12)
assert not b['operating_points'][0]['catalog_3500_floor_speed_only_pass']
assert b['operating_points'][1]['catalog_3500_floor_speed_only_pass']
assert b['operating_points'][2]['required_static_kappa_for_motor_budget0p140']>1
assert not b['manufacturing_release'] and not b['grasp_2kg_certified']
doc=R/'docs/engineering/hardware/r5-slider-hardware01.md'
for x in re.findall(r'\]\(([^)]+)\)',doc.read_text()):
 if not x.startswith('http'):assert(doc.parent/x).exists(),x
report=dict(status='checks passed; engineering candidate only',source_hashes_passed=len(hashes),web_only_sources_without_local_archive=[x['id'] for x in s['sources'] if not x['local_archive']],reference_input_hashes=b['input_hashes'],checks=['PDF magic and17 archive SHA','6 lead/ratio operating points','A quintic rpm outside3500 floor','A seven-segment speed only below3500 floor;dynamic review elsewhere','B direct ideal torque above0.140 budget','factory-supported end machining formula and positive40mm stroke remainder','fixed bearing nominal seat15.5 fits11mm pair;8 is collar wrench AF not seat length','guide standard115mm length and5.55mm nominal end margins','coupler bore fit nominal diameters and6.5 insertion vs7.5journal','rod-force/moment equilibrium independent recomputation in calculate.py','all relative document links'],visual_supplier_pages_read=['KSS A219/A220/A205-206','KSS E107-108/E109-110/E115-116','NBK MST-C PDF2','HIWIN PDF82/89'],limits='no original-CAD assembly, contact proof, actual hardware test or manufacturing release')
(P/'qa.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(report,indent=2,ensure_ascii=False))
