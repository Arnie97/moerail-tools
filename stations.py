#!/usr/bin/env python3

from typing import Iterable, List

from sql import sql_shell
from util import shell, argv, open
path = argv(1) or 'station_name.js'


def load_stations(script: str) -> Iterable[List[str]]:
    'Split the dataset by delimiters.'
    # skip javascript stuff around single quotes
    # skip the first '@' character in the string
    packed_stations = script.split("'")[1][1:]
    for s in packed_stations.split('@'):
        yield s.split('|')


def dump_stations(stations: Iterable[List[str]]) -> str:
    'Serialize the stations to delimiter-separated strings.'
    serialized = '@'.join('|'.join(s) for s in stations)
    return "var station_names = '@%s';" % serialized


if __name__ == '__main__':
    with open(path) as f:
        s = list(load_stations(f.read()))

    for interpreter in shell, sql_shell:
        interpreter({'s': s}, 'len(s) == %d.' % len(s))

    with open(path, 'w') as f:
        print(dump_stations(s), file=f)
