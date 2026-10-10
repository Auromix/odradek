# SPDX-License-Identifier: CC-BY-NC-4.0
"""IF09 supported, unpowered contact-panel and compression-gauge CAD, mm."""
from pathlib import Path
import csv, json, sys, itertools
import numpy as np
import cadquery as cq
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/contacts09'
sys.path.insert(0,str(ROOT/'engineering/arm_a16'))
import common as c
import skeleton_review as r
from assembly_sources import collect
g=c.cad

def box(p,s):return cq.Solid.makeBox(*s,cq.Vector(*p))
def hexhole(p,L,af=5.2):return cq.Workplane(g.plane(p,[1,0,0])).polygon(6,af/np.cos(np.pi/6)).extrude(L).val()
def mesh(s):
    v,f=s.tessellate(.05,.12);return trimesh.Trimesh(vertices=[x.toTuple() for x in v],faces=f,process=True)
def clean(s):
    s=s.clean().fix();assert s.isValid() and len(s.Solids())==1;return s

def main():
    for folder in ['step','stl-object','print-bed']:(OUT/folder).mkdir(parents=True,exist_ok=True)
    base=c.base_context();sources={};printed=[];rows=[];shapes={}
    def add(id,s,role,material,printable=False):
        s=clean(s);shapes[id]=s;m=mesh(s);assert m.is_watertight and m.is_winding_consistent and m.volume>0
        path=OUT/'step'/(id+'.step');cq.exporters.export(s,str(path));obj=OUT/'stl-object'/(id+'.stl');m.export(obj)
        p=dict(id=id,owner=7,frame='J7.rotor',role=role,material=material,volume_mm3=s.Volume(),com_mm=list(s.Center().toTuple()),
          bbox_mm=m.bounds.tolist(),step_path=str(path.relative_to(ROOT)),step_sha256=c.sha(path),stl_object_sha256=c.sha(obj),
          vertices_mm=m.vertices.tolist(),triangles=m.faces.tolist(),production_release=False)
        if printable:
            R=np.array([[0,1,0],[0,0,1],[1,0,0]],float);assert np.linalg.det(R)==1
            bed=m.copy();bed.vertices=bed.vertices@R.T;T=-bed.bounds[0];bed.apply_translation(T)
            fp=OUT/'print-bed'/(id+'.stl');bed.export(fp);reloaded=trimesh.load(fp,force='mesh')
            edges=np.sort(reloaded.edges,axis=1);n=len(reloaded.vertices)
            graph=coo_matrix((np.ones(len(edges)*2),(np.r_[edges[:,0],edges[:,1]],np.r_[edges[:,1],edges[:,0]])),shape=(n,n))
            components=connected_components(graph,directed=False,return_labels=False)
            assert components==1 and reloaded.is_watertight and reloaded.is_winding_consistent and reloaded.volume>0
            assert max(reloaded.extents)<250 and abs(reloaded.bounds[0,2])<1e-5
            p.update(print_bed_sha256=c.sha(fp),print_rotation=R.tolist(),print_translation_mm=T.tolist(),print_size_mm=reloaded.extents.tolist(),connected_components=components)
            printed.append(id)
        rows.append(p);return p
    # Same service screws at Y +/-29, same Ø52 insert and same mechanical
    # flange. Only the old PWR/CTRL windows become a removable pad-board seat.
    panel=g.cyl([103,0,0],[1,0,0],26,3)
    for y in [-29,29]:
        panel=panel.fuse(g.cyl([103,y,0],[1,0,0],4,3))
        panel=g.drill(panel,[102.9,y,0],[1,0,0],3.5,3.2)
    for y in [-9,9]:panel=panel.cut(box([102.9,y-5.8,-17.8],[3.2,11.6,11.6]))
    panel=panel.cut(box([104.4,-17.2,-.2],[1.7,34.4,18.4]))
    for y in [-14,14]:
        panel=panel.fuse(g.cyl([100,y,9],[1,0,0],4.5,4.4))
        panel=g.drill(panel,[99.9,y,9],[1,0,0],2.7,6.2)
        panel=panel.cut(hexhole([99.9,y,9],2.3))
    panel=panel.cut(box([99.9,-5,7.5],[4.6,10,3]))
    add('A18-IF09-101-contact-insert',panel,'printed_structure','PETG/PA12 supported unpowered fit only',True)
    # Tool-side gauge is a replaceable test fixture, never the actual head.
    gauge=g.ring([110,0,0],[1,0,0],43,27,4.6)
    gauge=gauge.cut(g.ring([109.9,0,0],[1,0,0],38.1,27,2.3))
    bridge=box([112.2,-38,0],[2.4,76,20]).intersect(g.cyl([112.2,0,0],[1,0,0],43,2.4))
    gauge=gauge.fuse(bridge)
    for y in [-14,14]:
        gauge=gauge.fuse(g.cyl([111.6,y,3],[1,0,0],4.5,.6))
        gauge=g.drill(gauge,[111.5,y,3],[1,0,0],2.7,3.2)
        gauge=gauge.cut(hexhole([112.4,y,3],2.3))
    for k in range(4):
        a=np.radians(45+90*k);gauge=g.drill(gauge,[109.9,36*np.cos(a),36*np.sin(a)],[1,0,0],4.5,4.8)
    gauge=g.drill(gauge,[109.9,0,31],[1,0,0],3.3,4.8)
    add('A18-IF09-102-tool-distance-gauge',gauge,'fit_fixture','PETG/PA12 test fixture, no tool load',True)
    def board(id,x,th,mount_z):
        s=box([x,-17,0],[th,34,18])
        for y in [-14,14]:s=g.drill(s,[x-.1,y,mount_z],[1,0,0],2.8,th+.2)
        return add(id,s,'PCB_geometry_only','Finished board1.6mm assumption; no routing/Gerbers or fabrication release')
    board('A18-IF09-201-arm-board',104.4,1.565,9)
    board('A18-IF09-202-tool-board',110,1.6,3)
    pins=[]
    names=[['CAN_H','CAN_L','SIGNAL_GND','MODULE_ID','TOOL_ENABLE'],['TOOL_V_A','TOOL_V_B','PRESENT','RETURN_A','RETURN_B']]
    for row,z in enumerate([6,12]):
        for col,y in enumerate([-8,-4,0,4,8]):
            net=names[row][col];k=1+row*5+col
            add(f'A18-IF09-pad-{k:02}',g.cyl([105.965,y,z],[1,0,0],1.5,.035),'contact_pad_envelope','Nominal plated pad, not a PCB stackup qualification')
            add(f'A18-IF09-pin-{k:02}',g.cyl([106,y,z],[1,0,0],1,4),'working_pin_envelope','P70 candidate nominal Ø2/working4/free5; not exact supplier CAD')
            pins.append(dict(pin=k,net=net,Y_mm=y,Z_mm=z,arm_contact_X_mm=106,tool_pin_base_X_mm=110,free_tip_X_mm=105,working_tip_X_mm=106))
    # Standard screws/nuts modelled nominally; no threads or electrical claims.
    for side in ['arm','tool']:
        for k,y in enumerate([-14,14]):
            if side=='arm':start,head,nutx,n,z=100,106,100,1,9
            else:start,head,nutx,n,z=110,110,112.4,-1,3
            s=g.cyl([start,y,z],[1,0,0],1.25,6).fuse(g.cyl([head,y,z],[n,0,0],2.25,2.5))
            # Hex socket front access is modelled, not a solid-head cylinder.
            socket=cq.Workplane(g.plane([head+n*2.6,y,z],[-n,0,0])).polygon(6,2/np.cos(np.pi/6)).extrude(1.5).val()
            add(f'A18-IF09-{side}-M2_5x6-{k}',s.cut(socket),'hardware','Purchased ISO4762 nominal M2.5x6, verify actual head')
            nut=hexhole([nutx,y,z],2,af=5).cut(g.cyl([nutx-.1,y,z],[1,0,0],1.35,2.2))
            add(f'A18-IF09-{side}-nut-{k}',nut,'hardware','Purchased M2.5 AF5 th2 nominal; sample fit required')
    # Conservative HFM blocks remain explicit evidence volumes, never silently
    # promoted to exact CAD, panel retention or a qualified blind-mate pair.
    evidence=[]
    for y,camera in [(-9,'upper'),(9,'lower')]:
        for name,start,size in [('jack',[82,y-4.8,-22.9],[19.8,9.6,21.8]),('plug',[101.8,y-4.55,-17.275],[25.23,9.1,10.55])]:
            evidence.append(dict(id=f'IF09-{camera}-{name}-envelope',shape=box(start,size),source='Rosenberger nominal envelope inherited from IF02; no mating overlap assumed'))
    # Restore full current assembly rows and only replace its face insert.
    current,assembly_sources,_=collect(last='skins06')
    a17path=ROOT/'engineering/arm_a17/build/style01/manifest.json';a17=json.loads(a17path.read_text())
    current=[p for p in current if p['id'] not in a17['replaces_only']]+[dict(p,step_path=str((a17path.parent/'step'/(p['id']+'.step')).relative_to(ROOT))) for p in a17['parts']]
    assert len(current)==541;old='A13-IF-303-face-insert';unchanged=[p for p in current if p['id']!=old];assert len(unchanged)==540
    inherited=ROOT/'engineering/arm_a17/build/style01/review.json';prior=json.loads(inherited.read_text());assert prior['sampled_clear']
    for path,digest in prior['source_sha256'].items():assert c.sha(ROOT/path)==digest,path
    sources.update(assembly_sources);sources[str(a17path.relative_to(ROOT))]=c.sha(a17path);sources[str(inherited.relative_to(ROOT))]=c.sha(inherited)
    for p in current:sources[p['step_path']]=c.sha(ROOT/p['step_path'])
    fixed=[(p,r.load(ROOT/p['step_path'])) for p in unchanged]
    vendor=json.loads((c.OUT/'vendor-audit.json').read_text())
    for m in vendor['motors']:
        for tag,frame in [('stator','fixed'),('external-output','rotor')]:
            path=c.CACHE/'vendor'/(m['joint']+'-'+tag+'.step');assert c.sha(path)==m['cache_step_sha256'][tag]
            fixed.append((dict(id=m['joint']+'-'+tag,frame=m['joint']+'.'+frame),r.load(path)))
    # Fixture tests are intentionally separate from the bare-arm mass/BOM.
    changed=[(p,shapes[p['id']]) for p in rows if p['id'] not in ['A18-IF09-102-tool-distance-gauge','A18-IF09-202-tool-board'] and '-pin-' not in p['id'] and '-tool-' not in p['id']]
    hits=[];tested=0
    def check(a,s,b,t,scope):
        nonlocal tested
        if not r.overlap(s,t):return
        tested+=1;vol=r.common_volume(s,t)
        if vol>.01:hits.append(dict(scope=scope,a=a,b=b,volume_mm3=vol))
    for (p,s),(t,w) in itertools.combinations([(p,shapes[p['id']]) for p in rows],2):check(p['id'],s,t['id'],w,'contact_fixture')
    for p,s in [(p,shapes[p['id']]) for p in rows]:
        for e in evidence:check(p['id'],s,e['id'],e['shape'],'nominal_coax_allocation')
    cached=set()
    for sample in prior['checks']:
        f=c.frames(sample['q_deg'])
        for p,s in changed:
            for t,w in fixed:
                rel=np.linalg.inv(f[p['frame']])@f[t['frame']];key=(p['id'],t['id'],tuple(np.round(rel,8).flat))
                if key in cached:continue
                cached.add(key);check(p['id'],s,t['id'],c.transform(w,rel),sample['sample'])
    compressed_nominal_mm=1.0
    # Independent worst-case example. These are process targets needing actual
    # supplier stroke and PCB/print measurements, not approved pin travel.
    stack=[dict(item='Mechanical face to arm pad',plus_minus_mm=.15),dict(item='Tool board seat',plus_minus_mm=.10),dict(item='Finished PCB/solder mounting',plus_minus_mm=.10),dict(item='Pin free height',plus_minus_mm=.10)]
    tolerance=sum(x['plus_minus_mm'] for x in stack)
    manifest=dict(revision='A18-IF09-CONTACT-FIT',layout=c.L,base_context=base,sources=sources,replaces_only=[old],printed_parts=printed,
      parts=[{k:v for k,v in p.items() if k not in ['vertices_mm','triangles']} for p in rows],pins=pins,
      interface=dict(mechanical_X_mm=110,contact_X_mm=106,ring_OD_mm=76,central_space_D_mm=54,M4_PCD_mm=72,M4_phase_deg=45,key_YZ_mm=[0,31],
        actual_tool_hardware_installed=False,arm_board_mount_YZ_mm=[[-14,9],[14,9]],tool_board_mount_YZ_mm=[[-14,3],[14,3]],camera_openings_YZ_mm=[[-9,-12],[9,-12]],camera_window_mm=[11.6,11.6],
        voltage_frozen=False,total_test_branch_limit_A=1,hot_swap_allowed=False,PoC_is_separate_power_domain=True),
      contact_compression=dict(nominal_mm=compressed_nominal_mm,assumed_process_stack=stack,assumed_range_mm=[compressed_nominal_mm-tolerance,compressed_nominal_mm+tolerance],
        manufacturer_travel_and_force_window_verified=False,production_tolerance_released=False),
      review=dict(inherited_A17_pose_count=len(prior['checks']),changed_arm_geometry_count=len(changed),exact_candidate_pairs=tested,collision_threshold_mm3=.01,hits=hits,
        sampled_clear=not hits,unchanged_geometry_review_sha256=c.sha(inherited),scope='New face/arm board/pads/arm screws against540 unchanged own parts and14 private motor partitions in26 inherited samples; contact-gauge assembly separately; conservative coax blocks separately. No full base shell, tolerance solids, dynamic wires, plug retention or real tools.'),
      manufacturing_scope='Only101 insert and102 gauge may be printed. PCB/contacts/fasteners are NOT print parts. Supported unpowered no tool load. Gauge is NOT a released head.',
      production_release=False)
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    (OUT/'meshes.json').write_text(json.dumps(rows,separators=(',',':'))+'\n')
    with (OUT/'pin-map.csv').open('w') as fp:
        w=csv.DictWriter(fp,fieldnames=list(pins[0]));w.writeheader();w.writerows(pins)
    print('IF09',len(rows),'parts',len(printed),'prints','pairs',tested,'hits',hits,flush=True)
    if hits:raise RuntimeError('IF09 geometry not cleared; manifest records failure')

if __name__=='__main__':main()
