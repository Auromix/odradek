#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Dimensioned nominal shoulder-pin stack illustration; not a production drawing."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from p16_packaging_study import P, OUT

def main():
    fig,axes=plt.subplots(2,1,figsize=(11,7),layout='constrained')
    for ax,(label,gap,lug,L) in zip(axes,[('Tip / SBSM-M3-4-25',P['tip_gap_mm'],6.,25.),('Base / SBSM-M3-4-30',P['base_gap_mm'],8.,30.)]):
        h=gap/2;start=-h-4;end=start+L
        def box(x,w,y,H,color,txt=None):
            ax.add_patch(Rectangle((x,y),w,H,fc=color,ec='#34424a',lw=.8))
            if txt:ax.text(x+w/2,y+H/2,txt,ha='center',va='center',fontsize=8)
        # Section: shoulder crosses both ears. Recesses omitted for clarity.
        for x in [start,h]:box(x,4,-7,14,'#a0b7c4','4')
        box(-lug/2,lug,-4.5,9,'#e8b86b','P16\neye')
        sl=(gap-lug-.2)/2-.02
        box(-lug/2-.02-sl,sl,-3,6,'#cfdae0');box(lug/2+.02,sl,-3,6,'#cfdae0')
        if end>h+4:box(h+4,end-h-4,-3.5,7,'#cfdae0')
        box(end,.5,-3.5,7,'#9ea7ad');box(end+.5,2.4,-3.175,6.35,'#6e808a')
        box(start,L,-2,4,'#536570');box(start-3,3,-3.5,7,'#536570');box(end,7,-1.5,3,'#536570')
        ax.annotate('',xy=(start,-10),xytext=(end,-10),arrowprops=dict(arrowstyle='<->',lw=1))
        ax.text((start+end)/2,-10.5,f'{L:g} mm shoulder (+0.25 / 0)',ha='center',va='top',fontsize=9)
        ax.annotate('',xy=(-h,9),xytext=(h,9),arrowprops=dict(arrowstyle='<->',lw=1))
        ax.text(0,9.5,f'{gap:g} mm clear gap',ha='center',va='bottom',fontsize=9)
        ax.text(end+3,5,'M3 nut + washer\noutside both supports',fontsize=9,ha='center',va='bottom')
        ax.set(title=label,xlim=(-24,28),ylim=(-14,17),aspect='equal',xlabel='Local tangent distance from actuator plane / mm');ax.set_yticks([]);ax.grid(axis='x',alpha=.18)
    fig.suptitle('P16-PACK-01 / true two-cheek shoulder support\nBoth metal bores Ø4.1; shoulder Ø4 f9; plastic bore Ø4.25. Nominal geometry only.',fontsize=13)
    OUT.mkdir(parents=True,exist_ok=True);fig.savefig(OUT/'pin-stack.png',dpi=180);plt.close(fig)
if __name__=='__main__':main()
