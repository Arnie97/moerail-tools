#!/usr/bin/env python3

import io
import re
import requests

from util import repl, AttrDict
from tickets import show_image, API


class Tracking(API):
    'http://hyfw.95306.cn/gateway/hywx/TrainWebClient/'

    def __init__(self):
        'Initialize the session.'
        self.session = requests.Session()
        self.params = {}
        response = self.fetch('hwzzPage.action', method='GET', json=False)
        pattern = '<input id="maths" .+? value="(.+?)" />'
        self.query = {
            'mathsid': re.search(pattern, response.text).group(1),
            'hwzz.yzm': '63FD155B6A364CB4BC1680C1F74B4B37',
            'hwzz.type': 1,
            'hwzz.hph': '',
        }

    def show_captcha(self):
        'Show the CAPTCHA image.'
        params = dict(math=0, update=self.query['mathsid'])
        response = self.fetch(
            'security/jcaptcha.jpg',
            method='GET', params=params, json=False,
        )
        show_image(io.BytesIO(response.content))

    def check_captcha(self, answer: str, test_case='1234567'):
        'Check whether the CAPTCHA answers are correct.'
        self.query['check_code'] = answer
        self.track_car(test_case)

    def track_car(self, car_no: str) -> AttrDict:
        'Track your rail shipment by car number.'
        self.query['hwzz.carNo'] = car_no
        response = self.fetch('hwzz_uouii.action', self.query)
        assert response.success, response.get('message', response.get('msg'))
        return AttrDict(response.object[0])

    def repl_handler(self, line: str):
        'Format the query results.'
        try:
            car_info = self.track_car(line.strip())
        except AssertionError as e:
            print(e)
        else:
            for k, v in car_info.items():
                if v:
                    print(k, ': ', v, sep='')
            print()


def auth():
    'Solve the CAPTCHA to get a valid session.'
    x = Tracking()
    while True:
        x.show_captcha()
        try:
            x.check_captcha(input('# ').strip())
        except AssertionError as e:
            print(e)
        else:
            return x


if __name__ == '__main__':
    repl(auth().repl_handler)
