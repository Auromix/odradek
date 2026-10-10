# SPDX-License-Identifier: CC-BY-NC-4.0
"""Ordinary stock cut/drill trial sheets from the selected source BREP."""
import json,csv
import numpy as np,cadquery as cq
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.lib.units import mm
import common as c
from assembly_sources import collect

def main():
    rows,sources,_=collect(last='skins06');stock=[p for p in rows if p['role']=='purchased_structure']
    selected=[p for p in stock if p['id'] in ['A16-R104-spacer-1','A16-S105-upper-stock-tube','A16-S108-fore-stock-tube']]
    assert len(stock)==6 and len(selected)==3
    pdf=canvas.Canvas(str(c.OUT/'stock07-fit-drawings.pdf'),pagesize=landscape(A3))
    records=[]
    def txt(x,y,s,size=9):pdf.setFont('Helvetica',size);pdf.drawString(x*mm,y*mm,s)
    for p in selected:
        shape=cq.importers.importStep(str(c.ROOT/p['step_path'])).val();bb=shape.BoundingBox()
        lo=np.array([bb.xmin,bb.ymin,bb.zmin]);hi=np.array([bb.xmax,bb.ymax,bb.zmax])
        spacer='R104' in p['id'];upper='S105' in p['id']
        if spacer:
            note=['Qty4 equal stock steel sleeves; OD12 / ID6; axial cut96.5 +0/-0.1mm.',
                  'Square both ends and deburr. Equal-length full annular seating; not printed columns.',
                  'No threads or cross holes. See current assembly07 for plate stack, not the historical R102 stack.']
            holes=[];length=96.5
        else:
            holes=[10,22,200,212] if upper else [7,17,40,50];length=220 if upper else 55
            note=[f'Qty1 stock6061-T6 rectangular tube20x40x2; cut length{length}mm. Nominal trial only.',
                  'Datum A=cut beginning (minimumCAD X); datum B=bottom(minimumCAD Z); datum C=outer20-wide side.',
                  f'4xD4.5 THRU both20-width walls, X from datum A: {", ".join(map(str,holes))}mm; Z from B=20mm.',
                  'Saw/drill/deburr with fixture; supported-fit targets length+/-0.2 and hole position+/-0.2mm.',
                  'Eight OD8/ID4.5/L16 anti-crush sleeves across both tubes; confirm actual inside width before clamping.']
            assert np.allclose(hi-lo,[length,20,40],atol=1e-5)
        edgepts=[np.array([e.positionAt(float(t)).toTuple() for t in np.linspace(0,1,2 if e.geomType()=='LINE' else 60)]) for e in shape.Edges()]
        pdf.setLineWidth(.15*mm);pdf.rect(10*mm,10*mm,400*mm,277*mm)
        txt(16,276,p['id']+(' / ALL FOUR IDENTICAL SLEEVES' if spacer else ''),14)
        txt(16,264,'mm | STOCK CUT / DRILL TRIAL | source CAD coordinates | supported, unpowered, unloaded',10)
        for k,(label,axes) in enumerate([('XY',(0,1)),('XZ',(0,2)),('YZ',(1,2))]):
            span=(hi-lo)[list(axes)];scale=min(116/max(span[0],1),135/max(span[1],1),1)
            origin=np.array([18+131*k,110]);txt(origin[0],246,label+' all edges, hidden included',8)
            for edge in edgepts:
                pts=(edge[:,axes]-lo[list(axes)])*scale+origin;path=pdf.beginPath();path.moveTo(*(pts[0]*mm))
                for pt in pts[1:]:path.lineTo(*(pt*mm))
                pdf.drawPath(path)
            txt(origin[0],102,f'BREP span{span[0]:.3f}x{span[1]:.3f}; scale{scale:.3f}',8)
        for i,line in enumerate(note):txt(16,87-10*i,line)
        txt(16,22,'Prototype dimensions only. Material certification, structural loads and production GD&T unqualified.',8)
        pdf.showPage();records.append(dict(id=p['id'],quantity=4 if spacer else 1,source_step_path=p['step_path'],source_step_sha256=c.sha(c.ROOT/p['step_path']),cad_bounds_mm=[lo.tolist(),hi.tolist()],length_mm=length,hole_x_from_start_mm=holes,hole_z_from_bottom_mm=None if spacer else 20,hole_diameter_mm=None if spacer else 4.5,notes=note))
    pdf.save()
    (c.OUT/'stock07.json').write_text(json.dumps(dict(layout=c.L,stock_piece_count=6,drawing_page_count=3,parts=records,drawing_sha256=c.sha(c.OUT/'stock07-fit-drawings.pdf'),production_release=False),indent=2)+'\n')
    with (c.OUT/'stock07-drill-table.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['part','hole','x_from_start_mm','z_from_bottom_mm','diameter_mm','direction'])
        for p in records:
            for i,x in enumerate(p['hole_x_from_start_mm']):w.writerow([p['id'],i+1,x,20,4.5,'THRU 20mm width, both walls'])
    print('STOCK07',len(records),'sheets;6 stock pieces',flush=True)

if __name__=='__main__':main()
