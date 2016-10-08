# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import logging
import imaplib
import re
from email import message_from_string
from active_mail_filter import amf_config

logger = logging.getLogger(amf_config.logging.logger)


class MboxFolder(object):
    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password
        self.imap = None
        self.connect()

    def __str__(self):
        return 'MboxFolder [host=' + self.host + ', username=' + self.username + \
               ', imap=' + str(self.imap) + ']'

    def connect(self):
        if self.imap is None:
            logger.debug('imap connecting to host %s:%d' % (self.host, imaplib.IMAP4_SSL_PORT))
            try:
                self.imap = imaplib.IMAP4_SSL(self.host, port=imaplib.IMAP4_SSL_PORT)
                self.imap.login(self.username, self.password)
            except Exception as e:
                logger.error('connection failure, %s.', str(e.message))
                raise e

    def disconnect(self):
        if self.imap is not None:
            logger.debug('imap disconnecting from host %s' % self.host)
            self.imap.logout()
            del self.imap
            self.imap = None

    def list_folders(self):
        folder_list = []
        result, folders = self.imap.list()
        for f in folders:
            fields = f.split('"')
            folder_list.append(fields[-2])
        return folder_list

    def is_valid_folder(self, folder_name):
        folders = self.list_folders()
        return folder_name in folders

    def list_email_uids(self, folder_name="inbox", pattern="ALL"):
        self.imap.select(folder_name)
        result, data = self.imap.uid("SEARCH", None, pattern)
        if result == 'OK':
            uids = data[0].split()
        else:
            uids = []
        logger.debug('search for %s in %s returned %d uids' % (pattern, folder_name, len(uids)))
        return uids

    def list_from_addresses(self, folder_name, max_count=None):
        from_list = set()
        uid_list = self.list_email_uids(folder_name=folder_name)
        if len(uid_list) > 0:
            msg_list = self.fetch_uid_headers(uid_list)
            for msg in msg_list:
                from_list.add(msg['From'].lower())
                if max_count is not None and len(from_list) >= max_count:
                    break
        logger.debug('found %d from addresses' % len(from_list))
        return list(from_list)

    @staticmethod
    def extract_email_address(from_string):
        if '<' in from_string and '>' in from_string:
            regex_expr = '<(.+?)>'
        elif '"' in from_string:
            regex_expr = '"(.+?)"'
        else:
            regex_expr = None

        if regex_expr is not None:
            try:
                found = re.search(regex_expr, from_string).group(1)
            except AttributeError:
                raise RuntimeError('%s: malformed email address' % from_string)
        else:
            found = from_string.split(' ')[0]
        return found

    def fetch_uid(self, uid):
        result, data = self.imap.uid("FETCH", uid, "(BODY.PEEK[])")
        if result != 'OK':
            raise LookupError('%lu not found' % uid)

        return message_from_string(data[0][1])

    def fetch_uid_headers(self, uids):
        uid_str = ",".join(uids)
        logger.debug('Fetching uids == { %s }' % uid_str)
        result, data = self.imap.uid("FETCH", uid_str, "(BODY.PEEK[HEADER.FIELDS (SUBJECT DATE FROM)])")
        if result != 'OK':
            raise LookupError('%lu not found' % uid_str)

        if (2 * len(uids)) != len(data):
            for i in range(0, len(data)):
                for j in range(0, len(data[i])):
                    logger.error('data[%d][%d] == %s', i, j, str(data[i][j]))
            raise LookupError('FETCH wrong count, expected %d got %d' % ((2 * len(uids)), len(data)))

        messages = []
        for i in range(1, len(data), 2):
            messages.append(message_from_string(data[i-1][1]))
        return messages

    def get_flags(self, uid):
        result, data = self.imap.uid("FETCH", uid, "(FLAGS)")
        if result != 'OK':
            raise LookupError('%lu not found' % uid)

        found = re.search('(FLAGS )\((.*?)\)', data[0]).group(2)
        return found

    def mark_uid_read(self, uid):
        result, data = self.imap.uid("STORE", uid, '+FLAGS', '(\Seen)')
        if result != 'OK':
            raise LookupError('%lu not found' % uid)

    def mark_uid_unread(self, uid):
        result, data = self.imap.uid("STORE", uid, '-FLAGS', '(\Seen)')
        if result != 'OK':
            raise LookupError('%lu not found' % uid)

    def list_email_uids_from_user(self, from_user, from_folder='inbox'):
        email_addr = self.extract_email_address(from_user)
        pattern = '(FROM "{email}")'.format(email=email_addr)
        email_uids = self.list_email_uids(folder_name=from_folder, pattern=pattern)
        return email_uids

    def move_emails_from_user(self, from_user, to_folder, from_folder='inbox'):
        moved_uids = []
        email_uids = self.list_email_uids_from_user(from_user, from_folder=from_folder)
        for uid in email_uids:
            email_msg = self.fetch_uid_headers([uid])
            email_from = email_msg[0]['From']
            if email_from.lower() == from_user.lower():
                self.move_uid(uid, to_folder)
                moved_uids.append(uid)
            else:
                logger.debug('%s not equal to %s' % (email_from.lower(), from_user.lower()))
        return moved_uids

    def move_uid(self, uid, to_folder):
        result, data = self.imap.uid('COPY', uid, to_folder)
        if result == 'OK':
            result, data = self.imap.uid('STORE', uid, '+FLAGS', '(\Deleted)')
            if result == 'OK':
                self.imap.expunge()
            else:
                logger.error('item mot deleted, {data}'.format(data=data))
        else:
            logger.error('item not copied, {data}'.format(data=data))
