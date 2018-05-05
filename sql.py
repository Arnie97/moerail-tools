import sqlite3
from string import ascii_uppercase
from typing import Iterable, Sequence, Dict

from util import repl
conn = sqlite3.connect(':memory:')


def sql_shell(tables: Dict[str, Sequence[Sequence]], banner=None):
    'Start an interactive SQL interpreter.'
    for name, data in tables.items():
        headers = ascii_uppercase[:len(data[0])]
        sql_shell_init(data, headers, name)
    if banner is not None:
        print(banner)
    sql_shell.buffer = ''
    repl(sql_shell_handler, '--> ')


def sql_shell_init(data: Iterable[Sequence], headers: Sequence, table: str):
    'Import data into the SQLite database.'
    conn.execute(
        'CREATE TABLE %s (%s)' %
        (table, ','.join(h + ' TEXT' for h in headers))
    )
    conn.executemany(
        'INSERT INTO %s (%s) VALUES (%s)' %
        (table, ','.join(headers), ','.join(['?'] * len(headers))),
        data
    )


def sql_shell_handler(line: str):
    'Execute the SQL statement and print the results.'
    sql_shell.buffer += line + '\n'
    if not sqlite3.complete_statement(sql_shell.buffer):
        return '... '

    try:
        cursor = conn.cursor()
        cursor.execute(sql_shell.buffer)
    except sqlite3.Error as e:
        print(e)
    else:
        for row in cursor.fetchall():
            print(row)
    finally:
        sql_shell.buffer = ''
        return '--> '
