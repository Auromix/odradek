# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Continuous support-function covers; only new-to-other interfaces are claimed."""
import sys,itertools,math,json
from pathlib import Path
import numpy as np,cadquery as cq
from scipy.spatial import HalfspaceIntersection,ConvexHull
from shapely.geometry import Polygon,box as box2,LineString
R=Path(__file__).resolve().parents[3];sys.path.insert(0,str(R/'engineering'));import r5_limit01 as c
W=Path(__file__).resolve().parent
registry={}
th=np.arange(128)*2*np.pi/128;ns=np.c_[np.cos(th),np.sin(th)]
def maxcos(theta,a,b):
 # interval may cross2pi; test closest copies of its interior and endpoints
 vals=[np.cos(theta-a),np.cos(theta-b)]
 v=np.maximum(*vals)
 for k in [-1,0,1]:
  z=theta+2*np.pi*k;v=np.where((z>=a)&(z<=b),1.,v)
 return v

def prism_support(h,y,inside):
 h=h+np.where(ns[:,0]>=0,91,31)*ns[:,0]+20*ns[:,1]+1e-5
 inter=np.array(inside)+[61,20]
 hs=HalfspaceIntersection(np.c_[ns,-h],inter).intersections;pts=hs[ConvexHull(hs).vertices]
 poly=Polygon(pts).simplify(1e-7,preserve_topology=True);yp=[y[0]-.001,y[1]+.001];shape=c.xzpoly(poly,*yp);assert shape.isValid();registry[id(shape)]=(poly,yp);return shape
def envbox(b,rot=False,q0=0.,q1=np.pi/2):
 corners=list(itertools.product(b[:,0],b[:,2]));h=np.full(128,-np.inf)
 for x,z in corners:
  if rot:v=math.hypot(x,z)*maxcos(th,math.atan2(z,x)+q0,math.atan2(z,x)+q1)
  else:v=ns@np.array([x,z])
  h=np.maximum(h,v)
 mid=b.mean(axis=0)[[0,2]]
 if rot:
  a=(q0+q1)/2;mid=np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])@mid
 return prism_support(h,b[:,1],mid)
def circe(r,y):return prism_support(np.ones(128)*r,y,[0,0])
def came(r,y,hub=False):
 h=r+8*maxcos(th,-np.pi/4,np.pi/4)
 if hub:h=np.maximum(7,h)
 return prism_support(h,y,[0,0] if hub else[8,0])
