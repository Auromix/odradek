# SPDX-License-Identifier: CC-BY-NC-4.0
"""A11 approved wing-spine design. Pinned A10 mechanics, new removable armour.
Dimensions mm. CAD solids are the manufacturing definition, Blender is rig/render.
"""
from pathlib import Path
import json,hashlib,math,shutil,sys
import numpy as np,cadquery as cq
import interfaces as c
b=c.legacy;OUT=c.OUT;ROOT=c.ROOT;BASE=ROOT/'engineering/arm_a10/build'
b.OUT=OUT;b.L=c.L;b.I=c.I
D=json.loads((BASE/'manifest.json').read_text())
def box(x,y,z,dx,dy,dz):return cq.Solid.makeBox(dx,dy,dz,b.V([x,y,z]))
def src(id):return cq.importers.importStep(str(BASE/'step'/f'{id}.step')).val()
def put(id,s,note):
 old=next(p for p in b.PARTS if p['id']==id)
 if len(s.Solids())!=1:
  print('DISCONNECTED',id,[(q.Volume(),q.Center().toTuple()) for q in s.Solids()],flush=True)
  cq.exporters.export(s,str(OUT/(id+'-diagnostic.step')))

 e=c.part(id,s,old['owner'],old['role'],note,old['frame'],old['material'])
 for key in ['tube_drawing','machining','nut_machining','intentional_thread_motor','thread_engagement_mm']:
  if key in old:e[key]=old[key]

def loft(stations,delta=0,axis='X',cy=0):
 # A twelve-face bevelled shield: central dorsal/ventral ridges, rounded
 # longitudinal waist; section faces remain straight for legible hard edges.
 def profile(y,z):
  y-=delta;z-=delta
  return [(-y,-z+7),(-y+6,-z+1),(0,-z-2),(y-6,-z+1),(y,-z+7),(y,z-7),(y-6,z-1),(0,z+2),(-y+6,z-1),(-y,z-7)]
 pl=cq.Plane(origin=b.V([stations[0][0],cy,0]),normal=b.V([1,0,0]),xDir=b.V([0,1,0])) if axis=='X' else cq.Plane(origin=b.V([0,0,stations[0][0]]),normal=b.V([0,0,1]),xDir=b.V([1,0,0]))
 wp=cq.Workplane(pl)
 for idx,(pos,y,z) in enumerate(stations):
  if idx:wp=wp.workplane(offset=pos-stations[idx-1][0])
  wp=wp.polyline([( (y-delta)*math.cos(2*math.pi*k/16), (z-delta)*math.sin(2*math.pi*k/16)) for k in range(16)] if axis=='Z' else profile(y,z)).close()
 return wp.loft(ruled=False).val()

def links():
 for owner in [3,4]:
  t0,t1,cy=(70,270,0) if owner==3 else (20,115,62)
  stations=[(t0-10,30,34),(t0+25,22,29),((t0+t1)/2,17,25.5),(t1-25,22,29),(t1+10,30,34)] if owner==3 else [(10,22,29),(35,20,27),(67.5,17,25.5),(90,20,27),(125,22,29)]
  exterior=loft(stations,cy=cy)
  for side,sign in [('upper',1),('lower',-1)]:
   # Loft a single closed C-section directly. Cutting a smooth nested
   # hollow loft with a coplanar split box can give OCCT an ambiguous
   # inside classification; this construction has one explicit wire.
   pl=cq.Plane(origin=b.V([stations[0][0],cy,0]),normal=b.V([1,0,0]),xDir=b.V([0,1,0]))
   wp=cq.Workplane(pl)
   for idx,(x,y,z) in enumerate(stations):
    if idx:wp=wp.workplane(offset=x-stations[idx-1][0])
    yi=y-2.4;zi=z-2.4
    outer=[(-y,.2),(-y,z-7),(-y+6,z-1),(0,z+2),(y-6,z-1),(y,z-7),(y,.2)]
    inner=[(yi,.2),(yi,zi-7),(yi-6,zi-1),(0,zi+2),(-yi+6,zi-1),(-yi,zi-7),(-yi,.2)]
    wp=wp.polyline([(yy,sign*zz) for yy,zz in outer+inner]).close()
   skin=wp.loft(ruled=False).val()
   for cx in [t0-5,t1+5]:
    pad=b.cyl([cx,cy,sign*24.7],[0,0,sign],5.5,15).intersect(exterior).fix()
    skin=skin.fuse(pad).fix()
    skin=b.drill(skin,[cx,cy,-42],[0,0,1],3.5,84)
    skin=b.drill(skin,[cx,cy,sign*28.5],[0,0,sign],7.8,20)
   for id in [f'P0{owner}-proximal-socket',f'P0{owner}-distal-socket']:
    for delta in [(0,0,0),(.4,0,0),(-.4,0,0),(0,.4,0),(0,-.4,0),(0,0,.4),(0,0,-.4)]:skin=skin.cut(b.SHAPES[id].translate(delta),tol=1e-5).fix()
   # Constant straight bore positively clears the stock tube corners.
   skin=skin.cut(box(t0-.4,cy-10.4,-20.4,t1-t0+.8,20.8,40.8),tol=1e-5).fix()
   put(f'S0{owner}-armour-{side}',skin,'A11 single-wire wing-spine C-section,2.4mm nominal wall,0.4mm mid-plane seam. Existing twoM3x12 datums; recessed access wells. Stock tube corner clearance explicitly cut. Physical fit pending.')

