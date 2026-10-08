# SPDX-License-Identifier: CC-BY-NC-4.0
"""Exact BREP assembly intersections, with explicitly confined thread fits."""
from pathlib import Path
import json,sys,hashlib,time,numpy as np,cadquery as cq
from OCP.gp import gp_Trsf
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
import interfaces as c
sys.path.insert(0,str(c.ROOT/'engineering/arm_a07'));import loads as ld

def bbox(s):
 # Conservative OCCT Add bounds avoid expensive optimal surface extrema.
 # Non-triangulated bounds contain complete BREP, so only broad-phase cost
 # changes; every candidate still receives exact narrow-phase intersection.
 box=Bnd_Box();BRepBndLib.Add_s(s.wrapped,box,False);return cq.BoundBox(box)

def volume(s):return sum(x.Volume() for x in s.Solids())
def common_solids(s,t):
 result=[]
 for x in s.Solids():
  a=bbox(x)
  for y in t.Solids():
   z=bbox(y)
   if any(getattr(a,k+'max')<=getattr(z,k+'min')+1e-5 or getattr(z,k+'max')<=getattr(a,k+'min')+1e-5 for k in ['x','y','z']):continue
   q=x.intersect(y)
   if volume(q)>.00001:result.extend(q.Solids())
 return cq.Compound.makeCompound(result)

def transformed(s,p,r):
 t=gp_Trsf();t.SetValues(*map(float,np.column_stack([r,p]).flatten()));return s.transformShape(cq.Matrix(t))

def items(use_vendor=False,hardware=True):
 raw=(c.OUT/'manifest.json').read_bytes();d=json.loads(raw);d['_audit_sha256']=hashlib.sha256(raw).hexdigest();ld.LAYOUT=d['layout'];ld.TARGET['flange_frame']['translation_mm']=d['flange_from_J7_mm'];result=[]
 for p in d['parts']:
  if p['role']=='fit_coupon' or not hardware and p['role']=='hardware' or use_vendor and p['role']=='motor_envelope':continue
  result.append((p,cq.importers.importStep(str(c.OUT/'step'/(p['id']+'.step'))).val()))
 if use_vendor:
  cache=c.ROOT/'work/arm-a10/vendor'
  for j in d['layout']['joints']:
   for name,fr in [('stator','fixed'),('external-output','rotor')]:
    path=cache/(j['id']+'-'+name+'.step')
    if not path.exists():continue
    p=dict(id=j['id']+'-supplier-'+name,frame=j['id']+'.'+fr,owner=int(j['id'][1])-1+(fr=='rotor'),role='supplier_motor',motor=j['id']);result.append((p,cq.importers.importStep(str(path)).val()))
 cache=c.ROOT/'work/arm-a10/local-bounds.json'
 if cache.exists():
  for id,e in json.loads(cache.read_text()).items():
   path=c.ROOT/'work/arm-a10/vendor'/(id.replace('-supplier-','-')+'.step') if '-supplier-' in id else c.OUT/'step'/(id+'.step')
   if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==e['step_sha256']:LOCAL_BOXES[id]=e
 return d,result

LOCAL_BOXES={}

def world_box(p,pos,r,w):
 entry=LOCAL_BOXES.get(p['id'])
 if entry:
  lo=np.array(entry['bounds_mm'][:3]);hi=np.array(entry['bounds_mm'][3:]);corners=np.array([[xx,yy,zz] for xx in [lo[0],hi[0]] for yy in [lo[1],hi[1]] for zz in [lo[2],hi[2]]]);points=corners@r.T+pos
  box=Bnd_Box();box.Update(*map(float,np.r_[points.min(axis=0),points.max(axis=0)]));return cq.BoundBox(box)
 return bbox(w)

def placed(parts,q):
 f,_=ld.fk(q);out=[]
 for p,s in parts:
  pos,r=f[p['frame']];w=transformed(s,pos,r);bb=world_box(p,pos,r,w);out.append((p,w,bb,pos,r))
 return sorted(out,key=lambda e:e[2].xmin)

