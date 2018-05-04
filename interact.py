#!/usr/bin/env python3

import sys
from typing import Callable


def progress(dot='.', file=sys.stdout):
    'Print a progress bar.'
    file.write(dot)
    file.flush()


def repl(handler: Callable, prompt='> '):
    'Prompt for user input.'
    try:
        import readline
        from stations import path, load_stations
        with open(path) as f:
            global names
            names = [s[1] for s in load_stations(f.read())]

    except (ImportError, FileNotFoundError):
        pass

    else:
        readline.parse_and_bind('tab: complete')
        readline.set_completer(suggestions)

    while True:
        try:
            handler(input(prompt).strip())
        except (KeyboardInterrupt, EOFError):
            print()
            break


def suggestions(text: str, state: int):
    'Generate completion suggestions.'
    text = text.strip()
    if not text:
        return
    p = [i for i in names if i.startswith(text)]
    if state < len(p):
        return p[state]


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


def argv(n: int, default='') -> str:
    'Return the n-th command-line argument if it exists, or default otherwise.'
    return sys.argv[n] if len(sys.argv) > n else default


if __name__ == '__main__':
    shell()
