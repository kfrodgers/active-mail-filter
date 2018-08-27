# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from active_mail_filter import get_logger

logger = get_logger()

DEF_BATCH_SIZE = 80


class ImapUser(object):
    def __init__(self, mailbox, to_folder, from_folder='inbox'):
        self.to_folder = to_folder
        self.from_folder = from_folder
        self.mailbox = mailbox

    def __str__(self):
        return '{m}: {f}'.format(m=self.mailbox, f=self.to_folder)

    def list_folders(self):
        self.mailbox.connect()
        folders = self.mailbox.list_folders()
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

        return len(moved_uids), moved_uids

    def forward_mail(self, smtp_to, smtp_host, smtp_login=None, smtp_passwd=None, smtp_port=587):
        from_list = []
        self.mailbox.connect()
        try:
            uids = self.mailbox.list_email_uids(folder_name=self.from_folder, pattern='(UNSEEN)')
            for uid in uids:
                logger.debug('Forwarding uid == %s', uid)
                from_user = self.mailbox.forward_message(uid, smtp_to, smtp_host,
                                                         smtp_login=smtp_login, smtp_passwd=smtp_passwd,
                                                         smtp_port=smtp_port)
                if from_user is not None:
                    self.mailbox.mark_uid_read(uid)
                    from_list.append(from_user)
        except Exception as e:
            logger.error(e.message)
            raise RuntimeError(e.message)

        return len(from_list), from_list
