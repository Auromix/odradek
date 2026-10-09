# SPDX-License-Identifier: CC-BY-NC-4.0
"""Conventional removable armour: rear caps and rectangular connection windows.

Candidate CAD only. Windows are deliberate geometry, never collision exemptions.
"""
import json,numpy as np,cadquery as cq
from shapely.geometry import Polygon,box as region
import common as c
import covers01 as skin
from vendor import interfaces

O=c.OUT/'covers02';O.mkdir(exist_ok=True);skin.O=O;g=c.cad
PORTS={
 'J2':[([-56.5,59,-90],[113,11,50])],
 'J3':[([26,50.5,-13.5],[11,26,27]),([24,-80,-80],[14,160,14]),([8,65.5,-19],[16,9,38])],
 'J4':[([-96.5,-15.5,-25.5],[36,52.35,51])],
 'J5':[([-123.5,32,-13.5],[103,11,27])],
 'J6':[([-41.5,20.5,-38.3],[76,8,11])],
 'J7':[([-92.5,-19.5,-49.8],[127.3,39,16.5])],
}
def endcap(station,sign):
    q,ru,rv=station;poly=Polygon([(u*ru,v*rv) for u,v in skin.PROFILE]).intersection(region(-200,.25,200,200) if sign==1 else region(-200,-200,200,-.25))
    return cq.Workplane(cq.Plane(origin=(q,0,0),normal=(1,0,0),xDir=(0,1,0))).polyline(list(poly.exterior.coords)[:-1]).close().extrude(2.6).val()

