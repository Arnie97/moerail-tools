#!/usr/bin/env python3

from datetime import date
from itertools import chain
from operator import itemgetter
from os.path import commonprefix
from tickets import API
from typing import Any, Iterable, Dict, List, Optional, Tuple
from util import repl, AttrDict


class Wifi12306(API):
    'https://wifi.12306.cn/wifiapps/ticket/api/'

    def __init__(self):
        super().__init__()
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.20(0x18001428) NetType/4G Language/zh_CN',
        })

    def request(self, *args, json=True, **kwargs):
        resp = super().request(*args, json=json, **kwargs)
        if not json:
            return resp
        if resp.get('status', -1):
            raise APIError(resp.get('error'))
        return resp.get('data')

    @staticmethod
    def yyyymmdd_format(date: date) -> str:
        return date.isoformat().replace('-', '')

    @staticmethod
    def from_yyyymmdd_format(s: str) -> date:
        return date.fromisoformat('{0[:4]}-{0[4:6]}-{0[6:8]}'.format(s))

    def train_list_by_station_name(
        self,
        from_station_name: str,
        to_station_name: str,
        query_date: Optional[date]=None,
    ) -> List[Dict[str, Any]]:
        if not query_date:
            query_date = date.today()
        return self.get(
            'stoptime/queryByStationName',
            params=dict(
                trainDate=query_date.isoformat(),
                fromStationName=from_station_name,
                toStationName=to_station_name))

    def run_rule_by_train_no(
        self,
        train_no: str,
        start_date: Optional[date]=None,
        end_date: Optional[date]=None,
    ) -> Dict[date, bool]:
        if not start_date:
            start_date = date.today()
        if not end_date:
            end_date = date.fromordinal(start_date.toordinal() + 1)
        resp = self.get(
            'trainDetailInfo/queryTrainRunRuleByTrainNoAndDateRange',
            params=dict(
                start=self.yyyymmdd_format(start_date),
                end=self.yyyymmdd_format(end_date),
                trainNo=train_no))
        return {
            self.from_yyyymmdd_format(k): resp[k] == '1'
            for k in sorted(resp)
        }

    def stop_time_by_train_code(
        self,
        train_code: str,
        query_date: Optional[date]=None,
        big_screen: Optional[bool]=False,
    ) -> List[Dict[str, Any]]:
        if not query_date:
            query_date = date.today()
        return self.get(
            'stoptime/queryByTrainCode',
            params=dict(
                getBigScreen=['NO', 'YES'][big_screen],
                trainDate=self.yyyymmdd_format(query_date),
                trainCode=train_code))

    def pre_seq_train_by_train_code(
        self,
        train_code: str,
        query_date: Optional[date]=None,
    ) -> List[Dict[str, Any]]:
        if not query_date:
            query_date = date.today()
        return self.get(
            'preSequenceTrain/getPreSequenceTrainInfo',
            params=dict(
                trainDate=self.yyyymmdd_format(query_date),
                trainCode=train_code))

    def train_set_type_by_train_code(self, train_code: str) -> Dict[str, Any]:
        return self.get(
            'trainDetailInfo/getTrainsetTypeByTrainCode',
            params=dict(trainCode=train_code))

    def train_compile_list_by_train_no(self, train_no: str) -> List[Dict]:
        return self.get(
            'trainDetailInfo/queryTrainCompileListByTrainNo',
            params=dict(trainNo=train_no))

    def train_equipment_by_train_no(self, train_no: str) -> List[Dict]:
        return self.get(
            'trainDetailInfo/queryTrainEquipmentByTrainNo',
            params=dict(trainNo=train_no))

    @staticmethod
    def denormalize_multiple_train_code(train_codes: Iterable[str]) -> str:
        train_numbers = []
        for i, t in enumerate(train_codes):
            if i == 0:
                prefix = t
                last_train_number = t
                train_numbers.append(t)
            elif t != last_train_number:
                prefix = commonprefix([prefix, t])
                last_train_number = t
                train_numbers.append(t)
        return prefix + '/'.join(t[len(prefix):] for t in train_numbers)

    def info_by_train_code(self, train_code: str) -> Optional[Dict[str, Any]]:
        stations = self.stop_time_by_train_code(train_code)
        if not stations:
            return
        start_station, *_, end_station = stations
        train_code = self.denormalize_multiple_train_code(
            s['stationTrainCode'] for s in stations)
        train_no = start_station['trainNo']
        distance = end_station['distance']
        time_span = self.explain_time_span(end_station['timeSpan'])
        return AttrDict(locals())

    @staticmethod
    def explain_time_span(milliseconds: int) -> Tuple[int, int]:
        return divmod(milliseconds // 1000 // 60, 60)

    @classmethod
    def explain_stop_time(cls, stations: List[Dict[str, Any]]) -> str:
        for s in stations:
            s['hours'], s['minutes'] = cls.explain_time_span(s['timeSpan'])
        return '\n'.join(chain(
            ['\n'],
            ['车次 里程 用时 编号 到站 发车 电报码 站名', '－' * 21],
            (
                '{stationTrainCode:5} {distance:4} {hours:02}:{minutes:02}'
                ' {stationNo} {arriveTime} {startTime} '
                '-{stationTelecode} {stationName}'.format_map(s)
                for s in stations),
        ))

    @staticmethod
    def explain_pre_seq_train(pre_seq_train: List[Dict[str, Any]]) -> str:
        return '\n'.join(chain(
            ['\n'],
            ['车次  里程  发时  到时  发站  到站', '－' * 18],
            (
                '{trainCode:5} {distance:>4} '
                '{startTime} {endTime} {startStation} {endStation}'.format_map(s)
                for s in pre_seq_train),
        ))

    @staticmethod
    def explain_train_equipment(train_equipment: List[Dict[str, Any]]) -> str:
        depot = '{bureaName}局（{deploydepotName}）{depotName} '.format_map(
            train_equipment[0])
        vehicles = ' '.join(e['trainsetName'] for e in train_equipment)
        if len(train_equipment) > 1:
            vehicles += ' 重联'
        return depot + vehicles

    @staticmethod
    def explain_train_compile_list(train_compile_list: List[Dict]) -> str:
        return '\n'.join(chain(
            ['\n'],
            ['编号 车种 定员 附注', '－' * 10],
            ('{coachNo:4} {coachType:4.4} {limit1:3} {commentCode:>3}'.
                format_map(c) for c in sorted(
                    train_compile_list, key=itemgetter('coachNo'))),
        ))

    def repl_handler(self, train_code: str) -> str:
        try:
            info = self.info_by_train_code(train_code)
        except APIError as e:
            print(e)
            return '> '

        print(
            '{train_code}（{start_station[stationName]}-'
            '{end_station[stationName]}，{distance} km，'
            '{time_span[0]:02}:{time_span[1]:02}）'.format_map(info))

        train_equipment = self.train_equipment_by_train_no(info.train_no)
        if train_equipment:
            print(self.explain_train_equipment(train_equipment))
        else:
            train_set_type = self.train_set_type_by_train_code(info.train_no)
            if train_set_type:
                print('{trainsetType}{trainsetTypeName}'.format_map(
                    train_set_type))

        train_compile_list = self.train_compile_list_by_train_no(info.train_no)
        if train_compile_list:
            print(self.explain_train_compile_list(train_compile_list))

        print(self.explain_stop_time(info.stations))

        pre_seq_train = self.pre_seq_train_by_train_code(train_code)
        if pre_seq_train:
            print(self.explain_pre_seq_train(pre_seq_train))

        return '> '


class APIError(ValueError):
    pass


if __name__ == '__main__':
    repl(Wifi12306().repl_handler)
