# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""CONTACT02 in-place molded keys; exact nominal CAD, not load qualification."""
import hashlib,json,math
from pathlib import Path
import cadquery as cq
import numpy as np
import trimesh
import ezdxf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4,landscape
from pypdf import PdfReader
from build_layout import moved

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/pad-retention-study'
SOURCE=ROOT/'engineering/generated/contact02-study'
STEM_D,HEAD_D,HEAD_DEPTH,BACK_RECESS=3.,4.5,1.2,.2
CENTERS=[(-14.,-3.5),(-4.,-3.5),(-14.,3.5),(-4.,3.5)]

def cylinder(d,z,h,x,y):
    return cq.Solid.makeCylinder(d/2,h,cq.Vector(x,y,z),cq.Vector(0,0,1))

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def export(name,shape):
    assert shape.isValid() and len(shape.Solids())==1
    paths={}
    for extension in ['step','stl']:
        p=OUT/(name+'.'+extension);cq.exporters.export(shape,str(p),tolerance=.015,angularTolerance=.1)
        paths[extension]=p
    back=cq.importers.importStep(str(paths['step'])).val()
    sym=back.cut(shape).Volume()+shape.cut(back).Volume()
    mesh=trimesh.load_mesh(paths['stl']);mesh.merge_vertices()
    assert sym<1e-5 and mesh.is_watertight and mesh.is_winding_consistent
    assert len(mesh.split())==1 and abs(mesh.volume-shape.Volume())/shape.Volume()<.002
    return {'part_id':name,'volume_mm3':shape.Volume(),'step_symmetric_difference_mm3':sym,
            'stl_watertight':bool(mesh.is_watertight),'stl_winding_consistent':bool(mesh.is_winding_consistent),
            'stl_volume_relative_error':abs(mesh.volume-shape.Volume())/shape.Volume(),
            'sha256':{k:sha(p) for k,p in paths.items()}}

