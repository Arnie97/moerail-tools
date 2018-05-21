#!/usr/bin/env python3

import sys
import os.path
import builtins
from typing import Callable


class AttrDict(dict):
    'Make the keys accessible via attributes.'
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


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
            suggestions.list = [s[1] for s in load_stations(f.read())]

    except (ImportError, FileNotFoundError):
        pass

    else:
        readline.parse_and_bind('tab: complete')
        readline.set_completer(suggestions)

    while True:
        try:
            prompt = handler(input(prompt).strip()) or prompt
        except (KeyboardInterrupt, EOFError):
            print()
            break


def suggestions(text: str, state: int):
    'Generate completion suggestions.'
    text = text.strip()
    if not text:
        return
    p = [i for i in suggestions.list if i.startswith(text)]
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


def module_dir(path='') -> str:
    'Return the location of this module, and append the path to it if given.'
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(here, path)


def argv(n: int, default='') -> str:
    'Return the n-th command-line argument if it exists, or default otherwise.'
    return sys.argv[n] if len(sys.argv) > n else default


def open(file, mode='r', buffering=-1, encoding=None, *args, **kwargs):
    'Open text files as UTF-8 by default.'
    if 'b' not in mode and encoding is None:
        encoding = 'utf-8'
    return builtins.open(file, mode, buffering, encoding, *args, **kwargs)


if __name__ == '__main__':
    shell()
