#! /usr/bin/python
# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import os
import sys
import logging
import simpleconfigparser

# read configuration file, add missing parameters
CONF_FILE = os.getenv('AMF_CONF_FILE', '/usr/local/etc/amf.conf')

amf_config = simpleconfigparser.simpleconfigparser()
amf_config.read(CONF_FILE)

if not amf_config.has_section('general'):
    amf_config.add_section('general')

if not amf_config.has_section('redis_server'):
    amf_config.add_section('redis_server')

if not amf_config.has_section('http_server'):
    amf_config.add_section('http_server')

if not amf_config.has_option('redis_server', 'redis_server_address'):
    amf_config.set('redis_server', 'redis_server_address', value='127.0.0.1')

if not amf_config.has_option('redis_server', 'redis_key'):
    amf_config.set('redis_server', 'redis_key', value='active_mail_filter')

if not amf_config.has_option('redis_server', 'cipher_key'):
    amf_config.set('redis_server', 'cipher_key', value='1234567890123456')

if not amf_config.has_option('http_server', 'listen_address'):
    amf_config.set('http_server', 'listen_address', value='0.0.0.0')

if not amf_config.has_option('http_server', 'cert_file'):
    amf_config.set('http_server', 'cert_file', value='')

if not amf_config.has_option('http_server', 'pkey_file'):
    amf_config.set('http_server', 'pkey_file', value='')

if not amf_config.has_option('general', 'http_server_address'):
    amf_config.set('general', 'http_server_address', value='127.0.0.1')

if not amf_config.has_option('general', 'http_server_port'):
    amf_config.set('general', 'http_server_port', value='5000')

if not amf_config.has_option('general', 'http_enable_auth'):
    amf_config.set('general', 'http_enable_auth', value='True')

if not amf_config.has_option('general', 'http_user'):
    amf_config.set('general', 'http_user', value='admin')

if not amf_config.has_option('general', 'http_password'):
    amf_config.set('general', 'http_password', value='admin')

if not amf_config.has_option('general', 'verify_ssl'):
    amf_config.set('general', 'verify_ssl', value='False')

if not amf_config.has_option('general', 'use_ssl'):
    amf_config.set('general', 'use_ssl', value='False')

if not amf_config.has_option('general', 'log_level'):
    amf_config.set('general', 'log_level', value='INFO')

if not amf_config.has_option('general', 'logger'):
    amf_config.set('general', 'logger', value='active_filter')

if not amf_config.has_option('general', 'log_file'):
    amf_config.set('general', 'log_file', value='/var/log/active_mail_filter.log')

# create logger
log_file_format = '%(asctime)s - %(levelname)s - %(filename)s - line %(lineno)d - %(message)s'
if hasattr(logging, amf_config.general.log_level):
    level = getattr(logging, amf_config.general.log_level)
else:
    level = logging.INFO

try:
    logging.basicConfig(filename=amf_config.general.log_file, format=log_file_format, level=level)
except IOError:
    logging.basicConfig(stream=sys.stderr, format=log_file_format)

amf_logger = logging.getLogger(amf_config.general.logger)
amf_logger.setLevel(level)
