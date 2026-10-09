# SPDX-License-Identifier: CC-BY-NC-4.0
"""Unscaled actual vendor STEP, mated by native mounting faces, local cache only."""
import json,sys,shutil,itertools, numpy as np, cadquery as cq
import common as c

DATUMS=[([0,0,0],[1,0,0],[0,1,0],[0,0,1]),
 ([0,65,0],[1,0,0],[0,0,1],[0,-1,0]),
 ([27.85,0,0],[0,1,0],[0,0,1],[1,0,0]),
 ([0,27.85,0],[1,0,0],[0,0,-1],[0,1,0]),
 ([0,40,0],[1,0,0],[0,0,1],[0,-1,0]),
 ([0,0,-30.3],[1,0,0],[0,-1,0],[0,0,-1]),
 ([25.7,0,0],[0,1,0],[0,0,1],[1,0,0])]

def interfaces():
    result=[]
    for j,(p,u,v,n) in zip(c.L['joints'],DATUMS):
        if j['model']=='RS10P':
            m=dict(step_file='RS10.stp',interface_frame={'T_raw_from_interface_mm':[[1,0,0,0],[0,-1,0,0],[0,0,-1,-14.5],[0,0,0,1]],'output_to_housing_front_mm':1.5},
              output_fasteners={'raw_step_xy_mm':[[13.5*np.cos(t),13.5*np.sin(t)] for t in np.arange(6)*np.pi/3],'drawing':'6xM4 depth5; PCD27'},
              fixed_front_fasteners={'raw_step_xy_mm':[[25.5*np.cos(t),25.5*np.sin(t)] for t in np.arange(6)*np.pi/3],'drawing':'6xM4 depth4.5; PCD51'})
        else:m=c.SRC['models'][j['model']]
        d=np.eye(4);d[:3,:3]=np.column_stack([u,v,n]);d[:3,3]=p
        result.append(dict(joint=j['id'],model=j['model'],out_mm=p,u=u,v=v,n=n,
          fixed_mm=(np.array(p)-np.array(n)*m['interface_frame']['output_to_housing_front_mm']).tolist(),
          model_source=m,T_joint_from_raw_mm=(d@np.linalg.inv(np.array(m['interface_frame']['T_raw_from_interface_mm']))).tolist()))
    return result

