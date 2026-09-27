# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Build unloaded RH output-interface fit coupons from measured vendor geometry.

No vendor CAD is needed here. Input is the independent interface extraction JSON.
STEP/STL/DXF, a four-page inspection PDF and verification JSON are generated.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq
import ezdxf
import numpy as np
import trimesh
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

MODELS = ['RH14-N', 'RH17-B', 'RH20-B', 'RH25-B']
PT_PER_MM = 72/25.4
BLUE=(.05,.20,.31); GREY=(.40,.46,.50); TEAL=(.03,.46,.48)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def line(c, x1,y1,x2,y2,color=BLUE,width=.7,dash=None):
    c.setStrokeColorRGB(*color);c.setLineWidth(width)
    c.setDash(dash or [])
    c.line(x1,y1,x2,y2);c.setDash([])


def text(c,x,y,s,size=9,color=BLUE,font='CJK'):
    c.setFont(font,size);c.setFillColorRGB(*color);c.drawString(x,y,s)


def arrow(c,x,y,dx,dy,size=4):
    ll=math.hypot(dx,dy);ux,uy=dx/ll,dy/ll;vx,vy=-uy,ux
    p=c.beginPath();p.moveTo(x,y);p.lineTo(x+ux*size+vx*size*.35,y+uy*size+vy*size*.35)
    p.lineTo(x+ux*size-vx*size*.35,y+uy*size-vy*size*.35);p.close()
    c.setFillColorRGB(*BLUE);c.drawPath(p,stroke=0,fill=1)


def horizontal_dim(c,x1,x2,y,from_y,label):
    line(c,x1,from_y,x1,y+6,GREY,.45);line(c,x2,from_y,x2,y+6,GREY,.45)
    line(c,x1,y,x2,y);arrow(c,x1,y,1,0);arrow(c,x2,y,-1,0)
    w=pdfmetrics.stringWidth(label,'CJK',9)
    c.setFillColorRGB(1,1,1);c.rect((x1+x2-w)/2-3,y-3,w+6,13,stroke=0,fill=1)
    text(c,(x1+x2-w)/2,y-2,label,9)


def coupon(model):
    u=model['unified_joint_interface'];holes=u['output_holes'];part='ODR-CPN-'+model['id']+'-R4'
    outer=u['outer_output_pilot']['diameter_mm']+8.
    central=u['central_clearance_boss']['diameter_mm']+.6
    thread=u['thread_depth_reference']['drawing_thread'];hole_d=3.5 if thread=='M3' else 4.5
    points=[tuple(p['xy_mm']) for p in holes['points']]
    h=4.
    for x,y in points:
        rr=math.hypot(x,y)
        if rr-hole_d/2 <= central/2 or rr+hole_d/2 >= outer/2:
            raise ValueError('Coupon has overlapping cuts')
    shape=cq.Workplane('XY').circle(outer/2).circle(central/2).extrude(h)
    shape=shape.faces('>Z').workplane().pushPoints(points).hole(hole_d)
    if not shape.val().isValid() or len(shape.val().Solids())!=1:
        raise AssertionError('Invalid coupon solid')
    expected=math.pi*h*((outer/2)**2-(central/2)**2-len(points)*(hole_d/2)**2)
    assert abs(shape.val().Volume()-expected)<1e-5
    assert len(shape.faces('>Z').val().Wires())==len(points)+2
    return {'part':part,'model':model['id'],'outer_diameter_mm':outer,'centre_hole_diameter_mm':central,
        'bolt_hole_diameter_mm':hole_d,'thickness_mm':h,'pcd_mm':holes['pcd_mm'],
        'holes':holes['points'],'nominal_volume_mm3':expected,'shape':shape,
        'source_step_sha256':model['input_sha256'],
        'T_vendor_from_joint_mm':u['T_world_from_joint_mm'],
        'thread':thread,'central_boss_height_mm':u['central_clearance_boss']['height_above_output_contact_mm']}


