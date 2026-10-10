# SPDX-License-Identifier: CC-BY-NC-4.0
"""Curve the selected carapace with exact BREP, retaining C03-C06 fixings.

A17 is a separate development candidate. Never overwrite the issued A16 kit
or reuse its collision/mass qualification after changing a surface.
"""
from pathlib import Path
import sys,json,hashlib
import cadquery as cq
import numpy as np
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.Approx import Approx_ChordLength

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'engineering/arm_a16'))
import common as c
import covers01 as skin
import covers02 as raw
import skeleton_review as r
from assembly_sources import collect

OUT=HERE/'build/style01';OUT.mkdir(parents=True,exist_ok=True)
RAW=HERE/'build/rounded-raw';RAW.mkdir(parents=True,exist_ok=True)

def wire(q,ry,rz,cu=0,cy=0,inset=0):
    # Circular section corner blends are real CAD curves, not render-only
    # smoothing. Keep broad planes and a shallow dorsal ridge for mecha form.
    wp=cq.Workplane(cq.Plane(origin=(q,cy,0),normal=(1,0,0),xDir=(0,1,0)))
    w=wp.polyline([(cu+a*ry,b*rz) for a,b in skin.PROFILE]).close().val()
    w=w.fillet2D(min(8.0,min(ry,rz)*.18),w.Vertices())
    if inset:
        ww=w.offset2D(-inset,kind='arc')
        assert len(ww)==1
        w=ww[0]
    return w

def curved(stations,cy,sign,ruled=False):
    if len(stations)==7 and stations[0][0]==46 and cy==0:
        # Local shoulder in the skin clears the existing200mm saddle/clamp.
        # Functional fixing seat height stays in the old C06 mount ledger.
        stations=[(46,42,40),(78,28,32),(123,23,28),(185,24,29),
          (200,26,31),(215,28,32),(235,40,33),(248,42,36),(282,45,49)]
    if len(stations)==6 and stations[0][0]==-91:
        # Root transition: same base gap/real motor; neck narrows above the
        # front holder. The rotating shoulder foot begins atq30, above this.
        stations=list(stations);stations[-1]=(28.5,65,64)
    sections=[]
    for s in stations:
        q,ry,rz=s[:3];cu=s[3] if len(s)>3 else 0
        outer=wire(q,ry,rz,cu,cy);inner=wire(q,ry,rz,cu,cy,2.6)
        # One closed C-section constrains inner and outer faces together.
        # Independent inner loft seam/edge compatibility previously produced
        # an inward fold despite a valid solid and watertight STL.
        slab=cq.Solid.extrudeLinear(outer,[inner],cq.Vector(.05,0,0))
        half=cq.Solid.makeBox(700,500,220,c.cad.V([-150,cy-250,.25 if sign==1 else -220.25]))
        slab=slab.intersect(half).fix()
        faces=[f for f in slab.Faces() if f.BoundingBox().xlen<1e-5 and abs(f.BoundingBox().xmin-q)<1e-5]
        assert len(faces)==1,(q,len(faces))
        assert len(faces[0].Wires())==1
        sections.append(faces[0].outerWire())
    # Keep ruled axial surfaces for motor cowls: smooth circumferential
    # blends without loft overshoot into source motors/adjacent joints.
    # Upper long skins use continuous axial lofts. The folding forearm keeps
    # its bounded ruled axial sections; its circumferential blends are curved.
    smooth=not ruled or len(stations)>5
    if not smooth:return cq.Solid.makeLoft(sections,ruled=True).fix()
    # Default degree8 fits can fold inward between widely spaced sections.
    # Bound degree and parameterise by chord length; verify physical core
    # clearances separately rather than assuming station values suffice.
    api=BRepOffsetAPI_ThruSections(True,False,1e-6)
    api.SetMaxDegree(3);api.SetParType(Approx_ChordLength)
    for w in sections:api.AddWire(w.wrapped)
    api.Build();return cq.Shape.cast(api.Shape()).fix()

