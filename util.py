#!/usr/bin/env python3

import sys
import os.path
import string
import builtins
from typing import Callable


class AttrDict(dict):
    'Make the keys accessible via attributes.'
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class FilterFormatter(string.Formatter):
    'Return an empty string for values that are interpreted as boolean false.'

    def get_field(self, field_name, args, kwargs):
        'Return the argument formatted by the format string in the brackets.'
        first, rest = string._string.formatter_field_name_split(field_name)
        obj = args[first] if isinstance(first, int) else kwargs.get(first)

        for is_attr, i in rest:
            if is_attr:
                obj = getattr(obj, i)
            elif obj:
                obj = self.format(i, obj, **kwargs)
            else:
                obj = ''

        return obj, first


def strip_lines(text: str, sep='') -> str:
    'Remove leading and trailing whitespace from each line in the text.'
    return sep.join(line.strip() for line in text.split('\n'))


def progress(dot='.', file=sys.stdout):
    'Print a progress bar.'
    file.write(dot)
    file.flush()


def repl(handler: Callable, prompt='> '):
    'Prompt for user input.'
    try:
        import readline
    except ImportError:
        pass
    else:
        readline.parse_and_bind('set disable-completion')

    while True:
        try:
            prompt = handler(input(prompt).strip()) or prompt
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
