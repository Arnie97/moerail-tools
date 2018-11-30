#!/usr/bin/env python3

import io
import re

from util import module_dir, repl, strip_lines, AttrDict, FilterFormatter
from tickets import show_image, API

CAR_OR_CONTAINER_PATTERN = r'([A-Z]{4})?[0-9]{7}'


class Tracking(API):
    'http://hyfw.95306.cn/gateway/hywx/TrainWebClient/'

    def __init__(self):
        'Initialize the session.'
        super().__init__()
        self.format = FilterFormatter().format
        response = self.fetch('hwzzPage.action', method='GET', json=False)
        pattern = '<input id="maths" .+? value="(.+?)" />'
        self.params[None] = {
            'mathsid': re.search(pattern, response.text).group(1),
            'hwzz.yzm': '63FD155B6A364CB4BC1680C1F74B4B37',
        }

    def load_captcha(self) -> io.BytesIO:
        'Fetch the CAPTCHA image.'
        params = dict(math=0, update=self.params[None]['mathsid'])
        response = self.fetch(
            'security/jcaptcha.jpg',
            method='GET', params=params, json=False,
        )
        return io.BytesIO(response.content)

    def fill_captcha(self, answer: str):
        'Save the recognized CAPTCHA text.'
        self.params[None]['check_code'] = answer

    def track(self, **kwargs) -> AttrDict:
        'Send the tracking request and parse the response message.'
        # insert the namespace prefix for each key
        data = {'hwzz.' + k: v for k, v in kwargs.items()}
        response = self.fetch('hwzz_uouii.action', data=data)
        assert response.success, response.get('message', response.get('msg'))
        return AttrDict(response.object[0])

    def track_car(self, car_no: str='0000000') -> AttrDict:
        'Track your rail shipment by car number.'
        return self.track(type=1, carNo=car_no, hph='')

    def track_container(self, container_no: str) -> AttrDict:
        'Track your rail shipment by container number.'
        return self.track(type=5, xz=container_no[:4], xh=container_no[4:])

    def repl_handler(self, line: str):
        'Catch the exceptions and print the error messages.'
        if not re.fullmatch(CAR_OR_CONTAINER_PATTERN, line):
            print('Invalid query:', line)
            return
        method = self.track_car if line.isdigit() else self.track_container
        try:
            info = method(line)
        except (AssertionError, KeyError) as e:
            print(e)
        else:
            print(self.explain(info))
        finally:
            print()

    def explain(self, info: AttrDict) -> str:
        'Convert the query result to a human-readable text message.'
        # remove trailing whitespace and null values
        for k, v in info.items():
            info[k] = str(v).rstrip()
            if info[k] in ['0', '-1', '发货人']:
                info[k] = ''

        # rename some fields to fit into the template
        converters = {
            'fz': 'cdyStation',
            'dz': 'destStation',
            'pm': 'cdyName',
            'xh': 'carNo',
            'tyrName': 'shpName',
            'conName': 'shpName',
            'wbID': 'wbNbr',
        }
        for k, v in converters.items():
            info[v] = info[v] or info[k]

        if info.conName == info.shpName:
            info.conName = ''
        elif info.conName:
            info.conName = '，发往' + info.conName

        if info.xh:
            info.carKind = '集装箱'
            info.carLE = 'L' if info.cdyName else 'E'
        elif info.carType.startswith(info.carKind):
            info.carKind = '车辆'

        if not info.cdyName:
            status = ''
        elif info.carLE == 'L':
            status = '负责运送{wbNbr[单号为 {} 的]}{cdyName}'
            if info.cdyName[-1:].isdigit():
                info.cdyName += '型集装箱'
        else:
            status = '当前状态为{cdyName}{wbNbr[，运单号为 {}]}'
            if info.cdyName.endswith('空'):
                info.cdyName += '车'
        if info.get('trainId'):
            info.train = ' %s 次列车' % info.trainId

        info.arrDep = {
            '': dict(A='到达', D='离开').get(info.arrDepId),
            '在站': '到达',
            '在途': '离开',
        }.get(info.xt) or '到达'

        explanation = '''
        截至 {eventDate} 时为止，您查询的{shpName[由{}托运{conName}的]}
        {carNo[ {} 号]}{carType[ {} 型]}{carKind}
        {cdyStation[已从{cdyAdm}{}站发出，]}
        {destStation[前往{destAdm}{}站，]}%s{cdyName[。该车]}
        {train[现被编入{}]}{trainOrder[机后第 {} 位]}{train[，]}
        目前已{arrDep}{eventProvince[位于{}{eventCity}的]}
        {eventAdm}{eventStation}站
        {dzlc[，距离终点站{destStation}站还有 {} km]}。
        ''' % status
        return self.format(strip_lines(explanation), **info)


def solve_captcha(captcha_image: io.BytesIO) -> str:
    'Solve the CAPTCHA image.'
    from captcha.captcha import image_filter, solve
    captcha_image = image_filter(captcha_image)
    template_image = module_dir('captcha/tests/templates/95306.bmp')
    answer_digits = solve(captcha_image, template_image)
    return ''.join(map(str, answer_digits))


def auth():
    'Load and answer the CAPTCHA to get a valid session.'
    x = Tracking()
    captcha_image = x.load_captcha()
    try:
        x.fill_captcha(solve_captcha(captcha_image))
        x.track_car()
    except (ImportError, AssertionError) as e:
        print(e)
        show_image(captcha_image)
    else:
        return x

    while True:
        try:
            x.fill_captcha(input('# ').strip())
            x.track_car()
        except AssertionError as e:
            print(e)
        else:
            return x


if __name__ == '__main__':
    repl(auth().repl_handler)
