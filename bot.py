#!/usr/bin/env python3

import io
import json
import random
import re
import sys
import time
from contextlib import redirect_stdout, redirect_stderr
from itertools import chain
from subprocess import run, PIPE
from string import ascii_uppercase
from typing import Dict, Iterable, Sequence, Tuple
from cqhttp import CQHttp
from util import argv, open, AttrDict
from trains import load_trains, parse_trains, sort_trains
from tracking import solve_captcha, strip_lines, Tracking

bot = CQHttp('http://localhost:5700/')
api = Tracking()


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


@bot.on_event('group_increase')
def new_group_member(context):
    'Send the welcome message.'
    bot.send(context, '群地位-1')


@bot.on_event('group_upload')
def new_group_file(context):
    'Detect file uploads.'
    reply = (
        '怎么又双叒叕是 base.apk [CQ:face,id=39]'
        if context['file']['name'] == 'base.apk'
        else '诶，我看看传了什么'
    )
    bot.send(context, reply)


@bot.on_request('group', 'friend')
def new_friend(context):
    'Accepts friend requests from administrators.'
    if context['user_id'] in limit.administrators:
        return {'approve': True}
    for i in limit.administrators:
        bot.send_private_msg(user_id=i, message=context)


@bot.on_message()
def new_msg_wrapper(context):
    'Wraps the message event.'
    context = AttrDict(context)
    context.notified = '[CQ:at,qq=%d]' % context.self_id in context.message
    context.message = unescape(context.message)
    # print(dict(context))

    value = new_msg(context)
    if value is None:
        return
    elif isinstance(value, dict):
        return value
    else:
        return dict(reply=value, at_sender=False)


def new_msg(context):
    'The message event handler.'
    if context.user_id in limit.administrators:
        return parse_shell(context) or RailwayContext(context)()
    elif context.get('group_id') in limit.railway_groups:
        return RailwayContext(context)()


def parse_shell(context) -> str:
    'Provide Python and Bash shells.'
    if context.message.startswith('$'):
        proc = run(context.message[1:], shell=True, stdout=PIPE)
        return proc.stdout.decode(sys.getfilesystemencoding()).strip()

    elif context.message.startswith('>>>'):
        result = io.StringIO()
        with redirect_stdout(result), redirect_stderr(result):
            print('\n-->', eval(context.message[3:]))
        return result.getvalue().strip()

    elif context.message.startswith('//'):
        limit.power_off = not limit.power_off
        if limit.power_off:
            return '下班喽~'

    elif context.message_type == 'private':
        return dict(reply=context.raw_message, auto_escape=True)


def match_identifiers(text: str, remove='-') -> AttrDict:
    'Return all non-overlapping identifiers in the text, with hyphens removed.'
    pattern = r'(?a)(?<!\w)([A-Z][-\w]+|\d{4,5}|\w+[A-Z])(?!\w)'
    return AttrDict(
        (i.replace(remove, ''), i)
        for i in re.findall(pattern, text)
    )


