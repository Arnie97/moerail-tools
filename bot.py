#!/usr/bin/env python3

import PIL.Image
import datetime
import html
import io
import json
import locale
import logging
import mwclient
import platform
import random
import re
import requests
import subprocess
import sys
import time
import traceback
import warnings
import zbar
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from difflib import get_close_matches
from itertools import chain, islice
from typing import Callable, Dict, Iterable, Tuple

from cqhttp import CQHttp
from util import argv, open, strip_lines, AttrDict
from trains import load_trains, parse_trains, sort_trains
from tracking import HyfwTracking, CrscTracking
from tracking import solve_captcha, CAR_OR_CONTAINER_PATTERN
from wifi12306 import Wifi12306

bot = CQHttp('http://localhost:5700/')
api = HyfwTracking()
crsc = CrscTracking()
wifi = Wifi12306()
scanner = zbar.ImageScanner()


def unescape(text: str) -> str:
    'Remove the escape codes.'
    escape_codes = '''
        & &amp;
        [ &#91;
        ] &#93;
        , &#44;
    '''
    escape_codes = [line.split() for line in escape_codes.strip().splitlines()]

    text = re.sub(r'\[CQ:.+?\]', '', text)
    for symbol, codes in escape_codes:
        text = text.replace(codes, symbol)
    return text


@bot.on_notice()
def new_notice(context):
    'Detect file uploads and new group members.'
    context = AttrDict(context)
    if (
        context.notice_type == 'group_upload' and
        context.file['name'] == 'base.apk'
    ):
        reply = '怎么又双叒叕是 base.apk [CQ:face,id=39]'
    elif context.notice_type == 'group_increase':
        reply = '群地位-1'
    else:
        return
    context.message_type = 'group'
    bot.send(context, reply)


@bot.on_request()
def new_request(context):
    'Accepts friend requests from administrators.'
    if context['user_id'] in limit.administrators:
        return {'approve': True}


@bot.on_message()
def new_message(context):
    'Wraps the message event.'
    context = AttrDict(context)
    context.sender = AttrDict(context.sender)
    context.message = unescape(context.raw_message).strip()
    if context.message_type == 'private' and not parse_loopback(context):
        return
    elif context.sender.user_id in limit.administrators:
        reply = parse_shell(context)
        if reply is not None:
            return dict(reply=reply, at_sender=False)
        elif context.message_type == 'private':
            return dict(reply=context.raw_message, auto_escape=True)
    GroupMessageHandler(context)()


def parse_loopback(context) -> bool:
    'Send group messages according to manual commands.'
    if not context.raw_message.startswith('@'):
        return True
    factors = context.raw_message[1:].partition(' ')
    group_key, delimit, text = factors
    matches = all(factors) and [
        group for group in bot.get_group_list()
        if group_key in group['group_name']
    ]
    if context.sender.user_id in limit.black_list:
        reply = '哼，坏蛋，不理你了！'
    elif not matches:
        reply = '''语法：@群名 要发送的消息

        可以将群名的任何一部分作为群名缩写。
        缩写长度不限，只要不与机器人已加入的其他群的名称相混淆即可。
        '''
        reply = strip_lines(reply, '\n').strip()
    elif len(matches) > 1:
        reply = '「%s」指的是哪个群呢？' % group_key
        reply += '\n' + '\n'.join(
            '{group_name}（{group_id}）'.format_map(group)
            for group in matches
        )
    else:
        bot.send_group_msg(group_id=matches[0]['group_id'], message=text)
        return
    bot.send(context, reply)


def parse_shell(context) -> str:
    'Provide Python and Bash shells.'
    if context.message.startswith('$'):
        command = context.message[1:].strip()
        proc = subprocess.run(command, shell=True, capture_output=True)
        return proc.stdout.decode(locale.getpreferredencoding()).strip()

    elif context.message.startswith('>>>'):
        command = context.message[3:].strip()
        result = python_interpreter(command, locals=dict(context=context))
        return '--> ' + result

    elif context.message.startswith('//'):
        if context.message_type != 'group':
            return system_info()
        elif context.group_id in limit.disabled_groups:
            limit.disabled_groups.discard(context.group_id)
            return '我回来啦（'
        else:
            limit.disabled_groups.add(context.group_id)
            return '下班喽~'


