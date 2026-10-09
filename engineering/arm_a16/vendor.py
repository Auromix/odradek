# SPDX-License-Identifier: CC-BY-NC-4.0
"""Unscaled actual vendor STEP, mated by native mounting faces, local cache only."""
import json, numpy as np, cadquery as cq
import common as c

DATUMS=[([0,0,0],[1,0,0],[0,1,0],[0,0,1]),
 ([0,65,0],[1,0,0],[0,0,1],[0,-1,0]),
 ([27.85,0,0],[0,1,0],[0,0,1],[1,0,0]),
 ([0,27.85,0],[1,0,0],[0,0,-1],[0,1,0]),
 ([0,30,0],[1,0,0],[0,0,1],[0,-1,0]),
 ([0,0,46.3],[1,0,0],[0,-1,0],[0,0,-1]),
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
    expected={s['local_filename']:s for s in c.SRC['sources']}
    a15=json.loads((c.ROOT/'engineering/arm_a15/robstride01/sources.json').read_text())
    expected.update({s['local_filename']:s for s in a15['sources']})
    shapes={};records=[];meshes=[]
    for inf in interfaces():
        j=inf['joint'];m=inf['model'];filename=inf['model_source']['step_file']
        path=c.ROOT/('work/arm-a15/robstride' if m=='RS10P' else 'work/arm-a05/vendor')/filename
        assert c.sha(path)==expected[filename]['sha256']
        if m not in shapes:
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
            shapes[m]=(full,cq.Compound.makeCompound(rear),cq.Compound.makeCompound(front))
        full,stator,rotor=shapes[m];T=np.array(inf['T_joint_from_raw_mm'])
        world=c.transform(full,T);cq.exporters.export(world,str(cache/(j+'-full.step')))
        error=abs(full.Volume()-stator.Volume()-rotor.Volume());assert error<max(.5,full.Volume()*1e-4)
        for label,s,frame in [('stator',stator,j+'.fixed'),('external-output',rotor,j+'.rotor')]:
            s=c.transform(s,T);cq.exporters.export(s,str(cache/(j+'-'+label+'.step')))
            vv,tt=s.tessellate(.2,.25)
            meshes.append(dict(id=j+'-supplier-'+label,frame=frame,model=m,role='supplier_reference',source_sha256=c.sha(path),vertices_mm=[list(v.toTuple()) for v in vv],triangles=[list(t) for t in tt]))
        bb=world.BoundingBox();records.append(dict(joint=j,model=m,source_sha256=c.sha(path),source_url=expected[filename]['url'],
          linear_scale=1,source_solid_count=len(full.Solids()),valid=world.isValid(),partition_volume_error_mm3=error,
          bbox_joint_mm=[bb.xmin,bb.ymin,bb.zmin,bb.xmax,bb.ymax,bb.zmax],interface=inf))
        print('NATIVE_MOTOR',j,m,'partition',error,flush=True)
    (cache/'meshes.json').write_text(json.dumps(meshes,separators=(',',':'))+'\n')
    (c.OUT/'vendor-audit.json').write_text(json.dumps(dict(revision=c.L['id'],layout=c.L,motors=records,
      partition_note='Externally visible output boss and pins only; this is not an internal rotor/stator mass model.',
      measured_internal_COM=False,production_release=False,supplier_rights='Exact vendor meshes remain in ignored work cache; published material is import scripts and source fingerprints.'),indent=2)+'\n')

if __name__=='__main__':run()
