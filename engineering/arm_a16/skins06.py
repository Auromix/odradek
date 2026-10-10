# SPDX-License-Identifier: CC-BY-NC-4.0
"""Simple split saddles and ordinary straight bosses fixing longitudinal skins."""
import json,numpy as np,cadquery as cq
import common as c
import covers01 as skin
import hardware01 as h
import skeleton_review as r
from wrist05 import insert
from module_review import review

O=c.OUT/'skins06';O.mkdir(exist_ok=True);g=c.cad

def height(part,x,y,sign):
    # Exact BREP intersection at the fixing centre; do not assume the smooth
    # longitudinal loft passes through a linearly interpolated section.
    probe=g.cyl([x,y,-100],[0,0,1],.01,200);w=part.intersect(probe);assert w.Volume()>1e-7
    b=w.BoundingBox();return b.zmax if sign==1 else -b.zmin

def main():
    g.OUT=O;skin.O=O;g.PARTS.clear();g.SHAPES.clear();h.H.clear();replacements=[];mounts=[];tools=[]
    upper={label:r.load(c.OUT/'covers02/step'/('A16-C02-upper-'+label+'.step')) for label in ['dorsal','ventral']}
    for station in [115,200]:
        s=cq.Solid.makeBox(8,26,46.6,g.V([station-4,-13,-23.3])).cut(cq.Solid.makeBox(8.2,20.4,40.4,g.V([station-4.1,-10.2,-20.2])))
        for y in [-15.5,15.5]:
            s=s.fuse(cq.Solid.makeBox(8,7,16,g.V([station-4,y-3.5,-8]))).clean().fix();s=g.drill(s,[station,y,-8.1],[0,0,1],3.5,16.2)
            s=g.drill(s,[station,y,8],[0,0,1],8.2,18)
            s=g.drill(s,[station,y,-26],[0,0,1],7.2,18)
        for label,sign in [('dorsal',1),('ventral',-1)]:
            n=np.array([0,0,sign],float);outer=height(upper[label],station,0,sign);face=outer-4;assert face-4>20.2
            p=np.array([station,0,face*sign],float);p0=np.array([station,0,23.3*sign],float)
            saddle=s.intersect(cq.Solid.makeBox(20,60,30,g.V([station-10,-30,.25 if sign==1 else -30.25]))).fix()
            if face>=23.3:saddle=saddle.fuse(g.cyl(p0-n*.1,n,4,face-23.3+.1)).clean().fix()
            else:saddle=saddle.cut(g.cyl(p,n,4.1,23.3-face+.1)).clean().fix()
            saddle=g.drill(saddle,p-n*4,n,4,4.1);sid=f'A16-C06-upper-saddle-{station}-{label}'
            g.add(sid,saddle,3,frame='J3.rotor',role='printed_structure',material='PETG supported fit',mass=saddle.Volume()*1.27e-6,note='Conventional split8mm-long saddle around stock20x40 tube; cavity20.4x40.4, seam0.5. Two ordinary clamp bolts; no stock-tube drilling or cable passage blockage. Tightening/friction requires physical fit.')
            boss=g.cyl(p,n,4,4);upper[label]=upper[label].fuse(boss).clean().fix();upper[label]=g.drill(upper[label],p-n*.1,n,3.5,12)
            upper[label]=upper[label].cut(g.cyl(p+n*4,n,3.7,8)).fix()
            length=8
            key=str(station)+'-'+label
            h.bolt('A16-C06-H-upper-'+key,p,n,3,length,4,3,'J3.rotor',w=.5,washer_hole=3.2)
            insert('A16-C06-H-upper-insert-'+key,p-n*4,n,3,'J3.rotor',4,sid)
            mounts.append(dict(joint='upper',k=key,frame='J3.rotor',p_mm=p.tolist(),n=n.tolist(),radius_mm=0,angle_deg=0,cover_outer_mm=outer,pilot_diameter_mm=4,insert_length_mm=4,bolt='M3x'+str(length),engagement_mm=3.5))
            tools.append(('upper-'+key,'J3.rotor',g.cyl(p+n*7.6,n,1.6,25)))
        for k,y in enumerate([-15.5,15.5],1):
            p=[station,y,-8];key=str(station)+'-'+str(k)
            h.bolt('A16-C06-H-saddle-'+key,p,[0,0,1],3,20,16,3,'J3.rotor',w=.5,washer_hole=3.2)
            h.nut('A16-C06-H-saddle-nut-'+key,[station,y,-10.4],[0,0,1],3,3,'J3.rotor')
    for label in upper:
        old='A16-C02-upper-'+label;replacements.append(old);skin.export('A16-C06-upper-'+label,upper[label],3,frame='J3.rotor',note='Original selected-A long continuous outline. Two ordinary axial saddle stations, twoM3 fixings per half. IntegralD8 straight supports; closed nominal print solid, actual fit pending.')
    # Fore tube is captured by existing end sockets: mount to the rear spine,
    # not to an inaccessible new clamp squeezed over the tube/socket overlap.
    oldplate='A16-C05-J5-mount-plate';plate=r.load(c.OUT/'wrist05/step'/(oldplate+'.step'));pid='A16-C06-fore-spine-and-J5-ring';replacements.append(oldplate)
    fore={label:r.load(c.OUT/'covers02/step'/('A16-C02-fore-'+label+'.step')) for label in ['dorsal','ventral']}
    for station in [85,95]:
        for label,sign in [('dorsal',1),('ventral',-1)]:
            n=np.array([0,0,sign],float);outer=height(fore[label],station,99,sign);face=outer-6.5;assert face>18
            p=np.array([station,99,face*sign]);support=g.cyl([station,99,12*sign],n,4,face-12)
            plate=plate.fuse(support).clean().fix();plate=g.drill(plate,p-n*5.7,n,4,5.8)
            fore[label]=fore[label].fuse(g.cyl(p,n,4,6.5)).clean().fix();fore[label]=g.drill(fore[label],p-n*.1,n,3.5,15)
            fore[label]=fore[label].cut(g.cyl(p+n*6.5,n,3.7,8)).fix()
            key=str(station)+'-'+label
            h.bolt('A16-C06-H-fore-'+key,p,n,3,12,6.5,4,'J4.rotor',w=.5,washer_hole=3.2)
            insert('A16-C06-H-fore-insert-'+key,p-n*5.7,n,4,'J4.rotor',5.7,pid)
            mounts.append(dict(joint='fore',k=key,frame='J4.rotor',p_mm=p.tolist(),n=n.tolist(),radius_mm=0,angle_deg=0,cover_outer_mm=outer,pilot_diameter_mm=4,insert_length_mm=5.7,bolt='M3x12',engagement_mm=5))
            tools.append(('fore-'+key,'J4.rotor',g.cyl(p+n*(6.5+3.6),n,1.6,25)))
    g.add(pid,plate,4,frame='J4.rotor',role='printed_structure',material='PETG supported fit',mass=plate.Volume()*1.27e-6,note='Original C05 native J5 ring/sockets retained. Four ordinaryD8 rear-spine standoffs centredX85/95,Y99; RX-M3x5.7 pilots. Tube path and transverse clamps unchanged.')
    for label in fore:
        replacements.append('A16-C02-fore-'+label);skin.export('A16-C06-fore-'+label,fore[label],4,frame='J4.rotor',note='Original A fore outline/connection window retained; two straight rear-spine supports per half. OrdinaryM3x12 removable covers, no unsupported friction-only decorative skin.')
    # The C05 insert target id follows the replacement plate, exactly as the
    # unchanged source pilots follow it. Rename only the target metadata.
    old=json.loads((c.OUT/'wrist05/manifest.json').read_text());relabels=[]
    for p in old['parts']:
        if p.get('intentional_heatset_target')==oldplate:
            source=r.load(c.OUT/'wrist05/step'/(p['id']+'.step'));q=g.add(p['id']+'-C06',source,p['owner'],frame=p['frame'],role=p['role'],material=p['material'],mass=p['mass_kg'],note=p['note']);q['intentional_heatset_target']=pid;q['heatset_zone_mm']=p['heatset_zone_mm'];replacements.append(p['id']);relabels.append(p['id'])
    parts=[{k:v for k,v in p.items() if k not in ['vertices_mm','triangles']} for p in g.PARTS]
    (O/'meshes.json').write_text(json.dumps(g.PARTS,separators=(',',':'))+'\n')
    (O/'manifest.json').write_text(json.dumps(dict(revision='A16-SKINS06-SPLIT-SADDLES',layout=c.L,base_context=c.base_context(),parts=parts,replaces_only=replacements,mounts=mounts,
        hardware_BOM={'ISO4762_M3x20_saddle_clamp':4,'ISO4032_M3_AF5.5_H2.4':4,'ISO4762_M3x12_fore':4,'ISO4762_M3x8_upper':4,'DIN125_M3_OD7_ID3.2_H0.5':12,'RX-M3Sx4.0':4,'RX-M3x5.7':4},
        inherited_C05_inserts=relabels,assembly='Fit upper saddles on bare stock tube before skin halves; ordinary through-clamp screws atY+/-15.5. Heat-set short inserts before fitting. Fore skins use existing rear spine. Remove skins before servicing clamps/native screws; real preload and tools must be tested.',physical_assembly_qualified=False,production_release=False),indent=2)+'\n')
    review('skins06',tools)

if __name__=='__main__':main()
