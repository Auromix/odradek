# SPDX-License-Identifier: CC-BY-NC-4.0
"""Rebuild and validate the base WITHOUT any arm module. Run in CAD Python.

Digital checks only. Stops on failures, never marks physical tests complete.
Existing actual Orca slices must match new print meshes or this command fails.
"""
import argparse,subprocess,sys,json,hashlib,os
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def run(name,args):
    print('BASE CHECK:',name,flush=True)
    env=dict(os.environ,ODRADEK_CAD_PYTHON=sys.executable)
    subprocess.run([str(x) for x in args],check=True,cwd=ROOT,env=env)
def main():
    p=argparse.ArgumentParser();p.add_argument('--blender',type=Path,required=True);p.add_argument('--render',action='store_true');a=p.parse_args()
    blender=a.blender.resolve();assert blender.is_file()
    py=sys.executable
    # Fail before rebuilding the release bundle if current native PCB is invalid.
    run('current controller native DRC and source audit',[py,HERE.parent/'electronics/base-io-b05/controller/check_native.py'])
    run('current schematic DRC and pin-net audit',[py,HERE.parent/'electronics/base-io-b05/controller/check_schematic.py'])
    for name in ('load_frame','check_load_frame','standalone_fixture'):
        run(name,[py,HERE/(name+'.py')])
    run('base-only Blender rebuild',[blender,'--background','--python-exit-code','1','--python',HERE/'blender_standalone_entry.py','--','--no-render'])
    E=HERE/'build/exterior'
    run('print mesh/bed',[py,HERE.parent/'base_b05/print_checks.py',E/'print-parts','--bed',256,256,256,'--margin',5,'--output',E/'print-checks.json'])
    for name in ('check_interface_contract','check_solids','check_integrated_hardware','check_service','check_fixture_fit'):
        run(name,[py,HERE/(name+'.py')])
    run('native blend and light checks',[blender,'--background',E/'ODR-BASE-B06-COMPACT.blend','--python-exit-code','1','--python',HERE/'check_fit.py','--python',HERE/'check_light_blender.py'])
    for name in ('slice_review','bom','manufacturing_definition','package','draw_fixture','draw_load_frame'):
        run(name,[py,HERE/(name+'.py')])
    for source in (HERE.parent/'electronics/base-light-b06/audit.py',HERE.parent/'electronics/base-io-b05/check_routed.py'):
        run('native manufacturing audit '+source.parent.name,[py,source])
    for folder in (E,HERE/'build/standalone-test'):run('3D viewer '+folder.name,[py,HERE/'viewer.py','--build-dir',folder])
    run('local5V body/driver integration',[py,HERE.parent/'electronics/base-io-b05/local5v/check_fit.py'])
    run('evidence validator self-check',[py,HERE/'test_qualification.py'])
    record=HERE/'build/qualification/unmeasured-template.json'
    if not record.exists():run('unmeasured test record',[py,HERE/'qualification.py','init'])
    else:
        from qualification import unmeasured
        if unmeasured(json.loads(record.read_text())):run('refresh empty template only',[py,HERE/'qualification.py','refresh-unmeasured'])
    run('qualification state (no physical measurements)',[py,HERE/'qualification.py','evaluate'])
    if a.render:run('base renders',[blender,'--background',E/'ODR-BASE-B06-COMPACT.blend','--python-exit-code','1','--python',HERE/'render.py'])
    report={'pass':True,'scope':'Base-only digital rebuild/geometry/native manufacturing file audits; NO measured physical qualification',
            'manifest_sha256':hashlib.sha256((E/'manifest.json').read_bytes()).hexdigest(),
            'arm_required':False,'production_released':False,'command_sources_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.glob('*.py'))}}
    (HERE/'build/base-only-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('BASE_ONLY_DIGITAL_PASS / PHYSICAL_PRODUCTION_RELEASE_PENDING',flush=True)
if __name__=='__main__':main()
