#!/usr/bin/env python3

import json

from interact import shell


def decompose(s):
    # G1234(Station A-Station B)
    return s.translate({
        ord(k): v for k, v in {
            '(': ' ', '-': ' ', ')': ''
        }.items()
    }).split()


def load():
    # https://kyfw.12306.cn/otn/resources/js/query/train_list.js
    with open('train_list.js', encoding='utf-8') as f:
        json_text = f.read().partition('=')[2]
    return json.loads(json_text)


def main(data):
    for day, trains in data.items():
        for train_type in trains.values():
            for train in train_type:
                train = train['train_no'], train['station_train_code']
                yield tuple([train[0]] + decompose(train[1]))


if __name__ == '__main__':
    print('Loading...')
    t = list(set(main(load())))
    print('Ready.')
    shell({'t': t}, 'len(t) == %d.' % len(t))
