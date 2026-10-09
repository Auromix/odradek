# SPDX-License-Identifier: CC-BY-NC-4.0
"""Review drawings from current exact BREP; never projections of cosmetic mesh.
Dimensions and feature table share the original CAD source. Candidate status is
intentional until assembly, fastener and powered-load release are complete.
"""
from pathlib import Path
import json,hashlib,textwrap,io
import cadquery as cq
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.lib.units import mm
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
import load_frame as cad
OUT=cad.OUT/'drawings';OUT.mkdir(parents=True,exist_ok=True)
parts=cad.make(30)
# Symmetric mirrored hangers both shown; purchased hardware listed, not machined.
selected=[]
for p in parts:
 if p['category'] in ('environment','hardware','printed'):continue
 if p['id'].startswith('B06-105-POST-') and not p['id'].endswith('-1'):continue
 if p['id'].endswith('--1') and ('SPREADER' in p['id'] or 'PRESS-PAD' in p['id']):continue
 selected.append(p)
REV='B06-LOAD-02-STANDALONE'
W,H=landscape(A3);c=canvas.Canvas(str(OUT/'B06-load-frame-review.pdf'),pagesize=(W,H))
c.setTitle('B06 load frame - coordinated engineering review')
def text(x,y,s,size=9):c.setFont('Helvetica',size);c.drawString(x*mm,y*mm,s)
def border(title,page):
 c.setStrokeColorRGB(.2,.25,.3);c.setLineWidth(.5);c.rect(10*mm,10*mm,W-20*mm,H-20*mm)
 text(16,280,'AUROMIX / ODRADEK  |  '+REV,13);text(16,270,title,12)
 text(16,16,'REVIEW CANDIDATE - NOT COMPLETE BASE MANUFACTURING RELEASE',10)
 text(16,11,'Units mm. Do not scale drawing. Exact STEP profile governs. '+f'Sheet {page}/{len(selected)+1}',8)
def view(p,xyz,box,label):
 x,y,w,h=box
 shape=p['shape']
 # OCCT automatic projection axes put Z horizontally for Y/X views.
 # Rotate presentation only so front X and side Y are horizontal, Z up.
 if label=='front XZ':shape=shape.rotate((0,0,0),(0,1,0),-90)
 elif label=='side YZ':shape=shape.rotate((0,0,0),(1,0,0),-90)
 svg=cq.exporters.getSVG(shape,{'width':w*mm,'height':h*mm,'projectionDir':xyz,'showAxes':False,'showHidden':True,'strokeWidth':.45,'strokeColor':(20,30,40),'hiddenColor':(160,170,180),'marginLeft':12,'marginTop':12})
 svg='\n'.join(line.rstrip() for line in svg.splitlines())+'\n'
 name=p['id']+'-'+label+'.svg';(OUT/name).write_text(svg)
 drawing=svg2rlg(io.BytesIO(svg.encode()));drawing.scale(w*mm/drawing.width,h*mm/drawing.height);renderPDF.draw(drawing,c,x*mm,y*mm)
 text(x,y+h+3,label.upper()+' - fitted view (NTS)',8)
