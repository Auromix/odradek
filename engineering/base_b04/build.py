# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Build native STEP assembly, individual exact solids, meshes and evidence."""
import argparse,csv,hashlib,itertools,json,time
from pathlib import Path
import cadquery as cq
import trimesh
from model import make,box,cyl,P,HERE,DENSITY,Part

OUT=HERE/'build'
def bbox(s):
    b=s.BoundingBox();return {'min':[b.xmin,b.ymin,b.zmin],'max':[b.xmax,b.ymax,b.zmax],'size':[b.xlen,b.ylen,b.zlen]}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def candidate(a,b):
    aa,bb=bbox(a),bbox(b)
    return all(min(aa['max'][i],bb['max'][i])-max(aa['min'][i],bb['min'][i])>1e-5 for i in range(3))
def overlap(a,b):
    if not candidate(a,b):return 0
    v=a.intersect(b).Volume()
    return max(0,v)
def components():
    path=HERE.parent/'electronics/base-b04/mechanical-interface.json'
    result=[]
    if path.exists():
        data=json.loads(path.read_text())
        for c in data['components']:
            lo=c['body_bbox_board_min_mm'];hi=c['body_bbox_board_max_mm'];sizes=[hi[i]-lo[i] for i in range(3)]
            if min(sizes)<.001:continue
            origin=[lo[i]+P['pcb_origin'][i] for i in range(3)]
            result.append(Part('PCB-'+c['ref'],box(*origin,*sizes),'FR4','Purchased component outer envelope; see PCB BOM',category='component',color=[.13,.16,.18,1]))
        verification=path.parent/'mechanical/verification.json'
        if verification.exists():
            for c in json.loads(verification.read_text())['component_reference_objects']:
                if '_' not in c['name']:continue
                lo=c['bbox_min_mm'];hi=c['bbox_max_mm']
                origin=[lo[i]+P['pcb_origin'][i] for i in range(3)]
                result.append(Part('PCB-'+c['name'],box(*origin,*[hi[i]-lo[i] for i in range(3)]),'FR4',c['scope'],category='component',color=[.22,.43,.28,1]))
        readback=path.parent/'native-readback.json'
        if readback.exists():
            for h in json.loads(readback.read_text())['holes']:
                if h['type']!='PTH':continue
                u,v=h['uv_mm']
                result.append(Part('PCB-pin-'+h['ref']+'-'+h['pin'],cyl((u-40,v-2,20.5),(0,0,1),h['drill_mm'][0]*.35,2.5),'steel','Trimmed lead allocation from native PTH readback',category='component'))
    return result
def cables():
    result=[]
    for name,x,diam in [('GMSL-A',48,3),('GMSL-B',56,3),('ECAT',64,6),('POWER',73,8)]:
        pts=[(x,60,44),(x,8,44),(x,-27,9),(x,-27,-105),(x,8,-140),(x,120,-140)]
        edges=[cq.Edge.makeLine(cq.Vector(*pts[0]),cq.Vector(*pts[1])),
          cq.Edge.makeThreePointArc(cq.Vector(*pts[1]),cq.Vector(x,8-35/2**.5,9+35/2**.5),cq.Vector(*pts[2])),
          cq.Edge.makeLine(cq.Vector(*pts[2]),cq.Vector(*pts[3])),
          cq.Edge.makeThreePointArc(cq.Vector(*pts[3]),cq.Vector(x,8-35/2**.5,-105-35/2**.5),cq.Vector(*pts[4])),
          cq.Edge.makeLine(cq.Vector(*pts[4]),cq.Vector(*pts[5]))]
        path=cq.Wire.assembleEdges(edges)
        sh=cq.Workplane(cq.Plane(origin=pts[0],normal=(0,-1,0))).circle(diam/2).sweep(path).val()
        result.append(Part('ROUTE-'+name,sh,'silicone','Routing gauge only: R35 centerline; cable/connector qualification pending',category='routing',color=[.90,.49,.13,1] if name=='POWER' else [.14,.24,.29,1]))
    return result
