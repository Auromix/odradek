# SPDX-License-Identifier: CC-BY-NC-4.0
"""Selected-A link skins as closed CAD solids. Supported geometry fit only.

Original motor/frame layout retained for this detachable cosmetic study.
The actuator qualification review is separate and has NOT approved that layout.
"""
from pathlib import Path
import sys, json, hashlib, math
import numpy as np, cadquery as cq, trimesh
from shapely.geometry import Polygon, box as region
from scipy.sparse.csgraph import connected_components
from scipy.sparse import coo_matrix

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
OUT = HERE / 'build'
BASE = ROOT / 'engineering/arm_a11/build'
sys.path.insert(0, str(ROOT / 'engineering/arm_a11'))
import interfaces as c
import refine
b = c.legacy
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
PROFILE = [(-1,0),(-1,.65),(-.72,.94),(0,1.10),(.72,.94),(1,.65),
           (1,0),(1,-.65),(.65,-.96),(0,-1.04),(-.65,-.96),(-1,-.65)]

def box(p, size):
    return cq.Solid.makeBox(*size, b.V(p))

def surface(stations, cy, sign):
    # A closed C-section wire avoids ambiguous nested hollow-loft booleans.
    # True section-normal offset rather than subtracting each section radius.
    wp = cq.Workplane(cq.Plane(origin=(stations[0][0],cy,0),normal=(1,0,0),xDir=(0,1,0)))
    for i,(x,ry,rz) in enumerate(stations):
        outer = Polygon([(u*ry,v*rz) for u,v in PROFILE])
        section = outer.difference(outer.buffer(-2.6,join_style=2)).intersection(
            region(-150,.2,150,150) if sign == 1 else region(-150,-150,150,-.2))
        assert section.geom_type == 'Polygon' and not section.interiors
        if i: wp = wp.workplane(offset=x-stations[i-1][0])
        wp = wp.polyline(list(section.exterior.coords)[:-1]).close()
    # Continuous longitudinal curves, hard section ridges preserved.
    return wp.loft(ruled=False).val().fix()

def mesh(s):
    assert s.isValid() and len(s.Solids()) == 1
    s = s.clean().fix()
    for tol in [.12,.05,.02]:
        v,f = s.tessellate(tol,.12)
        for precision in [5,6,4]:
            m = trimesh.Trimesh([x.toTuple() for x in v],f,process=True)
            m.merge_vertices(digits_vertex=precision)
            m.update_faces(m.nondegenerate_faces());m.update_faces(m.unique_faces())
            m.remove_unreferenced_vertices()
            edges = m.face_adjacency
            graph = coo_matrix((np.ones(len(edges)*2),(np.r_[edges[:,0],edges[:,1]],
                np.r_[edges[:,1],edges[:,0]])),shape=(len(m.faces),len(m.faces)))
            count = connected_components(graph,directed=False,return_labels=False)
            if m.is_watertight and m.is_winding_consistent and count == 1 and m.volume > 0:
                return m
    print('MESH_FAIL',len(m.vertices),len(m.faces),m.is_watertight,m.is_winding_consistent,count,m.volume,flush=True)
    diagnostic=ROOT/'work/arm-a14/link-shell01';diagnostic.mkdir(parents=True,exist_ok=True)
    cq.exporters.export(s,str(diagnostic/'tessellation-diagnostic.step'));m.export(diagnostic/'tessellation-diagnostic.stl')
    raise ValueError('CAD is closed but printable tessellation is not; redesign required')

