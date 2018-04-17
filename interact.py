#!/usr/bin/env python3

import sys


def progress(dot='.', file=sys.stdout):
    'Print a progress bar.'
    file.write(dot)
    file.flush()


def shell(ns=None, banner=None):
    'Start an interactive shell.'
    try:
        import IPython
    except ImportError:
        import code
        return code.interact(banner, local=ns)
    else:
        params = dict(user_ns=ns)
        if banner is not None:
            params['banner1'] = banner
        return IPython.embed(**params)


if __name__ == '__main__':
    shell()