class RailwayContext(AttrDict):

    def __init__(self, context):
        'Search the keywords in the received message.'
        self.update(
            bot.get_group_member_info(**context)
            if context.message_type == 'group'
            else dict(title='')
        )
        self.update(context)
        self.mentioned = re.findall(limit.self, context.message)
        self.numbers = re.findall(r'(?a)(?<!\d)\d{7}(?!\d)', context.message)
        self.identifiers = match_identifiers(context.message)
        self.unknown = []

    def __call__(context):
        'Response the query.'
        ignore_request = (
            not context.notified and
            not context.mentioned and
            context.message_type != 'private' or
            not context.greeting_filter() or
            not context.abuse_filter()
        )
        if ignore_request:
            return

        for i in context.identifiers:
            if context.model_filter(i) and context.train_filter(i):
                context.wildcard_filter(i)
        if context.numbers or context.unknown:
            if context.rate_filter():
                context.query_numbers()

    def rate_filter(context) -> bool:
        'Return error messages when the rate limit is exceeded.'
        if context.user_id in limit.administrators:
            return True
        elif limit.power_off:
            reply = '下班了，明天见~'
        elif context.user_id in limit.black_list:
            reply = '哼，坏蛋，不告诉你！'
        elif context.numbers and limit():
            reply = '哼，不理你了!'
        else:
            return True
        bot.send(context, reply)

    def greeting_filter(context) -> bool:
        'Get the corresponding greeting messages for preset keywords.'
        if '抱' in context.message:
            if context.user_id in limit.black_list:
                reply = '坏蛋，不让你抱，踩你哦（'
            elif context.title:
                reply = '抱抱%s~' % context.title
            else:
                reply = '抱w'
        elif '吃' in context.message:
            reply = '噫，不可以吃！'
        elif not context.numbers and not context.identifiers:
            if context.title:
                reply = '怎么啦，%s' % context.title
            else:
                reply = '诶，谁在叫我呢？'
        else:
            return True
        bot.send(context, reply)

    def abuse_filter(context) -> bool:
        'Prevent stop words and bad words.'
        context.numbers = [
            i for i in context.numbers
            if not re.search(limit.stop_words, i)
        ]
        if context.user_id in limit.administrators:
            return True
        for i in chain(context.numbers, context.identifiers):
            if re.search(limit.bad_words, i):
                bot.send(context, '哼，不许捣乱！')
                return False
        return True

    def model_filter(context, i: str) -> bool:
        'Return the introduction of railway cars.'
        if i in trainnets:
            reply = '''
                {0[1]}
                详见 https://trainnets.com/archives/{0[0]}。
                {1}
            '''.strip().format(
                trainnets[i],
                '\n如果你想追踪它的话，可以用 %s 这个车号。' % known_models[i]
                if i in known_models else ''
            )
            bot.send(context, strip_lines(reply))
        elif i in known_models:
            context.numbers.append(known_models[i])
        elif i in emu_models:
            reply, foreword = context.get_train_route(i)
            reply += '''
                {2}使用的动车组型号是{1}
                交路信息详见 https://moerail.ml/#{0}。
            '''.strip().format(i, emu_models[i], foreword)
            bot.send(context, strip_lines(reply, sep='\n'))
        else:
            return True

    def train_filter(context, i: str) -> bool:
        'Infer the models of other multiple units.'
        reply, foreword = context.get_train_route(i)
        for model, pattern in emu_patterns.items():
            if re.match(pattern, i):
                reply += '''
                    {2}使用的动车组型号应该是{1}。
                '''.strip().format(i, model, foreword)
                break
        else:
            if i not in trains:
                return True
        bot.send(context, reply)

    @staticmethod
    def get_train_route(i) -> Tuple[str, str]:
        'Provide information about passenger train routes.'
        description = get_train_description(i).strip()
        if i not in trains:
            return description % i, ''
        reply = description + '，从%s站始发，终到%s站。'
        return reply % trains[trains[i]], '列车'

    def wildcard_filter(context, i: str) -> bool:
        'Match incomplete model names.'
        prefix_matches = sorted(
            model for model in set(chain(known_models, trainnets))
            if (i in model or model in i) and len(model) > 1
        )
        description = get_train_description(i).strip()
        i = context.identifiers[i]
        if prefix_matches:
            reply = '''
                {0}… 你指的是 {1} 之类的吗？
            '''.strip().format(i, '、'.join(prefix_matches))
        elif len(description) > 6:
            reply = '''
                嗯，{}？我记不清了呢（
            '''.strip().format(description % i)
        else:
            context.unknown.append(i)
            return True
        bot.send(context, reply)

    def query_numbers(context):
        'Provide railway shipment tracking service.'
        if context.unknown:
            models = '、'.join(context.unknown)
            reply = '%s 是什么车哦，没见过呢' % models
        elif context.title:
            reply = '好的，%s' % context.title
        elif context.identifiers:
            reply = '好的，知道了'
        else:
            numbers = '、'.join(context.numbers)
            reply = random.choice(['好的，%s', '%s，收到']) % numbers
        bot.send(context, reply)

        for car, result in batch_tracking(context.numbers):
            reply = {
                '没有满足条件的查询结果！': '找不到 %s 呢。' % car,
                '货车追踪失败，请稍后再试！': '噫，%s？不告诉你哦~' % car,
            }.get(result, result)
            bot.send(context, reply)


