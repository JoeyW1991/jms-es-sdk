# -*- coding: utf-8 -*-
#
import datetime

import pytz
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk


class ESStore:

    def __init__(self, hosts, index="jumpserver", doc_type="command_store", **kwargs):
        self.hosts = hosts
        self.index = index
        self.doc_type = doc_type
        self.es = Elasticsearch(hosts=self.hosts, **kwargs)

    @staticmethod
    def make_data(command):
        data = dict(
            user=command["user"], asset=command["asset"],
            system_user=command["system_user"], input=command["input"],
            output=command["output"], session=command["session"],
            timestamp=command["timestamp"]
        )
        data["date"] = datetime.datetime.fromtimestamp(command['timestamp'], tz=pytz.UTC)
        return data

    def bulk_save(self, command_set, raise_on_error=True):
        actions = []
        for command in command_set:
            data = dict(
                _index=self.index,
                _type=self.doc_type,
                _source=self.make_data(command),
            )
            actions.append(data)
        return bulk(self.es, actions, index=self.index, raise_on_error=raise_on_error)

    def save(self, command):
        """
        保存命令到数据库
        """
        data = self.make_data(command)
        return self.es.index(index=self.index, doc_type=self.doc_type,
                             body=data)

    def get_query_body(self, match=None, exact=None, date_from=None, date_to=None):
        if date_to is None:
            date_to = datetime.datetime.now()
        if date_from is None:
            date_from = date_to - datetime.timedelta(days=7)

        time_from = date_from.timestamp()
        time_to = date_to.timestamp()

        body = {
            "query": {
                "bool": {
                    "must": [],
                    "filter": [
                        {"range": {
                            "timestamp": {
                                "gte": time_from,
                                "lte": time_to,
                            }
                        }}
                    ]
                }
            },
            "sort": {
                "timestamp": {
                    "order": "desc"
                }
            }
        }
        if match:
            for k, v in match.items():
                body["query"]["bool"]["must"].append({"match": {k: v}})
        if exact:
            for k, v in exact.items():
                body["query"]["bool"]["filter"].append({"term": {k: v}})
        return body

    def filter(self, date_from=None, date_to=None,
               user=None, asset=None, system_user=None,
               input=None, session=None):

        match = {}
        exact = {}

        if user:
            exact["user"] = user
        if asset:
            exact["asset"] = asset
        if system_user:
            exact["system_user"] = system_user

        if session:
            match["session"] = session
        if input:
            match["input"] = input

        body = self.get_query_body(match, exact, date_from, date_to)
        data = self.es.search(index=self.index, doc_type=self.doc_type, body=body)
        return data["hits"]

    def count(self, date_from=None, date_to=None,
               user=None, asset=None, system_user=None,
               input=None, session=None):
        match = {}
        exact = {}

        if user:
            exact["user"] = user
        if asset:
            exact["asset"] = asset
        if system_user:
            exact["system_user"] = system_user

        if session:
            match["session"] = session
        if input:
            match["input"] = input
        body = self.get_query_body(match, exact, date_from, date_to)
        del body["sort"]
        data = self.es.count(body=body)
        return data["count"]

    def __getattr__(self, item):
        return getattr(self.es, item)

    def all(self):
        """返回所有数据"""
        raise NotImplementedError("Not support")
