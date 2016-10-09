#! /usr/bin/python
# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import sys
import logging
from active_mail_filter import amf_config
from active_mail_filter.mboxfolder import MboxFolder

logger = logging.getLogger(amf_config.logging.logger)
stream = logging.StreamHandler(stream=sys.stdout)
stream.setLevel(logging.DEBUG)
logger.addHandler(stream)
logger.setLevel(logging.DEBUG)

def main():
    host = 'imap.gmail.com'
    username = 'user'
    password = 'pwd'
    mbox = MboxFolder(host, username, password)
    uids = mbox.list_from_addresses('inbox')
    print str(uids)
    print str(len(uids))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
