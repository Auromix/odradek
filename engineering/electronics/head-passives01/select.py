#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Apply a reviewable parts overlay to frozen HEAD-CTRL02, without editing it.

Standard-library only. This generates a selection BOM, not a netlist/PCB release.
All component pins and their original circuit nets remain in the parent snapshot.
"""
from pathlib import Path
import csv
import hashlib
import itertools
import json
import math

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
PARENT = D.parent / 'head-ctrl02'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(p, obj):
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')


def csvout(p, rows):
    with p.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def current_network(rip=6490, rt=100000, rb=100000, rd=100000, ron=4.5):
    # Divider is not an infinite-impedance voltage observer: include ADC bleed.
    lower = 1 / (1/rb + 1/(rd+ron))
    effective = 1 / (1/rip + 1/(rt+lower))
    ratio = lower / (rt+lower) * rd / (rd+ron)
    return effective, ratio


def main():
    cat = json.loads((D/'catalog.json').read_text())
    parts = cat['parts']
    parent = list(csv.DictReader((PARENT/'bom.csv').open()))
    pins = list(csv.DictReader((PARENT/'pin-net.csv').open()))
    pinmap = {}
    for p in pins:
        pinmap.setdefault(p['ref'], {})[p['pin']] = p['net']
    rm = {p['value']: n for n, p in parts.items() if p['kind'] == 'R'}
    cm = {
        '100nF': 'C1608X7R1H104K080AA',
        '1uF': 'C1608X7R1E105K080AB',
        '10nF': 'C0603C103K5RACTU',
        '22nF': 'C0603C223K5RACTU',
        '470pF': 'C0603C471J5GACTU',
        '22uF': 'C1210C226K4RACTU',
        '1000uF': 'EEUFR1E102',
    }
    overlay = []
    merged = []
    for row in parent:
        ref = row['ref']
        out = dict(row)
        if row['mpn'] != 'TBD':
            merged.append(out)
            continue
        if ref.startswith('R'):
            pn = rm[row['value']]
        elif ref.startswith('C'):
            val = row['value'].split()[0]
            pn = ('C1206C106K3RACTU' if ref == 'C6'
                  else 'C1210C106K5RACTU') if val == '10uF' else cm[val]
        elif ref.startswith('JP'):
            pn = 'TSW-102-07-T-S'
        else:
            raise AssertionError(f'Unhandled original TBD: {ref}')
        p = parts[pn]
        assert set(pinmap[ref]) == {'1', '2'}, ref
        # Only ratings/tolerances/packages change. No nominal R/C value change.
        if p['kind'] in ('C', 'R'):
            assert row['value'].split()[0] == p['value'].split()[0], ref
        note = p.get('qualification', 'Component candidate; footprint, circuit and thermal qualification pending.')
        if ref.startswith('JP'):
            note += ' Normally open; three removable shunts supplied loose.'
        if ref in ('R9', 'R39'):
            original_note = row['note'].removeprefix('1% ')
        else:
            original_note = row['note']
        out.update(mpn=pn, value=p['value'] if p['kind'] != 'JP' else row['value'],
                   footprint=p['footprint_candidate'],
                   source_url=cat['sources'][p['sources'][0]]['url'],
                   selection_status='selected candidate; not released',
                   note=original_note + ' | HEAD-PASSIVES01: ' + note,
                   unit_mass_g=str(p.get('typical_mass_g') or 'TBD'))
        merged.append(out)
        overlay.append(dict(
            ref=ref, original_value=row['value'], selected_value=out['value'],
            mpn=pn, manufacturer=p['manufacturer'], quantity=1,
            original_footprint=row['footprint'], footprint_candidate=out['footprint'],
            body_max_mm=json.dumps(p.get('body_max_mm')),
            pin1_net=pinmap[ref]['1'], pin2_net=pinmap[ref]['2'],
            source_ids=';'.join(p['sources']), selection_status=out['selection_status'],
            qualification=note))
    assert len(parent) == len(merged) == 242
    assert len(overlay) == 193
    assert len({x['ref'] for x in overlay}) == 193
    assert all(x['mpn'] != 'TBD' for x in merged)
    counts = {k: sum(x['ref'].startswith(k) for x in overlay) for k in ('R', 'C', 'JP')}
    assert counts == {'R': 106, 'C': 84, 'JP': 3}, counts
    grouped = []
    for pn in sorted({x['mpn'] for x in overlay}):
        rows = [r for r in overlay if r['mpn'] == pn]
        grouped.append(dict(mpn=pn, manufacturer=parts[pn]['manufacturer'],
                            value=parts[pn]['value'], quantity=len(rows),
                            references=' '.join(r['ref'] for r in rows),
                            footprint_candidate=parts[pn]['footprint_candidate']))
    csvout(D/'selection-overlay.csv', overlay)
    csvout(D/'bom-selected.csv', merged)
    csvout(D/'parts-grouped.csv', grouped)
    csvout(D/'service-accessories.csv', [dict(mpn='SNT-100-BK-T', quantity=3,
        normally_installed_quantity=0, purpose='JP1 BOOT / JP2 reset / JP3 EEPROM write; service only',
        source_url='https://www.samtec.com/products/snt-100-bk-t')])

    # Evaluate initial tolerance and resistor-body temperature separately.
    # The chosen 0..70 C interval is a study assumption, not a qualified ambient.
    dt = 45
    lo = (1-.001)*(1-25e-6*dt)
    hi = (1+.001)*(1+25e-6*dt)
    rows = []
    for factors in itertools.product((lo, hi), repeat=4):
        for ron, vf, af in itertools.product((0., 4.5), (.99, 1.01), (.925, 1.075)):
            values = [v*f for v, f in zip((6490, 100000, 100000, 100000), factors)]
            eff, ratio = current_network(*values, ron)
            rows.append((2.5*vf/(.00045*af*eff), ratio))
    vm = []
    for ft, fb, fd, ron in itertools.product((lo, hi), (lo, hi), (lo, hi), (0., 4.5)):
        rt, rb, rd = 100000*ft, 20000*fb, 100000*fd
        parallel = 1/(1/rb + 1/(rd+ron))
        vm.append(dict(on=parallel/(rt+parallel)*rd/(rd+ron), off=rb/(rt+rb)))
    eff, ratio = current_network()
    rl_lo = (1-.01)*(1-800e-6*dt)
    rl_hi = (1+.01)*(1+800e-6*dt)
    report = dict(revision='HEAD-PASSIVES01', parent='HEAD-CTRL02', release=False,
        input_hashes={str(p.relative_to(ROOT)): sha(p) for p in [
            PARENT/'bom.csv', PARENT/'pin-net.csv', PARENT/'netlist.json',
            PARENT/'calculations.json', D/'catalog.json', Path(__file__)]},
        coverage=dict(parent_positions=242, newly_selected_positions=193, counts=counts,
                      new_unique_board_MPNs=len(grouped), new_loose_accessory_MPNs=1,
                      final_MPN_TBD_count=0, parent_files_modified=False,
                      same_nominal_R_C_values=True, assembly_or_order_release=False),
        package_changes=[dict(ref=r['ref'], before=r['original_footprint'],
                              candidate=r['footprint_candidate']) for r in overlay
                         if r['original_footprint'] != r['footprint_candidate']],
        resistor_temperature_study=dict(body_temperature_assumption_C=[0,70],
            reference_C=25, max_delta_K=dt,
            precision_R_factor_bounds=[lo,hi],
            ipropi_effective_R_nominal_ohm=eff, ipropi_ADC_ratio_nominal=ratio,
            ipropi_trip_nominal_A=2.5/(.00045*eff),
            ipropi_trip_study_A=[min(v[0] for v in rows),max(v[0] for v in rows)],
            ipropi_ADC_ratio_study=[min(v[1] for v in rows),max(v[1] for v in rows)],
            current_study_corner_count=len(rows), switch_Ron_ohm=[0,4.5],
            inherited_VREF_fraction=.01, inherited_DRV_ratio_fraction=.075,
            VM_on_ratio_study=[min(v['on'] for v in vm),max(v['on'] for v in vm)],
            VM_off_ratio_study=[min(v['off'] for v in vm),max(v['off'] for v in vm)],
            VM_off_max_at15V=15*max(v['off'] for v in vm),
            powered_off_ADC_leakage_V_bound=2e-6*100000*hi,
            R26_ohm_study=[.1*rl_lo,.1*rl_hi],
            limitations=['Resistor temperatures are not ambient qualification.',
                'Inherited semiconductor bounds only; excludes aging, calibration, ADC errors, transients and thermal coupling.',
                'Powered-off switch bound applies at specified VDD=0, not every power ramp.',
                'R26 ripple and LAN regulator stability still require verification.']),
        power_examples=dict(RIPROPI_at2V5_mW=2.5**2/(6490*lo)*1000,
            minimum_1k_at3V399_mW=3.399**2/(1000*(1-.01)*(1-100e-6*dt))*1000,
            VM_upper_100k_conservative_full15V_mW=15**2/(100000*lo)*1000,
            continuous_3V399_across_33ohm_mW=3.399**2/33*1000,
            continuous_3V399_across_49R9_mW=3.399**2/49.9*1000,
            note='First three are bounded local examples. Last two exceed 0.1W and prohibit assuming full supply DC contention is acceptable. Real PHY/series waveforms need separate assessment.'),
        bulk_study=dict(nominal_F=.001,initial_tolerance_fraction=.20,
            initial_min_F=.0008,energy_nominal_12_to15_J=.5*.001*(15**2-12**2),
            energy_initial_min_12_to15_J=.5*.0008*(15**2-12**2),
            body_max_mm=[10.5,10.5,22],upright_stack_fit_verified=False,
            system_regen_verified=False,
            note='Initial tolerance only. Frequency, low temperature, aging, ESR/ESL and permitted bus transient can lower usable storage.'),
        pinmap_sha256=sha(PARENT/'pin-net.csv'),
        pending=['Controller PCB partition, land patterns and complete assembly envelope',
                 'DC-bias/aging and ripple/inrush/bulk sizing from actual waveforms',
                 'Regulator/reference stability, reset timing and PHY signal integrity',
                 'Supply/regen/short-circuit protection and calibration',
                 'Price, stock, controlled supplier specification and batch evidence'])
    dump(D/'selection-check.json', report)
    manifest = {str(p.relative_to(ROOT)):sha(p) for p in sorted(D.glob('*'))
                if p.is_file() and p.name not in ('manifest.json', 'independent-review.json')}
    dump(D/'manifest.json', dict(revision='HEAD-PASSIVES01', files=manifest,
                               schematic_ERC_not_rerun=True, reason='Frozen schematic unchanged; selection overlay only.'))
    print(json.dumps({'coverage':report['coverage'],
        'package_changes':len(report['package_changes']),
        'current_trip_A':report['resistor_temperature_study']['ipropi_trip_study_A']},indent=2))


if __name__ == '__main__':
    main()
