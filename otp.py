#!/usr/bin/env python3

import datetime
import requests

from util import repl


def station_encode(s: str) -> str:
    return '-' + '-'.join(
        '%02x' % byte
        for byte in s.encode('utf-8')
    )


def get_status(train, station, kind) -> requests.Response:
    url = 'http://dynamic.12306.cn/map_zwdcx/cx.jsp'
    params = {
        'cz': station,
        'cc': train,
        'cxlx': int(kind),
        'rq': datetime.date.today().isoformat(),
        'czEn': station_encode(station),
    }
    ua = {'User-Agent': 'Mozilla/5.0'}
    return requests.get(url, params, headers=ua)


def print_status(response: requests.Response):
    if response.status_code == 200:
        print('|', response.text.strip())
    else:
        print('X %d error' % response.status_code)


def main(options: str):
    options = options.split()
    if len(options) < 2:
        print('# usage: train stations')
        return False
    train, stations = options[0], options[1:]
    for station in stations:
        for kind in [0, 1]:
            print_status(get_status(train, station, kind))


if __name__ == '__main__':
    repl(main)
