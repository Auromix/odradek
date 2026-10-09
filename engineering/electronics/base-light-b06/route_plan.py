# SPDX-License-Identifier: CC-BY-NC-4.0
"""Plan the low-current two-layer lamp routes from actual editor readback.

Numerical clearance audit is independent of the native editor DRC. Not SI proof.
"""
import json, math, heapq, hashlib
from pathlib import Path
import numpy as np
from shapely import contains_xy
from shapely.geometry import Point,LineString,box
from shapely.affinity import rotate
from shapely.ops import unary_union
HERE=Path(__file__).resolve().parent
SRC=HERE/'reports/connected-native-50x14.json'
P=json.loads(SRC.read_text())['value']['pcb']
pads=[p for c in P for p in c['pads']]
STEP=.1;WIDTH=.25;GAP=.20;PLAN_GAP=.22;VD=.6;VH=.3
X,Y=np.meshgrid(np.arange(.5,49.5+STEP/2,STEP),np.arange(.5,13.5+STEP/2,STEP))
routes=[];vias=[]
holes=[(2,5,2.4),(48,5,2.4),(8,4,3.2),(42,4,3.2)]
def xy(p):return [p['x']*.0254,-p['y']*.0254]
def shape(p):
 x,y=xy(p);a,b=[v*.0254 for v in p['pad'][1:3]]
 return rotate(box(x-a/2,y-b/2,x+a/2,y+b/2),-p['rotation'],origin=(x,y))
def obs(net,layer,via=False):
 margin=VD/2 if via else WIDTH/2
 items=[Point(x,y).buffer(d/2+.35+margin) for x,y,d in holes]
 for p in pads:
  if via or (layer==p['layer'] and p['net']!=net):items.append(shape(p).buffer(PLAN_GAP+margin))
 for r in routes:
  if (via or r['layer']==layer) and r['net']!=net:items.append(LineString(r['points']).buffer(WIDTH/2+PLAN_GAP+margin))
 for v in vias:
  if via or v['net']!=net:items.append(Point(v['point']).buffer(VD/2+PLAN_GAP+margin))
 return unary_union(items)
def idx(p):return (int(round((p[1]-.5)/STEP)),int(round((p[0]-.5)/STEP)))
def pt(i):return [round(.5+i[1]*STEP,4),round(.5+i[0]*STEP,4)]
def route(net,start,end):
 blocked=np.array([contains_xy(obs(net,l).buffer(.06),X,Y) for l in [1,2]])
 vb=contains_xy(unary_union([obs(net,l,True) for l in [1,2]]).buffer(.06),X,Y)
 s=(0,*idx(start));t=(0,*idx(end));blocked[s]=False;blocked[t]=False
 q=[(0,0,s)];dist={s:0};prev={}
 while q:
  _,d,a=heapq.heappop(q)
  if d>dist[a]+1e-9:continue
  if a==t:
   path=[a]
   while path[-1]!=s:path.append(prev[path[-1]])
   path.reverse();chunks=[];layer=1;raw=[start]
   for old,new in zip(path,path[1:]):
    p=pt(new[1:])
    if old[0]!=new[0]:
     raw.append(p);chunks.append((layer,raw));raw=[p];layer=new[0]+1
     if not any(math.dist(p,v['point'])<.01 and v['net']==net for v in vias):vias.append(dict(net=net,point=p,hole_mm=VH,diameter_mm=VD))
    else:raw.append(p)
   raw[-1]=end;chunks.append((layer,raw))
   for layer,raw in chunks:
    if len(raw)<2:continue
    obstacle=obs(net,layer);compact=[raw[0]];i=0
    while i<len(raw)-1:
     for j in range(len(raw)-1,i,-1):
      if not LineString([raw[i],raw[j]]).intersects(obstacle):break
     if j==i or LineString([raw[i],raw[j]]).intersects(obstacle):raise RuntimeError('Clearance '+net)
     compact.append(raw[j]);i=j
    routes.append(dict(net=net,layer=layer,width_mm=WIDTH,points=compact))
   return
  for dl,dy,dx in [(0,-1,0),(0,1,0),(0,0,-1),(0,0,1),(1,0,0)]:
   b=(1-a[0],a[1],a[2]) if dl else (a[0],a[1]+dy,a[2]+dx)
   if not (0<=b[1]<Y.shape[0] and 0<=b[2]<X.shape[1]):continue
   if blocked[b] or (dl and vb[a[1:]]):continue
   nd=d+(50 if dl else 1)
   if nd<dist.get(b,float('inf')):
    dist[b]=nd;prev[b]=a
    h=abs(b[1]-t[1])+abs(b[2]-t[2])+50*(b[0]!=t[0])
    heapq.heappush(q,(nd+h,nd,b))
 raise RuntimeError('No route '+net)
# Short individual LED branches first, then shared returns and power.
for net in ['LED1_A','LED2_A','LED3_A','GATE','PWM_IN','5V_IN','LED_K','VLED','GND']:
 points=[xy(p) for p in pads if p['net']==net]
 connected=[points.pop(0)]
 while points:
  a,b=min(((a,b) for a in connected for b in points),key=lambda t:math.dist(*t))
  route(net,a,b);connected.append(b);points.remove(b)
 print('ROUTED',net,len(routes),len(vias),flush=True)
# Check all copper against foreign pads, paths and holes, exact continuous shapes.
violations=[]
for i,a in enumerate(routes):
 sa=LineString(a['points']).buffer(a['width_mm']/2)
 for p in pads:
  if a['layer']==p['layer'] and a['net']!=p['net'] and sa.distance(shape(p))<GAP-1e-6:violations.append(['pad',i,p['primitiveId']])
 for j,b in enumerate(routes[:i]):
  if a['layer']==b['layer'] and a['net']!=b['net'] and sa.distance(LineString(b['points']).buffer(b['width_mm']/2))<GAP-1e-6:violations.append(['route',i,j])
 for x,y,d in holes:
  if sa.distance(Point(x,y).buffer(d/2))<.35-1e-6:violations.append(['hole',i,x,y])
if violations:raise RuntimeError(violations)
out=dict(source_sha256=hashlib.sha256(SRC.read_bytes()).hexdigest(),units='mm, u right/v down',routes=routes,vias=vias,width_mm=WIDTH,gap_mm=GAP,numerical_clearance_pass=True)
(HERE/'route-plan.json').write_text(json.dumps(out,indent=2)+'\n')
print('PLAN',len(routes),'route chunks',len(vias),'vias')
