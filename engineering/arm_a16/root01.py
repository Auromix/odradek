# SPDX-License-Identifier: CC-BY-NC-4.0
"""Simple plate/spacer J1 root with native RS03 patterns and B06 datum."""
import json,math,csv
import numpy as np
import cadquery as cq
import common as c
g=c.cad;OUT=c.OUT/'root01';OUT.mkdir(exist_ok=True);g.OUT=OUT
g.PARTS.clear();g.SHAPES.clear()

def holes(s,points,d,z,h):
    for x,y in points:s=g.drill(s,[x,y,z-.1],[0,0,1],d,h+.2)
    return s

def main():
    context=c.base_context();(c.OUT/'base-context.json').write_text(json.dumps(context,indent=2)+'\n')
    cols=[(60,0),(0,60),(-60,0),(0,-60)]
    base=[(60*math.cos(math.radians(22.5+45*k)),60*math.sin(math.radians(22.5+45*k))) for k in range(8)]
    fixed=c.SRC['models']['RS03']['fixed_front_fasteners']['raw_step_xy_mm']
    output=c.SRC['models']['RS03']['output_fasteners']['raw_step_xy_mm']
    p=holes(g.ring([0,0,58],[0,0,1],67,28,8),base,6.6,58,8)
    p=holes(p,cols,5.6,58,8)
    for x,y in cols:
        pocket=cq.Workplane('XY',origin=(x,y,61)).polygon(6,8.3/math.cos(math.pi/6)).extrude(5.1).val()
        p=p.cut(pocket)
    g.add('A16-R101-base-adapter',p,0,frame='world',note='OD134; PCD120 8xD6.6 phase22.5; 4xD5.6 at cardinal phase with top-entry AF8.3 depth5 captive M5 nuts; boreD56. Install above B06 neck.')
    p=holes(g.ring([0,0,-2.5],[0,0,1],67,36.2,6),fixed,4.5,-2.5,6)
    p=holes(p,cols,5.6,-2.5,6)
    p=c.root_wire_slots(p,-2.5,6)
    g.add('A16-R102-J1-front-holder',p,0,frame='J1.fixed',note='RS03 front at rawZ35; use front tap drills rawZ26..34.5, not same-PCD rear holes. Ring ID72.4 clears output D70; thickness6mm.')
    # Conventional turned pedestal with a thin upper load plate. Small lower
    # disc leaves an independent static-annulus radial clearance of 1.2mm.
    p=g.cyl([0,0,0],[0,0,1],35,20).fuse(g.cyl([0,0,20],[0,0,1],60,10)).clean()
    p=holes(p,output,4.5,0,30)
    # Recess gives each output screw exactly20mm plate grip, rather than30.
    for x,y in output:p=g.drill(p,[x,y,20],[0,0,1],9.5,10.1)
    # Four ordinary through holes for the upcoming shoulder carrier.
    p=holes(p,[(x,y) for x in [-38,38] for y in [-28,28]],5.6,20,10)
    p=c.root_wire_slots(p,20,10)
    g.add('A16-R103-J1-output-pedestal',p,1,frame='J1.rotor',note='One-piece lathe/mill geometry; broad upper plate DOWN, motor contact UP for supported unloaded fit. D70x20 stem, D120x10 upper plate; six recessed M4x25.')
    for k,(x,y) in enumerate(cols,1):
        p=g.ring([x,y,66],[0,0,1],6,3,96.5)
        g.add(f'A16-R104-spacer-{k}',p,0,role='purchased_structure',material='stock steel precision tube OD12 ID6 (wall3), cut length96.5 +0/-0.1mm',frame='world',mass=p.Volume()*7.85e-6,note='Purchase metal spacer for prototype as well; do not print as a loaded column. Tube covers captive nut and bears on plate around the pocket.')
    hardware=[dict(part='M6x20 ISO4762 + DIN125 washer',qty=8,interface='B06/R101',grip_mm=8,washer_mm=1.6,engagement_mm=10.4,minimum_source_depth_mm=None,note='Base has THRU thread; underside tip clearance needs assembled verification.'),
      dict(part='M4x12 ISO4762 + washer0.8',qty=8,interface='RS03 front/R102',grip_mm=6,washer_mm=.8,engagement_mm=5.2,minimum_source_depth_mm=8),
      dict(part='M4x25 ISO4762 + washer0.8',qty=6,interface='RS03 output/R103',grip_mm=20,washer_mm=.8,engagement_mm=4.2,minimum_source_depth_mm=6),
      dict(part='M5x110 ISO4762 + washer1.0 + nut4.7',qty=4,interface='R102/spacer/R101 captive nut',grip_mm=102.8,washer_mm=1,nut_mm=4.7,nominal_tip_protrusion_mm=1.5,note='Top holder6 + spacer96.5 + pocket roof gap0.3 + washer1 + nut4.7; tip atZ59.5,1.5mm above unchanged base plane58. No lower washer in captive pocket.')]
    for h in hardware:
        if h.get('minimum_source_depth_mm') is not None:assert .5<h['engagement_mm']<h['minimum_source_depth_mm']-.5
    summary=[]
    for p in g.PARTS:
        assert p['solid_count']==1
        summary.append({k:v for k,v in p.items() if k not in ['vertices_mm','triangles']})
    result=dict(revision='A16-ROOT01',layout=c.L,base_context=context,parts=summary,hardware=hardware,
      simple_structure='Two flat annular plates, four stock tube spacers, one coaxial pedestal, ordinary bolts.',
      wire_passages={'parts':['R102','R103 upper plate','S101 foot'],'capsule_mm':[6,14],'end_radius_mm':3,'centre_radius_mm':55,'angles_deg':[55,235],'effective_allocation_mm':[4,10],'allocation_centre_radius_mm':55.5,'scope':'Only peripheral plate slots. Internal actuator shafts remain solid; rotating loop, exact connectors and actual wires not qualified.'},
      theoretical_mating_checks={'adapter_neck_radial_gap_mm':1,'plate_to_B06_bore_mm':0,'static_holder_rotor_radial_gap_mm':1.2,'motor_rear_to_adapter_top_mm':42.4,'columns_to_RS03_max_envelope_radial_gap_mm':1,'column_screw_tip_above_base_mm':1.5,'fixed_front_holes_corrected_axial_span_raw_mm':[26,34.5]},
      print_process={'material':'PETG or PA12 for supported fit; coupons before full prints','nozzle_mm':.4,'layer_mm':.2,'perimeters':5,'top_bottom_layers':6,'infill_percent':35,'orientation':'R101/R102 flat; R103 broad upper plate down, motor contact face up','support':'R103 is inverted to avoid25mm peripheral overhang.2.5mm internal counterbore ledges need slicer/bridge check and final drilling. Keep mating faces clear of brim.'},
      acceptance='Supported unpowered no-payload dimensional/assembly validation only; metal stock spacers. Neither PETG nor nominal metal density makes this a3kg-rated product.',
      assembly_qualified=False,wiring_qualified=False,loads_qualified=False,production_release=False)
    (OUT/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (OUT/'meshes.json').write_text(json.dumps(g.PARTS,separators=(',',':'))+'\n')
    with (OUT/'hardware.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=['part','qty','interface','grip_mm','washer_mm','engagement_mm','minimum_source_depth_mm','nut_mm','nominal_tip_protrusion_mm','note']);w.writeheader();w.writerows(hardware)
    print('ROOT_CAD_DONE',len(summary),'native pattern and base source verified',flush=True)

if __name__=='__main__':main()
