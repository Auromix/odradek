#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
from pathlib import Path
import json,math
D=Path(__file__).resolve().parents[1];rho=1.724e-8;w=.004;t=.000035
res=[]
for n,dx in [('VIN48',101-100.31),('RETURN48',92.69-85)]:
 Lmm=12.2+math.hypot(dx,7)+5;R=rho*Lmm*.001/(2*w*t);res.append(dict(net=n,conservative_main_path_length_mm=Lmm,width_each_outer_mm=4,finished_copper_assumption_um=35,parallel_outer_layers=2,ideal_roomtemp_resistance_ohm=R))
R=sum(x['ideal_roomtemp_resistance_ohm']for x in res)
out=dict(revision='BRI01',power_paths=res,rho_assumed_20C_ohm_m=rho,examples=[dict(current_A=I,ideal_copper_drop_V=I*R,ideal_copper_heat_W=I*I*R)for I in[10,20]],excluded_from_resistance=['contact and crimp resistance','throughhole barrel current distribution','solder joint resistance','temperature dependence','cable loss','fuse and source impedance'],current_rating=None,thermal_model='No temperature-rise prediction; actual finished copper/plating, assembly and closedhood test required',pulse_duration_s=None,internal_RJ45=dict(plug_total_reference_mm=22.78,max_cable_OD_mm=5.9,fixed_Rmin_4D_mm=23.6,height_conservative_before_insertion_mm=22.78+23.6+5.9,space_mm=48,necessary_insertion_minus_straight_mm=22.78+23.6+5.9-48))
(D/'calculations.json').write_text(json.dumps(out,indent=2)+'\n');print('power ideal copper pair R',R)
