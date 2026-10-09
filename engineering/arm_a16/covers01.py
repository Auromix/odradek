# SPDX-License-Identifier: CC-BY-NC-4.0
"""Selected-A hard-ridge, curved longitudinal shells over actual A16 core.

These are dimensional removable skin candidates; attachment and wiring not
released. No soft mesh is converted to an asserted manufacturing solid.
"""
import json, numpy as np, cadquery as cq, trimesh
from shapely.geometry import Polygon,box as region
import common as c
from vendor import interfaces
g=c.cad;O=c.OUT/'covers01';O.mkdir(exist_ok=True);g.OUT=O
PROFILE=[(-1,0),(-1,.65),(-.72,.94),(0,1.10),(.72,.94),(1,.65),(1,0),(1,-.65),(.65,-.96),(0,-1.04),(-.65,-.96),(-1,-.65)]

def export(id,s,owner,frame=None,note=''):
    assert s.isValid() and len(s.Solids())==1
    good=None
    for tol in [.15,.06,.02]:
        vv,ff=s.tessellate(tol,.12)
        for digits in [5,6,4]:
            m=trimesh.Trimesh([v.toTuple() for v in vv],ff,process=True);m.merge_vertices(digits_vertex=digits)
            m.update_faces(m.nondegenerate_faces());m.update_faces(m.unique_faces());m.remove_unreferenced_vertices()
            if m.is_watertight and m.is_winding_consistent and m.volume>0:good=m;break
        if good is not None:break
    assert good is not None,id
    for directory in ['step','stl']:(O/directory).mkdir(exist_ok=True)
    cq.exporters.export(s,str(O/'step'/(id+'.step')));good.export(O/'stl'/(id+'.stl'))
    bb=s.BoundingBox();p=dict(id=id,owner=owner,frame=frame or f'J{owner}.rotor',role='printed_cover',material='PETG supported fit',note=note,
      solid_count=1,watertight=True,volume_mm3=s.Volume(),mass_kg=s.Volume()*1.27e-6,com_mm=list(s.Center().toTuple()),bbox_size_mm=[bb.xlen,bb.ylen,bb.zlen],vertices_mm=good.vertices.tolist(),triangles=good.faces.tolist())
    g.PARTS.append(p);print('COVER',id,round(p['mass_kg'],4),flush=True);return p

def skin(stations,cy,sign,ruled=False):
    w=cq.Workplane(cq.Plane(origin=(stations[0][0],cy,0),normal=(1,0,0),xDir=(0,1,0)))
    for i,station in enumerate(stations):
        x,ry,rz=station[:3];cu=station[3] if len(station)>3 else 0
        outer=Polygon([(cu+u*ry,v*rz) for u,v in PROFILE])
        cross=outer.difference(outer.buffer(-2.6,join_style=2)).intersection(region(-200,.25,200,200) if sign==1 else region(-200,-200,200,-.25))
        assert cross.geom_type=='Polygon' and not cross.interiors
        if i:w=w.workplane(offset=x-stations[i-1][0])
        w=w.polyline(list(cross.exterior.coords)[:-1]).close()
    return w.loft(ruled=ruled).val().fix()

def main():
    c.base_context();g.PARTS.clear();g.SHAPES.clear();I=interfaces()
    # New long-arm parts keep normal-offset2.6mm walls and a deliberate seam.
    specs=[('upper',3,0,[(46,42,40),(78,28,32),(123,23,28),(205,23,28),(248,27,33),(282,43,49)]),
      ('fore',4,62,[(12,38,41,0),(45,35,36,8),(63,33,36,13.75),(78,33,34,14),(111,22,26,26),(151,26,33,28)])]
    for name,owner,cy,stations in specs:
        for label,sign in [('dorsal',1),('ventral',-1)]:
            s=skin(stations,cy,sign);p=export(f'A16-C-{name}-{label}',s,owner,note='Dimensional2.6mm normal-wall C-section;0.5mm split seam. Attachment design, motor motion and dynamic wiring pending.')
            assert p['solid_count']==1
    # Fixed motor cowls: grow only at actual front annular brackets; slim rear.
    for i,inf in enumerate(I):
        model=inf['model'];n,u,v=[np.array(inf[k],float) for k in ['n','u','v']];p=np.array(inf['out_mm'])
        if i==0:
            stations=[(-91,70,68),(-72,73,71),(-41,69,68),(-10,70,69),(4.5,71,70)]
        elif model=='RS04':stations=[(-60,64,64),(-49,66,65),(-26,66,65),(-4,71,69),(8.5,71,69)]
        elif model=='RS10P':
            stations=[(-69,33,33),(-57,34,33),(-24,34,33),(-2,37,36),(7.5,37,36)]
            if inf['joint']=='J6':stations=[(q,ry,31.35) for q,ry,rz in stations]
        else:stations=[(-60,33,33),(-42,35,34),(-8,37,36),(0,47,46),(33,47,46)]
        T=np.eye(4);T[:3,:3]=np.column_stack([n,u,v]);T[:3,3]=p
        for label,sign in [('a',1),('b',-1)]:
            s=c.transform(skin(stations,0,sign,ruled=True),T)
            # Explicitly provisional connector outlet; exact delivered mating
            # plugs determine its final location and bend radius.
            if model=='RS04':
                exit_raw=np.array([15.0311,56.097,-19.9,1]);Tm=np.array(inf['T_joint_from_raw_mm']);point=(Tm@exit_raw)[:3]
                direction=Tm[:3,:3]@np.array([.258819,.965926,0]);s=s.cut(g.cyl(point-direction*8,direction,10,30)).fix()
            entry=export(f'A16-C-{inf["joint"]}-cowl-{label}',s,i,frame=inf['joint']+'.fixed',note='Fixed split cowl around actual source casing; rear open for service. Source radial cable exit reserved on RS04; other exact mating plugs and airflow need hardware confirmation.')
            assert entry['solid_count']==1
    (O/'meshes.json').write_text(json.dumps(g.PARTS,separators=(',',':'))+'\n')
    parts=[{k:v for k,v in p.items() if k not in ['vertices_mm','triangles']} for p in g.PARTS]
    (O/'manifest.json').write_text(json.dumps(dict(revision='A16-COVERS01',layout=c.L,parts=parts,base_context=c.base_context(),
      style='Chosen A continuous graphite carapace; curved spine, hard section ridges and quiet bronze seams. Manta base retained byte-identical; four-petal head remains a separate module.',
      attachment_qualified=False,collision_qualified=False,production_release=False),indent=2)+'\n')
    print('COVER_CAD',len(parts),flush=True)

if __name__=='__main__':main()
