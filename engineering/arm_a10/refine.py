# SPDX-License-Identifier: CC-BY-NC-4.0
"""Explicit nominal hardware seats. Same-rigid-frame hardware only.
Moving fixed-side fasteners get full annular sweep relief where identified.
"""
import numpy as np,math,cadquery as cq
import interfaces as c
b=c.legacy

def shift(s,p,q):return s.translate(b.V(np.array(p)-np.array(q)))
def clearance(e,shape):
 if 'machining' in e:
  m=e['machining'];p=np.array(m['p']);n=np.array(m['n']);hd,hh=m['head'];d=m['d'];g=m['plate'];w=m['washer']
  # Shaft access only for through-bolts, not motor or threaded insert engagements.
  start=g+w-m['length'] if not e.get('intentional_thread_motor') else g
  sh=b.cyl(p+n*start,n,d/2+.25,g+w+hh+.3-start)
  sh=sh.fuse(b.cyl(p+n*(g+w),n,hd/2+.35,hh+4)).clean()
  return sh
 if 'nut_machining' in e:
  m=e['nut_machining'];p=np.array(m['p']);n=np.array(m['n']);af=m['af'];h=m['height']
  return cq.Workplane(b.plane(p-n*.1,n)).polygon(6,(af+.3)/math.cos(math.pi/6)).extrude(h+.2).val()
 # Washer clearance uses radial expansion without moving its clamping plane.
 if 'washer' in e['id']:
  # Axis is identified from exact bounding box; washers are axis-aligned locally.
  bb=shape.BoundingBox();sizes=np.array([bb.xlen,bb.ylen,bb.zlen]);idx=np.argmin(sizes);n=np.eye(3)[idx];p=np.array(shape.Center().toTuple())-n*sizes[idx]/2
  return b.cyl(p,n,max(sizes)/2+.25,float(sizes[idx]))
 return None

def refine(ids=None):
 # All nominal hardware seats are generated before printing; no pair suppression.
 allparts=list(b.PARTS)
 for old in allparts:
  if old['role'] not in ['printed_structure','printed_cover'] or ids is not None and old['id'] not in ids:continue
  s=b.SHAPES[old['id']];fr=old['frame'];owner=old['owner']
  for h in allparts:
   if h['role']!='hardware' or h['owner']!=owner or h['id'].startswith('ROOT-insert'):continue
   cutter=clearance(h,b.SHAPES[h['id']])
   if cutter is None:continue
   if h['frame']==fr:pass
   elif fr==c.frame(owner) and h['frame']==f'J{owner+1}.fixed':cutter=cutter.translate(b.V(c.L['joints'][owner]['offset']))
   elif fr==f'J{owner+1}.fixed' and h['frame']==c.frame(owner):cutter=cutter.translate(b.V(-np.array(c.L['joints'][owner]['offset'])))
   else:continue
   # Bounding boxes avoid unnecessary Boolean operations.
   a=s.BoundingBox();z=cutter.BoundingBox()
   if any(getattr(a,k+'max')<=getattr(z,k+'min') or getattr(z,k+'max')<=getattr(a,k+'min') for k in ['x','y','z']):continue
   s=s.cut(cutter,tol=1e-5).fix()
  # Compact wrist rotor carrier intersects one fixed shoulder screw head in
  # several poses; relief includes the entire circular sweep, not one pose.
  if old['id']=='P05-wrist-pitch-to-yaw':
   inf=c.I[4]
   for h in allparts:
    if not h['id'].startswith('J5-fixed-') or 'machining' not in h:continue
    m=h['machining'];p=np.array(m['p']);n=np.array(m['n']);v=p-inf['out'];rad=np.linalg.norm(v-n*np.dot(v,n));r=m['head'][0]/2+.4
    origin=inf['out']+n*(np.dot(v,n)+m['plate'])
    ring=b.ring(origin,n,rad+r,max(.1,rad-r),m['washer']+m['head'][1]+.4)
    s=s.cut(ring,tol=1e-5).fix()
  if old['id']=='P01-shoulder-monobloc':
   # Root fastening heads lie below shoulder rotor. Clear their circular sweep.
   jz=c.L['joints'][0]['offset'][2]
   for h in allparts:
    if not h['id'].startswith('ROOT-M4-') or 'machining' not in h:continue
    m=h['machining'];p=np.array(m['p'])-[0,0,jz];n=np.array(m['n']);rad=np.linalg.norm(p[:2]);r=m['head'][0]/2+.4
    s=s.cut(b.ring([0,0,p[2]+m['plate']],n,rad+r,rad-r,m['washer']+m['head'][1]+.4),tol=1e-5).fix()
  if old['id'] in ['P03-proximal-socket','P04-proximal-socket']:
   axis=3 if old['id'].startswith('P03') else 4
   for h in allparts:
    if not h['id'].startswith(f'J{axis}-output-') or 'machining' not in h:continue
    m=h['machining'];p=np.array(m['p']);n=np.array(m['n'])
    # Long straight 3mm-AF key ports through the socket end wall. The tube,
    # captive armour nuts and retention hardware are fitted afterwards.
    s=b.drill(s,p+n*m['plate'],n,4.2,100).fix()
  if old['id']=='P02-cross-shoulder':
   # J1 output screw heads are fixed relative to J2 fixed frame. A spherical
   # centre sweep about J2 Y bounds their entire orientation change.
   offset=np.array(c.L['joints'][1]['offset'])
   for h in allparts:
    if not h['id'].startswith('J1-output-') or 'machining' not in h:continue
    m=h['machining'];p=np.array(m['p'])+np.array(m['n'])*(m['plate']+m['washer']+m['head'][1]/2)-offset
    rad=math.hypot(p[0],p[2]);minor=math.hypot(m['head'][0]/2,m['head'][1]/2)+.4
    torus=cq.Solid.makeTorus(rad,minor,b.V([0,p[1],0]),b.V([0,1,0]))
    s=s.cut(torus,tol=1e-5).fix()
  if old['id'] in ['J7-armour-A','J7-armour-B']:
   # Fixed J6 screw heads sweep about yaw. The axial cylinder orientation
   # stays constant, so a tight annulus protects the entire yaw range.
   offset=np.array(c.L['joints'][6]['offset'])
   for h in allparts:
    if not h['id'].startswith('J6-fixed-') or 'machining' not in h:continue
    m=h['machining'];p=np.array(m['p']);n=np.array(m['n']);rad=math.hypot(p[0],p[1]);rr=m['head'][0]/2+.4
    org=np.array([0,0,p[2]])+n*(m['plate']+m['washer'])-offset
    s=s.cut(b.ring(org,n,rad+rr,max(.1,rad-rr),m['head'][1]+.4),tol=1e-5).fix()
  new=b.add(old['id'],s,owner,old['role'],old['material'],old['note']+' Hardware washer/head/nut clearance included.',fr)
  assert new['solid_count']==1,(old['id'],new['solid_count'])
 print('REFINED HARDWARE SEATS',flush=True)
