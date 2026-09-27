#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Nominal change drawing and load-demand sheet; original CAD only."""
import math,json
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
import p16_carrier02_study as c2
OUT=c2.OUT
f=json.loads((c2.ROOT/'engineering/generated/contact02-study/study.json').read_text())['fingers'][0];parts,_=c2.root_parts(f)
fig,axs=plt.subplots(1,2,figsize=(12,7),layout='constrained')
shapes=[(k,s.intersect(c2.B(-15,40,-32,44,-33,15))) for k,s in parts.items() if 'LED' not in k and 'pad' not in k]
for ax,axes in zip(axs,[[0,1],[0,2]]):
 for k,s in shapes:
  if s.Volume()<1e-8:continue
  v,t=s.tessellate(.08,.05);v=np.array([x.toTuple() for x in v]);t=np.array(t);colour='#559298' if 'blade' in k else '#c8d2d7' if 'steel_crank' in k else '#e0e5e7'
  ax.add_collection(PolyCollection(v[t][:,:,axes],facecolors=colour,edgecolors='none',alpha=1))
 ax.set(xlim=(-15,40),aspect='equal',xlabel='Local x / mm');ax.grid(alpha=.2)
axs[0].set(ylim=(-32,44),ylabel='Local u / mm',title='Root top projection / distal cut at x40 for illustration')
axs[1].set(ylim=(-33,15),ylabel='Local z / mm',title='Root side projection / q = 0')
for ax in axs:ax.axvline(25,c='#ab493f',ls='--',lw=1)
axs[0].text(26,38,'x>25 unchanged',fontsize=9,color='#ab493f');axs[0].annotate('R1 tongue relief\nfull neck 18 x 6',xy=(24.6,9.3),xytext=(3,31),arrowprops={'arrowstyle':'->'},fontsize=9)
axs[0].annotate('7 mm bridge width\ncontinues to u+5',xy=(13.5,-15),xytext=(-13,-28),arrowprops={'arrowstyle':'->'},fontsize=9)
axs[1].annotate('Tip pin D4\n(r26, phase68)',xy=(9.7398,-24.1068),xytext=(20,-30),arrowprops={'arrowstyle':'->'},fontsize=9)
axs[1].annotate('Bridge height8\n7.4 inside hub',xy=(13.5,-5),xytext=(22,-16),arrowprops={'arrowstyle':'->'},fontsize=9)
fig.suptitle('P16-CARRIER-02 / near-root change only',fontsize=16);fig.savefig(OUT/'root-revision.png',dpi=170);plt.close(fig)
W,H=landscape(A3);c=canvas.Canvas(str(OUT/'P16-CARRIER-02-root-study.pdf'),pagesize=(W,H));navy=colors.HexColor('#173448');teal=colors.HexColor('#167c83');gray=colors.HexColor('#4b5b65')
def text(x,y,s,size=10,col=gray):c.setFont('Helvetica',size);c.setFillColor(col);c.drawString(x*mm,y*mm,s)
def line(x1,y1,x2,y2,col=gray):c.setStrokeColor(col);c.setLineWidth(.7);c.line(x1*mm,y1*mm,x2*mm,y2*mm)
def lines(x,y,ss,size=10,dy=6):
 for s in ss:text(x,y,s,size);y-=dy
def page(n,title):
 text(14,282,'ODRADEK / P16-CARRIER-02',12,teal);text(14,269,title,21,navy);line(14,261,406,261)
 text(14,11,'NOMINAL MECHANISM STUDY - NOT FOR MANUFACTURE / dimensions mm / CC BY-NC 4.0',9)
 text(14,6,'Odradek - Auromix contributors | https://github.com/Auromix/odradek',8);text(393,11,f'{n}/2',9)
