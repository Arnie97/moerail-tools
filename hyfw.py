#!/usr/bin/env python3

import json
import requests
from string import ascii_uppercase as alphabet
from typing import List, Dict

from interact import progress


def stations(pinyin: str) -> List[Dict[str, str]]:
    'Get all the stations from 95306.'
    # http://www.12306.cn/mormhweb/hyfw/hyckcx/
    url = 'http://dynamic.12306.cn/yjcx/doPickJZM'
    params = dict(param=pinyin, type=1, czlx=0)
    response = requests.post(url, params)
    return json.loads(response.text)


def dfs(pinyin='') -> List[Dict[str, str]]:
    'Load recursively when the API limit is exceeded.'
    progress()
    results = stations(pinyin)
    if len(results) < 100:
        return results
    else:
        return sum((dfs(pinyin + c) for c in alphabet), [])


if __name__ == '__main__':
    while True:
        results = dfs(input('> '))
        print()
        for r in results:
            print(str(r).replace("'", ''))
        print('=', len(results))