for page,p in enumerate(selected,1):
 border(p['id'],page);b=p['shape'].BoundingBox()
 view(p,(0,0,1),(18,165,125,87),'top XY')
 view(p,(0,-1,0),(155,165,105,87),'front XZ')
 view(p,(1,0,0),(274,165,120,87),'side YZ')
 text(18,155,'ENVELOPE / GLOBAL ASSEMBLY DATUM',10)
 text(18,147,f'X [{b.xmin:.3f}, {b.xmax:.3f}]  Y [{b.ymin:.3f}, {b.ymax:.3f}]  Z [{b.zmin:.3f}, {b.zmax:.3f}]')
 text(18,140,f'Overall {b.xlen:.3f} x {b.ylen:.3f} x {b.zlen:.3f}; material {p["material"]}; exact STEP: {p["id"]}.step')
 text(18,132,'Assembly origin: X0 centreline; Y75 arm axis; Z0 tabletop. Ordinate features below use these datums.')
 text(18,125,'Metal general linear +/-0.10; hole centres +/-0.10; cut silicone +/-0.50; threads as called out; deburr R0.5.')
 yy=117
 for line in [p['process'],*p['notes']]:
  for row in textwrap.wrap(line,150):text(18,yy,row,8);yy-=4
 yy-=2;text(18,yy,'FEATURES: entry X/Y/Z ; axis ; bore/depth ; machining callout',9);yy-=5
 for f in p['features']:
  pos='/'.join(f'{v:.3f}' for v in f['entry_mm']);ax='/'.join(str(v) for v in f.get('axis',[]))
  dim=f'D{f["model_diameter_mm"]:.3f} x {f["depth_mm"]:.3f}' if 'model_diameter_mm' in f else 'profile slot'
  line=f'{pos} ; [{ax}] ; {dim} ; {f["callout"]}'
  for row in textwrap.wrap(line,165):
   if yy<27:raise ValueError('Feature table exceeds page: '+p['id'])
   text(18,yy,row,7);yy-=3.5
 c.showPage()
border('W01 WELDMENT / PURCHASED HARDWARE / RELEASE GATES',len(selected)+1)
y=252
notes=[
 'W01 consists of B06-101 deck, B06-102 rear web, B06-103 lower jaw; STEP assembly gives nominal position.',
 'Web top Z2 touches deck bottom Z2; web bottom Z-90 touches jaw top Z-90. NO overlapping plates.',
 'Continuous steel fillet weld, leg size z6 (nominal throat 4.24), both accessible sides of each plate joint.',
 'Do not weld desk pad face, clamp threaded bores or shelf tapped holes. Keep front upper fillet within Y-51..-45.',
 'Weld beads NOT represented by CAD solids; welding procedure, inspection and distortion control pending.',
 'Fixture assembly; weld sequence/stress relief agreed with fabricator; machine designated datums after weld.',
 'Bought clamp screws: 2x Ganter DIN6332-M12-100-SK (AF6); feet: 2x DIN6311-25-S with snap ring.',
 'Foot flat D25 face points UP to aluminium spreader. Supplier swivel bore/pin seat is envelope only; sample fit required.',
 'Main flange/post bolts: 4x ISO4762 M8x16 top; 4x M8x20 bottom; thread engagements12.5/13.5 mm; nominal tip gap3 mm.',
 'Shelf mounts: 4x M6x20 + washers; tray:4x M4x10 in D8.4x3 counterbores, no washer; stops:4x M4x20. Standard-hardware static audit passes; physical seats/tools still require samples.',
 'No printed cosmetic part transmits motor load or clamp preload. Never replace steel threaded jaw with printed polymer.',
 'Desk thickness budget15..60; controller box budget180x150x50,3kg; box removes toward desk interior (+Y).',
 'Base flange follows interface-contract.json independently of any arm; T01 test plate8mm + washer1.6mm gives10.4mm engagement with M6x20.',
 'Native IO PCB Gerber/IPC356 exists separately; passive board is not an EtherCAT master/ESC or GMSL decoder.',
 'Remaining gates: full bolts/tools/weld clearance; material/load screening; LED PCB/power; cable bend/strain relief; slicing.',
 'After coordinated files pass: unpowered prototype build and inspection, then restrained desk/thermal/electrical tests.',
 'This document supports design review and fabricator DFM discussion. Do not order a complete base using this file alone.'
]
for n in notes:
 for row in textwrap.wrap(n,145):text(18,y,row,9);y-=5
 y-=3
c.showPage();c.save()
meta={'cad_source_sha256':hashlib.sha256(Path(cad.__file__).read_bytes()).hexdigest(),'pdf_sha256':hashlib.sha256((OUT/'B06-load-frame-review.pdf').read_bytes()).hexdigest(),'sheets':len(selected)+1,'status':'Review candidate; explicit unreleased gates on final sheet'}
(OUT/'provenance.json').write_text(json.dumps(meta,indent=2)+'\n');print('DRAWN',meta['sheets'])
