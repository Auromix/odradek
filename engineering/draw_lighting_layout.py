# SPDX-License-Identifier: CC-BY-NC-4.0
# Attribution: Odradek - Auromix contributors
"""Front-projection LED placement study; not PCB artwork or manufacturing release."""
from pathlib import Path
import csv
import hashlib
import json
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle
import numpy as np
import ezdxf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'engineering/generated/lighting-layout'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pfile = ROOT/'engineering/parameters/r4-layout.json'
    source = ROOT/'docs/engineering/sources/head-lighting-io.json'
    p = json.loads(pfile.read_text()); data = json.loads(source.read_text())
    assert hashlib.sha256(pfile.read_bytes()).hexdigest() == data['parameters']['sha256']
    panels = {s['panel']: s for s in data['pixel_maps']}
    fig, ax = plt.subplots(figsize=(13, 10))
    fig.patch.set_facecolor('#faf9f5'); ax.set_facecolor('#faf9f5')
    doc = ezdxf.new('R2010'); doc.units = ezdxf.units.MM; model = doc.modelspace()
    for name,color in [('STRUCTURE',8),('WINDOW',3),('LED_LAND_ENVELOPE',2),('CONTACT_RESERVE',4),('PAD',5),('CAMERA_PROXY',6),('ANNOTATION',7)]:
        doc.layers.new(name, dxfattribs={'color':color})
    records = []

    def poly(points, layer, face, edge, alpha=1):
        points=np.asarray(points)
        ax.add_patch(Polygon(points, closed=True, facecolor=face, edgecolor=edge, lw=.8, alpha=alpha))
        model.add_lwpolyline(points.tolist(),close=True,dxfattribs={'layer':layer})

    def circle(x,y,r,layer,face,edge):
        ax.add_patch(Circle((x,y),r,facecolor=face,edgecolor=edge,lw=1))
        model.add_circle((x,y),r,dxfattribs={'layer':layer})

    circle(0,0,45,'STRUCTURE','#333b40','#111a20')
    circle(0,0,31,'WINDOW','#101b23','#45555e')
    for cy in [-50,50]:
        circle(0,cy,13,'CAMERA_PROXY','#344c56','#223139')
        circle(0,cy,8,'CAMERA_PROXY','#122630','#7d9198')

    fingers={f['id']:f for f in p['head']['fingers']}
    for name, f in fingers.items():
        L,W=f['length_mm'],f['width_mm']; phi=math.radians(f['phi_deg'])
        R=np.array([[math.cos(phi),-math.sin(phi)],[math.sin(phi),math.cos(phi)]])
        root=f['root_radius_mm']*R[:,0]
        def transform(points):return np.asarray(points)@R.T+root
        body=[(0,-W*.27),(L*.18,-W*.5),(L*.72,-W*.25),(L,-W*.05),(L,W*.05),(L*.72,W*.25),(L*.18,W*.5),(0,W*.27)]
        window=[(L*.13,-W*.24),(L*.24,-W*.36),(L*.72,-W*.20),(L*.94,-W*.08),(L*.94,W*.08),(L*.72,W*.20),(L*.24,W*.36),(L*.13,W*.24)]
        poly(transform(body),'STRUCTURE','#3a4349','#19272d')
        poly(transform(window),'WINDOW','#6f5b33','#b3a275')
        s=f['contact_along_mm']
        # Reserve band is an ECAD restriction, not an added mechanical solid.
        reserve=transform([(s-12,-W*.17),(s+12,-W*.17),(s+12,W*.17),(s-12,W*.17)])
        poly(reserve,'CONTACT_RESERVE','#87a8aa','#557d81',.65)
        for sign in [-1,1]:
            y=sign*W*.08
            poly(transform([(s-9,y-2.5),(s+9,y-2.5),(s+9,y+2.5),(s-9,y+2.5)]),'PAD','#c2c8ca','#30434d')
        for driver in panels[name]['drivers']:
            for pixel in driver['pixels']:
                x,y=pixel['x_mm'],pixel['y_mm'];center=transform([[x,y]])[0]
                land=transform([(x-1.2,y-.4),(x+1.2,y-.4),(x+1.2,y+.4),(x-1.2,y+.4)])
                poly(land,'LED_LAND_ENVELOPE','#ffd581','#ffe4a4')
                records.append([name,driver['ic'],pixel['sw'],pixel['cs'],x,y,*center,f['root_z_mm'],f['phi_deg']])
        tip=transform([[L*.6,0]])[0]
        ax.annotate(f'{name}  {panels[name]["pixel_count"]} LEDs',xy=tip,xytext=(145 if tip[0]>0 else -145,130 if tip[1]>0 else -138),
                    ha='center',fontsize=11,color='#203943',arrowprops={'arrowstyle':'-','color':'#5b6b70','lw':.7})
    for driver in panels['circle']['drivers']:
        for pixel in driver['pixels']:
            x,y=pixel['x_mm'],pixel['y_mm']
            poly([(x-1.2,y-.4),(x+1.2,y-.4),(x+1.2,y+.4),(x-1.2,y+.4)],'LED_LAND_ENVELOPE','#ffd581','#ffe4a4')
            records.append(['circle',driver['ic'],pixel['sw'],pixel['cs'],x,y,x,y,0,0])
    assert len(records)==609
    assert len({tuple(r[:4]) for r in records})==609
    ax.annotate('285 LEDs / 2 ICs\nCircular pixel display',xy=(0,0),xytext=(0,-99),ha='center',fontsize=10,color='#203943',
                arrowprops={'arrowstyle':'-','color':'#5b6b70','lw':.7})
    ax.set(xlim=(-195,195),ylim=(-164,152),xlabel='Head local x (mm)',ylabel='Head local y (mm)')
    ax.set_aspect('equal');ax.grid(alpha=.12);ax.spines[['top','right']].set_visible(False)
    fig.suptitle('609 LED positions within the selected four-petal silhouette',fontsize=19,y=.975,color='#203943')
    ax.set_title('Front projection at q = 0 | Upper roots z = 0 mm; lower roots z = +50 mm',fontsize=11,pad=12)
    fig.text(.5,.025,'Amber: LED land envelopes   Grey: contact pads   Teal: part of the LED exclusion band\n2D placement study only: no copper routing, component stack, diffusion or load qualification',ha='center',fontsize=10,color='#455d66')
    fig.subplots_adjust(top=.88,bottom=.12,left=.10,right=.96)
    fig.savefig(OUT/'led-front-projection.png',dpi=150);fig.savefig(OUT/'led-front-projection.svg');plt.close(fig)
    model.add_text('HLIO-01 / mm / FRONT PROJECTION ONLY / NOT PCB OR MANUFACTURING RELEASE',dxfattribs={'height':3,'layer':'ANNOTATION'}).set_placement((-175,-145))
    doc.saveas(OUT/'led-front-projection.dxf');assert not ezdxf.readfile(OUT/'led-front-projection.dxf').audit().errors
    with (OUT/'led-coordinate-reference.csv').open('w',newline='') as fh:
        writer=csv.writer(fh);writer.writerow(['panel','driver','SW','CS','panel_x_mm','panel_y_mm','head_x_mm','head_y_mm','root_z_mm','panel_rotation_deg']);writer.writerows(records)
    (OUT/'evidence.json').write_text(json.dumps({'revision':'HLIO-01-projection','pixel_count':609,'unique_electrical_addresses':609,'parameter_sha256':hashlib.sha256(pfile.read_bytes()).hexdigest(),'pixel_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'units':'mm','drawing_scope':'open-state front projection; root_z is not LED surface height; no copper/solder/PCB release','dxf_audit_passed':True},indent=2)+'\n')
    print('609 unique LED addresses plotted; millimetre DXF audit passed.')


if __name__=='__main__':main()
