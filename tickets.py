#!/usr/bin/env python3

import datetime
import io
import json
import os.path
import re
import requests
from getpass import getpass
from typing import BinaryIO, Iterable, Tuple
from urllib.parse import unquote

from util import module_dir, open, shell, strip_lines, AttrDict
today = datetime.date.today().isoformat()


class API:
    'https://example.com/'

    def __init__(self, params=None, headers=None):
        'Initialize the session.'
        self.session = requests.Session()
        self.params = params or {}
        if headers:
            self.session.headers = headers

    def fetch(self, path, params=None, method='POST', json=True, **kwargs):
        'Initiate an API request.'
        url = self.__doc__ + path
        if not isinstance(params, dict):
            params = self.params.get(params, {})
        query = 'params' if method == 'GET' else 'data'
        params.update(kwargs.get(query, {}))
        kwargs[query] = params
        response = self.session.request(method, url, **kwargs)
        return AttrDict(response.json()) if json else response


class Ticket(API):
    'https://kyfw.12306.cn/'

    def __init__(self, persist_cookies='cookies.json'):
        'Load the headers and cookies from external files.'
        with open(module_dir('tickets.json')) as f:
            params = json.load(f)
        super().__init__(params, params.pop('headers'))

        self.persist_cookies = persist_cookies
        if persist_cookies:
            if os.path.exists(persist_cookies):
                with open(persist_cookies) as f:
                    cj = requests.utils.cookiejar_from_dict(json.load(f))
                self.session.cookies = cj

        self.init_query_path()

    def init_query_path(self):
        'Get the API endpoint, which varies between "queryA" and "queryZ".'
        response = self.fetch('otn/leftTicket/init', json=False)
        query_path_pattern = re.compile("var CLeftTicketUrl = '(.+)';")
        self.query_path = query_path_pattern.search(response.text).group(1)

    def query(self, depart: str, arrive: str, date=today, student=False):
        'List trains between two stations.'
        response = self.fetch(
            'otn/' + self.query_path,
            method='GET', params=AttrDict([
                ('leftTicketDTO.train_date', date),
                ('leftTicketDTO.from_station', depart),
                ('leftTicketDTO.to_station', arrive),
                ('purpose_codes', '0x00' if student else 'ADULT')
            ])
        )
        return [train.split('|') for train in response.data['result']]

    def load_captcha(self) -> io.BytesIO:
        'Fetch the CAPTCHA image.'
        response = self.fetch(
            'passport/captcha/captcha-image',
            method='GET', params='captcha', json=False,
        )
        return io.BytesIO(response.content)

    def input_captcha(self) -> str:
        'Convert the area IDs to coordinates.'
        layout = '''
            -----------------
            | 0 | 1 | 2 | 3 |
            -----------------
            | 4 | 5 | 6 | 7 |
            -----------------
        '''
        coordinates = '''
            30,41 110,44 180,43 260,42
            35,95 105,98 185,97 255,96
        '''.split()
        print(strip_lines(layout, '\n'))
        answers = input('Please enter the area IDs, for example "604": ')
        return ','.join(coordinates[int(i)] for i in answers if i.isdigit())

    def check_captcha(self, coordinates: str):
        'Check whether the CAPTCHA answers are correct.'
        response = self.fetch(
            'passport/captcha/captcha-check',
            params='captcha', data=dict(answer=coordinates),
        )
        assert response.result_code == '4', response.result_message
        print(response.result_message)

    def login(self, **credentials):
        'Sign in to your 12306 account.'
        response = self.fetch(
            'passport/web/login',
            params='otn', data=credentials,
        )
        assert not response.result_code, response.result_message
        print(response.result_message)
        self.get_auth_token()
        self.save_cookies()

    def get_auth_token(self):
        'Get the user authentication tokens in cookies.'
        response = self.fetch('passport/web/auth/uamtk', 'otn')
        assert not response.result_code, response.result_message
        print(response.result_message)

        response = self.fetch('otn/uamauthclient', {'tk': response.newapptk})
        assert not response.result_code, response.result_message
        print('%s: %s' % (response.username, response.result_message))

    def save_cookies(self):
        'Save the cookies in a JSON file.'
        if self.persist_cookies:
            cj = requests.utils.dict_from_cookiejar(self.session.cookies)
            with open(self.persist_cookies, 'w') as f:
                json.dump(cj, f)

    def is_logged_in(self) -> bool:
        'Check whether the user is logged in.'
        response = self.fetch('otn/login/checkUser', 'att')
        return response.data['flag']

    def request_order(self, secret: str) -> Tuple[dict, dict]:
        'Request for order.'
        assert self.is_logged_in()
        self.fetch(
            'otn/leftTicket/submitOrderRequest', data={
                'secretStr': unquote(secret),
                'tour_flag': 'dc',
            }
        )
        response = self.fetch('otn/confirmPassenger/initDc', 'att', json=False)
        ticket_info_pattern = re.compile('ticketInfoForPassengerForm=(.*?);')
        ticket_info_json = ticket_info_pattern.search(response.text).group(1)
        ticket_info = json.loads(ticket_info_json.replace("'", '"'))

        token_pattern = re.compile("globalRepeatSubmitToken = '(.*?)'")
        token = token_pattern.search(response.text).group(1)
        return ticket_info, {'REPEAT_SUBMIT_TOKEN': token}

    def left_tickets(self, secret: str) -> Iterable[Tuple[str, str]]:
        'Get the count of remaining train tickets for each coach class.'
        ticket_info, token = self.request_order(secret)
        for k, v in ticket_info['queryLeftNewDetailDTO'].items():
            if k.endswith('_num') and int(v) >= 0:
                yield k[:-4], int(v)

    def list_passengers(self, token={}) -> dict:
        'List the available passengers in your 12306 account.'
        assert self.is_logged_in()
        response = self.fetch(
            'otn/confirmPassenger/getPassengerDTOs',
            params='att', data=token,
        )
        return response.data['normal_passengers']


def show_image(file: BinaryIO, img_path='captcha.jpg'):
    'Save the image to a file if Pillow is not installed.'
    try:
        from PIL import Image
    except ImportError:
        with open(img_path, 'wb') as f:
            f.write(file.read())
        print('Open the image "%s" to solve the CAPTCHA.' % img_path)
    else:
        Image.open(file).show()


def main():
    'The entrypoint.'
    x = Ticket()
    if x.is_logged_in():
        print('Already logged in.')
    else:
        show_image(x.load_captcha())
        coordinates = x.input_captcha()
        x.check_captcha(coordinates)
        x.login(username=input('Login: '), password=getpass())

    Z53 = x.query('SJP', 'WCN')[-1]
    print(dict(x.left_tickets(Z53[0])))
    shell(vars())


if __name__ == '__main__':
    main()
