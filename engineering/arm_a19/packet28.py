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
import binding50 as binding
c=w.c
def main():
    path=OUT/'manifest.json';d=json.loads(path.read_text());review=json.loads((OUT/'review20.json').read_text());native=json.loads((OUT/'native-audit26.json').read_text())
    binding.validate()
    assert review['changed_pair_sampled_clear'] and binding.assembly_compatible(review['source_sha256'][str(path.relative_to(ROOT))])
    assert binding.assembly_compatible(native['assembly_sha256'])
    for name,digest in review['source_sha256'].items():binding.require_source_digest(ROOT/name,digest)
    for name in ['load27.json','root32.json','tool31.json']:
        proof=json.loads((OUT/name).read_text());assert binding.assembly_compatible(proof['source_assembly_sha256']),name
        if name=='root32.json':assert proof['source_load27_sha256']==c.sha(OUT/'load27.json')
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
    for name,flag,checker in [('tools37.json','nominal_staged_all_clear','tools37.py'),('paths38.json','all_sampled_paths_clear','paths38.py')]:
        if (OUT/name).exists():
            proof=json.loads((OUT/name).read_text());assert proof[flag] and binding.assembly_compatible(proof['source_assembly_sha256'])
            assert proof['source_checker_sha256']==c.sha(HERE/checker)
            if name=='paths38.json':assert proof['source_tools37_sha256']==c.sha(OUT/'tools37.json')
            shutil.copy2(OUT/name,PACK/name)
    if (OUT/'full-review35.json').exists():
        proof=json.loads((OUT/'full-review35.json').read_text());assert proof['sampled_all_arm_pairs_clear']
        assert binding.assembly_compatible(proof['source_sha256'][str(path.relative_to(ROOT))]) and proof['source_checker_sha256']==c.sha(HERE/proof.get('source_checker_file','full_review35.py'))
        for source,digest in proof['source_sha256'].items():binding.require_source_digest(ROOT/source,digest)
        shutil.copy2(OUT/'full-review35.json',PACK/'full-review35.json')
    if (OUT/'paths38.json').exists():shutil.copy2(HERE/'assembly38.md',PACK/'assembly-stages38.md')
    shutil.copy2(HERE/'harness29.md',PACK/'harness-current.md')
    if (OUT/'review44.json').exists():
        proof=json.loads((OUT/'review44.json').read_text())
        assert not proof['hits']
        shutil.copy2(OUT/'review44.json',PACK/'review44.json')
    if (OUT/'wire41.json').exists():
        proof=json.loads((OUT/'wire41.json').read_text());assert binding.assembly_compatible(proof['source_assembly_sha256'])
        shutil.copy2(OUT/'wire41.json',PACK/'wire41.json');shutil.copy2(HERE/'wire41.md',PACK/'wire41.md')
    if (OUT/'bearing42.json').exists():
        proof=json.loads((OUT/'bearing42.json').read_text());assert binding.assembly_compatible(proof['source_assembly_sha256'])
        shutil.copy2(OUT/'bearing42.json',PACK/'bearing42.json')
        shutil.copy2(HERE/'bearing42.md',PACK/'bearing42.md')
    if binding.BRIDGE.exists():
        shutil.copy2(binding.BRIDGE,PACK/'catalogue-binding50.json');shutil.copy2(binding.BASE,PACK/'evidence-input-assembly.json')
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
2. 先紧固J1输出螺钉，再装12 mm肩部L支架；四个脚板孔与十个电机孔保持原位置。沉孔保留原M4×12夹持厚度及旋入，不加长原螺钉。肩部外罩及其五金最后安装；完整先后关系见assembly-stages38.md。
3. J5换实际RS03及新固定环、输出L支架。先装8颗M4×14固定螺钉及6颗M4×16输出螺钉，两侧均0.8 mm垫圈、5.2 mm名义旋入。核对厂家孔深和真实有效螺纹；扭矩值未发行。
4. J6安装到75 mm轴距；四个原外罩热熔件与五金整体移至新座。勿沿用55 mm局部坐标。保留J7、支承和IF09原件，检查全套口／板／法兰的装配方向。
5. 前臂上下罩为本包修整件。RS03两片罩采用四个DIN7984低头M3×16、四个M3螺母及八个0.5 mm垫圈（四片用于间隔）；145/165/185/195°固定座采用普通Ø7.4、深1 mm沉孔，保留2 mm底厚，低头螺钉高出座面1.5 mm，不增厚固定座挤占J6空间。名义夹持10.5 mm、头下垫圈0.5 mm、后侧螺纹5 mm，螺母2.4 mm、外露2.6 mm。先装后侧螺母，再装罩和外侧垫圈，工具可达与打印件预紧保持尚需实物核对。
6. J4罩使用ISO7380-1 M3×16圆头内六角（头D5.7／高1.65／AF2），J4管夹四颗M4×35各增加一片0.8 mm头下垫圈，连同原片共1.6 mm；后侧原片及螺母不动，名义螺母后外露1.4 mm。勿换回原高头罩螺钉或省略新增垫圈。
7. 在外部支撑下手动逐轴试动并记录卡滞、间隙和孔位偏差。没有真实动态线束，不接电、不加3 kg工件；不能靠螺钉强拉打印件补偿孔位或变形。

