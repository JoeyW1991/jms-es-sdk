# coding: utf-8
import datetime

import pytz
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

__version__ = '0.5.1'


class ESStore:

    def __init__(self, hosts, index="jumpserver", doc_type="command_store", **kwargs):
        self.hosts = hosts
        self.index = index
        self.doc_type = doc_type
        self.es = Elasticsearch(hosts=self.hosts, **kwargs)

    @staticmethod
    def make_data(command):
        timestamp = command["timestamp"]
        if isinstance(timestamp, datetime.datetime) and timestamp.tzinfo != pytz.UTC:
            timestamp = timestamp.timestamp()
        if isinstance(timestamp, (int, float)):
            command["timestamp"] = datetime.datetime.fromtimestamp(
                timestamp, tz=pytz.UTC
            )
        data = dict(
            user=command["user"], asset=command["asset"],
            system_user=command["system_user"], input=command["input"],
            output=command["output"], session=command["session"],
            timestamp=command["timestamp"]
        )
        return data

    def bulk_save(self, command_set, raise_on_error=True):
        actions = []
        for command in command_set:
            data = dict(
                _index=self.index,
                _type=self.doc_type,
                _source=self.make_data(command),
                _timestamp=datetime.datetime.utcnow()
            )
            actions.append(data)
        return bulk(self.es, actions, index=self.index, raise_on_error=raise_on_error)

    def save(self, command):
        """
        保存命令到数据库
        """
        data = self.make_data(command)
        return self.es.index(index=self.index, doc_type=self.doc_type,
                             body=data, timestamp=datetime.datetime.utcnow())

    def get_query_body(self, match=None, exact=None, date_from=None, date_to=None):
        if date_to is None:
            date_to = datetime.datetime.now()
        if date_from is None:
            date_from = date_to - datetime.timedelta(days=7)

        body = {
            "query": {
                "bool": {
                    "must": [],
                    "filter": [
                        {"range": {
                            "timestamp": {
                                "gte": date_from,
                                "lte": date_to,
                            }
                        }}
                    ]
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

    def __getattr__(self, item):
        return getattr(self.es, item)

    def all(self):
        """返回所有数据"""
        raise NotImplementedError("Not support")
