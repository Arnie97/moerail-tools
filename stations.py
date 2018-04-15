#!/usr/bin/env python3

import sys
from typing import Iterable, List

from interact import shell
path = sys.argv[1] if len(sys.argv) > 1 else 'station_name.js'


def parse_stations(script: str) -> Iterable[List[str]]:
    'Split the dataset by delimiters.'
    # skip javascript stuff around single quotes
    # skip the first '@' character in the string
    packed_stations = script.split("'")[1][1:]
    for s in packed_stations.split('@'):
        yield s.split('|')


if __name__ == '__main__':
    with open(path) as f:
        s = list(parse_stations(f.read()))
        shell({'s': s}, 'len(s) == %d.' % len(s))
