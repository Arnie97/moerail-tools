#!/usr/bin/env python3

import re
import mwclient
from typing import Iterable, List, Sequence, TextIO

from stations import path, load_stations, dump_stations
from util import argv, open


class Wikipedia:

    def __init__(self, stations: Sequence[List[str]], provinces: Sequence):
        'Connect to Chinese Wikipedia.'
        self.site = mwclient.Site('zh.wikipedia.org')
        self.template = self.site.pages['T:Infobox China railway station']

        self.stations = stations
        self.names = {s[1]: index for index, s in enumerate(stations)}
        self.provinces = provinces

    def fill_missing_provinces(self) -> Sequence[List[str]]:
        'Try to fetch the province field from Chinese Wikipedia.'
        for station_page in self.template.embeddedin(namespace=0):
            self.parse_province_abbr(station_page)
        return self.stations

    def parse_province_abbr(self, page: mwclient.page.Page):
        'Fill in the province abbreviation of the station location.'
        match = re.match(r'(.+)(?:站|乘降所)', page.name)
        if not match:
            return print(page.name, '?')

        name = match.group(1)
        if name not in self.names:
            name = self.convert(title=name, uselang='zh-cn')
            if name not in self.names:
                return print(page.name, '/', name, '?')

        station = self.stations[self.names[name]]
        if station[-1]:
            return

        match = re.search(r'车站(?:位置|地址)\s*=(.+\S+)', page.text())
        if not match:
            return print(page.name, 'X')

        for code, abbr, province in self.provinces:
            if province in match.group(1):
                station[-1] = abbr
                return print(station[1], '->', abbr)

    def convert(self, **kwargs) -> str:
        'Convert between language variants, such as zh-CN and zh-TW.'
        return self.site.get('parse', **kwargs)['parse']['displaytitle']


def load_provices(file: TextIO) -> Iterable[List[str]]:
    'Load the province list from a text file.'
    for line in file:
        if line.strip():
            yield line.split()


if __name__ == '__main__':
    with open(path) as f:
        stations = list(load_stations(f.read()))
    with open(argv(2) or 'provinces.txt') as f:
        provinces = list(load_provices(f))

    stations = Wikipedia(stations, provinces).fill_missing_provinces()

    with open(path, 'w') as f:
        print(dump_stations(stations), file=f)
