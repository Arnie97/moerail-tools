#!/usr/bin/env python3

import re
import json

from interact import argv


def main(src, dest):
    'Group the train routes by the vehicle model used.'
    pattern = r'新?CR[\w/-]+型(?:重联)?'
    with open(src) as f:
        lst = {}
        for line in f:
            code, _, model = line.partition(' ')
            try:
                models = re.findall(pattern, model)
                assert len(models) == 1
            except:
                print(line)
            else:
                model = models[0]
            if model not in lst:
                lst[model] = []
            lst[model].append(code)

    print(len(lst), 'models found:')
    print('\n'.join(sorted(lst.keys())))
    with open(dest, 'w') as f:
        json.dump(lst, f)


if __name__ == '__main__':
    main(argv(1) or 'models.txt', argv(2) or 'models.json')
