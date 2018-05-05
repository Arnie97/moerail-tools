#!/usr/bin/env python3

import json
from typing import Iterable, Tuple

from sql import sql_shell
from util import shell, argv, open
path = argv(1) or 'train_list.js'


def decompose(s):
    'Split the information string by delimiters.'
    # G1234(Station A-Station B)
    return s.translate({
        ord(k): v for k, v in {
            '(': '|', '-': '|', ')': ''
        }.items()
    }).split('|')


def load_trains(script: str) -> dict:
    'Deserialize the jsonp script.'
    # https://kyfw.12306.cn/otn/resources/js/query/train_list.js
    json_text = script.partition('=')[2]
    return json.loads(json_text)


def parse_trains(data: dict) -> Iterable[Tuple[str, str, str, str]]:
    'Flatten the train list and return all items in it.'
    for day, trains in data.items():
        for train_type in trains.values():
            for train in train_type:
                train = train['train_no'], train['station_train_code']
                yield tuple([train[0]] + decompose(train[1]))


if __name__ == '__main__':
    print('Loading...')
    with open(path) as f:
        data = load_trains(f.read())
        t = list(set(parse_trains(data)))
    print('Ready.')

    for interpreter in shell, sql_shell:
        interpreter({'t': t}, 'len(t) == %d.' % len(t))
