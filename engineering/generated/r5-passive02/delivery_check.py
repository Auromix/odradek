#!/usr/bin/env python3
"""Read current inputs/outputs and record a scoped delivery audit, not a test rig."""
from pathlib import Path
import hashlib
import json
import math
import re

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
STUDY=json.loads((OUT/'study.json').read_text())
MASS=json.loads((OUT/'mass-model.json').read_text())
SEARCH=json.loads((OUT/'candidate-search.json').read_text())
checks=[]
def ck(name,value):checks.append(dict(id=name,pass_=bool(value)))
for rel,digest in STUDY['source_hashes'].items():
    ck('source '+rel,hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==digest)
for name,value in MASS['source_STEP_hashes_match'].items():ck('source STEP '+name,value)
ck('40 source STEP items',len(MASS['source_STEP_hashes_match'])==40)
ck('238 unique candidate parameter sets',len(SEARCH['candidates'])==238 and len({tuple(tuple(p) for p in c['params']) for c in SEARCH['candidates']})==238)
ck('no2mm candidate claimed',STUDY['search']['close2mm_count']==0)
ck('known mass balance',math.isclose(MASS['moving_known_mass_four_branches_kg']+MASS['fixed_guide_mass_four_kg'],MASS['sum_matches_CARRIER01_mass_kg'],abs_tol=1e-9))
ck('full cycle not qualified',STUDY['one_second_qualification'] is False)
ck('manufacturing not released',STUDY['manufacturing_release'] is False)
for key,row in STUDY['independent_checks'].items():
    ck(key+' energy',row['work_energy_max_residual_J']<2e-6)
    ck(key+' four coordinate',row['full_four_bordered_mass_solve_max_position_error_m']<2e-7)
    ck(key+' convergence',row['event_refinement_error_s']<1e-7)
for key,rows in STUDY['runs'].items():
    for row in rows:
        ck(key+' '+row['direction']+' stops before command end',row['stop_time_s']<.5)
        ck(key+' '+row['direction']+' no extrapolation',row['complete_cycle_qualified'] is False)
        for st in row['static_box']:
            ck(key+' static2T4T '+str(st['box_orientation_offset_deg']),math.isclose(st['second_tier_tension_N'],2*st['leaf_tension_N']) and math.isclose(st['input_force_N'],4*st['leaf_tension_N']))
doc=ROOT/'docs/engineering/r5-passive02.md'
for link in re.findall(r'\]\(([^)]+)\)',doc.read_text()):
    if not link.startswith('http'):ck('doc link '+link,(doc.parent/link.split('#')[0]).resolve().exists())
files=sorted([p for p in OUT.iterdir() if p.is_file() and p.name!='verification.json']+[ROOT/'engineering/r5_passive02.py',doc])
audit=dict(revision='R5-PASSIVE02',scope='source identity and calculation-output consistency; no physical qualification',checks=checks,all_passed=all(c['pass_'] for c in checks),visual_review='return-comparison.png visually checked at2040x1360; all curves stop at first events; labels and captions readable',files_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
(OUT/'verification.json').write_text(json.dumps(audit,indent=2)+'\n')
assert audit['all_passed'],[c for c in checks if not c['pass_']]
print(json.dumps(dict(checks=len(checks),all_passed=True,artifact_hashes=len(files))))
