# SPDX-License-Identifier: CC-BY-NC-4.0
import json, heapq, math
from pathlib import Path
from shapely.geometry import Point, LineString, box
from shapely.affinity import rotate
from shapely.ops import unary_union
from shapely import contains_xy
import numpy as np
R=Path(__file__).parent
d=json.loads((R/'route-input.json').read_text())['value']
xy=lambda x,y:(x*.0254,-y*.0254)
def padshape(p):
 x,y=xy(p['x'],p['y']);w,h=[v*.0254 for v in p['pad'][1:3]]
 s=Point(x,y).buffer(w/2) if p['pad'][0]=='ELLIPSE' and abs(w-h)<.01 else box(x-w/2,y-h/2,x+w/2,y+h/2)
 return rotate(s,-p['rotation'],origin=(x,y))
objects=[]
for p in d['pads']:
 for ly in ([1,2,15,16] if p['layer'] in [12] else [p['layer']]):objects.append((p['net'],ly,padshape(p)))
for l in d['lines']:
 if l['net'] and l['layer'] in [1,2,15,16]:objects.append((l['net'],l['layer'],LineString([xy(l['startX'],l['startY']),xy(l['endX'],l['endY'])]).buffer(l['lineWidth']*.0254/2)))
for v in d['vias']:
 for ly in [1,2,15,16]:objects.append((v['net'],ly,Point(xy(v['x'],v['y'])).buffer(v['diameter']*.0254/2)))
routes=[]
vias=[dict(net='LAMP_FUSED48',point=[95.5,25.5],hole_mm=.6,diameter_mm=1.0),dict(net='LAMP_FUSED48',point=[89.5,25.5],hole_mm=.6,diameter_mm=1.0),dict(net='RETURN48',point=[75,24.5],hole_mm=.6,diameter_mm=1.0),dict(net='RETURN48',point=[68,29],hole_mm=.6,diameter_mm=1.0),dict(net='LAMP5V',point=[74.7,22],hole_mm=.6,diameter_mm=1.0),dict(net='RETURN48',point=[80,33.8],hole_mm=.6,diameter_mm=1.0)]
for v in vias:
 for ly in [1,2,15,16]:objects.append((v['net'],ly,Point(v['point']).buffer(.5)))
cs={c['designator']:c for c in d['components']}
def pin(c,n):
 p=next(p for p in d['pads'] if p['primitiveId'].startswith(cs[c]['primitiveId']) and p['padNumber']==str(n))
 return xy(p['x'],p['y'])
grid=.1; xs=np.arange(1,115.01,grid);ys=np.arange(1,55.01,grid);XX,YY=np.meshgrid(xs,ys,indexing='ij')
def route(net,layer,a,b,width=.5):
 margin=.4+width/2
 obs=unary_union([s.buffer(margin) for n,ly,s in objects if ly==layer and n!=net])
 mask=contains_xy(obs,XX,YY)
 start=tuple(round((a[i]-1)/grid) for i in range(2));goal=tuple(round((b[i]-1)/grid) for i in range(2))
 if mask[start] or mask[goal]:raise ValueError(('Blocked endpoint',net,a,b))
 q=[(0,0,start)];cost={start:0};prev={};found=False
 dirs=[(1,0),(0,1),(-1,0),(0,-1),(1,1),(-1,1),(-1,-1),(1,-1)]
 while q:
  _,g,c=heapq.heappop(q)
  if g!=cost.get(c):continue
  if c==goal:found=True;break
  for dx,dy in dirs:
   n=(c[0]+dx,c[1]+dy)
   if not(0<=n[0]<len(xs) and 0<=n[1]<len(ys)) or mask[n]:continue
   if dx and dy and (mask[c[0]+dx,c[1]] or mask[c[0],c[1]+dy]):continue
   ng=g+math.hypot(dx,dy)
   if ng<cost.get(n,1e99):
    cost[n]=ng;prev[n]=c;heapq.heappush(q,(ng+math.dist(n,goal),ng,n))
 if not found:raise ValueError(('No route',net,a,b))
 pts=[goal];c=goal
 while c!=start:c=prev[c];pts.append(c)
 pts=pts[::-1];out=[tuple(a)];lastdir=None
 for i in range(1,len(pts)):
  direction=(pts[i][0]-pts[i-1][0],pts[i][1]-pts[i-1][1])
  if lastdir is not None and direction!=lastdir:out.append((1+pts[i-1][0]*grid,1+pts[i-1][1]*grid))
  lastdir=direction
 out.append(tuple(b))
 smoothed=[out[0]]; i=0
 while i<len(out)-1:
  j=len(out)-1
  while j>i+1 and LineString([out[i],out[j]]).intersects(obs):j-=1
  smoothed.append(out[j]);i=j
 out=smoothed
 if LineString(out).intersects(obs):raise ValueError(('Exact path intersects obstacle',net,out))
 routes.append(dict(net=net,layer=layer,points=out,width_mm=width))
 objects.append((net,layer,LineString(out).buffer(width/2)))
 print(net,layer,round(LineString(out).length,2),len(out),flush=True)
route('LAMP_FUSED48',1,pin('F1',1),(95.5,25.5))
route('LAMP_FUSED48',15,(95.5,25.5),(89.5,25.5))
route('LAMP_FUSED48',1,(89.5,25.5),pin('D1',2))
route('LAMP_VIN',1,pin('D1',1),pin('C1',2))
route('LAMP_VIN',1,pin('C1',2),pin('U1',1))
route('LAMP5V',2,pin('U1',3),(74.7,22),.3)
route('LAMP5V',1,(74.7,22),pin('C2',2),.3)
route('LAMP5V',1,pin('C2',2),pin('R1',2))
route('LAMP5V',1,pin('C2',2),pin('J7',1),.3)
route('RETURN48',2,pin('U1',2),pin('J5',1))
route('RETURN48',2,pin('U1',2),(75,24.5))
route('RETURN48',2,pin('U1',2),(68,29))
route('RETURN48',1,(75,24.5),pin('C1',1))
route('RETURN48',1,(68,29),pin('C2',1))
route('RETURN48',1,(68,29),pin('R1',1))
route('RETURN48',2,pin('U1',2),(80,33.8),.3)
route('RETURN48',1,(80,33.8),pin('J7',4),.3)
route('RETURN48',1,pin('J7',4),pin('J7',3),.3)
route('RETURN48',1,pin('J7',3),pin('J7',5),.3)
route('RETURN48',1,pin('J7',5),pin('J7',4),.3)
(R/'routes.json').write_text(json.dumps(dict(routes=routes,vias=vias),indent=2)+'\n')
