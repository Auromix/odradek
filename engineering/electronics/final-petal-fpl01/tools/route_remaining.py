# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Deterministic FPL01 local SW column/CS row buses, exact KiCad shapes.
Keep all LED positions. Reserved In2 ground. Unresolved paths go to router.
"""
import json,math,re,shutil,heapq,itertools,time
from pathlib import Path
from collections import defaultdict
import wx,pcbnew
app=wx.App(False);import sys
D=Path(sys.argv[1]).resolve();b=pcbnew.LoadBoard(str(D/'petal.kicad_pcb'))
u=pcbnew.FromMM;vec=lambda p:pcbnew.VECTOR2I(u(p[0]),u(p[1]))
poly=[[x,40-y] for x,y in json.loads((D.parent/'mechanical-power-budget.json').read_text())['board_outline_reference_mm']]
area=sum(a[0]*z[1]-z[0]*a[1] for a,z in zip(poly,poly[1:]+poly[:1]));sign=1 if area>0 else -1
layers=[pcbnew.F_Cu,pcbnew.In1_Cu,pcbnew.In2_Cu,pcbnew.In3_Cu,pcbnew.In4_Cu,pcbnew.B_Cu];obs=[];holes=[];records=[];failed=[];buckets=defaultdict(list)
def inside(p,m):return all(sign*((z[0]-a[0])*(p[1]-a[1])-(z[1]-a[1])*(p[0]-a[0]))/math.dist(a,z)>=m for a,z in zip(poly,poly[1:]+poly[:1]))
def addobs(sh,n,l):
 bb=pcbnew.SHAPE.BBox(sh);box=[bb.GetLeft()/1e6,bb.GetTop()/1e6,bb.GetRight()/1e6,bb.GetBottom()/1e6];i=len(obs);obs.append((sh,n,l,box))
 for gx in range(math.floor((box[0]-.5)/2),math.floor((box[2]+.5)/2)+1):
  for gy in range(math.floor((box[1]-.5)/2),math.floor((box[3]+.5)/2)+1):buckets[(gx,gy)].append(i)
for fp in b.GetFootprints():
 for pd in fp.Pads():
  for lay in layers:
   if pd.IsOnLayer(lay):addobs(pd.GetEffectiveShape(lay),pd.GetNetname(),lay)
for tr in b.GetTracks():
 if isinstance(tr,pcbnew.PCB_VIA):
  for lay in layers:addobs(tr.GetEffectiveShape(lay),tr.GetNetname(),lay)
  p=tr.GetPosition();holes.append(((p.x/1e6,p.y/1e6),tr.GetDrillValue()/1e6))
 else:addobs(tr.GetEffectiveShape(),tr.GetNetname(),tr.GetLayer())
def hits(shape,name,lay=None):
 bb=pcbnew.SHAPE.BBox(shape,u(.151));x0,y0,x1,y1=bb.GetLeft()/1e6,bb.GetTop()/1e6,bb.GetRight()/1e6,bb.GetBottom()/1e6
 ids=set()
 for gx in range(math.floor(x0/2),math.floor(x1/2)+1):
  for gy in range(math.floor(y0/2),math.floor(y1/2)+1):ids.update(buckets[(gx,gy)])
 return any(net!=name and (lay is None or layer==lay) and not (z1<x0 or z0>x1 or w1<y0 or w0>y1) and pcbnew.SHAPE.Collide(shape,sh,u(.151)) for sh,net,layer,(z0,w0,z1,w1) in (obs[i] for i in ids))
budget=json.loads((D.parent/'mechanical-power-budget.json').read_text())
mounts=[(x,40-y) for x,y in budget['mounts_xy_mm']]
def distseg(p,a,z):
 vx,vy=z[0]-a[0],z[1]-a[1];den=vx*vx+vy*vy
 t=max(0,min(1,((p[0]-a[0])*vx+(p[1]-a[1])*vy)/den)) if den else 0
 return math.dist(p,(a[0]+t*vx,a[1]+t*vy))
def recthit(a,z,box):
 # Liang-Barsky: inclusive segment/expanded rectangle intersection.
 lo,hi=0.,1.;dx,dy=z[0]-a[0],z[1]-a[1]
 for p,q in [(-dx,a[0]-box[0]),(dx,box[2]-a[0]),(-dy,a[1]-box[1]),(dy,box[3]-a[1])]:
  if abs(p)<1e-12:
   if q<0:return False
  else:
   t=q/p
   if p<0:lo=max(lo,t)
   else:hi=min(hi,t)
   if lo>hi:return False
 return True
def keepfree(a,z,r,layer,name):
 # Match the native circumscribed circular keepout with 0.01 extra geometric guard.
 if any(distseg(p,a,z)<3.26+r for p in mounts):return False
 if layer==pcbnew.B_Cu and name!='GND':
  q=r+.151
  if recthit(a,z,[62-q,43-q,66+q,47+q]):return False
 return True
def linefree(a,z,name,width,lay):return keepfree(a,z,width/2,lay,name) and inside(a,width/2+.251) and inside(z,width/2+.251) and not hits(pcbnew.SHAPE_SEGMENT(vec(a),vec(z),u(width)),name,lay)
def track(a,z,name,width,lay):
 if a==z:return True
 if not linefree(a,z,name,width,lay):return False
 tr=pcbnew.PCB_TRACK(b);tr.SetStart(vec(a));tr.SetEnd(vec(z));tr.SetWidth(u(width));tr.SetLayer(lay);tr.SetNet(b.FindNet(name));tr.SetLocked(True);b.Add(tr);tr.thisown=False;addobs(pcbnew.SHAPE_SEGMENT(vec(a),vec(z),u(width)),name,lay);records.append({'kind':'track','net':name,'a':a,'b':z,'width_mm':width,'layer':b.GetLayerName(lay)});return True
def viafree(p,name):return keepfree(p,p,.25,pcbnew.B_Cu,'__VIA__') and inside(p,.501) and not hits(pcbnew.SHAPE_CIRCLE(vec(p),u(.25)),name) and all(math.dist(p,h)>=.251+(dr+.25)/2 for h,dr in holes)
def via(p,name):
 if not viafree(p,name):return False
 v=pcbnew.PCB_VIA(b);v.SetPosition(vec(p));v.SetWidth(u(.5));v.SetDrill(u(.25));v.SetViaType(pcbnew.VIATYPE_THROUGH);v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu);v.SetNet(b.FindNet(name));v.SetLocked(True);b.Add(v);v.thisown=False
 for lay in layers:addobs(pcbnew.SHAPE_CIRCLE(vec(p),u(.25)),name,lay)
 holes.append((p,.25));records.append({'kind':'via','net':name,'xy':p,'diameter_mm':.5,'drill_mm':.25});return True
b.BuildConnectivity();pcbnew.ZONE_FILLER(b).Fill(b.Zones())
boarditems={x.m_Uuid.AsString():x for x in b.GetTracks()}
for fp in b.GetFootprints():
 for p in fp.Pads():boarditems[p.m_Uuid.AsString()]=p
route_records=[]
def cluster(obj):
 todo=[obj];seen={}
 while todo:
  v=todo.pop();key=v.m_Uuid.AsString();v=boarditems.get(key,v) # SWIG GetConnectedItems upcasts vias to PCB_TRACK; recover actual type by UUID
  if key in seen:continue
  seen[key]=v
  if isinstance(v,pcbnew.ZONE):continue
  todo.extend(b.GetConnectivity().GetConnectedItems(v))
 return seen
route_layers=[pcbnew.F_Cu,pcbnew.In1_Cu,pcbnew.In3_Cu,pcbnew.In4_Cu,pcbnew.B_Cu]
def anchors(items):
 result=[]
 for it in items.values():
  if isinstance(it,pcbnew.PCB_VIA):
   p=it.GetPosition();pts=[(p.x/1e6,p.y/1e6)];ls=range(len(route_layers))
  elif isinstance(it,pcbnew.PCB_TRACK):
   if it.GetLayer() not in route_layers:continue
   a=it.GetStart();z=it.GetEnd();a=(a.x/1e6,a.y/1e6);z=(z.x/1e6,z.y/1e6);n=max(1,math.ceil(math.dist(a,z)/.6));pts=[(a[0]+(z[0]-a[0])*i/n,a[1]+(z[1]-a[1])*i/n) for i in range(n+1)];ls=[route_layers.index(it.GetLayer())]
  elif isinstance(it,pcbnew.PAD):
   p=it.GetPosition();pts=[(p.x/1e6,p.y/1e6)];ls=[i for i,l in enumerate(route_layers) if it.IsOnLayer(l)]
  else:continue
  result += [(p,l) for p in pts for l in ls]
 return result
step=float(sys.argv[2]) if len(sys.argv)>2 else .2
def pt(k):return (round(k[0]*step,5),round(k[1]*step,5))
def gridanchors(items,name,width):
 result={}
 for a,li in anchors(items):
  k=(round(a[0]/step),round(a[1]/step),li);z=pt(k)
  if linefree(a,z,name,width,route_layers[li]):result[k]=a
 return result
pending=json.loads((D/'checks/drc.json').read_text())['unconnected_items']
# Route short local problems first; existing source connectivity is recalculated each time.
def issue_priority(v):
 text=' '.join(i['description'] for i in v['items'])
 ic=next(f for f in b.GetFootprints() if f.GetReference()=='U1').GetPosition();cx,cy=ic.x/1e6,ic.y/1e6
 vulnerable=any('Pad ' in i['description'] and 'of D' in i['description'] and abs(i['pos']['x']-cx)<9 and abs(i['pos']['y']-cy)<9 for i in v['items'])
 priority=-3 if vulnerable else 0 if 'of U1' in text or any('['+n+']' in text for n in ['SCLK','MOSI','MISO_HOST','MISO_IC','SS_N','VSYNC']) else 1 if any(k in text for k in ['[VLED_','[VCC_','[VCAP]','[VIO_','[IFS]']) else 2 if '[SW' in text else 3
 name=boarditems[v['items'][0]['uuid']].GetNetname()
 favored=__import__('os').environ.get('FPL_PRIORITY','').split(',')
 priority=-2 if name in favored else priority
 return (priority,math.hypot(v['items'][0]['pos']['x']-v['items'][1]['pos']['x'],v['items'][0]['pos']['y']-v['items'][1]['pos']['y']))
pending.sort(key=issue_priority)
for index,issue in enumerate(pending):
 boarditems.update({it.m_Uuid.AsString():it for it in b.GetTracks()}) # newly added vias also require canonical typed objects
 a,z=(boarditems[i['uuid']] for i in issue['items']);name=a.GetNetname();b.BuildConnectivity();ca=cluster(a);cz=cluster(z)
 if set(ca)&set(cz):continue
 if __import__('os').environ.get('FPL_ONLY') and name not in __import__('os').environ['FPL_ONLY'].split(','):continue
 if name=='GND':failed.append({'kind':'GND-still-disconnected','items':issue['items']});continue
 if len(ca)>len(cz):ca,cz=cz,ca
 width=.15 # existing project minimum; actual per-net length/drop audit governs power suitability
 starts=gridanchors(ca,name,width);targets=gridanchors(cz,name,width)
 if not starts or not targets:failed.append({'kind':'no-grid-access','net':name,'start_count':len(starts),'target_count':len(targets)});continue
 targetxy=[pt(k) for k in targets];hcache={};ecache={};vcache={}
 def heuristic(k):
  if k[:2] not in hcache:
   p=pt(k);hcache[k[:2]]=min(math.dist(p,t) for t in targetxy)
  return hcache[k[:2]]
 def edgefree(k,nk):
  key=tuple(sorted([k,nk]))
  if key not in ecache:ecache[key]=linefree(pt(k),pt(nk),name,width,route_layers[k[2]])
  return ecache[key]
 def vfree(k):
  key=k[:2]
  if key not in vcache:vcache[key]=viafree(pt(k),name)
  return vcache[key]
 serial=itertools.count();queue=[];cost={};prev={};origin={};goal=None;t0=time.time()
 for k,ap in starts.items():cost[k]=math.dist(pt(k),ap);origin[k]=k;heapq.heappush(queue,(cost[k]+heuristic(k),next(serial),cost[k],k))
 visited=0
 while queue and visited<int(__import__('os').environ.get('FPL_MAX_VISITS','150000')):
  _,_,g,k=heapq.heappop(queue)
  if g>cost[k]+1e-8:continue
  visited+=1
  if k in targets:goal=k;break
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   nk=(k[0]+dx,k[1]+dy,k[2]);ng=g+step*math.hypot(dx,dy)
   if ng>=cost.get(nk,1e12) or not edgefree(k,nk):continue
   cost[nk]=ng;prev[nk]=k;origin[nk]=origin[k];heapq.heappush(queue,(ng+heuristic(nk),next(serial),ng,nk))
  if vfree(k):
   for li in range(len(route_layers)):
    if li==k[2]:continue
    nk=(k[0],k[1],li);ng=g+2.0
    if ng>=cost.get(nk,1e12):continue
    cost[nk]=ng;prev[nk]=k;origin[nk]=origin[k];heapq.heappush(queue,(ng+heuristic(nk),next(serial),ng,nk))
 if goal is None:failed.append({'kind':'maze-unresolved','net':name,'visited':visited});print('FAIL',name,visited,time.time()-t0, 'bounds',[(i,len([k for k in cost if k[2]==i]), [min((pt(k)[a] for k in cost if k[2]==i),default=0) for a in [0,1]], [max((pt(k)[a] for k in cost if k[2]==i),default=0) for a in [0,1]]) for i in range(len(route_layers))],flush=True);continue
 nodes=[goal];k=goal
 while k in prev:k=prev[k];nodes.append(k)
 nodes.reverse();path=[(starts[origin[goal]],nodes[0][2])]+[(pt(n),n[2]) for n in nodes]+[(targets[goal],goal[2])]
 # Preserve all layer transitions; simplify only line-of-sight in one layer.
 simple=[path[0]];i=0
 while i<len(path)-1:
  li=path[i][1];j=i+1
  while j<len(path)-1 and path[j+1][1]==li:j+=1
  if path[i+1][1]!=li:j=i+1
  else:
   while j>i+1 and not linefree(path[i][0],path[j][0],name,width,route_layers[li]):j-=1
  simple.append(path[j]);i=j
 for (aa,li),(zz,lj) in zip(simple,simple[1:]):
  if li==lj:assert track(aa,zz,name,width,route_layers[li]),(name,aa,zz)
  else:assert aa==zz and via(aa,name),(name,aa,zz)
 rec={'net':name,'width_mm':width,'visited':visited,'elapsed_s':round(time.time()-t0,3),'path_mm_layer':simple};route_records.append(rec);print('ROUTED',name,len(simple),'nodes',visited,'seconds',rec['elapsed_s'],flush=True)
 # Save after each net so a bounded interruption does not discard verified work.
 b.BuildConnectivity();pcbnew.ZONE_FILLER(b).Fill(b.Zones());pcbnew.SaveBoard(str(D/'petal.kicad_pcb'),b)
(D/('route-'+str(step)+'mm.json')).write_text(json.dumps({'method':'native-shape-checked 0.1mm lattice A*; exact line-of-sight simplification; In2 reserved GND; not a substitute for final native DRC','step_mm':step,'routes':route_records,'all_added_shapes':records,'unresolved':failed},indent=2)+'\n')
b.BuildConnectivity();pcbnew.ZONE_FILLER(b).Fill(b.Zones());pcbnew.SaveBoard(str(D/'petal.kicad_pcb'),b);None
print('COMPLETE',len(route_records),'unresolved',failed)
