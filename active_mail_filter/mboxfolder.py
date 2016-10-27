# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import re
import smtplib
import imaplib
from email import message_from_string
from active_mail_filter import get_logger, trace

logger = get_logger()
MAX_FETCH_HEADERS = 2048


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
        uids = []
        result, data = self.imap.select(folder_name)
        if result == 'OK':
            result, data = self.imap.uid("SEARCH", None, pattern)
            if result == 'OK':
                uids = data[0].split()
            else:
                logger.error('Folder search failed, %s', str(data[0]))
        else:
            logger.error('%s: Invalid folder, %s', folder_name, str(data[0]))
        logger.debug('search for %s in %s returned %d uids' % (pattern, folder_name, len(uids)))
        return uids

    def list_from_addresses(self, folder_name):
        from_list = set()
        uid_list = self.list_email_uids(folder_name=folder_name)
        if len(uid_list) > 0:
            msg_list = self.fetch_uid_headers(uid_list)
            for i in range(0, len(msg_list)):
                if 'From' in msg_list[i]:
                    from_list.add(msg_list[i]['From'].lower())
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
        return found.translate(None, '\t\n\r').strip()

    @staticmethod
    def _get_email_message(data):
        try:
            email_message = message_from_string(data.decode(encoding='UTF-8', errors='ignore'))
        except UnicodeEncodeError:
            email_message = message_from_string(data.decode(encoding='ascii', errors='ignore'))
        return email_message

    def fetch_uid(self, uid):
        result, data = self.imap.uid("FETCH", uid, "(BODY.PEEK[])")
        if result != 'OK':
            raise LookupError('%lu not found' % uid)

        return data[0][1]

    def fetch_uid_message(self, uid):
        return self._get_email_message(self.fetch_uid(uid))

    def fetch_uid_headers(self, uids, batch_size=MAX_FETCH_HEADERS):
        messages = []
        for index in range(0, len(uids), batch_size):
            count = len(uids[index:index+batch_size])
            uid_str = ",".join(uids[index:index+batch_size])
            trace('Fetching uids[%d:%d] == { %s }', index, index+batch_size, uid_str)
            result, data = self.imap.uid("FETCH", uid_str, "(BODY.PEEK[HEADER.FIELDS (SUBJECT DATE TO FROM)])")
            if result != 'OK':
                raise LookupError('%lu not found' % uid_str)

            if (2 * count) > len(data):
                for i in range(0, len(data)):
                    logger.error('data[%d] type=%s value=%s', i, str(type(data[i])), str(data[i]))
                raise LookupError('FETCH bad count, expected %d got %d' % ((2 * count), len(data)))

            for i in range(0, (2 * count), 2):
                messages.append(self._get_email_message(data[i][1]))

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

    def list_email_uids_from_users(self, from_users, from_folder='inbox'):
        email_addresses = list(set(self.extract_email_address(f) for f in from_users))

        sub_pattern = 'FROM "%s"' % email_addresses[0]
        for i in range(1, len(email_addresses)):
            sub_pattern = 'OR %s FROM "%s"' % (sub_pattern, email_addresses[i])

        pattern = '(%s)' % sub_pattern
        try:
            email_uids = self.list_email_uids(folder_name=from_folder, pattern=pattern)
        except Exception as e:
            logger.warning('Failed search for pattern %s', pattern)
            logger.error(e)
            raise e
        return email_uids

    def move_emails_from_users(self, from_users, to_folder, from_folder='inbox'):
        moved_uids = []
        from_lower_users = [x.lower() for x in from_users]
        email_uids = self.list_email_uids_from_users(from_users, from_folder=from_folder)
        for uid in email_uids:
            email_msg = self.fetch_uid_headers([uid])
            email_from = email_msg[0]['From']
            if email_from.lower() in from_lower_users:
                self.move_uid(uid, to_folder)
                moved_uids.append(uid)
            else:
                trace('%s not in %s', email_from.lower(), str(from_lower_users))
        return moved_uids

    def delete_uid(self, uid):
        result, data = self.imap.uid('STORE', uid, '+FLAGS', '(\Deleted)')
        if result == 'OK':
            self.imap.expunge()
        else:
            logger.error('item not deleted, %s' % str(data))

    def move_uid(self, uid, to_folder):
        result, data = self.imap.uid('COPY', uid, to_folder)
        if result == 'OK':
            self.delete_uid(uid)
        else:
            logger.error('item not copied, %s' % str(data))

    def forward_message(self, uid, to_user, smtp_login, smtp_passwd, smtp_server, smtp_port=587):
        email_message = self.fetch_uid_headers([uid])
        if len(email_message) > 0 and 'From' in email_message[0]:
            try:
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.ehlo()
                server.starttls()
                server.login(smtp_login, smtp_passwd)
                server.sendmail(email_message[0]['From'], to_user, self.fetch_uid(uid))
                server.quit()
                from_user = email_message[0]['From']
                logger.debug('Forwarded message from %s to %s', from_user, to_user)
            except Exception as e:
                logger.error('Failed to forward mail from %s, %s', email_message[0]['From'], e.message)
                raise e
        else:
            from_user = None
        return from_user
