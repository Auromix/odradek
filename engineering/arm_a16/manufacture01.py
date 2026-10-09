# SPDX-License-Identifier: CC-BY-NC-4.0
"""Core print-bed files, dimensional drawing issue and stock/hardware BOM.

Not a production release; cosmetic candidates intentionally excluded.
"""
import csv,itertools,json,math,zipfile
from collections import Counter
import numpy as np,trimesh,cadquery as cq,ezdxf
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.lib.units import mm
import common as c
from vendor import interfaces

O=c.OUT/'manufacture01';O.mkdir(exist_ok=True)
DETAIL={
'S101':['Foot8 thick: X-55..55; Y-36..68.5; Z30..38.','4xD5.6: X+/-38,Y+/-28, parallelZ.','J2 fixed annulus OD134 ID80, faceY68.5, Z centre114.','8-thick annulus, native10xD4.5 RS04 front holes.','Wire capsule6x14,endR3,centreR55 at55deg;235deg port lies outside foot.'],
'S102':['J2 output faceY68;10-thick,OD70; native9xD5.5.','J3 annulus shiftedY-15: OD134 ID80,8thick.','Native J3 front10xD4.5;3xD6.5x3.6 locating-pin reliefs.','Output /fixed tool boresD10 /D9.5; native point table attached.'],
'S103':['Native J3 output faceX27.85; OD70 x10.','SocketX50..75.1; nominal20.4x40.4 internal.','Stock tube startsX50; clamp centresX60/72, Z0.','2xD4.5 parallelY; M4x35 with OD8/ID4.5/L16 crush sleeves.'],
'S104':['Native J4 fixed faceY27.35, centreX340;8 thick.','SocketX244.9..270;20.4x40.4; tube endsX270.','ClampX250/262,Z0; D4.5 parallelY.','D11 open tool reliefs fromY14 towards+Y,36deep.'],
'S105':['Purchased rectangular6061-T6 tube20x40x2, L220.','4xD4.5 through the20mm width; holesX10/22/200/212 from cut end.','Hole axisparallelY; Z0 (20 from bottom40mm face).','8x nominal material surfaces: verify stock dimensions and squareness.'],
'S106':['Native J4 output faceY27.85; OD70x10.','Tube socketX20..40.1,20.4x40.4, centreY62.','ClampsX27/37,Z0,D4.5 parallelY.','Native9xD5.5 and3xD6.5x3.6 pin reliefs.'],
'S107':['Rear-spine conventionalU bracket; J5 fixed centreX185,Y62.','Tube socketX49.9..75; nominal20.4x40.4, centreY62.','ClampsX60/70,Z0,D4.5 parallelY; D11 tool reliefsY76..116.','J5 front ringOD65 ID42.4;8thick; spineY95.5..103.5.'],
'S108':['Purchased rectangular6061-T6 tube20x40x2, L55.','4xD4.5 through20mm width; X7/17/40/50 from cut end.','Hole axisparallelY; Z0 (20 from bottom40mm face).','Hole/end spacings close: check actual drill burr and edge quality.'],
'S109':['Native J5 output faceY40;OD40x10.','J6 fixed planeZ-28.8; centreX55, ringOD65 ID42.4.','Ring clippedY+/-27.5; flat connecting spineY22..27.','6xD4.5 each native RS10P pattern; D9.5 tool reliefs.'],
'S110':['Native J6 output planeZ-30.3;OD40,10 nominal screw grip.','J7 fixed faceX100.3,8thick; centreX75.','J7 annulusOD84 ID37.4;6nativeD3.5 /PCD50.','Cage6xD3.5 PCD70,30+60*k; D8x0.6 washer-edge relief.','OutputD9.5 counterboresZ-40.3..-48.4; strapZ-48.3..-38.3.'],
}
ORIENT={
'S101':[1,-3,2], 'S102':[3,2,-1], 'S103':[-3,2,1],
'S104':[1,3,-2], 'S106':[1,3,-2], 'S107':[1,3,-2],
'S109':[1,3,-2], 'S110':[1,2,3],
}

def rotation(axes):
    a=np.zeros((3,3))
    for i,k in enumerate(axes):a[i,abs(k)-1]=1 if k>0 else -1
    assert abs(np.linalg.det(a)-1)<1e-9;return a

