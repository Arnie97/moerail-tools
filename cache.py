#!/usr/bin/env python3

import time
import json
import os.path
from shot import Automation
from trains import load


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
