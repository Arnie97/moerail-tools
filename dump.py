#!/usr/bin/env python3

import sys
import re
import json


def main(argv):
    pattern = r'新?CR[\w-]+型(重联)?'
    with open(argv[0]) as f:
        lst = {}
        for line in f:
            code, _, model = line.partition(' ')
            model = re.match(pattern, model)[0]
            if model not in lst:
                lst[model] = []
            lst[model].append(code)

    with open(argv[1], 'w') as f:
        json.dump(lst, f)


if __name__ == '__main__':
    main(sys.argv[1:])
