#!/usr/bin/env python3

import sys
import readline
from typing import Callable


def progress(dot='.', file=sys.stdout):
    'Print a progress bar.'
    file.write(dot)
    file.flush()


def repl(handler: Callable, prompt='> '):
    'Prompt for user input.'
    while True:
        try:
            handler(input(prompt).strip())
        except (KeyboardInterrupt, EOFError):
            print()
            break


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
