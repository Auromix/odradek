# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Deterministic FPL01 local SW column/CS row buses, exact KiCad shapes.
Keep all LED positions. Reserved In2 ground. Unresolved paths go to router.
"""
import json,math,re,shutil
from pathlib import Path
from collections import defaultdict
import wx,pcbnew
app=wx.App(False);import sys
D=Path(sys.argv[1]).resolve();b=pcbnew.LoadBoard(str(D/'petal.kicad_pcb'))
u=pcbnew.FromMM;vec=lambda p:pcbnew.VECTOR2I(u(p[0]),u(p[1]))
poly=[[x,40-y] for x,y in json.loads((D.parent/'mechanical-power-budget.json').read_text())['board_outline_reference_mm']]
area=sum(a[0]*z[1]-z[0]*a[1] for a,z in zip(poly,poly[1:]+poly[:1]));sign=1 if area>0 else -1
layers=[pcbnew.F_Cu,pcbnew.In1_Cu,pcbnew.In2_Cu,pcbnew.In3_Cu,pcbnew.In4_Cu,pcbnew.B_Cu];obs=[];holes=[];records=[];failed=[]
def inside(p,m):return all(sign*((z[0]-a[0])*(p[1]-a[1])-(z[1]-a[1])*(p[0]-a[0]))/math.dist(a,z)>=m for a,z in zip(poly,poly[1:]+poly[:1]))
def addobs(sh,n,l):
 bb=pcbnew.SHAPE.BBox(sh);obs.append((sh,n,l,[bb.GetLeft()/1e6,bb.GetTop()/1e6,bb.GetRight()/1e6,bb.GetBottom()/1e6]))
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
 return any(net!=name and (lay is None or layer==lay) and not (z1<x0 or z0>x1 or w1<y0 or w0>y1) and pcbnew.SHAPE.Collide(shape,sh,u(.151)) for sh,net,layer,(z0,w0,z1,w1) in obs)
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
byref={fp.GetReference():fp for fp in b.GetFootprints()}
def point(ref,num):
 p=next(p for p in byref[ref].Pads() if p.GetNumber()==str(num)).GetPosition();return p.x/1e6,p.y/1e6
def connectpath(ref,pin,ref2,pin2,net,mid=(),width=.15):
 path=[point(ref,pin),*mid,point(ref2,pin2)]
 if all(linefree(a,z,net,width,pcbnew.B_Cu) for a,z in zip(path,path[1:])):
  for a,z in zip(path,path[1:]):assert track(a,z,net,width,pcbnew.B_Cu)
 else:failed.append({'kind':'priority-decoupling','a':[ref,pin],'b':[ref2,pin2]})
connectpath('U1',16,'C3',1,'VLED_3V3')
connectpath('C3',1,'C6',1,'VLED_3V3',width=.3)
# VCC and VCAP use local through-via escape before decouplers; no long B-side barriers.
connectpath('C7',1,'C4',1,'VCC_3V3',width=.2)
# VCAP is connected after escape; verify its final loop length.
ic_center=byref['U1'].GetPosition();cx,cy=ic_center.x/1e6,ic_center.y/1e6
connectpath('U1',31,'U1',41,'GND',mid=[(cx+1.8,cy-1.8)],width=.15)
# Compact staggered pin fanout, avoiding all actually placed packages and front LEDs.
u1=byref['U1']
for pd in u1.Pads():
 num=pd.GetNumber();name=pd.GetNetname()
 if not num or int(num)==41 or name.startswith('unconnected') or int(num) in [16,31]:continue
 p=pd.GetPosition();a=(p.x/1e6,p.y/1e6);dx,dy=a[0]-cx,a[1]-cy
 normal=(1 if dx>0 else -1,0) if abs(dx)>abs(dy) else (0,1 if dy>0 else -1)
 esc=(a[0]+normal[0]*.5,a[1]+normal[1]*.5);n=int(num)
 # A jointly ordered fanout avoids endpoint inversions and leaves >=1mm via pitch.
 if D.parent.name=='upper':
  if n<=10:end=(84.5-(n-1),46.5)
  elif n<=20:end=(72,45.4-1.2*(n-11))
  elif n<=30:end=(75.5+(n-21),33.5)
  else:end=(88,34.6+1.2*(n-31))
 else:
  if n<=10:end=(61-(n-1),47)
  elif n<=20:end=(51.6,43-(n-11))
  elif n<=30:end=(53+(n-22),34.3)
  else:end=(64,34.2+(n-32))
 done=viafree(end,name) and linefree(a,esc,name,.15,pcbnew.B_Cu) and linefree(esc,end,name,.15,pcbnew.B_Cu)
 if done:
  assert track(a,esc,name,.15,pcbnew.B_Cu);assert track(esc,end,name,.15,pcbnew.B_Cu);assert via(end,name)
 else:failed.append({'kind':'QFN-fanout','pin':num,'net':name,'planned_endpoint':end})
# Connector pins escape as a complete ordered group before long routes can box them in.
for num in range(3,11):
 pd=next(p for p in byref['J1'].Pads() if p.GetNumber()==str(num));p=pd.GetPosition();a=(p.x/1e6,p.y/1e6);end=(48.2,a[1]);name=pd.GetNetname()
 if viafree(end,name) and linefree(a,end,name,.15,pcbnew.B_Cu):
  assert track(a,end,name,.15,pcbnew.B_Cu);assert via(end,name)
 else:failed.append({'kind':'GH-escape','pin':num,'net':name})
# Local ground returns; every cap gets a short native-shape-checked ground via.
for fp in b.GetFootprints():
 for pd in fp.Pads():
  if pd.GetNetname()!='GND' or (fp.GetReference()=='U1' and pd.GetNumber() in ['31','41']):continue
  p=pd.GetPosition();a=(p.x/1e6,p.y/1e6);done=False
  for radius in [.7,.85,1,1.2,1.5,2]:
   for ang in range(0,360,30):
    z=(round(a[0]+radius*math.cos(math.radians(ang)),4),round(a[1]+radius*math.sin(math.radians(ang)),4))
    if viafree(z,'GND') and linefree(a,z,'GND',.2,pcbnew.B_Cu):
     assert track(a,z,'GND',.2,pcbnew.B_Cu);assert via(z,'GND');done=True;break
   if done:break
  if not done:failed.append({'kind':'GND-via','ref':fp.GetReference(),'pin':pd.GetNumber()})
# A real back GND copper patch under solder mask; keep material/thermal claims separate.
patch=pcbnew.ZONE(b);patch.SetLayer(pcbnew.B_Cu);patch.SetNet(b.FindNet('GND'));patch.SetLocalClearance(u(.15));patch.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
o=patch.Outline();o.NewOutline()
for x,y in [(62,43),(66,43),(66,47),(62,47)]:o.Append(u(x),u(y))
b.Add(patch);patch.thisown=False
assert via((66.6,46),'GND');assert track((66.6,46),(65.5,46),'GND',.4,pcbnew.B_Cu)
leds=sorted((f for f in b.GetFootprints() if f.GetReference().startswith('D')),key=lambda f:int(f.GetReference()[1:]));col=defaultdict(list);csnodes=defaultdict(list)
for fp in leds:
 p=next(p for p in fp.Pads() if p.GetNumber()=='2');a=p.GetPosition();col[(p.GetNetname(),round(a.x/1e6,4))].append((a.x/1e6,a.y/1e6))
for (name,x),pts in col.items():
 pts.sort(key=lambda p:p[1])
 for a,z in zip(pts,pts[1:]):
  if recthit(a,z,[cx-9,cy-9,cx+9,cy+9]):continue # preserve LED escape corridors over the rear QFN
  if not track(a,z,name,.5,pcbnew.F_Cu):failed.append({'kind':'SW-column','net':name,'a':a,'b':z})
for name in sorted({k[0] for k in col}):
 cols=sorted([(x,sorted(pts,key=lambda p:p[1])) for (n,x),pts in col.items() if n==name])
 if len(cols)!=2:continue
 (x1,p1),(x2,p2)=cols;y=max(p1[0][1],p2[0][1])+2
 a,z=(x1,y),(x2,y)
 if recthit(a,z,[cx-9,cy-9,cx+9,cy+9]):continue
 if not track(a,z,name,.5,pcbnew.F_Cu):failed.append({'kind':'SW-bridge','net':name,'a':a,'b':z})
for fp in leds:
 pd=next(p for p in fp.Pads() if p.GetNumber()=='1');p=pd.GetPosition();start=(p.x/1e6,p.y/1e6);name=pd.GetNetname();cs=int(name[2:]);dy=-1 if cs<(7 if D.parent.name=='upper' else 5) else 1;found=None
 for dx in [0,-.6,.6,-1.2,1.2,-2,2]:
  end=(start[0]+dx,start[1]+dy)
  if viafree(end,name) and linefree(start,end,name,.2,pcbnew.F_Cu):found=end;break
 if found is None:failed.append({'kind':'CS-escape','ref':fp.GetReference(),'net':name,'start':start});continue
 assert track(start,found,name,.2,pcbnew.F_Cu);assert via(found,name);csnodes[name].append(found)
for name,pts in sorted(csnodes.items()):
 pts.sort()
 for a,z in zip(pts,pts[1:]):
  if not track(a,z,name,.2,pcbnew.In1_Cu):failed.append({'kind':'CS-bus-gap','net':name,'a':a,'b':z})
b.BuildConnectivity();pcbnew.ZONE_FILLER(b).Fill(b.Zones());pcbnew.SaveBoard(str(D/'petal.kicad_pcb'),b);None
assert pcbnew.ExportSpecctraDSN(b,str(D/'petal-seeded.dsn'))
p=D/'petal-seeded.dsn';p.write_text(re.sub(r'^\(pcb .*?\n','(pcb "petal-seeded.dsn"\n',p.read_text(),count=1))
(D/'physical-buses.json').write_text(json.dumps({'revision':'FPL-01','method':'SW vertical F.Cu spines and pairs; CS horizontal In1.Cu lanes and pin1 escapes; exact native collision test; unresolved left unrouted','clearance_guard_mm':.151,'LED_positions_unchanged':True,'records':records,'unresolved':failed},indent=2)+'\n')
print('Physical buses',len(records),'unresolved',len(failed),'QFN',[f for f in failed if f['kind']=='QFN-fanout'])
