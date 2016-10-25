# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from simple_db import SimpleRedisDb, UUID
from simple_password import SimplePassword
from active_mail_filter import get_logger

logger = get_logger()

USER = 'user'
EMAIL = 'email'
PASSWORD = 'password'
MAILSERVER = 'mail_server'
SOURCE = 'source'
TARGET = 'target'


class UserRecords(object):
    def __init__(self, host, key='active_mail_filter', cipher='1234567890123456'):
        self.cipher = SimplePassword(cipher)
        self.redis_db = SimpleRedisDb(host=host, key=key)

    def __str__(self):
        return 'UserRecords [cipher=%s, redis_db=%s]' % (str(self.cipher), str(self.redis_db))

    def add_user(self, user, email, password, mail_server, source, target):
        record = {UUID: None,
                  USER: user,
                  EMAIL: email,
                  PASSWORD: self.cipher.encode(password),
                  MAILSERVER: mail_server,
                  SOURCE: source,
                  TARGET: target}

        for rec in self.redis_db.get_all_records():
            if rec[USER] == user and rec[SOURCE] == source and rec[TARGET] == target:
                logger.error('%s already added' % user)
                raise ValueError('duplicate entry')

        return self.redis_db.add_record(record_dict=record)

    def update_user(self, record_uuid, user_record):
        password = self.cipher.encode(user_record[PASSWORD])
        user_record[PASSWORD] = password
        self.redis_db.update_record(record_uuid, user_record)
        return

    def get_all_users(self):
        records = self.redis_db.get_all_records()
        for rec in records:
            password = self.cipher.decode(rec[PASSWORD])
            rec[PASSWORD] = password

        return records

    def get_user(self, user, source=None, target=None):
        records = []
        for rec in self.get_all_users():
            if (rec[USER] == user) and \
                    (source is None or rec[SOURCE] == source) and \
                    (target is None or rec[TARGET] == target):
                records.append(rec)

        return records

    def get_user_by_uuid(self, uuid):
        rec = self.redis_db.get_record(uuid)
        password = self.cipher.decode(rec[PASSWORD])
        rec[PASSWORD] = password
        return rec

    def del_record(self, record_key):
        self.redis_db.delete_record(record_key)