def cap(station,sign):
    q,ry,rz=station
    solid=cq.Solid.extrudeLinear(wire(q,ry,rz),[],cq.Vector(2.6,0,0))
    if q==-60 and ry==33 and rz==33:
        # Compact J7 rear face is adjacent to the J6 yaw sweep. Retain a
        # flush cap here instead of the dome used on the larger joints.
        half=cq.Solid.makeBox(700,500,220,c.cad.V([-150,-250,.25 if sign==1 else -220.25]))
        return solid.intersect(half).fix()
    # Shallow convex rear face replaces the flat box-like pod end. Retain
    # the service opening through the full dome, at identical clocking.
    depth=min(ry,rz)*.10
    dome=cq.Solid.makeLoft([wire(q-depth,ry*.18,rz*.18),wire(q-depth*.80,ry*.60,rz*.60),
      wire(q-depth*.35,ry*.90,rz*.90),wire(q,ry,rz)],ruled=False)
    solid=solid.fuse(dome).clean().fix()
    # Hollow the convex face rather than carrying a solid decorative lump.
    # Axial/radial nominal offset2.6; true normal minimum still needs audit.
    inner=cq.Solid.makeLoft([wire(q-depth+2.6,max(ry*.18-2.6,1),max(rz*.18-2.6,1)),
      wire(q-depth*.80+2.6,ry*.60-2.6,rz*.60-2.6),
      wire(q-depth*.35+2.6,ry*.90-2.6,rz*.90-2.6),
      wire(q+2.7,ry-2.6,rz-2.6)],ruled=False)
    solid=solid.cut(inner).fix()
    solid=solid.cut(cq.Solid.makeBox(depth+2.8,20,14,c.cad.V([q-depth-.1,-10,-7]))).fix()
    half=cq.Solid.makeBox(700,500,220,c.cad.V([-150,-250,.25 if sign==1 else -220.25]))
    return solid.intersect(half).fix()

def baseline_id(id):
    if '-C03-root-cowl-' in id:return id.replace('A16-C03-root','A16-C02-J1')
    if '-C04-J4-cowl-' in id:return 'A16-C02-elbow-'+('ventral' if id.endswith('-a') else 'dorsal')
    for a in ['C04','C05','C06']:
        if '-'+a+'-' in id:return id.replace('-'+a+'-','-C02-')
    raise ValueError(id)

def plate_clearance(part,id):
    # New loft stations also move the skin around the fixed J4 socket.
    # Transfer a physical clearance volume, not only the material that had
    # been removed from the old cover. All four parts share J3.rotor.
    if not (id.startswith(('A16-C04-J4-cowl-','A17-C04-J4-cowl-',
                          'A16-C06-upper-','A17-C06-upper-'))):return part
    file=c.OUT/'cowls04/step/A16-C04-J4-mount-plate.step'
    plate=cq.importers.importStep(str(file)).val()
    part=part.cut(plate).fix()
    for axis in range(3):
        for sign in [-1,1]:
            delta=[0.,0.,0.];delta[axis]=sign*.25
            part=part.cut(plate.translate(tuple(delta))).fix()
    return part.clean().fix()

def trim_existing():
    """Repair a generated CAD batch without rerunning unchanged lofts."""
    d=json.loads((OUT/'manifest.json').read_text())
    prior=c.sha(OUT/'manifest.json')
    meshes=json.loads((OUT/'meshes.json').read_text())
    assert len(meshes)==18 and d['layout']==c.L
    c.cad.PARTS.clear();skin.O=OUT;c.cad.OUT=OUT
    history=[]
    for p in d['parts']:
        file=OUT/'step'/(p['id']+'.step');digest=c.sha(file)
        original=cq.importers.importStep(str(file)).val()
        new=plate_clearance(original,p['id'])
        assert new.isValid() and len(new.Solids())==1,(p['id'],len(new.Solids()))
        skin.export(p['id'],new,p['owner'],frame=p['frame'],note=p['note']+' J4 fixed socket axial clearance cuts at +/-0.25mm, no change to mounting datums.')
        history.append(dict(id=p['id'],prior_step_sha256=digest,removed_mm3=original.Volume()-new.Volume()))
    rows=c.cad.PARTS
    (OUT/'meshes.json').write_text(json.dumps(rows,separators=(',',':'))+'\n')
    d['parts']=[{k:v for k,v in p.items() if k not in ['vertices_mm','triangles']} for p in rows]
    d['socket_clearance_repair']=dict(prior_manifest_sha256=prior,parts=history,
        note='Actual unchanged J4 mount plate cut from both upper and elbow skins. Six +/-0.25mm axis translations reserve clearance; not a global normal-gap or tolerance qualification.')
    (OUT/'manifest.json').write_text(json.dumps(d,indent=2)+'\n')
    print('A17_TRIM_EXISTING_DONE',len(rows),flush=True)