def export_and_check(data,out):
    stem=data['part'];shape=data['shape'];checks={}
    for sub in ['STEP','STL','DXF','coordinates']:(out/sub).mkdir(parents=True,exist_ok=True)
    step=out/'STEP'/f'{stem}.step';stl=out/'STL'/f'{stem}.stl';dxf=out/'DXF'/f'{stem}.dxf'
    cq.exporters.export(shape,str(step));cq.exporters.export(shape,str(stl),tolerance=.03,angularTolerance=.08)
    rd=cq.importers.importStep(str(step)).val()
    checks['step_valid']=rd.isValid();checks['step_solid_count']=len(rd.Solids())
    checks['step_volume_error_mm3']=abs(rd.Volume()-data['nominal_volume_mm3'])
    assert checks['step_valid'] and checks['step_solid_count']==1 and checks['step_volume_error_mm3']<1e-5
    mesh=trimesh.load(stl,force='mesh',process=True)
    checks['stl_watertight']=bool(mesh.is_watertight)
    checks['stl_body_count']=int(mesh.body_count);checks['stl_euler_number']=int(mesh.euler_number)
    checks['stl_volume_relative_error']=abs(float(mesh.volume)-data['nominal_volume_mm3'])/data['nominal_volume_mm3']
    assert checks['stl_watertight'] and checks['stl_body_count']==1
    assert checks['stl_euler_number']==-2*len(data['holes']) and checks['stl_volume_relative_error']<.003
    doc=ezdxf.new('R2010');doc.units=ezdxf.units.MM
    for name,color in [('CUT_OUTLINE',7),('CUT_CENTER',3),('CUT_BOLT',2)]:doc.layers.new(name,dxfattribs={'color':color})
    ms=doc.modelspace();ms.add_circle((0,0),data['outer_diameter_mm']/2,dxfattribs={'layer':'CUT_OUTLINE'})
    ms.add_circle((0,0),data['centre_hole_diameter_mm']/2,dxfattribs={'layer':'CUT_CENTER'})
    for p in data['holes']:ms.add_circle(p['xy_mm'],data['bolt_hole_diameter_mm']/2,dxfattribs={'layer':'CUT_BOLT'})
    doc.saveas(dxf);back=ezdxf.readfile(dxf);audit=back.audit()
    circles=list(back.modelspace().query('CIRCLE'));checks['dxf_circle_count']=len(circles)
    checks['dxf_audit_errors']=len(audit.errors);checks['dxf_units']=back.units
    assert len(circles)==len(data['holes'])+2 and not audit.errors and back.units==ezdxf.units.MM
    bolt=[c for c in circles if c.dxf.layer=='CUT_BOLT']
    for c,p in zip(bolt,data['holes']):
        assert np.allclose(np.asarray(c.dxf.center)[:2],p['xy_mm'],atol=1e-7)
        assert abs(c.dxf.radius-data['bolt_hole_diameter_mm']/2)<1e-9
    with (out/'coordinates'/f'{stem}.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['hole','x_mm','y_mm','angle_deg','diameter_mm'])
        writer.writerows([i,*p['xy_mm'],p['angle_deg'],data['bolt_hole_diameter_mm']] for i,p in enumerate(data['holes'],1))
    checks['artifact_sha256']={str(p.relative_to(out)):sha(p) for p in [step,stl,dxf]}
    return checks


def page(c,d,page_number):
    W,H=landscape(A4)
    text(c,30,H-34,'ODRADEK  /  OUTPUT INTERFACE COUPON',19,font='Helvetica-Bold')
    text(c,30,H-56,'输出接口试装样片 · 非承力 · 禁止动力运行或悬挂负载',11,color=TEAL)
    text(c,30,H-76,d['part']+'  |  '+d['model']+'  |  REV R4  |  单位 mm',10)
    line(c,30,H-87,W-30,H-87,TEAL,1.1)
    scale=PT_PER_MM;cx=252;cy=303
    R=d['outer_diameter_mm']/2*scale;r=d['centre_hole_diameter_mm']/2*scale
    def circ(x,y,r,color=BLUE,width=.9,dash=None):
        c.setStrokeColorRGB(*color);c.setLineWidth(width);c.setDash(dash or []);c.circle(x,y,r,stroke=1,fill=0);c.setDash([])
    circ(cx,cy,R);circ(cx,cy,r)
    circ(cx,cy,d['pcd_mm']/2*scale,GREY,.55,[5,3])
    line(c,cx-R-17,cy,cx+R+17,cy,GREY,.4,[8,3,2,3]);line(c,cx,cy-R-17,cx,cy+R+17,GREY,.4,[8,3,2,3])
    text(c,cx+R+18,cy-3,'+X',8);text(c,cx+4,cy+R+12,'+Y',8)
    for i,p in enumerate(d['holes'],1):
        x,y=p['xy_mm'];circ(cx+x*scale,cy+y*scale,d['bolt_hole_diameter_mm']/2*scale)
        ang=math.atan2(y,x);label_r=d['pcd_mm']/2*scale+12
        lx,ly=cx+label_r*math.cos(ang),cy+label_r*math.sin(ang)
        text(c,lx-3,ly-3,str(i),7.5,color=TEAL)
    text(c,30,500,'俯视 +Z → 原点 / 正面观察，+X 向右、+Y 向上',8.7)
    # Horizontal outer diameter dimension below the whole view.
    horizontal_dim(c,cx-R,cx+R,cy-R-26,cy,'Ø '+f"{d['outer_diameter_mm']:.1f}")
    label='中心贯通孔  Ø '+f"{d['centre_hole_diameter_mm']:.1f}"
    text(c,cx-pdfmetrics.stringWidth(label,'CJK',9)/2,cy+7,label,9)
    label='凸台避让 +0.6（直径）'
    text(c,cx-pdfmetrics.stringWidth(label,'CJK',7.5)/2,cy-10,label,7.5,color=GREY)
    text(c,30,111,f"孔阵：{len(d['holes'])} × Ø {d['bolt_hole_diameter_mm']:.1f} THRU / PCD Ø {d['pcd_mm']:.1f}",10)
    text(c,30,96,'孔号仅在图纸中；实体未打孔号。旋转整片找正，禁止镜像切片。',8)
    # Side section: simple profile including centre opening, consistent 4 mm.
    sx,sy=345,75;side_w=104;side_h=10
    line(c,sx,sy,sx+side_w,sy);line(c,sx,sy+side_h,sx+side_w,sy+side_h)
    line(c,sx,sy,sx,sy+side_h);line(c,sx+side_w,sy,sx+side_w,sy+side_h)
    line(c,sx+side_w+11,sy,sx+side_w+11,sy+side_h)
    arrow(c,sx+side_w+11,sy,0,1,3);arrow(c,sx+side_w+11,sy+side_h,0,-1,3)
    text(c,sx+side_w+18,sy+2,'4.0',8);text(c,sx,sy-14,'侧视示意 / 平面贴打印床，+Z 向上',7.5)
    # Right hand coordinate table.
    tx=512;ty=H-118;tw=W-30-tx
    text(c,tx,ty+9,'孔中心坐标（相对于样片中心）',10)
    columns=[tx,tx+31,tx+105,tx+177]
    line(c,tx,ty-3,tx+tw,ty-3,TEAL,.8)
    for x,label in zip(columns,['孔号','X / mm','Y / mm','角度 / °']):text(c,x+3,ty-16,label,8.4)
    y=ty-34
    for i,p in enumerate(d['holes'],1):
        if i%2:
            c.setFillColorRGB(.95,.97,.98);c.rect(tx,y-4,tw,15,stroke=0,fill=1)
        vals=[str(i),f"{p['xy_mm'][0]:+.4f}",f"{p['xy_mm'][1]:+.4f}",f"{p['angle_deg']:.5f}"]
        for x,val in zip(columns,vals):text(c,x+3,y,val,8,font='Helvetica')
        y-=16
    y=min(y-6,192)
    text(c,tx,y,'试装与检验建议',10,color=TEAL);y-=17
    notes=[
      '材料：PLA 或 PETG；厚度 4.0；打印层高建议 0.20。',
      '打印方向：XY 平面放床面；不做 XY 或整体缩放。',
      '建议 4 道壁，100% 填充；孔尺寸先用校准样件检查。',
      '尺寸建议：外径/厚度 ±0.20；孔径 +0.20/0 mm。',
      '孔中心位置建议 ±0.15 mm，仅用于打印试装评估。',
      '不指定 ISO 配合，不替代金属连接件制造公差。',
      '不选螺钉长度；原关节有螺纹后缩，先核对可达性。',
      '不装机带电、不测试夹持力、不以本件承担关节载荷。',
    ]
    for s in notes:text(c,tx,y,s,7.5);y-=14
    line(c,30,44,W-30,44,GREY,.7)
    text(c,30,29,'比例：主视图 1:1；侧视示意不按比例。尺寸优先，PDF 打印选择实际大小。',7.5)
    text(c,W-176,29,f'R4  |  2026-09-27  |  {page_number}/4',8,font='Helvetica')
    c.showPage()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    root=Path(__file__).resolve().parents[1]
    parser.add_argument('--source',type=Path,default=root/'docs/engineering/sources/rh-interface-extraction.json')
    parser.add_argument('--output',type=Path,default=root/'engineering/generated/interface-coupons')
    parser.add_argument('--font',type=Path,required=True,help='TrueType font with Chinese glyphs, e.g. Arial Unicode.ttf')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    pdfmetrics.registerFont(TTFont('CJK',str(args.font)))
    source=json.loads(args.source.read_text());lookup={m['id']:m for m in source['models']}
    entries=[];parts=[]
    for name in MODELS:
        data=coupon(lookup[name]);checks=export_and_check(data,args.output)
        record={k:v for k,v in data.items() if k!='shape'};record['verification']=checks
        entries.append(record);parts.append(data)
    (args.output/'PDF').mkdir(exist_ok=True)
    pdf=args.output/'PDF'/'ODR-interface-coupons-R4.pdf'
    c=canvas.Canvas(str(pdf),pagesize=landscape(A4),pageCompression=1)
    c.setTitle('Odradek R4 output-interface fit coupons — NOT LOAD BEARING')
    c.setAuthor('Auromix contributors')
    for i,d in enumerate(parts,1):page(c,d,i)
    c.save()
    result={'status':'geometry/export checks passed; unpowered physical fit check not yet performed',
       'input_extraction_sha256':sha(args.source),'units':'mm','source_spdx':'PolyForm-Noncommercial-1.0.0',
       'manufacturing_scope':'3D printed, non-load-bearing fit coupons only',
       'parts':entries,'pdf':str(pdf.relative_to(args.output)),'pdf_sha256':sha(pdf)}
    (args.output/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'parts':len(entries),'step_stl_dxf':'PASS','pdf':str(pdf),'status':result['status']},indent=2))


if __name__=='__main__':main()
