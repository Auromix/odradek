# SPDX-License-Identifier: CC-BY-NC-4.0
"""Pin, verify and import RobStride candidate STEP without redistributing assets."""
from pathlib import Path
import hashlib, json, urllib.request
import cadquery as cq

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).parent
CACHE=ROOT/'work/arm-a15/robstride'
CATALOG_SHA='76c85c3c11f15bf3adc1676d6a4b8c931ffd9c18cec41221f8ea5a8b54e22ea1'

def run():
    sources=json.loads((HERE/'sources.json').read_text())
    CACHE.mkdir(parents=True,exist_ok=True)
    for s in sources['sources']:
        p=CACHE/s['local_filename']
        if not p.exists():p.write_bytes(urllib.request.urlopen(s['url'],timeout=60).read())
        assert hashlib.sha256(p.read_bytes()).hexdigest()==s['sha256'],p
    report=[];meshes=[]
    for model,filename in [('RS10P','RS10.stp'),('RS02','rs02.stp')]:
        p=CACHE/filename;w=cq.importers.importStep(str(p))
        solid=cq.Compound.makeCompound([s for v in w.vals() for s in v.Solids()])
        assert solid.isValid() and solid.Volume()>0
        b=solid.BoundingBox();vv,tt=solid.tessellate(.15,.20)
        # Preserve supplier coordinates. No bounding-box mating or invented
        # output datum is used in this inspection scene.
        meshes.append(dict(model=model,vertices_mm=[list(v.toTuple()) for v in vv],
                           triangles=[list(t) for t in tt],source_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
        report.append(dict(model=model,file=filename,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                           solid_count=len(solid.Solids()),valid=solid.isValid(),volume_mm3=solid.Volume(),
                           bbox_supplier_mm=[b.xmin,b.ymin,b.zmin,b.xmax,b.ymax,b.zmax],
                           extent_mm=[b.xlen,b.ylen,b.zlen],linear_scale=1.0,
                           assembly_interface_datum_released=False,
                           note='RS10.stp is from official10P directory; RS10P manual and20260917 drawing match D57 body. Still confirm delivered hardware revision.'))
    (CACHE/'inspection-meshes.json').write_text(json.dumps(meshes,separators=(',',':'))+'\n')
    out=HERE/'build';out.mkdir(exist_ok=True)
    (out/'vendor-audit.json').write_text(json.dumps(dict(sources=sources,models=report,
        catalog_sha256=CATALOG_SHA,rights='Supplier STEP and derived geometry remain in ignored local work cache; own scripts and fingerprints only are published.',
        assembly_ready=False,production_release=False),indent=2)+'\n')
    print('VERIFIED_VENDOR_MODELS',[(r['model'],r['extent_mm']) for r in report])

if __name__=='__main__':run()