def main():
    c.base_context();g.PARTS.clear();I=interfaces()
    specs=[('upper',3,0,[(46,42,40),(78,28,32),(123,23,28),(205,23,28),(235,40,33),(248,42,36),(282,45,49)]),
       ('fore-dorsal',4,62,[(46,35,36,18.5),(63,33,36,16.5),(78,33,34,16.5),(111,22,26,26),(133,26,33,28)]),
       ('fore-ventral',4,62,[(46,35,36,18.5),(63,33,36,16.5),(78,33,34,16.5),(100,23,27,24)])]
    for name,owner,cy,stations in specs:
        for label,sign in ([('dorsal',1),('ventral',-1)] if name=='upper' else [('dorsal',1)] if name=='fore-dorsal' else [('ventral',-1)]):
            partname=f'A16-C02-{name}' + ('-'+label if name=='upper' else '')
            part=skin.skin(stations,cy,sign,ruled=name!='upper')
            if name!='upper':part=part.cut(cq.Solid.makeBox(34,12,51,g.V([48.5,44,-25.5]))).fix()
            skin.export(partname,part,owner,note='Nominal2.6mm cross-section wall; global3D minimum not audited. Dorsal/ventral seam0.5. Ruled fore facets bound the fold-side surface atY45.5, with a conventional socket window; belly endsX100. No continuous sweep proof or qualified attachment.')
    for index,inf in enumerate(I):
        model=inf['model'];n,u,v=[np.array(inf[k],float) for k in ['n','u','v']];p=np.array(inf['out_mm'])
        if index==0:stations=[(-91,70,68),(-72,73,71),(-41,69,68),(-10,70,69),(4.5,71,70),(28.5,73,71)]
        elif model=='RS04':stations=[(-60,64,64),(-49,64,64),(-26,64,64),(-4,71,69),(8.5,71,69)]
        elif model=='RS10P':
            stations=[(-69,33,33),(-57,34,33),(-24,34,33),(-2,37,36),(7.5,37,36)]
            if inf['joint']=='J6':stations=[(q,ry,31.35) for q,ry,rz in stations]
        else:stations=[(-60,33,33),(-42,35,34),(-8,37,36),(0,47,46),(38,47,46)]
        if inf['joint']=='J3':
            # One millimetre narrower front profile clears ordinary J2 fixed
            # screw heads without adding brackets or changing motor datums.
            stations=[(q,70 if q>=-4 else ry,rz) for q,ry,rz in stations]
        T=np.eye(4);T[:3,:3]=np.column_stack([n,u,v]);T[:3,3]=p
        for label,sign in [('a',1),('b',-1)]:
            s=skin.skin(stations,0,sign,ruled=True)
            if index:
                s=s.fuse(endcap(stations[0],sign)).clean().fix()
                # Rear service allocation only; not an assumed hollow actuator
                # route or a released delivered connector location.
                q=stations[0][0];s=s.cut(cq.Solid.makeBox(3.0,20,14,g.V([q-.1,-10,-7]))).fix()
            s=c.transform(s,T)
            for origin,size in PORTS.get(inf['joint'],[]):s=s.cut(cq.Solid.makeBox(*size,g.V(origin))).fix()
            if model=='RS04':
                raw=np.array([15.0311,56.097,-19.9,1]);A=np.array(inf['T_joint_from_raw_mm']);point=(A@raw)[:3];direction=A[:3,:3]@np.array([.258819,.965926,0]);s=s.cut(g.cyl(point-direction*8,direction,10,30)).fix()
            skin.export(f'A16-C02-{inf["joint"]}-cowl-{label}',s,index,frame=inf['joint']+'.fixed',note='Fixed split armour with2.6mm rear cap (J1 base transition open), simple straight-edged connection windows, rear20x14 service allocation. Attachment and exact plug/airflow/motion qualification pending.')
    # These covers share the J3 rotor rigid frame. Join intersecting skins,
    # then put a true0.5mm axial seam atX275: each segment fits a250mm bed.
    # This replaces the overlap; it is not an allowed-collision flag.
    for label,j4 in [('dorsal','b'),('ventral','a')]:
        upperid=f'A16-C02-upper-{label}';jointid=f'A16-C02-J4-cowl-{j4}'
        upper=cq.importers.importStep(str(O/'step'/(upperid+'.step'))).val()
        joint=cq.importers.importStep(str(O/'step'/(jointid+'.step'))).val().translate((340,0,0))
        joined=upper.fuse(joint).clean().fix();assert joined.isValid() and len(joined.Solids())==1
        g.PARTS[:]=[p for p in g.PARTS if p['id'] not in [upperid,jointid]]
        for id,start,length in [(upperid,0,274.75),(f'A16-C02-elbow-{label}',275.25,200)]:
            section=joined.intersect(cq.Solid.makeBox(length,400,400,g.V([start,-200,-200]))).fix()
            skin.export(id,section,3,note='Rigid J3-frame upper/elbow armour; former overlapping skins unioned and split atX275 with0.5 seam. Each closed CAD segment fits250mm envelope. Standard joining tabs/fasteners and motion/hardware checks pending.')
    parts=[{k:v for k,v in p.items() if k not in ['vertices_mm','triangles']} for p in g.PARTS]
    (O/'meshes.json').write_text(json.dumps(g.PARTS,separators=(',',':'))+'\n')
    (O/'manifest.json').write_text(json.dumps(dict(revision='A16-COVERS02-CONVENTIONAL-WINDOWS',layout=c.L,base_context=c.base_context(),parts=parts,
      connection_windows_mm=PORTS,style='Selected A continuous hard-ridge carapace; thinner rear profile, covered rear cases and explicit folding belly pocket. No new mechanism.',
      fixed_joins='Upper/J4 same-frame skins unioned, then divided atX275 with0.5mm seam for250mm printing; attachment not designed. No same-frame collision waiver.',
      collision_qualified=False,attachment_qualified=False,manufacture_release=False),indent=2)+'\n');print('COVERS02',len(parts),flush=True)
    ids={p['id'] for p in parts}
    for folder in ['step','stl']:
        for stale in (O/folder).glob('*'):
            if stale.is_file() and stale.stem not in ids:stale.unlink()

if __name__=='__main__':main()
