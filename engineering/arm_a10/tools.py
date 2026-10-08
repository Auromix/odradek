# SPDX-License-Identifier: CC-BY-NC-4.0
"""Nominal straight hex-key corridors in an explicitly staged assembly."""
import json,hashlib,numpy as np
import collision as x
from interfaces import OUT

def run():
 d,parts=x.items(False,True);q=d['layout']['poses']['reference'];frames,_=x.ld.fk(q);placed={p['id']:(p,s) for p,s,bb,pos,r in x.placed(parts,q)};checks=[]
 for h in d['parts']:
  if 'machining' not in h or h['id'].startswith('S0') or '-armour-' in h['id'] or h['id'].startswith('T'):continue
  m=h['machining'];af={3:2.5,4:3,5:4,6:5}[m['d']];n=np.array(m['n']);p=np.array(m['p'])+n*(m['plate']+m['washer']+m['head'][1]+.1);length=100 if h['id'].startswith('ROOT-M6') else 45
  tool=x.c.legacy.cyl(p,n,af/2/np.cos(np.pi/6)+.15,length);pos,r=frames[h['frame']];tool=x.transformed(tool,pos,r);bb=x.bbox(tool);issues=[]
  output=h['id'].startswith('J') and '-output-' in h['id'];root=h['id'].startswith('ROOT-M6');nextframe=f'J{h["owner"]+1}.fixed'
  for id,(a,s) in placed.items():
   if id==h['id'] or a['role']=='printed_cover' or a['owner']>h['owner']:continue
   if root and id!='P00-root-open':continue
   if h['id'].startswith('J7-fixed-') and (id.startswith('J7-bearing') or id.startswith('J7-6807') or id.startswith('J7-cage')):continue
   # Connect proximal module to motor before inserting pipe and captive nuts.
   if output and h['owner'] in [3,4]:
    prefix=f'T{h['owner']}'
    if id.startswith(prefix) or id.startswith(f'T0{h['owner']}') or id.startswith(f'S0{h['owner']}'):continue
   if output and a['frame']==nextframe and a['role'] in ['motor_envelope','hardware']:continue
   cb=x.bbox(s)
   if any(getattr(bb,k+'max')<=getattr(cb,k+'min')+1e-5 or getattr(cb,k+'max')<=getattr(bb,k+'min')+1e-5 for k in ['x','y','z']):continue
   v=x.volume(x.common_solids(tool,s))
   if v>.05:issues.append(dict(part=id,intersection_mm3=v))
  checks.append(dict(screw=h['id'],key_AF_mm=af,straight_length_mm=length,overlaps=issues,assembly_rule='Root before J1; upstream output before downstream motor; covers absent. Tool starts above head.'))
 out=dict(manifest_sha256=d['_audit_sha256'],checks=checks,scope='Nominal straight shaft only at reference assembly pose, no wrench handle/fingers, tolerances or physical verification.')
 (OUT/'tool-access-audit.json').write_text(json.dumps(out,indent=2)+'\n');print('TOOLS',len(checks),sum(bool(q['overlaps']) for q in checks),flush=True)
if __name__=='__main__':run()