打印件没有实测尺寸、公差、热熔拉脱、切片支持和结构强度结果。金属版须重新设计／验证承力界面与质量输入，不能将打印件材料名替换后直接量产。
''')
    (PACK/'README.md').write_text(f'''# A19同源机身整合试配包

保持340/185 mm轴距与裸法兰3 kg目标。实际RS03用于J5，J5—J6轴距75 mm；12 mm肩部普通L支架与分体曲面护罩同时整合，B06底座几何保持同源不变。

本包{len(audits)}件打印件、6件采购结构件、{len(hardware)}项名义五金均取自同一装配清单；未进入当前候选的失败件不在本目录。每件STL已做拓扑、单连通、落床和尺寸核对。切片参考条件与结果单独记录于slice45，尚未实际打印。公开Blender包含自有件与同源底座，供应商电机几何留在本机私有模型，未经缩放。

整合后新件检查{len(review['checks'])}个有限姿态，未发现大于0.08 mm³相交；该范围只含变更新件与剩余旧件／实际电机以及新件之间。旧件对另外按下述21姿态全件证据核对，仍没有完整底座内件、连续扫掠、公差或动态线束。此结果不能扩大为整个工作空间通过。

裸臂质量估算{d['estimated_bare_mass_kg']:.3f} kg（含0.49 kg余量）；4099个未过滤碰撞的静态样本，J2 {d['sampled_max_abs_Nm'][1]:.3f} Nm、J5 {d['sampled_max_abs_Nm'][4]:.3f} Nm。J2助力与热保持仍未解决，不能据此执行3 kg任务。load27是新质量输入的载荷，root32使用本版载荷及金属根部自重做线性分析；其余臂身仍按塑料试配质量。4→3 mm二次位移细化变化最大0.62%，但没有真实接触、预紧、助力支座和整机金属质量，不能作为生产强度放行。

tool31的18个直线内六角入口在列明的装配阶段无几何相交，仍未验证真实扳手手柄、握持、螺母约束和拧紧扭矩。harness-current列明现有动态同轴／CAN线材为什么不能直接套进预留通道。

