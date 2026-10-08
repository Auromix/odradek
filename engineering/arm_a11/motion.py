# SPDX-License-Identifier: CC-BY-NC-4.0
"""22 bounded path samples, original body BREP plus exposed hardware.
Exact untouched geometry at identical old path samples reuses pinned A10 proof;
every new/changed part is tested against every broad-phase neighbour.
"""
import json,hashlib,numpy as np
import collision as x
from interfaces import ROOT,OUT

def main():
 d,parts=x.items(False,False);_,allparts=x.items(False,True)
 for p,s in allparts:
  if p['role']!='hardware':continue
  if 'machining' in p:
   m=p['machining'];s=x.c.legacy.cyl(np.array(m['p'])+np.array(m['n'])*(m['plate']+m['washer']),m['n'],m['head'][0]/2,m['head'][1]);p={k:v for k,v in p.items() if k not in ['machining','intentional_thread_motor']}
  parts.append((p,s))
 baseline=ROOT/'engineering/arm_a10/build';prior_path=baseline/'motion-context-audit.json';prior=json.loads(prior_path.read_text());bd=json.loads((baseline/'manifest.json').read_text())
 assert prior['manifest_sha256']==hashlib.sha256((baseline/'manifest.json').read_bytes()).hexdigest()
 assert all(not r['overlaps'] for r in prior['path_samples'])
 hashes=json.loads((ROOT/'work/arm-a10/certified-static-pairs.json').read_text())['step_hashes'];old={p['id']:p for p in bd['parts']}
 for p,s in parts:
  path=OUT/'step'/(p['id']+'.step')
  if p['id'] in old and hashlib.sha256(path.read_bytes()).hexdigest()==hashes.get(p['id']) and all(p.get(k)==old[p['id']].get(k) for k in ['frame','owner','role']):x.CERT_UNCHANGED.add(p['id'])
 cache={};results=[]
 for start,end in [('idle','attention'),('attention','reference')]:
  for i in range(11):
   q=(np.array(d['layout']['poses'][start])*(1-i/10)+np.array(d['layout']['poses'][end])*(i/10)).tolist()
   proof=next(r for r in prior['path_samples'] if r['path']==start+' -> '+end and r['sample']==i);assert proof['q_deg']==q
   x.CERT_CHECK={tuple(sorted([e['a'],e['b']])):e for e in proof['intentional_fits']}
   r=x.inspect(parts,q,cache);r.update(path=start+' -> '+end,sample=i);results.append(r)
   print('MOTION',start,end,i,len(r['overlaps']),flush=True)
 report=dict(manifest_sha256=d['_audit_sha256'],prior_report_sha256=hashlib.sha256(prior_path.read_bytes()).hexdigest(),unchanged_pinned_items=len(x.CERT_UNCHANGED),path_samples=results,status='22_discrete_samples_only',scope='Body/analytic motor envelopes and exposed hardware; original BREP. Recomputed every changed/new part. Not continuous-time, full joint domain, supplier-motor path, cable, tolerance or load qualification. Base checked separately at named poses.')
 (OUT/'motion-audit.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
