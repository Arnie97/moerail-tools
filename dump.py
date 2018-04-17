#!/usr/bin/env python3

from typing import List, Dict, Iterable

import kyfw
import hyfw
from tmis import tmis
from stations import path
from interact import shell


class AttrDict(dict):
    'Make the keys accessible via attributes.'
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


def stations() -> Dict[str, List[str]]:
    'Combine the two railway station datasets by telecode.'
    stations = AttrDict()
    names = {}
    stations_95306 = hyfw.dfs()
    stations_12306 = kyfw.stations()

    for s in stations_95306:
        pinyin = s['PYM'].lower()
        if len(pinyin) > 3:
            pinyin = pinyin[:2] + pinyin[-1]
        elif len(pinyin) < 3:
            pinyin = ''

        name, telecode = s['ZMHZ'], s['DBM']
        stations[telecode] = [pinyin, name, s['TMIS'], s['SSJC']]
        names[name] = telecode

    for s in stations_12306:
        old = stations.get(s.telecode)
        new = [s.pinyin_code, s.name, '', '']

        if s.name in names and s.telecode != names[s.name]:
            conflict = '%s/%s -> %s/%s' % (names[s.name], new, s.telecode, old)
            if s.telecode in stations:
                conflict = 'Name conflict: %s -> ?' % conflict
            else:
                conflict = 'Solved conflict: %s' % conflict
                old = stations[s.telecode] = stations.pop(names[s.name])
                old[:2] = new[:2]

        elif s.telecode in stations and s.name != stations[s.telecode][1]:
            new[-2] = tmis(s.name).get(s.name, '')
            conflict = '%s/(%s => %s)' % (s.telecode, old, new)

            if new[-2] and old[-2] != new[-2]:  # TMIS codes conflict
                conflict = 'Ambiguous telecode: %s' % conflict
            else:
                conflict = 'Solved conflict: %s' % conflict
                old[:2] = new[:2]

        else:
            conflict = None
            if s.telecode not in stations:
                stations[s.telecode] = [''] * 4
            stations[s.telecode][:2] = new[:2]

        if conflict:
            ns = AttrDict(vars())
            ns.s = ns.stations
            shell(ns, conflict)

    return stations


def serialize(stations: Dict[str, List[str]]) -> Iterable[str]:
    'Dump the stations to delimiter-separated strings.'
    for k, v in stations.items():
        v.insert(2, '' if ' ' in k else k)
        yield '|'.join(v)


if __name__ == '__main__':
    with open(path, 'w') as f:
        all_stations = stations()
        serialized = '@'.join(serialize(all_stations))
        print("var station_names = '@%s';" % serialized, file=f)
        print('Dumped %d stations to "%s".' % (len(all_stations), path))