当前仅用于外部支撑、断电、无载装配试配。不是金属生产放行版。实际螺纹／预紧、材料与制造公差、散热、断电保持、电气PCB、GMSL链路和寿命测试未放行。
''')
    with (PACK/'README.md').open('a') as fp:
        if (PACK/'tools37.json').exists():
            fp.write('\n[常规结构装配顺序38](assembly-stages38.md)说明J1／J3紧固后装骨架、J7轴承从两端预装及接口仓后装。109个电机螺钉名义工具轴，以及五条局部装入／三条台面预装路径在报告列出的有限采样无相交；不含真实工具手柄、连续装入、公差、预紧或带线束装配。\n')
        if (PACK/'full-review35.json').exists():
            proof=json.loads((PACK/'full-review35.json').read_text())
            fp.write(f'\n追加整臂全零件证据35／44：{len(rows)}项自有件和14个实际电机分区，{len(proof["checks"])}个有限姿态覆盖全部零件对，含旧件之间。原全件扫描发现肘部紧固件干涉，现用标准圆头螺钉与普通垫圈修正；仅几何／坐标／配合元数据一致的未改零件对继承原证据，12项新五金对所有当前零件重新计算。详细继承、失败原对及复查结果见review44，不能描述为对所有当前件重新做了一次全空间扫描。未发现大于0.08 mm³非许可相交，仅显式螺纹区／热熔配合区扣除；仍不包含底座内件、连续扫掠、公差、真实线束或实物资格。\n')
        if (PACK/'j7-bearing-calibration/manifest.json').exists():
            fp.write('\n[J7六件轴承配合小样](j7-bearing-calibration/README.md)核对实际6807与打印座孔／轴颈；独立于41件机身打印清单，没有实际打印结果。\n')
        if (PACK/'wire41.md').exists():
            fp.write('\n[细同轴候选与电气预算41](wire41.md)记录1.8 mm、反复弯曲R18的厂家候选及GMSL损耗／PoC算式。没有循环寿命、扭转、实际组件测量或采购放行。\n')
        if (PACK/'slice45.json').exists():
            proof=json.loads((PACK/'slice45.json').read_text());assert binding.assembly_compatible(proof['source_assembly_sha256']) and proof['all_slices_completed']
            fp.write('\n[参考切片45](slice45.md)以OrcaSlicer2.4.2／Prusa MK4 0.4喷嘴／0.2层高／PETG逐件检查41机身件与13小样。54件均生成非空模型挤出路径；支持是否可拆、粘附、尺寸和强度仍无实物结果，不发行给未知打印机的G-code。\n')
        if binding.BRIDGE.exists():
            fp.write('\n目录直径订正50：J5的旧显示元数据57 mm改为RS03名义106 mm，实际1:1电机STEP始终正确。轴位、质量、所有零件与STEP哈希均完全相同；报告保留订正前的原输入哈希，catalogue-binding50与evidence-input-assembly记录唯一字段差异。没有把旧计算／渲染改写为重新执行的结果。\n')
        if (PACK/'drawings/47-current-part-fit-drawings.pdf').exists():
            fp.write('\n[47页当前名义零件工作图](drawings/47-current-part-fit-drawings.pdf)包含41打印件和6采购结构件；当前孔表与STEP同源，各视图标明CAD坐标与比例，不是金属GD&T发行图。\n')
        if (PACK/'calibration-coupons/manifest.json').exists():
            fp.write('\n[7件小型校准夹具](calibration-coupons/README.md)独立存放，验证孔径、管套、薄耳座及实际电机配合面；不是机身替换件，不计入41件打印清单。\n')
        if (PACK/'kinematics51.md').exists():
            fp.write('\n[坐标、运动与重力关系51](kinematics51.md)及67姿态独立校验明确J2零位、J5／6／7轴向和mm／rad换算。[试配执行记录52](trial-fit52.md)给出先小样再模块的装配流程，trial-measurements52.csv记录47件实测；当前均没有实际打印结果。\n')
    hashes={str(p.relative_to(PACK)):c.sha(p) for p in PACK.rglob('*') if p.is_file() and p!=PACK/'SHA256SUMS.json'}
    (PACK/'SHA256SUMS.json').write_text(json.dumps(hashes,indent=2)+'\n');print('PACK28',len(audits),len(hardware),len(hashes),flush=True)
if __name__=='__main__':main()
