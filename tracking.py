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
        'Catch the exceptions and print the error messages.'
        try:
            car_info = self.track_car(line.strip())
        except AssertionError as e:
            print(e)
        else:
            print(self.explain(car_info))
            print()

    @staticmethod
    def explain(info: AttrDict) -> str:
        'Format the query results.'
        info.arrDep = dict(A='到达', D='离开').get(info.arrDepId, '')
        if not info.carKind.endswith('车'):
            info.carKind += '车'

        explanation = '''
        截至 {eventDate} 时为止，
        您查询的{conName}所属的 {carNo} 号 {carType} 型{carKind}已被编入
        由{cdyAdm}{cdyStation}站开往{destAdm}{destStation}站
        的 {trainId} 次货物列车机后 {trainOrder} 位，
        负责运送编号为 {wbID} 的{cdyName}。该列车现已{arrDep}
        位于{eventProvince}{eventCity}的{eventAdm}{eventStation}站，
        距离终点站{destStation}站还有 {dzlc} km。
        '''
        return strip_lines(explanation).format(**info)


def strip_lines(text: str, sep='') -> str:
    'Remove leading and trailing whitespace from each line in the text.'
    return sep.join(line.strip() for line in text.split('\n'))


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
