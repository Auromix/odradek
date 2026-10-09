# SPDX-License-Identifier: CC-BY-NC-4.0
"""Conventional native flange brackets and stock rectangular-tube trial core."""
import json, shutil, numpy as np, cadquery as cq, trimesh
import common as c
from vendor import interfaces
g=c.cad;O=c.OUT/'skeleton01';O.mkdir(exist_ok=True);g.OUT=O
I=interfaces();H=[]

def vec(x):return np.array(x,float)
def pts(i,kind):
    a=I[i];m=a['model_source'];flip=m['interface_frame']['T_raw_from_interface_mm'][1][1]
    return [vec(a['u'])*x+vec(a['v'])*y*flip for x,y in m[kind]['raw_step_xy_mm']]
def mount(s,i,kind,p,th):
    a=I[i];n=vec(a['n']);d=5 if a['model']=='RS04' and kind=='output_fasteners' else 3 if a['model']=='RS00' else 4
    for v in pts(i,kind):s=g.drill(s,vec(p)+v-n*.1,n,d+.5,th+.2)
    if a['model']=='RS04' and kind=='output_fasteners':
        for x,y in [(-12.67842,12.67842),(17.31905,4.64063),(-4.64063,-17.31905)]:s=g.drill(s,vec(p)+vec(a['u'])*x+vec(a['v'])*y-n*.1,n,6.5,3.6)
    return s
def output(i,th=10):
    a=I[i];r=35 if a['model']=='RS04' else 20
    return mount(g.cyl(a['out_mm'],a['n'],r,th),i,'output_fasteners',a['out_mm'],th)
def holder(i,th=8,inner=None):
    a=I[i];r=67 if a['model']=='RS04' else 42 if a['model']=='RS00' else 32.5
    ri=inner or (40 if a['model']=='RS04' else 18.7 if a['model']=='RS00' else 21.2)
    return mount(g.ring(a['fixed_mm'],a['n'],r,ri,th),i,'fixed_front_fasteners',a['fixed_mm'],th)
def box(p,size):return cq.Solid.makeBox(*size,g.V(p))
def add(id,s,owner,**kw):
    # Some valid inherited STEP loses validity under OCC same-domain cleanup.
    # Preserve the valid original topology rather than forcing that cleanup.
    if not s.isValid():s=s.fix()
    cleaned=s.clean()
    if cleaned.isValid():s=cleaned
    assert s.isValid() and len(s.Solids())==1,id
    mesh=None
    for tol in [.15,.06,.02]:
        vv,tt=s.tessellate(tol,.12)
        for digits in [5,6,4]:
            m=trimesh.Trimesh([v.toTuple() for v in vv],tt,process=True);m.merge_vertices(digits_vertex=digits)
            m.update_faces(m.nondegenerate_faces());m.update_faces(m.unique_faces());m.remove_unreferenced_vertices()
            if m.is_watertight and m.is_winding_consistent and m.volume>0:mesh=m;break
        if mesh is not None:break
    assert mesh is not None,id+' non-watertight export after refined tessellation'
    for directory in ['step','stl']:(O/directory).mkdir(exist_ok=True)
    cq.exporters.export(s,str(O/'step'/(id+'.step')));mesh.export(O/'stl'/(id+'.stl'))
    bb=s.BoundingBox()
    p=dict(id=id,owner=owner,frame=kw.get('frame') or g.local_frame(owner),role=kw.get('role','printed_structure'),material=kw.get('material','PA12 fit prototype'),note=kw.get('note',''),
        solid_count=1,watertight=True,volume_mm3=s.Volume(),mass_kg=kw.get('mass',s.Volume()*g.DENSITY),com_mm=list(s.Center().toTuple()),bbox_size_mm=[bb.xlen,bb.ylen,bb.zlen],vertices_mm=mesh.vertices.tolist(),triangles=mesh.faces.tolist())
    g.PARTS.append(p);g.SHAPES[id]=s;print('CORE_PART',id,flush=True);return p