def B(x0,x1,y0,y1,z0,z1):return np.array([[x0,y0,z0],[x1,y1,z1]],float)
rows,added,_=c.build();newids={r['id'] for r in added};data=[]
for r in rows:
 n=r['id'];s=r['shape'];parts=[]
 if n=='rotor_split_trunnion_cradle':
  parts=[envbox(B(0,23,-11.8,11.8,-7.5,-3.5),True)]
  for sign in [1,-1]:
   for rad,a,b in [(7.5,9.2,12.5),(5,12.5,13),(4,13,29 if sign==1 else 18.8)]:parts.append(circe(rad,[a,b] if sign==1 else[-b,-a]))
 elif n=='detachable_cam_crank':parts=[came(5,[21,28.5],True)]
 elif n=='IKO_CFS4':parts=[came(4,[20.5,35.5])]
 elif n=='custom_D3_crosspin':parts=[circe(math.hypot(7,1.5),[21.5,24.5])]
 elif n=='IKO_CFS4_supplied_nut':parts=[came(7/math.sqrt(3),[21.3,24.5])]
 elif n.startswith('bearing_pedestal'):
  bs=[B(-11,11,13,19,-11,11),B(-10,10,12,13,-10,10),B(8,18,13,19,-26,-6),B(8,35,11,22,-30,-26)]+[B(x-4,x+4,13,19,-18,-7) for x in[0,10]]
  if n.endswith('negative'):
   for b in bs:b[:,1]=[-b[1,1],-b[0,1]]
  parts=[envbox(b) for b in bs]
 elif n.startswith('outer_cap'):
  bs=[B(-10,10,19,20,-10,10)]+[B(x-4,x+4,19,20,-18,-7) for x in[0,10]]
  if n.endswith('negative'):
   for b in bs:b[:,1]=[-b[1,1],-b[0,1]]
  parts=[envbox(b) for b in bs]
 elif n=='external_negative_side_stop_arch':
  bs=[B(-4,28,-26,-23.5,-18,-10),B(12,28,-26,-23.5,-18,17.5),B(-8,28,-26,-23.5,11.5,14.5),B(-8,8,-26,-23.5,7,19),B(17,27,-26,-23.5,-16,-6),B(-8,-3,-31,-21,10.5,16),B(19,25,-31,-21,-21,-16),B(-3,7,-23.5,-20.5,8,8.9),B(-3,7,-23.5,-20.5,17.1,18),B(16.9,17.9,-23.5,-20.5,-16,-6),B(26.1,27.1,-23.5,-20.5,-16,-6)]
  parts=[envbox(b) for b in bs]
 elif n=='upper_guard_contact_bridge':
  q=np.radians(89.5);xm=(3.5+14.5*np.cos(q))/np.sin(q)
  parts=[envbox(B(-2,7.5,-23.5,-20.5,9,17)),envbox(B(-2,xm,-23.5,-9.5,11.5,14.5))]
 elif n=='lower_guard_contact_bridge':parts=[envbox(B(18,26,-23.5,-19.5,-15,-5.5)),envbox(B(20,23,-23.5,-9.5,-12,-7.29))]
 elif r['group']=='guide':
  rr=np.linspace(31,91,241);qa=np.radians(np.array([c.qR(x) for x in rr])-45)
  line=LineString(np.c_[rr+8*np.cos(qa),20+8*np.sin(qa)])
  poly=line.buffer(7.15,resolution=48)
  for x in [45,94]:poly=poly.union(box2(x-4,-16,x+4,20))
  poly=poly.difference(line.buffer(4.15,resolution=48))
  # Fill bolt holes conservatively. Boundary is identical to the frozen guide.
  env=c.xzpoly(poly,29.999,34.001)
  for hole in poly.interiors:env=env.cut(c.xzpoly(Polygon(hole),29.99,34.01))
  registry[id(env)]=(poly,[29.999,34.001]);parts=[env]
 else:parts=[envbox(c.bbox(s),r['group']=='rotor')]
 for i,p in enumerate(parts):data.append(dict(id=n+f'/{i}',new=n in newids,shape=p,poly=registry[id(p)][0],y=registry[id(p)][1]))
# Actual frozen shape strips; rotating their bounding rectangles is conservative.
petals={}
for kind in ['upper','lower']:
 sh=cq.Compound.makeCompound(list(c.petal(kind,'right').values()));pp=[]
 L=150 if kind=='upper' else 100
 for x in np.arange(0,L,5):
  ss=sh.intersect(c.box(x,x+5,-100,100,-100,100));b=c.bbox(ss)
  for hand in ['right','left']:
   bb=b.copy()
   if hand=='left':bb[:,1]=[-b[1,1],-b[0,1]]
   intervals=np.linspace(0,np.pi/2,13) if kind=='upper' and x==20 else [0,np.pi/2]
   for qi in range(len(intervals)-1):
    ev=envbox(bb,True,intervals[qi],intervals[qi+1]);pp.append(dict(id=f'FORM02_{kind}_{hand}_{x}/q{qi}',hand=hand,shape=ev,poly=registry[id(ev)][0],y=registry[id(ev)][1],new=False))
 petals[kind]=pp

