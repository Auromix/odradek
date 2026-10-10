# SPDX-License-Identifier: CC-BY-NC-4.0
"""Compact ordinary wrist skin mounting, with standard brass heat-set inserts."""
import json,math,numpy as np,cadquery as cq
import common as c
import covers01 as skin
import hardware01 as h
import skeleton_review as r
from shapely.geometry import Polygon,LineString
from vendor import interfaces
from module_review import review

O=c.OUT/'wrist05';O.mkdir(exist_ok=True);g=c.cad
INSERT_SOURCE='https://www.igo3d.com/mediafiles/Sonstiges/Ruthex/ruthex_Datenblatt_RX-Serie.pdf'
SPECS=[('J5','A16-S107-fore-distal-socket',4,'J4.rotor',[185,62,0],[75,105]),
       ('J6','A16-S109-wrist-pitch-yaw-L',5,'J5.rotor',[55,0,0],[135,165,195,225])]

def insert(id,p,n,owner,frame,length,target):
    s=g.ring(p,n,2.3,1.5,length)
    e=g.add(id,s,owner,frame=frame,role='hardware',material='Purchased lead-free brass heat-set RX-M3x5.7 /RX-M3Sx4.0; nominal envelope, not knurl detail',mass=s.Volume()*8.5e-6,
            note=f'Ruthex manufacturer datasheet15.08.2022: maximumOD4.6, recommended pilotD4.0,minwall1.6; length{length}. Brass density8.5 is assumed; pull-out and insertion process unqualified.')
    e['intentional_heatset_target']=target;e['heatset_zone_mm']=dict(p=np.array(p).tolist(),n=np.array(n).tolist(),length=length,outer_diameter=4.62,pilot_diameter=3.98)
    return e

