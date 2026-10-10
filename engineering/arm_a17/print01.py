# SPDX-License-Identifier: CC-BY-NC-4.0
"""Separate 18-cover replacement fit pack; never issue failed geometry."""
from pathlib import Path
import sys,json,csv,zipfile,shutil,hashlib
import numpy as np,cadquery as cq,trimesh
from scipy.spatial.transform import Rotation
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.lib.units import mm
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'engineering/arm_a16'))
import common as c
from vendor import interfaces
OUT=HERE/'build/style01';PACK=ROOT/'manufacturing/candidates/arm-body-a17-manta'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    d=json.loads((OUT/'manifest.json').read_text());review=json.loads((OUT/'review.json').read_text())
    assert review['sampled_clear'] and review['table_plane_sampled_clear'],'Failed geometry must not be issued'
    for f,h in review['source_sha256'].items():assert sha(ROOT/f)==h
    for name in ['native-audit.json','physics.json']:
        audit=json.loads((OUT/name).read_text())
        assert audit['manifest_sha256']==sha(OUT/'manifest.json'),(name,'stale manifest')
    native=json.loads((OUT/'native-audit.json').read_text())
    for name,h in native['images'].items():assert sha(OUT/(name+'.png'))==h
    PACK.mkdir(parents=True,exist_ok=True)
    for name in ['step','print-bed']:(PACK/name).mkdir(exist_ok=True)
    pdf=canvas.Canvas(str(PACK/'18-cover-fit-drawings.pdf'),pagesize=landscape(A3));bed=[]
    I={x['joint']:x for x in interfaces()}
    def txt(x,y,t,z=9):pdf.setFont('Helvetica',z);pdf.drawString(x*mm,y*mm,t)
    for p in d['parts']:
        file=OUT/'step'/(p['id']+'.step');shape=cq.importers.importStep(str(file)).val()
        assert shape.isValid() and len(shape.Solids())==1
        shutil.copy2(file,PACK/'step'/file.name)
        mesh=trimesh.load(OUT/'stl'/(p['id']+'.stl'),force='mesh')
        edges=mesh.face_adjacency
        graph=coo_matrix((np.ones(len(edges)),(edges[:,0],edges[:,1])),shape=(len(mesh.faces),len(mesh.faces)))
        assert connected_components(graph,directed=False,return_labels=False)==1
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
        joint=next((j for j in I if '-'+j+'-' in p['id']),None)
        sign=1 if p['id'].endswith(('-a','-dorsal')) else -1
        normal=np.array(I[joint]['v'] if joint else [0,0,1],float)*sign
        if '-root-' in p['id']:normal=np.array([0,sign,0],float)
        rotation=Rotation.align_vectors([[0,0,1]],[normal])[0].as_matrix();assert abs(np.linalg.det(rotation)-1)<1e-9
        old=mesh.vertices.copy();mesh.vertices=old@rotation.T;shift=-mesh.bounds[0];mesh.apply_translation(shift)
        assert max(mesh.extents)<250
        target=PACK/'print-bed'/(p['id']+'.stl');mesh.export(target)
        back=trimesh.load(target,force='mesh');assert back.is_watertight and np.max(abs(back.bounds[0]))<1e-4
        error=float(np.max(abs((mesh.vertices-shift)@rotation-old)));assert error<1e-7
        bed.append(dict(id=p['id'],R_bed_from_cad=rotation.tolist(),translation_mm=shift.tolist(),size_mm=back.extents.tolist(),roundtrip_error_mm=error,source_step_sha256=sha(file),print_stl_sha256=sha(target)))
        bb=shape.BoundingBox();lo=np.array([bb.xmin,bb.ymin,bb.zmin]);hi=np.array([bb.xmax,bb.ymax,bb.zmax])
        curves=[np.array([e.positionAt(float(q)).toTuple() for q in np.linspace(0,1,2 if e.geomType()=='LINE' else 60)]) for e in shape.Edges()]
        pdf.setLineWidth(.15*mm);pdf.rect(10*mm,10*mm,400*mm,277*mm)
        txt(16,276,p['id'],15);txt(16,263,'mm | REPLACEMENT FIT DRAWING | supported, unpowered, unloaded',10)
        txt(16,253,'STEP local frame: '+p['frame']+'; orthographic coordinates use this frame.',9)
        for k,(label,axes) in enumerate([('XY',(0,1)),('XZ',(0,2)),('YZ',(1,2))]):
            span=(hi-lo)[list(axes)];scale=min(112/max(span[0],1),132/max(span[1],1),1);origin=np.array([18+131*k,104])
            txt(origin[0],247,label+'; all edges, hidden included',8)
            for e in curves:
                points=(e[:,axes]-lo[list(axes)])*scale+origin;path=pdf.beginPath();path.moveTo(*(points[0]*mm))
                for v in points[1:]:path.lineTo(*(v*mm))
                pdf.drawPath(path)
            txt(origin[0],97,f'Overall {span[0]:.3f} x {span[1]:.3f}; scale {scale:.3f}',8)
        txt(16,81,'STEP is complete nominal geometry. Extents are exact BREP bounds, not outline sample extrema.')
        txt(16,71,'C03-C06 fixing axes and standard screws retained; see inherited-mounts.csv and A16 assembly07.')
        txt(16,61,'Do not stack the old cover. Covers are cosmetic parts, not a qualified arm load path.')
        txt(16,51,'Curved section nominal2.6mm; rear cap nominal axial/radial2.6. Global minimum wall not qualified.')
        txt(16,41,'Bed STL uses a proper rigid transform. Check slicer supports, screw seats and actual fit before use.')
        txt(16,31,'Finite samples exclude swept volume, dynamic harness, thermal holding and3kg operation.',8)
        txt(16,21,'Not a metal GD&T drawing or production release.',8);pdf.showPage()
    pdf.save()
    with (PACK/'inherited-mounts.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['module','joint','index','frame','x_mm','y_mm','z_mm','nx','ny','nz'])
        for name in ['cowls04','wrist05','skins06']:
            src=json.loads((c.OUT/name/'manifest.json').read_text())
            for m in src['mounts']:writer.writerow([name,m['joint'],m['k'],m['frame'],*m['p_mm'],*m['n']])
        for angle in [20,160,200,340]:
            a=np.radians(angle);writer.writerow(['root-cover03','J1',angle,'J1.fixed',62*np.cos(a),62*np.sin(a),0,0,0,1])
    for name in ['manifest.json','review.json','native-audit.json','physics.json']:
        shutil.copy2(OUT/name,PACK/name)
    for file in OUT.glob('*.png'):shutil.copy2(file,PACK/file.name)
    note='''# A17 连续甲壳替换试配件

这18件外壳替换A16的18件同位置外壳；不得把两个版本同时安装。其余23件打印结构件、6件库存金属件、494件名义采购件及7个灵足电机仍按A16完整试配包准备。这里是独立的外观候选，尚不是生产版。

STEP为原装配坐标；print-bed为毫米贴床STL，变换见print-audit。截面名义2.6mm，弧形后盖轴向/径向名义2.6mm，不是全局最小壁厚证明。需要切片、支撑、去毛刺、同批材料试片、固定耳和热熔螺母的实物检查。41件整臂并未实装。

保留普通M3固定件、垫圈、鞍座和安装轴。先装结构、确认原厂电机及固定面，再装罩；结构/工具拆装仍按A16 assembly07和first-sample07。罩上的线缆开口是服务空间，完整动态线束并未安装；不得假定电机中空或J7可无限旋转。

review只证明指定26个有限姿态的精确几何检查，详见范围和继承的旧件SHA。外观、有限样本和闭合网格不证明3kg负载、实际工具可达、热、线束及金属强度。IF08触点+双相机端口仍是独立提案，未装进此模型。

18-cover-fit-drawings为名义试配投影，全部边包括隐藏边。完整形状依STEP，安装轴依inherited-mounts和原模块说明；生产公差、金属GD&T和实物验收均未发行。

physics记录当前质量与静态筛选。肩部原始重力需求仍超过电机零速参考；本包不准许无支撑通电动作或3kg载荷试验。
'''
    (PACK/'README.md').write_text(note)
    audit=dict(revision=d['revision'],source_manifest_sha256=sha(OUT/'manifest.json'),source_review_sha256=sha(OUT/'review.json'),print_parts=bed,print_count=len(bed),production_release=False,physical_fit_qualified=False)
    (PACK/'print-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    files=[p for p in PACK.rglob('*') if p.is_file() and p.suffix!='.zip' and p.name!='SHA256SUMS.txt']
    (PACK/'SHA256SUMS.txt').write_text(''.join(sha(p)+'  '+str(p.relative_to(PACK))+'\n' for p in sorted(files)))
    with zipfile.ZipFile(PACK/'A17-manta-cover-supported-fit.zip','w',zipfile.ZIP_DEFLATED) as z:
        for f in files+[PACK/'SHA256SUMS.txt']:z.write(f,f.relative_to(PACK))
    with zipfile.ZipFile(PACK/'A17-manta-cover-supported-fit.zip') as z:
        assert z.testzip() is None
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            h,p=line.split('  ',1);assert hashlib.sha256(z.read(p)).hexdigest()==h
    print('A17_PRINT_PACK',len(bed),flush=True)

if __name__=='__main__':main()
