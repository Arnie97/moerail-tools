#!/usr/bin/env python3

import json
import requests
from collections import OrderedDict

from util import repl, progress


def tmis(name='', bureau=0) -> OrderedDict:
    url = 'http://hyfw.12306.cn/hyinfo/action/FwcszsAction_getljcz'
    params = 'limit timestamp sheng shi'
    params = {k: '' for k in params.split()}
    params.update(q=name, ljdm=format(bureau, '02'))
    while True:
        try:
            response = requests.post(url, params, timeout=1).json()
        except (requests.exceptions.Timeout, json.JSONDecodeError):
            progress('X')
        else:
            break
    return OrderedDict((d['HZZM'], d['TMISM']) for d in response)


def dfs(name='') -> OrderedDict:
    'Split bulk requests into chunks.'
    results = tmis(name)
    if len(results) == 50:
        for i in range(1, 19):
            progress()
            results.update(tmis(name, i))
    return results


def main(name: str):
    'Format the query results.'
    results = dfs(name)
    if len(results) >= 50:
        print()
    for k, v in results.items():
        print('|', k.ljust(5, '\u3000'), v)
    print('=', len(results), '\n')


if __name__ == '__main__':
    repl(main)
