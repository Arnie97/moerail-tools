#!/usr/bin/env python3

import time
import os.path
from typing import Iterable, List, TextIO

from shot import Automation
from trains import load_trains, decompose, path
from util import argv, open


def mkdir(path: str):
    'Create a directory if it does not exist.'
    if not os.path.exists(path):
        os.mkdir(path)
    elif os.listdir(path):
        msg = 'Warning: the target directory "%s" exists, and is not empty.'
        print(msg % path)


def emu_codes(data: dict, code_types='DGC') -> Iterable[str]:
    'Return the train codes within specific categories.'
    for day, trains in data.items():
        if not trains:
            continue
        for code_type in code_types:
            for train in trains[code_type]:
                yield decompose(train['station_train_code'])[0]


def unique_trains(file: TextIO) -> List[str]:
    'Return unique and sorted list of train codes.'
    print('Loading...')
    data = load_trains(file.read())
    codes = sorted(set(emu_codes(data)))
    print('Ready, %d trains to be checked.' % len(codes))
    return codes


def batch_query(me: Automation, codes: Iterable, img_dir: str, models: TextIO):
    'Save screenshots and train models for all the given trains.'
    for code in codes:
        try:
            me.query(code)
        except LookupError:
            print(code, 'not found?')
        else:
            img_path = os.path.join(img_dir, '%s.png' % code)
            me.get_shot().save(img_path)
            print(code, me.get_text(), file=models)


if __name__ == '__main__':
    me = Automation()
    with open(path) as f:
        codes = unique_trains(f)
    img_dir = argv(3) or 'img'
    mkdir(img_dir)
    time.sleep(5)

    with open(argv(2) or 'models.txt', 'w') as f:
        batch_query(me, codes, img_dir, f)