def root():
 # D140 preserves the eight M6 PCD120 holes and their complete D13 tool wells.
 s=b.SHAPES['P00-root-open']
 limit=b.cyl([0,0,0],[0,0,1],70,32).fuse(box(-200,-200,32,400,400,200))
 put('P00-root-open',s.intersect(limit).fix(),'A11 D140 root mounting land, eight M6/PCD120 datums retained. Four posts/top ring unchanged. Must mate to a separately validated load chassis, not the cosmetic collar.')
 stations=[(43,78,74),(72,69,69),(108,66,66),(137.4,68,68)]
 shell=loft(stations,axis='Z').cut(loft(stations,2.4,axis='Z'),tol=1e-5).fix()
 for z,r in [(45,72),(120,69)]:
  for sign in [-1,1]:
   shell=shell.fuse(b.cyl([-6,sign*r,z],[1,0,0],4.5,12)).fix()
   shell=b.drill(shell,[-7,sign*r,z],[1,0,0],3.5,14)
 # Explicit0.4mm root/top-ring keepout protects post corners and seating ring.
 for id in ['P00-root-open','P00-J1-top-ring']:
  for delta in [(0,0,0),(.4,0,0),(-.4,0,0),(0,.4,0),(0,-.4,0),(0,0,.4),(0,0,-.4)]:shell=shell.cut(b.SHAPES[id].translate(delta),tol=1e-5).fix()
 # Clip any flange screw approach before splitting. Source geometry is not moved.
 for name,x0,width in [('A',.2,150),('B',-150,149.8)]:
  s=shell.intersect(box(x0,-160,40,width,320,110)).fix()
  put('S00-waist-'+name,s,'A11 tapered root shield. Start Z43mm arm frame; 3.6mm vertical clearance above shared base Z74 at mount Z34.6. Existing four M3x20 seams. Not load-bearing.')

def cuffs():
 for idx,j in enumerate(c.L['joints']):
  if idx==0:continue
  inf=c.I[idx];rad=j['diameter_mm']/2;org=inf['out']-inf['n']*(inf['depth']-5)
  depth=inf['depth']-inf['m']['interface_frame']['output_to_housing_front_mm']-13
  pl=b.plane(org,inf['n']);wp=cq.Workplane(pl)
  # Shallow axial bevels and ten broad faces instead of a cylindrical cap.
  for k,(a,rr) in enumerate([(0,rad+2.6),(2.2,rad+3.5),(depth-2.2,rad+3.5),(depth,rad+2.6)]):
   if k:wp=wp.workplane(offset=a-last)
   wp=wp.polygon(10,2*rr/math.cos(math.pi/10));last=a
  band=wp.loft(ruled=True).val().cut(b.cyl(org-inf['n'],inf['n'],rad+.6,depth+2),tol=1e-5).fix()
  station=19 if idx==6 else 8
  for sign in [-1,1]:
   band=band.fuse(b.cyl(org+inf['v']*sign*(rad+5)+inf['n']*station-inf['u']*6,inf['u'],4.5,12)).fix()
   band=b.drill(band,org+inf['v']*sign*(rad+5)+inf['n']*station-inf['u']*7,inf['u'],3.5,14)
  for angle in [30,90,150,210,270,330]:
   t=math.radians(angle);u=inf['u']*math.cos(t)+inf['v']*math.sin(t)
   cutter=cq.Workplane(cq.Plane(origin=b.V(org+u*(rad-1)+inf['n']*13),normal=b.V(inf['n']),xDir=b.V(u))).rect(12,8).extrude(max(1,depth-18)).val()
   band=band.cut(cutter,tol=1e-5).fix()
  for e in b.PARTS:
   if e['role']=='printed_structure' and e['owner']==idx:
    s=b.SHAPES[e['id']]
    if e['frame']==c.frame(idx):s=s.translate(b.V(-np.array(j['offset'])))
    elif e['frame']!=j['id']+'.fixed':continue
    band=band.cut(s,tol=1e-5).fix()
  for name,x0,width in [('A',.2,200),('B',-200,199.8)]:
   cut=cq.Workplane(pl).center(x0+width/2,0).rect(width,400).extrude(depth+1).val()
   put(j['id']+'-armour-'+name,band.intersect(cut).fix(),'A11 ten-face cuff with 2.2mm axial bevels; supplier housing unchanged. Existing M3x20 clamps; open vent sectors. Connector, liner and thermal validation pending.')

