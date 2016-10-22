#! /usr/bin/python
# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import logging
from active_mail_filter import amf_config
from active_mail_filter.simple_password import SimplePassword

logger = logging.getLogger(amf_config.logging.logger)
logger.setLevel(logging.DEBUG)


def test_password():
    start = 'Passw0rd!'
    cipher = SimplePassword(secret_key='cipher-key-12345')
    encoded = cipher.encode(start)
    decoded = cipher.decode(encoded)
    logger.info(cipher)
    logger.info('%s == %s', start, encoded)
    if decoded != start:
        logger.error('Password encode/decode failed %s != %s', decoded, start)
    else:
        logger.info('match!')

if __name__ == '__main__':
    try:
        test_password()
    except KeyboardInterrupt:
        pass