def main():
    g.OUT=O;skin.O=O;g.PARTS.clear();g.SHAPES.clear();h.H.clear();I=interfaces();replacements=set();mounts=[];tools=[]
    for joint,oldplate,owner,frame,offset,angles in SPECS:
        inf=next(x for x in I if x['joint']==joint);n,u,v=[np.array(inf[k],float) for k in ['n','u','v']];p=np.array(inf['out_mm']);off=np.array(offset,float)
        T=np.eye(4);T[:3,:3]=np.column_stack([n,u,v]);T[:3,3]=p
        back=float(np.dot(np.array(inf['fixed_mm'])-p,n));front=back+8;tab0=front+.5;tab1=tab0+3
        rad=31 if joint=='J5' else 31.5
        plate=r.load(c.OUT/'skeleton01/step'/(oldplate+'.step'));points=[p+rad*(math.cos(math.radians(a))*u+math.sin(math.radians(a))*v) for a in angles]
        for pt in points:
            plate=plate.fuse(g.cyl(pt+off+n*back,n,4,8)).clean().fix()
            plate=g.drill(plate,pt+off+n*(back-.1),n,3.5,8.2)
            plate=g.drill(plate,pt+off+n*(front-5.7),n,4,5.8)
        radial=[]
        if joint=='J5':
            for a in [240,300]:
                angle=math.radians(a);d=np.array([math.cos(angle),math.sin(angle)]);direction=d[0]*u+d[1]*v
                centre=p+n*2.5;rp=centre+direction*32.5
                plate=g.drill(plate,rp+off-direction*4,direction,4,4.1)
                edge=Polygon([(x*37,y*36) for x,y in skin.PROFILE]).intersection(LineString([[0,0],(d*100).tolist()]))
                exterior=float(np.linalg.norm(np.array(edge.coords[-1])))
                radial.append((a,rp,direction,exterior))
        pid='A16-C05-'+joint+'-mount-plate'
        g.add(pid,plate,owner,frame=frame,role='printed_structure',material='PETG supported fit',mass=plate.Volume()*1.27e-6,
              note='Original ring profile and native interfaces retained; four ordinaryD8 cylindrical pads centredR31.5. D4.0x5.7 heat-set pilots for genuine RX-M3x5.7; minimum nominal radial wall2mm. Print calibration and insert retention must be tested.')
        replacements.add(oldplate);rv=31.35 if joint=='J6' else 36;ru=37
        outer=cq.Workplane(cq.Plane(origin=(tab0,0,0),normal=(1,0,0),xDir=(0,1,0))).polyline([(a*ru,b*rv) for a,b in skin.PROFILE]).close().extrude(3).val()
        for label,sign in [('a',1),('b',-1)]:
            oldid='A16-C02-'+joint+'-cowl-'+label;replacements.add(oldid);part=r.load(c.OUT/'covers02/step'/(oldid+'.step'))
            for a,pt in zip(angles,points):
                if math.sin(math.radians(a))*sign<0:continue
                t=math.radians(a);d=np.array([math.cos(t),math.sin(t)]);e=np.array([-d[1],d[0]])
                poly=[d*x+e*y for x,y in [(26.5,-4),(70,-4),(70,4),(26.5,4)]]
                strip=cq.Workplane(cq.Plane(origin=(7,0,0),normal=(1,0,0),xDir=(0,1,0))).polyline([x.tolist() for x in poly]).close().extrude(3.5).val()
                patch=skin.skin([(7,ru,rv),(tab1+.5,ru,rv)],0,sign,ruled=True).intersect(strip)
                tab=cq.Workplane(cq.Plane(origin=(tab0,0,0),normal=(1,0,0),xDir=(0,1,0))).polyline([x.tolist() for x in poly]).close().extrude(3).val().intersect(outer)
                part=part.fuse(c.transform(tab.fuse(patch).clean(),T)).clean().fix();part=g.drill(part,pt+n*(tab0-.1),n,3.5,3.2)
            if joint=='J5' and sign==-1:
                for a,rp,direction,exterior in radial:
                    part=part.fuse(g.cyl(rp+direction*.05,direction,4,exterior-32.5-.05)).clean().fix()
                    part=g.drill(part,rp-direction*.1,direction,3.5,exterior-32.5+.2)
                    part=part.cut(g.cyl(rp+direction*(exterior-32.5),direction,3.7,6)).fix()
            for delta in h.points(inf,'fixed_front_fasteners'):
                part=g.drill(part,p+delta+n*(front-.1),n,9.8,7.5)
            if joint=='J6':
                for pt in points:
                    # 0.3mm radial service clearance around the ordinary
                    # fixed D8 boss; stops before the0.5mm spacer/ear plane.
                    part=part.cut(g.cyl(pt+n*(back-.1),n,4.3,8.3)).clean().fix()
            skin.export('A16-C05-'+joint+'-cowl-'+label,part,owner,frame=joint+'.fixed',note='Two straight3mm ears per split cowl; local wall patch, native washer/headD9.8 access reliefs. M3x8 into ordinary brass heat-set inserts. Heat-set pullout and actual tool access unqualified.')
        for k,pt in enumerate(points,1):
            q=pt+off
            h.bolt(f'A16-C05-H-{joint}-{k}',q+n*front,n,3,8,3.5,owner,frame,w=.5,washer_hole=3.2)
            h.washer(f'A16-C05-H-{joint}-spacer-{k}',q+n*front,n,3,owner,frame,.5,7,hole=3.2)
            insert(f'A16-C05-H-{joint}-insert-{k}',q+n*(front-5.7),n,owner,frame,5.7,pid)
            mounts.append(dict(joint=joint,k=k,frame=frame,p_mm=q.tolist(),n=n.tolist(),radius_mm=rad,angle_deg=angles[k-1],tab_q_mm=[tab0,tab1],insert_length_mm=5.7,pilot_diameter_mm=4,bolt='M3x8',engagement_mm=4))
            tools.append((joint+'-'+str(k),frame,g.cyl(q+n*(front+7.1),n,1.6,20)))
        for k,(a,rp,direction,exterior) in enumerate(radial,1):
            q=rp+off;grip=exterior-32.5
            length=next(z for z in [8,10,12,14,16] if 2.5<=z-grip-.5<=3.9)
            key='radial-'+str(k)
            h.bolt('A16-C05-H-J5-'+key,q,direction,3,length,grip,owner,frame,w=.5,washer_hole=3.2)
            insert('A16-C05-H-J5-insert-'+key,q-direction*4,direction,owner,frame,4,pid)
            tools.append(('J5-'+key,frame,g.cyl(q+direction*(grip+3.6),direction,1.6,20)))
            mounts.append(dict(joint='J5',k=key,frame=frame,p_mm=q.tolist(),n=direction.tolist(),radius_mm=32.5,angle_deg=a,pilot_diameter_mm=4,insert_length_mm=4,bolt='M3x'+str(length),engagement_mm=length-grip-.5))
    housingid='A13-J7-101-bearing-housing';replacements.add(housingid);housing=r.load(c.OUT/'skeleton01/step'/(housingid+'.step'));newhousing='A16-C05-J7-bearing-housing'
    for sign in [1,-1]:
        for x in [39,49]:
            n=np.array([0,0,sign],float);p=np.array([x,0,42*sign],float);housing=g.drill(housing,p-n*4,n,4,4.1)
    g.add(newhousing,housing,6,frame='J7.fixed',role='printed_structure',material='PETG supported fit',mass=housing.Volume()*1.27e-6,note='Original bearing seats/cage bolts unchanged; fourD4.0x4.0 radial heat-set pilots atX39/49,Y0,Z+/-42. RX-M3Sx4.0; physical bearing/pullout checks pending.')
    for k,(label,sign,outer,length) in enumerate([('a',1,50.6,12),('b',-1,47.84,10)],1):
        oldid='A16-C02-J7-cowl-'+label;replacements.add(oldid);part=r.load(c.OUT/'covers02/step'/(oldid+'.step'));n=np.array([0,0,sign],float)
        # Ordinary round rear clearance: J6 origin isX-75 in this frame.
        # This cuts cosmetic material, never source motor, cage or bearing.
        # Keeps the J7 lower skirt outside the fixed J6 front ring/cowl over
        # yaw; finite samples must still verify the resulting assembly.
        part=part.cut(g.cyl([-75,0,-55],[0,0,1],46,55)).clean().fix()
        for j,x in enumerate([39,49],1):
            p=np.array([x,0,42*sign],float);key=str(k)+'-'+str(j)
            boss=g.cyl(p+n*.05,n,4,outer-42-.05);part=part.fuse(boss).clean().fix();part=g.drill(part,p-n*.1,n,3.5,outer-42+.3)
            h.bolt(f'A16-C05-H-J7-{key}',p,n,3,length,outer-42,6,'J7.fixed',w=.5,washer_hole=3.2)
            insert(f'A16-C05-H-J7-insert-{key}',p-n*4,n,6,'J7.fixed',4,newhousing)
            tools.append(('J7-'+key,'J7.fixed',g.cyl(p+n*(outer-42+3.6),n,1.6,25)))
            mounts.append(dict(joint='J7',k=key,frame='J7.fixed',p_mm=p.tolist(),n=n.tolist(),radius_mm=42,angle_deg=90 if sign==1 else 270,pilot_diameter_mm=4,insert_length_mm=4,bolt='M3x'+str(length),engagement_mm=length-(outer-42)-.5))
        skin.export('A16-C05-J7-cowl-'+label,part,6,frame='J7.fixed',note='Original silhouette with ordinary rearR46 circular relief about J6 axis, Z-55..0; two radialM3 fixings per half into standard short brass inserts. No motor, bearing, gear or axis change.')
    parts=[{k:v for k,v in p.items() if k not in ['vertices_mm','triangles']} for p in g.PARTS];ids={p['id'] for p in parts}
    for sub in ['step','stl']:
        for f in (O/sub).glob('*'):
            if f.stem not in ids:f.unlink()
    (O/'meshes.json').write_text(json.dumps(g.PARTS,separators=(',',':'))+'\n')
    (O/'manifest.json').write_text(json.dumps(dict(revision='A16-WRIST05-STANDARD-INSERTS',layout=c.L,base_context=c.base_context(),parts=parts,replaces_only=sorted(replacements),mounts=mounts,
        insert_source=dict(url=INSERT_SOURCE,manufacturer='ruthex',document_date='2022-08-15',max_outer_mm=4.6,pilot_mm=4.0,min_wall_mm=1.6,limitations='Old source: confirm actual purchased SKU dimensions; no pullout or process qualification.'),
        hardware_BOM={'ISO4762_M3x8':6,'J5_radial_M3_lengths':'see mounts','ISO4762_M3x12_J7':2,'ISO4762_M3x10_J7':2,'DIN125_M3_OD7_ID3.2_H0.5':18,'RX-M3x5.7':6,'RX-M3Sx4.0':6},
        assembly='Heat-set inserts on calibration coupon first, then plates/cage while motor/shaft absent. Insert flush with fixed front/outer radial face. Install source motors and bearings, add0.5mm spacers and covers. Support arm while removing covers. No plastic tapped threads.',
        physical_assembly_qualified=False,retention_strength_qualified=False,production_release=False),indent=2)+'\n')
    review('wrist05',tools)

if __name__=='__main__':main()
