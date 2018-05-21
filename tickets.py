#!/usr/bin/env python3

import io
import json
import requests
from string import digits
from PIL import Image

from util import argv, open, AttrDict


class API:

    def __init__(self, params: dict):
        'Initialize the session.'
        self.site_root = 'https://kyfw.12306.cn/'
        self.session = requests.Session()
        self.session.headers = params.pop('headers')
        self.params = params

    def fetch(self, path, params, method, json=True, **kwargs):
        'Initiate an API request.'
        url = self.site_root + path
        params = self.params.get(params, params)
        query = 'params' if method == 'GET' else 'data'
        params.update(kwargs.get(query, {}))
        kwargs[query] = params
        response = self.session.request(method, url, **kwargs)
        return AttrDict(response.json()) if json else response

    def show_captcha(self):
        'Show the CAPTCHA image.'
        response = self.fetch(
            'passport/captcha/captcha-image',
            method='GET', params='captcha', json=False,
        )
        Image.open(io.BytesIO(response.content)).show()
        layout = '''
            -----------------
            | 0 | 1 | 2 | 3 |
            -----------------
            | 4 | 5 | 6 | 7 |
            -----------------
        '''
        for line in layout.split('\n'):
            print(line.strip())

    def input_captcha(self):
        'Convert the area IDs to coordinates.'
        coordinates = '''
            30,41 110,44 180,43 260,42
            35,95 105,98 185,97 255,96
        '''.split()
        answers = input('Please enter the area IDs, for example "604": ')
        return ','.join(coordinates[int(i)] for i in answers if i in digits)

    def check_captcha(self, coordinates: str):
        'Check whether the CAPTCHA answers are correct.'
        response = self.fetch(
            'passport/captcha/captcha-check',
            method='POST', params='captcha', data=dict(answer=coordinates),
        )
        assert response.result_code == '4', response.result_message
        print(response.result_message)


def main():
    'The entrypoint.'
    with open(argv(1) or 'tickets.json') as f:
        x = API(json.load(f))
    x.show_captcha()
    coordinates = x.input_captcha()
    x.check_captcha(coordinates)


if __name__ == '__main__':
    main()