def run():
    cache=c.CACHE/'vendor';cache.mkdir(exist_ok=True)
    if '--layout-only' in sys.argv:
        audit=json.loads((c.OUT/'vendor-audit.json').read_text())
        for inf,p in zip(interfaces(),audit['motors']):
            assert inf==p['interface'],'Local motor datum changed; reimport/reposition is required.'
            p['cache_step_sha256']={tag:c.sha(cache/(p['joint']+'-'+tag+'.step')) for tag in ['full','stator','external-output']}
        audit['layout']=c.L;audit['revision']=c.L['id'];audit['layout_only_sync']='Only parent frame offsets changed. All seven motor-local interface matrices unchanged; local STEP bytes pinned below.'
        (c.OUT/'vendor-audit.json').write_text(json.dumps(audit,indent=2)+'\n');print('LOCAL_DATUMS_UNCHANGED_LAYOUT_SYNC');return
    expected={s['local_filename']:s for s in c.SRC['sources']}
    a15=json.loads((c.ROOT/'engineering/arm_a15/robstride01/sources.json').read_text())
    expected.update({s['local_filename']:s for s in a15['sources']})
    original=c.CACHE/'vendor-original01'
    if '--reposition' in sys.argv:
        if not original.exists():
            original.mkdir();shutil.copyfile(c.OUT/'vendor-audit.json',original/'audit.json')
            for f in cache.glob('*.step'):shutil.copyfile(f,original/f.name)
        previous=json.loads((original/'audit.json').read_text())
    else:previous=None
    shapes={};records=[];meshes=[]
    for inf in interfaces():
        j=inf['joint'];m=inf['model'];filename=inf['model_source']['step_file']
        path=c.ROOT/('work/arm-a15/robstride' if m=='RS10P' else 'work/arm-a05/vendor')/filename
        assert c.sha(path)==expected[filename]['sha256']
        if previous:
            prior=next(x for x in previous['motors'] if x['joint']==j)
            assert prior['source_sha256']==c.sha(path)
            T=np.array(inf['T_joint_from_raw_mm']);relative=T@np.linalg.inv(np.array(prior['interface']['T_joint_from_raw_mm']))
            assert np.max(abs(relative[:3,:3].T@relative[:3,:3]-np.eye(3)))<1e-9
            transformed=[]
            for name in ['full','stator','external-output']:
                w=cq.importers.importStep(str(original/(j+'-'+name+'.step')))
                transformed.append(c.transform(w.val(),relative))
            full,stator,rotor=transformed
            # Entries are now already in new joint coordinates; normal export
            # code below uses identity. Preserve the audited raw mapping.
            shapes[m+'_reuse_'+j]=(full,stator,rotor)
            key=m+'_reuse_'+j
        else:key=m
        if key not in shapes:
            w=cq.importers.importStep(str(path));full=cq.Compound.makeCompound([s for v in w.vals() for s in v.Solids()])
            rawT=np.array(inf['model_source']['interface_frame']['T_raw_from_interface_mm'],float)
            origin=rawT[:3,3];n=rawT[:3,2];proj=inf['model_source']['interface_frame']['output_to_housing_front_mm']
            radius={'RS03':35,'RS04':35,'RS00':17.5,'RS10P':20}[m]
            zone=c.cad.cyl(origin-n*proj,n,radius+.01,proj+4)
            rear=[];front=[]
            for s in full.Solids():
                a=s.intersect(zone);b=s.cut(zone)
                if a.Volume()>1e-7:front.extend(a.Solids())
                if b.Volume()>1e-7:rear.extend(b.Solids())
            shapes[key]=(full,cq.Compound.makeCompound(rear),cq.Compound.makeCompound(front))
        full,stator,rotor=shapes[key];T=np.eye(4) if previous else np.array(inf['T_joint_from_raw_mm'])
        world=c.transform(full,T);cq.exporters.export(world,str(cache/(j+'-full.step')))
        error=prior['partition_volume_error_mm3'] if previous else abs(full.Volume()-stator.Volume()-rotor.Volume())
        if not previous:assert error<max(.5,full.Volume()*1e-4)
        for label,s,frame in [('stator',stator,j+'.fixed'),('external-output',rotor,j+'.rotor')]:
            s=c.transform(s,T);cq.exporters.export(s,str(cache/(j+'-'+label+'.step')))
            vv,tt=s.tessellate(.2,.25)
            meshes.append(dict(id=j+'-supplier-'+label,frame=frame,model=m,role='supplier_reference',source_sha256=c.sha(path),vertices_mm=[list(v.toTuple()) for v in vv],triangles=[list(t) for t in tt]))
        if previous:
            b=prior['bbox_joint_mm'];corners=np.array(list(itertools.product(*[(b[k],b[k+3]) for k in range(3)])))
            mapped=corners@relative[:3,:3].T+relative[:3,3];bbox=np.r_[mapped.min(axis=0),mapped.max(axis=0)].tolist()
        else:
            bb=world.BoundingBox();bbox=[bb.xmin,bb.ymin,bb.zmin,bb.xmax,bb.ymax,bb.zmax]
        records.append(dict(joint=j,model=m,source_sha256=c.sha(path),source_url=expected[filename]['url'],
          linear_scale=1,source_solid_count=len(full.Solids()),valid=world.isValid(),partition_volume_error_mm3=error,
          bbox_joint_mm=bbox,interface=inf,partition_audit_inherited_under_rigid_transform=bool(previous),
          cache_step_sha256={tag:c.sha(cache/(j+'-'+tag+'.step')) for tag in ['full','stator','external-output']}))
        print('NATIVE_MOTOR',j,m,'partition',error,flush=True)
    (cache/'meshes.json').write_text(json.dumps(meshes,separators=(',',':'))+'\n')
    (c.OUT/'vendor-audit.json').write_text(json.dumps(dict(revision=c.L['id'],layout=c.L,motors=records,
      partition_note='Externally visible output boss and pins only; this is not an internal rotor/stator mass model.',
      measured_internal_COM=False,production_release=False,supplier_rights='Exact vendor meshes remain in ignored work cache; published material is import scripts and source fingerprints.'),indent=2)+'\n')

if __name__=='__main__':run()