def socket(s,x0,x1,y=0):
    return s.cut(box([x0,y-10.2,-20.2],[x1-x0,20.4,40.4])).clean()
def clamp_holes(s,xs,y):
    for x in xs:s=g.drill(s,[x,y-16,0],[0,1,0],4.5,32)
    return s
def long_tools(s,i,kind,p,start,length):
    n=vec(I[i]['n']);d=10 if I[i]['model']=='RS04' and kind=='output_fasteners' else 9.5
    for v in pts(i,kind):s=g.drill(s,vec(p)+v+n*start,n,d,length)
    return s

def main():
    c.base_context();g.PARTS.clear();g.SHAPES.clear()
    # Root-to-shoulder L bracket: flat foot plus a vertical annular plate.
    a=I[1];fixed=vec(a['fixed_mm'])+[0,0,114]
    foot=box([-55,-36,30],[110,104.5,8])
    for x in [-38,38]:
        for y in [-28,28]:foot=g.drill(foot,[x,y,29.9],[0,0,1],5.6,8.2)
    ring=holder(1).translate((0,0,114))
    tail=box([-55,60.5,35],[110,8,79])
    tail=tail.cut(g.cyl(fixed-vec(a['n'])*.1,a['n'],40,8.2))
    s=foot.fuse(ring,tail).clean();s=mount(s,1,'fixed_front_fasteners',fixed,8)
    add('A16-S101-root-to-shoulder-L',s,1,note='Conventional L bracket; flat8mm foot and8mm annular face. Supported print; metal welded/bent/milled redesign requires strength validation.')
    # Orthogonal cross adapter, without any new transmission.
    s=output(1).fuse(holder(2).translate((0,-10,0)),box([27.35,42,-12],[8,18,24])).clean()
    s=mount(s,1,'output_fasteners',I[1]['out_mm'],10)
    p=vec(I[2]['fixed_mm'])+[0,-10,0];s=mount(s,2,'fixed_front_fasteners',p,8)
    s=long_tools(s,1,'output_fasteners',I[1]['out_mm'],10,25)
    s=long_tools(s,2,'fixed_front_fasteners',p,8,25)
    add('A16-S102-shoulder-cross-adapter',s,2,note='Native J2 output to native J3 front ring; no gear/cam. Bolt access recut after unions.')
    # Upper arm: two ordinary tube-end sockets, purchased220mm tube.
    s=output(2).fuse(box([37.85,-14,-24],[37.15,28,48])).clean();s=socket(s,50,75.1)
    s=long_tools(s,2,'output_fasteners',I[2]['out_mm'],10,40)
    s=clamp_holes(s,[60,72],0)
    add('A16-S103-upper-proximal-socket',s,3,note='220mm stock20x40x2 tube beginsX50. Fit gap0.2 per side;2xM4 transverse clamp through tube; output bolts before tube.')
    p=vec(I[3]['fixed_mm'])+[340,0,0]
    s=holder(3).translate((340,0,0)).fuse(box([245,-14,-24],[33,49.35,48])).clean();s=socket(s,244.9,270)
    s=mount(s,3,'fixed_front_fasteners',p,8);s=long_tools(s,3,'fixed_front_fasteners',p,8,30);s=clamp_holes(s,[250,262],0)
    # D10 is exactly tangent to the X245 socket edge at the first clamp;
    # D11 makes an intentional open scallop instead of a zero-width lip.
    for x in [250,262]:s=g.drill(s,[x,14,0],[0,1,0],11,36)
    add('A16-S104-upper-distal-socket',s,3,note='Tube endsX270; offset end socket joins native J4 front annulus. Tool channels open with tube removed.')
    s=box([50,-10,-20],[220,20,40]).cut(box([49.9,-8,-18],[220.2,16,36]))
    for x in [60,72,250,262]:s=g.drill(s,[x,-11,0],[0,1,0],4.5,22)
    add('A16-S105-upper-stock-tube',s,3,role='purchased_structure',material='6061-T6 stock rectangular tube20x40x2, saw cut220mm; drill4xD4.5 on side centreline',mass=s.Volume()*2.70e-6,note='Catalogue material assumption only, not strength certification. Tube is purchased metal in supported fit.')
    # Forearm, same tube section and ordinary offset sockets.
    s=output(3).fuse(box([-20,37.85,-24],[35,12.15,48]),box([10,48,-24],[30,28,48])).clean();s=socket(s,20,40.1,62)
    s=long_tools(s,3,'output_fasteners',I[3]['out_mm'],10,45);s=clamp_holes(s,[27,37],62)
    add('A16-S106-fore-proximal-socket',s,4,note='Ordinary elbow L/socket; tube centreY62. Bolt J4 output before installing tube.')
    p=vec(I[4]['fixed_mm'])+[185,62,0]
    s=holder(4).translate((185,62,0)).fuse(box([50,48,-24],[31,28,48]),box([63,72,-12],[18,31.5,24]),box([63,95.5,-12],[100,8,24])).clean();s=socket(s,49.9,75,62)
    s=mount(s,4,'fixed_front_fasteners',p,8);s=long_tools(s,4,'fixed_front_fasteners',p,8,35);s=clamp_holes(s,[60,70],62)
    for x in [60,70]:s=g.drill(s,[x,76,0],[0,1,0],11,40)
    add('A16-S107-fore-distal-socket',s,4,note='Offset tube socket to native RS10P J5 fixed ring. No redundant gears.')
    s=box([20,52,-20],[55,20,40]).cut(box([19.9,54,-18],[55.2,16,36]))
    for x in [27,37,60,70]:s=g.drill(s,[x,51,0],[0,1,0],4.5,22)
    add('A16-S108-fore-stock-tube',s,4,role='purchased_structure',material='6061-T6 stock rectangular tube20x40x2, saw cut55mm; drill4xD4.5',mass=s.Volume()*2.70e-6,note='Fore axis spacing185 unchanged; fixed rear spine completes span outside wrist pitch sweep.')
    # Simple L cross carrier for the two native25:1 wrist actuators.
    p=vec(I[5]['fixed_mm'])+[55,0,0]
    j6ring=holder(5).intersect(box([-40,-27.5,-45],[80,55,30]))
    join=box([-15,22,-20],[33,10,6]).intersect(g.cyl([0,32,0],[0,-1,0],20,10))
    s=output(4).fuse(j6ring.translate((55,0,0)),box([-15,22,-36.8],[33,5,22.8]),box([15,22,-36.8],[73,5,8]),join).clean()
    s=mount(s,4,'output_fasteners',I[4]['out_mm'],10)
    s=long_tools(s,4,'output_fasteners',I[4]['out_mm'],10,25)
    s=mount(s,5,'fixed_front_fasteners',p,8);s=long_tools(s,5,'fixed_front_fasteners',p,8,38)
    add('A16-S109-wrist-pitch-yaw-L',s,5,note='One L bracket, native J5 output/J6 front ring; open screw access; not a new joint module.')
    # Reuse J7 cartridge; replace only its input support for native RS10P.
    p=vec(I[6]['fixed_mm'])+[75,0,0]
    s=output(5).fuse(holder(6).translate((75,0,0)),box([-16,-18,-48.3],[124.3,36,10])).clean()
    s=s.cut(g.ring([0,0,-42],[0,0,1],30.4,20.6,5.4))
    s=mount(s,5,'output_fasteners',I[5]['out_mm'],18)
    # Recess input heads so they remain above the RS00 case.
    for v in pts(5,'output_fasteners'):s=g.drill(s,vec(I[5]['out_mm'])+v+vec(I[5]['n'])*10,vec(I[5]['n']),9.5,8.1)
    s=mount(s,6,'fixed_front_fasteners',p,8)
    for k in range(6):
        t=np.radians(30+60*k);s=g.drill(s,[100.2,35*np.cos(t),35*np.sin(t)],[1,0,0],3.5,8.2)
        s=g.drill(s,[99.7,35*np.cos(t),35*np.sin(t)],[1,0,0],8,.6)
    add('A16-S110-wrist-yaw-roll-L',s,6,note='J7 front ring/cartridge planes retained;6x cage through boltsPCD70; annular screw-head sweep relief, no extra mechanism.')
    old=c.ROOT/'engineering/arm_a13/wrist-route01/build'
    D=json.loads((old/'integration-parts.json').read_text());retained=[]
    for p in D['new_parts']:
        if p['id'].endswith('108-yaw-clearance-carrier'):continue
        if p['id'].startswith(('A13-IF-304','A13-IF-305')):continue
        f=old/'step'/(p['id']+'.step');w=cq.importers.importStep(str(f));s=w.val()
        owner=7 if p['frame']=='J7.rotor' else 6
        # Keep proven imported topology byte-for-byte. OCC cleanup on this
        # recessed carrier mutates a valid Solid into an invalid one; avoid it.
        assert s.isValid() and len(s.Solids())==1
        m=trimesh.Trimesh(p['vertices_mm'],p['triangles'],process=False)
        assert m.is_watertight and m.is_winding_consistent and m.volume>0
        shutil.copyfile(f,O/'step'/f.name);m.export(O/'stl'/(p['id']+'.stl'))
        entry=dict(id=p['id'],owner=owner,frame=p['frame'],role='printed_structure',material='PA12/PETG supported fit only',note='Unchanged valid A13 STEP, no topology cleanup; new arm context, qualification pending.',
          solid_count=1,watertight=True,volume_mm3=s.Volume(),mass_kg=s.Volume()*1.27e-6,com_mm=list(s.Center().toTuple()),bbox_size_mm=m.extents.tolist(),vertices_mm=p['vertices_mm'],triangles=p['triangles'])
        g.PARTS.append(entry)
        retained.append(dict(id=p['id'],source=str(f.relative_to(c.ROOT)),source_sha256=c.sha(f)))
    parts=[]
    for p in g.PARTS:parts.append({k:v for k,v in p.items() if k not in ['vertices_mm','triangles']})
    result=dict(revision='A16-SKELETON01',layout=c.L,base_context=c.base_context(),parts=parts,retained=retained,
      excluded_tool_side_dummies=['A13-IF-304-tool-pocket','A13-IF-305-tool-pocket-cover'],
      manufacturing_scope='Only supported, unpowered, unloaded bracket/tube/cartridge fit. Brackets are ordinary flange plates and tube sockets, not decorative mesh proxies.',
      nominal_motor_bolt_plan={'RS04_fixed':'M4x12 /8 grip /.8washer /3.2 insertion /5 minimum source depth','RS04_output':'M5x16 /10 grip /1washer /5 insertion /6.5 minimum source depth','RS10P_fixed':'M4x12 /8 grip /.8washer /3.2 insertion /4.5 source depth','RS10P_output':'M4x14 /10 grip /.8washer /3.2 insertion /5 source depth','RS00_fixed':'M3x12 button /8 grip /.5washer /3.5 insertion; actual front usable depth must be measured'},
      hardware_and_tool_access_qualified=False,whole_arm_collision_qualified=False,harness_qualified=False,production_release=False)
    (O/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');(O/'meshes.json').write_text(json.dumps(g.PARTS,separators=(',',':'))+'\n')
    ids={p['id'] for p in g.PARTS}
    for directory in ['step','stl']:
        for stale in (O/directory).glob('*'):
            if stale.is_file() and stale.stem not in ids:stale.unlink()
    print('SKELETON_PARTS',len(parts),flush=True)

if __name__=='__main__':main()
