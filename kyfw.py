import requests
from collections import namedtuple
from typing import Iterable


fields = 'pinyin_code name telecode pinyin_full pinyin_short id'
Station = namedtuple('Station', fields.split())


def stations() -> Iterable[Station]:
    'Get all the train stations from 12306.'
    url = 'https://kyfw.12306.cn/otn/resources/js/framework/station_name.js'
    script = requests.get(url).text

    # skip javascript stuff around single quotes
    # skip the first '@' character in the string
    packed_stations = script.split("'")[1][1:]
    stations = []
    for s in packed_stations.split('@'):
        yield Station(*s.split('|'))
