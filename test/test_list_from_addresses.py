#! /usr/bin/python
# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import logging
from active_mail_filter import get_logger
from active_mail_filter.mboxfolder import MboxFolder

logger = get_logger()
logger.setLevel(logging.DEBUG)


def main():
    host = 'imap.mail.yahoo.com'
    username = 'user@yahoo.com'
    password = 'password'
    folder = 'inbox'
    mbox = MboxFolder(host, username, password)
    uids = mbox.list_from_addresses(folder)
    start = 0
    batch_count = 5
    while start < len(uids):
        print str(uids[start:start+batch_count])
        start += batch_count
    print 'Total = %d' % len(uids)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
