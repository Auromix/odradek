# SPDX-License-Identifier: CC-BY-NC-4.0
"""One current supported-fit body BOM/41-print pack; not a production release."""
from pathlib import Path
import csv,json,sys,shutil,zipfile,math
import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build'
sys.path.insert(0,str(HERE));import feasibility01 as f
from assembly_sources import collect
c=f.c;PACK=ROOT/'manufacturing/candidates/arm-body-a18-unified-fit'

def collect_current():
    rows,sources,operations=collect(last='skins06')
    chain=[ROOT/'engineering/arm_a17/build/style01/manifest.json',OUT/'contacts09/manifest.json',OUT/'front-cowls10/manifest.json']
    for path in chain:
        d=json.loads(path.read_text());assert d['layout']==c.L
        if path.parent.name=='contacts09':assert d['review']['sampled_clear']
        if path.parent.name=='front-cowls10':assert d['changed_pair_sampled_clear']
        sources[str(path.relative_to(ROOT))]=c.sha(path)
        assert all(any(p['id']==id for p in rows) for id in d['replaces_only'])
        rows=[p for p in rows if p['id'] not in d['replaces_only']]
        additions=d['parts']
        if path.parent.name=='contacts09':additions=[p for p in additions if p['role'] not in ['fit_fixture','working_pin_envelope'] and '-tool-' not in p['id']]
        for p in additions:
            entry=dict(p);entry.setdefault('step_path',str((path.parent/'step'/(p['id']+'.step')).relative_to(ROOT)))
            entry['current_source_module']=path.parent.name;rows.append(entry)
        operations.append(dict(source=str(path.relative_to(ROOT)),remove=d['replaces_only'],add=[p['id'] for p in additions]))
    assert len(rows)==556 and len({p['id'] for p in rows})==556
    for p in rows:sources[p['step_path']]=c.sha(ROOT/p['step_path'])
    return rows,sources,operations

