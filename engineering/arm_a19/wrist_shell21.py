# SPDX-License-Identifier: CC-BY-NC-4.0
"""Removable curved hard carapace on actual RS03: two parts, four screws."""
from pathlib import Path
import json,sys,math
import numpy as np
import cadquery as cq
import trimesh
from scipy.spatial.transform import Rotation
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/wrist-shell21'
sys.path.insert(0,str(HERE));import wrist16 as w
sys.path.insert(0,str(ROOT/'engineering/arm_a17'));import style01 as style
c=w.c;g=c.cad

def main():
    corepath=HERE/'build/wrist-core19/manifest.json';core=json.loads(corepath.read_text());review=json.loads((corepath.parent/'review20.json').read_text())
    core_verified=review['changed_pair_sampled_clear'] and review['source_sha256'][str(corepath.relative_to(ROOT))]==c.sha(corepath)
    if '--construction-only' not in sys.argv:assert core_verified
    for folder in ['step','stl-object','print-bed']:(OUT/folder).mkdir(parents=True,exist_ok=True)
    inf=core['motor_interface'];n,u,v=[np.array(inf[k],float) for k in ['n','u','v']];p=np.array(inf['out_mm']);T=np.eye(4);T[:3,:3]=np.column_stack([n,u,v]);T[:3,3]=p
    parts=[];meshes=[]
    def add(id,s,role,owner=4,frame='J5.fixed'):
        s=s.fix();assert s.isValid() and len(s.Solids())==1,(id,len(s.Solids()))
        vs,ts=s.tessellate(.04,.1);m=trimesh.Trimesh([a.toTuple() for a in vs],ts,process=True);assert m.is_watertight and m.is_winding_consistent and m.volume>0,id
        step=OUT/'step'/(id+'.step');cq.exporters.export(s,str(step));m.export(OUT/'stl-object'/(id+'.stl'))
        row=dict(id=id,owner=owner,frame=frame,role=role,material='PETG/PA12 supported unpowered fit' if role=='printed_cover' else 'purchased steel nominal envelope',volume_mm3=s.Volume(),mass_kg=s.Volume()*(1.27e-6 if role=='printed_cover' else 7.85e-6),com_mm=list(s.Center().toTuple()),step_path=str(step.relative_to(ROOT)),step_sha256=c.sha(step))
        if role=='printed_cover':
            direction=v*(1 if id.endswith('-a') else -1);R=Rotation.align_vectors([[0,0,1]],[direction])[0].as_matrix();bed=m.copy();bed.vertices=bed.vertices@R.T;shift=-bed.bounds[0];bed.apply_translation(shift);bed.export(OUT/'print-bed'/(id+'.stl'));assert max(bed.extents)<250
            row.update(print_rotation=R.tolist(),print_translation_mm=shift.tolist(),print_size_mm=bed.extents.tolist(),print_stl_sha256=c.sha(OUT/'print-bed'/(id+'.stl')))
        parts.append(row);meshes.append(dict(row,vertices_mm=m.vertices.tolist(),triangles=m.faces.tolist()));return row
    stations=[(-62,55,53),(-53,57,55),(-34,58,57),(-5,65,63),(-3,65,63)]
    outer=cq.Solid.extrudeLinear(style.wire(6,65,63),[],cq.Vector(3,0,0))
    for label,sign in [('a',1),('b',-1)]:
        shell=style.curved(stations,0,sign,ruled=True).fuse(style.cap((-62,55,53),sign)).fix()
        for mount in core['cover_mounts']:
            angle=mount['angle_deg'];a=math.radians(angle)
            if math.sin(a)*sign<0:continue
            radial=np.array([math.cos(a),math.sin(a)]);tangent=np.array([-radial[1],radial[0]])
            polygon=[radial*x+tangent*y for x,y in [(53,-5),(85,-5),(85,5),(53,5)]]
            tab=cq.Workplane(g.plane([6,0,0],[1,0,0])).polyline([q.tolist() for q in polygon]).close().extrude(3).val().intersect(outer)
            strip=cq.Workplane(g.plane([-4,0,0],[1,0,0])).polyline([q.tolist() for q in polygon]).close().extrude(13).val()
            half=cq.Solid.makeBox(30,200,100,g.V([-10,-100,0 if sign>0 else -100]))
            tab=tab.intersect(half)
            patch=style.curved([(-4,65,63),(9,65,63)],0,sign,ruled=True).intersect(strip).intersect(half)
            shell=shell.fuse(tab,patch).fix();shell=g.drill(shell,[5.9,57*math.cos(a),57*math.sin(a)],[1,0,0],3.5,3.2)
            # Ordinary1mm counterbore retains2mm floor. Low head projects
            #1.5mm; do not thicken the whole tab into the yaw cowl sweep.
            shell=g.drill(shell,[8,57*math.cos(a),57*math.sin(a)],[1,0,0],7.4,1.1)
        # Actual rear service opening, enlarged for connector measurement.
        shell=shell.cut(cq.Solid.makeBox(12,26,18,g.V([-69,-13,-9]))).fix()
        shell=c.transform(shell,T)
        # Fore shell and new fixed bracket are on the same rigid side of J5.
        # Transfer only their real local assembly geometry plus0.5mm reserves.
        old=json.loads((ROOT/'engineering/arm_a18/build/assembly12.json').read_text())
        obstacles=[q for q in core['parts'] if q['id']=='A19-S19-fore-spine-RS03-ring']
        # Fore skin is planar-trimmed toX119; this native cowl startsX120.
        # Do not rely on unstable thin-loft booleans to form this junction.
        print('SHELL21_PRECUT',label,[(s.Volume(),w.r.bounds(s)) for s in shell.Solids()],flush=True)
        for entry in obstacles:
            obstacle=w.r.load(ROOT/entry['step_path']).translate((-185,-62,0))
            for delta in [(0,0,0),(.5,0,0),(-.5,0,0),(0,.5,0),(0,-.5,0),(0,0,.5),(0,0,-.5)]:
                before=np.array(w.r.bounds(shell));volume=shell.Volume();candidate=shell.cut(obstacle.translate(delta)).fix()
                after=np.array(w.r.bounds(candidate));assert candidate.Volume()<=volume+1e-3 and np.all(after[:3]>=before[:3]-1e-3) and np.all(after[3:]<=before[3:]+1e-3)
                shell=candidate
            print('SHELL21_CUT',label,entry['id'],[(s.Volume(),w.r.bounds(s)) for s in shell.Solids()],flush=True)
        add('A19-C21-J5-cowl-'+label,shell,'printed_cover')
    for i,mount in enumerate(core['cover_mounts'],1):
        # Fixed plate reference is local J5, not the forearm parent frame.
        q=np.array(mount['p_mm'])-[185,62,0];bearing=q+n*11
        start=q-n*5;bolt=g.cyl(start,n,1.5,16).fuse(g.cyl(bearing,n,2.75,2)).fix()
        tool=cq.Workplane(g.plane(bearing+n*2.1,-n)).polygon(6,2/math.cos(math.pi/6)).extrude(1.5).val();bolt=bolt.cut(tool).fix()
        key=f'A19-H21-J5-cover-{i}';add(key,bolt,'hardware')
        add(key+'-washer',g.ring(q+n*10.5,n,3.5,1.6,.5),'hardware')
        add(key+'-spacer',g.ring(q+n*8,n,3.5,1.6,.5),'hardware')
        nut=cq.Workplane(g.plane(q-n*2.4,n)).polygon(6,5.5/math.cos(math.pi/6)).extrude(2.4).val();nut=g.drill(nut,q-n*2.5,n,3,2.6);add(key+'-nut',nut,'hardware')
    result=dict(revision='A19-RS03-SHELL21',layout=core['layout'],base_context=c.base_context(),source_core_sha256=c.sha(corepath),parts=parts,replaces_only=[],core_replacement_manifest=str(corepath.relative_to(ROOT)),assembly='First bolt native motor/brackets and torque-test fasteners with external support. Then four captive-access M3 nuts,0.5mm spacers and the two halves. M3x16 +11.5mm grip +.5mm washer leaves4mm behind plate,2.4mm nut plus1.6mm projection. No glue or tapped plastic.',rear_service_window_mm=[26,18],nominal_shell_wall_mm=2.6,front_bezel='Native structural ring remains visible; no cosmetic face across J6 sweep. Cover mounts confined to unswept rear sector145/165/185/195deg.',collision_and_tool_qualified=False,production_release=False)
    result['core_review_current_at_construction']=core_verified
    result['front_bezel']='Native structural ring remains visible; no cosmetic face across J6 sweep. Cover stations145/165/185/195deg.'
    result['assembly']='Four DIN7984 M3x16 nominalD5.5 headH2 AF2 inD7.4 depth1 tabs. Head projects1.5mm above3mm tab; tab floor2mm. 10.5mm grip +0.5mm washer leaves5mm behind plate, M3 nut2.4 plus2.6mm tip. Test printed clamp retention.'
    result['fastener_source']='https://www.bossard.com/us-en/eshop/screws-and-bolts-with-internal-drive/hex-socket-head-cap-screws-with-low-head-partially-fully-threaded/p/2844/'
    (OUT/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');(OUT/'meshes.json').write_text(json.dumps(meshes,separators=(',',':'))+'\n');print('SHELL21',len(parts),flush=True)
if __name__=='__main__':main()
