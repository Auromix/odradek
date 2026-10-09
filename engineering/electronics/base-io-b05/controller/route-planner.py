# SPDX-License-Identifier: CC-BY-NC-4.0
import json, heapq, math
from pathlib import Path
from shapely.geometry import Point, LineString, box, Polygon
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
removed_lines=['28e291ba5984bd24', 'a5c63f2c8723efc4', '23998e879fc57f95', 'e59212dc79f53816']
assert all(any(p['primitiveId']==i and p['net']=='LAMP5V' for p in d['lines']) for i in removed_lines)
objects=[]
for p in d['pads']:
 for ly in ([1,2,15,16] if p['layer'] in [12] else [p['layer']]):objects.append((p['net'],ly,padshape(p)))
for l in d['lines']:
 if l['primitiveId'] in removed_lines:continue
 if l['net'] and l['layer'] in [1,2,15,16]:objects.append((l['net'],l['layer'],LineString([xy(l['startX'],l['startY']),xy(l['endX'],l['endY'])]).buffer(l['lineWidth']*.0254/2)))
for v in d['vias']:
 for ly in [1,2,15,16]:objects.append((v['net'],ly,Point(xy(v['x'],v['y'])).buffer(v['diameter']*.0254/2)))
for r in d.get('regions',[]):
 nums=[n for n in r['complexPolygon']['polygon'] if isinstance(n,(int,float))]
 poly=Polygon([xy(nums[i],nums[i+1]) for i in range(0,len(nums),2)])
 if 5 in r['ruleType']:objects.append(('__KEEP_OUT__',r['layer'],poly.buffer(r['lineWidth']*.0254/2)))
routes=[]
vias=[]
cs={c['designator']:c for c in d['components']}
def pin(c,n):
 p=next(p for p in d['pads'] if p['primitiveId'].startswith(cs[c]['primitiveId']) and p['padNumber']==str(n))
 return xy(p['x'],p['y'])
grid=.1; xs=np.arange(1,115.01,grid);ys=np.arange(1,55.01,grid);XX,YY=np.meshgrid(xs,ys,indexing='ij')
def route(net,layer,a,b,width=.5):
 margin=.18+width/2
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

# Connect all new controller pins and selected legacy rail anchors using a
# nearest tree. Reuse existing copper only via authoritative pin anchors.
from collections import defaultdict
spec=json.loads((R/'specification.json').read_text());new={p['ref'] for p in spec['specs']};groups=defaultdict(list)
for c,ps in d['pins'].items():
 if c in new:
  for p in ps:
   if p['net']:groups[p['net']].append(xy(p['x'],p['y']))
groups['LAMP5V'].extend([xy(v['x'],v['y']) for v in d['vias'] if v['net']=='LAMP5V']);groups['LAMP5V'].append(pin('J7',1));groups['RETURN48'].append(pin('U1',2));groups['LAMP_PWM'].append(pin('J7',2))
def via_ok(net,p):
 s=Point(p).buffer(.3+.18)
 return 1<p[0]<115 and 1<p[1]<55 and not any(n!=net and ly in (1,2,15,16) and s.intersects(o) for n,ly,o in objects)
def add_via(net,p):
 vias.append(dict(net=net,point=list(p),hole_mm=.3,diameter_mm=.6))
 for ly in [1,2,15,16]:objects.append((net,ly,Point(p).buffer(.3)))
def has_via(net,p):
 return any(v['net']==net and math.dist(v['point'],p)<.002 for v in vias) or any(v['net']==net and math.dist(xy(v['x'],v['y']),p)<.002 for v in d['vias']) or any(t['net']==net and t['layer']==12 and math.dist(xy(t['x'],t['y']),p)<.002 for t in d['pads'])
def connect(net,a,b):
 width=.25 if net in ('LAMP5V','RETURN48','CTRL3V3') else .2
 try:
  if net=='LAMP_PWM' or (net=='LAMP5V' and math.dist(a,b)>8):raise ValueError('Prefer bottom for long PWM branch')
  route(net,1,a,b,width);return
 except ValueError:pass
 # Both endpoint pads are SMD. Place through vias outside their lands, then
 # use the bottom layer. All branches roll back together on a failed attempt.
 candidates=[]
 for p in (a,b):
  if has_via(net,p):
   candidates.append([p]);continue
  opts=[(p[0]+dx,p[1]+dy) for dx,dy in [(0,1.5),(0,-1.5),(1.5,0),(-1.5,0),(0,2.2),(0,-2.2),(2.2,0),(-2.2,0)]]
  candidates.append([v for v in opts if via_ok(net,v)])
 saved=(len(objects),len(routes),len(vias))
 for va in candidates[0]:
  for vb in candidates[1]:
   try:
    if not has_via(net,va):add_via(net,va)
    if not has_via(net,vb):add_via(net,vb)
    if math.dist(a,va)>.001:route(net,1,a,va,width)
    route(net,2,va,vb,width)
    if math.dist(vb,b)>.001:route(net,1,vb,b,width)
    return
   except ValueError:
    del objects[saved[0]:];del routes[saved[1]:];del vias[saved[2]:]
 raise ValueError(('No two-layer route',net,a,b))
# Explicit staggered TSSOP fanout, with no via-in-pad.
fanout={4:(18,19.35),5:(20,19.5),6:(21,19.7),9:(22.2758,19.37144),10:(22.92604,20.37144),13:(21.62556,10.6285),18:(18.37436,10.6285),19:(17.72412,9.6285)}
for pn,pos in fanout.items():
 pp=next(p for p in d['pins']['U2'] if p['padNumber']==str(pn));net=pp['net'];a=xy(pp['x'],pp['y'])
 assert via_ok(net,pos),(net,pos,'fanout via blocked')
 add_via(net,pos);route(net,1,a,pos,.2);groups[net]=[pos if math.dist(t,a)<.001 else t for t in groups[net]]
a=pin('J7',2);pos=(82.69986,31.1)
assert via_ok('LAMP_PWM',pos),('J7 PWM via blocked',pos)
add_via('LAMP_PWM',pos);route('LAMP_PWM',1,a,pos,.2)
groups['LAMP_PWM']=[pos if math.dist(t,a)<.001 else t for t in groups['LAMP_PWM']]
a=pin('J7',1);pos=(85.7,28.8)
assert via_ok('LAMP5V',pos),('J7 5V via blocked',pos)
add_via('LAMP5V',pos);route('LAMP5V',1,a,pos,.25)
groups['LAMP5V']=[pos if math.dist(t,a)<.001 else t for t in groups['LAMP5V']]
route('LAMP5V',1,pin('U3',1),pin('U3',3),.25)
route('LAMP5V',1,pin('U3',3),pin('C5',1),.25)
order=['CTRL3V3','RETURN48','CTRL_NRST','CTRL_SWDIO','CTRL_SWCLK','MCU_PWM','MCU_TX','MCU_RX','UART_TX','UART_RX','LAMP_PWM','LAMP5V']
for net in order:
 pts=list(dict.fromkeys(groups[net]));connected=[pts.pop(0)]
 while pts:
  _,i,j=min((math.dist(a,b),i,j) for i,a in enumerate(connected) for j,b in enumerate(pts))
  a,b=connected[i],pts.pop(j);connect(net,a,b);connected.append(b)
(R/'routes.json').write_text(json.dumps(dict(routes=routes,vias=vias,removed_lines=removed_lines),indent=2)+'\n')
print('PLANNED',len(routes),'branches',len(vias),'vias')
