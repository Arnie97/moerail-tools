import requests
from collections import namedtuple
from typing import Iterable

from stations import parse_stations


fields = 'pinyin_code name telecode pinyin_full pinyin_short id'
Station = namedtuple('Station', fields.split())


def stations() -> Iterable[Station]:
    'Get all the train stations from 12306.'
    url = 'https://kyfw.12306.cn/otn/resources/js/framework/station_name.js'
    script = requests.get(url).text
    for s in parse_stations(script):
        yield Station(*s)
