#!/usr/bin/env python3

import datetime
import io
import json
import requests
from string import digits
from typing import BinaryIO

from util import argv, open, shell, AttrDict
today = datetime.date.today().isoformat()


class API:

    def __init__(self, params: dict):
        'Initialize the session.'
        self.site_root = 'https://kyfw.12306.cn/'
        self.session = requests.Session()
        self.session.headers = params.pop('headers')
        self.params = params

    def fetch(self, path, params=None, method='POST', json=True, **kwargs):
        'Initiate an API request.'
        url = self.site_root + path
        if not isinstance(params, dict):
            params = self.params.get(params, {})
        query = 'params' if method == 'GET' else 'data'
        params.update(kwargs.get(query, {}))
        kwargs[query] = params
        response = self.session.request(method, url, **kwargs)
        return AttrDict(response.json()) if json else response

    def query(self, depart: str, arrive: str, date=today, student=False):
        'List trains between two stations.'
        response = self.fetch(
            'otn/leftTicket/query',
            method='GET', params=AttrDict([
                ('leftTicketDTO.train_date', date),
                ('leftTicketDTO.from_station', depart),
                ('leftTicketDTO.to_station', arrive),
                ('purpose_codes', '0x00' if student else 'ADULT')
            ])
        )
        return [train.split('|') for train in response.data['result']]

    def show_captcha(self):
        'Show the CAPTCHA image.'
        response = self.fetch(
            'passport/captcha/captcha-image',
            method='GET', params='captcha', json=False,
        )
        show_image(io.BytesIO(response.content))
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
            params='captcha', data=dict(answer=coordinates),
        )
        assert response.result_code == '4', response.result_message
        print(response.result_message)

    def login(self, **credentials):
        response = self.fetch(
            'passport/web/login',
            params='otn', data=credentials,
        )
        assert not response.result_code, response.result_message
        print(response.result_message)

        self.fetch('otn/login/userLogin', 'att', json=False)

        response = self.fetch('passport/web/auth/uamtk', 'otn')
        assert not response.result_code, response.result_message
        print(response.result_message)

        response = self.fetch(
            'otn/uamauthclient',
            data=dict(tk=response.newapptk)
        )
        assert not response.result_code, response.result_message
        print('%s: %s' % (response.username, response.result_message))

        self.fetch('otn/index/initMy12306', method='GET', json=False)


def show_image(file: BinaryIO):
    'Save the image to a file if Pillow is not installed.'
    try:
        from PIL import Image
    except ImportError:
        img_path = argv(2) or 'captcha.jpg'
        with open(img_path, 'wb') as f:
            f.write(file.read())
        print('Open the image "%s" to solve the CAPTCHA.' % img_path)
    else:
        Image.open(file).show()


def main():
    'The entrypoint.'
    with open(argv(1) or 'tickets.json') as f:
        x = API(json.load(f))

    t = x.query('BJP', 'SHH')
    shell({'t': t}, 'len(t) == %d.' % len(t))

    x.show_captcha()
    coordinates = x.input_captcha()
    x.check_captcha(coordinates)
    x.login(username=input('Login: '), password=input('Password: '))


if __name__ == '__main__':
    main()
