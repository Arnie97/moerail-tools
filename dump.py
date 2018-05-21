#!/usr/bin/env python3

from typing import List, Iterable

import kyfw
import hyfw
import tmis
from stations import path, dump_stations
from util import shell, progress, open, AttrDict


def combine_stations() -> Iterable[List[str]]:
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
            if s.telecode not in stations:
                stations[s.telecode] = [''] * 4
            stations[s.telecode][:2] = new[:2]
            continue

        # resolve merge conflicts manually
        shell(dict(vars(), s=stations), '\n%s' % conflict)

    for k, v in stations.items():
        # drop telecodes with spaces
        # so those can be used as temporary names in conflict solving
        v.insert(2, '' if ' ' in k else k)
        yield v


def heuristic_search(stations, initials=None) -> Iterable[List[str]]:
    'Search the TMIS database using name initials.'
    # create indexes for faster lookup
    names, tmis_codes = (
        {s[field]: index for index, s in enumerate(stations)}
        for field in (1, -2)
    )
    if not initials:
        initials = {name[0] for name in names}.union(
            {s[-1] for s in stations}
        )
    for initial in initials:
        progress()
        for name, tmis_code in tmis.dfs(initial).items():
            # append as a new station
            if name not in names and tmis_code not in tmis_codes:
                yield ['', name, '', tmis_code, '']

            # replace in-place
            elif name in names:
                old = stations[names[name]]
                if not old[-2]:
                    old[-2] = tmis_code
                elif old[-2] != tmis_code:
                    conflict = 'TMIS code conflict: %s' % old
                    shell(dict(vars(), s=stations), '\n%s' % conflict)


if __name__ == '__main__':
    stations = list(combine_stations())
    stations.extend(heuristic_search(stations))

    shell(dict(vars(), s=stations), 'Well done.')

    with open(path, 'w') as f:
        print(dump_stations(stations), file=f)
        print('Dumped %d stations to "%s".' % (len(stations), path))
