# SPDX-License-Identifier: CC-BY-NC-4.0
"""Dimensioned A3 root FIT drawings and separate bed-space STL package."""
import json, math, hashlib, zipfile
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A3,landscape
import trimesh
import common as c

O=c.OUT/'root01'

def main():
    D=json.loads((O/'manifest.json').read_text());P=O/'print-bed';P.mkdir(exist_ok=True)
    rows=[]
    for p in D['parts']:
        if p['role']!='printed_structure':continue
        s=O/'stl'/(p['id']+'.stl');m=trimesh.load(s,force='mesh');t=-m.bounds[0];t[:2]=-(m.bounds[0,:2]+m.bounds[1,:2])/2
        m.apply_translation(t);target=P/s.name;m.export(target)
        assert m.is_watertight and abs(m.bounds[0,2])<1e-6
        rows.append(dict(id=p['id'],object_stl_sha256=c.sha(s),bed_stl_sha256=c.sha(target),T_bed_translation_mm=t.tolist(),unit='mm',bed_dimensions_mm=m.extents.tolist()))
    (O/'print-bed-transforms.json').write_text(json.dumps(rows,indent=2)+'\n')
    pdf=canvas.Canvas(str(O/'A16-ROOT01-fit-drawings.pdf'),pagesize=landscape(A3));pdf.setTitle('A16 ROOT01 - dimensional fit issue, not load release')
    def line(x,y,a,b):pdf.line(x*mm,y*mm,a*mm,b*mm)
    def text(x,y,s,size=9):pdf.setFont('Helvetica',size);pdf.drawString(x*mm,y*mm,s)
    def circle(x,y,r):pdf.circle(x*mm,y*mm,r*mm,stroke=1,fill=0)
    def dimension(x,y,a,b,label):
        line(x,y,a,b);circle(x,y,.7);circle(a,b,.7);text((x+a)/2+2,(y+b)/2+2,label)
    def sheet(name,note):
        pdf.setLineWidth(.22*mm);pdf.rect(10*mm,10*mm,400*mm,277*mm);line(10,35,410,35)
        text(15,278,name,17);text(15,267,note,10)
        text(15,27,'A16 / ROOT01  |  FIT ISSUE ONLY  |  mm  |  1:1 nominal views on A3',10)
        text(15,19,'Supported, unpowered, no payload. Printed dimensions need coupons. No3kg load or production qualification.',9)
    def plan(ro,ri,points,d):
        x,y=100,170;circle(x,y,ro)
        if ri:circle(x,y,ri)
        pdf.setDash(3*mm,1*mm);line(x-ro-10,y,x+ro+10,y);line(x,y-ro-10,x,y+ro+10);pdf.setDash()
        for a,b in points:circle(x+a,y+b,d/2)
        dimension(x-ro,y-ro-12,x+ro,y-ro-12,f'OD {ro*2:g}')
        if ri:text(x-ri+2,y+5,f'ID {ri*2:g}')
    def coords(points,x,y):
        text(x,y,'Hole coordinates in local XY; datum B at centre',9)
        for k,(a,b) in enumerate(points,1):text(x,y-5-k*4.6,f'{k:02d}   X {a:9.3f}   Y {b:9.3f}',8)
    base=[(60*math.cos(math.radians(22.5+45*k)),60*math.sin(math.radians(22.5+45*k))) for k in range(8)]
    cols=[(60,0),(0,60),(-60,0),(0,-60)]
    sheet('A16-R101 BASE ADAPTER','PETG / PA12 trial; planar plate. Bottom datum A at assembly Z58. OD134 +/-0.15 after coupon compensation.')
    plan(67,28,base,6.6)
    for x,y in cols:
        circle(100+x,170+y,2.8)
        path=pdf.beginPath()
        for k in range(6):
            t=k*math.pi/3;r=8.3/(2*math.cos(math.pi/6));a,b=(100+x+r*math.cos(t))*mm,(170+y+r*math.sin(t))*mm
            (path.moveTo if k==0 else path.lineTo)(a,b)
        path.close();pdf.drawPath(path)
    coords(base,195,232)
    text(195,175,'8x D6.6 THRU / PCD120 /22.5 +45*k deg')
    text(195,164,'4x D5.6 THRU at (+/-60,0), (0,+/-60)')
    text(195,153,'4x AF8.3 hex nut pockets,5 deep FROM TOP')
    text(195,142,'M5 nut4.7 high;0.3 recess; pocket bottomZ61')
    pdf.rect(195*mm,95*mm,134*mm,8*mm);dimension(345,95,345,103,'8')
    text(195,81,'Bore D56 +0.2/0; general printed linear tolerance +/-0.2.')
    text(195,70,'Break sharp edges0.3; clear brim from datum A. No finishing on B06.')
    pdf.showPage()
    fixed=c.SRC['models']['RS03']['fixed_front_fasteners']['raw_step_xy_mm']
    sheet('A16-R102 J1 FRONT HOLDER','PETG / PA12 trial; flat plate. Bottom datum A at J1local Z-2.5. Ring ID72.4 +0.2/0.')
    plan(67,36.2,fixed,4.5)
    for x,y in cols:circle(100+x,170+y,2.8)
    coords(fixed,195,232)
    text(195,175,'8x D4.5 THRU / native RS03 front PCD98')
    text(195,164,'4x D5.6 THRU at (+/-60,0), (0,+/-60)')
    text(195,153,'8x M4x12 +0.8 washer: nominal insertion5.2')
    text(195,142,'Source front depth8; do NOT use rear-hole datum')
    pdf.rect(195*mm,95*mm,134*mm,6*mm);dimension(345,95,345,101,'6')
    text(195,81,'OD134 +/-0.15; print flat. Hole positions retained from native STEP.')
    text(195,70,'Check RS03 actual output register;1.2mm nominal radial running gap.')
    pdf.showPage()
    output=c.SRC['models']['RS03']['output_fasteners']['raw_step_xy_mm']
    sheet('A16-R103 J1 OUTPUT PEDESTAL','PETG / PA12 trial; conventional coaxial turned/milled form. Bottom datum A at J1 rotorZ0.')
    plan(60,0,output,4.5);circle(100,170,35)
    for x,y in output:circle(100+x,170+y,4.75)
    for x in [-38,38]:
        for y in [-28,28]:circle(100+x,170+y,2.8)
    coords(output,195,232)
    text(195,181,'6x D4.5 THRU / source output PCD30.36')
    text(195,170,'6x counterbore D9.5 x10 FROM TOP')
    text(195,159,'4x D5.6 through upper plate at X+/-38,Y+/-28')
    pdf.rect(227*mm,80*mm,70*mm,20*mm);pdf.rect(202*mm,100*mm,120*mm,10*mm)
    dimension(340,80,340,100,'20');dimension(354,100,354,110,'10')
    text(195,66,'M4x25 +0.8 washer:20 grip /4.2 insertion /source blind depth6')
    text(195,54,'Overall30; D70 +/-0.15 stem /D120 upper plate. Print A flat; coupon fit first.')
    pdf.showPage()
    sheet('A16-R104 SPACERS / ASSEMBLY STACK','Purchased steel spacers; do not print as loaded columns. Four equal lengths; saw-cut then square/deburr.')
    circle(80,185,6);circle(80,185,2.75);dimension(65,168,95,168,'OD12 / ID5.5')
    pdf.rect(150*mm,180*mm,96.5*mm,12*mm);dimension(150,165,246.5,165,'96.5 +0/-0.1')
    text(25,140,'4x spacers at PCD120 cardinal phase.4x M5x110 +washer1.0 + nut4.7 in upper-entry pockets.',11)
    text(25,126,'Nominal stack: holder6 + spacer96.5 + pocket roof gap0.3 + washer1 + nut4.7 + tip1.5 =110.',10)
    text(25,112,'Bolt head bearingZ169.5; tipZ59.5. B06 unchanged mating planeZ58:1.5mm nominal clearance.',10)
    text(25,98,'Base8x M6x20 +washer1.6:8mm grip,10.4 insertion into THRU; verify underside against actual base.',10)
    text(25,84,'Prototype assembly first: no motor power, no real gas spring, external support; clear all connectors.',10)
    text(25,70,'Production metal plates, preload, material, bearing loads and fatigue require separate drawings/qualification.',10)
    pdf.save()
    files=[p for p in O.rglob('*') if p.is_file() and p.suffix in ['.step','.stl','.csv','.pdf','.json'] and p.name!='meshes.json']
    target=O/'A16-root-supported-fit.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(O))
        z.write(c.HERE/'README.md','README.md')
        z.writestr('SHA256SUMS.txt',''.join(f'{c.sha(p)}  {p.relative_to(O)}\n' for p in files))
    with zipfile.ZipFile(target) as z:assert z.testzip() is None
    print('ROOT_PACKAGE',len(files),'files',target,flush=True)

if __name__=='__main__':main()
