# SPDX-License-Identifier: CC-BY-NC-4.0
"""One selected, fully replaced body fit kit; never a payload production release."""
import csv,json,shutil,zipfile,hashlib
from collections import Counter
import numpy as np,trimesh,fitz
import common as c
from assembly_sources import collect

O=c.ROOT/'manufacturing/selected/arm-body-a16-fit';O.mkdir(parents=True,exist_ok=True)
HERE=c.HERE

def main():
    rows,sources,operations=collect(last='skins06');context=c.base_context()
    for module in ['root-cover03','cowls04','wrist05','skins06']:
        folder=c.OUT/module;file=folder/'review.json' if (folder/'review.json').exists() else folder/'manifest.json'
        d=json.loads(file.read_text());assert d['layout']==c.L and d['scoped_clear'] and d['tool_access']['scoped_clear'],module
        sources[str(file.relative_to(c.ROOT))]=c.sha(file)
        for path,digest in d['source_sha256'].items():assert c.sha(c.ROOT/path)==digest
    for sub in ['step','print-bed','drawings','records']:(O/sub).mkdir(exist_ok=True)
    print_records={};page_map={};stock_pages=[]
    # Reuse issued transformations and actual per-part drawing pages. Sources
    # remain modular; this selected issue contains no rejected/old duplicate.
    kits=[('root01','A16-ROOT01-fit-drawings.pdf'),('manufacture01','A16-core-fit-drawings.pdf'),('root-cover03','A16-root-cover03-fit.pdf'),('cowls04','fit-drawings.pdf'),('wrist05','fit-drawings.pdf'),('skins06','fit-drawings.pdf')]
    for name,pdfname in kits:
        folder=c.OUT/name
        audit=folder/'print-audit.json'
        if audit.exists():
            D=json.loads(audit.read_text());assert D['layout']==c.L
            for p in D.get('print_parts',[]):print_records[p['id']]=(p,folder)
        if name=='root01':
            transform=folder/'print-bed-transforms.json';sources[str(transform.relative_to(c.ROOT))]=c.sha(transform)
            for p in json.loads(transform.read_text()):print_records[p['id']]=(dict(p,size_mm=p['bed_dimensions_mm'],source_stl_sha256=p['object_stl_sha256']),folder)
        p=folder/pdfname
        if not p.exists():
            if name=='root01':
                p=next(iter(folder.glob('*drawings*.pdf')),None)
            assert p is not None and p.exists(),(name,pdfname)
        sources[str(p.relative_to(c.ROOT))]=c.sha(p)
        doc=fitz.open(p)
        for i,page in enumerate(doc):
            text=page.get_text()
            for line in text.splitlines():
                if line.startswith(('A16-','A13-')):
                    page_map[line.strip()]=(p,i);break
        if name=='root01':
            page_map['A16-R101-base-adapter']=(p,0)
            page_map['A16-R103-J1-output-pedestal']=(p,2)
    selected_prints=[];stock=[];hardware=[]
    selected_ids={p['id'] for p in rows}
    for row in rows:
        source=c.ROOT/row['step_path'];shutil.copyfile(source,O/'step'/source.name)
        if row['role'].startswith('printed'):
            assert row['id'] in print_records,(row['id'],'missing print transformation')
            record,folder=print_records[row['id']];path=folder/'print-bed'/(row['id']+'.stl')
            assert path.exists();m=trimesh.load(path,force='mesh')
            assert m.is_watertight and m.is_winding_consistent and len(m.split())==1 and max(m.extents)<250
            assert abs(m.bounds[0,2])<1e-4
            current=source.parent.parent/'stl'/(row['id']+'.stl')
            expected=record.get('source_stl_sha256') or record.get('source_sha256')
            assert c.sha(current)==expected,(row['id'],'stale bed transform')
            shutil.copyfile(path,O/'print-bed'/path.name)
            selected_prints.append(dict(record,source_module=row['source_module'],print_stl_sha256=c.sha(path)))
        elif row['role']=='purchased_structure':stock.append(row)
        else:hardware.append(row)
    assert len(selected_prints)==41 and len(stock)==6,(len(selected_prints),len(stock))
    for sub in ['step','print-bed']:
        for p in (O/sub).glob('*'):
            if p.stem not in selected_ids:p.unlink()
    joined=fitz.open()
    for p in selected_prints:
        assert p['id'] in page_map,(p['id'],'missing drawing page')
        file,index=page_map[p['id']];doc=fitz.open(file);joined.insert_pdf(doc,from_page=index,to_page=index)
    assert len(joined)==41;joined.save(O/'drawings/41-print-part-fit-drawings.pdf',garbage=4,deflate=True)
    stock_record=json.loads((c.OUT/'stock07.json').read_text());assert stock_record['layout']==c.L
    assert stock_record['stock_piece_count']==6 and stock_record['drawing_page_count']==3
    assert c.sha(c.OUT/'stock07-fit-drawings.pdf')==stock_record['drawing_sha256']
    for p in stock_record['parts']:assert c.sha(c.ROOT/p['source_step_path'])==p['source_step_sha256']
    for name,dest in [('stock07-fit-drawings.pdf','drawings/3-stock-cut-drill-fit-drawings.pdf'),('stock07.json','records/stock07.json'),('stock07-drill-table.csv','stock-drill-table.csv')]:
        file=c.OUT/name;sources[str(file.relative_to(c.ROOT))]=c.sha(file);shutil.copyfile(file,O/dest)
    with (O/'assembly-BOM.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['id','category','quantity','frame','source_module','material','nominal_mass_kg','note'])
        for p in rows:w.writerow([p['id'],p['role'],1,p['frame'],p['source_module'],p['material'],p['mass_kg'],p['note']])
    with (O/'purchased-hardware-summary.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['nominal_description','quantity'])
        w.writerows(sorted(Counter(p['note'] for p in hardware).items()))
    with (O/'stock-cut-list.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['id','material','quantity','source_module','note'])
        for p in stock:w.writerow([p['id'],p['material'],1,p['source_module'],p['note']])
    with (O/'print-list.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['id','source_module','size_x_mm','size_y_mm','size_z_mm','print_stl_sha256'])
        for p in selected_prints:w.writerow([p['id'],p['source_module'],*p['size_mm'],p['print_stl_sha256']])
    vendor_file=c.OUT/'vendor-audit.json';vendor=json.loads(vendor_file.read_text());assert vendor['layout']==c.L
    with (O/'actuator-candidate-list.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['joint','supplier','model','quantity','nominal_mass_kg','native_protocol','source_step_url','source_step_sha256','status'])
        for motor,joint in zip(vendor['motors'],c.L['joints']):
            assert motor['joint']==joint['id'] and motor['model']==joint['model'] and motor['linear_scale']==1
            w.writerow([motor['joint'],'RobStride',motor['model'],1,joint['mass_kg'],'CAN',motor['source_url'],motor['source_sha256'],'FIT CANDIDATE;3kg chain not qualified;confirm supplied revision before purchase'])
    sources[str(vendor_file.relative_to(c.ROOT))]=c.sha(vendor_file)
    for name in ['gravity-modules.json','shoulder02-modules.json','native-modules-audit.json','motion07.json','kinematics07.json','viewer-qa07.json']:
        path=c.OUT/name;assert path.exists(),name
        d=json.loads(path.read_text());assert d['layout']==c.L
        for src in d.get('sources',[]):assert c.sha(c.ROOT/src['path'])==src['sha256']
        sources[str(path.relative_to(c.ROOT))]=c.sha(path);shutil.copyfile(path,O/'records'/path.name)
    gravity=json.loads((c.OUT/'gravity-modules.json').read_text());shoulder=json.loads((c.OUT/'shoulder02-modules.json').read_text())
    assert shoulder['gravity_sha256']==c.sha(c.OUT/'gravity-modules.json')
    native=json.loads((c.OUT/'native-modules-audit.json').read_text())
    assert native['canonical_base_world_geometry_unchanged'] and native['own_part_count']==len(rows)
    for p in native['source_files']:assert c.sha(c.ROOT/p['path'])==p['sha256']
    assert c.sha(c.ROOT/native['native_path'])==native['native_sha256']
    public_path=c.OUT/'public-native07-audit.json';public=json.loads(public_path.read_text())
    assert public['layout']==c.L and public['own_meshes']==len(rows) and public['canonical_base_meshes']==221
    assert public['canonical_world_geometry_unchanged'] and not public['supplier_mesh_data_present']
    assert len(public['removed_supplier_mesh_groups'])==14
    assert public['source_private_native_sha256']==native['native_sha256']
    assert c.sha(c.ROOT/public['public_native_path'])==public['public_native_sha256']
    sources[str(public_path.relative_to(c.ROOT))]=c.sha(public_path)
    shutil.copyfile(public_path,O/'records'/public_path.name)
    motion=json.loads((c.OUT/'motion07.json').read_text());assert motion['sampled_clear'] and motion['table_plane_sampled_clear']
    for src,digest in motion['source_sha256'].items():assert c.sha(c.ROOT/src)==digest
    shutil.copyfile(c.OUT/'kinematics07-joint-table.csv',O/'joint-axis-table.csv')
    sources[str((c.OUT/'kinematics07-joint-table.csv').relative_to(c.ROOT))]=c.sha(c.OUT/'kinematics07-joint-table.csv')
    with (O/'cover-mount-table.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['module','joint','index','frame','axis_point_x_mm','y_mm','z_mm','nx','ny','nz','radius_mm','angle_deg'])
        root=json.loads((c.OUT/'root-cover03/manifest.json').read_text())
        for k,angle in enumerate(root['mount_angles_deg'],1):
            theta=np.radians(angle);w.writerow(['root-cover03','J1',k,'J1.fixed',62*np.cos(theta),62*np.sin(theta),0,0,0,1,62,angle])
        for module in ['cowls04','wrist05','skins06']:
            d=json.loads((c.OUT/module/'manifest.json').read_text())
            for p in d['mounts']:w.writerow([module,p['joint'],p['k'],p['frame'],*p['p_mm'],*p['n'],p['radius_mm'],p['angle_deg']])
    for name in ['assembly07.md','release-gates07.md','harness-boundary07.md','first-sample07.md','kinematics07.md']:
        file=HERE/name;assert file.exists();shutil.copyfile(file,O/name);sources[str(file.relative_to(c.ROOT))]=c.sha(file)
    for name in ['modules-attention.png','modules-idle.png','modules-reference.png']:
        file=c.OUT/name;assert c.sha(file)==native['images'][file.stem];shutil.copyfile(file,O/name)
    for name in ['common.py','assembly_sources.py','assembly07.py','motion07.py','wrist05.py','skins06.py','blender.py','blender_public07.py','gravity.py','shoulder02.py','stock_sheet07.py','kinematics07.py','viewer.py']:
        file=HERE/name;sources[str(file.relative_to(c.ROOT))]=c.sha(file)
    record=dict(revision='A16-SELECTED-ALL-COVER-FIT07',layout=c.L,base_context=context,source_sha256=sources,parts=rows,replacement_chain=operations,
        print_parts=selected_prints,printed_count=len(selected_prints),purchased_structure_count=len(stock),nominal_hardware_count=len(hardware),
        geometric_issue='41 selected printed parts,6 stock metal parts, all ordinary nominal fasteners; every cosmetic half has fixing geometry. Source motor solids remain private and unscaled in local native scene.',
        allowable_activity='External support, unpowered, unloaded print/fit/manual assembly only. No loaded or powered operation.',
        raw3kg_shoulder_Nm=gravity['loaded3kg_sampled_abs_max_Nm'][1],assumed_spring_shoulder_Nm=shoulder['assumed_force_envelope_worst_shoulder_Nm'],
        selected_body_finite_motion_samples=motion['sample_count'],finite_sampled_motion_clear=motion['sampled_clear'],
        thermal_payload_qualified=False,physical_print_qualified=False,whole_motion_qualified=False,connected_harness_qualified=False,metal_manufacturing_qualified=False,production_release=False)
    (O/'manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    (O/'README.md').write_text('''# A16 收敛臂身：完整外罩固定试配资料

此目录只收录当前装配需要的件，不混入废弃候选。共41件塑料打印件、6件采购金属管/隔套和完整名义紧固件。普通法兰、矩形管、分体鞍座、固定耳、螺钉和标准热熔螺母；未添加凸轮、齿轮联动或差动机构。

**只能有支撑、断电、空载试装。尚不是3kg额定或量产放行。** 电机原厂STEP没有公开再分发；本地Blender使用对应未缩放原厂实体和B06同一份底座。source_sha256和replacement_chain追溯每一件，移除旧件后再装新件。

- print-bed/：41件毫米贴床STL，查看print-list.csv后切片；内部支撑、孔径收缩和预紧需小样与首件验证。
- step/：当前自有打印/普通采购包络的原装配坐标实体，含实际固定孔和服务窗口，不含原厂电机几何。
- A16-body-own-parts.blend：完整当前自有臂身和同源B06底座；公开版移除原厂电机实体。本地完整原厂实体装配见work/arm-a16/actual-motors-modules.blend。
- drawings/：41页当前打印件名义尺寸工作图；完整几何以STEP为准，不是金属GD&T放行图。
- drawings/3-stock-cut-drill-fit-drawings.pdf：6件管材/隔套的3页下料钻孔工作图，stock-drill-table.csv列出端面到孔的尺寸；无需打印这些管材。
- assembly-BOM.csv、purchased-hardware-summary.csv、stock-cut-list.csv：只包含当前装配件，旧支架/旧罩不重复。
- assembly07.md：实际逐段装配与可拆顺序；harness-boundary07.md：供电、CAN、GMSL和法兰的保留接口与未解决事项。
- release-gates07.md：3kg肩部、金属骨架、线束、热与实物验收缺口，不能以网格闭合或三个姿态通过替代。
- first-sample07.md：当前装配的孔/螺母/轴承/接缝小样和实测记录要求；actuator-candidate-list.csv是与几何匹配的关节候选，不代表3kg链选型已经合格。
- joint-axis-table.csv、kinematics07.md：当前七轴零位/偏移、正运动学、雅可比和重力关系；cover-mount-table.csv列出当前外罩固定轴线。

原型打印前，先核实到货电机版本，尤其RS00固定面盲孔深度；按各模块小样校准热熔螺母与6807配合。不要直接将本塑料骨架改材质标签后当成金属量产件。
''')
    files=sorted(p for p in O.rglob('*') if p.is_file() and p.suffix!='.zip' and p.name!='SHA256SUMS.txt')
    sums=''.join(c.sha(p)+'  '+str(p.relative_to(O))+'\n' for p in files);(O/'SHA256SUMS.txt').write_text(sums)
    target=O/'A16-complete-body-supported-fit.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(O))
        z.writestr('SHA256SUMS.txt',sums)
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            digest,name=line.split('  ',1);assert hashlib.sha256(z.read(name)).hexdigest()==digest
    print('SELECTED_BODY',len(rows),'parts',len(selected_prints),'prints',len(hardware),'hardware;41 current drawing pages; source/ZIP verified',flush=True)

if __name__=='__main__':main()