def python_interpreter(source, globals=None, locals=None) -> str:
    'Run the Python code snippet and collect all the output as a string.'
    result = io.StringIO()
    try:
        code_obj = compile(source, '<interpreter>', 'single')
        with redirect_stdout(result):
            exec(code_obj, globals, locals)
    except:
        exc_type, exc_value, tb = sys.exc_info()
        result.write(traceback.format_exception_only(exc_type, exc_value)[-1])
        traceback.print_exc()
    return result.getvalue().strip()


def system_info() -> str:
    'Provide a summary of runtime environment.'
    reply = '''
        {0.node} (up {1} days, {2})
        {0.system} {0.release}
        {3} {4}
        CoolQ HTTP API v{5[plugin_version]}
    '''
    uptime = datetime.timedelta(seconds=time.monotonic())
    uptime_hms = time.strftime('%H:%M:%S', time.gmtime(uptime.seconds))
    python_version = platform.python_build()[0]
    if platform.python_version() not in python_version:
        python_version = 'v%s (%s)' % (platform.python_version(), python_version)
    return strip_lines(reply, '\n').strip().format(
        platform.uname(), uptime.days, uptime_hms,
        platform.python_implementation(), python_version,
        bot.get_version_info(),
    )


def match_identifiers(text: str, remove='-') -> OrderedDict:
    'Return all non-overlapping identifiers in the text, with hyphens removed.'
    pattern = r'(?a)(?<!\w)([A-Z][-\w]+|\d{4,8}|\w+[-A-Z]\w*)(?!\w)'
    return OrderedDict(
        (i.replace(remove, ''), i)
        for i in re.findall(pattern, text)
    )