# A continuous cover is based on every primitive box corner, not angle samples.
# Verify native home solids belong to their analytic covers; the support theorem
# then includes the full independent R/q range. Native STEP tolerance is explicit.
contain=[]
for r in rows:
 ps=[p['shape'] for p in data if p['id'].startswith(r['id']+'/')]
 home=r['shape'] if r['group']=='guide' else c.pose(r['shape'],31,0)
 residual=home
 for cover in ps:
  if c.vol(residual)<1e-8:break
  residual=residual.cut(cover)
 outside=c.vol(residual);assert outside<1e-4,(r['id'],outside)
 contain.append(dict(id=r['id'],outside_cover_home_mm3=outside))
# Orthogonal prism geometry: if distance<d, each XZ polygon must have a
# point with X in the other prism's transformed Y range enlarged by d,
# and those two clipped Z intervals must be separated by less than d.
# The contrapositive gives a rigorous lower bound, including asynchronous R/q.
def interval(poly,xlo,xhi):
 p=poly.intersection(box2(xlo,-1000,xhi,1000))
 return None if p.is_empty else [p.bounds[1],p.bounds[3]]
def separated(a,b,ang,d):
 if ang==180:
  # All these local covers remain at positive radial X.
  return a['poly'].bounds[0]+b['poly'].bounds[0]>=d
 if ang==90:
  ar=[-b['y'][1]-d,-b['y'][0]+d];br=[a['y'][0]-d,a['y'][1]+d]
 elif ang==270:
  ar=[b['y'][0]-d,b['y'][1]+d];br=[-a['y'][1]-d,-a['y'][0]+d]
 else:raise AssertionError(ang)
 A=interval(a['poly'],*ar);B=interval(b['poly'],*br)
 return A is None or B is None or max(A[0]-B[1],B[0]-A[1])>=d
res=[]
for aa,bb in itertools.combinations(c.FINGERS,2):
 ka,ha,pa=c.FINGERS[aa];kb,hb,pb=c.FINGERS[bb];ang=(pb-pa)%360
 A=data+[p for p in petals[ka] if p['hand']==ha];B=data+[p for p in petals[kb] if p['hand']==hb]
 best=1e3;critical=None;unproven=[]
 for a,b in itertools.product(A,B):
  if not(a['new'] or b['new']):continue
  if not separated(a,b,ang,1e-6):unproven.append([a['id'],b['id']]);continue
  # Only refine potential improvements; all other pairs have this certified bound.
  if separated(a,b,ang,best):continue
  lo=0.;hi=best
  for _ in range(35):
   mid=(lo+hi)/2
   if separated(a,b,ang,mid):lo=mid
   else:hi=mid
  best=lo;critical=[a['id'],b['id']]
 r=dict(pair=[aa,bb],distance_lower_bound_mm=max(0,best-1e-5),critical_cover_pair=critical,unproven_cover_pairs=unproven)
 res.append(r);print(r,flush=True)
out=dict(scope='All independent R31..91,q0..90, NEW interfaces only; exact support-function outer covers plus orthogonal-prism distance bound. Does not certify all old-old hardware interfaces.',support_directions=128,support_padding_mm=1e-5,axial_y_padding_mm=.001,polygon_simplify_tolerance_mm=1e-7,containment=contain,rows=res,
 source_hashes={str(p.relative_to(R)):c.sha(p) for p in [Path(__file__),R/'engineering/r5_limit01.py',R/'engineering/r5_carrier01.py',R/'engineering/generated/r5-carrier01/parts-manifest.json']},
 method='For each bbox corner, maximize x*cos(q)-z*sin(q) and x*sin(q)+z*cos(q) support over the entire quarter-circle; add independent radial interval support. Intersect 128 outward halfspaces. Exact XZ-prism clipping by orthogonal Y bands enlarged by d yields a sufficient distance>=d predicate; bisection only tightens this sufficient bound. Old guide holes filled conservatively. Curved solids were not replaced by a smaller shape.')
c.dump(W/'continuous-new-interfaces.json',out)
