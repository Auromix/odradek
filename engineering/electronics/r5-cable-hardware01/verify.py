#!/usr/bin/env python3
"""Independent algebra/metadata audit. Does not qualify physical assemblies."""
from pathlib import Path
import csv
import hashlib
import json
import math

H=Path(__file__).resolve().parent
R=H.parents[2]
data=json.loads((H/'catalogue-data.json').read_text())
b=json.loads((H/'budget.json').read_text())
rows=list(csv.DictReader((H/'load-scenarios.csv').open()))
checks=[]
def check(name,value):
    checks.append({'id':name,'pass':bool(value)})
def close(a,z):
    return math.isclose(float(a),z,rel_tol=1e-12,abs_tol=1e-10)
check('24_load_angle_cases',len(rows)==24)
for row in rows:
    case=b['combinations'][row['combination']]
    T=float(row['T_N']); beta=math.radians(float(row['direction_deflection_deg']))
    # Independent vector norm, not sine half-angle expression used in calculate.
    p=math.hypot(T*(1-math.cos(beta)),T*math.sin(beta))
    check(row['combination']+'_'+row['T_N']+'_'+row['direction_deflection_deg']+'_force',close(row['pulley_radial_load_N'],p))
    check(row['combination']+'_'+row['T_N']+'_'+row['direction_deflection_deg']+'_term',close(row['minimum_terminal_retention_fraction_for_guideline10'],10*T/case['min_break_N']))
check('all_assembly_qualification_false',all(x['assembly_qualified']=='False' for x in rows))
check('no_actual_working_load_claim',all(v['qualified_working_tension_N'] is None for v in b['combinations'].values()))
check('highest_loads_fail_bend_screen',all(x['bend_proxy_meets_guideline10']=='False' for x in rows if (x['combination'],x['T_N']) in [('leaf_upgrade','75'),('secondary_upgrade','150')]))
check('middle_loads_pass_only_bend_screen',all(x['bend_proxy_meets_guideline10']=='True' for x in rows if (x['combination'],x['T_N']) in [('leaf_upgrade','50'),('secondary_upgrade','100')]))
check('line_mass_not_solid_density',close(b['combinations']['secondary_upgrade']['mass_g_per_m'],.55*453.59237/30.48))
check('original_calculation_checks',all(x['pass'] for x in b['checks']))
sources=json.loads((R/'docs/engineering/sources/r5-cable-hardware01.json').read_text())
check('unique_source_ids',len({x['id'] for x in sources['sources']})==len(sources['sources']))
mi=json.loads((H/'mechanical-interface.json').read_text())
check('SP4125_requires_spacers',mi['pulleys']['SP4125']['nominal_per_side_bearing_over_nylon_projection_mm']==0)
check('no_frozen_terminal_envelope',mi['termination_planning']['actual_loop_bbox_mm'] is None)
check('source_not_manufacturer_approval',not sources['manufacturer_confirmation_received'])
files=[p for p in H.iterdir() if p.is_file() and p.name!='verification.json']
files += [R/'docs/engineering/hardware/r5-cable-hardware01.md',R/'docs/engineering/sources/r5-cable-hardware01.json']
record={
 'revision':'R5-CABLE-HARDWARE01','scope':'arithmetic and output audit, not a safety/load/life test',
 'checks':checks,'all_passed':all(x['pass'] for x in checks),
 'files_sha256':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)},
 'visual_review':'component-screen.svg rendered locally and viewed; source PDF17/29 visually checked; third-party material stays outside repo'
}
(H/'verification.json').write_text(json.dumps(record,indent=2)+'\n')
assert record['all_passed'],[x for x in checks if not x['pass']]
print(json.dumps({'checks':len(checks),'all_passed':True,'artifact_hashes':len(files)}))
