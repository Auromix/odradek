# SPDX-License-Identifier: CC-BY-NC-4.0
"""Motor-only gravity demand is a lower-bound diagnostic at a named straight pose."""
from pathlib import Path
import json,hashlib,sys,numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=HERE/'build'
sys.path.insert(0,str(ROOT/'engineering/arm_a07'));import loads as ld
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/'engineering/arm_a11/build/manifest.json';D=json.loads(source.read_text());ld.LAYOUT=D['layout'];ld.TARGET['flange_frame']['translation_mm']=[110,0,0]
# A zero-mass truthy ledger entry deliberately prevents fallback to A06 budget.
zero=dict(id='zero_mass_no_structure',frame='world',owner=0,mass_kg=0,com_mm=[0,0,0],inertia_kg_mm2=np.zeros((3,3)).tolist(),role='diagnostic')
ld.structure_entries=lambda:[zero]
limits=[13,28.5,13,13,8,3.6,3.6]
budget_masses={j['id']:j['mass_kg'] for j in ld.LAYOUT['joints']}
nominal_masses={'RS00':.310,'RS03':.900,'RS04':1.420,'RS06':.621}
# Catalogue nominal check is distinct from the old dimensional design budget
# (which used the +20g tolerance for RS03/RS04 and +3g for RS00).
for j in ld.LAYOUT['joints']:j['mass_kg']=nominal_masses[j['model']]
nominal_reference=ld.evaluate(D['layout']['poses']['reference'],3)
# Sensitivity: only documented minima; RS06 has no mass tolerance, so remove
# that entire motor in this deliberately unrealistically light diagnostic.
for j in ld.LAYOUT['joints']:j['mass_kg']={'RS00':.307,'RS03':.880,'RS04':1.400,'RS06':0}[j['model']]
documented_minima_reference=ld.evaluate(D['layout']['poses']['reference'],3)
for j in ld.LAYOUT['joints']:j['mass_kg']=budget_masses[j['id']]
cases={k:ld.evaluate(q,3) for k,q in D['layout']['poses'].items()}
# Rotate the upper-arm roll to place the J6 axis horizontal: known joint-limit pose,
# not asserted collision-free. Report payload-only drive moment independently.
q=list(D['layout']['poses']['reference']);q[2]=90;cases['J6_horizontal_axis_diagnostic']=ld.evaluate(q,3)
F,joints=ld.fk(q);pos=F['flange'][0]/1000;payload_only=[abs(float(axis@np.cross(pos-origin,[0,0,-3*9.81]))) for origin,axis in joints]
q_ref=D['layout']['poses']['reference'];F,joints=ld.fk(q_ref)
entries=ld.ledger(3,[0,0,0]);contributions=[]
for b in entries:
 p,R=F[b['frame']];point=(p+R@np.array(b['com_mm']))/1000
 contributions.append(dict(id=b['id'],mass_kg=b['mass_kg'],gravity_drive_signed_Nm=[-float(a@np.cross(point-o,[0,0,-9.81*b['mass_kg']])) if b['owner']>=i+1 else 0 for i,(o,a) in enumerate(joints)]))
# Only sums of same-signed contributions at a named pose support a lower-bound statement.
ref=cases['reference'];proof={}
for i in [1,3]:
 signed=[r['gravity_drive_signed_Nm'][i] for r in contributions];nonzero=[v for v in signed if abs(v)>1e-9]
 assert all(v>=0 for v in nonzero) or all(v<=0 for v in nonzero)
 proof[f'J{i+1}']=dict(demand_Nm=ref['axes'][i]['abs_holding_Nm'],catalog_stall_table_Nm=limits[i],same_sign_motor_payload_terms=True,exceeds_catalog=ref['axes'][i]['abs_holding_Nm']>limits[i],mass_scope='motors and3kg point payload only; no frame, shell, hardware, connectors or harness')
errors=[]
for name,c in cases.items():
 q=c['q_deg'];h=1e-4
 for i,a in enumerate(c['axes']):
  plus=q.copy();minus=q.copy();plus[i]+=h;minus[i]-=h
  diff=(ld.potential(plus,3,[0,0,0])-ld.potential(minus,3,[0,0,0]))/(2*np.radians(h));errors.append(abs(diff-a['holding_Nm']))
assert max(errors)<1e-6
spec=ROOT/'work/arm-a14/vendor/RS-20260917.pdf'
report=dict(revision='A14-QUAL01',target='3kg bare flange centre; long arm; J7 tool datum X110',sources=dict(layout=dict(path=str(source.relative_to(ROOT)),sha256=sha(source)),motor_catalog=dict(url=json.loads((spec.parent/'spec-source.json').read_text())['url'],sha256=sha(spec),version='2026.09.17',table_pages=dict(RS00=5,RS03=21,RS04=25,RS06=33))),catalog_stall_table_Nm=limits,cases=cases,reference_contributions=contributions,reference_lower_bound_proof=proof,catalog_nominal_reference=nominal_reference,documented_minima_without_RS06_reference=documented_minima_reference,budget_motor_masses_kg=budget_masses,catalog_nominal_masses_kg=nominal_masses,J6_horizontal_payload_only_Nm=payload_only,max_virtual_work_error_Nm=max(errors),selection_frozen=False,production_release=False,limits=['Catalog stall rows are test-condition references, not guaranteed compact closed-housing capacities. RS04 stall figure has no explicit heatsink label next to its table; confirm conditions.','Named straight pose diagnostic only; no whole-workspace upper bound or validated collision-free path. The lower bound is conditional on the specified motor masses, centres and same-direction downstream additions, not a universal physical impossibility.','Neither nominal motors nor the existing budget meet J2/J4. Documented mass minima with RS06 artificially omitted still fail J4, but do not independently disprove J2. New counterbalance mechanisms/layouts require new analysis.','No supplier contacted, motor changed or load target reduced.'])
OUT.mkdir(exist_ok=True);(OUT/'motor-only-review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(proof=proof,J6_payload_only_Nm=payload_only,virtual_work_error=max(errors)),indent=2),flush=True)