class GroupMessageHandler(AttrDict):

    def __init__(context, original_context: dict):
        'Extract identifiers from the message.'
        context.update(original_context)
        notification = '[CQ:at,qq={self_id}]'.format_map(context)
        context.notified = notification in context.raw_message
        context.mentioned = re.findall(limit.self, context.raw_message)
        context.identifiers = match_identifiers(context.message)
        context.sender.title = (
            context.sender.get('title') or
            limit.titles.get(context.sender.user_id, '')
        )

    def __call__(context) -> bool:
        'Response the query.'
        # short-circuit evaluation, stops at the first match
        unknown_items = (
            context.message_type == 'group' and
            context.share_filter() and
            context.qr_scan_filter() and
            (context.notified or context.mentioned) and
            context.greeting_filter() and
            context.abuse_filter() and
            context.speed_filter() and
            [
                context.winsky_filter(i) and
                context.model_filter(i) and
                context.train_filter(i) and
                context.tracking_filter(i) and
                context.shanghai_filter(i) and
                context.beijing_filter(i) and
                context.flight_filter(i)
                for i in context.identifiers
            ]
        )
        if (  # if the message is understandable as a whole, i.e.
            not unknown_items or  # a) greeting keywords found in the message
            all(unknown_items) and  # b) no identifiers were understood yet :(
            # if the whole message is not just a single identifier,
            context.message not in context.identifiers.values() and
            # and it matches a wiki article without word segmentation
            not context.wiki_filter()
        ):
            return  # then stop here and forget about identifiers

        unknown_items = [
            context.identifiers[i]
            for unknown, i in zip(unknown_items, context.identifiers)
            if unknown and
            context.wiki_filter(i) and
            context.wildcard_train_filter(i) and
            context.wildcard_model_filter(i)
        ]
        if any(unknown_items):
            reply = '%s 是什么哦，没见过呢'
            reply %= '、'.join(unknown_items)
            bot.send(context, reply)

        """
        match = re.fullmatch(r'''
            \[CQ:rich,
                title   = (?P<title>[^\],]+),
                content = (?P<body>[^\],]+)
            \]
        ''', context.raw_message, re.VERBOSE)
        """

    def share_filter(context) -> bool:
        'Convert QQ share cards to plain messages.'
        match = re.fullmatch(
            r'\[CQ:json,data=(?P<body>\{[^\]]+\})\]',
            context.raw_message)
        if not match:
            return True

        try:
            body = json.loads(unescape(match.group('body')))['meta']
        except:
            pprof(time.time(), 'share', 'fail', match.group('body'))
            return True

        for card_type, card_conf in limit.card_types.items():
            if card_type not in body:
                continue
            card = body[card_type]

            for site, suffix in limit.get('url_trim', {}).items():
                url = card[card_conf['url']]
                if '://%s/' % site in url:
                    card[card_conf['url']] = url.partition(suffix)[0]
            if card.get('desc') == card.get('title'):
                card.pop('desc', None)

            reply = api.format(card_conf['fmt'], **card)
            bot.send(context, reply)
            return

        return True

    def greeting_filter(context) -> bool:
        'Get the corresponding greeting messages for preset keywords.'
        for keyword, response in limit.greetings.items():
            if re.search(keyword, context.raw_message):
                break
        else:  # nothing recognized
            if context.identifiers:
                return True
            elif not (context.abuse_filter() and context.wiki_filter()):
                return False  # found in wiki sites
            response = limit.greetings['^$']

        if isinstance(response, str):
            response = [response]
        if context.sender.user_id in limit.black_list and len(response) >= 3:
            reply = 2
        elif context.sender.title and len(response) >= 2:
            reply = 1
        else:
            reply = 0
        reply = random.choice(response[reply].split('|'))
        if reply:
            bot.send(context, reply.format(context.sender.title))

    def abuse_filter(context) -> bool:
        'Ignore the stop words and reject the bad words.'
        if re.search(limit.stop_words, context.message):
            return
        for pattern in [limit.self, r'^\W+', r'\s+$']:
            context.message = re.sub(pattern, '', context.message)

        if context.sender.user_id in limit.administrators:
            return True
        elif (
            len(context.identifiers) > limit.max_queries or
            re.search(limit.bad_words, context.message) or
            any(re.search(limit.bad_words, i) for i in context.identifiers)
        ):
            reply = '哼，不许捣乱！'
            bot.set_group_ban(duration=300, **context)
        elif context.sender.user_id in limit.black_list:
            reply = '哼，坏蛋，不理你了！'
        elif context.group_id in limit.disabled_groups:
            reply = '下班了，明天见~'
        else:
            return True
        bot.send(context, reply)

    def speed_filter(context) -> bool:
        'Limit the time-consuming requests.'
        roger_required = any(
            CAR_OR_CONTAINER_PATTERN.fullmatch(i)
            for i in context.identifiers
        )
        throttle_required = roger_required or any(
            count or i.startswith('PQ')
            for count, i in enumerate(context.identifiers)
        )
        if not throttle_required:
            return True
        elif context.sender.user_id not in limit.administrators and limit():
            bot.send(context, '哼，不理你了！')
            return
        elif not roger_required:
            return True
        elif context.sender.title:
            reply = '好的，%s' % context.sender.title
        else:
            reply = '好的，%s/%s，收到/嗯，%s/%s，明白/%s，知道了'
            reply = random.choice(reply.split('/'))
            reply %= ' '.join(context.identifiers.values())
        bot.send(context, reply)
        return True

    def qr_scan_filter(context: AttrDict) -> bool:
        img_file = re.compile(r'(?<=\[CQ:image,file=)[0-9A-Fa-f]{32}\.\w+(?=.+\])')
        match = img_file.search(context.raw_message)
        if not match:
            return True

        try:
            img = bot.get_image(file=match.group(0), **context)
            # if img['size'] > 10485760:
            #     return True

            # img_conf = configparser.ConfigParser()
            # img_conf.read('../../data/image/%s.cqimg' % match.group(0))
            # img_resp = requests.get(img_conf['image']['url']).content
            img_resp = requests.get(img['url']).content

            # with PIL.Image.open(img['file']) as img:
            with PIL.Image.open(io.BytesIO(img_resp)) as img:
                img = img.convert('L')

        except Exception as e:
            logging.error(e, exc_info=True, stack_info=True)
            return True

        for threshold in range(220, 20, -10):
            scan_result = scanner.scan_pil_image(img.point(
                lambda x: 0 if x < threshold else 0xFF
            ).convert('1'))
            if scan_result:
                reply = '\n-> '.join(s.decode() for s in scan_result)
                bot.send(context, '-> ' + url)
                return False

        return True

    def model_filter(context, i: str) -> bool:
        'Introduce the rolling stock.'
        if i not in trainnets:
            return True
        url, reply = trainnets[i]
        if ':' == url:
            pass
        elif ':' in url:
            reply += '详见 %s。' % url
        else:
            reply += '详见 https://trainnets.com/archives/%s。' % url
        if i in known_models:
            serial = known_models[i]
            reply += '如果你想追踪它的话，可以用 %s 这个车号。' % serial
        bot.send(context, strip_lines(reply))
        return context.train_filter(i) and False

    def train_filter(context, i: str) -> bool:
        'Gather and integrate train information from multiple sources.'
        i = context.identifiers[i]
        try:
            current_info = wifi.info_by_train_code(i)
        except:
            current_info = None
        model = get_train_model(i)
        freight_train = normalize_freight_train_number(i)
        category_description = get_train_category(freight_train or i).strip()

        if current_info:
            current_info.train = category_description % current_info.train_code
            reply = '''
                {train}，从{start_station[stationName]}站始发，
                终到{end_station[stationName]}站。
                列车全程运行 {distance} km，
                运行时间 {time_span[0]} 小时 {time_span[1]} 分钟。
            '''
            reply = strip_lines(reply).format_map(current_info)
        elif i in trains:
            reply = category_description + '，从%s站始发，终到%s站。'
            reply %= trains[trains[i]]
        elif freight_train in cr_express:
            reply = get_cr_express(freight_train)
        elif freight_train in known_traces or model:
            reply = '嗯，{}？'.format(category_description % i)
        else:
            return True
        if model:
            reply += model
        if freight_train in known_traces:
            reply += get_train_trace(freight_train)
        bot.send(context, reply)

    def tracking_filter(context, i)-> bool:
        'Solve the CAPTCHA to track freight cars or containers.'
        if i in known_models:
            reply = '''
                {} 的车号应该是 {}，我帮你查一下。
            '''.strip().format(i, known_models[i])
            bot.send(context, reply)
            i = known_models[i]
        if not CAR_OR_CONTAINER_PATTERN.fullmatch(i):
            return True
        elif i.isdigit():
            reply = tracking_handler(crsc.track_car, i)
            if reply:
                bot.send(context, reply)
                return
            else:
                method = api.track_car
        else:
            method = api.track_container
        try:
            if 'captcha_solved' not in context:
                api.fill_captcha(solve_captcha(api.load_captcha()))
        except:
            result = None
        else:
            context.captcha_solved = True
            result = tracking_handler(method, i)
        reply = {
            '没有满足条件的查询结果！': '找不到 {} 呢。',
            '货车追踪失败，请稍后再试！': '噫，{}？不告诉你哦~',
            '验证码错误': '咦，{} 怎么没查出来，等会儿再试试？',
            None: '{} 没查出来，再试一次吧（',
            0: '找不到 {} 呢。',
        }.get(result, result).format(i)
        bot.send(context, reply)

    def wildcard_model_filter(context, i: str) -> bool:
        'Match incomplete model names.'
        keys = set(chain(known_models, trainnets))
        if not i.isdigit():
            matches = get_close_matches(i, keys)
            keys -= set(matches)
        else:
            matches = []
        matches += sorted(
            model for model in keys
            if (i in model or model in i) and len(model) > 1
        )
        if not matches:
            return True
        reply = '%s… 你是指 %s 之类的吗？'
        reply %= (context.identifiers[i], '、'.join(matches[:6]))
        bot.send(context, reply)

    def wildcard_train_filter(context, i: str) -> bool:
        'Return the category of a train number as fallback.'
        i = context.identifiers[i]
        freight_train = normalize_freight_train_number(i)
        category_description = get_train_category(freight_train or i).strip()
        if len(category_description) > 6:  # if any categories found
            category_description %= i
            reply = '嗯，%s？我记不清了呢（' % category_description
        elif i.isdigit() and len(i) == 6:
            reply = '客车不能追踪呢。'
            reply += '如果您要查询按货车办理的六位编号特种车辆，请在前面补零。'
        else:
            return True
        bot.send(context, reply)

    def wiki_filter(context, i=None) -> bool:
        'Return the first article found in a bunch of wiki sites.'
        titles = context.identifiers[i] if i else context.message
        if not titles:
            return True
        elif titles.endswith('线'):
            titles += '|%s铁路' % titles[:-1]

        with ThreadPoolExecutor() as executor:
            all_results = executor.map(
                lambda site: (site, wiki_extract(site, titles=titles)),
                limit.wiki_sites
            )
        valid_results = (
            (site, AttrDict(page))
            for site, pages in all_results
            for page in pages
            if 'extract' in page
        )
        for site, page in valid_results:
            # based on code from OpenSearchXml by Brion Vibber
            sentence_boundaries = r'[.!?](?:[ \n]|$)|[。．！？｡]'
            # use the first five lines as text extract if no sentences found
            if not re.search(sentence_boundaries, page.extract):
                page = AttrDict(next(wiki_extract(
                    site, pageids=page.pageid, exintro=None, exsentences=None
                )))
                non_empty_lines = filter(None, page.extract.splitlines())
                page.extract = '\n'.join(islice(non_empty_lines, 5))
            page.extract = re.sub(r'\{\\displaystyle.+\}|(\n +)+', ' ', page.extract)
            thumbnail_url = page.get('thumbnail', {}).get('source')
            if thumbnail_url:
                page.extract += '[CQ:image,file=%s]' % thumbnail_url
            bot.send(context, page.extract)
            return
        return titles

    def flight_filter(context, i) -> bool:
        'Get flight information from FlightAware.'
        if not re.fullmatch(r'[A-Z\d]+[A-Z][A-Z\d]+', i):
            return True
        if 'flight_aware_auth' not in limit:
            return True

        resp = requests.get(
            url='http://flightxml.flightaware.com/json/FlightXML3/FlightInfoStatus',
            params=dict(ident=i, howMany=1),
            auth=limit.flight_aware_auth,
        )
        flights = resp.json().get('FlightInfoStatusResult', {}).get('flights')
        if not flights:
            return True
        info = flights[0]

        owner = html.unescape(requests.get(
            url='http://flightxml.flightaware.com/json/FlightXML3/TailOwner',
            params=dict(ident=i),
            auth=limit.flight_aware_auth,
        ).json().get('TailOwnerResult', {}).get('owner'))
        if owner and owner != 'Unknown Owner':
            info['tail_owner'] = owner.replace('""', '')

        for airport in 'origin', 'destination':
            a = info.get(airport)
            if not a:
                continue
            a['name'] = airports.get(a['alternate_ident'], ' ' + a['airport_name'])
            explain = '{name}（{alternate_ident}，{code}）{terminal[T{} 航站楼]}'
            info[airport] = api.format(explain, **a)

        for schedule in [
            'filed_departure_time',
            'actual_departure_time',
            'filed_arrival_time',
            'actual_arrival_time',
        ]:
            time_info = AttrDict(info.get(schedule, {}))
            if not time_info:
                continue
            timestamp = time_info.get('epoch')
            if not timestamp:
                del info[schedule]
                continue

            local_time = datetime.datetime.fromtimestamp(timestamp).isoformat()
            info[schedule] = local_time.replace('T', ' ') + ' ' + time_info.tz

        filed_ete = info.get('filed_ete')
        if filed_ete:
            info['filed_ete'] = '%02d:%02d' % divmod(filed_ete // 60, 60)

        reply = '''
            {airline_name[{}航空公司 ]}
            {flightnumber[{airline_iata} {} ]}航班，
            由{origin}出发，飞往{destination}。
            航班由{tail_owner[ {} 所属]}
            {full_aircrafttype[ {} 型]}飞机{tailnumber[ {} ]}执飞
            {filed_departure_time[；预定于 {} 起飞]}
            {filed_arrival_time[，{} 降落]}
            {filed_ete[，飞行时间 {}]}
            {filed_airspeed_kts[，航速 {} 节]}
            {filed_altitude[，高度 {} 英尺]}
            {actual_departure_time[；实际于 {} 起飞]}
            {actual_arrival_time[，{} 降落]}。
            {route[航路 {}。]}
        '''
        bot.send(context, api.format(strip_lines(reply), **info))

    def shanghai_filter(context, i) -> bool:
        'Track the electric multiple units operated by CR Shanghai.'
        reply = '''
            您查询的 {sku} 号二维码位于{modelTypeName}{modelType} {cdh} 动车
            组 {coachNo} {coachTypeName[号{}]}车 {seatRowNo} 排 {seatName} 席位。
            {train[该车组正在担当{}列车。]}
        '''
        if i in known_models:
            i = known_models[i]
        if not re.fullmatch(r'PQ\d{7}', i):
            return True

        url = 'https://g.xiuxiu365.cn/railway_api/web/index/train'
        try:
            info = requests.get(url, dict(pqCode=i), verify=False).json()
            assert info['code'] == 200
            info = AttrDict(info['data'])
        except AssertionError:
            reply = '找不到这个二维码诶。'
        except:
            reply = '咦，{} 怎么没查出来，等会儿再试试？'.format(i)
        else:
            k = info.cdh.replace('-', '')
            if k and k not in known_models:
                known_models[k] = i
            if info.trainName:
                trainNo = re.match(r'[A-Z][0-9]+', info.trainName)
                if trainNo:
                    trainNo = trainNo.group(0)
                if trainNo and trainNo in trains:
                    info.train = '由{1}站开往{2}站的 {0} 次'.format(*trains[trains[trainNo]])
                elif info.trainName:
                    info.train = ' {0} 次'.format(info.trainName)
            reply = api.format(strip_lines(reply), i, **info)
        finally:
            bot.send(context, reply)

    def beijing_filter(context, i) -> bool:
        'Track the electric multiple units operated by CR Beijing.'
        reply = '''
            您查询的 {QrCode} 号二维码位于 {TrainId} 号动车
            组 {CarriageNo} 车 {Seatorder} 排 {SeatNo} 席位。
            {TrainnoDate[截至 {} 为止，]}
            {train[该车正在担当{}列车]}。
        '''
        if i in known_models:
            i = known_models[i]
        if not re.fullmatch(r'\d{8}', i):
            return True

        from hashlib import md5
        url = 'https://aymaoto.jtlf.cn/webapi/otoshopping/ewh_getqrcodetrainnoinfo'
        signature = 'qrcode=%s&key=ltRsjkiM8IRbC80Ni1jzU5jiO6pJvbKd' % i
        data = dict(qrCode=i, sign=md5(signature.encode()).hexdigest())
        info = AttrDict(requests.post(url, data).json())
        if info.State == 400:
            reply = '找不到这个二维码诶。'
        else:
            info = AttrDict(info['data']['TrainInfo'])

            t = info.TrainId.replace('-', '')
            if t not in known_models or i.endswith('000'):
                known_models[t] = i

            if info.TrainnoId in trains:
                info.train = '由{1}站开往{2}站的 {0} 次'.format(*trains[trains[info.TrainnoId]])
            elif info.TrainnoId:
                info.train = ' {0} 次'.format(info.TrainnoId)
            reply = api.format(strip_lines(reply), **info)
        bot.send(context, reply)

    def winsky_filter(context, i) -> bool:
        'Return the first matching item from the aircraft database.'
        reply = '''
            {注册号} 的机型为 {机型}，{串号[串号为 {}，]}
            {发动机型号[采用 {} 发动机。该飞机]}
            {隶属[隶属于{}，]}{首次交付[于{}首次交付，]}
            {引进日期[于{}引入]}{运营机构[{}运营，]}
            {状态[目前状态为{}。]}{备注[{}。]}
        '''
        i = context.identifiers[i]
        if not i.startswith('B-'):
            return True
        for aircraft in winsky_handler(i):
            if aircraft['注册号'] != i:
                continue
            # convert the date to Chinese format
            for key in ['首次交付', '引进日期']:
                if '-' in aircraft[key]:
                    fields = zip(aircraft[key].split('-'), '年月日')
                    aircraft[key] = ''.join(chain.from_iterable(fields))
            # remove possible duplicates
            if aircraft['状态'] in aircraft['备注']:
                aircraft.pop('状态')
            reply = api.format(reply.strip(), **aircraft)
            bot.send(context, strip_lines(reply))
            context.flight_filter(i)
            return

        return True


def wiki_extract(site: mwclient.Site, **kwargs) -> Iterable[Dict]:
    'Get plain-text extracts of the given wiki articles.'
    if not site.writing_script_pattern.search(kwargs.get('titles', '')):
        return

    params = AttrDict(
        action='query',
        prop='extracts|pageimages',
        piprop='thumbnail',
        pithumbsize=800,
        uselang='zh-cn',
        converttitles=True,
        redirects=True,
        explaintext=True,
        exintro=True,
        exsentences=2,
    )
    params.update(kwargs)
    yield from site.api(**params)[params.action]['pages'].values()


def winsky_handler(registration: str) -> Iterable[AttrDict]:
    'Identify a civil aircraft by its registration number.'
    url = 'http://winskywebapp.vipsinaapp.com/winsky/index.php'
    url += '/home/PlaneInfo/getById?parameter=' + registration
    page = requests.get(url).text.replace(',', '，')
    matches = re.findall(r'<td><b>([^<]+)</b></td>\s+<td>([^<]*)</td>', page)
    for i in range(0, len(matches), 10):
        yield AttrDict(matches[i:i + 10])


def tracking_handler(method: Callable, number: str) -> str:
    'Track rail freight operations, and save the results for later use.'
    try:
        info = AttrDict(method(number))
        assert info, 0
        info.update(carNo=number, trainId=info.get('trainId', ''))
    except (AssertionError, KeyError) as e:
        return e.args[0]
    except json.decoder.JSONDecodeError as e:
        logging.error(e, exc_info=True, stack_info=True)
    else:
        known_models[info.carType.strip()] = info.carNo
        freight_train = normalize_freight_train_number(info.trainId)
        known_traces[freight_train or info.trainId.strip()] = info.copy()
        if freight_train:
            category_description = get_train_category(freight_train)
            info.train = category_description % info.pop('trainId').strip()
        return api.explain(info)


class Limit(AttrDict):
    'Limit the request rate.'

    def __init__(self, rate=1.5, per=60):
        allowance = rate  # unit: messages
        last_check = time.monotonic()
        self.update(locals())

    def __call__(self) -> bool:
        now = time.monotonic()
        self.allowance += (now - self.last_check) / self.per * self.rate
        self.last_check = now
        if self.allowance > self.rate:
            self.allowance = self.rate  # throttle
        if self.allowance < 1:
            return True
        else:
            self.allowance -= 1
            return False


class TrainRange:

    TRAIN_NO_PATTERN = re.compile(r'([A-Z]*|00)([0-9]+)')

    def __init__(self, first: str, last: str):
        'Parse the range representation.'
        assert first and last
        self.prefix, first = self.split(first)
        ignored_prefix, last = self.split(last)
        self.range = range(first, last + 1)

    def __repr__(self):
        'Provide a text representation for reproducibility.'
        repr_str = "{0.__class__.__name__}('{0.prefix}{1}', '{0.prefix}{2}')"
        return repr_str.format(self, self.range.start, self.range.stop - 1)

    def __contains__(self, train: str) -> bool:
        'Check whether a train number is in the specified range.'
        try:
            prefix, number = self.split(train)
        except:
            return False
        else:
            return prefix == self.prefix and number in self.range

    def split(self, train: str) -> Tuple[str, int]:
        'Split the train number into the prefix part and the numeric part.'
        match = self.TRAIN_NO_PATTERN.fullmatch(train)
        return match.group(1), int(match.group(2))


def normalize_freight_train_number(train: str) -> str:
    'Try to remove prefixes and suffixes to comprehend the train number.'
    match = re.search(r'(?<!\d)[1-9]\d{4,}|^X\d{3,4}(?!\d)', train)
    if match:
        return match.group(0)


def get_train_category(train: str) -> str:
    'Infer the category of a train number from its range.'
    results = [' %s 次']
    for tr in train_ranges:
        if train not in tr:
            continue
        elif tr.category.startswith('@'):
            results.insert(0, tr.category[1:])
        else:
            results.append(tr.category)
    if len(results) == 1:
        results.append('列车')
    return ''.join(results)


def get_cr_express(train: str) -> str:
    'Return the introduction to CR Express freight trains.'
    reply = '''
        {2} 次{1}班列，由{5}站始发，终到{6}站
        {10[，经由{}]}。列车{12[速度标尺为{}，]}
        {4[装车站为{}，]}{7[卸车站为{}；]}编组为{9}。
        {13[{}。]}
    '''
    return api.format(strip_lines(reply), *cr_express[train])


def get_train_model(train: str) -> str:
    'Return the rolling stock model used for a train.'
    if train in emu_models:
        reply = '''
            列车使用的动车组型号是{}
            交路信息详见 https://moerail.ml/#{}。
        '''
        return strip_lines(reply).format(emu_models[train], train)
    for model, pattern in emu_patterns.items():
        if re.match(pattern, train):
            reply = '列车使用的动车组型号是{}。'
            return reply.format(model)


def get_train_trace(train: str) -> str:
    'Return the last known location of a train.'
    reply = '''
        我在{eventAdm}的{eventStation}站见过呢，
        机后第 {trainOrder} 位拉着编号 {carNo} 的 {carType}。
    '''
    return api.format(strip_lines(reply), **known_traces[train])


def parse_train_ranges(lines: Iterable[str]) -> Iterable[TrainRange]:
    'Parse the range rules of train number categories.'
    for line in lines:
        category, *range_pairs = line.strip().split()
        for pair in range_pairs:
            tr = TrainRange(*pair.split('-'))
            tr.category = category
            yield tr


def parse_trainnets(lines: Iterable[str]) -> Dict[str, Tuple[str, str]]:
    'Extract keywords from the trainnets database.'
    trainnets = {}
    for line in lines:
        url, _, intro = line.strip().partition(' ')
        identifiers = [i for i in match_identifiers(intro) if not i.isdigit()]
        if identifiers:
            for extra, i in enumerate(identifiers):
                if i not in trainnets:
                    trainnets[i] = (url, intro)
                elif not extra:
                    print(i, intro[:30])
        else:
            print('?', intro[:30])
    return trainnets


def load_database(name: str, path: str, handler=json.load, default=None):
    'Load the database into module namespace.'
    try:
        with open(path) as f:
            results = handler(f)
    except FileNotFoundError:
        results = default or {}
    finally:
        globals()[name] = results


def initialize(config_file: str):
    'Load all the databases.'
    global limit
    limit = Limit()
    with open(config_file) as f:
        limit.update(json.load(f))
    limit.titles = {v: k for k, v in limit.get('titles', {}).items()}
    for key in ['administrators', 'black_list', 'disabled_groups']:
        limit[key] = set(limit.get(key, []))
    if 'flight_aware_auth' in limit:
        limit.flight_aware_auth = \
            requests.auth.HTTPBasicAuth(**limit.flight_aware_auth)

    wiki_sites = []
    for host, pattern in limit.get('wiki_sites', {}).items():
        site = mwclient.Site(host, do_init=False)
        site.writing_script_pattern = re.compile(pattern)
        wiki_sites.append(site)
    limit.wiki_sites = wiki_sites

    databases = {
        'airports': ['airports_json'],
        'known_models': ['serial_json'],
        'known_traces': ['traces_json'],
        'emu_patterns': ['emu_json', lambda f: json.load(f)[':']],
        'emu_models': [
            'emu_text',
            lambda f: {
                train_number: emu_model
                for line in f.read().splitlines()
                for train_number, _, emu_model in [line.partition(' ')]
            },
        ],
        'trainnets': [
            'trainnets_text',
            lambda f: parse_trainnets(f.read().splitlines()),
        ],
        'train_ranges': [
            'trains_text',
            lambda f: list(parse_train_ranges(f.read().splitlines())),
            [],
        ],
        'trains': [
            'trains_json',
            lambda f: sort_trains(parse_trains(load_trains(f.read()))),
        ],
        'cr_express': [
            'express_json',
            lambda f: {
                train_number: record
                for record in json.load(f)
                for train_number in record[2].split('/')
            },
        ],
    }
    for name, (filename, *params) in databases.items():
        if filename in limit:
            filename = limit[filename]
        else:
            limit[filename] = filename
        load_database(name, filename, *params)

    scanner_conf = [
        (zbar.SymbolType.NONE, zbar.Config.ENABLE, 0),
        (zbar.SymbolType.QRCODE, zbar.Config.ENABLE, 1),
        (zbar.SymbolType.QRCODE, zbar.Config.X_DENSITY, 1),
        (zbar.SymbolType.QRCODE, zbar.Config.Y_DENSITY, 1),
    ]
    for conf in scanner_conf:
        scanner.set_config(*conf)


if __name__ == '__main__':
    initialize(argv(1) or 'bot_config.json')
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    warnings.filterwarnings('once')
    try:
        bot.run()
    finally:
        print('Committing changes...')
        with open(limit.serial_json, 'w') as f:
            json.dump(known_models, f)
        with open(limit.traces_json, 'w') as f:
            json.dump(known_traces, f)
        print('Goodbye.')
