# SPDX-License-Identifier: CC-BY-NC-4.0
"""Explicit replacement chain: no duplicate old plate or cowls in assembly."""
import json
import common as c
CORE=['root01','skeleton01','hardware01','covers02']
MODULES=['root-cover03','cowls04','wrist05','skins06']

def collect(last=None,meshes=False):
    items={};sources={};operations=[]
    for name in CORE+MODULES:
        path=c.OUT/name/'manifest.json'
        if not path.exists():
            if name in CORE:raise FileNotFoundError(path)
            continue
        d=json.loads(path.read_text());assert d['layout']==c.L
        sources[str(path.relative_to(c.ROOT))]=c.sha(path)
        if meshes:
            mp=path.parent/'meshes.json';rows=json.loads(mp.read_text());sources[str(mp.relative_to(c.ROOT))]=c.sha(mp)
        else:rows=d['parts']
        for old in d.get('replaces_only',[]):
            assert old in items,(name,'unmatched replacement',old)
            del items[old];operations.append(dict(module=name,remove=old))
        for p in rows:
            assert p['id'] not in items,(name,'duplicate',p['id'])
            f=path.parent/'step'/(p['id']+'.step');sources[str(f.relative_to(c.ROOT))]=c.sha(f)
            items[p['id']]=dict(p,source_module=name,step_path=str(f.relative_to(c.ROOT)))
        if name==last:break
    return list(items.values()),sources,operations
