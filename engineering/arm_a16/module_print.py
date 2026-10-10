# SPDX-License-Identifier: CC-BY-NC-4.0
"""Hash-bound modular supported-fit kit with nominal BREP orthographics."""
import csv,json,sys,zipfile,numpy as np,trimesh,cadquery as cq
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.lib.units import mm
import common as c
from vendor import interfaces

def main(module):
    O=c.OUT/module;mf=O/'manifest.json';d=json.loads(mf.read_text());assert d['layout']==c.L
    rev=json.loads((O/'review.json').read_text()) if (O/'review.json').exists() else d
    assert rev['scoped_clear'] and rev['tool_access']['scoped_clear'],'Do not issue failed geometry'
    sources={str(mf.relative_to(c.ROOT)):c.sha(mf)}
    for path,digest in rev['source_sha256'].items():assert c.sha(c.ROOT/path)==digest
    sources.update(rev['source_sha256']);I={p['joint']:p for p in interfaces()};bed=[];P=O/'print-bed';P.mkdir(exist_ok=True)
    pdf=canvas.Canvas(str(O/'fit-drawings.pdf'),pagesize=landscape(A3))
    def txt(x,y,s,z=9):pdf.setFont('Helvetica',z);pdf.drawString(x*mm,y*mm,s)
    for p in d['parts']:
        if not p['role'].startswith('printed'):continue
        f=O/'step'/(p['id']+'.step');sources[str(f.relative_to(c.ROOT))]=c.sha(f)
        obj=O/'stl'/(p['id']+'.stl');m=trimesh.load(obj,force='mesh');old=m.vertices.copy();R=np.eye(3)
        joint=next((j for j in I if '-'+j+'-' in p['id']),None)
        if joint:R=np.array([I[joint][k] for k in ['u','v','n']],float)
        assert abs(np.linalg.det(R)-1)<1e-9
        v=old@R.T;t=-v.min(axis=0);m.vertices=v+t;target=P/obj.name;m.export(target);back=trimesh.load(target,force='mesh')
        assert back.is_watertight and back.is_winding_consistent and len(back.split())==1
        assert max(back.extents)<250 and max(abs(back.bounds[0]))<1e-4
        error=float(np.max(abs((m.vertices-t)@R-old)));assert error<1e-7
        bed.append(dict(id=p['id'],R_bed_from_cad=R.tolist(),translation_mm=t.tolist(),size_mm=back.extents.tolist(),roundtrip_error_mm=error,source_stl_sha256=c.sha(obj),print_stl_sha256=c.sha(target),orientation='Fixed face/cowl axis upright on broad rear datum; brim and internal ear support required. Inspect overhangs in slicer; not G-code or physical qualification.'))
        shape=cq.importers.importStep(str(f)).val();bb=shape.BoundingBox();lo=np.array([bb.xmin,bb.ymin,bb.zmin]);hi=np.array([bb.xmax,bb.ymax,bb.zmax]);samples=[np.array([e.positionAt(float(q)).toTuple() for q in np.linspace(0,1,2 if e.geomType()=='LINE' else 40)]) for e in shape.Edges()]
        pdf.setLineWidth(.15*mm);pdf.rect(10*mm,10*mm,400*mm,277*mm);txt(16,276,p['id'],15);txt(16,264,'mm | NOMINAL FIT ONLY | supported, unpowered, unloaded | original CAD axes',10)
        for k,(label,axes) in enumerate([('XY',(0,1)),('XZ',(0,2)),('YZ',(1,2))]):
            span=(hi-lo)[list(axes)];scale=min(112/max(span[0],1),132/max(span[1],1),1);origin=np.array([18+131*k,107]);txt(origin[0],247,label+' all edges, hidden included',8)
            for e in samples:
                a=(e[:,axes]-lo[list(axes)])*scale+origin;path=pdf.beginPath();path.moveTo(*(a[0]*mm))
                for v in a[1:]:path.lineTo(*(v*mm))
                pdf.drawPath(path)
            txt(origin[0],99,f'Overall{span[0]:.3f} x{span[1]:.3f}; scale{scale:.3f}',8)
        txt(16,84,'STEP defines complete nominal geometry; native holes retained. mount-table.csv lists added centres/axes.')
        txt(16,74,'RS04:4xD3.5 atR64,45/135/225/315deg; plate8, spacer0.5, ear3, head washer0.5.')
        txt(16,64,'RS04:4xM3x16 per joint,2 per cover half;8xOD7/ID3.2/H0.5 washers and4xAF5.5/H2.4 nuts.')
        txt(16,54,'Replacement parts only: never stack old bracket or old cowl. Base and motor native datums unchanged.')
        txt(16,44,'Trial printed linear +/-0.2 after coupon calibration; inspect washer seating and de-support internal ears.')
        txt(16,34,'Source dimensions, thread engagement and hardware envelopes do not certify plastic retention or metal GD&T.')
        txt(16,24,'Three named static poses and empty straight hex-key space only; motion, actual tools and load not released.',8)
        pdf.showPage()
    pdf.save()
    with (O/'hardware-BOM.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['specification','quantity']);w.writerows(d['hardware_BOM'].items())
    with (O/'mount-table.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['joint','index','frame','x_mm','y_mm','z_mm','nx','ny','nz','radius_mm','angle_deg'])
        for p in d['mounts']:w.writerow([p['joint'],p['k'],p['frame'],*p['p_mm'],*p['n'],p['radius_mm'],p['angle_deg']])
    note='''# 常规护罩模块试配包

仅用于有支撑、断电、空载的尺寸装配。print-bed/为毫米贴床STL；STEP保留原装配坐标。贴床变换可逆，不改变电机基准。需要切片检查、brim和固定耳下方支撑；尚未产生G-code或实物合格记录。

manifest.json的replaces_only明确旧件移除清单。安装新件时不得保留重复的旧支架或罩。原厂安装面、非均匀孔位与B06底座接口不变。每半罩两颗普通M3螺钉，3mm直耳，0.5mm垫圈隔开承板；四个后侧普通螺母在连接关节前预装。每个关节4xM3×16、8个OD7/ID3.2/H0.5垫圈、4个AF5.5/H2.4螺母，不在塑料上直接攻丝。

先装后侧螺母和原厂固定螺钉，检查固定面贴合；再装垫圈、罩、头下垫圈与螺钉。肩交叉罩保留原8.5mm前缘，只在固定耳处向前伸出；J4肘罩保留X275.25分段面，与上臂X274.75之间为0.5mm接缝。没有允许相碰的实体。

通过低位、互动和参考三个静态姿态的本模块/当前骨架/名义采购件/14份原厂实体干涉检查。另检查参考姿态中D3.2×25mm轴向工具空包络；它不代表实际六角匙插入、横柄操作或连续运动合格。须由首件逐颗确认工具可达、螺母/垫圈落座、打印耳根强度、拆罩顺序及手动全过程。

fit-drawings.pdf为名义试配正投影，全边包括隐藏边；外形尺寸取精确BREP包围盒，轮廓曲线采样仅用于画图。完整名义几何以STEP为准，新增孔坐标见mount-table.csv。3kg负载、封闭壳体温升和后续金属骨架尚未放行。
'''
    (O/'README.md').write_text(note)
    audit=dict(layout=c.L,source_sha256=sources,print_parts=bed,print_count=len(bed),scope='Closed single-component meshes,250mm bed, proper rigid transforms, exact BREP dimension spans; slicing and physical fit unqualified',production_release=False)
    (O/'print-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    files=[mf,O/'print-audit.json',O/'README.md',O/'hardware-BOM.csv',O/'mount-table.csv',O/'fit-drawings.pdf']+list(P.glob('*.stl'))+list((O/'step').glob('*.step'))
    if (O/'review.json').exists():files.append(O/'review.json')
    zpath=O/('A16-'+module+'-supported-fit.zip')
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
        for f in files:z.write(f,f.relative_to(O))
        z.writestr('SHA256SUMS.txt',''.join(c.sha(f)+'  '+str(f.relative_to(O))+'\n' for f in files))
    with zipfile.ZipFile(zpath) as z:
        assert z.testzip() is None
        import hashlib
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            digest,name=line.split('  ',1);assert hashlib.sha256(z.read(name)).hexdigest()==digest
    print('MODULE_PRINT',module,len(bed),'closed bed STLs; archive integrity verified',flush=True)

if __name__=='__main__':main(sys.argv[1])