def main():
    rows,sources,operations=collect_current();budget=[]
    for p in rows:
        if 'mass_kg' not in p:
            rho={'printed_structure':1.27e-6,'PCB_geometry_only':1.85e-6,'contact_pad_envelope':8.96e-6,'hardware':7.85e-6}[p['role']]
            p['mass_kg']=p['volume_mm3']*rho;p['density_estimate_kg_mm3']=rho
        budget.append(dict(id=p['id'],owner=p['owner'],frame=p['frame'],mass_kg=p['mass_kg'],com_mm=p['com_mm']))
    for owner,mass,com in [(3,.1,[170,0,11]),(4,.08,[92.5,62,11]),(7,.06,[65,0,0]),(2,.25,[45,-80,0])]:budget.append(dict(id=f'allowance-{owner}',owner=owner,frame=f'J{owner}.rotor',mass_kg=mass,com_mm=com))
    q=np.array(list(c.L['poses'].values())+[[j['limits_deg'][0]+f.rs.halton(k,b)*(j['limits_deg'][1]-j['limits_deg'][0]) for j,b in zip(c.L['joints'],[2,3,5,7,11,13,17])] for k in range(1,4097)],float)
    t=f.torque(c.L,q,3,budget);errors=[]
    def potential(v):
        frames=f.frames(c.L,v);bodies=budget+[dict(frame=j['id']+'.fixed',mass_kg=j['mass_kg'],com_mm=j['motor_center']) for j in c.L['joints']]
        return sum(x['mass_kg']*9.81*(frames[x['frame']]@np.r_[x['com_mm'],1])[2]/1000 for x in bodies)+3*9.81*frames['flange'][2,3]/1000
    v=[23,55,35,-85,68,24,42];exact=f.torque(c.L,np.array([v],float),3,budget)[0]
    for i in range(7):
        plus=v.copy();minus=v.copy();h=1e-4;plus[i]+=h;minus[i]-=h
        errors.append(abs((potential(plus)-potential(minus))/(2*math.radians(h))-exact[i]))
    assert max(errors)<1e-6
    count={role:sum(p['role']==role for p in rows) for role in sorted({p['role'] for p in rows})}
    print('CURRENT_ROLES',count,flush=True)
    printed=[p for p in rows if p['role'] in ['printed_cover','printed_structure']];assert len(printed)==41
    for folder in ['step-print-parts','step-stock-parts','print-bed']:(PACK/folder).mkdir(parents=True,exist_ok=True)
    a16=ROOT/'manufacturing/selected/arm-body-a16-fit';a17=ROOT/'manufacturing/candidates/arm-body-a17-manta'
    oldprints={p['id']:p for p in json.loads((a16/'manifest.json').read_text())['print_parts']}
    old17={p['id']:p for p in json.loads((a17/'print-audit.json').read_text())['print_parts']}
    audits=[]
    for p in printed:
        source=ROOT/p['step_path'];shutil.copy2(source,PACK/'step-print-parts'/source.name)
        if p.get('current_source_module') in ['contacts09','front-cowls10']:
            stl=source.parent.parent/'print-bed'/(p['id']+'.stl');rotation=p['print_rotation'];translation=p['print_translation_mm'];h=p.get('print_bed_sha256',p.get('print_stl_sha256'))
        elif p['id'] in old17:
            stl=a17/'print-bed'/(p['id']+'.stl');rotation=old17[p['id']]['R_bed_from_cad'];translation=old17[p['id']]['translation_mm'];h=old17[p['id']]['print_stl_sha256']
            assert c.sha(source)==old17[p['id']]['source_step_sha256']
        else:
            stl=a16/'print-bed'/(p['id']+'.stl');record=oldprints[p['id']]
            rotation=record.get('R_bed_from_object',record.get('R_bed_from_cad',record.get('rotation')))
            assert rotation is not None, p['id']
            translation=record['T_bed_translation_mm'] if 'T_bed_translation_mm' in record else record['translation_mm']
            h=record['bed_stl_sha256'] if 'bed_stl_sha256' in record else record['print_stl_sha256']
        assert c.sha(stl)==h;assert abs(np.linalg.det(rotation)-1)<1e-9
        m=trimesh.load(stl,force='mesh');edges=m.face_adjacency;graph=coo_matrix((np.ones(len(edges)),(edges[:,0],edges[:,1])),shape=(len(m.faces),len(m.faces)))
        components=connected_components(graph,directed=False,return_labels=False)
        assert components==1 and m.is_watertight and m.is_winding_consistent and m.volume>0
        assert max(m.extents)<250 and abs(m.bounds[0,2])<1e-4
        target=PACK/'print-bed'/stl.name;shutil.copy2(stl,target)
        audits.append(dict(id=p['id'],frame=p['frame'],source_step_sha256=c.sha(source),print_stl_sha256=h,bed_rotation=rotation,bed_translation_mm=translation,size_mm=m.extents.tolist(),connected_components=components))
    for p in rows:
        if p['role']=='purchased_structure':shutil.copy2(ROOT/p['step_path'],PACK/'step-stock-parts'/Path(p['step_path']).name)
    physics=dict(estimated_bare_mass_kg=sum(p['mass_kg'] for p in rows)+sum(j['mass_kg'] for j in c.L['joints'])+.49,
      undeveloped_allowance_kg=.49,flange_payload_kg=3,flange_J7_local_mm=[110,0,0],sampled_abs_max_Nm=np.max(abs(t),axis=0).tolist(),
      zero_speed_catalogue_reference_Nm=[f.rs.SPECS[j['model']]['zero_speed_reference_Nm'] for j in c.L['joints']],sample_count=len(q),virtual_work_max_error_Nm=max(errors),
      motor_CG_measured=False,material_densities_measured=False,gas_spring_or_actual_wires_modelled=False,production_release=False)
    from qualification13 import review
    qualification,force_rows=review(rows,budget,q,c.L,sources)
    report=dict(revision='A18-UNIFIED-BODY-FIT12',layout=c.L,base_context=c.base_context(),source_sha256=sources,replacement_chain=operations,parts=rows,
      role_counts=count,print_count=len(printed),print_audit=audits,physics=physics,production_release=False,
      allowance='External support, all power off, no payload; no metal manufacturing qualification, no electrical/GMSL or3kg operating release.',
      collision_scope='26 A17 original finite configurations hash-bound unchanged pairs plus IF09 changes. Four front cowls additionally checked in159 configurations; unchanged pairs in added133 configurations not checked. No continuous sweep, tolerance, wires or actual head.')
    (OUT/'assembly12.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');shutil.copy2(OUT/'assembly12.json',PACK/'manifest.json')
    fields=['id','frame','role','material','mass_kg','step_path']
    with (PACK/'assembly-CAD-ledger.csv').open('w') as fp:
        w=csv.DictWriter(fp,fieldnames=fields);w.writeheader();w.writerows({k:p.get(k,'') for k in fields} for p in rows)
    with (PACK/'print-list.csv').open('w') as fp:
        w=csv.writer(fp);w.writerow(['id','frame','size_x_mm','size_y_mm','size_z_mm','source_step_sha256','print_stl_sha256'])
        for p in audits:w.writerow([p['id'],p['frame'],*p['size_mm'],p['source_step_sha256'],p['print_stl_sha256']])
    current_unchanged=['stock-cut-list.csv','stock-drill-table.csv','joint-axis-table.csv','actuator-candidate-list.csv']
    history=['purchased-hardware-summary.csv','assembly07.md','first-sample07.md','harness-boundary07.md','kinematics07.md','release-gates07.md']
    (PACK/'reference-history').mkdir(exist_ok=True)
    for name in current_unchanged+history:
        destination=PACK/name if name in current_unchanged else PACK/'reference-history'/('inherited-'+name)
        shutil.copy2(a16/name,destination)
        obsolete=PACK/('inherited-'+name)
        if obsolete.exists():obsolete.unlink()
    hardware=list(csv.DictReader((a16/'purchased-hardware-summary.csv').open()))
    assert sum(int(p['quantity']) for p in hardware)==494
    hardware.extend([dict(nominal_description='ISO4762 nominal M2.5x6; head D4.5 h2.5, verify sample',quantity=2),dict(nominal_description='M2.5 nut AF5 thickness2 nominal; verify sample',quantity=2)])
    assert sum(int(p['quantity']) for p in hardware)==count['hardware']
    with (PACK/'purchased-hardware-current.csv').open('w') as fp:
        w=csv.DictWriter(fp,fieldnames=['nominal_description','quantity']);w.writeheader();w.writerows(hardware)
    # Map exact replacement IDs into current instructions; inherited documents
    # remain historical evidence rather than a competing assembly manifest.
    guide=(a16/'assembly07.md').read_text()
    guide=guide.replace('# A16 整臂外罩固定版装配顺序','# A18 当前整臂试配装配顺序')
    guide=guide.replace('以`manufacturing/selected/arm-body-a16-fit/manifest.json`为当前选中装配清单','以本包`manifest.json`及`print-list.csv`为当前试配装配清单')
    for op in operations:
        if 'add' in op and len(op['remove'])==len(op['add']):
            for old,new in zip(op['remove'],op['add']):guide=guide.replace(old,new)
    guide=guide.replace('IF107、301、302、303和原有接口紧固件保留','IF107、301、302和原有接口紧固件保留；旧303替换为A18-IF09-101触点面板')
    guide=guide.replace('`release-gates07.md`','`reference-history/inherited-release-gates07.md`')
    guide+='\n\n## 当前候选附加步骤\n\nJ3/J4采用本包四件A18-C04前罩；J2仍采用A17件。J4盲弧槽与M4螺钉末端须逐项测量，不能装旧前罩或短换螺钉来掩盖干涉。臂侧触点板在Y±14/Z9，用两颗M2.5x6及后侧螺母；工具量规／板孔位Z3，不计入裸臂41件。先装板和螺母，再安装面板两M3；仅在断电支撑下测针压缩和同轴服务空间。完整PCB、接插件固定和动力线束尚未发行。\n'
    (PACK/'assembly-current.md').write_text(guide)
    for name in ['qualification13.json','spring-required-force13.csv']:shutil.copy2(OUT/name,PACK/name)
    shutil.copy2(HERE/'supplier-verification13.md',PACK/'supplier-verification13.md')
    summary='\n'.join(f"- {p['id']}：毛截面面积{p['gross_area_mm2']:.1f} mm²，静重力弯曲／扭转毛截面等效应力{p['gross_von_mises_bending_torsion_only_MPa']:.2f} MPa。" for p in qualification['tube_gross_section_screen'])
    (PACK/'current-static-screen.md').write_text('''# 当前CAD静态筛选13\n\n输入为本包当前556个自有CAD项、7个目录电机质量、0.49kg未完成件余量及3kg法兰中心负载。弹簧额外暂留0.15kg支座质量。171行肩部推力需求表已按IF09／FRONT10更新，取代A17旧质量预算的表11。推力窗口是实测曲线需求，不是已获供应商保证。22.8Nm只用于静态筛选，封闭壳内热条件未验证。\n\n''' +summary+'\n\n管材为20×40×2毛截面；按所有所属运动质量的绝对重力矩叠加筛选。未计孔边应力、管套／螺钉载荷路径、弯曲挠度、材料许用值、动力、横向剪切、局部屈曲或疲劳，不给出通过结论，更不代表完整金属骨架设计。数值销位仍未建成／验证支座，不发布气弹簧加工图。\n')
    shutil.copy2(ROOT/'manufacturing/candidates/arm-a18-contact09/two-part-contact-fit-drawings.pdf',PACK/'IF09-two-part-fit-drawings.pdf')
    native=json.loads((OUT/'front-cowls10/native-audit.json').read_text());assert native['manifest_sha256']==c.sha(OUT/'front-cowls10/manifest.json')
    public=ROOT/native['public_own_native_path'];assert c.sha(public)==native['public_own_native_sha256'];shutil.copy2(public,PACK/public.name)
    shutil.copy2(OUT/'front-cowls10/native-audit.json',PACK/'native-audit.json')
    for name,h in native['images'].items():
        path=OUT/'front-cowls10'/(name+'.png');assert c.sha(path)==h;shutil.copy2(path,PACK/path.name)
    readme=f'''# A18整臂收敛试配包

这是当前完整塑料试配候选，保留340/185 mm长版、七个灵足关节、B06同源底座与法兰中心3 kg目标。不是生产放行版。当前裸臂估算{physics['estimated_bare_mass_kg']:.3f} kg，J2原始静态筛选{physics['sampled_abs_max_Nm'][1]:.3f} Nm，助力、散热与真实载荷尚未放行。

## 当前件与旧件替换

- 41件打印件以本包`print-bed/`为当前来源，`step-print-parts/`是同一清单的名义CAD。不要把旧版同名或同功能壳体叠加安装。
- 其中22件沿用A16、14件沿用A17曲面罩、4件J3/J4前罩采用A18、1件触点面板采用IF09；替换链在manifest逐项列出。J2罩仍是A17原形，不伪装成前遮罩已完成。
- 6件采购金属管／隔套在`step-stock-parts/`及当前切割／钻孔CSV中，不打印。
- 原494个名义五金模型保留，臂侧新增2颗M2.5x6螺钉及2个M2.5螺母。PCB与10个铜焊盘包络在CAD账本中，十焊盘是板上特征，不是十个独立采购件；电气PCB尚未发行；完整498个名义五金见`purchased-hardware-current.csv`。
- 七个电机按原型号采购，原厂模型在本机私有Blender中保持实际比例。公开`A18-ownparts-fit.blend`已移除14个原厂电机外形分件，不含供应商CAD再分发；可按官方源模型和同一轴表重装。

## 试装顺序

先按`assembly-current.md`安装通用骨架、6件金属管和普通五金；再按本包当前41件清单装罩。`reference-history/`为历史证据，旧罩编号须通过manifest替换链映射到当前件，不能混用。IF09面板遵循独立两页图与独立接口试配包：臂侧板安装孔Y±14/Z9，工具板量规Y±14/Z3；工具量规不属于裸臂41件，也不是四瓣头。PCB、触点、相机插头和功率支路未放行，当前不通电。

J3前唇边名义2.6mm；J4前唇边4.7mm，以两条5mm宽前侧盲弧槽让开既有M4螺钉末端，保留2.75mm背部连接层；原厂固定螺钉位采用后侧避让腔，不改原M3外罩固定座和五金长度。肩部两个极限姿态按实际支架做轴向±0.5mm切削避让，这不是全局公差／连续扫掠证明。

41个STL均闭合、绕向一致、正体积、单连通、落床且尺寸小于250mm；新唇边、盲槽、后凸台与孔仍需切片支持和实物校准。文件正确不等于切片或样件已经验证。四件前罩的新件检查为159个有限姿态，其余未改零件在新增133姿态之间未重查；不可把报告扩大为整臂全域通过。

仅允许外部支撑、全部断电、无工件的试配。3 kg运作、金属骨架强度／疲劳、实际螺纹、助力支座与力曲线、线束、相机链路、热与断电保持仍待验证。此包不提供金属GD&T生产图，也不把塑料CAD换密度称作金属设计。
'''
    (PACK/'README.md').write_text(readme)
    files={str(p.relative_to(PACK)):c.sha(p) for p in sorted(PACK.rglob('*')) if p.is_file() and p.name not in ['SHA256SUMS.json','A18-whole-body-supported-fit.zip']}
    (PACK/'SHA256SUMS.json').write_text(json.dumps(files,indent=2)+'\n');archive=PACK/'A18-whole-body-supported-fit.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(PACK.rglob('*')):
            if p.is_file() and p!=archive:z.write(p,str(p.relative_to(PACK)))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        import hashlib
        assert all(hashlib.sha256(z.read(name)).hexdigest()==h for name,h in files.items())
    print('A18_UNIFIED',len(rows),'ownCAD',len(printed),'prints','mass',physics['estimated_bare_mass_kg'],'torques',physics['sampled_abs_max_Nm'],'zip',archive.stat().st_size,flush=True)

if __name__=='__main__':main()
