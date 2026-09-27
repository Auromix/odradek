#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Independent manual finger geometry fixture; no powered or load-bearing use.

Dependencies: cadquery, trimesh, numpy, matplotlib, reportlab, Pillow.
Default dimensions are mm. This fixture does not change the shared arm model.
STEP is in assembly coordinates; print STL files are explicitly reoriented.
"""
import argparse
import csv
import copy
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepAdaptor import BRepAdaptor_Surface
import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parents[1]
P = {
    "revision": "finger-fixture-02", "unit": "mm",
    "base_length": 130.0, "base_width": 76.0, "base_thickness": 6.0,
    "base_mount_holes": [[-50.0,-28.0],[-50.0,28.0],[50.0,-28.0],[50.0,28.0]],
    "base_mount_hole_diameter": 5.5, "pivot_height": 38.0,
    "fork_gap": 11.2, "cheek_thickness": 6.0,
    "dial_radius": 28.0, "left_cheek_radius": 12.0,
    "rotor_radius": 24.0, "rotor_width": 10.0,
    "axis_print_pilot_diameter": 3.0, "axis_drill_finish_diameter": 3.2,
    "pin_nominal_diameter": 3.0, "stop_radius": 18.0,
    "stop_slot_width": 3.6, "q_min_deg": 0.0, "q_max_deg": 130.0,
    "rotor_tongue_x_limits": [10.0,54.0], "rotor_tongue_z_limits": [-6.0,0.0],
    "blade_mount_holes_x": [36.0,48.0], "blade_mount_hole_diameter": 3.2,
    "blade_root_x": 30.0, "blade_thickness": 6.0,
    "led_recess_depth": 0.8, "pad_length": 12.0, "pad_width": 16.0,
    "pad_surface_center_normal": 11.0,
}
BLUE=(.07,.19,.26); GRAY=(.43,.48,.50); TEAL=(.03,.42,.43); ORANGE=(.85,.43,.08)
MM=72/25.4


def load_parameters(path):
    raw=path.read_bytes();layout=json.loads(raw)
    if layout["length_unit"]!="mm":raise ValueError("Expected layout dimensions in mm")
    p=copy.deepcopy(P);lookup={f["id"]:f for f in layout["head"]["fingers"]}
    for variant,fid in (("upper","UR"),("lower","LL")):
        f=lookup[fid]
        p[variant]={"source_finger_id":fid,"length_from_axis":f["length_mm"],"width":f["width_mm"],
            "contact_along":f["contact_along_mm"],"review_angle_deg":f["closure_study_deg"],
            "pad_target_q_deg":f["pad_target_q_deg"],"pad_local_normal_tilt_deg":f["pad_target_q_deg"]-90,
            "source_root_z_mm":f["root_z_mm"],"source_root_radius_mm":f["root_radius_mm"]}
        if f["thickness_mm"]!=p["blade_thickness"]:raise ValueError("Fixture needs review for changed blade thickness")
        if not p["q_min_deg"]<=f["closure_study_deg"]<=p["q_max_deg"]:raise ValueError("Closure angle outside fixture slot")
    p["pad_surface_center_normal"]=layout["head"]["contact_study"]["pad_surface_center_normal_mm"]
    p["source_layout"]={"revision":layout["revision"],"sha256":hashlib.sha256(raw).hexdigest(),
        "file":str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "contact_study":layout["head"]["contact_study"]}
    return p


def cylinder_y(radius, y0, length, x=0, z=0):
    return cq.Solid.makeCylinder(radius,length,cq.Vector(x,y0,z),cq.Vector(0,1,0))


def box_at(dx,dy,dz,x,y,z):
    return cq.Workplane("XY").box(dx,dy,dz,centered=(False,False,False)).translate((x,y,z)).val()


def slot_shape(p):
    r=p["stop_radius"]; w=p["stop_slot_width"]; pin=p["pin_nominal_diameter"]
    if not 0<pin<w or p["q_max_deg"]-p["q_min_deg"]>=180:
        raise ValueError("Slot assumes positive clearance and an arc shorter than 180 degrees")
    # Capsule end-cap clearance would otherwise permit overtravel. Shift the
    # cap centers inward so the nominal 3 mm pin meets the specified endpoints.
    beta=2*math.asin(((w-pin)/2)/(2*r))
    a=math.radians(p["q_min_deg"])+beta; b=math.radians(p["q_max_deg"])-beta
    y0=p["fork_gap"]/2-.1; thickness=p["cheek_thickness"]+.2
    annulus=cylinder_y(r+w/2,y0,thickness).cut(cylinder_y(r-w/2,y0-.1,thickness+.2))
    far=100.0
    wedge=cq.Workplane("XZ").polyline([(0,0),(far*math.cos(a),far*math.sin(a)),
        (far*math.cos(b),far*math.sin(b))]).close().extrude(thickness).translate((0,y0+thickness,0)).val()
    arc=annulus.intersect(wedge)
    for q in (a,b):
        arc=arc.fuse(cylinder_y(w/2,y0,thickness,r*math.cos(q),r*math.sin(q)))
    return arc,math.degrees(beta)


def base_part(p):
    length,width,t=p["base_length"],p["base_width"],p["base_thickness"]
    base=cq.Workplane("XY").box(length,width,t,centered=(True,True,False)).edges("|Z").fillet(4).val()
    for x,y in p["base_mount_holes"]:
        base=base.cut(cq.Solid.makeCylinder(p["base_mount_hole_diameter"]/2,t+2,cq.Vector(x,y,-1)))
    gap=p["fork_gap"]; thick=p["cheek_thickness"]; h=p["pivot_height"]
    right=cylinder_y(p["dial_radius"],gap/2,thick,z=h)
    left=cylinder_y(p["left_cheek_radius"],-gap/2-thick,thick,z=h)
    for y0 in (gap/2,-gap/2-thick):
        base=base.fuse(box_at(24,thick,h-t,-12,y0,t))
    base=base.fuse(right).fuse(left)
    base=base.cut(cylinder_y(p["axis_print_pilot_diameter"]/2,-20,40,z=h))
    slot,beta=slot_shape(p)
    base=base.cut(slot.translate((0,0,h)))
    # Recessed radial ticks on the outside of the dial; marked values are
    # explained in the PDF. They do not penetrate the 6 mm cheek.
    ticks=sorted(set(list(range(0,int(p["q_max_deg"])+1,15))+[p["q_max_deg"]]))
    for q in ticks:
        major=q in (0,90,p["q_max_deg"]); inner=23.5 if major else 25.0
        tick=box_at(28-inner,.7,.5,inner,gap/2+thick-.6,-.25)
        tick=tick.rotate((0,0,0),(0,-1,0),q).translate((0,0,h))
        base=base.cut(tick)
    # Inward (-X) arrow on the base; geometry only, no CAD-font dependency.
    arrow=cq.Workplane("XY").polyline([(-22,-1.3),(-39,-1.3),(-39,-4),(-47,0),(-39,4),(-39,1.3),(-22,1.3)]).close().extrude(.8).translate((0,0,t-.6)).val()
    return base.cut(arrow).clean(),beta


def rotor_part(p):
    rw=p["rotor_width"]
    hub=cylinder_y(p["rotor_radius"],-rw/2,rw)
    x0,x1=p["rotor_tongue_x_limits"]; z0,z1=p["rotor_tongue_z_limits"]
    hub=hub.fuse(box_at(x1-x0,rw,z1-z0,x0,-rw/2,z0))
    for x in (0,p["stop_radius"]):
        hub=hub.cut(cylinder_y(p["axis_print_pilot_diameter"]/2,-rw/2-1,rw+2,x=x))
    for x in p["blade_mount_holes_x"]:
        hub=hub.cut(cq.Solid.makeCylinder(p["blade_mount_hole_diameter"]/2,20,cq.Vector(x,0,-12)))
    return hub.clean()


def blade_outline(p,variant):
    spec=p[variant]; L=spec["length_from_axis"]; w=spec["width"]
    root=p["blade_root_x"]
    return [(root,-6),(root+16,-6),(root+28,-w/2),(L-10,-w/2),(L,-w/2+8),
            (L,w/2-8),(L-10,w/2),(root+28,w/2),(root+16,6),(root,6)]


def blade_part(p,variant):
    spec=p[variant]; L=spec["length_from_axis"]; w=spec["width"]; t=p["blade_thickness"]
    blade=cq.Workplane("XY").polyline(blade_outline(p,variant)).close().extrude(t).val()
    for x in p["blade_mount_holes_x"]:
        blade=blade.cut(cq.Solid.makeCylinder(p["blade_mount_hole_diameter"]/2,t+2,cq.Vector(x,0,-1)))
    # One shallow luminous-face witness region. The proud pad is an integral
    # printed geometry marker; neither is an actual LED or qualified pad.
    recess=box_at(L-68,w-12,p["led_recess_depth"]+.1,58,-(w-12)/2,t-p["led_recess_depth"])
    blade=blade.cut(recess)
    s=spec["contact_along"]; half=p["pad_length"]/2; h=p["pad_surface_center_normal"]
    slope=-math.tan(math.radians(spec["pad_local_normal_tilt_deg"]))
    pad=cq.Workplane("XZ").polyline([(s-half,t-p["led_recess_depth"]),(s+half,t-p["led_recess_depth"]),
        (s+half,h+half*slope),(s-half,h-half*slope)]).close().extrude(p["pad_width"]).translate((0,p["pad_width"]/2,0)).val()
    return blade.fuse(pad).clean()


def pose(shape,p,q):
    return shape.rotate((0,0,0),(0,-1,0),q).translate((0,0,p["pivot_height"]))


def contact_pose(p,variant,q):
    angle=math.radians(q); s=p[variant]["contact_along"]
    d=p["pad_surface_center_normal"];alpha=math.radians(p[variant]["pad_local_normal_tilt_deg"])
    return {"variant":variant,"q_deg":q,"contact_center_mm":[s*math.cos(angle)-d*math.sin(angle),0,
        p["pivot_height"]+s*math.sin(angle)+d*math.cos(angle)],
        "light_face_outward_normal":[-math.sin(angle),0,math.cos(angle)],
        "wedge_contact_outward_normal":[math.sin(alpha-angle),0,math.cos(angle-alpha)],
        "normal_points_toward_palm_minus_X":q>0 and q<180}


def bbox(shape):
    # Explicitly ignore cached STL triangulation: default OCC/CQ bounding can
    # change after tessellation and report a small artificial bounding margin.
    b=Bnd_Box();BRepBndLib.AddOptimal_s(shape.wrapped,b,False,False)
    return list(b.Get())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_part(name,shape,print_shape,out):
    step=out/"STEP"/(name+".step"); stl=out/"STL"/(name+"-print.stl")
    cq.exporters.export(shape,str(step)); cq.exporters.export(print_shape,str(stl),tolerance=.035,angularTolerance=.08)
    rd=cq.importers.importStep(str(step)).val()
    mesh=trimesh.load(stl,force="mesh",process=True)
    volume=shape.Volume(); rel=abs(mesh.volume-volume)/volume
    b=bbox(shape); pb=bbox(print_shape)
    checks={"step_valid":rd.isValid(),"step_solids":len(rd.Solids()),
        "step_volume_relative_error":abs(rd.Volume()-volume)/volume,
        "stl_watertight":bool(mesh.is_watertight),"stl_winding_consistent":bool(mesh.is_winding_consistent),
        "stl_body_count":int(mesh.body_count),"stl_volume_relative_error":float(rel),
        "stl_bounds_max_error_mm":float(np.max(np.abs(mesh.bounds.flatten()-np.array([pb[:3],pb[3:]]).flatten()))),
        "step_bounds_max_error_mm":float(np.max(np.abs(np.array(bbox(rd))-np.array(b)))),
        "print_min_z_mm":pb[2],"volume_mm3":volume,
        "native_bounds_mm":b,"print_bounds_mm":pb,
        "sha256":{str(step.relative_to(out)):sha(step),str(stl.relative_to(out)):sha(stl)}}
    assert checks["step_valid"] and checks["step_solids"]==1
    assert checks["step_volume_relative_error"]<1e-7 and checks["step_bounds_max_error_mm"]<1e-5,(name,checks)
    assert checks["stl_watertight"] and checks["stl_winding_consistent"] and checks["stl_body_count"]==1
    assert checks["stl_volume_relative_error"]<.004 and checks["stl_bounds_max_error_mm"]<.05
    assert abs(pb[2])<1e-6
    return checks


def assembly_shapes(p,parts,variant,q):
    main_axis=cylinder_y(1.5,-12.1,35,z=p["pivot_height"])
    pin=pose(cylinder_y(1.5,-5.5,25,x=p["stop_radius"]),p,q)
    return [("base",parts["base"],(.23,.29,.32)),("rotor",pose(parts["rotor"],p,q),(.52,.59,.61)),
            (variant,pose(parts[variant],p,q),(.79,.61,.32)),
            ("axis_reference_only",main_axis,(.7,.72,.75)),("stop_pin_reference_only",pin,(.7,.72,.75))]


def export_assembly(p,parts,variant,q,out):
    entries=assembly_shapes(p,parts,variant,q)
    name=f"assembly-{variant}-q{q:07.3f}".replace(".","p")
    asm=cq.Assembly(name=name)
    for item,shape,color in entries:asm.add(shape,name=item,color=cq.Color(*color))
    dest=out/"STEP"/(name+".step");asm.save(str(dest))
    reimport=cq.importers.importStep(str(dest)).val()
    assert reimport.isValid() and len(reimport.Solids())==5
    return {"file":str(dest.relative_to(out)),"step_valid":reimport.isValid(),"solids":len(reimport.Solids()),
            "q_deg":q,"variant":variant,"hardware_caveat":"Only smooth 3 mm shaft/pin reference cylinders; screw heads, nuts, washers and blade screws are specified in BOM, not represented by vendor CAD."}


def mesh_preview(entries,path):
    fig=plt.figure(figsize=(9,6.5),dpi=150);ax=fig.add_subplot(111,projection="3d",computed_zorder=False)
    allpoints=[];alltris=[];allcolors=[]
    for _,shape,color in entries:
        v,f=shape.tessellate(.20,.16);vertices=np.array([x.toTuple() for x in v]);faces=np.array(f)
        mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=True);mesh.fix_normals()
        camera=np.array([math.cos(math.radians(20))*math.cos(math.radians(132)),math.cos(math.radians(20))*math.sin(math.radians(132)),math.sin(math.radians(20))])
        front=mesh.face_normals@camera>0
        tris=mesh.triangles[front];norm=mesh.face_normals[front]
        light=np.array([-.5,.3,.8]);light/=np.linalg.norm(light)
        shade=.65+.35*np.clip(norm@light,0,1)
        rgba=np.column_stack([np.array(color)[None,:]*shade[:,None],np.ones(len(tris))])
        alltris.append(tris);allcolors.append(rgba);allpoints.append(vertices)
    # Sort triangles across all parts together; object-level painting would
    # incorrectly draw a rear rotor over the front dial and hide its arc slot.
    poly=Poly3DCollection(np.vstack(alltris),facecolors=np.vstack(allcolors),edgecolors="none",linewidths=0,antialiaseds=False,zsort="average")
    ax.add_collection3d(poly)
    v=np.vstack(allpoints);lo=v.min(0);hi=v.max(0);center=(lo+hi)/2;span=max(hi-lo)*1.05
    ax.set_xlim(center[0]-span/2,center[0]+span/2);ax.set_ylim(center[1]-span/2,center[1]+span/2);ax.set_zlim(0,span)
    ax.set_box_aspect([1,1,1]);ax.view_init(elev=20,azim=132);ax.set_axis_off()
    fig.subplots_adjust(0,0,1,1);fig.savefig(path,dpi=150,facecolor="white",bbox_inches="tight",pad_inches=.02);plt.close(fig)


def qa_motion(p,parts):
    results=[];base=parts["base"]
    angles=sorted(set([i*2.5 for i in range(int(p["q_max_deg"]/2.5)+1)]+[p[v][k] for v in ("upper","lower") for k in ("review_angle_deg","pad_target_q_deg")]))
    for variant in ("upper","lower"):
        worst=0.0; worst_q=None
        for q in angles:
            moving=pose(parts["rotor"],p,q).fuse(pose(parts[variant],p,q))
            interference=moving.intersect(base).Volume()
            if interference>worst:worst=interference;worst_q=q
            assert interference<1e-5,(variant,q,interference)
        results.append({"variant":variant,"sampled_angles_deg":angles,"base_moving_interference_max_mm3":worst,
                        "angle_of_max_interference_deg":worst_q,"passes_sampled_interference_test":True})
    slot_checks=[]
    for q in (-1.,0.,1.,90.,p["q_max_deg"]-1,p["q_max_deg"],p["q_max_deg"]+1):
        pin=pose(cylinder_y(p["pin_nominal_diameter"]/2,p["fork_gap"]/2,p["cheek_thickness"],x=p["stop_radius"]),p,q)
        volume=pin.intersect(base).Volume()
        expected=(q<p["q_min_deg"] or q>p["q_max_deg"])
        assert (volume>.01) if expected else (volume<1e-5),(q,volume)
        slot_checks.append({"q_deg":q,"pin_cheek_interference_mm3":volume,
                            "expected_interference_beyond_stop":expected,"passed":True})
    return {"motion_sampling":results,"nominal_stop_contact_checks":slot_checks,
            "scope":"Ideal CAD geometry and nominal 3 mm pin only. Samples do not constitute continuous collision proof; tolerances, print deformation and hand forces are unverified."}


def qa_dimensions(p,parts):
    """Compare dimensions and hole axes to the design table, not just roundtrip."""
    expected={"base":[-p["base_length"]/2,-p["base_width"]/2,0,p["base_length"]/2,p["base_width"]/2,p["pivot_height"]+p["dial_radius"]],
              "rotor":[-p["rotor_radius"],-p["rotor_width"]/2,-p["rotor_radius"],p["rotor_tongue_x_limits"][1],p["rotor_width"]/2,p["rotor_radius"]]}
    for v in ("upper","lower"):
        padmax=p["pad_surface_center_normal"]+p["pad_length"]/2*abs(math.tan(math.radians(p[v]["pad_local_normal_tilt_deg"])))
        expected[v]=[p["blade_root_x"],-p[v]["width"]/2,0,p[v]["length_from_axis"],p[v]["width"]/2,padmax]
    bounds=[];holes=[]
    for name,shape in parts.items():
        error=max(abs(a-b) for a,b in zip(bbox(shape),expected[name]))
        assert error<1e-6,(name,error)
        bounds.append({"part":name,"expected_bounds_mm":expected[name],"max_error_mm":error,"passed":True})
        wanted=[]
        if name=="base":
            wanted.extend((f"table_{i}",[x,y,0],[0,0,1],p["base_mount_hole_diameter"]/2,1) for i,(x,y) in enumerate(p["base_mount_holes"],1))
            wanted.append(("main_axis",[0,0,p["pivot_height"]],[0,1,0],p["axis_print_pilot_diameter"]/2,2))
        if name=="rotor":
            wanted.extend((label,[x,0,0],[0,1,0],p["axis_print_pilot_diameter"]/2,1) for label,x in (("main_axis",0),("stop_pin",p["stop_radius"])))
        if name in ("rotor","upper","lower"):
            wanted.extend((f"blade_{i}",[x,0,0],[0,0,1],p["blade_mount_hole_diameter"]/2,1) for i,x in enumerate(p["blade_mount_holes_x"],1))
        cyls=[]
        for face in shape.Faces():
            if face.geomType()=="CYLINDER":
                cy=BRepAdaptor_Surface(face.wrapped).Cylinder();loc=cy.Location();axis=cy.Axis().Direction()
                cyls.append((cy.Radius(),np.array([loc.X(),loc.Y(),loc.Z()]),np.array([axis.X(),axis.Y(),axis.Z()])))
        for label,center,direction,radius,count in wanted:
            center=np.array(center);direction=np.array(direction);matches=0
            for r,loc,axis in cyls:
                if abs(r-radius)<1e-7 and np.linalg.norm(np.cross(direction,axis))<1e-7 and np.linalg.norm(np.cross(loc-center,direction))<1e-7:matches+=1
            assert matches==count,(name,label,matches,count)
            holes.append({"part":name,"hole":label,"radius_mm":radius,"axis":direction.tolist(),"axis_point_mm":center.tolist(),"expected_cylindrical_faces":count,"matched_faces":matches,"passed":True})
    return {"bounds":bounds,"hole_axes_and_diameters":holes,"passed":True}


def qa_wedges(p,parts):
    results=[]
    for variant in ("upper","lower"):
        spec=p[variant];alpha=math.radians(spec["pad_local_normal_tilt_deg"])
        expected_normal=np.array([math.sin(alpha),0,math.cos(alpha)])
        expected_center=np.array([spec["contact_along"],0,p["pad_surface_center_normal"]])
        matches=[]
        for face in parts[variant].Faces():
            if face.geomType()=="PLANE":
                normal=np.array(face.normalAt().toTuple());center=np.array(face.Center().toTuple())
                if np.linalg.norm(normal-expected_normal)<1e-7 and np.linalg.norm(center-expected_center)<1e-7:matches.append(face)
        assert len(matches)==1,(variant,len(matches))
        at_target=contact_pose(p,variant,spec["pad_target_q_deg"])
        assert np.linalg.norm(np.array(at_target["wedge_contact_outward_normal"])-[-1,0,0])<1e-12
        transformed=matches[0].rotate((0,0,0),(0,-1,0),spec["pad_target_q_deg"])
        cad_normal=np.array(transformed.normalAt().toTuple());cad_center=np.array(transformed.Center().toTuple())
        assert np.linalg.norm(cad_normal-[-1,0,0])<1e-7
        head_r=cad_center[0]+spec["source_root_radius_mm"]
        head_z=cad_center[2]+spec["source_root_z_mm"]
        study=p["source_layout"]["contact_study"]
        assert abs(head_r-study["target_radius_mm"])<1e-7
        assert abs(head_z-study["target_common_contact_z_mm"])<1e-7
        results.append({"variant":variant,"local_surface_center_mm":expected_center.tolist(),
            "local_surface_normal":expected_normal.tolist(),"surface_matches":len(matches),
            "target_q_deg":spec["pad_target_q_deg"],"local_normal_tilt_deg":spec["pad_local_normal_tilt_deg"],
            "normal_at_target_q":at_target["wedge_contact_outward_normal"],
            "transformed_CAD_face_normal":cad_normal.tolist(),
            "projected_head_contact_radius_mm":head_r,"projected_head_contact_z_mm":head_z,
            "projection_scope":"Coordinate projection to source head; fixture does not physically reproduce multiple roots or simultaneous contacts.","passed":True})
    return results


def line(c,x1,y1,x2,y2,color=BLUE,width=.7,dash=None):
    c.setStrokeColorRGB(*color);c.setLineWidth(width);c.setDash(dash or []);c.line(x1,y1,x2,y2);c.setDash([])


def text(c,x,y,value,size=9,color=BLUE,font="CJK"):
    c.setFont(font,size);c.setFillColorRGB(*color);c.drawString(x,y,str(value))


def arrow(c,x,y,dx,dy,size=4):
    ll=math.hypot(dx,dy);ux,uy=dx/ll,dy/ll;vx,vy=-uy,ux
    p=c.beginPath();p.moveTo(x,y);p.lineTo(x+ux*size+vx*size*.35,y+uy*size+vy*size*.35)
    p.lineTo(x+ux*size-vx*size*.35,y+uy*size-vy*size*.35);p.close();c.setFillColorRGB(*BLUE);c.drawPath(p,stroke=0,fill=1)


def hdim(c,x1,x2,y,fromy,label):
    for x in (x1,x2):line(c,x,fromy,x,y+5,GRAY,.4)
    line(c,x1,y,x2,y);arrow(c,x1,y,1,0);arrow(c,x2,y,-1,0)
    width=pdfmetrics.stringWidth(label,"CJK",9);c.setFillColorRGB(1,1,1);c.rect((x1+x2-width)/2-3,y-3,width+6,12,stroke=0,fill=1)
    text(c,(x1+x2-width)/2,y-2,label)


def vdim(c,y1,y2,x,fromx,label):
    for y in (y1,y2):line(c,fromx,y,x+5,y,GRAY,.4)
    line(c,x,y1,x,y2);arrow(c,x,y1,0,1);arrow(c,x,y2,0,-1);text(c,x+5,(y1+y2)/2-3,label)


def polyline(c,points,color=BLUE,fill=None,width=.8):
    path=c.beginPath();path.moveTo(*points[0])
    for pt in points[1:]:path.lineTo(*pt)
    path.close();c.setStrokeColorRGB(*color);c.setLineWidth(width)
    if fill:c.setFillColorRGB(*fill)
    c.drawPath(path,stroke=1,fill=1 if fill else 0)


def header(c,title,subtitle,page):
    W,H=landscape(A4);text(c,28,H-33,title,18,font="Helvetica-Bold")
    text(c,28,H-55,subtitle,10,color=TEAL);line(c,28,H-68,W-28,H-68,TEAL,1)
    line(c,28,37,W-28,37,GRAY,.6)
    text(c,28,23,"几何台架 / 手动 / 不承载 2 kg / 无电驱动 / 尺寸单位 mm / 非生产图纸",8)
    text(c,W-190,23,f"FF-02  |  2026-09-27  |  {page}/5",8,font="Helvetica")


def pdf_document(p,out,font,bom,checks):
    pdfmetrics.registerFont(TTFont("CJK",str(font)))
    path=out/"PDF"/"finger-fixture-dimensions.pdf";c=canvas.Canvas(str(path),pagesize=landscape(A4))
    c.setTitle("Odradek manual finger geometry fixture FF-02")
    W,H=landscape(A4)
    header(c,"ODRADEK / MANUAL FINGER FIXTURE",f"源 {p['source_layout']['revision']}：上片 140 / 下片 100，从转轴计；每次只装一片。",1)
    c.drawImage(str(out/"PREVIEW"/f"upper-q{p['upper']['review_angle_deg']:g}.png"),20,140,width=440,height=350,preserveAspectRatio=True,anchor="c")
    text(c,42,132,f"真实 CAD 网格：上片 q={p['upper']['review_angle_deg']:g}°",10)
    text(c,42,115,"金属轴/限位销仅用圆柱标识；紧固件头、螺母与垫片见 BOM。",8)
    x0,y0,scale=587,250,1.33
    c.setStrokeColorRGB(*GRAY);c.circle(x0,y0,24*scale,stroke=1,fill=0)
    line(c,x0-60,y0,x0+180,y0,GRAY,.5,[4,3]);line(c,x0,y0-35,x0,y0+180,GRAY,.5,[4,3])
    for q in (0,90,p["upper"]["pad_target_q_deg"],p["q_max_deg"]):
        a=math.radians(q);x=x0+140*scale*math.cos(a);y=y0+140*scale*math.sin(a)
        line(c,x0,y0,x,y,TEAL if q==p["upper"]["pad_target_q_deg"] else GRAY,1.6 if q==p["upper"]["pad_target_q_deg"] else .8)
        text(c,x+4,y+4,f"{q:.2f}°",8,color=TEAL if q==p["upper"]["pad_target_q_deg"] else GRAY)
    text(c,501,478,"右侧观察：+X 向外，+Z 向前",10)
    text(c,501,461,"闭合 q 为绕 -Y 的正旋转",9)
    line(c,585,222,520,222,ORANGE,1.5);arrow(c,520,222,1,0)
    text(c,504,202,"掌心方向 = -X",9,color=ORANGE)
    for i,s in enumerate(["q=0°：灯面朝 +Z。","q=90°：灯面正对掌心 -X。","q>90°：灯面开始带 -Z 分量。","台架不含中央屏幕与对向手指。","观察动作不证明力闭合或承载能力。"]):text(c,501,170-i*18,s,9)
    c.showPage()

    header(c,"01 / BASE AND FORK","支座整体打印，底板平放；Ø3.0 轴孔为先导孔，打印后同轴钻至 Ø3.2。",2)
    cx,cy=242,313;sc=MM
    c.setStrokeColorRGB(*BLUE);c.roundRect(cx-65*sc,cy-38*sc,130*sc,76*sc,4*sc,stroke=1,fill=0)
    for x,y in p["base_mount_holes"]:
        c.circle(cx+x*sc,cy+y*sc,2.75*sc,stroke=1,fill=0)
        line(c,cx+x*sc-5,cy+y*sc,cx+x*sc+5,cy+y*sc,GRAY,.4)
    for half,y0,y1 in ((12,-11.6,-5.6),(28,5.6,11.6)):
        polyline(c,[(cx-half*sc,cy+y0*sc),(cx+half*sc,cy+y0*sc),(cx+half*sc,cy+y1*sc),(cx-half*sc,cy+y1*sc)],fill=(.94,.97,.97))
    text(c,60,449,"俯视：+Z → 台面；比例 1:1",9)
    hdim(c,cx-65*sc,cx+65*sc,cy-38*sc-27,cy-38*sc,"130.0")
    hdim(c,cx-50*sc,cx+50*sc,cy+38*sc+19,cy+28*sc,"安装孔距 100.0")
    vdim(c,cy-38*sc,cy+38*sc,cx-65*sc-25,cx-65*sc,"76.0")
    text(c,60,151,"4 × Ø5.5 THRU：孔中心 (±50, ±28)，相对底板中心。",9)
    text(c,60,131,"底板 6.0 厚；外角 R4；固定到台面或用夹具夹紧后缓慢手动。",8.5)
    text(c,60,111,"本台架未指定台面螺栓、螺母板或夹具，不含热熔嵌件。",8.5)
    sx,sy,sc=622,242,2.55
    c.setStrokeColorRGB(*BLUE);c.rect(sx-65*sc,sy,130*sc,6*sc,stroke=1,fill=0)
    join_z=38-math.sqrt(28**2-12**2)
    start=math.degrees(math.atan2(join_z-38,12))%360
    extent=360-2*math.degrees(math.asin(12/28))
    c.arc(sx-28*sc,sy+10*sc,sx+28*sc,sy+66*sc,startAng=start,extent=extent)
    for side in (-1,1):line(c,sx+side*12*sc,sy+6*sc,sx+side*12*sc,sy+join_z*sc)
    c.circle(sx,sy+38*sc,1.5*sc,stroke=1,fill=0)
    # Actual capsule profile: annular arc plus round end caps, with inset beta.
    c.setStrokeColorRGB(*TEAL);c.setLineWidth(3.6*sc)
    beta=checks["slot_cap_center_inset_deg"];c.setLineCap(1)
    c.arc(sx-18*sc,sy+(38-18)*sc,sx+18*sc,sy+(38+18)*sc,startAng=beta,extent=p["q_max_deg"]-2*beta)
    c.setLineWidth(.8);c.setLineCap(0)
    text(c,488,449,"右视：从 +Y 观察，比例约 0.90:1",9)
    vdim(c,sy,sy+38*sc,sx+31*sc,sx,"轴高 38.0")
    text(c,488,187,"右盘 Ø56 / 厚 6；左耳 Ø24 / 厚 6。",9)
    text(c,488,168,"内净距 11.2；两耳外宽 23.2。",9)
    text(c,488,149,"弧槽中心 R18，槽宽 3.6；名义限位 0–130°。",9)
    text(c,488,130,"端帽中心角内缩约 0.955°，补偿 Ø3 销的间隙。",8)
    text(c,488,111,"槽及角度受打印误差影响；不得强压越过止挡。",8)
    c.showPage()

    header(c,"02 / ROTOR AND PIN LOCATIONS","共用转子；两片灯片通过两个 M3 螺栓替换。图中坐标原点为转轴中心。",3)
    cx,cy,sc=238,302,MM
    c.setStrokeColorRGB(*BLUE)
    zlow,zhigh=p["rotor_tongue_z_limits"]
    upper_angle=math.degrees(math.asin(zhigh/24));lower_angle=math.degrees(math.asin(zlow/24))
    c.arc(cx-24*sc,cy-24*sc,cx+24*sc,cy+24*sc,startAng=upper_angle,extent=360+lower_angle-upper_angle)
    for z in (zlow,zhigh):line(c,cx+math.sqrt(24**2-z*z)*sc,cy+z*sc,cx+54*sc,cy+z*sc)
    line(c,cx+54*sc,cy+zlow*sc,cx+54*sc,cy+zhigh*sc)
    for x in (0,18):c.circle(cx+x*sc,cy,1.5*sc,stroke=1,fill=0)
    for x in (36,48):
        for dx in (-1.6,1.6):line(c,cx+(x+dx)*sc,cy+zlow*sc,cx+(x+dx)*sc,cy+zhigh*sc,GRAY,.5,[3,2])
    line(c,cx-30*sc,cy,cx+58*sc,cy,GRAY,.5,[6,3]);line(c,cx,cy-30*sc,cx,cy+30*sc,GRAY,.5,[6,3])
    hdim(c,cx,cx+54*sc,cy-24*sc-28,cy+zlow*sc,"转轴 → 托舌端 54.0")
    hdim(c,cx,cx+18*sc,cy+24*sc+26,cy,"限位销 R18.0")
    text(c,82,464,"侧视 XZ，比例 1:1；转子沿 Y 厚 10.0。",9)
    text(c,82,169,"圆盘 Ø48；托舌 x=10…54，z=-6…0，y=±5。",9)
    text(c,82,149,"主轴孔与销孔：打印 Ø3.0，完工 Ø3.2，沿 Y 贯通。",9)
    text(c,82,129,"灯片底面 z=0，直接贴托舌上表面；无粘胶固定要求。",8.5)
    tx,ty=481,449
    text(c,tx,ty,"孔中心及方向（转子原生 STEP 坐标）",11,color=TEAL)
    rows=[("主轴", "(0, 0, 0)","沿 Y / Ø3.0 → 3.2"),
          ("限位销","(18, 0, 0)","沿 Y / Ø3.0 → 3.2"),
          ("灯片螺栓 A","(36, 0, -3)","沿 Z / Ø3.2"),
          ("灯片螺栓 B","(48, 0, -3)","沿 Z / Ø3.2")]
    for i,(name,xyz,note) in enumerate(rows):
        y=ty-31-i*43;line(c,tx,y+17,W-34,y+17,GRAY,.4)
        text(c,tx,y,name,9);text(c,tx+93,y,xyz,9,font="Helvetica");text(c,tx+93,y-15,note,8)
    for i,s in enumerate(["轴侧间隙：11.2 − 10.0 − 2×0.5 = 0.2。","装两片约 0.5 mm 的 M3 平垫片在转子两侧。","仅轻调锁紧螺母，保持手动转动；不可夹弯支座。","若垫片/打印尺寸不同，量测后配垫或磨平端面。","打印 STL 已绕 X 旋转 90°，轴孔竖直朝上。","托舌 Ø3.2 横孔可能需钻通清理。"]):text(c,481,220-i*19,s,8.7)
    c.showPage()

    header(c,"03 / INTERCHANGEABLE LIGHT BLADES","浅凹区标识灯面；实体楔面同步整体接触角。均为打印占位，不含 LED、电路或弹性垫。",4)
    for variant,cy in (("upper",379),("lower",184)):
        spec=p[variant];L=spec["length_from_axis"];w=spec["width"];cx=73;sc=MM
        points=[(cx+x*sc,cy+y*sc) for x,y in blade_outline(p,variant)]
        polyline(c,points,fill=(.97,.96,.91))
        c.setStrokeColorRGB(*TEAL);c.rect(cx+58*sc,cy-(w-12)/2*sc,(L-68)*sc,(w-12)*sc,stroke=1,fill=0)
        for x in p["blade_mount_holes_x"]:c.circle(cx+x*sc,cy,1.6*sc,stroke=1,fill=0)
        c.setFillColorRGB(.77,.83,.83);c.setStrokeColorRGB(*BLUE)
        c.rect(cx+(spec["contact_along"]-6)*sc,cy-8*sc,12*sc,16*sc,stroke=1,fill=1)
        line(c,cx,cy-38*sc,cx,cy+31*sc,GRAY,.5,[4,3])
        hdim(c,cx,cx+L*sc,cy-w/2*sc-28,cy,"轴 → 尖端 "+str(int(L)))
        vdim(c,cy-w/2*sc,cy+w/2*sc,cx+L*sc+20,cx+(L-10)*sc,str(int(w)))
        text(c,78,cy+w/2*sc+18,("UPPER 上片" if variant=="upper" else "LOWER 下片")+"  /  俯视 +Z  /  1:1",9)
    tx=541;ty=461
    notes=["两片共用：", "板厚 6.0（z=0…6）；浅凹深 0.8。", "根部 x=30，2×Ø3.2 在 x=36、48。", "楔垫投影 12×16，表面中心 h=11。",
           f"上接触点 x={p['upper']['contact_along']:.3f}，z=11。",
           f"下接触点 x={p['lower']['contact_along']:.3f}，z=11。",
           f"上楔面目标 q={p['upper']['pad_target_q_deg']:.3f}°。",
           f"下楔面目标 q={p['lower']['pad_target_q_deg']:.3f}°。",
           "楔面法线相对板法线倾角 α=q目标-90°。", "在目标 q，楔面法线朝掌心 -X。",
           "单指不验证上下根差 50 或四指避让。", "本体片形与本台架宽片轮廓不同。",
           "台架 0–130° 不等于全爪许可行程。", "打印叶片本体长上 110 / 下 70。"]
    for i,s in enumerate(notes):text(c,tx,ty-i*17,s,9 if i==0 else 8.1,color=TEAL if i==0 else BLUE)
    for variant,xcenter in (("upper",592),("lower",727)):
        alpha=p[variant]["pad_local_normal_tilt_deg"];slope=-math.tan(math.radians(alpha));sc=4.5;y0=113
        outline=[(xcenter-6*sc,y0+5.2*sc),(xcenter+6*sc,y0+5.2*sc),
                 (xcenter+6*sc,y0+(11+6*slope)*sc),(xcenter-6*sc,y0+(11-6*slope)*sc)]
        polyline(c,outline,fill=(.88,.93,.92))
        line(c,xcenter-40,y0+11*sc,xcenter+40,y0+11*sc,GRAY,.4,[3,2])
        text(c,xcenter-44,99,("上" if variant=="upper" else "下")+f" α={alpha:.4f}°",8,color=TEAL)
    text(c,548,75,"楔垫侧视示意：中心 z=11，表面沿 +X 降低。",8)
    c.showPage()

    header(c,"04 / BOM, ASSEMBLY AND GEOMETRY CHECK","所列尺寸是台架候选；普通打印误差会改变间隙与限位。逐项测量，禁止加负载。",5)
    tx=32;y=461
    for x,t in [(tx,"项"),(tx+210,"数量"),(tx+257,"说明")]:text(c,x,y,t,9,color=TEAL)
    line(c,tx,y-8,810,y-8,TEAL,.7)
    for row in bom:
        y-=24;text(c,tx,y,row["description"],8.2);text(c,tx+214,y,row["quantity"],8.2);text(c,tx+257,y,row["note_zh"],8.0)
    y-=25;line(c,tx,y+8,810,y+8,GRAY,.6)
    steps=["1  清理支座槽与所有孔；同轴钻主轴/销先导孔至 Ø3.2；检查底板稳定。",
           "2  每次选一片灯片，用两套 M3×20 + 平垫 + 螺母固定到转子托舌。",
           "3  放入转子两侧垫片，穿 M3×35 主轴；装外侧平垫与锁紧螺母，保留自由转动。",
           "4  将 M3×25 限位销穿过转子与弧槽；外侧螺母仅防脱，不压紧槽板。",
           "5  夹固底座，缓慢从 0° 转到 90°、楔垫目标角、114°/126°、130°，检查灯面与接触凸台。",
           "6  用量角器实测两端角度；记录孔间隙、卡滞、接触点，禁止强推止挡。"]
    for s in steps:y-=19;text(c,tx,y,s,8.4)
    y-=20;text(c,tx,y,"打印建议：PLA/PETG 可做几何样件；层高约 0.20，4 道壁，根部/转子实心；参数须先校准。",8.1)
    y-=17;text(c,tx,y,"只评估无载运动；不装电机，不悬挂工件，不测夹力，不把打印止挡用于急停或保持。",8.1)
    y-=17;text(c,tx,y,"CAD 导入/流形/尺寸与采样干涉检查见 verification.json；这些检查不等于实体测试。",8.1)
    c.showPage();c.save()
    return path


def write_bom(out):
    bom=[
        {"id":"FF-B","description":"打印 U 形支座","quantity":1,"note_zh":"底板平放；含弧槽与刻线"},
        {"id":"FF-R","description":"打印共用转子","quantity":1,"note_zh":"STL 已侧立，主轴孔沿打印 Z"},
        {"id":"FF-U/L","description":"打印上片 / 下片","quantity":"各 1","note_zh":"每次仅安装其中一片；无实际 LED"},
        {"id":"AXIS","description":"M3×35 金属螺栓（主轴）","quantity":1,"note_zh":"优先光杆接触孔壁；不是额定轴承"},
        {"id":"STOP","description":"M3×25 金属螺栓（限位销）","quantity":1,"note_zh":"孔/槽中缓慢运动；不承担夹持力"},
        {"id":"BLADE","description":"M3×20 金属螺栓（换片）","quantity":2,"note_zh":"两孔 x=36/48；灯片贴合托舌"},
        {"id":"NUT","description":"M3 防松螺母","quantity":4,"note_zh":"轴/销处仅防脱；具体厚度实测后核长度"},
        {"id":"WASHER","description":"M3 平垫片，约 0.5 厚","quantity":10,"note_zh":"主轴 4、销 2、灯片螺栓 4；实测配垫"},
    ]
    with (out/"BOM.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=list(bom[0]));w.writeheader();w.writerows(bom)
    return bom


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=ROOT/"engineering/generated/finger-fixture")
    parser.add_argument("--parameters",type=Path,default=ROOT/"engineering/parameters/r4-layout.json")
    parser.add_argument("--font",type=Path,default=Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),help="TrueType font with Chinese glyphs")
    args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
    for folder in ("STEP","STL","PDF","PREVIEW"):(out/folder).mkdir(exist_ok=True)
    p=load_parameters(args.parameters.resolve());base,beta=base_part(p);parts={"base":base,"rotor":rotor_part(p),"upper":blade_part(p,"upper"),"lower":blade_part(p,"lower")}
    for name,shape in parts.items():assert shape.isValid() and len(shape.Solids())==1,name
    printed={"base":parts["base"],"rotor":parts["rotor"].rotate((0,0,0),(1,0,0),90).translate((0,0,5)),
             "upper":parts["upper"],"lower":parts["lower"]}
    reports={name:export_part(name,shape,printed[name],out) for name,shape in parts.items()}
    print("4 STEP/STL parts exported and reimported",flush=True)
    dimensions=qa_dimensions(p,parts);wedge_checks=qa_wedges(p,parts)
    motion=qa_motion(p,parts);print("dimensions, hole axes, sampled motion and nominal hard stops checked",flush=True)
    assemblies=[]
    for variant,q in (("upper",0),("upper",90),("upper",p["upper"]["pad_target_q_deg"]),
                      ("upper",p["upper"]["review_angle_deg"]),("upper",p["q_max_deg"]),
                      ("lower",p["lower"]["pad_target_q_deg"]),("lower",p["lower"]["review_angle_deg"])):
        assemblies.append(export_assembly(p,parts,variant,q,out))
    preview_names=[]
    for variant in ("upper","lower"):
        q=p[variant]["review_angle_deg"];name=f"{variant}-q{q:g}.png";preview_names.append(name)
        mesh_preview(assembly_shapes(p,parts,variant,q),out/"PREVIEW"/name)
    # Remove only stale names owned by this generator, so old geometry cannot
    # be mistaken for the current contact design after a parameter revision.
    assembly_names={Path(a["file"]).name for a in assemblies}
    for old in (out/"STEP").glob("assembly-*.step"):
        if old.name not in assembly_names:old.unlink()
    for pattern in ("upper-q*.png","lower-q*.png"):
        for old in (out/"PREVIEW").glob(pattern):
            if old.name not in preview_names:old.unlink()
    contacts=[contact_pose(p,v,q) for v in ("upper","lower") for q in (0,90,p[v]["pad_target_q_deg"],p[v]["review_angle_deg"],p["q_max_deg"])]
    bom=write_bom(out)
    hole_rows=[]
    for i,(x,y) in enumerate(p["base_mount_holes"],1):hole_rows.append(["base",f"mount_{i}",x,y,0,0,0,1,5.5,5.5])
    for part in ("base","rotor"):
        h=p["pivot_height"] if part=="base" else 0
        hole_rows.append([part,"axis",0,0,h,0,1,0,3.0,3.2])
    hole_rows.append(["rotor","stop_pin",18,0,0,0,1,0,3.0,3.2])
    for part in ("rotor","upper","lower"):
        for i,x in enumerate((36,48),1):hole_rows.append([part,f"blade_mount_{i}",x,0,-3 if part=="rotor" else 3,0,0,1,3.2,3.2])
    with (out/"hole-coordinates.csv").open("w",newline="") as f:
        w=csv.writer(f);w.writerow(["part","hole","x_mm","y_mm","z_mm","axis_x","axis_y","axis_z","CAD_d_mm","finish_d_mm"]);w.writerows(hole_rows)
    verification={"revision":p["revision"],"status":"CAD geometry checks only; no physical validation; no 2 kg capability",
        "parameters":p,"slot_cap_center_inset_deg":beta,"parts":reports,"assemblies":assemblies,
        "motion":motion,"dimensions_and_holes":dimensions,"wedge_surface_checks":wedge_checks,"contact_geometry":contacts,
        "nominal_fastener_stack_mm":{"axis":{"grip_outer_cheeks":23.2,"external_washers":1.0,"assumed_nut":3.9,"under_head_length":35,"nominal_protrusion":6.9},
          "stop":{"rotor_plus_side_gap_plus_cheek":16.6,"washers":1.0,"assumed_nut":3.9,"under_head_length":25,"nominal_protrusion":3.5},
          "blade":{"blade_plus_tongue":12.0,"washers":1.0,"assumed_nut":3.9,"under_head_length":20,"nominal_protrusion":3.1}},
        "dependencies":{"cadquery":cq.__version__,"trimesh":trimesh.__version__,"numpy":np.__version__},
        "all_checked_parts_valid":True,"limitations":["Fastener dimensions are generic candidates; vendor fit, grade and installed nut thickness unverified.",
            "Nominal stop angles depend on actual pin diameter and printed slot geometry.","No motor, LED, thermal insert, bearing or elastomer pad selected.",
            "No force closure, holding force, strength, fatigue or powered motion qualification.","Sampled interference checks are not a continuous collision proof."]}
    pdf_document(p,out,args.font,bom,verification)
    (out/"verification.json").write_text(json.dumps(verification,indent=2,ensure_ascii=False)+"\n")
    (out/"parameters.json").write_text(json.dumps(p,indent=2,ensure_ascii=False)+"\n")
    readme=f'''# 单指手动几何台架 FF-02

**仅用于几何验证，不承 2 kg 工件，不安装电机，不测试夹力。**

目的：用一个手动自由度观察灯面朝向、接触垫中心和闭合角；四指协同、力闭合、屏幕/相机避让不在本件范围内。

当前从 `{p['source_layout']['revision']}` 自动读取 UR/LL 的长度、宽度、接触位置、楔垫目标角与闭合候选角，输入 SHA-256 记录在 `parameters.json`。台架的 0–130° 行程仅为实验余量，不代表整头四指许可行程。

## 文件

- `PDF/finger-fixture-dimensions.pdf`：5 页尺寸、孔位、装配与 BOM；尺寸优先，1:1 页需按实际大小打印。
- `STEP/`：4 个独立零件及 7 个装配姿态，单位 mm；主轴/销仅为圆柱参考，没有完整厂商紧固件模型。
- `STL/*-print.stl`：已放平的打印文件，单位约定 mm；底板/灯片背面放床，转子侧面放床。STL 本身不编码单位。
- `BOM.csv`、`hole-coordinates.csv`、`parameters.json`：采购候选、原生 STEP 孔坐标和参数。
- `verification.json`：STEP 回读、STL 封闭流形/尺寸、角度采样干涉、限位与接触坐标。
- `PREVIEW/`：由真实 CAD 网格渲染的上/下片姿态。

## 装配边界

先把主轴/销的 Ø3.0 打印先导孔同轴钻至 Ø3.2，清理弧槽。每次只装上片或下片之一，用两套 M3×20 固定在共用转子上。主轴用 M3×35、销用 M3×25；平垫和防松螺母按 BOM。不要用螺母夹弯 U 形支座：两侧各 0.5 mm 平垫时，转子名义剩余轴向间隙仅 0.2 mm，必须实测后调整。

刻线以 +X 向外为 0°，+Z 向前为 90°，最后一条长刻线为 130°；小刻线每 15°，最后一格 120→130° 为 10°。底座箭头指向掌心 -X。弧槽端帽已按 Ø3.0 名义销补偿间隙，实体角度仍需量角器测量，不应强压止挡。锁紧销螺母仅防脱，不能压住槽板。

灯片从转轴算的长度是 140/100 mm，打印叶片本身从 x=30 开始，实际长 110/70 mm。**当前接触中心**：上 x={p['upper']['contact_along']:.6f}、下 x={p['lower']['contact_along']:.6f}，均为本地 z=11 mm。旧 90/70 mm 平垫不再用于此台架。板面 z=6，浅凹区只是灯面标识；一体楔面是几何占位，不是 LED 或弹性防滑垫。

上楔面法线相对板法线倾角 {p['upper']['pad_local_normal_tilt_deg']:.6f}°，下为 {p['lower']['pad_local_normal_tilt_deg']:.6f}°；在上 q={p['upper']['pad_target_q_deg']:.6f}°、下 q={p['lower']['pad_target_q_deg']:.6f}° 时，楔面法线恰朝本地掌心 -X。全闭合候选角分别 {p['upper']['review_angle_deg']:g}°/{p['lower']['review_angle_deg']:g}°，与楔面目标接触角不是同一概念。CAD QA 核对了实际楔面平面的中心和法线。

本台架单独安装一片，**不复现两组根部的 50 mm 高差、四指同时接触或当前本体收尖片形**。中心楔面只标记单指接触中心与法线，不复现本体双垫面积。它的宽片轮廓为便于打印和观察的工具形状；共同 z=110、Ø80 工件接触与相邻片避让仍必须在整体模型/台架验证。

打印材料、方向和孔隙决定实际行为。PLA/PETG 建议仅作首轮外观/装配样件，约 0.20 mm 层高、4 道壁，转子和根部可用实心；这些建议不是承载工艺规范。无需热熔嵌件，未选定轴承。将台架夹固到台面后缓慢手动，记录实测限位角、间隙和卡滞。

## 复现

```bash
python engineering/build_finger_fixture.py --font /path/to/Chinese-capable.ttf
```

依赖 CadQuery、trimesh、NumPy、Matplotlib、ReportLab、Pillow；版本见 `verification.json`。默认输出本目录，可用 `--output` 改目录；`--parameters` 指定整体参数输入。脚本独立于本体 `build_layout.py`；不会修改共享参数或本体 CAD。数值和 CAD QA 不等于实体通过。
'''
    (out/"README.md").write_text(readme)
    print(f"created {out}: 4 printable parts, 7 assemblies, 5-page PDF; CAD checks passed")


if __name__=="__main__":main()
