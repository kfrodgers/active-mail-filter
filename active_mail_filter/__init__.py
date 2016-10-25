#! /usr/bin/python
# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import os
import sys
import logging
import simpleconfigparser

CONF_FILE = os.getenv('AMF_CONF_FILE', '/usr/local/etc/amf.conf')
_CONF_ = None


def read_configuration_file(refresh=False):
    global _CONF_

    # read configuration file, add missing parameters
    if _CONF_ is None or refresh:
        _CONF_ = simpleconfigparser.simpleconfigparser()
        _CONF_.read(CONF_FILE)

        default_conf = {'general': {'http_server_address': '127.0.0.1',
                                    'http_server_port': '5000',
                                    'http_enable_auth': 'True',
                                    'http_user': 'admin',
                                    'http_password': 'admin',
                                    'verify_ssl': 'False',
                                    'use_ssl': 'False',
                                    'log_level': 'INFO',
                                    'logger': 'active_filter',
                                    'log_file': '/var/log/active_mail_filter.log'},
                        'redis_server': {'redis_server_address': '127.0.0.1',
                                         'redis_key': 'active_mail_filter',
                                         'cipher_key': '1234567890123456'},
                        'http_server': {'listen_address': '0.0.0.0',
                                        'cert_file': '',
                                        'pkey_file': ''}
                        }

        for section in sorted(default_conf.keys()):
            if not _CONF_.has_section(section=section):
                _CONF_.add_section(section=section)

            for option in sorted(default_conf[section].keys()):
                if not _CONF_.has_option(section=section, option=option):
                    _CONF_.set(section=section, option=option, value=default_conf[section][option])

    config = _CONF_
    return config


def write_configuration_file(conf):
    with open(CONF_FILE, 'w+') as handle:
        conf.write(handle)
        handle.write('\n')
    handle.close()


def get_logger():
    return logging.getLogger(_CONF_.general.logger)


def trace(msg, *args, **kwargs):
    logger = get_logger()
    if logger.isEnabledFor(4):
        logger._log(4, msg, args, **kwargs)


def get_default_level():
    if hasattr(logging, _CONF_.general.log_level):
        level = getattr(logging, _CONF_.general.log_level)
    elif _CONF_.general.log_level.lower() == 'trace':
        level = 4
    else:
        level = logging.INFO
    return level


def init_logging():
    logging.addLevelName(4, 'TRACE')
    try:
        log_file_format = '%(asctime)s - %(levelname)s - %(filename)s - line %(lineno)d - %(message)s'
        logging.basicConfig(filename=_CONF_.general.log_file, format=log_file_format, level=get_default_level())
    except IOError:
        log_file_format = '%(levelname)s:%(filename)s: %(message)s'
        logging.basicConfig(stream=sys.stderr, format=log_file_format)


read_configuration_file()
init_logging()
get_logger().setLevel(get_default_level())