def batch_tracking(cars: Sequence[str]) -> Iterable[Tuple[str, str]]:
    'Response railway shipment queries.'
    api.query['check_code'] = solve_captcha(api.load_captcha())
    for car in cars:
        try:
            info = api.track_car(car)
        except AssertionError as e:
            yield car, e.args[0]
        else:
            if info.carType:
                known_models[info.carType] = info.carNo
            if info.trainId:
                info.train = get_train_description(info.trainId) % info.trainId
                info.trainId = None
            yield car, api.explain(info)


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

    def __init__(self, first: str, last: str):
        'Parse the range representation.'
        assert first and last
        self.prefix, first = self.split(first)
        ignored_prefix, last = self.split(last)
        self.range = range(first, last + 1)

    def __contains__(self, train: str) -> bool:
        'Check whether a train number is in the specified range.'
        try:
            prefix, number = self.split(train)
        except:
            return False
        else:
            return prefix == self.prefix and number in self.range

    @staticmethod
    def split(train: str) -> Tuple[str, int]:
        'Split the train number into the prefix part and the numeric part.'
        assert train
        if train[0] in ascii_uppercase:
            return train[0], int(train[1:])
        else:
            return '', int(train)


def get_train_description(train: str) -> str:
    'Provide information about the train number itself.'
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


def parse_train_ranges(lines: Iterable[str]) -> Iterable[TrainRange]:
    'Parse the train number ranges to determine train categories.'
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
        identifiers = match_identifiers(intro)
        if identifiers:
            for extra, i in enumerate(identifiers):
                if i not in trainnets:
                    trainnets[i] = (url, intro)
                elif not extra:
                    print(i, intro[:30])
        else:
            print('?', intro[:30])
    return trainnets


def main(config_file: str):
    'Load the databases.'
    global limit
    limit = Limit()
    try:
        with open(config_file) as f:
            limit.update(json.load(f))
    except AssertionError:
        pass

    global known_models
    try:
        with open(limit.serial_json) as f:
            known_models = json.load(f)
    except:
        known_models = {}

    global emu_patterns
    try:
        with open(limit.emu_json) as f:
            emu_patterns = json.load(f)[':']
    except:
        emu_patterns = {}

    global emu_models
    emu_models = {}
    try:
        with open(limit.emu_text) as f:
            lines = f.read().splitlines()
    except:
        pass
    else:
        for line in lines:
            train, _, model = line.partition(' ')
            emu_models[train] = model

    global trainnets
    try:
        with open(limit.trainnets_text) as f:
            lines = f.read().splitlines()
    except:
        trainnets = {}
    else:
        trainnets = parse_trainnets(lines)

    global train_ranges
    try:
        with open(limit.trains_text) as f:
            lines = f.read().splitlines()
    except:
        train_ranges = []
    else:
        train_ranges = list(parse_train_ranges(lines))

    global trains
    try:
        with open(limit.trains_json) as f:
            print('Loading...')
            data = load_trains(f.read())
    except:
        trains = {}
    else:
        routes = parse_trains(data)
        print('Sorting...')
        trains = sort_trains(routes)
        print('Ready.')

    bot.run(host='localhost', port=7700)
    with open(limit.serial_json, 'w') as f:
        json.dump(known_models, f)


if __name__ == '__main__':
    main(argv(1) or 'bot_config.json')