page(1,'1 mm nominal root clearance without thinning the tongue')
c.drawImage(str(OUT/'root-revision.png'),12*mm,74*mm,width=258*mm,height=174*mm,preserveAspectRatio=True,anchor='c',mask='auto')
lines(280,247,['Authoritative original STEP / local frame', 'UR / LL metal_blade_with_narrow_tongue', 'UR / LL integral_steel_crank_spindle', '', 'x: petal length; u: hinge axis; z: face.', 'Tongue x15..24: u +/-9; thickness6.', 'R1 arcs from (24,+/-9) to (25,+/-10).', 'Two D3.4 holes: x21, u +/-4.5.', 'Distal x>25: exact original geometry.', '', 'Steel bridge: x10..17.', 'u -29.1..-5: z -8..0 (7 x 8).', 'u -5..+5: z -7.4..0 (7 x 7.4).', 'Minimum inscribed path: 51.8 mm2.', 'Hub overlap10; avoids M2 keeper heads.', 'All old shaft/pin datums retained.', '', 'Unchanged nominal bearing interface', 'Solid shaft D12; centers u19 and29.', 'P16 actuation plane u-18.', 'Root R70; upper z0 / lower z+50.', 'Upper q0..109 / lower q0..122 deg.'],10,6)
lines(16,60,['The OD48 coaxial conservative support shell has exactly 1.000 mm nominal gap for all four roots.', 'This is also the geometric ceiling at the immutable distal x25 face; tolerances and elastic motion remain unqualified.', 'Clearance is an analytic rotational-invariance result, not an end-state screenshot result.', 'Steel material was added; the 18 x 6 tongue was not thinned. Four independent hinge axes and mirrored modules remain.', 'J7 contact stays head z-140; face z0. Parent 24 mm wrist extension is not integrated. Original wrist +/-90 remains blocked.'],10,7)
c.showPage();page(2,'Loads use the real offset and the net section after holes')
load=json.loads((OUT/'loads.json').read_text());qa=json.loads((OUT/'qa-mass.json').read_text());bridge=load['bridge_300N_continuous_force_direction_bound'][0]
# Geometric-center free-body in u, not a claim about actual pressure centers.
ox,oy,sc=65,216,2.7;line(ox-22*sc,oy,ox+34*sc,oy)
for u,label in [(-18,'F'),(19,'A'),(29,'B')]:
 x=ox+u*sc;line(x,oy-8,x,oy+8,teal);text(x-3,oy+12,label,12,navy);text(x-5,oy-15,str(u),10)
text(20,247,'Geometric reaction screen / local u (not pressure centers)',12,navy)
lines(21,184,['300 N at u-18, bearings at u19 / u29:', '|RA| = 4.7 F = 1410 N; |RB| = 3.7 F = 1110 N.', 'Offset alone: 300 x 18 = 5400 Nmm.', 'Additional opposed pair due to offset: 540 N.', 'Actuator-only hinge moment needs a stop or inertia;', 'ideal radial bearings do not supply hinge torque.'],11,7)
lines(228,247,['Net-section areas from exact CAD slices', 'Bridge retained sub-prism: 7 x 7.4 = 51.8 mm2.', 'Main shaft at u11.9: D12 = 113.097 mm2.', 'Aluminum tongue at M3 row: 67.200 mm2.', 'Steel fork at nut pockets: 54.826 mm2.', 'Upper clamp cap at M3 row: 44.800 mm2.', '', '300 N bridge directional conservative screen:', f'Bending upper {bridge["bending_stress_any_radial_direction_upper_MPa"]:.1f} MPa; torsion shear {bridge["torsional_shear_upper_MPa"]:.1f} MPa.', f'Combined nominal upper {bridge["nominal_von_mises_combined_upper_MPa"]:.1f} MPa.', f'Factor2 requires yield >= {bridge["required_yield_factor2_MPa"]:.1f} MPa BEFORE concentrations.', 'Actual corner/fillet stress and fatigue remain open.', 'A material name alone does not close this gate.'],10,6.8)
lines(228,147,['Steel candidate: original D80 x L80 bar, +QT.', 'Ovako6082/MoC410M, 40<D<100: Rel >=650 MPa.', 'Certificate/heat state required; notch/fatigue still open.'],10,6)
y=124
for i in [0,4]:
 a=load['grip_witness_cases'][i];b=load['grip_witness_cases'][i+1];name='Upper' if i==0 else 'Lower'
 text(21,y,f'{name} / diameter80, mu0.4, 2kg x factor2, one free-sharing LP witness',12,navy)
 text(21,y-8,f'eta0.85 + present bare-finger gravity: F {a["axial_actuator_force_N"]:.1f} N; radial reactions {a["reactions"]["radial_magnitudes_N"][0]:.1f} / {a["reactions"]["radial_magnitudes_N"][1]:.1f} N.',10)
 text(21,y-15,f'300 N plus same contacts: {b["reactions"]["radial_magnitudes_N"][0]:.1f} / {b["reactions"]["radial_magnitudes_N"][1]:.1f} N; unbalanced hinge torque is explicitly retained.',10)
 y-=28
lines(21,62,[f'Modeled mass {qa["mass"]["modeled_mass_g"]/1000:.3f} kg; full head planning {qa["mass"]["whole_head_planning_g"][0]/1000:.3f}..{qa["mass"]["whole_head_planning_g"][1]/1000:.3f} kg, excluding J7 and parent extension.', 'Bare finger gravity omits later real lamps and pad retainers; LP witness is not a load-sharing hardware result.', 'M3 preload, clamp separation, hole/fillet fatigue, true bearing pressure centers, P16 duty/holding and cable motion remain open.', 'Reproduce: p16_carrier02_study.py --motion; p16_carrier02_loads.py; p16_carrier02_export.py; draw_p16_carrier02.py.', 'Sources and exact arrays: geometry.json, motion.json, loads.json, qa-mass.json; see docs/engineering/p16-carrier02-study.md.'],10,7)
c.save();print(OUT/'P16-CARRIER-02-root-study.pdf')
