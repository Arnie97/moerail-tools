#!/usr/bin/env python3

import time
import json
import os.path
from shot import Automation


def load():
    # https://kyfw.12306.cn/otn/resources/js/query/train_list.js
    with open('train_list.js', encoding='utf-8') as f:
        json_text = f.read().partition('=')[2]
    return json.loads(json_text)


def main(path):
    if not os.path.exists(path):
        os.mkdir(path)

    codes = set()
    for day, trains in load().items():
        if not trains:
            continue
        for type in 'DGC':
            for train in trains[type]:
                # G1234(Station A-Station B)
                code = train['station_train_code'].partition('(')[0]
                codes.add(code)

    me = Automation()
    for code in codes:
        try:
            me.query(code)
        except LookupError:
            print(code, 'not found?')
        else:
            me.get_shot().save(path + '%s.png' % code)
            print(code, me.get_text())


if __name__ == '__main__':
    time.sleep(5)
    main('img/')
