#!/usr/bin/env python3

import json
import requests
from collections import OrderedDict


def tmis(name='') -> OrderedDict:
    url = 'http://hyfw.12306.cn/hyinfo/action/FwcszsAction_getljcz'
    params = 'limit timestamp sheng shi ljdm'
    params = {k: '' for k in params.split()}
    params['q'] = name
    response = requests.post(url, params)
    list_of_dicts = json.loads(response.text)
    return OrderedDict((d['HZZM'], d['TMISM']) for d in list_of_dicts)


if __name__ == '__main__':
    while True:
        for k, v in tmis(input('> ')).items():
            print(k, v, sep='\t')