def main():
    context=c.base_context()
    rows,sources,_=collect(last='skins06')
    current=[p for p in rows if p['role']=='printed_cover']
    assert len(current)==18
    skin.skin=curved;raw.endcap=cap;raw.O=RAW;skin.O=RAW;c.cad.OUT=RAW
    raw.main()
    c.cad.PARTS.clear();skin.O=OUT;c.cad.OUT=OUT
    remap={};stats=[]
    for p in current:
        id=p['id'];old=baseline_id(id)
        base=cq.importers.importStep(str(c.OUT/'covers02/step'/(old+'.step'))).val()
        actual=cq.importers.importStep(str(ROOT/p['step_path'])).val()
        new=cq.importers.importStep(str(RAW/'step'/(old+'.step'))).val()
        # Trims are half-spaces, not just material removed from the old skin:
        # apply them explicitly so a changed inner section cannot leave chips.
        if '-C03-root-' in id:
            new=new.cut(cq.Solid.makeBox(400,400,20.2,c.cad.V([-200,-200,-110]))).fix()
        if id.startswith('A16-C06-upper-') or id.startswith('A16-C06-fore-'):
            # C06 has ordinary straight supports and clearance holes only.
            # Rebuild them from the signed mount ledger, preserving seats.
            ledger=json.loads((c.OUT/'skins06/manifest.json').read_text())['mounts']
            section='upper' if '-upper-' in id else 'fore'
            label=id.rsplit('-',1)[1];grip=4 if section=='upper' else 6.5
            for mount in ledger:
                if mount['joint']!=section or not mount['k'].endswith('-'+label):continue
                point=np.array(mount['p_mm'],float);n=np.array(mount['n'],float)
                radius=4;length=grip
                if section=='upper':
                    # Wider straight boss joins the raised skin; original
                    # 4mm screw seat remains recessed at its old datum.
                    # A finite local footprint avoids a tolerance-degenerate
                    # Boolean against the curved ridge. Use a conservative
                    # outer height within the actual boss footprint.
                    probe=new.intersect(c.cad.cyl([point[0],point[1],-100],[0,0,1],1,200))
                    assert probe.Volume()>1e-6,(id,mount['k'],'empty seat probe')
                    bound=probe.BoundingBox();outer=bound.zmax if n[2]>0 else -bound.zmin
                    length=max(grip,outer-abs(point[2]));radius=6
                new=new.fuse(c.cad.cyl(point,n,radius,length)).clean().fix()
                new=c.cad.drill(new,point-n*.1,n,3.5,15)
                new=new.cut(c.cad.cyl(point+n*grip,n,3.7,8)).fix()
        elif id.startswith('A16-C05-J7-cowl-'):
            new=new.cut(c.cad.cyl([-75,0,-55],[0,0,1],46,55)).fix()
        # Transfer mounting tabs/bosses and actual reliefs from the issued
        # module, at unchanged datums. No triangle-mesh morph or motor scaling.
        plus=actual.cut(base).fix();minus=base.cut(actual).fix()
        if id.startswith('A16-C05-J7-cowl-'):
            # J7 uses only two straight radial bosses per half. Rebuild these
            # simple features directly: a shell Boolean difference can leave
            # tangential sliver faces, although the resulting BREP is valid.
            sign=1 if id.endswith('-a') else -1
            outer=50.6 if sign==1 else 47.84
            n=np.array([0,0,sign],float)
            for x in [39,49]:
                point=np.array([x,0,42*sign],float)
                new=new.fuse(c.cad.cyl(point+n*.05,n,4,outer-42-.05)).clean().fix()
                new=c.cad.drill(new,point-n*.1,n,3.5,outer-42+.3)
        else:
            if minus.Volume()>1e-6:new=new.cut(minus,tol=1e-5).fix()
            if plus.Volume()>1e-6:new=new.fuse(plus,tol=1e-5).clean().fix()
        new=plate_clearance(new,id)
        assert new.isValid() and len(new.Solids())==1,(id,len(new.Solids()))
        nid=id.replace('A16-','A17-',1)
        skin.export(nid,new,p['owner'],frame=p['frame'],note='Rounded CAD section with unchanged C03-C06 mounting features and reliefs. Nominal section2.6mm; global wall, physical fit, mass and motion require fresh validation. Appearance development candidate, not production.')
        remap[id]=nid
        stats.append(dict(old=id,new=nid,old_volume_mm3=actual.Volume(),new_volume_mm3=new.Volume(),transferred_addition_mm3=plus.Volume(),transferred_cut_mm3=minus.Volume()))
        print('A17_STYLE',nid,flush=True)
    meshes=c.cad.PARTS
    (OUT/'meshes.json').write_text(json.dumps(meshes,separators=(',',':'))+'\n')
    parts=[{k:v for k,v in p.items() if k not in ['vertices_mm','triangles']} for p in meshes]
    d=dict(revision='A17-MANTA-CARAPACE01',layout=c.L,base_context=context,parts=parts,replaces_only=list(remap),source_sha256=sources,remap=remap,change_stats=stats,
      intent='Manta base: blended sections, restrained hard dorsal ridge, continuous taper. Same Lingzu motors/long reach/base load interfaces. No new mechanical transmission.',
      prototype_release=False,production_release=False,scope='Development candidate; old A16 issue unchanged. All A16 collision/mass reports invalid for this candidate until rerun.')
    (OUT/'manifest.json').write_text(json.dumps(d,indent=2)+'\n')
    print('A17_CURVED_CAD',len(parts),flush=True)

if __name__=='__main__':
    if '--trim-existing' in sys.argv:trim_existing()
    else:main()
