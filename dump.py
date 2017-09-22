#!/usr/bin/env python3

import sys
import re
import json


def main(argv):
    pattern = r'新?CR[\w/-]+型(?:重联)?'
    with open(argv[0]) as f:
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
    with open(argv[1], 'w') as f:
        json.dump(lst, f)


if __name__ == '__main__':
    main(sys.argv[1:])
