# SPDX-License-Identifier: CC-BY-NC-4.0
"""Bounded named-path sampling and actual desktop/context clearance."""
import json,hashlib,numpy as np,cadquery as cq
import collision as x
from interfaces import ROOT,OUT

def run(context_only=False):
 d,parts=x.items(False,False);cache={};results=[]
 # Motion adds exposed hardware heads, washers and nuts; blind thread shanks
 # were checked separately at the three named poses in full assembly audits.
 _,hardware=x.items(False,True)
 for p,s in hardware:
  if p['role']!='hardware':continue
  if 'machining' in p:
   m=p['machining'];s=x.c.legacy.cyl(np.array(m['p'])+np.array(m['n'])*(m['plate']+m['washer']),m['n'],m['head'][0]/2,m['head'][1]);p={k:v for k,v in p.items() if k not in ['machining','intentional_thread_motor']}
  parts.append((p,s))
 # Rigid-owner pair relative geometry is invariant. The exact named-pose audit
 # already checked all these pairs, including bounding-box exclusions.
 report=json.loads((OUT/'collision-full.json').read_text());assert report['manifest_sha256']==hashlib.sha256((OUT/'manifest.json').read_bytes()).hexdigest()
 bad={tuple(sorted([a['a'],a['b']])):a for a in report['checks']['idle']['overlaps']}
 for i,(p,s) in enumerate(parts):
  for q,t in parts[i+1:]:
   if p['owner']==q['owner']:
    key=tuple(sorted([p['id'],q['id']]));cache[key]=(bad.get(key),None)
 if context_only:
  previous=json.loads((OUT/'motion-context-audit.json').read_text());assert previous['manifest_sha256']==d['_audit_sha256'];results=previous['path_samples']
 for start,end in ([] if context_only else [('idle','attention'),('attention','reference')]):
  for i in range(11):
   q=(np.array(d['layout']['poses'][start])*(1-i/10)+np.array(d['layout']['poses'][end])*(i/10)).tolist();r=x.inspect(parts,q,cache);r.update(path=start+' -> '+end,sample=i);results.append(r);print('sample',start,end,i,len(r['overlaps']),flush=True)
 # Table Z0 and B04 body in original world, excluding root bolt thread volumes.
 base=ROOT/'engineering/arm_a10/context/base_b04';bd=json.loads((base/'manifest.json').read_text());bs=[]
 for p in bd['parts']:
  path=base/(p.get('step') or '__missing__')
  if p['category'] in ['guide','routing','environment'] or not path.exists():continue
  bs.append((p['id'],cq.importers.importStep(str(path)).val()))
 rootr=x.ld.rotation([0,0,1],90);rootp=np.array([0,135,34.6]);contexts=[]
 for name,q in d['layout']['poses'].items():
  placed=x.placed(hardware,q);issues=[];fits=[];zmin=1e9
  for p,s,bb,pos,r in placed:
   s=x.transformed(s,rootp,rootr);b=x.bbox(s);zmin=min(zmin,b.zmin)
   if b.zmin<-.05:issues.append(dict(a=p['id'],b='table-Z0',min_z_mm=b.zmin))
   for id,t in bs:
    cb=x.bbox(t)
    if any(getattr(b,k+'max')<=getattr(cb,k+'min')+1e-5 or getattr(cb,k+'max')<=getattr(b,k+'min')+1e-5 for k in ['x','y','z']):continue
    common=x.common_solids(s,t);v=x.volume(common)
    if v>.05:
     if p['id'].startswith('ROOT-M6-') and id=='B04-104-FLANGE' and 'machining' in p:
      m=p['machining'];nn=np.array(m['n']);eng=m['length']-m['plate']-m['washer'];org=np.array(m['p'])-nn*(eng+.1);zone=x.c.legacy.cyl(org,nn,m['d']/2+.05,eng+.2);zone=x.transformed(zone,rootp,rootr);outside=sum(x.volume(z.cut(zone)) for z in common.Solids())
      if outside<=.05:
       fits.append(dict(screw=p['id'],base=id,volume_mm3=v,outside_thread_zone_mm3=outside));continue
     issues.append(dict(a=p['id'],b=id,volume_mm3=v))
  contexts.append(dict(pose=name,min_arm_z_mm=zmin,intentional_base_thread_fits=fits,overlaps=issues))
 out=dict(manifest_sha256=d['_audit_sha256'],path_samples=results,context_poses=contexts,status='discrete_samples_only',base_context_manifest_sha256=hashlib.sha256((base/'manifest.json').read_bytes()).hexdigest(),limitations=['Linear joint interpolation at11 samples per path, body plus exposed heads/washers/nuts. Blind thread shafts checked in separate named-pose audits, no continuous-time or full-domain proof.','Original B04 metal interface and envelope context, not later exterior revision.','No plugs, flexible harness, deformed prints, load or hardware safety clearance.'])
 (OUT/'motion-context-audit.json').write_text(json.dumps(out,indent=2)+'\n');print('MOTION',sum(bool(a['overlaps']) for a in results),'context',sum(bool(a['overlaps']) for a in contexts),flush=True)
if __name__=='__main__':
 import sys
 run('--context-only' in sys.argv)
