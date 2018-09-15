#!/usr/bin/env python3

import io
import re
import requests

from util import module_dir, repl, AttrDict, FilterFormatter
from tickets import show_image, API


class Tracking(API):
    'http://hyfw.95306.cn/gateway/DzswNewD2D/Dzsw/'

    def __init__(self):
        'Initialize the session.'
        self.format = FilterFormatter().format
        self.session = requests.Session()
        self.params = {}
        self.fetch('page/business-chcx-hwzzsy', method='GET', json=False)

    def load_captcha(self) -> io.BytesIO:
        'Fetch the CAPTCHA image.'
        response = self.fetch(
            'security/jcaptcha.jpg',
            method='GET', json=False,
        )
        return io.BytesIO(response.content)

    def check_captcha(self):
        'Load and answer the CAPTCHA to get a valid session.'
        captcha_image = self.load_captcha()
        try:
            return solve_captcha(captcha_image)
        except ImportError as e:
            print(e)
            show_image(captcha_image)
            return input('# ').strip()
        except AssertionError as e:
            return self.check_captcha()

    def track(self, path: str, **data) -> AttrDict:
        'Send the tracking request and parse the response message.'
        path = (
            'action/ChcxAction_query%s;DZSW_SESSIONID=Gtnad16GUaNSpTSnWR1_'
            '-H5zsKIBvKgnao0eRvMR9c97gLekevwj!2012403419'
        ) % path
        data['QUERY_CAPTCA'] = self.check_captcha()
        response = self.fetch(path, data)
        assert response.success, response.get('message', response.get('msg'))
        return AttrDict(response.object[0])

    def track_car(self, car_no: str) -> AttrDict:
        'Track your rail shipment by car number.'
        assert len(car_no) == 7, 'Illegal car number'
        return self.track('HwzzInfoByCarNo', carNo=car_no, hph='')

    def track_container(self, container_no: str) -> AttrDict:
        'Track your rail shipment by container number.'
        assert len(container_no) == 11, 'Illegal container number'
        return self.track(
            'XhInfoByJzxNo', xz=container_no[:4], xh=container_no[4:]
        )

    def repl_handler(self, line: str):
        'Catch the exceptions and print the error messages.'
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
        'Format the query results.'
        converters = {
            'fz': 'cdyStation',
            'dz': 'destStation',
            'pm': 'cdyName',
            'xh': 'carNo',
            'tyrName': 'conName',
        }
        for k, v in converters.items():
            info[v] = info[v] or info[k]
        if not info.wbID or info.wbID == '-1':
            info.wbID = info.wbNbr
        if info.xh:
            info.carKind = '集装箱'
            info.carLE = 'L' if info.cdyName else 'E'
        elif info.carType.startswith(info.carKind):
            info.carKind = '车辆'
        if info.carLE == 'L':
            status = '负责运送{wbID[编号为 {} 的]}{cdyName}'
            if info.cdyName[-1].isdigit():
                info.cdyName += '类货物'
        else:
            status = '当前状态为{cdyName}{wbID[，编号为 {}]}'
            if info.cdyName.endswith('空'):
                info.cdyName += '车'
            elif not info.cdyName.strip():
                info.cdyName = '空'
        info.arrDep = {
            '': dict(A='到达', D='离开').get(info.arrDepId),
            '在站': '到达',
            '在途': '离开',
        }.get(info.xt) or '到达'

        explanation = '''
        截至 {eventDate} 时为止，您查询的{conName[由{}托运的]}
        {carNo[ {} 号]}{carType[ {} 型]}{carKind}
        {cdyStation[已从{cdyAdm}{}站发出，]}
        {destStation[前往{destAdm}{}站，]}%s。
        该车%s目前已{arrDep}{eventProvince[位于{}{eventCity}的]}
        {eventAdm}{eventStation}站
        {dzlc[，距离终点站{destStation}站还有 {} km]}。
        '''

        explanation %= status, '''
        现被编入{trainId[ {} 次列车]}{train[{}]}
        机后第 {trainOrder} 位，
        ''' if info.trainOrder else ''

        return self.format(strip_lines(explanation), **info)


def strip_lines(text: str, sep='') -> str:
    'Remove leading and trailing whitespace from each line in the text.'
    return sep.join(line.strip() for line in text.split('\n'))


def solve_captcha(captcha_image: io.BytesIO) -> str:
    'Solve the CAPTCHA image.'
    import pytesseract
    from captcha.captcha import image_filter, remove_noise, vertical_align
    captcha_image = image_filter(captcha_image, threshold=160)
    captcha_image = vertical_align(remove_noise(captcha_image, radius=2))
    answer = pytesseract.image_to_string(captcha_image)
    assert len(answer) == 5
    return answer


if __name__ == '__main__':
    repl(Tracking().repl_handler)