def main():
    D=json.loads((c.OUT/'skeleton01/manifest.json').read_text());H=json.loads((c.OUT/'hardware01/manifest.json').read_text())
    assert D['layout']==H['layout']==c.L
    sources={str((c.OUT/n/'manifest.json').relative_to(c.ROOT)):c.sha(c.OUT/n/'manifest.json') for n in ['root01','skeleton01','hardware01']}
    for folder in ['print-bed','drawings']:(O/folder).mkdir(exist_ok=True)
    rows=[];bed=[]
    pdf=canvas.Canvas(str(O/'A16-core-fit-drawings.pdf'),pagesize=landscape(A3));pdf.setTitle('A16 conventional core - dimensional fit issue')
    def txt(x,y,s,sz=9):pdf.setFont('Helvetica',sz);pdf.drawString(x*mm,y*mm,s)
    for p in D['parts']:
        src=c.OUT/'skeleton01/step'/(p['id']+'.step');sources[str(src.relative_to(c.ROOT))]=c.sha(src)
        shape=cq.importers.importStep(str(src)).val();assert shape.isValid()
        key=p['id'].split('-')[1] if p['id'].startswith('A16-') else None
        if p['role']=='printed_structure':
            obj=c.OUT/'skeleton01/stl'/(p['id']+'.stl');m=trimesh.load(obj,force='mesh');assert m.is_watertight and m.is_winding_consistent
            R=rotation(ORIENT.get(key,[-3,2,1]));v=m.vertices.copy();vr=v@R.T;t=-vr.min(axis=0);m.vertices=vr+t
            path=O/'print-bed'/(p['id']+'.stl');m.export(path);back=trimesh.load(path,force='mesh');assert back.is_watertight and back.is_winding_consistent and len(back.split())==1
            assert max(back.extents)<250 and max(abs(back.bounds[0]))<.0001
            err=float(np.max(abs((m.vertices-t)@R-v)));assert err<1e-7
            bed.append(dict(id=p['id'],source_stl_sha256=c.sha(obj),print_stl_sha256=c.sha(path),R_bed_from_cad=R.tolist(),translation_mm=t.tolist(),size_mm=back.extents.tolist(),roundtrip_error_mm=err,orientation='Deliberate assembly-flat/bore orientation; unsupported roofs and bridges require slicer inspection. Not sliced or physically printed.'))
        rows.append(dict(id=p['id'],category=p['role'],quantity=1,material=p['material'],volume_mm3=p['volume_mm3'],nominal_mass_kg=p['mass_kg'],note=p['note']))
        pdf.setLineWidth(.15*mm);pdf.rect(10*mm,10*mm,400*mm,277*mm);txt(16,276,p['id'],15)
        txt(16,265,'mm | supported, unpowered, unloaded fit issue | STEP defines complete nominal geometry',10)
        # True orthographic projection of the original BREP edges. All edges
        # shown, including hidden edges; this is labelled, not a false HLR.
        samples=[]
        for edge in shape.Edges():
            count=2 if edge.geomType()=='LINE' else 40
            samples.append(np.array([edge.positionAt(float(t)).toTuple() for t in np.linspace(0,1,count)]))
        bb=shape.BoundingBox();minimum=np.array([bb.xmin,bb.ymin,bb.zmin]);maximum=np.array([bb.xmax,bb.ymax,bb.zmax])
        for k,(label,axes) in enumerate([('XY',(0,1)),('XZ',(0,2)),('YZ',(1,2))]):
            lo=minimum[list(axes)];hi=maximum[list(axes)];span=hi-lo;scale=min(113/max(span[0],1),135/max(span[1],1),1.1)
            origin=np.array([18+131*k,108]);txt(origin[0],249,label+' all edges, hidden included',8)
            for points in samples:
                q=(points[:,axes]-lo)*scale+origin
                path=pdf.beginPath();path.moveTo(q[0,0]*mm,q[0,1]*mm)
                for a,b in q[1:]:path.lineTo(a*mm,b*mm)
                pdf.drawPath(path)
            y=origin[1]-6;pdf.line(origin[0]*mm,y*mm,(origin[0]+span[0]*scale)*mm,y*mm);txt(origin[0],y-5,f'{span[0]:.3f} overall / drawing scale{scale:.3f}',8)
            txt(origin[0],y-10,f'Vertical{span[1]:.3f}; CAD axes {label}',8)
        notes=DETAIL.get(key,['Retained original A13 cartridge/interface STEP, unmodified; source dimensions and bearing stack in linked fit documents.','J7 local mounting/shaft datums retained. Supplier motor pilot, bearing seats and captive nuts need physical gauges.'])
        for k,note in enumerate(notes):txt(16,79-k*6,note,9)
        txt(16,38,'Printed default linear +/-0.2 after coupons; drilled holes +/-0.1 as trial targets; no metal GD&T release.',9)
        txt(16,28,'No inferred tapped plastic threads. Purchased motors/tubes/steel sleeves/fasteners are not printed.',9)
        txt(16,18,'Projection scale varies per view. Original CAD frame retained. Check supports, nut access, manual fit and actual motor plugs.',8)
        pdf.showPage()
    pdf.save()
    # Exact stock drill drawing; these holes pass through20, not through40.
    stock=[]
    for key,length,xs in [('S105',220,[10,22,200,212]),('S108',55,[7,17,40,50])]:
        doc=ezdxf.new('R2010');doc.units=4;space=doc.modelspace();space.add_lwpolyline([(0,0),(length,0),(length,40),(0,40)],close=True)
        for x in xs:space.add_circle((x,20),2.25)
        space.add_text(f'{key}: tube20x40x2 / L{length} +/-0.1 /4xD4.5 through20; mm',dxfattribs={'height':2.5}).set_placement((0,47))
        space.add_text('X from cut end: '+','.join(map(str,xs))+'; Z20 from lower edge. Burr-free.',dxfattribs={'height':2.5}).set_placement((0,-8))
        path=O/'drawings'/(key+'-tube-drill.dxf');doc.saveas(path);r=ezdxf.readfile(path)
        circles=list(r.modelspace().query('CIRCLE'));assert sorted(x.dxf.center.x for x in circles)==xs and all(x.dxf.radius==2.25 for x in circles)
        stock.append(dict(id=key,length_mm=length,hole_x_from_cut_end_mm=xs,through_width_mm=20,hole_diameter_mm=4.5,dxf_sha256=c.sha(path)))
    with (O/'parts.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    counts=Counter()
    for b in H['bolts']:
        counts[f'M{b["diameter_mm"]}x{b["length_mm"]}; headOD{b["head_diameter_mm"]}xH{b["head_height_mm"]}']+=1
        counts[f'washer hole{b["diameter_mm"]+.4:g} OD{b["washer_outer_mm"]:g} thickness{b["washer_mm"]:g}']+=1
    boltids={b['id'] for b in H['bolts']}|{b['id']+'-washer' for b in H['bolts']}
    for p in H['parts']:
        if p['id'] not in boltids:counts[p['note']]+=1
    assert sum(counts.values())==len(H['parts'])
    with (O/'hardware-BOM.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['specification','quantity','scope']);w.writerows((name,n,'Nominal purchased envelope; measure delivered part') for name,n in sorted(counts.items()))
    # Native point table includes the actual nonuniform RS04 hole coordinates.
    from hardware01 import points
    with (O/'native-mount-hole-table.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['joint','model','pattern','index','x_joint_mm','y_joint_mm','z_joint_mm','axis_x','axis_y','axis_z'])
        for inf in interfaces():
            for pattern,origin in [('fixed_front_fasteners',inf['fixed_mm']),('output_fasteners',inf['out_mm'])]:
                for k,v in enumerate(points(inf,pattern),1):w.writerow([inf['joint'],inf['model'],pattern,k,*[f'{x:.6f}' for x in np.array(origin)+v],*inf['n']])
    report=dict(revision='A16-CORE-FIT01',layout=c.L,source_sha256=sources,print_parts=bed,stock_tubes=stock,hardware_parts=len(H['parts']),bolt_count=len(H['bolts']),
        exclusions=['18 cosmetic cover candidates: attachment/collision/connected wiring pending.','Motors, stock tubes, steel spacers and hardware are purchased, never printed.','External tool-side dummy cups and full flower head excluded.'],
        scope='Closed STL, proper rotation/inverse,250mm bed fit, dimensional all-edge BREP orthographics, native hole table, tube DXF and nominal BOM. Slicer/physical fit/load/metal production not qualified.',
        physical_assembly_qualified=False,production_release=False)
    (O/'print-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    files=list((O/'print-bed').glob('*.stl'))+list((O/'drawings').glob('*.dxf'))+list(O.glob('*.csv'))+[O/'print-audit.json',O/'A16-core-fit-drawings.pdf']
    files += list((c.OUT/'skeleton01/step').glob('*.step'))
    target=O/'A16-core-supported-fit.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for path in files:z.write(path,str(path.relative_to(O)) if path.is_relative_to(O) else 'step/'+path.name)
        for name in ['README.md','assembly01.md','first-sample.md']:z.write(c.HERE/name,name)
        z.writestr('SHA256SUMS.txt',''.join(c.sha(p)+'  '+(str(p.relative_to(O)) if p.is_relative_to(O) else 'step/'+p.name)+'\n' for p in files)+''.join(c.sha(c.HERE/name)+'  '+name+'\n' for name in ['README.md','assembly01.md','first-sample.md']))
    with zipfile.ZipFile(target) as z:assert z.testzip() is None
    print('CORE_MANUFACTURE',len(bed),'printable body parts',len(stock),'stock tubes',len(H['parts']),'hardware envelopes',flush=True)

if __name__=='__main__':main()
