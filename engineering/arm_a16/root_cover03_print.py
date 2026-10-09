# SPDX-License-Identifier: CC-BY-NC-4.0
"""Separate supported-fit addon kit; never silently replace the issued model."""
import csv,json,zipfile,numpy as np,cadquery as cq,trimesh
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.lib.units import mm
import common as c

O=c.OUT/'root-cover03'

def main():
    mf=O/'manifest.json';d=json.loads(mf.read_text());assert d['layout']==c.L and d['scoped_clear'] and d['tool_access']['scoped_clear']
    for path,digest in d['source_sha256'].items():assert c.sha(c.ROOT/path)==digest
    P=O/'print-bed';P.mkdir(exist_ok=True);bed=[];sources={str(mf.relative_to(c.ROOT)):c.sha(mf)}
    pdf=canvas.Canvas(str(O/'A16-root-cover03-fit.pdf'),pagesize=landscape(A3))
    def text(x,y,s,size=9):pdf.setFont('Helvetica',size);pdf.drawString(x*mm,y*mm,s)
    for p in d['parts']:
        if p['role']=='hardware':continue
        source=O/'step'/(p['id']+'.step');sources[str(source.relative_to(c.ROOT))]=c.sha(source)
        stl=O/'stl'/(p['id']+'.stl');m=trimesh.load(stl,force='mesh');original=m.vertices.copy()
        t=-m.bounds[0];t[:2]=-(m.bounds[0,:2]+m.bounds[1,:2])/2;m.apply_translation(t)
        target=P/stl.name;m.export(target);back=trimesh.load(target,force='mesh')
        assert back.is_watertight and back.is_winding_consistent and len(back.split())==1 and max(back.extents)<250
        assert abs(back.bounds[0,2])<1e-5 and np.max(abs(m.vertices-t-original))<1e-7
        bed.append(dict(id=p['id'],source_sha256=c.sha(stl),print_sha256=c.sha(target),translation_mm=t.tolist(),rotation=np.eye(3).tolist(),size_mm=back.extents.tolist(),orientation='Holder flat; each cowl upright with external brim, internal supports under tabs. Supports and slicing not qualified.'))
        s=cq.importers.importStep(str(source)).val();edges=[]
        for e in s.Edges():edges.append(np.array([e.positionAt(float(q)).toTuple() for q in np.linspace(0,1,2 if e.geomType()=='LINE' else 36)]))
        pdf.setLineWidth(.15*mm);pdf.rect(10*mm,10*mm,400*mm,277*mm);text(16,276,p['id'],15)
        text(16,264,'A16 root-cover addon | mm | supported, unpowered, unloaded FIT ONLY',10)
        bb=s.BoundingBox();minimum=np.array([bb.xmin,bb.ymin,bb.zmin]);maximum=np.array([bb.xmax,bb.ymax,bb.zmax])
        for k,(label,axes) in enumerate([('XY',(0,1)),('XZ',(0,2)),('YZ',(1,2))]):
            lo=minimum[list(axes)];hi=maximum[list(axes)];span=hi-lo;scale=min(112/max(span[0],1),134/max(span[1],1),1)
            xy=np.array([18+131*k,108]);text(xy[0],248,label+' all edges; hidden included',8)
            for e in edges:
                a=(e[:,axes]-lo)*scale+xy;path=pdf.beginPath();path.moveTo(*(a[0]*mm))
                for v in a[1:]:path.lineTo(*(v*mm))
                pdf.drawPath(path)
            text(xy[0],99,f'Overall {span[0]:.3f} x{span[1]:.3f}; scale{scale:.3f}',8)
        text(16,84,'4xD3.5 atR62;20/160/200/340deg. X=+/-58.2609,Y=+/-21.2052; source CAD is authoritative.')
        text(16,74,'R102 plateZ-2.5..3.5; tabsZ4..7,3thick; washer fills0.5 gap. Two tabs per half, straight8-wide strips.')
        text(16,64,'4xM3x16 +8xDIN125 OD7/ID3.2/H0.5 washers +4xM3 nuts AF5.5/H2.4. No plastic tapped threads.')
        text(16,54,'Old R102 and two C02 root skins are replaced; do not stack/install duplicate source parts.')
        text(16,44,'Cowl bottomJ1Z-89.8 /worldZ75.2; B06 neck topZ74. Nominal vertical service seam1.2mm.')
        text(16,38,'Nominal trial linear +/-0.2 after coupons. Motor/base mounts and wire slots retain current source dimensions.')
        text(16,27,'New screw grip9.5+head washer0.5; nutZ-4.9..-2.5, screw tipZ-8.5. Retention/load/thermal not qualified.')
        text(16,17,'STEP and STL supplied for fit. Inspect internal supports, washer seats, actual tools and manual removal.',8)
        pdf.showPage()
    pdf.save();assert len(bed)==3
    with (O/'hardware-BOM.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['specification','quantity']);w.writerows(d['hardware_BOM'].items())
    note='''# 根部护罩四螺钉试装模块

只用于有支撑、断电、空载试配。三件打印件：新R102替换板及两半根部罩；16个名义钢件全部采购，不打印。

**替换关系：** A16-C03-root-front-holder替代旧A16-R102-J1-front-holder；C03两半罩替代C02两半J1罩。当前整臂Blender/viewer仍保留7aa310d的C02主版本，未静默把此模块当成全臂安装完成。

先装R102下方四个M3螺母及板上四个0.5垫圈，再放罩内直耳、头下垫圈和M3×16；每半罩两颗。螺钉孔X±58.2609位于S101底脚X±55之外，避免脚板挡住上方工具。reference支撑维护姿态中另检查D3.2的普通L形六角匙空包络（短竖段19.9 mm、横向向外30 mm），避开R103上盘和S101。它不是实选工具、插入路径或套筒啮合验证，实际六角匙形状、拧紧过程仍需首件核查。需要先拆罩才能接近内部连接；不直接套用金属连接拧紧扭矩。

plate_slots保持原R102的6×14外围走线槽；两条现有空包络已纳入本模块的CAD检查。只证明J1=0的三个静态姿态，不证明真实线束或转动服务环。

罩件底端裁至J1局部Z−89.8，即桌面Z75.2，与B06颈台顶Z74形成1.2 mm名义竖向接缝。底座全部216个产品件的同源清单包围盒最高Z74.000001，因此本根部模块在竖向范围上分离；这是名义包围盒证明，尚未包含实物公差或完整壳体BREP审查。

print-bed/为毫米贴床STL；板平放，罩直立加外侧brim，内部直耳下需要支撑。STEP保留J1.fixed原装配坐标，不得用贴床坐标修改电机基准。图纸为3页名义试配图，不是金属承力件生产图。必须去支撑、去毛刺、核实螺母/垫圈落座与全部螺钉。

manifest.json提供替换关系、源哈希、三个姿态及检查范围。没有任何碰撞豁免；未核验整套底座外壳、真实插头、连续路径、保持强度或温升。全臂3 kg生产资格仍未获得。
'''
    (O/'README.md').write_text(note)
    audit=dict(layout=c.L,source_sha256=sources,print_parts=bed,hardware_count=16,scope='Closed mesh,250mm bed envelope, proper translation, nominal BREP orthographics and purchased BOM. Slicer and physical assembly unqualified.',production_release=False)
    (O/'print-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    files=[mf,O/'print-audit.json',O/'README.md',O/'hardware-BOM.csv',O/'A16-root-cover03-fit.pdf']+list(P.glob('*.stl'))+list((O/'step').glob('*.step'))
    target=O/'A16-root-cover03-supported-fit.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(O))
        z.writestr('SHA256SUMS.txt',''.join(c.sha(p)+'  '+str(p.relative_to(O))+'\n' for p in files))
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        import hashlib
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            digest,name=line.split('  ',1);assert hashlib.sha256(z.read(name)).hexdigest()==digest
    print('ROOT_COVER03_PRINT',len(bed),'closed printable shapes,16 purchased parts',flush=True)

if __name__=='__main__':main()
