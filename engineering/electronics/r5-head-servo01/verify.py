#!/usr/bin/env python3
"""Read-only audit plus verification.json; never approves energizing hardware.
SPDX-License-Identifier: CC-BY-NC-4.0
"""
from pathlib import Path
import csv,hashlib,json,math,re
O=Path(__file__).resolve().parent;R=O.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
s=json.loads((O/'study.json').read_text())
checks=[]
def ck(n,x):
 checks.append({'check':n,'pass':bool(x)})
 if not x:raise AssertionError(n)
for x in s['inputs']:ck('input hash '+x['path'],sha(R/x['path'])==x['sha256'])
p=list(csv.DictReader((O/'connection-map.csv').open()))
ck('79 audited functional connection rows',len(p)==79)
keys=[(x['candidate'],x['connector'],x['pin']) for x in p];ck('no duplicate driver contact',len(keys)==len(set(keys)))
get={(x['candidate'],x['connector'],x['pin']):x for x in p}
for mp,ep in [(3,5),(4,6),(5,7),(6,8),(7,9),(8,10)]:ck('MC complement polarity M3.'+str(mp),get['MC5010','M3',str(mp)]['destination']=='IE3L pin '+str(ep))
for mp,ep in [(1,6),(3,5),(5,8),(7,7),(9,10),(11,9)]:ck('Elmo complement polarity J10.'+str(mp),get['Elmo','J10',str(mp)]['destination']=='IE3L pin '+str(ep))
for cand in ['MC5010','Elmo']:
 ck(cand+' has six encoder signals',sum(x['candidate']==cand and x['group']=='encoder' and x['signal'] in ['A+','A-','B+','B-','Z+','Z-'] for x in p)==6)
ck('actual 3600 rpm',abs(s['demand']['peak_rpm']-3600)<1e-9)
ck('reintegrated braking matches denser upstream to 100uJ',abs(s['braking_work_reintegration_error_J'])<.0001)
ck('entire grip range not overclaimed',s['requirements']['range_load_bound_completed'] is False)
ck('current convention unresolved',s['model']['Kt_phase_RMS_or_amplitude'].startswith('not established'))
ck('9 native EtherCAT stations',s['native_network']['total']==9)
bom=list(csv.DictReader((O/'candidate-bom.csv').open()));ck('only two servo candidates',sum(x['role'].endswith('servo') or x['role'].endswith('servo configuration') for x in bom)==2)
D=R/'docs/engineering/hardware/r5-head-servo01.md';text=D.read_text();ck('no control characters in document',all(ord(c)>=32 or c in '\n\t' for c in text))
for ref in re.findall(r'\]\(([^)]+)\)',text):
 if not ref.startswith(('http:','https:','#')):ck('local link '+ref,(D.parent/ref).exists())
S=R/'docs/engineering/sources/r5-head-servo01.json';source=json.loads(S.read_text());ck('source revision gap explicit',len(source['access_gaps'])==2)
for x in source['sources']:
 if x.get('local_archive'):
  z=R.parent.parent/x['local_archive'];ck('archived source '+x['id'],sha(z)==x['sha256'])
files=[p for p in sorted(O.iterdir()) if p.is_file() and p.name not in ['verification.json']]+[D,S]
out={'revision':'R5-HEAD-SERVO01','status':'engineering calculation and mapping checks only; no hardware energization, thermal, current normalization, EtherCAT hardware or functional safety acceptance','checks':checks,'passed':len(checks),'failed':0,'artifacts':[{'path':str(p.relative_to(R)),'sha256':sha(p),'bytes':p.stat().st_size} for p in files]}
(O/'verification.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n');print('PASS',len(checks),'checks,',len(files),'artifact hashes')
