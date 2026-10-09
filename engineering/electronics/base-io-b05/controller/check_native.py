# SPDX-License-Identifier: CC-BY-NC-4.0
"""Audit current saved native candidate. Nonzero DRC ALWAYS blocks this check."""
import json, hashlib
from pathlib import Path
from shapely.geometry import LineString
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
R = HERE.parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
native = json.loads((HERE/'native-readback.json').read_text())
assert native['ok'] and native['verification']['native_reopened']
for name, expected in native['source_sha256'].items():
    assert sha(R/name) == expected, 'Stale native readback: ' + name
current = native['value']
legacy = json.loads((R/'reports/b06-data-reopened.json').read_text())['value']
for key in ('pads', 'lines', 'vias'):
    by_id = {p['primitiveId']: p for p in current[key]}
    for p in legacy[key]:
        assert by_id[p['primitiveId']] == p, 'Legacy copper changed: ' + p['primitiveId']
spec = json.loads((HERE/'specification.json').read_text())
components = {c['designator']: c for c in current['components']}
assert len(components) == 32 and sum(c['addIntoBom'] for c in components.values()) == 26
for ref, nets in spec['nets'].items():
    actual = {p['padNumber']: p['net'] for p in components[ref]['pads']}
    for number, net in nets.items():
        assert actual[number] == net, ref + '.' + number
    assert all(not net for number, net in actual.items() if number not in nets), 'Unused pin connected: ' + ref
assert {p['padNumber']: p['net'] for p in components['J7']['pads']} == {
    '1':'LAMP5V', '2':'LAMP_PWM', '3':'RETURN48', '4':'RETURN48', '5':'RETURN48'}
baseline = json.loads((HERE/'route-input.json').read_text())['value']
plan = json.loads((HERE/'routes.json').read_text())
def segments(lines):
    return [(p['net'], p['layer'], LineString([(p['startX']*.0254, -p['startY']*.0254),
                                              (p['endX']*.0254, -p['endY']*.0254)])) for p in lines]
planned = segments([p for p in baseline['lines'] if p['primitiveId'] not in plan['removed_lines']])
planned += [(p['net'], p['layer'], LineString([a,b])) for p in plan['routes'] for a,b in zip(p['points'],p['points'][1:])]
actual = segments(current['lines'])
keys = {(n,l) for n,l,_ in planned}
assert keys == {(n,l) for n,l,_ in actual}
for net, layer in keys:
    wanted = unary_union([s for n,l,s in planned if (n,l)==(net,layer)])
    have = unary_union([s for n,l,s in actual if (n,l)==(net,layer)])
    assert wanted.difference(have.buffer(.002)).is_empty, 'Missing native route: ' + net
    assert have.difference(wanted.buffer(.002)).is_empty, 'Unplanned native route: ' + net
assert len(current['vias']) == len(baseline['vias']) + len(plan['vias']) == 39
def leaves(node):
    if isinstance(node,list):
        return sum((leaves(x) for x in node), [])
    if isinstance(node,dict):
        if 'errorType' in node and 'objs' in node:
            return [node]
        return leaves(node.get('list', []))
    return []
errors = leaves(current['drc'])
report = {'pass':not current['drc'], 'manufacturing_released':False,
          'candidate_data_consistent':True, 'arm_required':False,
          'legacy_copper_unchanged':True, 'native_route_union_matches_plan':True,
          'component_quantity':26, 'pads':len(current['pads']), 'lines':len(current['lines']),
          'vias':len(current['vias']), 'drc_error_count':len(errors),
          'drc_categories':[[c['name'],c['count']] for c in current['drc']],
          'source_sha256':native['source_sha256'], 'readback_sha256':sha(HERE/'native-readback.json'),
          'limits':['Native saved-data audit only; check_routed.py separately verifies current manufacturing exports',
                    'No physical rail, thermal, EMC, signal, assembly or load qualification']}
(R/'reports/b06-controller-native-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print('CONTROLLER_CANDIDATE_DATA_CONSISTENT / DRC', len(errors), '/ PRODUCTION False')
if current['drc']:
    raise SystemExit('Current native PCB DRC unresolved; fabrication release blocked')
