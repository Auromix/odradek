#!/usr/bin/env python3
"""Build the offline A05 viewer from readable source files. CC-BY-NC-4.0."""
from pathlib import Path
import argparse,json

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser()
parser.add_argument('--inline-copy',type=Path)
args=parser.parse_args()
template=ROOT/'docs/viewers/arm-body/a05.template.html'
layout=ROOT/'engineering/parameters/arm-a05-layout.json'
data=json.loads(layout.read_text())
html=template.read_text()
replacements={
 'LAYOUT':json.dumps(data,ensure_ascii=False,separators=(',',':')),
 'THREE':(ROOT/'docs/viewers/arm-body/vendor/three-r160.min.js').read_text(),
 'MODEL':(ROOT/'engineering/arm_a05/model.js').read_text(),
 'VIEWER':(ROOT/'engineering/arm_a05/viewer.js').read_text()
}
for key,value in replacements.items():
    html=html.replace('@@'+key+'@@',value)
assert '@@' not in html
assert len(html.encode())<1_000_000
target=ROOT/'docs/viewers/arm-body/arm-body-viewer.html'
target.write_text(html)
if args.inline_copy:
    args.inline_copy.parent.mkdir(parents=True,exist_ok=True)
    args.inline_copy.write_text(html)
print(f'A05 built: {len(html.encode())} bytes')
