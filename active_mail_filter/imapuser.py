# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import mboxfolder
from active_mail_filter import get_logger

logger = get_logger()

DEF_BATCH_SIZE = 32


class ImapUser(object):
    def __init__(self, host, username, password, to_folder, from_folder='inbox'):
        self.username = username
        self.password = password
        self.host = host
        self.to_folder = to_folder
        self.from_folder = from_folder
        self.mailbox = None
        self._connect()

    def _connect(self):
        if self.mailbox is None:
            self.mailbox = mboxfolder.MboxFolder(self.host, self.username, self.password)
            if not self.mailbox.is_valid_folder(self.to_folder):
                raise ValueError('{f}: Invalid folder'.format(f=self.to_folder))
            self.mailbox.disconnect()

    def __str__(self):
        return '{u}/{h}: {f}'.format(u=self.username, h=self.host, f=self.to_folder)

    def disconnect(self):
        if self.mailbox is not None:
            self.mailbox.disconnect()

    def list_folders(self):
        self.mailbox.connect()
        folders = self.mailbox.list_folders()
        self.disconnect()
        return folders

    def filter_mail(self, batch_size=DEF_BATCH_SIZE):
        moved_uids = []
        self.mailbox.connect()
        try:
            from_list = self.mailbox.list_from_addresses(folder_name=self.to_folder)
            for i in range(0, len(from_list), batch_size):
                uids = self.mailbox.move_emails_from_users(from_list[i:i+batch_size],
                                                           self.to_folder, from_folder=self.from_folder)
                moved_uids.extend(uids)
        except Exception as e:
            logger.error(e.message)
            raise RuntimeError(e.message)

        self.disconnect()
        return len(moved_uids), moved_uids
