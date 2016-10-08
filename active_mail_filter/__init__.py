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

if not amf_config.has_section('logging'):
    amf_config.add_section('logging')

if not amf_config.has_section('redis_server'):
    amf_config.add_section('redis_server')

if not amf_config.has_section('http_client'):
    amf_config.add_section('http_client')

if not amf_config.has_section('http_server'):
    amf_config.add_section('http_server')

if not amf_config.has_option('redis_server', 'redis_server'):
    amf_config.set('redis_server', 'redis_server', value='127.0.0.1')

if not amf_config.has_option('redis_server', 'redis_key'):
    amf_config.set('redis_server', 'redis_key', value='active_mail_filter')

if not amf_config.has_option('redis_server', 'cipher_key'):
    amf_config.set('redis_server', 'cipher_key', value='1234567890123456')

if not amf_config.has_option('http_client', 'server_address'):
    amf_config.set('http_client', 'server_address', value='127.0.0.1')

if not amf_config.has_option('http_server', 'enable_auth'):
    amf_config.set('http_server', 'enable_auth', value='True')

if not amf_config.has_option('http_server', 'listen_address'):
    amf_config.set('http_server', 'listen_address', value='0.0.0.0')

if not amf_config.has_option('http_server', 'listen_port'):
    amf_config.set('http_server', 'listen_port', value='5000')

if not amf_config.has_option('http_server', 'http_user'):
    amf_config.set('http_server', 'http_user', value='admin')

if not amf_config.has_option('http_server', 'http_password'):
    amf_config.set('http_server', 'http_password', value='admin')

if not amf_config.has_option('logging', 'log_level'):
    amf_config.set('logging', 'log_level', value='INFO')

if not amf_config.has_option('logging', 'logger'):
    amf_config.set('logging', 'logger', value='active_filter')

if not amf_config.has_option('logging', 'log_file'):
    amf_config.set('logging', 'log_file', value='/var/log/active_mail_filter.log')

# create logger
format = '%(created)f - %(levelname)s - %(filename)s - line %(lineno)d - %(message)s'
if amf_config.logging.log_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
    level = getattr(logging, amf_config.logging.log_level)

try:
    logging.basicConfig(filename=amf_config.logging.log_file, format=format, level=level)
except IOError:
    logging.basicConfig(stream=sys.stderr, format=format)

amf_logger = logging.getLogger(amf_config.logging.logger)
amf_logger.setLevel(level)
