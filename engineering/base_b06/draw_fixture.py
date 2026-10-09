# SPDX-License-Identifier: CC-BY-NC-4.0
"""Coordinated machining-review sheets from exported native fixture STEP."""
from pathlib import Path
import json,hashlib,io,textwrap
import cadquery as cq
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.lib.units import mm
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg
HERE=Path(__file__).resolve().parent;OUT=HERE/'build/standalone-test';D=OUT/'drawings'
manifest=json.loads((OUT/'fixture-manifest.json').read_text())
parts=manifest['parts'][:2];W,H=landscape(A3)
pdf=D/'B06-standalone-fixture-review.pdf';c=canvas.Canvas(str(pdf),pagesize=(W,H));c.setTitle('B06 standalone fixture - machining review')
def text(x,y,s,size=8):c.setFont('Helvetica',size);c.drawString(x*mm,y*mm,s)
for n,p in enumerate(parts,1):
    step=OUT/p['step'];assert hashlib.sha256(step.read_bytes()).hexdigest()==p['step_sha256']
    shape=cq.importers.importStep(str(step)).val();b=shape.BoundingBox()
    c.setStrokeColorRGB(.2,.25,.3);c.rect(10*mm,10*mm,W-20*mm,H-20*mm)
    text(16,280,'AUROMIX / ODRADEK | B06-TEST-01 | '+p['id'],13)
    text(16,271,'INDEPENDENT BASE TEST FIXTURE - METAL ONLY - APPARATUS QUALIFICATION PENDING',9)
    for label,projection,rect in [('TOP XY',(0,0,1),(18,165,125,90)),('FRONT XZ',(0,-1,0),(161,165,112,90)),('SIDE YZ',(1,0,0),(284,165,112,90))]:
        x,y,w,h=rect;shown=shape
        if label=='FRONT XZ':shown=shape.rotate((0,0,0),(0,1,0),-90)
        elif label=='SIDE YZ':shown=shape.rotate((0,0,0),(1,0,0),-90)
        svg=cq.exporters.getSVG(shown,{'width':w*mm,'height':h*mm,'projectionDir':projection,'showAxes':False,'showHidden':True,'strokeWidth':.5,'marginLeft':12,'marginTop':12})
        svg='\n'.join(s.rstrip() for s in svg.splitlines())+'\n';(D/(p['id']+'-'+label.replace(' ','-')+'.svg')).write_text(svg)
        drawing=svg2rlg(io.BytesIO(svg.encode()));renderPDF.draw(drawing,c,x*mm,y*mm)
        text(x,y+h+2,label+' / fitted view, NTS')
    text(18,156,f'Material: {p["material"]}; envelope {b.xlen:.3f} x {b.ylen:.3f} x {b.zlen:.3f} mm',9)
    text(18,149,f'Global X [{b.xmin:.3f},{b.xmax:.3f}] Y [{b.ymin:.3f},{b.ymax:.3f}] Z [{b.zmin:.3f},{b.zmax:.3f}]')
    text(18,142,'Assembly datum: base upper plane Z58; axis XY(0,75). Machining coordinates below use this common datum.')
    yy=135
    for s in [p['process'],*p['notes']]:
        for row in textwrap.wrap(s,155):text(18,yy,row);yy-=4
    yy-=3;text(18,yy,'FEATURES / entry X,Y,Z mm / axis direction / bore and depth / required machining',9);yy-=6
    for i,f in enumerate(p['features'],1):
        s=f'{i:02d}  '+','.join(f'{x:.3f}' for x in f['entry_mm'])+' ; axis '+','.join(str(x) for x in f['axis'])+f' ; D{f["model_diameter_mm"]:.3f} depth{f["depth_mm"]:.3f} ; '+f['callout']
        for row in textwrap.wrap(s,163):
            if yy<31:raise ValueError('Feature table overflow')
            text(18,yy,row,7.5);yy-=3.7
    text(16,22,'Threads shown as pilot bores. Use STEP + explicit callouts; do not scale views. Inspect actual apparatus before loads.',8)
    text(16,16,'ENGINEERING REVIEW CANDIDATE - NOT PRODUCTION OR LOAD RELEASE',10)
    text(365,11,f'Sheet {n}/2',8);c.showPage()
c.save()
report={'pdf':pdf.name,'sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'fixture_manifest_sha256':hashlib.sha256((OUT/'fixture-manifest.json').read_bytes()).hexdigest(),
        'parts':{p['id']:p['step_sha256'] for p in parts},'status':'machining review, not signed production release'}
(D/'drawing-provenance.json').write_text(json.dumps(report,indent=2)+'\n');print('FIXTURE_DRAWINGS',pdf)