def main():
 OUT.mkdir(parents=True,exist_ok=True);b.PARTS[:]=json.loads(json.dumps(D['parts']));b.SHAPES.clear()
 incremental='--root-only' in sys.argv or '--covers-only' in sys.argv
 if incremental:
  current=json.loads((OUT/'manifest.json').read_text());b.PARTS[:]=current['parts']
 for folder in ([] if incremental else ['step','stl']):
  (OUT/folder).mkdir(exist_ok=True)
  for p in (BASE/folder).glob('*'):shutil.copy2(p,OUT/folder/p.name)
 for p in b.PARTS:
  if not incremental or p['role']=='printed_structure' or p['id'].startswith(('P00-','S00-','ROOT-')):b.SHAPES[p['id']]=cq.importers.importStep(str((OUT if incremental else BASE)/'step'/f"{p['id']}.step")).val()
 if not incremental or '--covers-only' in sys.argv:links()
 root()
 if not incremental:cuffs()
 for p in b.PARTS:
  if p['role']=='hardware' and p['id'] not in b.SHAPES:b.SHAPES[p['id']]=cq.importers.importStep(str(OUT/'step'/f"{p['id']}.step")).val()
 import refine
 changed=([p['id'] for p in b.PARTS if p['role']=='printed_cover']+['P00-root-open']) if not incremental else ['S00-waist-A','S00-waist-B','P00-root-open']+(['S03-armour-upper','S03-armour-lower','S04-armour-upper','S04-armour-lower'] if '--covers-only' in sys.argv else [])
 refine.refine(changed)
 data=json.loads(json.dumps(current if incremental else D));data['parts']=b.PARTS;data['layout']=c.L;data['revision']='A11-long-wing-spine';data['status']='approved_style_digital_fit_prototype_not_load_rating'
 data['root_placement_mm']=[0,75,34.6];data['root_yaw_deg']=90
 data['baseline_manifest_sha256']=hashlib.sha256((BASE/'manifest.json').read_bytes()).hexdigest()
 data['base_interface']['root_land_diameter_mm']=140
 data['base_interface']['source_note']='PCD120 retained; SHAPE08 cosmetic collar is not the threaded load chassis. New chassis and hidden desk-clamp integration remain pending.'
 data['changed_parts']=sorted(set((current.get('changed_parts',[]) if incremental else [])+[p['id'] for p in b.PARTS if p['role']=='printed_cover']+['P00-root-open']));data['physical_gates']+=['Shared B05 cosmetic collar is not a completed load chassis.','A11 armour requires slicer review and unpowered supported fit.']
 (OUT/'manifest.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
 compact={k:v for k,v in data.items() if k!='parts'};compact['parts']=[{k:v for k,v in p.items() if k not in ['vertices_mm','triangles']} for p in b.PARTS]
 (OUT/'parts.json').write_text(json.dumps(compact,ensure_ascii=False,indent=2)+'\n')
 print('A11_BUILD',len(b.PARTS),len(changed),flush=True)
if __name__=='__main__':
 main()
 if '--root-only' not in sys.argv and '--covers-only' not in sys.argv:
  import shoulder
  shoulder.main()
