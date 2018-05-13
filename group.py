#!/usr/bin/env python3

import re
import json
from typing import Dict, TextIO

from util import argv, open
PATTERN = r'新?CR[\w/-]+型(?:重联)?'


def group(file: TextIO) -> Dict[str, list]:
    'Group the train routes by the vehicle model used.'
    lst = {}
    for line in file:
        code, _, model = line.partition(' ')
        try:
            models = re.findall(PATTERN, model)
            assert len(models) == 1
        except:
            print(line)
        else:
            model = models[0]
        if model not in lst:
            lst[model] = []
        lst[model].append(code)
    return lst


def main(src, dest):
    with open(src) as f:
        lst = group(f)
    print('\n'.join(sorted(lst.keys())))
    print(len(lst), 'models found.')
    with open(dest, 'w') as f:
        json.dump(lst, f)


if __name__ == '__main__':
    main(argv(1) or 'models.txt', argv(2) or 'models.json')