def inspect(parts,q,static_cache=None):
 things=placed(parts,q);issues=[];allowed=[];examined=0
 for idx,(p,s,bb,pos,r) in enumerate(things):
  for a,t,cb,ap,ar in things[idx+1:]:
   if cb.xmin>=bb.xmax-1e-5:break
   if any(getattr(bb,k+'max')<=getattr(cb,k+'min')+1e-5 or getattr(cb,k+'max')<=getattr(bb,k+'min')+1e-5 for k in ['y','z']):continue
   key=tuple(sorted([p['id'],a['id']]))
   if p['owner']==a['owner'] and static_cache is not None and key in static_cache:
    bad,ok=static_cache[key]
    if bad:issues.append(bad)
    if ok:allowed.append(ok)
    continue
   examined+=1
   if p['role']=='supplier_motor' or a['role']=='supplier_motor':print('supplier_pair',p['id'],a['id'],flush=True)
   common=common_solids(s,t);v=volume(common);bad=None;ok=None
   if v>.05:
    # Hot brass insert is deliberately larger than its printed5.5mm pilot.
    if ('P00-root-open' in key and any(x.startswith('ROOT-insert-') for x in key)):
     ok=dict(a=p['id'],b=a['id'],volume_mm3=v,reason='specified RX-M4 hot-insert press fit; physical coupon required')
    else:
     bolt,other,bp,br=(p,a,pos,r) if 'machining' in p else (a,p,ap,ar)
     target=bolt.get('intentional_thread_motor');motor=other.get('motor') or other['id'].split('-motor-envelope')[0] if other['role'] in ['motor_envelope','supplier_motor'] else other['id']
     if target and target==motor:
      m=bolt['machining'];eng=m['length']-m['plate']-m['washer'];origin=np.array(m['p']);n=np.array(m['n']);zone=c.legacy.cyl(origin-n*(eng+.1),n,m['d']/2+.05,eng+.2);zone=transformed(zone,bp,br)
      remaining=sum(volume(z.cut(zone)) for z in common.Solids());
      if remaining<=.05:ok=dict(a=p['id'],b=a['id'],volume_mm3=v,reason='nominal screw engagement confined to declared blind/thread zone')
      else:bad=dict(a=p['id'],b=a['id'],volume_mm3=v,outside_thread_zone_mm3=remaining)
     else:bad=dict(a=p['id'],b=a['id'],volume_mm3=v)
   if bad:issues.append(bad)
   if ok:allowed.append(ok)
   if p['owner']==a['owner'] and static_cache is not None:static_cache[key]=(bad,ok)
 return dict(q_deg=q,overlaps=issues,intentional_fits=allowed,narrow_phase_checks=examined)

def seed_cache(parts):
 path=c.ROOT/'work/arm-a10/certified-static-pairs.json';cache={};proof=None
 if path.exists():
  proof=json.loads(path.read_text());valid={}
  for p,s in parts:
   file=c.OUT/'step'/(p['id']+'.step');valid[p['id']]=file.exists() and hashlib.sha256(file.read_bytes()).hexdigest()==proof['step_hashes'].get(p['id'])
  bad={tuple(sorted([v['a'],v['b']])):v for v in proof['overlaps']}
  for idx,(p,s) in enumerate(parts):
   for q,t in parts[idx+1:]:
    if p['owner']==q['owner'] and valid[p['id']] and valid[q['id']]:
     key=tuple(sorted([p['id'],q['id']]));cache[key]=(bad.get(key),None)
 return cache,dict(reused_rigid_pairs=len(cache),source_report_sha256=proof['report_sha256'] if proof else None,scope='Exact unchanged original STEP hashes only; altered and moving-owner pairs recomputed.')

def run(mode='quick'):
 vendor=mode=='supplier';hardware=mode!='quick';d,parts=items(vendor,hardware);cache,proof=seed_cache(parts);checks={}
 for name,q in d['layout']['poses'].items():
  start=time.time();checks[name]=inspect(parts,q,cache);print(name,'overlaps',len(checks[name]['overlaps']),'seconds',round(time.time()-start,1),flush=True)
 report=dict(manifest_sha256=d['_audit_sha256'],mode=mode,parts=len(parts),unchanged_rigid_geometry=proof,checks=checks,scope='Named poses only; exact original BREP'+(' with local pinned supplier CAD' if vendor else ' and analytic motor envelopes'),limitations=['Thread-zone exemptions are geometrically confined, not whole-motor pair suppression.','No hardware plugs, flexible harness, printer shrinkage, deflection or continuous-time proof.','Table/base geometry must be checked separately.'])
 (c.OUT/(f'collision-{mode}.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print('COLLISION',mode,'DONE',flush=True)
if __name__=='__main__':run(sys.argv[1] if len(sys.argv)>1 else 'quick')
