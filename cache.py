#!/usr/bin/env python3

import time
import json
from shot import query


def load():
    # https://kyfw.12306.cn/otn/resources/js/query/train_list.js
    with open('train_list.js', encoding='utf-8') as f:
        json_text = f.read().partition('=')[2]
    return json.loads(json_text)


def main(src):
    codes = set()
    for day, trains in load().items():
        for train in trains['G'] + trains['D']:
            code = train['station_train_code'].partition('(')[0]
            codes.add(code)
    for code in codes:
        try:
            im = query(code).convert('1', dither=False)
        except LookupError:
            print(code, 'not found?')
        else:
            im.save(src + '%s.png' % code)


if __name__ == '__main__':
    time.sleep(5)
    main('temp/')
