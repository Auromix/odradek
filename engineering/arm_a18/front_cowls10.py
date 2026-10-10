# SPDX-License-Identifier: CC-BY-NC-4.0
"""Integral front shields on four removable J3/J4 cowls; no added mechanism."""
from pathlib import Path
import json,sys,math,itertools
import numpy as np
import cadquery as cq
import trimesh
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/front-cowls10'
sys.path.insert(0,str(ROOT/'engineering/arm_a16'))
import common as c
import skeleton_review as r
from assembly_sources import collect
from vendor import interfaces
from hardware01 import points as native_hole_offsets
sys.path.insert(0,str(ROOT/'engineering/arm_a17'))
import style01 as style

def main():
    for folder in ['step','stl-object','print-bed']:(OUT/folder).mkdir(parents=True,exist_ok=True)
    a17path=ROOT/'engineering/arm_a17/build/style01/manifest.json';a17=json.loads(a17path.read_text())
    inherited=ROOT/'engineering/arm_a17/build/style01/review.json';prior=json.loads(inherited.read_text());assert prior['sampled_clear']
    for path,h in prior['source_sha256'].items():assert c.sha(ROOT/path)==h,path
    contactpath=HERE/'build/contacts09/manifest.json';contacts=json.loads(contactpath.read_text());assert contacts['review']['sampled_clear']
    current,sources,_=collect(last='skins06');current=[p for p in current if p['id'] not in a17['replaces_only']]+[dict(p,step_path=str((a17path.parent/'step'/(p['id']+'.step')).relative_to(ROOT))) for p in a17['parts']]
    current=[p for p in current if p['id'] not in contacts['replaces_only']]
    fixture=lambda p:p['role'] in ['fit_fixture','working_pin_envelope'] or '-tool-' in p['id']
    current.extend(p for p in contacts['parts'] if not fixture(p))
    assert len(current)==556
    sources.update({str(p.relative_to(ROOT)):c.sha(p) for p in [a17path,inherited,contactpath]})
    for p in current:sources[p['step_path']]=c.sha(ROOT/p['step_path'])
    replacements=[];parts=[];meshes=[];g=c.cad;I={x['joint']:x for x in interfaces()}
    for joint in ['J3','J4']:
        inf=I[joint];n,u,v=[np.array(inf[k]) for k in ['n','u','v']];p=np.array(inf['out_mm'])
        T=np.eye(4);T[:3,:3]=np.column_stack([n,u,v]);T[:3,3]=p
        if joint=='J4':T[:3,3]+=[340,0,0]
        ru=70 if joint=='J3' else 71;rv=69
        # Integral2.6mm face, same corner curvature and same split as current
        # shell. InnerD100 leaves the rotating adapter area open; four ports
        # retain original cover screw heads and tool access at unchanged seats.
        front_start=10.7 if joint=='J4' else 12.8
        face=cq.Solid.extrudeLinear(style.wire(front_start,ru,rv),[],cq.Vector(15.4-front_start,0,0))
        face=face.cut(g.cyl([front_start-.1,0,0],[1,0,0],50,15.5-front_start))
        if joint=='J4':
            for offset in native_hole_offsets(inf,'fixed_front_fasteners'):
                face=face.cut(g.cyl([10.6,float(offset@u),float(offset@v)],[1,0,0],3.9,2.2))
        start=8.4 if joint=='J3' else 11.4
        outer=style.wire(start,ru,rv);inner=style.wire(start,ru,rv,inset=2.6)
        lip=cq.Solid.extrudeLinear(outer,[inner],cq.Vector(12.9-start,0,0));face=face.fuse(lip).fix()
        for angle in [45,135,225,315]:
            h=np.radians(angle);access_start=min(start,front_start)-.1
            face=g.drill(face,[access_start,64*np.cos(h),64*np.sin(h)],[1,0,0],7.6,15.5-access_start)
        for label,sign in [('a',1),('b',-1)]:
            old=f'A17-C04-{joint}-cowl-{label}';row=next(x for x in current if x['id']==old);s=r.load(ROOT/row['step_path'])
            half=cq.Solid.makeBox(9,200,100,g.V([8,-100,.25 if sign==1 else -100.25]))
            addition=c.transform(face.intersect(half),T);new=s.fuse(addition).clean().fix()
            if joint=='J4':new=style.plate_clearance(new,old)
            if joint=='J4':
                # Ordinary curved slots clear the existing long M4 tips over
                # J4's permitted rotation, rather than silently shortening
                # purchased bolts or moving their fastening stack.
                for radius in [60,70]:
                    slot=g.ring([13.45,0,0],[1,0,0],radius+2.5,radius-2.5,2.05)
                    # Retain the unswept74-degree rear sector as a real bridge.
                    keep=cq.Workplane(g.plane([13.35,0,0],[1,0,0])).polyline([[0,0],[150*np.cos(np.radians(138)),150*np.sin(np.radians(138))],[150*np.cos(np.radians(212)),150*np.sin(np.radians(212))]]).close().extrude(2.3).val()
                    slot=slot.cut(keep)
                    for a in [-148,138]:
                        slot=slot.fuse(g.cyl([13.45,radius*np.cos(np.radians(a)),radius*np.sin(np.radians(a))],[1,0,0],2.5,2.05))
                    new=new.cut(c.transform(slot,T)).fix()
            if joint=='J3':
                # Carry ordinary connection/service reliefs across the newly
                # extended front lip. J2 remains unchanged: its front mask
                # cannot fit the adjacent J3 shell at the current lateral gap.
                new=new.cut(cq.Solid.makeBox(40,40,38,g.V([24,50,-19]))).fix()
                new=new.cut(cq.Solid.makeBox(40,180,30,g.V([24,-90,-95.5]))).fix()
                # J2 cover-head sweep lies at localY>=68.5. This front edge
                # relief leaves0.7mm nominal axial separation, preserves all
                # four J3 fixing ears, and is an actual printed opening.
                new=new.cut(cq.Solid.makeBox(20,30,180,g.V([36.2,67.8,-90]))).fix()
                plate=r.load(c.OUT/'cowls04/step/A16-C04-J2-mount-plate.step')
                for angle in [-60,110]:
                    q=c.L['poses']['reference'].copy();q[1]=angle;F=c.frames(q)
                    obstacle=c.transform(plate,np.linalg.inv(F['J3.fixed'])@F['J1.rotor'])
                    new=new.cut(obstacle).fix()
                    for axis in range(3):
                        for sign_delta in [-1,1]:
                            delta=[0.,0.,0.];delta[axis]=sign_delta*.5
                            new=new.cut(obstacle.translate(tuple(delta))).fix()
            if len(new.Solids())!=1:
                debug=ROOT/'work/arm-a18/front10-disconnected.step';debug.parent.mkdir(parents=True,exist_ok=True);cq.exporters.export(new,str(debug))
                print('DISCONNECTED',old,[(s.Volume(),r.bounds(s)) for s in new.Solids()],flush=True)
            assert new.isValid() and len(new.Solids())==1,(old,len(new.Solids()))
            id=old.replace('A17','A18');step=OUT/'step'/(id+'.step');cq.exporters.export(new,str(step))
            vs,fs=new.tessellate(.05,.12);m=trimesh.Trimesh(vertices=[x.toTuple() for x in vs],faces=fs,process=True)
            assert m.is_watertight and m.is_winding_consistent and m.volume>0
            m.export(OUT/'stl-object'/(id+'.stl'))
            # Keep the inherited radial split-plane bed convention. Supports
            # on face lip/seat must be checked in slicer before printing.
            from scipy.spatial.transform import Rotation
            R=Rotation.align_vectors([[0,0,1]],[v*sign])[0].as_matrix();assert abs(np.linalg.det(R)-1)<1e-9
            bed=m.copy();bed.vertices=bed.vertices@R.T;shift=-bed.bounds[0];bed.apply_translation(shift);bed.export(OUT/'print-bed'/(id+'.stl'))
            assert max(bed.extents)<250
            q=dict(id=id,owner=row['owner'],frame=row['frame'],role='printed_cover',material='PETG/PA12 supported unpowered fit',
              volume_mm3=new.Volume(),mass_kg=new.Volume()*1.27e-6,com_mm=list(new.Center().toTuple()),
              step_path=str(step.relative_to(ROOT)),step_sha256=c.sha(step),print_stl_sha256=c.sha(OUT/'print-bed'/(id+'.stl')),
              print_rotation=R.tolist(),print_translation_mm=shift.tolist(),print_size_mm=bed.extents.tolist(),
              added_mass_kg=(new.Volume()-s.Volume())*1.27e-6,
              vertices_mm=m.vertices.tolist(),triangles=m.faces.tolist())
            meshes.append(q);parts.append({k:z for k,z in q.items() if k not in ['vertices_mm','triangles']});replacements.append(old)
    newitems=[(p,r.load(ROOT/p['step_path'])) for p in parts]
    unchanged=[p for p in current if p['id'] not in replacements];items=newitems+[(p,r.load(ROOT/p['step_path'])) for p in unchanged]
    vendor=json.loads((c.OUT/'vendor-audit.json').read_text())
    for motor in vendor['motors']:
        for tag,fr in [('stator','fixed'),('external-output','rotor')]:
            fp=c.CACHE/'vendor'/(motor['joint']+'-'+tag+'.step');assert c.sha(fp)==motor['cache_step_sha256'][tag]
            items.append((dict(id=motor['joint']+'-'+tag,frame=motor['joint']+'.'+fr),r.load(fp)))
    poses=[dict(name=x['sample'],q=x['q_deg'],inherited_unchanged_pair_review=True) for x in prior['checks']]
    # Extra5-degree sweeps only qualify newly changed covers in these paths.
    # Unchanged pairs in extra samples do NOT inherit the26-pose old review.
    for index in [1,2,3]:
        lo,hi=c.L['joints'][index]['limits_deg']
        for value in np.linspace(lo,hi,math.ceil((hi-lo)/5)+1):
            q=c.L['poses']['reference'].copy();q[index]=float(value)
            poses.append(dict(name=f'J{index+1}-front-sweep-{value:.2f}',q=q,inherited_unchanged_pair_review=False))
    cache={};hits=[];checks=[]
    for pose in poses:
        F=c.frames(pose['q']);world=[(p,c.transform(s,F[p['frame']])) for p,s in items]
        boxes=np.array([r.bounds(s) for p,s in world]);lo=boxes[:,:3];hi=boxes[:,3:]
        broad=np.all((hi[:,None,:]>lo[None,:,:]+1e-5)&(hi[None,:,:]>lo[:,None,:]+1e-5),axis=2);mask=np.triu(broad,1);mask[len(newitems):,:]=False
        candidates=np.argwhere(mask);fresh=0;count=0
        for i,j in candidates:
            p,s=world[i];t,w=world[j];rel=np.linalg.inv(F[p['frame']])@F[t['frame']]
            key=(p['id'],t['id'],tuple(np.round(rel,8).flat))
            if key not in cache:cache[key]=r.common_volume(s,w);fresh+=1
            if cache[key]>.08:
                hits.append(dict(sample=pose['name'],a=p['id'],b=t['id'],volume_mm3=cache[key]));count+=1
        checks.append(dict(sample=pose['name'],q_deg=pose['q'],positive_bbox_pairs=len(candidates),fresh_exact_pairs=fresh,hits=count,inherited_unchanged_pairs=pose['inherited_unchanged_pair_review']))
        if fresh or count:print('FRONT10_CHECK',pose['name'],fresh,'hits',count,flush=True)
    report=dict(revision='A18-FRONT-COWLS10',layout=c.L,base_context=c.base_context(),sources=sources,replaces_only=replacements,parts=parts,
      inherited_screw_stations='FourR64 stations per motor, unchanged tab seats at local axial8..11; M3x16 hardware retained; D7.6 access through new face.',
      face_parameters=dict(J3_axial_span_from_output_mm=[12.8,15.4],J4_axial_span_from_output_mm=[10.7,15.4],J4_front_blind_groove_floor_mm=2.75,J4_native_head_back_pocket_end_axial_mm=12.8,J3_nominal_face_thickness_mm=2.6,rotating_opening_D_mm=100,access_D_mm=7.6,J2_front_mask_omitted='Cannot fit adjacent J3 shell with current15mm lateral offset. ExistingJ2 shell retained, not suppressed in rendering.'),
      total_added_mass_kg=sum(p['added_mass_kg'] for p in parts),checks=checks,hits=hits,exact_distinct_pairs=len(cache),changed_pair_sampled_clear=not hits,
      scope='Four changed J3/J4 cowls vs current own assembly and14 supplier partitions.26 old samples plus three5-degree single-joint reference paths. Full base shell, unchanged pairs in new paths, wires, tolerance and continuous motion not qualified.',
      production_release=False)
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');(OUT/'meshes.json').write_text(json.dumps(meshes,separators=(',',':'))+'\n')
    print('FRONT10_DONE',len(poses),'poses',len(hits),'hits',flush=True)
    if hits:raise RuntimeError('Front10 failed; do not issue print kit')

if __name__=='__main__':main()
