#!/usr/bin/env python3

import io
import json
import mwclient
import random
import re
import sys
import time
from contextlib import redirect_stdout, redirect_stderr
from itertools import chain, islice
from subprocess import run, PIPE
from string import ascii_uppercase
from typing import Dict, Iterable, Tuple
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
    context.raw_message = context.message
    context.message = unescape(context.message).strip()
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
    if context.message_type == 'private' and not parse_loopback(context):
        return
    if context.user_id in limit.administrators:
        return parse_shell(context) or RailwayContext(context)()
    elif context.get('group_id') in limit.railway_groups:
        return RailwayContext(context)()


def parse_loopback(context) -> bool:
    '''语法：@群名 要发送的消息

    可以将群名的任何一部分作为群名缩写。
    缩写长度不限，只要不与机器人已加入的其他群的名称相混淆即可。
    '''
    if not context.raw_message.startswith('@'):
        return True
    elif context.user_id in limit.black_list:
        bot.send(context, '哼，坏蛋，不理你了！')
        return

    factors = context.raw_message[1:].partition(' ')
    if not all(factors):
        reply = parse_loopback.__doc__.strip()
        bot.send(context, strip_lines(reply, '\n'))
        return

    group_key, delimit, text = factors
    matches = [
        group for group in bot.get_group_list()
        if group_key in group['group_name']
    ]
    if len(matches) == 1:
        bot.send_group_msg(group_id=matches[0]['group_id'], message=text)
    else:
        reply = '「%s」指的是哪个群呢？' % group_key
        reply += '\n' + '\n'.join(
            '{group_name}（{group_id}）'.format(**group)
            for group in matches
        ) if matches else ''
        bot.send(context, reply)


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
    pattern = r'(?a)(?<!\w)([A-Z][-\w]+|\d{4,7}|\w+[A-Z])(?!\w)'
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
        self.mentioned = re.findall(limit.self, context.raw_message)
        self.identifiers = match_identifiers(context.message)

    def __call__(context) -> bool:
        'Response the query.'
        unknown_items = (
            any((
                context.notified,
                context.mentioned,
                context.message_type == 'private'
            )) and
            context.greeting_filter() and
            context.abuse_filter() and
            [
                context.model_filter(i) and
                context.train_filter(i) and
                context.tracking_filter(i) and
                context.wiki_filter(i) and
                context.wildcard_filter(i)
                for i in context.identifiers
            ]
        )
        if not unknown_items:
            return
        elif all(unknown_items):
            unknown_items = [context.wiki_filter()]
        else:
            pairs = zip(unknown_items, context.identifiers.values())
            unknown_items = [i for unknown, i in pairs if unknown]
        if any(unknown_items):
            reply = '%s 是什么哦，没见过呢'
            reply %= '、'.join(unknown_items)
            bot.send(context, reply)

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
        if context.user_id in limit.black_list and len(response) >= 3:
            reply = 2
        elif context.title and len(response) >= 2:
            reply = 1
        else:
            reply = 0
        reply = random.choice(response[reply].split('|'))
        if reply:
            bot.send(context, reply.format(context.title))

    def abuse_filter(context) -> bool:
        'Throttle the number of messages and remove the stop words.'
        if re.search(limit.stop_words, context.message):
            return
        elif limit.power_off and context.user_id not in limit.administrators:
            bot.send(context, '下班了，明天见~')
            return

        roger = False
        original, context.identifiers = context.identifiers, AttrDict()
        for count, (k, v) in enumerate(original.items()):
            if context.user_id in limit.administrators:
                pass
            elif re.search(limit.bad_words, k) or count >= limit.max_queries:
                bot.send(context, '哼，不许捣乱！')
                return
            context.identifiers[k] = v
            if k.isdigit() and len(k) == 7 or count > 1:
                roger = True

        if roger:
            if context.user_id in limit.black_list:
                bot.send(context, '哼，坏蛋，不告诉你！')
                return
            elif context.user_id not in limit.administrators and limit():
                bot.send(context, '哼，不理你了!')
                return
            elif context.title:
                reply = '好的，%s' % context.title
            else:
                reply = '好的，%s/%s，收到/嗯，%s/%s，明白/%s，知道了'
                reply = random.choice(reply.split('/'))
                reply %= '、'.join(context.identifiers)
            bot.send(context, reply)
        return True

    def model_filter(context, i: str) -> bool:
        'Return the introduction of railway cars.'
        if i.isdigit() and len(i) == 6:
            reply = '''
                客车目前不能追踪呢，你可以
                去 http://passearch.info/?type=number&keyword={0} 看看
                有没有车迷记录 {0} 的配属状况。
            '''.strip().format(i)
        elif i in trainnets:
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
        elif i in emu_models:
            reply, foreword = context.get_train_route(i)
            reply += '''
                {2}使用的动车组型号是{1}
                交路信息详见 https://moerail.ml/#{0}。
            '''.strip().format(i, emu_models[i], foreword)
        elif i in cr_express:
            reply = '''
                {2} 次{1}班列，由{5}站始发，终到{6}站
                {10[，经由{}]}。列车{12[速度标尺为{}，]}
                {4[装车站为{}，]}{7[卸车站为{}；]}编组为{9}。
                {13[{}。]}
            '''
            reply = api.format(reply.strip(), *cr_express[i])
        else:
            return True
        bot.send(context, strip_lines(reply))

    def train_filter(context, i: str) -> bool:
        'Infer the models of other multiple units.'
        reply, foreword = context.get_train_route(i)
        for model, pattern in emu_patterns.items():
            if re.match(pattern, i):
                reply += '''
                    {2}使用的动车组型号是{1}。
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

    def tracking_filter(context, i)-> bool:
        'Provide railway shipment tracking service.'
        if i in known_models:
            reply = '''
                {} 的车号应该是 {}，我帮你查一下。
            '''.strip().format(i, known_models[i])
            bot.send(context, reply)
            i = known_models[i]
        if not i.isdigit() or len(i) != 7:
            return True
        elif 'captcha' not in context:
            api.query['check_code'] = solve_captcha(api.load_captcha())
            context.captcha = True
        result = tracking_handler(i)
        reply = {
            '没有满足条件的查询结果！': '找不到 {} 呢。',
            '货车追踪失败，请稍后再试！': '噫，{}？不告诉你哦~',
            '验证码错误': '咦，{} 怎么没查出来，等会儿再试试？',
            None: '{} 没查出来，再试一次吧（',
        }.get(result, result).format(i)
        bot.send(context, reply)

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
            reply = '嗯，{}？'.format(description % i)
            train_number = re.sub(r'\D', '', i)
            if train_number in known_traces:
                trace = '''
                    我在{eventAdm}的{eventStation}站见过呢，
                    机后第 {trainOrder} 位拉着编号 {carNo} 的 {carType}。
                '''.strip().format_map(known_traces[train_number])
                reply += strip_lines(trace)
            else:
                reply += '我记不清了呢（'
        else:
            return True
        bot.send(context, reply)

    def wiki_filter(context, i=None) -> bool:
        'Return the first article found in a bunch of wiki sites.'
        if i:
            titles = context.identifiers[i]
        else:
            titles = context.message
            for stop_words in [limit.stop_words, limit.self, r'^\W+']:
                titles = re.sub(stop_words, '', titles)
        if not titles:
            return True
        for site in wiki_sites:
            page = AttrDict(next(wiki_extract(site, titles)))
            if 'missing' in page:
                continue
            # based on code from OpenSearchXml by Brion Vibber
            sentence_boundaries = r'[.!?](?:[ \n]|$)|[。．！？｡]'
            # use the first five lines as text extract if no sentences found
            if not re.search(sentence_boundaries, page.extract):
                page = AttrDict(next(wiki_extract(
                    site, titles, exintro=None, exsentences=None
                )))
                non_empty_lines = filter(None, page.extract.splitlines())
                page.extract = '\n'.join(islice(non_empty_lines, 5))
            bot.send(context, page.extract)
            return
        return titles


def wiki_extract(site: mwclient.Site, titles: str, **kwargs) -> Iterable[Dict]:
    'Get plain-text extracts of the given wiki articles.'
    params = AttrDict(
        action='query',
        prop='extracts',
        uselang='zh-cn',
        titles=titles,
        converttitles=True,
        redirects=True,
        explaintext=True,
        exintro=True,
        exsentences=2,
    )
    params.update(kwargs)
    yield from site.api(**params)[params.action]['pages'].values()


def tracking_handler(car: str) -> str:
    'Response railway shipment queries.'
    try:
        info = api.track_car(car)
    except AssertionError as e:
        return e.args[0]
    except json.decoder.JSONDecodeError as e:
        print(e.doc)
    else:
        if info.carType:
            known_models[info.carType] = info.carNo
        if not info.trainId.isdigit() or int(info.trainId) > 10000:
            if info.trainOrder and info.eventAdm:
                known_traces[re.sub(r'\D', '', info.trainId)] = info.copy()
            info.train = get_train_description(info.trainId) % info.trainId
            info.pop('trainId')
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
        if not train.isdigit():
            train = re.sub(r'\D', '', train)
            if train and int(train) > 10000:
                return get_train_description(train)
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

    databases = {
        'known_models': [limit.serial_json],
        'known_traces': [limit.traces_json],
        'emu_patterns': [limit.emu_json, lambda f: json.load(f)[':']],
        'emu_models': [
            limit.emu_text,
            lambda f: {
                train_number: emu_model
                for line in f.read().splitlines()
                for train_number, _, emu_model in [line.partition(' ')]
            },
        ],
        'trainnets': [
            limit.trainnets_text,
            lambda f: parse_trainnets(f.read().splitlines()),
        ],
        'train_ranges': [
            limit.trains_text,
            lambda f: list(parse_train_ranges(f.read().splitlines())),
            [],
        ],
        'trains': [
            limit.trains_json,
            lambda f: sort_trains(parse_trains(load_trains(f.read()))),
        ],
        'cr_express': [
            limit.express_json,
            lambda f: {
                train_number: record
                for record in json.load(f)
                for train_number in record[2].split('/')
            },
        ],
    }
    globals()['wiki_sites'] = [
        mwclient.Site(site)
        for site in limit.wiki_sites
    ]
    for name, params in databases.items():
        load_database(name, *params)


if __name__ == '__main__':
    initialize(argv(1) or 'bot_config.json')
    try:
        bot.run(host='localhost', port=7700)
    except ValueError:  # closed stderr
        raise
    finally:
        print('Committing changes...')
        with open(limit.serial_json, 'w') as f:
            json.dump(known_models, f)
        with open(limit.traces_json, 'w') as f:
            json.dump(known_traces, f)
        print('Goodbye.')