def draw_pdf(rows):
    W,H=landscape(A4);c=canvas.Canvas(str(OUT/'ODR-PAD-RETENTION-01-review.pdf'),pagesize=(W,H))
    c.setTitle('Odradek CONTACT02 molded pad keys - nominal review')
    for n,r in enumerate(rows,1):
        c.setFillColorRGB(.05,.2,.3);c.setFont('Helvetica-Bold',19)
        c.drawString(28,H-35,'ODRADEK / MOLDED PAD KEYS')
        c.setFont('Helvetica',10);c.drawString(28,H-53,f'{r["variant"]} finger | all dimensions mm | nominal prototype / NOT RELEASED')
        # Backside detailed view; origin at the actual blade toe, x runs left.
        ox,oy,s=274,386,9.
        def line(a,b):c.line(ox+a[0]*s,oy+a[1]*s,ox+b[0]*s,oy+b[1]*s)
        c.setLineWidth(.8);c.setStrokeColorRGB(.1,.2,.25)
        c.rect(ox-20*s,oy-8*s,22*s,16*s,fill=0)
        c.setDash(3,2)
        for cy in [-3.5,3.5]:c.rect(ox-18*s,oy+(cy-2.5)*s,18*s,5*s,fill=0)
        c.setDash()
        for x,y in CENTERS:
            c.circle(ox+x*s,oy+y*s,HEAD_D/2*s);c.circle(ox+x*s,oy+y*s,STEM_D/2*s)
            line((x-.8,y),(x+.8,y));line((x,y-.8),(x,y+.8))
        c.setFont('Helvetica-Bold',10);c.drawString(58,482,'BACK VIEW / coupon outline only')
        c.setFont('Helvetica',8);c.drawString(58,299,'Dashed: two pad footprints, 18 x 5, centers y = +/-3.5')
        c.drawString(58,285,'Coupon: x = -20...+2; y = -8...+8; z = 0...6')
        c.drawString(58,271,'Full blade retains CONTACT02 outline; toe datum x = 0')
        # Explicit section at either pad center. Soft key underside is recessed.
        bx,by,ss=272,151,9.
        def poly(v,fillcolor):
            c.setFillColorRGB(*fillcolor);p=c.beginPath();p.moveTo(bx+v[0][0]*ss,by+v[0][1]*ss)
            for x,z in v[1:]:p.lineTo(bx+x*ss,by+z*ss)
            p.close();c.drawPath(p,stroke=1,fill=1)
        poly([(-20,0),(2,0),(2,6),(-20,6)],(.82,.86,.88))
        for x in [-14.,-4.]:
            poly([(x-2.25,0),(x+2.25,0),(x+2.25,1.2),(x+1.5,1.2),(x+1.5,6),(x-1.5,6),(x-1.5,1.2),(x-2.25,1.2)],(1,1,1))
            poly([(x-2.25,.2),(x+2.25,.2),(x+2.25,1.2),(x+1.5,1.2),(x+1.5,6),(x-1.5,6),(x-1.5,1.2),(x-2.25,1.2)],(.28,.66,.60))
        k=r['cot_q'];poly([(-18,6),(0,6),(0,11+9*k),(-18,11-9*k)],(.28,.66,.60))
        c.setFillColorRGB(.05,.2,.3);c.setFont('Helvetica-Bold',10);c.drawString(58,115,'A-A / through y = +/-3.5')
        c.setFont('Helvetica',8);c.drawString(58,99,'Soft undercuts are cast in place; no adhesive strength credited.')
        x=370;y=473;c.setFont('Helvetica-Bold',11);c.drawString(x,y,'DIMENSION / FEATURE TABLE');y-=23
        lines=[
            'Blade datum: toe X=0, center Y=0, back Z=0.',
            f'Full blade length {r["length_mm"]:g}; thickness 6.',
            '4 x through hole diameter 3.0, axis +Z.',
            '4 x backside counterbore diameter 4.5, depth 1.2.',
            'Hole centers: X=-14 / -4; Y=-3.5 / +3.5.',
            'Hole pitch X=10; pair pitch Y=7.',
            'Soft head diameter 4.5; Z=0.2...1.2.',
            'Soft stem diameter 3.0; Z=1.2...6.',
            'Soft back recess 0.2; head thickness 1.0.',
            '2 x pad plan: X=-18...0; width 5.',
            f'Pad top Z = 11 + (X+9) * ({k:.9f}).',
            f'Pad thickness: X=-18: {5-9*k:.6f}; X=0: {5+9*k:.6f}.',
            f'Pad wedge reference q = {r["target_q_deg"]:.6f} deg.',
            f'Min. nominal bore-to-outline ligament: {r["min_head_to_outer_edge_mm"]:.6f}.',
            'Material: blade 6061-T6 candidate; soft DS30 candidate.',
            'Prototype coupons: printed geometry, NOT load-rated.',
            'Deburr hole edges; radius/tolerance/shrinkage not frozen.',
            'Do not machine or mold as a released load-bearing part.',
        ]
        c.setFont('Helvetica',9)
        for line_text in lines:c.drawString(x,y,line_text);y-=17
        c.setFont('Helvetica',8);c.drawString(28,39,'ODR-PAD-RETENTION-01 | Auromix contributors | CC-BY-NC-4.0 | Nominal drawing, dimensions govern')
        c.drawRightString(W-28,22,f'{n}/2');c.showPage()
    c.save();assert len(PdfReader(OUT/'ODR-PAD-RETENTION-01-review.pdf').pages)==2

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    study=json.loads((SOURCE/'study.json').read_text());p=json.loads((ROOT/'engineering/parameters/r4-layout.json').read_text())
    face=np.array(p['head']['face_center_mm']);rows=[];inputs={str((SOURCE/'study.json').relative_to(ROOT)):sha(SOURCE/'study.json')}
    contact_case=next(c for c in study['contact_cases'] if c['diameter_mm']==80 and c['z_limits_mm']==[115.,155.])
    grasp=next(g for g in contact_case['conditional_grasps'] if g['mu']==.4 and g['cap_Nm']==3.7)
    assert grasp['feasible']
    fig,axs=plt.subplots(2,2,figsize=(11,7),layout='constrained')
    for row_index,fi in enumerate([0,2]):
        f=study['fingers'][fi];variant='UPPER' if fi==0 else 'LOWER';L=f['length_mm'];phi=np.deg2rad(f['phi_deg'])
        er=np.array([np.cos(phi),np.sin(phi),0]);et=np.array([-np.sin(phi),np.cos(phi),0]);T=np.eye(4)
        T[:3,:3]=np.column_stack([er,et,[0,0,1.]])
        T[:3,3]=face+f['root_radius_mm']*er+[0,0,f['root_z_mm']]
        Tinverse=np.linalg.inv(T);shift=np.eye(4);shift[0,3]=-L
        def original(kind):
            path=SOURCE/'parts-step'/f'{f["id"]}_{kind}.step';inputs[str(path.relative_to(ROOT))]=sha(path)
            return moved(cq.importers.importStep(str(path)).val(),shift@Tinverse)
        oldbody=original('structure');oldpads=[original('pad_minus'),original('pad_plus')]
        holes=[];keys=[]
        for x,y in CENTERS:
            holes.append(cylinder(HEAD_D,0,HEAD_DEPTH,x,y).fuse(cylinder(STEM_D,HEAD_DEPTH,6-HEAD_DEPTH,x,y)).clean())
            keys.append(cylinder(HEAD_D,BACK_RECESS,HEAD_DEPTH-BACK_RECESS,x,y).fuse(cylinder(STEM_D,HEAD_DEPTH,6-HEAD_DEPTH,x,y)).clean())
        body=oldbody
        for hole in holes:body=body.cut(hole)
        body=body.clean();pads=[oldpads[k].fuse(*keys[k*2:k*2+2]).clean() for k in [0,1]]
        coupon=cq.Workplane('XY').box(22,16,6,centered=(False,True,False)).translate((-20,0,0)).val()
        for hole in holes:coupon=coupon.cut(hole)
        coupon=coupon.clean()
        # Geometry is a subset of the prior combined body/pad envelope. This
        # transfers the previous nominal external separation, not compliance.
        previous=oldbody.fuse(*oldpads).clean();current=body.fuse(*pads).clean()
        outside=current.cut(previous).Volume();removed=previous.cut(current).Volume()
        assert outside<1e-6 and abs(removed-4*math.pi*(HEAD_D/2)**2*BACK_RECESS)<1e-6
        assert all(body.intersect(pad).Volume()<1e-6 for pad in pads)
        assert pads[0].distance(pads[1])>=2-1e-6
        records=[export(f'ODR-RET-{variant}-{suffix}',s) for suffix,s in [('BLADE',body),('COUPON',coupon),('PAD-MINUS',pads[0]),('PAD-PLUS',pads[1])]]
        # Exact distance from each circle center to the convex original blade
        # outline, minus radius; each full counterbore must fit the metal plan.
        W=f['width_mm'];outline=np.array([(-L,-W*.27),(-.82*L,-W*.5),(0,-7),(0,7),(-.82*L,W*.5),(-L,W*.27)])
        margins=[]
        for center in CENTERS:
            point=np.array(center)
            for a,b in zip(outline,np.roll(outline,-1,axis=0)):
                e=b-a;t=np.clip((point-a)@e/(e@e),0,1)
                margins.append(float(np.linalg.norm(point-(a+t*e))-HEAD_D/2))
        # Transform a documented feasible force solution to the rotating blade
        # basis. This is a witness, not worst-case sizing or minimum force.
        q=np.deg2rad(contact_case['fingers'][fi]['components']['pad_minus']['q_deg']);co,si=np.cos(q),np.sin(q)
        B=T[:3,:3]@np.array([[co,0,-si],[0,1,0],[si,0,co]])
        force_rows=[]
        for side in [0,1]:
            F=-B.T@np.array(grasp['forces_on_object_N'][fi*2+side]);shear=float(np.linalg.norm(F[:2]))
            hit=contact_case['fingers'][fi]['components']['pad_minus' if side==0 else 'pad_plus']
            root=f['root_radius_mm']*er+np.array([0,0,f['root_z_mm']])
            point=B.T@(np.array(hit['point_head_mm'])-root)-np.array([L,0,0])
            center=np.array([-9.,-3.5 if side==0 else 3.5,6.]);moment=np.cross(point-center,F)
            # If the in-plane resultant is carried at the footprint center,
            # these are the compression-only center-of-pressure offsets.
            # This is a diagnostic force-path assumption, not pressure FEA.
            cop=[float(-moment[1]/F[2]),float(moment[0]/F[2])] if F[2]<0 else None
            force_rows.append({'pad':'minus' if side==0 else 'plus','force_on_pad_blade_N':F.tolist(),
                'force_application_point_toe_mm':point.tolist(),'moment_about_pad_base_center_Nmm':moment.tolist(),
                'center_of_pressure_diagnostic_offset_mm':cop,
                'center_of_pressure_inside_18x5_footprint':bool(abs(cop[0])<=9 and abs(cop[1])<=2.5) if cop else False,
                'in_plane_shear_N':shear,'net_outward_force_N':max(0.,float(F[2])),
                'two_stem_average_shear_MPa':shear/(2*math.pi*(STEM_D/2)**2),
                'two_head_annulus_average_net_tension_MPa':max(0.,float(F[2]))/(2*math.pi*((HEAD_D/2)**2-(STEM_D/2)**2))})
        row={'variant':variant,'finger_reference':f['id'],'length_mm':L,'target_q_deg':f['pad_target_q_deg'],
            'cot_q':1/math.tan(math.radians(f['pad_target_q_deg'])),
            'outside_original_envelope_mm3':outside,'recess_void_volume_mm3':removed,
            'min_head_to_outer_edge_mm':min(margins),'new_blade_volume_mm3':body.Volume(),
            'removed_metal_mm3':oldbody.Volume()-body.Volume(),'added_soft_key_volume_mm3':sum(k.Volume() for k in keys),
            'pad_intersection_volume_mm3':pads[0].intersect(pads[1]).Volume(),'pad_pair_min_distance_mm':pads[0].distance(pads[1]),
            'parts':records,'force_witness':force_rows}
        rows.append(row)
        # Native DXF is a 1:1 local feature reference, with layers that cannot be
        # mistaken for a flattened single laser-cut outline.
        doc=ezdxf.new('R2010');doc.units=4
        for layer in ['BLADE','THROUGH_D3','BACK_CB_D4_5','PAD_PLAN','COUPON']:
            doc.layers.new(layer)
        model=doc.modelspace();model.add_lwpolyline(outline.tolist(),close=True,dxfattribs={'layer':'BLADE'})
        model.add_lwpolyline([(-20,-8),(2,-8),(2,8),(-20,8)],close=True,dxfattribs={'layer':'COUPON'})
        for x,y in CENTERS:
            for rr,layer in [(1.5,'THROUGH_D3'),(2.25,'BACK_CB_D4_5')]:model.add_circle((x,y),rr,dxfattribs={'layer':layer})
        for y in [-3.5,3.5]:model.add_lwpolyline([(-18,y-2.5),(0,y-2.5),(0,y+2.5),(-18,y+2.5)],close=True,dxfattribs={'layer':'PAD_PLAN'})
        doc.saveas(OUT/f'ODR-RET-{variant}-features.dxf');back=ezdxf.readfile(OUT/f'ODR-RET-{variant}-features.dxf')
        assert back.units==4 and len(back.modelspace().query('CIRCLE'))==8 and not back.audit().has_errors
        ax=axs[row_index,0];ax.fill(*outline.T,color='#cbd3d7');ax.set_xlim(-23,3);ax.set_ylim(-9,9)
        for y in [-3.5,3.5]:ax.add_patch(plt.Rectangle((-18,y-2.5),18,5,fill=False,edgecolor='#1c847a',ls='--'))
        for x,y in CENTERS:
            ax.add_patch(plt.Circle((x,y),2.25,facecolor='#91c5bd',edgecolor='#28695f'));ax.add_patch(plt.Circle((x,y),1.5,fill=False,edgecolor='#254957'))
        ax.set(aspect='equal',xlabel='X from blade toe / mm',ylabel='Y / mm',title=variant+' / backside retaining heads')
        ax=axs[row_index,1];ax.add_patch(plt.Rectangle((-20,0),22,6,facecolor='#cbd3d7'))
        k=row['cot_q'];ax.fill([-18,0,0,-18],[6,6,11+9*k,11-9*k],color='#4ca99b')
        for x in [-14,-4]:
            ax.add_patch(plt.Rectangle((x-2.25,0),4.5,1.2,facecolor='white'))
            ax.add_patch(plt.Rectangle((x-2.25,.2),4.5,1.,facecolor='#4ca99b'))
            ax.add_patch(plt.Rectangle((x-1.5,1.2),3.,4.8,facecolor='#4ca99b'))
        ax.set(aspect='equal',xlim=(-23,3),ylim=(-1,14),xlabel='X from blade toe / mm',ylabel='Z / mm',title=variant+' / section at either pad center')
    fig.suptitle('CONTACT02 molded-key retention / geometry study, not a qualified joint')
    fig.savefig(OUT/'pad-retention-section.png',dpi=170);plt.close(fig);draw_pdf(rows)
    report={'revision':'R4-PAD-RETENTION-01','input_sha256':inputs,'generator_sha256':sha(Path(__file__)),
        'manufacturing_release':False,'dimensions_mm':{'stem_d':STEM_D,'head_d':HEAD_D,'counterbore_depth':HEAD_DEPTH,'back_recess':BACK_RECESS,'hole_centers_toe_xy':CENTERS},
        'variants':rows,'pair_of_stems_area_mm2':2*math.pi*(STEM_D/2)**2,
        'pair_of_head_annuli_area_mm2':2*math.pi*((HEAD_D/2)**2-(STEM_D/2)**2),
        'limits':['No adhesion credited. In-place molding process and air removal not qualified.',
                  'Nominal sharp holes; practical edge radius, material tolerance and casting shrinkage not frozen.',
                  'Silicone allowable peel/shear/tear, compression, creep and fatigue not measured.',
                  'Average stress proxy is not local key-root stress or a rated load.',
                  'Zero net outward force does not exclude moment-induced local peel; center-of-pressure diagnostic assumes centered in-plane transfer.',
                  'Force witness uses 80x40 cylinder, mu .4, 2 kg x2 gravity, cap 3.7 Nm, no self weight or drive losses.',
                  'Printed coupon is a separate bench sample, not a gripper insert.',
                  'No claim for deformed pad external collision or PCB/harness integration.']}
    report['output_sha256']={p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='verification.json'}
    (OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'variants':[{'type':r['variant'],'edge_mm':r['min_head_to_outer_edge_mm'],'force':r['force_witness']} for r in rows],
                      'parts':sum(len(r['parts']) for r in rows),'outside_mm3':[r['outside_original_envelope_mm3'] for r in rows]},indent=2))

if __name__=='__main__':main()
