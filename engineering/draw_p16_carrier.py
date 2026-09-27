#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Original nominal interface drawings; deliberately not manufacturing release."""
from pathlib import Path
import math,json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'engineering/generated/p16-carrier-01'
W,H=landscape(A3);c=canvas.Canvas(str(OUT/'P16-CARRIER-01-interface-drawings.pdf'),pagesize=(W,H))
NAVY=colors.HexColor('#182d3e');TEAL=colors.HexColor('#007c83');GRAY=colors.HexColor('#52616b')

def text(x,y,s,size=10,col=GRAY):
 c.setFillColor(col);c.setFont('Helvetica',size);c.drawString(x*mm,y*mm,s)
def line(x1,y1,x2,y2,col=GRAY,width=.7):
 c.setStrokeColor(col);c.setLineWidth(width);c.line(x1*mm,y1*mm,x2*mm,y2*mm)
def rect(x,y,w,h,fill=False):
 c.setStrokeColor(TEAL);c.setFillColor(colors.HexColor('#e8f1f2'));c.rect(x*mm,y*mm,w*mm,h*mm,stroke=1,fill=fill)
def circ(x,y,r):
 c.setStrokeColor(TEAL);c.circle(x*mm,y*mm,r*mm,stroke=1,fill=0)
def dim(x1,y1,x2,y2,s):
 line(x1,y1,x2,y2);dx,dy=x2-x1,y2-y1;L=math.hypot(dx,dy);nx,ny=-dy/L,dx/L
 for x,y in [(x1,y1),(x2,y2)]:line(x-2*nx,y-2*ny,x+2*nx,y+2*ny)
 text((x1+x2)/2+2,(y1+y2)/2+2,s,9)
def page(n,title):
 text(14,282,'ODRADEK / P16-CARRIER-01',12,TEAL);text(14,269,title,22,NAVY)
 line(14,262,406,262);text(14,11,'NOMINAL STUDY - NOT FOR MANUFACTURE / mm unless stated / CC BY-NC 4.0',9)
 text(14,6,'Odradek - Auromix contributors | https://github.com/Auromix/odradek',8);text(388,11,f'{n} / 4',9)
def lines(x,y,items,size=10,leading=6):
 for a in items:text(x,y,a,size);y-=leading

page(1,'Carrier, four independent axes and removable optics')
c.drawImage(str(OUT/'carrier-open.png'),12*mm,72*mm,width=245*mm,height=132*mm,preserveAspectRatio=True,anchor='c',mask='auto')
lines(270,247,['Coordinates / assembly', 'Face origin: [0, 0, 0]; +Z forward.', 'J7 output contact: Z = -140.', 'Existing 10 mm adapter front: Z = -130.', 'Carrier rear-most metal: Z = -154.', 'Upper / lower finger roots: Z = 0 / +50.', 'Root radial distance: R70.', 'Upper q: 0..109 deg; lower: 0..122 deg.', '', 'Wrist blocked: q7=-90 hits J6.', 'Holding/payload are NOT qualified.', 'P16/camera shapes shown are envelopes.', 'Vendor CAD is not redistributed.', '', 'Assembly sequence', '1. Attach J7 adapter; thread depth pending.', '2. Attach carrier with four M4 candidates.', '3. Install bearing pairs and root spindles.', '4. Fit P16 pin/spacer stacks and base bolts.', '5. Fit removable optical module last.'],10,6)
lines(16,58,['Authoritative nominal geometry: main-carrier.step, integral-steel-root-spindle.step, bearing-outer-cap.step,', 'base-bracket.step and removable-optical-frame.step. Exact source hashes and QA are in study.json / review.json.', 'Alloy, fits, fillets, fatigue, bearing adjustment, fastener preload and cable strain relief remain engineering gates.', 'Full distal LED stack and mechanically retained soft pads are not integrated in this root/carrier branch.'],11,7)
c.showPage()

page(2,'Main carrier / J7 and structural section dimensions')
# Actual topological coordinates shown at 1:1 in top projection.
x0,y0=108,164
for r in [42,26]:circ(x0,y0,r)
for x,y in [(30,0),(0,30),(-30,0),(0,-30)]:circ(x0+x,y0+y,2.25)
for x,y in [(-35,-22),(-35,22),(35,-22),(35,22)]:circ(x0+x,y0+y,6);circ(x0+x,y0+y,1.7)
line(x0-52,y0,x0+52,y0);line(x0,y0-52,x0,y0+52)
text(42,228,'Carrier rear ring / XY / nominal 1:1',12,NAVY)
lines(24,97,['Ring: OD84 / ID52 / thickness8; Z -130..-122.', 'Four D4.5 clearance holes: (30,0),(0,30),(-30,0),(0,-30).', 'Four optical-column bosses: (+/-35,+/-22), OD12 / holeD3.4.', 'Radial webs: width16 x thickness8. Full silhouette: STEP.', 'Module stems: 20 x 20 closed section, blind D14 bore.', 'Minimum nominal straight wall3; end ligament4 below housing.'],10,6)
# Local u / z stem and arm schematic, nonuniform scaling labeled
ox,oy,sc=258,202,.6
rect(ox+14*sc,oy-154*sc,20*sc,136*sc,True)
rect(ox-33*sc,oy-154*sc,67*sc,8*sc,True)
line(ox+17*sc,oy-154*sc,ox+17*sc,oy-28*sc);line(ox+31*sc,oy-154*sc,ox+31*sc,oy-28*sc)
rect(ox+12*sc,oy-24*sc,22*sc,48*sc,False)
dim(ox+45*sc,oy-154*sc,ox+45*sc,oy,'154 to root axis')
text(222,236,'Upper module / u-Z schematic / 0.6:1',12,NAVY)
lines(223,86,['Upper bore length126; lower152 (root Z offset+50).', 'Base arm Z(local) -154..-146; bracket -146..-139.', 'Base M4 holes: local (r,u) = (+/-10,-18).', 'Counterbores D7.5 x 4.2; through D4.4.', 'Nominal M4x10: 7.2 engagement; not torque release.', 'A single machined solid is geometrically connected.', 'Deep boring, tool access and distortion need DFM.'],10,6)
text(24,40,'J7 adapter uses the measured 8-hole PCD44 pattern, NOT uniform 45 degree spacing.',11,NAVY)
text(24,33,'Angles: 52.64583, 82.64583, 142.64583, 172.64583, 232.64583, 262.64583, 322.64583, 352.64583 deg.',9)
text(24,26,'J7 screw length remains TBD: manufacturer recess9 / effective thread5 does not identify full thread runout.',10)
c.showPage()