def main():
    OUT.mkdir(exist_ok=True);(OUT/'parts').mkdir(exist_ok=True)
    parts=make(P['nominal_desk_thickness'],environment=True)+components()+cables()
    manifest={'revision':P['revision'],'length_unit':'mm','coordinates':P['coordinates'],'parts':[],
      'tolerances':P['tolerances'],'stage':P['stage'],'parameters_sha256':digest(HERE/'parameters.json')}
    assembly=cq.Assembly(name='Odradek_Base_B04_P1')
    checks=[]
    for p in parts:
        b=bbox(p.shape);valid=p.shape.isValid();n=len(p.shape.Solids())
        assert valid and n==1,(p.id,valid,n)
        path=OUT/'parts'/p.id
        cq.exporters.export(p.shape,str(path.with_suffix('.stl')),tolerance=.07,angularTolerance=.14)
        # Environment and purchased parts are not fabrication STEP drawings.
        if p.category=='custom':
            cq.exporters.export(p.shape,str(path.with_suffix('.step')))
            re=cq.importers.importStep(str(path.with_suffix('.step'))).val()
            mesh=trimesh.load_mesh(path.with_suffix('.stl'),process=True)
            checks.append({'part':p.id,'valid_single_solid':valid and n==1,'step_volume_error_mm3':abs(re.Volume()-p.shape.Volume()),'watertight':bool(mesh.is_watertight)})
            assert checks[-1]['step_volume_error_mm3']<.02 and mesh.is_watertight,p.id
        if p.category!='environment':assembly.add(p.shape,name=p.id.replace('-','_'),color=cq.Color(*p.color))
        manifest['parts'].append({'id':p.id,'material':p.material,'process':p.process,'category':p.category,
          'quantity':1,'features':p.features,'notes':p.notes,'bbox':b,'local_bbox':b,'volume_mm3':p.shape.Volume(),
          'mass_kg':p.shape.Volume()*DENSITY[p.material] if p.material in DENSITY and p.category in ['custom','hardware','fastener'] else None,
          'color':p.color,'step':str(path.with_suffix('.step').relative_to(OUT)) if p.category=='custom' else None,
          'stl':str(path.with_suffix('.stl').relative_to(OUT))})
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    assembly.export(str(OUT/'ODR-BASE-B04-P1.step'))
    (OUT/'geometry-checks.json').write_text(json.dumps(checks,indent=2))
    # Export a single GLB with named individual nodes (millimetres -> metres, Z up retained).
    scene=trimesh.Scene()
    for p in manifest['parts']:
        mesh=trimesh.load_mesh(OUT/p['stl'],process=True);mesh.apply_scale(.001)
        mesh.visual.face_colors=[int(v*255) for v in p['color']]
        scene.add_geometry(mesh,node_name=p['id'],geom_name=p['id'])
    scene.export(OUT/'ODR-BASE-B04-P1.glb')
    with (OUT/'parts-bom.csv').open('w',newline='') as f:
        fields=['id','category','quantity','material','process','mass_kg']
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(manifest['parts'])
    print(json.dumps({'parts':len(parts),'custom':len(checks),'modeled_mass_kg':sum(p['mass_kg'] or 0 for p in manifest['parts']),'out':str(OUT)}),flush=True)
    # Check every rigid custom part pair, plus environment, PCB and routing.
    selected=[p for p in parts if p.category not in ['fastener','hardware']]
    contacts=[]
    for a,b in itertools.combinations(selected,2):
        if a.category=='component' and b.category=='component':continue
        v=overlap(a.shape,b.shape)
        if v>.02:contacts.append({'a':a.id,'b':b.id,'intersection_mm3':v})
    (OUT/'nominal-collisions.json').write_text(json.dumps(contacts,indent=2))
    print('nominal_interferences',json.dumps(contacts),flush=True)
if __name__=='__main__':main()
