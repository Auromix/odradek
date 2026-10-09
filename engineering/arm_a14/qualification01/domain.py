# SPDX-License-Identifier: CC-BY-NC-4.0
"""Joint-domain motor-only gravity screening; samples are not usable paths."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'engineering/arm_a07'));import loads as ld
source=ROOT/'engineering/arm_a11/build/manifest.json';D=json.loads(source.read_text());ld.LAYOUT=D['layout'];ld.TARGET['flange_frame']['translation_mm']=[110,0,0]
ld.structure_entries=lambda:[dict(id='zero_mass_no_structure',frame='world',owner=0,mass_kg=0,com_mm=[0,0,0],inertia_kg_mm2=np.zeros((3,3)).tolist(),role='diagnostic')]
for j in ld.LAYOUT['joints']:j['mass_kg']={'RS00':.310,'RS03':.900,'RS04':1.420,'RS06':.621}[j['model']]
limits=[13,28.5,13,13,8,3.6,3.6]
def halton(n,b):
 f=1.;v=0.
 while n:f/=b;v+=f*(n%b);n//=b
 return v
maxima=[dict(abs_holding_Nm=-1) for _ in range(7)]
q_all=list(D['layout']['poses'].values())
q_all+=[[j['limits_deg'][0]+halton(k,b)*(j['limits_deg'][1]-j['limits_deg'][0]) for j,b in zip(ld.LAYOUT['joints'],[2,3,5,7,11,13,17])] for k in range(1,4097)]
for q in q_all:
 c=ld.evaluate(q,3)
 for i,a in enumerate(c['axes']):
  if a['abs_holding_Nm']>maxima[i]['abs_holding_Nm']:maxima[i]=dict(**a,q_deg=q,catalog_zero_speed_reference_Nm=limits[i],exceeds_reference=a['abs_holding_Nm']>limits[i])
errors=[]
for a in maxima:
 q=a['q_deg'];i=int(a['joint'][1:])-1;h=1e-4;plus=q.copy();minus=q.copy();plus[i]+=h;minus[i]-=h
 v=(ld.potential(plus,3,[0,0,0])-ld.potential(minus,3,[0,0,0]))/(2*np.radians(h));errors.append(abs(v-a['holding_Nm']))
assert max(errors)<1e-6
report=dict(revision='A14-QUAL01-DOMAIN',layout_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),sample_count=len(q_all),mass_scope='catalogue nominal motors plus3kg at flange centre, frame/shell/hardware/harness all excluded',maxima=maxima,max_virtual_work_error_Nm=max(errors),selection_frozen=False,production_release=False,limitations=['Unfiltered joint-domain samples; witnesses are not collision-qualified configurations or paths.','Sample maxima are lower bounds on the unfiltered mathematical domain, not global upper bounds or allowable workspace.','Diagnostic geometry and motor centres retained from A11. Supplier heat boundary and enclosed thermal derating remain unconfirmed.','No drive friction, inertia, acceleration, vibration, off-centre payload, harness or operating temperature qualification.'])
(HERE/'build/motor-only-domain.json').write_text(json.dumps(report,indent=2)+'\n')
print('DOMAIN_COMPLETE',[(a['joint'],round(a['abs_holding_Nm'],3),a['exceeds_reference']) for a in maxima],flush=True)
