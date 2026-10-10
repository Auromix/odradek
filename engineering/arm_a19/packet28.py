# SPDX-License-Identifier: CC-BY-NC-4.0
"""One current whole-body supported-fit pack, with no failed alternatives."""
from pathlib import Path
import sys,json,csv,shutil
import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/assembly25';PACK=ROOT/'manufacturing/candidates/arm-body-a19-integrated-fit'
sys.path.insert(0,str(HERE));import wrist16 as w
c=w.c
def main():
    path=OUT/'manifest.json';d=json.loads(path.read_text());review=json.loads((OUT/'review20.json').read_text());native=json.loads((OUT/'native-audit26.json').read_text())
    assert review['changed_pair_sampled_clear'] and review['source_sha256'][str(path.relative_to(ROOT))]==c.sha(path)
    assert native['assembly_sha256']==c.sha(path)
    for name,digest in review['source_sha256'].items():assert c.sha(ROOT/name)==digest,name
    PACK.mkdir(parents=True,exist_ok=True)
    for folder in ['print-bed','step-print-parts','step-stock-parts']:(PACK/folder).mkdir(exist_ok=True)
    rows=d['parts'];audits=[];oldpack=ROOT/'manufacturing/candidates/arm-body-a18-unified-fit'
    for p in rows:
        source=ROOT/p['step_path'];assert c.sha(source)==p['step_sha256']
        if p['role'] in ['printed_structure','printed_cover']:
            a=p['print_audit'];stl=ROOT/a['print_stl_path'] if 'print_stl_path' in a else oldpack/'print-bed'/(p['id']+'.stl')
            assert c.sha(stl)==a['print_stl_sha256'];m=trimesh.load(stl,force='mesh',process=True)
            assert m.is_watertight and m.is_winding_consistent and m.volume>0 and max(m.extents)<250 and abs(m.bounds[0,2])<1e-4,p['id']
            edges=m.edges_unique;graph=coo_matrix((np.ones(len(edges)),(edges[:,0],edges[:,1])),shape=(len(m.vertices),len(m.vertices)));count=int(connected_components(graph,directed=False,return_labels=False));assert count==1,p['id']
            shutil.copy2(stl,PACK/'print-bed'/stl.name);shutil.copy2(source,PACK/'step-print-parts'/source.name)
            audits.append(dict(a,id=p['id'],size_mm=m.extents.tolist(),connected_components=count))
        elif p['role']=='purchased_structure':shutil.copy2(source,PACK/'step-stock-parts'/source.name)
    for name in ['manifest.json','review20.json','native-audit26.json','assembly-ledger.csv','load27.json','J2-ideal-passive-limit27.csv','tool31.json','root32.json']:
        shutil.copy2(OUT/name,PACK/name)
    shutil.copy2(HERE/'harness29.md',PACK/'harness-current.md')
    public=ROOT/native['public_native_path'];assert c.sha(public)==native['public_native_sha256'];shutil.copy2(public,PACK/public.name)
    for name,digest in native['images'].items():
        source=OUT/(name+'.png');assert c.sha(source)==digest;shutil.copy2(source,PACK/source.name)
    (PACK/'print-audit.json').write_text(json.dumps(audits,indent=2)+'\n')
    with (PACK/'print-list.csv').open('w') as fp:
        writer=csv.writer(fp);writer.writerow(['id','size_x_mm','size_y_mm','size_z_mm','step_sha256','print_stl_sha256'])
        for a in audits:writer.writerow([a['id'],*a['size_mm'],a['source_step_sha256'],a['print_stl_sha256']])
    hardware=[]
    core=json.loads((HERE/'build/wrist-core19/manifest.json').read_text());screws={p['id']:p['description'] for p in core['screw_stacks']}
    for p in rows:
        if p['role']!='hardware':continue
        id=p['id'];note=p.get('note','')
        if id in screws:note=screws[id]
        elif id.startswith('A19-H19-') and id.endswith('-washer'):note='M4 flat washer nominalOD9 ID4.4 thickness0.8; verify purchased tolerance'
        elif id.startswith('A19-H21-'):
            note='DIN934 M3 nut AF5.5 thickness2.4' if id.endswith('-nut') else 'DIN125 M3 washer OD7 ID3.2 thickness0.5; spacer uses same washer' if id.endswith(('-washer','-spacer')) else 'DIN7984 M3x16 low headD5.5 H2 AF2; verify purchased dimensions'
        hardware.append(dict(id=id,frame=p['frame'],nominal_description=note,material=p.get('material',''),quantity=1))
    with (PACK/'hardware-individual-ledger.csv').open('w') as fp:
        writer=csv.DictWriter(fp,fieldnames=list(hardware[0]));writer.writeheader();writer.writerows(hardware)
    for name in ['stock-cut-list.csv','stock-drill-table.csv']:
        shutil.copy2(oldpack/name,PACK/name)
    with (PACK/'joint-layout-current.csv').open('w') as fp:
        writer=csv.writer(fp);writer.writerow(['joint','motor_model','mass_kg','offset_x_mm','offset_y_mm','offset_z_mm','axis_x','axis_y','axis_z','minimum_deg','maximum_deg'])
        for j in d['layout']['joints']:writer.writerow([j['id'],j['model'],j['mass_kg'],*j['offset'],*j['axis'],*j['limits_deg']])
    (PACK/'assembly-current.md').write_text('''# A19当前整臂试配装配

本包manifest是当前唯一清单，包含全部当前自有件。不要叠装A18旧J5、旧肩部下罩、旧前臂罩或旧55 mm腕部支架。B06底座继续使用同源交接；双相机端口和触点面板IF09保持原结构，但没有电气放行。

1. 外部支架支撑所有连杆，断开全部供电。按当前stock CSV准备六件采购管／隔套；沿用A18的普通骨架装配顺序，旧件编号以manifest removed_part_ids替换。
2. 根部换12 mm肩部L支架；四个脚板孔与十个电机孔保持原位置。沉孔保留原M4×12夹持厚度及旋入，不加长原螺钉；恢复原罩固定座与新下罩。
3. J5换实际RS03及新固定环、输出L支架。先装8颗M4×14固定螺钉及6颗M4×16输出螺钉，两侧均0.8 mm垫圈、5.2 mm名义旋入。核对厂家孔深和真实有效螺纹；扭矩值未发行。
4. J6安装到75 mm轴距；四个原外罩热熔件与五金整体移至新座。勿沿用55 mm局部坐标。保留J7、支承和IF09原件，检查全套口／板／法兰的装配方向。
5. 前臂上下罩为本包修整件。RS03两片罩采用四个DIN7984低头M3×16、四个M3螺母及八个0.5 mm垫圈（四片用于间隔）；145/165/185/195°固定座采用普通Ø7.4、深1 mm沉孔，保留2 mm底厚，低头螺钉高出座面1.5 mm，不增厚固定座挤占J6空间。名义夹持10.5 mm、头下垫圈0.5 mm、后侧螺纹5 mm，螺母2.4 mm、外露2.6 mm。先装后侧螺母，再装罩和外侧垫圈，工具可达与打印件预紧保持尚需实物核对。
6. 在外部支撑下手动逐轴试动并记录卡滞、间隙和孔位偏差。没有真实动态线束，不接电、不加3 kg工件；不能靠螺钉强拉打印件补偿孔位或变形。

打印件没有实测尺寸、公差、热熔拉脱、切片支持和结构强度结果。金属版须重新设计／验证承力界面与质量输入，不能将打印件材料名替换后直接量产。
''')
    (PACK/'README.md').write_text(f'''# A19同源机身整合试配包

保持340/185 mm轴距与裸法兰3 kg目标。实际RS03用于J5，J5—J6轴距75 mm；12 mm肩部普通L支架与分体曲面护罩同时整合，B06底座几何保持同源不变。

本包{len(audits)}件打印件、6件采购结构件、{len(hardware)}项名义五金均取自同一装配清单；未进入当前候选的失败件不在本目录。每件STL已做拓扑、单连通、落床和尺寸核对。尚未切片或实际打印。公开Blender包含自有件与同源底座，供应商电机几何留在本机私有模型，未经缩放。

整合后新件检查{len(review['checks'])}个有限姿态，未发现大于0.08 mm³相交；只检查变更新件与剩余旧件／实际电机以及新件之间，未重查全部旧件对，也未包含完整底座内件、连续扫掠、公差、工具或动态线束。此结果不能扩大为整个工作空间通过。

裸臂质量估算{d['estimated_bare_mass_kg']:.3f} kg（含0.49 kg余量）；4099个未过滤碰撞的静态样本，J2 {d['sampled_max_abs_Nm'][1]:.3f} Nm、J5 {d['sampled_max_abs_Nm'][4]:.3f} Nm。J2助力与热保持仍未解决，不能据此执行3 kg任务。load27是新质量输入的载荷，root32使用本版载荷及金属根部自重做线性分析；其余臂身仍按塑料试配质量。4→3 mm二次位移细化变化最大0.62%，但没有真实接触、预紧、助力支座和整机金属质量，不能作为生产强度放行。

tool31的18个直线内六角入口在列明的装配阶段无几何相交，仍未验证真实扳手手柄、握持、螺母约束和拧紧扭矩。harness-current列明现有动态同轴／CAN线材为什么不能直接套进预留通道。

当前仅用于外部支撑、断电、无载装配试配。不是金属生产放行版。实际螺纹／预紧、材料与制造公差、散热、断电保持、电气PCB、GMSL链路和寿命测试未放行。
''')
    with (PACK/'README.md').open('a') as fp:
        if (PACK/'drawings/47-current-part-fit-drawings.pdf').exists():
            fp.write('\n[47页当前名义零件工作图](drawings/47-current-part-fit-drawings.pdf)包含41打印件和6采购结构件；当前孔表与STEP同源，各视图标明CAD坐标与比例，不是金属GD&T发行图。\n')
        if (PACK/'calibration-coupons/manifest.json').exists():
            fp.write('\n[7件小型校准夹具](calibration-coupons/README.md)独立存放，验证孔径、管套、薄耳座及实际电机配合面；不是机身替换件，不计入41件打印清单。\n')
    hashes={str(p.relative_to(PACK)):c.sha(p) for p in PACK.rglob('*') if p.is_file() and p.name!='SHA256SUMS.json'}
    (PACK/'SHA256SUMS.json').write_text(json.dumps(hashes,indent=2)+'\n');print('PACK28',len(audits),len(hardware),len(hashes),flush=True)
if __name__=='__main__':main()
