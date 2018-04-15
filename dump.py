#!/usr/bin/env python3

from typing import List, Dict, Iterable

import kyfw
import hyfw
from stations import path


def stations() -> Dict[str, List[str]]:
    'Combine the two railway station datasets by telecode.'
    stations = {}
    stations_95306 = hyfw.dfs()
    stations_12306 = kyfw.stations()

    for s in stations_95306:
        pinyin = s['PYM'].lower()
        if len(pinyin) > 3:
            pinyin = pinyin[:2] + pinyin[-1]
        elif len(pinyin) < 3:
            pinyin = ''

        telecode = s['DBM']
        if telecode not in stations:
            stations[telecode] = [pinyin, s['ZMHZ'], s['TMIS'], s['SSJC']]

    for s in stations_12306:
        if s.telecode not in stations:
            stations[s.telecode] = [s.pinyin_code, s.name, '', '']
        else:
            stations[s.telecode][0] = s.pinyin_code

    return stations


def serialize(stations: Dict[str, List[str]]) -> Iterable[str]:
    'Dump the stations to delimiter-separated strings.'
    for k, v in stations.items():
        v.insert(2, k)
        yield '|'.join(v)


if __name__ == '__main__':
    with open(path, 'w') as f:
        all_stations = stations()
        serialized = '@'.join(serialize(all_stations))
        print("var station_names = '@%s';" % serialized, file=f)
        print('Dumped %d stations to "%s".' % (len(all_stations), path))
