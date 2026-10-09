# SPDX-License-Identifier: CC-BY-NC-4.0
"""Verify saved schematic evidence and every schematic pin against PCB nets."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
review = json.loads((HERE / 'schematic-review.json').read_text())
native = json.loads((HERE / 'native-readback.json').read_text())
assert native['verification']['schematic_reopened_DRC0']
assert review['native_schematic_errors'] == review['warning_count'] == 0
for name, expected in review['source_sha256'].items():
    assert sha(R / name) == expected, 'Stale schematic evidence: ' + name
assert sha(HERE / 'schematic-netlist.enet') == review['netlist_sha256']
netlist = json.loads((HERE / 'schematic-netlist.enet').read_text())
before = json.loads((HERE / 'schematic-netlist-before-cleanup.enet').read_text())
assert netlist == before, 'Electrical netlist changed during label cleanup'
pcb = {c['designator']: c for c in native['value']['components']}
checked = 0
seen = set()
for component in netlist['components'].values():
    ref = component['props']['Designator']
    seen.add(ref)
    # RJ45 locator holes and H1-H6 NPTH holes have no electrical pin number.
    assert all(not p['net'] for p in pcb[ref]['pads'] if not p['padNumber'])
    actual = {p['padNumber']: p['net'] for p in pcb[ref]['pads'] if p['padNumber']}
    wanted = {n: p['net'] for n, p in component['pinInfoMap'].items()}
    assert actual == wanted, 'Schematic/PCB pin or net mismatch: ' + ref
    checked += len(wanted)
assert seen == set(pcb) and len(seen) == 32
report = {
    'pass': True, 'arm_required': False, 'production_released': False,
    'native_schematic_errors': 0, 'native_schematic_warnings': 0,
    'component_count': len(seen), 'pins_checked': checked,
    'every_schematic_pin_matches_PCB': True,
    'complete_netlist_identical_before_after_cleanup': True,
    'before_netlist_sha256': sha(HERE / 'schematic-netlist-before-cleanup.enet'),
    'netlist_sha256': review['netlist_sha256'],
    'source_sha256': review['source_sha256'],
    'limits': ['Digital DRC and saved netlist equivalence only; no electrical or physical qualification']
}
(R / 'reports/b06-schematic-audit.json').write_text(json.dumps(report, indent=2) + '\n')
print('SCHEMATIC DRC0 /', len(seen), 'components /', checked, 'pins match PCB')
