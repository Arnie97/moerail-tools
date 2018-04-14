#!/usr/bin/env python3

import json
import requests
from collections import OrderedDict


def tmis(name='', bureau=0) -> OrderedDict:
    url = 'http://hyfw.12306.cn/hyinfo/action/FwcszsAction_getljcz'
    params = 'limit timestamp sheng shi'
    params = {k: '' for k in params.split()}
    params.update(q=name, ljdm=format(bureau, '02'))
    response = requests.post(url, params)
    list_of_dicts = json.loads(response.text)
    return OrderedDict((d['HZZM'], d['TMISM']) for d in list_of_dicts)


if __name__ == '__main__':
    while True:
        name = input('> ')
        results = tmis(name)
        if len(results) == 50:
            for i in range(1, 19):
                results.update(tmis(name, i))
        for k, v in results.items():
            print(k, v, sep='\t')
        print('=', len(results))
