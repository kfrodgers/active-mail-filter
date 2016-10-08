# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from Crypto.Cipher import AES
import logging
import base64
import string
import random
from active_mail_filter import amf_config

logger = logging.getLogger(amf_config.logging.logger)


class SimplePassword(object):
    def __init__(self, secret_key):
        logger.debug('secret key length == %d' % len(secret_key))
        self.secret_key = secret_key
        self.cipher = AES.new(self.secret_key, mode=AES.MODE_ECB)

    def __str__(self):
        return 'SimplePassword [secret_key=' + self.secret_key + ', cipher=' + str(self.cipher) + ']'

    def encode(self, password):
        oldlen = len(password)
        addlen = 2
        while ((oldlen + addlen) % 16) != 0:
            password = random.choice(string.letters) + password
            addlen+=1

        password = '%2.2d%s' % (addlen, password)
        logger.debug('added %d bytes to password' % addlen)
        return base64.b64encode(self.cipher.encrypt(password))

    def decode(self, encoded_password):
        try:
            decoded = self.cipher.decrypt(base64.b64decode(encoded_password))
        except ValueError as e:
            decoded = ''
            logger.error('password decrypt failed, %s', e.message)

        password = decoded.strip()
        logger.debug('skipping first %s bytes' % password[0:2])
        try:
            addlen = int(password[0:2])
        except ValueError:
            addlen = 0
        return password[addlen:]
