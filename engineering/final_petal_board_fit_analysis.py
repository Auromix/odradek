# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
# Independent fit study, not released ECAD. Does not alter pocket or ULP-02.
import json,csv,math,hashlib
from pathlib import Path
import cadquery as cq
import numpy as np
from scipy.spatial import ConvexHull
ROOT=Path(__file__).resolve().parents[1]; P=ROOT/'engineering/generated/led-petal-pocket'; U=ROOT/'engineering/electronics/upper-petal-prototype/ulp02'
def loadshape(name):return cq.importers.importStep(str(P/name)).val()
def hashfile(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def poly(shape):
 f=max(shape.Faces(),key=lambda f:f.Center().z)
 v=list({(round(v.X,8),round(v.Y,8)) for v in f.outerWire().Vertices()});h=ConvexHull(v)
 # Both supplied outlines must be convex; vertex rounding is 1e-8 mm.
 assert abs(h.volume - cq.Face.makeFromWires(f.outerWire()).Area()) < 1e-5
 return np.array([v[i] for i in h.vertices])
def boxcorners(x,y,w,h):return np.array([(x-w/2,y-h/2),(x+w/2,y-h/2),(x+w/2,y+h/2),(x-w/2,y+h/2)])
def edge_clear(p,rect):
 ans=[]
 for a,b in zip(p,np.roll(p,-1,axis=0)):
  e=b-a;d=rect-a
  ans.extend((e[0]*d[:,1]-e[1]*d[:,0])/np.linalg.norm(e))
 return min(ans)
def circle_clear(rect,m):
 x0,y0=rect.min(axis=0);x1,y1=rect.max(axis=0)
 return min(math.hypot(max(x0-x,0,x-x1),max(y0-y,0,y-y1))-3.25 for x,y in m)
def overlaps(a,b,margin=0):
 a0=a.min(axis=0);a1=a.max(axis=0);b0=b.min(axis=0);b1=b.max(axis=0)
 return all(a1+margin>b0+1e-9) and all(b1+margin>a0+1e-9)
f=json.load(open(U/'footprint-constraints.json'))
# Envelope includes max(package, land) and extra 0.25 mm rectangle margin each side.
# NTC public a,b,c interpretation remains candidate, envelope >= max body and selected lands.
sizes={'TI_RKP0040B':(5.4,5.4),'C0805':(2.9,1.45),'C0603':(2.2,.95),'R0603':(2.5,.95),'NTC0603':(2.1,.95)}
parts=[r for r in csv.DictReader(open(U/'bom.csv')) if not r['ref'].startswith('D') and r['ref']!='J1']
results={}
for typ,L,dy in [('UPPER',150,8),('LOWER',100,6)]:
 p=poly(loadshape(f'{typ}-PCB_outline.step')); mount=[(33,dy),(33,-dy),(L-28,0)]
 old=[];grid=[]
 for row in csv.DictReader(open(U/'led-placement-reference.csv')):
  x,y=float(row['x_mm']),float(row['y_mm']);r=boxcorners(x,y,2.4,.9)
  e=edge_clear(p,r);c=circle_clear(r,mount)
  old.append(dict(ref=row['ref'],x=x,y=y,edge_clearance_mm=e,mount_keepout_clearance_mm=c,passes=e>=.25-1e-8 and c>=.25-1e-8))
 for x in range(30,L-22,4):
  for y in range(-16,17,4):
   r=boxcorners(x,y,2.4,.9);e=edge_clear(p,r);c=circle_clear(r,mount)
   if e>=.25-1e-8 and c>=.25-1e-8:grid.append(dict(x=x,y=y,edge_clearance_mm=e,mount_keepout_clearance_mm=c))
 # Greedy preserves consecutive physical columns. Multiple columns use disjoint CS per scan row.
 columns={x:[r for r in grid if r['x']==x] for x in sorted({r['x'] for r in grid})}
 groups=[];cur=[]
 for x,col in columns.items():
  if len(cur)+len(col)>14:groups.append(cur);cur=[]
  cur+=col
 if cur:groups.append(cur)
 assert len(groups)<=11 and all(len(g)<=14 for g in groups)
 # Keep 11 scan rows for equal brightness across both petal types; unpopulated rows off.
 for sw,g in enumerate(groups):
  for cs,led in enumerate(g):led.update(sw_provisional=sw,cs_provisional=cs)
 oldpass=[i for i in old if i['passes']];oldfails=[i for i in old if not i['passes']]
 # Placement is 2D fitting envelope only, not routed/decoupling-valid. Reserve root aperture+0.5/side.
 aperture=boxcorners(43,0,10,18.5); placed=[]; allowed_cache={}
 for row in parts:
  ref=row['ref'];base=sizes[row['footprint']]; dims=[(base[0]+.5,base[1]+.5,0),(base[1]+.5,base[0]+.5,90)]
  candidates=[]
  target=(55,0) if ref=='U1' else ((52,0) if ref.startswith('C') else (62,0))
  if ref=='TH1':target=(62,5)
  if row['footprint'] not in allowed_cache:
   allowed=[]
   for w,h,rot in dims:
    for x in np.arange(49,69.01,.5):
     for y in np.arange(-12,12.01,.5):
      r=boxcorners(x,y,w,h)
      if edge_clear(p,r)<.25 or circle_clear(r,mount)<0 or overlaps(r,aperture):continue
      allowed.append((x,y,w,h,rot,r))
   allowed_cache[row['footprint']]=allowed
  for x,y,w,h,rot,r in allowed_cache[row['footprint']]:
   if any(overlaps(r,np.array(other['envelope_xy_mm'])) for other in placed):continue
   candidates.append((math.hypot(x-target[0],y-target[1]),x,y,w,h,rot,r))
  if not candidates:raise Exception((typ,ref,'no placement'))
  _,x,y,w,h,rot,r=min(candidates,key=lambda a:a[0])
  placed.append(dict(ref=ref,mpn=row['manufacturer_part_number'],footprint=row['footprint'],center_xy_mm=[x,y],rotation_deg=rot,envelope_size_mm=[w,h],envelope_xy_mm=r.tolist(),edge_clearance_mm=edge_clear(p,r),mount_keepout_clearance_mm=circle_clear(r,mount)))
 N=len(grid);Iavg=N*.02/11;Ipeak=max(map(len,groups))*.02;Pled=3.3*Iavg;plan=Pled+.05
 results[typ]={
  'length_mm':L,'polygon_xy_mm':p.tolist(),'mounts_xy_mm':mount,'pcb_area_excluding_holes_mm2':loadshape(f'{typ}-PCB_outline.step').Volume()/.8,
  'backreserve_area_mm2':loadshape(f'{typ}-back_component_volume_reserve.step').Volume()/1.45,
  'ULP02_unmodified_dot_overlap':{'passing_count':len(oldpass),'failing_count':len(oldfails),'failures':oldfails},
  'candidate_grid':{'pitch_xy_mm':[4,4],'start_x_mm':30,'emitter_body_max_xy_mm':[1.7,.9],'combined_body_land_envelope_xy_mm':[2.4,.9],'edge_clearance_requirement_mm':.25,'mount_keepout_diameter_mm':6.5,'extra_clearance_from_mount_keepout_mm':.25,'dots':grid,'count':N,'min_edge_clearance_mm':min(r['edge_clearance_mm'] for r in grid),'min_mount_keepout_clearance_mm':min(r['mount_keepout_clearance_mm'] for r in grid),'scan_row_counts':list(map(len,groups)),'scan_rows_programmed':11,'max_CS_count':max(map(len,groups)),'mapping_status':'provisional adjacency partition for power feasibility only; no released netlist, register file, or ECAD'},
  'back_components_fit_only':{'envelope_method':'max body/land bbox plus 0.25 per side; 2D only; component height+solder not certified; packing does not validate electrical placement or routing','aperture_exclusion_xy_mm':aperture.tolist(),'parts':placed,'count':len(placed),'min_edge_clearance_mm':min(v['edge_clearance_mm'] for v in placed),'min_mount_keepout_clearance_mm':min(v['mount_keepout_clearance_mm'] for v in placed)},
  'power':{'I_LED_peak_A_at20mA':Ipeak,'I_LED_average_A_before_blanking':Iavg,'P_VLED_W_before_blanking':Pled,'logic_planning_W_not_datasheet_max':.05,'total_planning_W':plan,'area_average_W_cm2':plan/(loadshape(f'{typ}-PCB_outline.step').Volume()/.8/100),'dV_at8us_44uF_V':Ipeak*8/44,'dV_at8us_assumed20uF_V':Ipeak*8/20,'P_LED_typ_VF2V_W':Iavg*2,'P_driver_switch_CS_typ_W':Iavg*1.3},
 }

 # Check analytical planar tests independently against the unmodified exact CAD reserves.
 front=loadshape(f'{typ}-front_LED_volume_reserve.step')
 back=loadshape(f'{typ}-back_component_volume_reserve.step')
 residuals=[]
 for dot in grid:
  q=cq.Workplane('XY').box(2.4,.9,.8).translate((dot['x'],dot['y'],4.8)).val()
  residuals.append(q.cut(front).Volume())
 for item in placed:
  x,y=item['center_xy_mm'];w,h=item['envelope_size_mm']
  q=cq.Workplane('XY').box(w,h,1.45).translate((x,y,2.875)).val()
  residuals.append(q.cut(back).Volume())
 assert max(residuals)<1e-6
 results[typ]['CAD_check']={'test':'rectangular LED body/land envelopes and backside keepout envelopes minus existing exact STEP reserves','tested_envelopes':len(residuals),'maximum_outside_volume_mm3':max(residuals),'limitation':'No solder, tolerances, copper, vias, routing, true component geometry, connector latch, wire, or deformation included'}

sources=[
 {'id':'JST-GH','url':'https://www.jst-mfg.com/product/pdf/eng/eGH.pdf','pages_1based':[2,3],'sha256':'b1dcb317b6b9a4fbbedd2dbf42c64c95306a252d23de8933b85fcf161240b722','bytes':146619,'observations':'Mated top height7.3 depth4.25; side height4.35 axialdepth7.15. Ten-way header width15.75. Assembly dimensions reference only. Pages visually checked.'},
 {'id':'JST-SH','url':'https://www.jst-mfg.com/product/pdf/eng/eSH.pdf','pages_1based':[1,2,3],'sha256':'ea3071ca5ee5a6069eba534fa39a10f34c9fb742ee42135a69ab4156bfa0f5de','bytes':84427,'observations':'Side mating height2.95 axialdepth6.25; SM10B-SRSS-TB width12; SHR-10V-S without protrusions width11; SSH-003T-P0.2-H contacts. Assembly reference values. Pages visually checked.'},
 {'id':'JST-controlled-model-access','url':'https://www.jst-mfg.com/product/index.php?doc=4&filename=BM10B-GHS-TBT.pdf&series=105&type=10','observations':'Official page offers email delivery after company/contact form; no form submitted, no controlled drawing or pair STEP obtained.'},
 {'id':'WE-LED','url':'https://www.we-online.com/components/products/datasheet/150060YS75000.pdf','pages_1based':[1,2],'sha256':'146c8bedf22adb44575b9391a34ca902d873ae9d4f9be55f3f88dc288088a9f4','bytes':900146,'observations':'Package1.6+/-0.1 by0.8+/-0.1 by0.7+/-0.1; land2.4 by0.8; pin1K pin2A. Typical Vf2V used for distribution estimate only, not worst-case.'},
 {'id':'TI-LP5860','url':'https://www.ti.com/lit/ds/symlink/lp5860.pdf','pages_1based':[1,4,6,46,50,51,58,59],'sha256':'2d0234bb32de821d8c3ba9208bf5e1fae3f43d4570b1e42697d0ef791f70e771','bytes':4052513,'observations':'Rev A; 11 scans/18 sinks; 5x5mm QFN,1mm maximum height; local decoupling/ground thermal pad. Datasheet thermal environment is not this metal-backed petal.'}
]
inputs={str(p.relative_to(ROOT)):hashfile(p) for p in [
 ROOT/'engineering/led_petal_pocket_study.py',P/'study.json',
 *[P/f'{typ}-{part}.step' for typ in ['UPPER','LOWER'] for part in ['PCB_outline','front_LED_volume_reserve','back_component_volume_reserve','metal']],
 U/'bom.csv',U/'footprint-constraints.json',U/'led-placement-reference.csv',U/'mechanical-power-budget.json',U/'sources.json']}
connectors=[
 {'id':'GH-top','header':'BM10B-GHS-TBT(LF)(SN)','housing':'GHR-10V-S','contact':'SSHL-002T-P0.2','source':'JST-GH','mated_bbox_xyz_reference_mm':[4.25,15.75,7.3]},
 {'id':'GH-side','header':'SM10B-GHS-TB(LF)(SN)','housing':'GHR-10V-S','contact':'SSHL-002T-P0.2','source':'JST-GH','mated_bbox_xyz_reference_mm':[7.15,15.75,4.35]},
 {'id':'SH-side','header':'SM10B-SRSS-TB(LF)(SN)','housing':'SHR-10V-S','contact':'SSH-003T-P0.2-H','source':'JST-SH','mated_bbox_xyz_reference_mm':[6.25,12.0,2.95]}
]
for c in connectors:
 if c['id'].startswith('GH'):
  c['catalogue_land_total_width_mm']=15.95
  c['land_width_plus_025_each_side_mm']=16.45
  c['land_note']='Reference pad span from mounting-side diagram; actual mounting datum/rotation/mirroring must be established, not assumed concentric with mated body box.'
 dx,dy,h=c['mated_bbox_xyz_reference_mm']
 c.update({'bottom_z_mm':3.6-h,'rear_protrusion_beyond_metal_z0_mm':max(h-3.6,0),'excess_over_regular_back_height_mm':h-1.45,'floor_interference_zdepth_mm':max(1.9-(3.6-h),0),'nominal_centered_opening_leftover_xy_mm':[9-dx,17.5-dy],'reference_bbox_center_xy_mm':[43,0], 'status':'catalogue reference envelope only; not manufacturer 3D model or insertion sweep'})
 static=cq.Workplane('XY').box(dx,dy,h).translate((43,0,3.6-h/2)).val()
 c['static_reference_box_metal_intersection_mm3']={typ:static.intersect(loadshape(f'{typ}-metal.step')).Volume() for typ in ['UPPER','LOWER']}
 assert max(c['static_reference_box_metal_intersection_mm3'].values()) < 1e-6

payload={'revision':'FINAL-PETAL-FIT-01','status':'independent feasibility; not final board, fabrication release, or full assembly validation','license':'CC-BY-NC-4.0','accessed':'2026-09-27','units':'mm unless stated','generator_sha256':hashfile(Path(__file__)), 'inputs_sha256':inputs,'manufacturer_sources':sources,'third_party_documents':'Downloaded/visually read outside repository; not redistributed. Source identifiers are not an endorsement or purchasing status.','coordinate_frame':'root toward tip +X; metal rear face Z0; component XY shown in mechanical frame, not manufacturing-side pin numbering','component_envelope_method':'max physical XY/selected land XY plus0.25mm each side for backside packages; LEDs use2.4x0.9 body/land union bbox then0.25mm edge and mount clearance; no solder/tolerance','boards':results,'connectors':connectors,'thermal_gaps_nominal_mm':{'bare_PCB_bottom_to_metal_floor':1.7,'IC_top_to_metal_floor_for1mm_package':.7,'highest_C_top_to_metal_floor_for1_45mm_package':.25},'four_petals_planning':{'peak_synchronous_VLED_A':2*sum(x['power']['I_LED_peak_A_at20mA'] for x in results.values()),'VLED_average_A':2*sum(x['power']['I_LED_average_A_before_blanking'] for x in results.values()),'board_power_W':2*sum(x['power']['total_planning_W'] for x in results.values()),'excludes':'central round display, cameras, conversion losses and other head electronics'}}
out=ROOT/'docs/engineering/sources/final-petal-board-fit-analysis.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(payload,indent=2,default=lambda x:x.item() if isinstance(x,np.generic) else x)+'\n')
print(json.dumps({'output':str(out.relative_to(ROOT)),'counts':{t:r['candidate_grid']['count'] for t,r in results.items()},'CAD_reserve_outside_mm3':{t:r['CAD_check']['maximum_outside_volume_mm3'] for t,r in results.items()}},indent=2))

# Original vector illustration from calculations; contains no reproduced vendor artwork.
import html
svg=[]
def put(s):svg.append(s)
def txt(x,y,s,size=18,color='#182a38',weight='normal'):
 put(f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}">{html.escape(s)}</text>')
def rect(x,y,w,h,fill,stroke='none',sw=1,extra=''):
 put(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>')
def line(x1,y1,x2,y2,stroke='#6b7c87',sw=1,extra=''):
 put(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}" {extra}/>')
put('<svg xmlns="http://www.w3.org/2000/svg" width="1520" height="1180" viewBox="0 0 1520 1180">')
put('<style>text{font-family:Arial,sans-serif}</style>');rect(0,0,1520,1180,'#f7f9f9')
txt(40,44,'FINAL-PETAL-FIT-01  |  Mechanical / LED board feasibility',28,weight='bold')
txt(40,73,'Candidate coordinates only. Existing pocket and ULP-02 are unchanged. No routed final PCB or production release.',17)
for typ,ox in [('UPPER',50),('LOWER',900)]:
 r=results[typ];p=r['polygon_xy_mm'];sc=6
 def xy(x,y,cy):return ox+(x-27)*sc,cy-y*sc
 txt(ox,119,f'{typ}  L{r["length_mm"]}  |  {r["candidate_grid"]["count"]} LED candidate',23,weight='bold')
 for side,cy in [('FRONT',245),('BACK',555)]:
  pts=' '.join(f'{a},{b}' for a,b in (xy(x,y,cy) for x,y in p))
  put(f'<polygon points="{pts}" fill="#e2edeb" stroke="#306762" stroke-width="2"/>')
  for x,y in r['mounts_xy_mm']:
   a,b=xy(x,y,cy)
   put(f'<circle cx="{a}" cy="{b}" r="{3.25*sc}" fill="#ffe2bf" stroke="#af6500"/>')
   put(f'<circle cx="{a}" cy="{b}" r="{1.2*sc}" fill="#fff" stroke="#718088"/>')
  if side=='FRONT':
   for d in r['candidate_grid']['dots']:
    a,b=xy(d['x']-1.2,d['y']+.45,cy);rect(a,b,2.4*sc,.9*sc,'#d79212')
   txt(ox,371,'Front: body + land envelopes; 4 mm grid; 0.25 mm extra clearance',16)
   txt(ox,395,f'PCB x27...{r["length_mm"]-22}; area {r["pcb_area_excluding_holes_mm2"]/100:.2f} cm2',16)
  else:
   a,b=xy(38,9.25,cy);rect(a,b,10*sc,18.5*sc,'#f6d7d7','#a74747',1,extra='stroke-dasharray="5 4"')
   a,b=xy(43-7.15/2,15.75/2,cy);rect(a,b,7.15*sc,15.75*sc,'#ddaaa9','#a44747',1)
   for d in r['back_components_fit_only']['parts']:
    x,y=d['center_xy_mm'];w,h=d['envelope_size_mm'];a,b=xy(x-w/2,y+h/2,cy)
    color='#2c668d' if d['ref']=='U1' else ('#bc774b' if d['ref']=='TH1' else '#80a6b0')
    rect(a,b,w*sc,h*sc,color,'#375a68',.5)
    if d['ref']=='U1':txt(a+8,b+23,'U1',14,'#fff')
   txt(ox,685,'Back: 20 package/land envelopes + side-GH reference box',16)
   txt(ox,709,'Packing only: decoupling loops, fanout and routing are not proven.',16)
   txt(ox,733,f'20 mA / 11 scans: {r["power"]["I_LED_peak_A_at20mA"]*1000:.0f} mA peak, {r["power"]["total_planning_W"]:.3f} W planning',16)
line(40,762,1480,762,'#b8c6ca')
txt(40,796,'Full mating reference envelopes  |  Side section, unchanged PCB underside z3.6',23,weight='bold')
for c,ox in zip(connectors,[70,570,1070]):
 dx,dy,h=c['mated_bbox_xyz_reference_mm'];sc=15;cy=1000;cx=ox+165
 txt(ox,833,c['id'],21,weight='bold')
 txt(ox,858,f'Depth {dx:g} x width {dy:g} x height {h:g} mm',16)
 # Metal floor reference, kept out within existing 9 mm aperture.
 rect(cx-125,cy-1.9*sc,125-4.5*sc,1.9*sc,'#a8b1b8')
 rect(cx+4.5*sc,cy-1.9*sc,125-4.5*sc,1.9*sc,'#a8b1b8')
 line(cx-140,cy,cx+140,cy,'#394d58',1,extra='stroke-dasharray="4 4"')
 rect(cx-125,cy-4.4*sc,250,.8*sc,'#2e776c')
 rect(cx-dx/2*sc,cy-3.6*sc,dx*sc,h*sc,'#d39f98','#a74747',1)
 txt(ox,1082,f'Bottom z{c["bottom_z_mm"]:.2f}; rear protrusion {c["rear_protrusion_beyond_metal_z0_mm"]:.2f}',16)
 txt(ox,1105,'No wire bend, lock access or mating stroke included.',15)
txt(40,1148,'Orange circles: mounting keepouts. Red: connector reserve. Blue: package fit only. Sizes in mm; front/back drawings share mechanical XY.',16)
txt(40,1172,'Original analysis · CC-BY-NC-4.0 · Auromix contributors · Vendor reference: JST eGH.pdf pp2–3; eSH.pdf pp1–3. Not frozen.',14)
put('</svg>')
d=ROOT/'engineering/generated/final-petal-board-fit';d.mkdir(parents=True,exist_ok=True);(d/'fit-overview.svg').write_text('\n'.join(svg)+'\n')
