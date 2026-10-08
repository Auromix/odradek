# SPDX-License-Identifier: CC-BY-NC-4.0
"""Pinned supplier interfaces and A10 local frame helpers. Dimensions mm."""
from pathlib import Path
import sys,json,numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'engineering/arm_a08'))
import build as legacy
SOURCE=json.loads((ROOT/'docs/engineering/sources/arm-a05-mechanical-sources.json').read_text())
BASE=json.loads((ROOT/'engineering/arm_a09/build/long/manifest.json').read_text())
L=json.loads(json.dumps(BASE['layout']))
L['id']='arm-a11-long-wing-spine';L['status']='printable_geometry_validation_not_load_rating'
L['joints'][0]['offset'][2]=130
L['pedestal']['motor_lower_cable_cavity_height_mm']=41.8
L['joints'][1]['limits_deg']=[-60,110];L['joints'][3]['limits_deg']=[-145,135]
L['joints'][1]['limit_status']='Reduced for shoulder bridge. Discrete samples and named paths only.'
L['poses']['idle']=[0,110,0,-145,125,0,0]
I=[legacy.info(j) for j in L['joints']];I[5]['outer']=32
OUT=ROOT/'engineering/arm_a11/build'
HARDWARE=[];JOINTS=[]
def a(v):return np.array(v,float)
def frame(owner):return 'world' if owner==0 else f'J{owner}.rotor'
def part(id,s,owner,role='printed_structure',note='',frame_name=None,material=None,mass=None):
 e=legacy.add(id,s,owner,role,material or ('PA12 solid-mass estimate; FDM fit material needs coupons' if role in ['printed_structure','fit_coupon'] else 'PETG removable armour'),note,frame_name,mass)
 if e['solid_count']!=1:raise ValueError(f'{id} disconnected: {e["solid_count"]}')
 return e

def std_bolt(id,p,n,d,length,grip,owner,fr=None,motor=None,washer=None,button=False):
 washer=(.8 if d==4 else 1 if d in [5,8] else .5) if washer is None else washer
 if d==6:
  axis=np.array(n,float);origin=np.array(p,float)
  sh=legacy.cyl(origin+axis*(grip+washer-length),axis,3,length).fuse(legacy.cyl(origin+axis*(grip+washer),axis,5,6)).clean()
  e=legacy.add(id,sh,owner,'hardware','steel ISO4762 M6x20 class8.8','SourceB04 M6 through-thread matched; nominal engagement10.4mm',fr,sh.Volume()*7.85e-6)
  e['intentional_thread_motor']=motor;e['machining']=dict(p=list(map(float,p)),n=list(map(float,n)),d=6,length=length,plate=grip,washer=washer,head=[10,6]);e['thread_engagement_mm']=length-grip-washer
  w=legacy.ring(origin+axis*grip,axis,6,3.2,washer);legacy.add(id+'-washer',w,owner,'hardware','steel M6 washer12x6.4x1.6','',fr,w.Volume()*7.85e-6)
 else:legacy.screw(id,p,n,d,length,grip,washer,owner,fr,motor,button)
 e=next(e for e in legacy.PARTS if e['id']==id)
 HARDWARE.append(dict(id=id,type='screw',nominal=e['material'],d=d,length=length,grip_mm=grip,washer_mm=washer,engagement_mm=length-grip-washer,motor=motor,frame=e['frame'],p_mm=list(map(float,p)),n=list(map(float,n))))
 return e

def std_nut(id,p,n,d,owner,fr=None):
 e=legacy.nut(id,p,n,d,owner,fr,back_washer=False)
 HARDWARE.append(dict(id=id,type='nut',nominal=e['material'],frame=e['frame'],p_mm=list(map(float,p)),n=list(map(float,n))))
 return e

def tool_holes(s,inf,kind,th,offset=(0,0,0),recess=None):
 """Bores recut after unions; a 25mm straight hex-key approach is machined away."""
 p0=inf['out' if kind=='output_fasteners' else 'fixed']+a(offset);n=inf['n'];model=inf['j']['model']
 d=5 if model=='RS04' and kind=='output_fasteners' else 3 if model=='RS00' or model=='RS06' and kind=='fixed_front_fasteners' else 4
 hd={3:5.5,4:7,5:8.5}[d];access=max(hd+1.2,{3:7.6,4:9.6,5:10}[d])
 for v in legacy.xy_holes(inf,kind):
  s=legacy.drill(s,p0+v-n,n,d+.6,th+2)
  s=legacy.drill(s,p0+v+n*th,n,access,25)
 if kind=='output_fasteners' and model=='RS04':
  for px,py in [(-12.67842,12.67842),(17.31905,4.64063),(-4.64063,-17.31905)]:s=legacy.drill(s,p0+inf['u']*px+inf['v']*py-n*.1,n,6.5,3.6)
 return s.fix()

def mounting_bolts(index,output_th,fixed_th):
 inf=I[index];j=inf['j'];m=j['model'];fr=j['id']+'.fixed';owner=index;off=a(j['offset']) if index>0 else a([0,0,j['offset'][2]])
 fd=4 if m in ['RS03','RS04'] else 3;fl=16 if m=='RS04' else 14 if m=='RS03' else 12
 # Front fixed rings: M4x14/8mm=>5.2mm; M4x16/11mm=>4.2; M3x12/8mm=>3.5.
 for k,v in enumerate(legacy.xy_holes(inf,'fixed_front_fasteners'),1):std_bolt(j['id']+f'-fixed-{k}',inf['fixed']+v,inf['n'],fd,fl,fixed_th,owner,fr,j['id'],button=j['id']=='J7')
 od=5 if m=='RS04' else 3 if m=='RS00' else 4
 ol=40 if index==6 else 14 if m=='RS00' else 16 if output_th==10 else 25
 for k,v in enumerate(legacy.xy_holes(inf,'output_fasteners'),1):std_bolt(j['id']+f'-output-{k}',inf['out']+v,inf['n'],od,ol,output_th,index+1,j['id']+'.rotor',j['id'],washer=.5 if od==3 else 1 if od==5 else .8)
 JOINTS.append(dict(joint=j['id'],model=m,fixed_holes=inf['m']['fixed_front_fasteners'],output_holes=inf['m']['output_fasteners'],output_thickness_mm=output_th,fixed_thickness_mm=fixed_th,assembly='Fasten upstream output before installing downstream motor; covers installed last.'))
