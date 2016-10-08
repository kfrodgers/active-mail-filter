# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import redis
import logging
from uuid import uuid4
from active_mail_filter import amf_config

logger = logging.getLogger(amf_config.logging.logger)

UUID = 'uuid'


class SimpleRedisDb(object):
    def __init__(self, host, key, port=6379):
        """

        :param host: database host
        :param port: database port default 6397
        :param key: hash set name default active_mail_filter
        """
        self.host = host
        self.port = port
        self.key = key
        self.redis = None

    def __str__(self):
        return 'SimpleRedisDb [host=%s, port=%d, key=%s, redis=%s]' % \
               (self.host, self.port, self.key, str(self.redis))

    def __del__(self):
        """
        Close database on delete of object
        :return:
        """
        self._close_db()

    def _open_db(self):
        """
        Opens/reopens database if necessary
        :return:
        """
        if self.redis is None:
            self.redis = redis.Redis(connection_pool=redis.ConnectionPool(host=self.host, port=self.port, db=0))

    def _close_db(self):
        """
        Closes database
        :return:
        """
        if self.redis is not None:
            del self.redis
            self.redis = None

    def _clear_all(self):
        """
        Removes all keys from hash set
        :return:
        """
        self._open_db()
        record_keys = self.redis.hkeys(self.key)
        for u in record_keys:
            self.redis.hdel(self.key, u)

    def get_record(self, record_key):
        """
        Return record dictionary for specified UUID
        :param record_key:
        :return:
        record dictionary or None if not found
        """
        self._open_db()

        record_str = self.redis.hget(self.key, record_key)
        if record_str is None:
            raise LookupError('%s key not found' % record_key)

        return eval(record_str)

    def get_all_records(self):
        """
        Return a list of all records
        :return:
        list of all record dictionaries
        """
        self._open_db()

        all_records = []
        record_keys = self.redis.hkeys(self.key)
        for u in record_keys:
            record_str = self.redis.hget(self.key, u)
            if record_str is not None:
                all_records.append(eval(record_str))

        return all_records

    def add_record(self, record_dict):
        """
        Add a record to the hash set, auto generate UUID
        :param record_dict: record dictionary
        :return:
        hash set key or UUID generated for volume dictionary
        """
        self._open_db()

        record_dict[UUID] = unicode(uuid4())
        self.redis.hset(self.key, record_dict[UUID], unicode(record_dict))
        return record_dict[UUID]

    def delete_record(self, record_key):
        """
        Delete record from hash set by UUID
        :param record_key:
        :return:
        """
        self._open_db()
        self.redis.hdel(self.key, record_key)

    def update_record(self, record_key, record_dict):
        """
        Update/replace record dictionary by UUID
        :param record_key: UUID
        :param record_dict: volume dictionary
        :return:
        """
        self._open_db()
        record_dict[UUID] = record_key
        self.redis.hset(self.key, record_dict[UUID], unicode(record_dict))
