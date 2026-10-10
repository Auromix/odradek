# SPDX-License-Identifier: CC-BY-NC-4.0
"""Conventional native RS03/J6 brackets: no added gearing or cable bore."""
from pathlib import Path
import json,sys,math
import numpy as np
import cadquery as cq
import trimesh
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/wrist-core19'
sys.path.insert(0,str(HERE));import wrist16 as w
from hardware01 import points
c=w.c;g=c.cad
L=json.loads((HERE/'build/wrist16-offset75/native-fit.json').read_text())['layout']

def box(p,size):return cq.Solid.makeBox(*size,g.V(p))
def main():
    for name in ['step','stl-object','print-bed']:(OUT/name).mkdir(parents=True,exist_ok=True)
    source=ROOT/'engineering/arm_a18/build/assembly12.json';old=json.loads(source.read_text());rows=old['parts'];parts=[];meshes=[];screws=[]
    inf=w.interface();n=np.array(inf['n']);p=np.array(inf['out_mm']);fixed=np.array(inf['fixed_mm'])
    def load(id):return w.r.load(ROOT/next(p for p in rows if p['id']==id)['step_path'])
    def add(id,s,owner,frame,role='printed_structure',note=''):
        s=s.fix();assert s.isValid() and len(s.Solids())==1,(id,len(s.Solids()))
        vs,ts=s.tessellate(.045,.1);m=trimesh.Trimesh([v.toTuple() for v in vs],ts,process=True)
        assert m.is_watertight and m.is_winding_consistent and m.volume>0,id
        step=OUT/'step'/(id+'.step');cq.exporters.export(s,str(step));m.export(OUT/'stl-object'/(id+'.stl'))
        entry=dict(id=id,owner=owner,frame=frame,role=role,material='PETG/PA12 supported fit' if role.startswith('printed') else 'purchased steel nominal envelope',volume_mm3=s.Volume(),mass_kg=s.Volume()*(1.27e-6 if role.startswith('printed') else 7.85e-6),com_mm=list(s.Center().toTuple()),step_path=str(step.relative_to(ROOT)),step_sha256=c.sha(step),note=note)
        if role.startswith('printed'):
            # Split functional mounting plane laid on its back; exact rotation
            # is recorded. Holes and tool channels require slicer support QA.
            R=np.array([[1,0,0],[0,0,1],[0,-1,0]],float);bed=m.copy();bed.vertices=bed.vertices@R.T;shift=-bed.bounds[0];bed.apply_translation(shift);bed.export(OUT/'print-bed'/(id+'.stl'))
            assert max(bed.extents)<250
            entry.update(print_rotation=R.tolist(),print_translation_mm=shift.tolist(),print_size_mm=bed.extents.tolist(),print_stl_sha256=c.sha(OUT/'print-bed'/(id+'.stl')))
        parts.append(entry);meshes.append(dict(entry,vertices_mm=m.vertices.tolist(),triangles=m.faces.tolist()));return entry
    def drill_native(s,kind,origin,th):
        for delta in points(inf,kind):s=g.drill(s,origin+delta-n*.1,n,4.5,th+.2)
        return s
    # Existing tube socket, transverse fasteners and long shell support pads
    # retained. Replace the old small ring and its four insert mount stations.
    off=np.array([185,62,0]);s=load('A16-C06-fore-spine-and-J5-ring')
    s=s.cut(box([151.5,89,-40],[70,25,80])).fix()
    ring=g.ring(fixed+off,n,61,35.2,8);ring=drill_native(ring,'fixed_front_fasteners',fixed+off,8)
    s=s.fuse(ring).fix()
    s=s.cut(g.cyl(fixed+off-n*.1,n,35.6,30.2)).fix()
    # Small raised seal above the native flat front face: ordinary shallow
    # circular relief, not a shifted mating plane or fictitious stand-off.
    s=s.cut(g.cyl(fixed+off-n*.1,n,45.1,.7)).fix()
    for delta in points(inf,'fixed_front_fasteners'):
        # Axial head and hex service access with the body unpowered and
        # upstream covers removed; no sculpted motor/cable shortcuts.
        s=g.drill(s,fixed+off+delta+n*8,n,9.5,28)
    mounts=[]
    for angle in [45,135,225,315]:
        t=math.radians(angle);q=fixed+off+np.array([57*math.cos(t),0,57*math.sin(t)])
        s=g.drill(s,q-n*.1,n,3.5,8.2);mounts.append(dict(angle_deg=angle,p_mm=q.tolist(),normal=n.tolist(),radius_mm=57))
    add('A19-S19-fore-spine-RS03-ring',s,4,'J4.rotor',note='Stock tube/socket and C06 fore shell seats retained; native RS03 eight M4 holes and R57 cover stations; no plastic tapped load threads.')
    # Keep actual J6 flange/support pads and move it20mm. A straight L leg
    # connects a native D70 output plate to that unchanged J6 mount.
    existing=load('A16-C05-J6-mount-plate')
    right=existing.intersect(box([21,-100,-100],[150,200,200])).translate((20,0,0))
    disc=g.cyl(p,n,35,10)
    vertical=box([-15,22,-36.8],[33,5,40.8])
    horizontal=box([15,22,-36.8],[93,5,8])
    join=box([-15,22,-20],[33,10,6])
    s=disc.fuse(vertical,horizontal,right,join).fix();s=drill_native(s,'output_fasteners',p,10)
    for delta in points(inf,'output_fasteners'):s=g.drill(s,p+delta+n*10,n,9.5,25)
    from vendor import interfaces
    J6=interfaces()[5];n6=np.array(J6['n']);p6=np.array(J6['fixed_mm'])+[75,0,0]
    for delta in points(J6,'fixed_front_fasteners'):
        s=g.drill(s,p6+delta-n6*3.3,n6,4.5,11.5)
        s=g.drill(s,p6+delta+n6*8,n6,9.5,38)
    for entry in rows:
        if entry.get('intentional_heatset_target')=='A16-C05-J6-mount-plate':
            z=entry['heatset_zone_mm'];q=np.array(z['p'])+[20,0,0];normal=np.array(z['n'])
            s=g.drill(s,q-normal*3.4,normal,3.5,z['length']+3.6)
            s=g.drill(s,q-normal*.1,normal,4,z['length']+.2)
    # Old translated right-hand piece contains no old J5 disc/native holes;
    # the original J6 ring and four insert seats remain exact geometry.
    add('A19-S19-RS03-to-J6-L',s,5,'J5.rotor',note='Native D70 output contact plate, ordinary straight L legs; J6 moves55→75mm. J6 four heat-set pilots remain unchanged locally.')
    for kind,origin,grip,length,depth,owner,frame in [('fixed_front_fasteners',fixed,8,14,8,4,'J5.fixed'),('output_fasteners',p,10,16,6,5,'J5.rotor')]:
        for index,delta in enumerate(points(inf,kind),1):
            pos=origin+delta;insertion=length-grip-.8;assert 0<insertion<depth-.4
            bearing=pos+n*(grip+.8);start=pos-n*insertion
            bolt=g.cyl(start,n,2,length).fuse(g.cyl(bearing,n,3.5,4)).fix()
            tool=cq.Workplane(g.plane(bearing+n*4.1,-n)).polygon(6,3/math.cos(math.pi/6)).extrude(1.6).val();bolt=bolt.cut(tool).fix()
            prefix=f'A19-H19-J5-{kind.split("_")[0]}-{index}'
            e=add(prefix,bolt,owner,frame,'hardware');e['intentional_thread_motor']='J5';e['thread_zone_mm']=dict(p=pos.tolist(),n=n.tolist(),depth=insertion,diameter=4.02)
            add(prefix+'-washer',g.ring(pos+n*grip,n,4.5,2.2,.8),owner,frame,'hardware')
            screws.append(dict(id=prefix,description=f'ISO4762 M4x{length}',mount_origin_mm=pos.tolist(),normal=n.tolist(),grip_mm=grip,washer_mm=.8,insertion_mm=insertion,source_depth_mm=depth))
    replaced=[p['id'] for p in rows if p['id'].startswith('A16-H-J5-') or p['id'].startswith('A16-C05-H-J5-') or p['id'] in ['A16-C06-fore-spine-and-J5-ring','A16-C05-J6-mount-plate','A17-C05-J5-cowl-a','A17-C05-J5-cowl-b']]
    # Covers and their fasteners are absent from this core-only study, not
    # presented as a complete body. Reposition four existing J6 heatsets.
    heatsets=[]
    for pold in rows:
        if pold.get('intentional_heatset_target')=='A16-C05-J6-mount-plate':
            oldshape=load(pold['id']);entry=add(pold['id']+'-X75',oldshape.translate((20,0,0)),pold['owner'],pold['frame'],'hardware')
            entry['intentional_heatset_target']='A19-S19-RS03-to-J6-L';z=dict(pold['heatset_zone_mm']);z['p']=(np.array(z['p'])+[20,0,0]).tolist();entry['heatset_zone_mm']=z
            replaced.append(pold['id']);heatsets.append(entry['id'])
        elif pold['id'].startswith('A16-C05-H-J6-'):
            entry=add(pold['id']+'-X75',load(pold['id']).translate((20,0,0)),pold['owner'],pold['frame'],'hardware')
            replaced.append(pold['id'])
    # Small real clearance cut in the adjacent forearm dorsal skin. It has
    # no motor-scaling or render-only masking; retain its fixing seats.
    oldcover='A17-C06-fore-dorsal';cover=load(oldcover)
    obstacle=load('A16-C06-fore-spine-and-J5-ring')
    obstacle=w.r.load(OUT/'step/A19-S19-fore-spine-RS03-ring.step')
    for delta in [(0,0,0),(.5,0,0),(-.5,0,0),(0,.5,0),(0,-.5,0),(0,0,.5),(0,0,-.5)]:cover=cover.cut(obstacle.translate(delta)).fix()
    add('A19-C19-fore-dorsal',cover,4,'J4.rotor','printed_cover',note='Same A17 exterior and cover fixings; local RS03 bracket clearance reserve0.5mm axis offsets, not a full tolerance qualification.')
    replaced.append(oldcover)
    budget=[dict(id=p['id'],owner=p['owner'],frame=p['frame'],mass_kg=p['mass_kg'],com_mm=p['com_mm']) for p in rows if p['id'] not in replaced]
    budget.extend(dict(id=p['id'],owner=p['owner'],frame=p['frame'],mass_kg=p['mass_kg'],com_mm=p['com_mm']) for p in parts)
    for owner,mass,com in [(3,.1,[170,0,11]),(4,.08,[92.5,62,11]),(7,.06,[65,0,0]),(2,.25,[45,-80,0]),(4,.15,[185,130,0])]:budget.append(dict(id=f'allowance-{owner}-{mass}',owner=owner,frame=f'J{owner}.rotor',mass_kg=mass,com_mm=com))
    q=np.array(list(L['poses'].values())+[[j['limits_deg'][0]+w.f.rs.halton(k,b)*(j['limits_deg'][1]-j['limits_deg'][0]) for j,b in zip(L['joints'],[2,3,5,7,11,13,17])] for k in range(1,4097)],float)
    t=w.f.torque(L,q,3,budget)
    report=dict(revision='A19-WRIST-CORE19',layout=L,base_context=c.base_context(),source_assembly_sha256=c.sha(source),motor_interface=inf,parts=parts,replaces_only=sorted(set(replaced)),cover_mounts=mounts,screw_stacks=screws,refreshed_J6_heatsets=heatsets,sampled_static_max_Nm=np.max(abs(t),axis=0).tolist(),static_sample_count=len(q),undeveloped_cowl_allowance_kg=.15,motor_zero_speed_reference_Nm=[13,28.5,28.5,28.5,13,9.5,3.6],scope='Core-only candidate. Missing J5 cowls/mount hardware; old J6 cover hardware must move with new local seats. All changed-part collision/tool/print checks pending.',production_release=False)
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');(OUT/'meshes.json').write_text(json.dumps(meshes,separators=(',',':'))+'\n')
    print('WRIST19',len(parts),report['sampled_static_max_Nm'],flush=True)
if __name__=='__main__':main()