def main():
    for folder in ['step','stl-object','print-bed']:(OUT/folder).mkdir(parents=True,exist_ok=True)
    D = json.loads((BASE/'manifest.json').read_text())
    assert sha(BASE/'manifest.json') == '3b9a2291509e0666eeb8d9e73c320538a4235337ffa10af1d1915665a819b559'
    specs = [dict(owner=3,cy=0,stations=[(58,40,42),(76,32,35),(122,23,28),
             (197,20,26),(248,25,32),(282,31,34)],mounts=[65,275],name='upper'),
             dict(owner=4,cy=62,stations=[(6,32,37),(39,25,31),(75,19,25),
             (111,21,27),(129,23,29)],mounts=[15,120],name='fore')]
    cache=ROOT/'work/arm-a14/link-shell01/cache.json';cache.parent.mkdir(parents=True,exist_ok=True)
    cached=json.loads(cache.read_text()) if '--fore-only' in sys.argv else {}
    parts=cached.get('parts',[])[:2];references=cached.get('source_files',{});hardware=cached.get('hardware',[])
    for spec in specs:
        if '--fore-only' in sys.argv and spec['owner']==3:continue
        owner=spec['owner'];cy=spec['cy']
        structure=[]
        for id in [f'P0{owner}-proximal-socket',f'P0{owner}-distal-socket',f'T0{owner}-stock-tube']:
            path=BASE/'step'/(id+'.step');structure.append((id,cq.importers.importStep(str(path)).val()))
            references[str(path.relative_to(ROOT))]=sha(path)
        for side,sign in [('upper',1),('lower',-1)]:
            skin = surface(spec['stations'],cy,sign)
            # Full-diameter columns join the tall style surface to the old
            # captive-nut positions. Counterbores retain the old washer plane.
            columns=[]
            for cx in spec['mounts']:
                column=b.cyl([cx,cy,sign*24.4],[0,0,sign],7.5,45)
                columns.append(column)
                # Trim outer tips with a local smooth section envelope.
                # Columns may protrude above the style surface until intersected
                # by the envelope; construct solid outer loft independently.
                wp=cq.Workplane(cq.Plane(origin=(spec['stations'][0][0],cy,0),normal=(1,0,0),xDir=(0,1,0)))
                for i,(x,ry,rz) in enumerate(spec['stations']):
                    if i:wp=wp.workplane(offset=x-spec['stations'][i-1][0])
                    wp=wp.polyline([(u*ry,v*rz) for u,v in PROFILE]).close()
                envelope=wp.loft(ruled=False).val()
                skin=skin.fuse(column.intersect(envelope).fix()).fix()
            # Relief around real frame solids; seat contact at Z +/-24.4 is
            # deliberate, not hidden by suppressing arbitrary collision pairs.
            protect=b.fuse(columns)
            for id,support in structure:
                clearance=support
                for delta in [(.4,0,0),(-.4,0,0),(0,.4,0),(0,-.4,0),(0,0,.4),(0,0,-.4)]:
                    clearance=clearance.fuse(support.translate(delta)).fix()
                clearance=clearance.cut(protect,tol=1e-5).fix()
                skin=skin.cut(clearance,tol=1e-5).fix()
                # Column undersides follow nominal socket/rib faces rather
                # than retaining intersecting material beneath the washer.
                # This is a conformal supported-fit seat, not a frozen CNC datum.
                skin=skin.cut(support,tol=1e-5).fix()
            # Preserve the exact stock hardware; explicit access wells reach
            # the washer plane even at the high flared ends.
            for cx in spec['mounts']:
                skin=b.drill(skin,[cx,cy,-80],[0,0,1],3.5,160).fix()
                skin=b.drill(skin,[cx,cy,sign*28.0],[0,0,sign],8.0,60).fix()
            relevant=[p for p in D['parts'] if p['role']=='hardware' and
                (p['id'].startswith(f'S0{owner}-') or p['frame']==f'J{owner}.rotor')]
            for h in relevant:
                path=BASE/'step'/(h['id']+'.step')
                sh=cq.importers.importStep(str(path)).val();cut=refine.clearance(h,sh)
                if cut is None:continue
                a=skin.BoundingBox();z=cut.BoundingBox()
                if not any(getattr(a,k+'max')<=getattr(z,k+'min') or getattr(z,k+'max')<=getattr(a,k+'min') for k in ['x','y','z']):
                    skin=skin.cut(cut,tol=1e-5).fix()
                references[str(path.relative_to(ROOT))]=sha(path)
            if owner==4:
                # Two deliberate rounded entry scallops replace thin isolated
                # side lips left at the proximal flange screw-access channels.
                # No disconnected solid is silently kept or discarded.
                for y in [cy-30,cy+30]:
                    skin=skin.cut(b.cyl([13,y,-1 if sign==1 else 1],[0,0,sign],8,17),tol=1e-5).fix()
                # J4 fixed screw heads/washer cylinders sweep around Y; use
                # full annuli rather than hiding collisions at sampled angles.
                for h in D['parts']:
                    if h['role']!='hardware' or not h['id'].startswith('J4-fixed-'):continue
                    path=BASE/'step'/(h['id']+'.step');sh=cq.importers.importStep(str(path)).val();bb=sh.BoundingBox()
                    v=np.array(h['vertices_mm']);centre=(v.min(0)+v.max(0))/2
                    radius=math.hypot(centre[0],centre[2]);rr=max(bb.xlen,bb.zlen)/2+.4
                    ring=b.ring([0,bb.ymin-.4,0],[0,1,0],radius+rr,max(.1,radius-rr),bb.ylen+.8)
                    skin=skin.cut(ring,tol=1e-5).fix();references[str(path.relative_to(ROOT))]=sha(path)
            id=f'A14-LS-{spec["name"]}-{side}'
            if len(skin.Solids()) != 1:
                print('DISCONNECTED',id,[(s.Volume(),s.Center().toTuple()) for s in skin.Solids()],flush=True)
                cq.exporters.export(skin,str(cache.parent/(id+'-diagnostic.step')))
            assert skin.isValid() and len(skin.Solids())==1,(id,len(skin.Solids()))
            m=mesh(skin);step=OUT/'step'/(id+'.step');stl=OUT/'stl-object'/(id+'.stl')
            cq.exporters.export(skin,str(step));m.export(stl)
            # Split seam down; low 54-57mm upper-link height rather than a
            # fragile 246mm upright print. Support/slicer approval is separate.
            R=np.eye(3) if sign==1 else np.diag([1,-1,-1])
            verts=m.vertices@R.T;translation=-verts.min(0);verts+=translation
            bed=trimesh.Trimesh(verts,m.faces,process=False);bedpath=OUT/'print-bed'/(id+'.stl');bed.export(bedpath)
            bb=skin.BoundingBox()
            parts.append(dict(id=id,frame=f'J{owner}.rotor',owner=owner,role='detachable_nonload_cover_supported_fit',
                vertices_mm=m.vertices.tolist(),triangles=m.faces.tolist(),bbox_mm=m.bounds.tolist(),
                solid_count=1,volume_mm3=skin.Volume(),mass_kg_uniform_PETG=skin.Volume()*1.27e-6,
                centre_mm=list(skin.Center().toTuple()),step_sha256=sha(step),stl_sha256=sha(stl),
                print_bed_sha256=sha(bedpath),print_transform=dict(rotation=R.tolist(),translation_mm=translation.tolist()),
                print_bbox_mm=bed.bounds.tolist(),mount_centres_mm=[[cx,cy,sign*24.4] for cx in spec['mounts']],
                washer_seat_z_mm=sign*28,through_hole_mm=3.5,tool_well_mm=8.0,
                nominal_section_wall_mm=2.6,split_gap_mm=.4))
            print('PART',id,np.round(np.ptp(m.vertices,axis=0),2).tolist(),flush=True)
            cache.write_text(json.dumps(dict(parts=parts,source_files=references,hardware=hardware),separators=(',',':')))
        hardware.extend(p['id'] for p in D['parts'] if p['id'].startswith(f'S0{owner}-') and p['role']=='hardware')
    hardware=[p['id'] for p in D['parts'] if p['role']=='hardware' and p['id'].startswith(('S03-','S04-'))]
    report=dict(revision='A14-LINK-SHELL01',status='nominal_CAD_fit_study_not_production_or_print_release',
        parts=parts,source_files=references,baseline_manifest_sha256=sha(BASE/'manifest.json'),retained_hardware=hardware,
        replaces=['A12-W20-upper-blade','A12-W21-fore-blade','A12-W22-upper-dorsal-lid','A12-W23-fore-dorsal-lid'],
        layout=D['layout'],motor_geometry_changed=False,load_release=False,
        notes=['Fore shell extends to X6..129 to enclose retained X15/X120 fastener columns; A12 ended X18..118.',
               'Upper shell narrowed at ends and shortened to X58..282; original joint centres and range unchanged.',
               'Mount undersides are nominal conformal socket/rib seats; no overlapping cover material retained. Physical preload and local thickness still need validation.',
               'Fore root clears complete nominal J4 fixed head/washer annuli with 0.4mm allowance; not a full arm motion sweep.',
               'Fore proximal paired R8 side scallops at X13/Ycy+/-30 clear low flange-access lips; no disconnected islands retained.',
               'No operating harness installed. Positive frame fastening via existing captive nuts; no motor friction clamp.',
               'Envelope is selected-A continuous longitudinal loft with hard cross-section ridges. Actual wall varies longitudinally; section nominal 2.6mm.',
               'These parts retain the old actuator layout only as a dimensional study. A14-QUAL01 rejects its 3kg continuous holding qualification.',
               'No manufacturing tolerance or physical printer/material process is frozen. Metal socket architecture remains separate.'])
    (OUT/'parts.json').write_text(json.dumps(report,separators=(',',':'))+'\n')
    print('COMPLETE',len(parts),flush=True)

if __name__=='__main__':main()