page(3,'Integral root spindle and double bearing cartridge')
# Axis section; vertical coordinate is radial, horizontal is u. 4:1.
ox,oy,sc=72,159,3.6
for u0,u1,r in [(-5,5,12),(5,42,6),(12,14,8.65)]:rect(ox+u0*sc,oy-r*sc,(u1-u0)*sc,2*r*sc,True)
for u0,u1 in [(14,24),(24,34)]:
 rect(ox+u0*sc,oy+6*sc,(u1-u0)*sc,10*sc);rect(ox+u0*sc,oy-16*sc,(u1-u0)*sc,10*sc)
for u in [5,12,14,24,34,36,37,41,42]:line(ox+u*sc,oy-21*sc,ox+u*sc,oy-18*sc);text(ox+u*sc-1,oy-24*sc,str(u),8)
line(ox-30,oy,ox+160,oy);text(ox+164,oy,'+u',10)
text(26,239,'Bearing section / selected dimensions enlarged 3.6:1',12,NAVY)
lines(262,232,['Two SKF 7201 BECBP: 12 x 32 x 10.', 'Bearing B: u14..24; A: u24..34.', 'Rear inner shoulder: OD17.3,u12..14.', 'Rear outer shoulder: boreD28,u12..14.', 'Carrier body OD48,u12..34.', 'Cap OD48,u34..38.', 'Cap boreD27.5 at u34..36;', 'front reliefD30 at u36..38.', '4 x M3 on PCD40, angles45+90k.', 'Cap throughD3.4, body threadM3.', 'M3x10 / washer0.5; 5.5 engagement.', '', 'Lock end: spacer u34..36, MB1 u36..37,', 'KM1 M12x1 u37..41; end at u42.', 'MB1 slot nominal3.2 wide x1.6 deep,', 'u35.8..42.1; no internal axial M4.', 'Thread/MB1 bent tabs are simplified.', 'Fit, thread runout and washer to verify.'],10,6)
lines(22,50,['One steel part carries crank -> narrow blade fork and integral solid bearing spindle; no keyed D10 tenon.', 'P16 tip pin center at q0: (r,u,z) = (9.739771,-18,-24.106780); crank radius26; phase68 degrees.', 'P16 pin gaps: tip14.2 / base22; cheeks4; real NBK D4 shoulders with M3 threads outside both cheeks.', 'Do not infer preload: BECBP has catalog CB positive clearance. Outer-ring adjustment and actual pressure centers are unresolved.', 'Own support-shell clearance: upper0.226 / lower0.380. No tolerance allowance; near-root transition needs relief.'],10,7)
c.showPage()

page(4,'Front camera interface and removable optical module')
ox,oy,sc=100,177,3
rect(ox-16*sc,oy-15*sc,32*sc,30*sc,False);circ(ox,oy,10.25*sc)
for x,y in [(-10.5,-10.5),(-10.5,10.5),(10.5,-10.5),(10.5,10.5)]:circ(ox+x*sc,oy+y*sc,1.2*sc);circ(ox+x*sc,oy+y*sc,2.2*sc)
dim(ox-10.5*sc,oy+54,ox+10.5*sc,oy+54,'21');dim(ox-55,oy-10.5*sc,ox-55,oy+10.5*sc,'21')
text(30,242,'Original camera plate / 3:1 / integrated in front frame',12,NAVY)
lines(224,239,['Camera native mounting plane z0.', '32 x 30 plate, thickness4.', 'Lens clearanceD20.5.', '4 x throughD2.4 / counterboreD4.4 x2.', 'M2x6 head below front plane;', 'nominal body engagement4 of available6.', 'Countersink is NOT used.', '', 'Camera poses: (0,+/-50,-14) mount centers.', 'Pitch outward8 deg about head X.', 'Native front lens extends to z+13.911658.', 'Physical back extends to z-33.550037.', 'Total physical CAD depth47.461695.', 'Summary34.2 excludes rear hardware.', '', 'D64 x12 central display reservation:', 'head Z -11..+1, includes GH allowance.', 'No routed round PCBA is claimed.', 'Keepout is excluded from hardware mass.'],10,6)
lines(23,90,['Removable optical frame Z around -15..-11, with camera plates tilted8 degrees; exact relief silhouette is STEP.', 'Four columns OD10 / ID3.4 / L107, centers(+/-35,+/-22), Z-122..-15. Four cut M3 tie rods, L128.', 'Tie rods are nominal thread envelopes with two nuts/washers each; final locking and compression stiffness TBD.', 'Actual camera STEP contains Image plane and Simple FOV reference solids; these are not mechanical material.', 'Female FAKRA reserved at full unattached26.2 mm length behind male; no precise mated datum is asserted.', 'Lens FOV occlusion, cable bend radius, strain relief and connector withdrawal need follow-on optical/harness validation.'],10,7)
c.save()
print(OUT/'P16-CARRIER-01-interface-drawings.pdf')
