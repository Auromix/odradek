# SPDX-License-Identifier: CC-BY-NC-4.0
"""Curve the selected carapace with exact BREP, retaining C03-C06 fixings.

A17 is a separate development candidate. Never overwrite the issued A16 kit
or reuse its collision/mass qualification after changing a surface.
"""
from pathlib import Path
import sys,json,hashlib
import cadquery as cq
import numpy as np

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
    outer=[];inner=[]
    for s in stations:
        q,ry,rz=s[:3];cu=s[3] if len(s)>3 else 0
        outer.append(wire(q,ry,rz,cu,cy))
        inner.append(wire(q,ry,rz,cu,cy,2.6))
    # Keep ruled axial surfaces for motor cowls: smooth circumferential
    # blends without loft overshoot into source motors/adjacent joints.
    # Upper long skins use continuous axial lofts. The folding forearm keeps
    # its bounded ruled axial sections; its circumferential blends are curved.
    smooth=not ruled or len(stations)>5
    solid=cq.Solid.makeLoft(outer,ruled=not smooth).cut(cq.Solid.makeLoft(inner,ruled=not smooth)).fix()
    half=cq.Solid.makeBox(700,500,220,c.cad.V([-150,cy-250,.25 if sign==1 else -220.25]))
    return solid.intersect(half).fix()

def cap(station,sign):
    q,ry,rz=station
    solid=cq.Solid.extrudeLinear(wire(q,ry,rz),[],cq.Vector(2.6,0,0))
    half=cq.Solid.makeBox(700,500,220,c.cad.V([-150,-250,.25 if sign==1 else -220.25]))
    return solid.intersect(half).fix()

def baseline_id(id):
    if '-C03-root-cowl-' in id:return id.replace('A16-C03-root','A16-C02-J1')
    if '-C04-J4-cowl-' in id:return 'A16-C02-elbow-'+('ventral' if id.endswith('-a') else 'dorsal')
    for a in ['C04','C05','C06']:
        if '-'+a+'-' in id:return id.replace('-'+a+'-','-C02-')
    raise ValueError(id)

def main():
    context=c.base_context()
    rows,sources,_=collect(last='skins06')
    current=[p for p in rows if p['role']=='printed_cover']
    assert len(current)==18
    skin.skin=curved;raw.endcap=cap;raw.O=RAW;skin.O=RAW;c.cad.OUT=RAW
    if '--reuse-raw' not in sys.argv:raw.main()
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
                new=new.fuse(c.cad.cyl(point,n,4,grip)).clean().fix()
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

if __name__=='__main__':main()
