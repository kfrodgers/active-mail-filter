# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import sys
import getopt
import logging
import signal
from flask import make_response, jsonify
from flask_httpauth import HTTPBasicAuth
from flask_cors import CORS
import connexion

from active_mail_filter import get_logger, read_configuration_file
from daemon import start_daemon_thread, sigterm_handler

_CONF_ = read_configuration_file()

logger = get_logger()


app = connexion.App(__name__, specification_dir="./")
app.add_api('swagger.yaml')

webapp = app.app
webapp.static_folder = "./static"
CORS(webapp)

auth = HTTPBasicAuth()
listen_address = (_CONF_['http_server']['listen_address'], _CONF_.getint('general', 'http_server_port'))
ssl_context = (_CONF_['http_server']['cert_file'], _CONF_['http_server']['pkey_file'])


def _read_file(file_name):
    with open(file_name) as _file:
        return _file.read()


@webapp.route('/')
def index():
    return _read_file('../active_mail_filter/index.html')


@auth.get_password
def get_password(username):
    password = None
    if username == _CONF_['general']['http_user']:
        password = _CONF_['general']['http_password']
    return password


@auth.error_handler
def unauthorized():
    return make_response(jsonify({'message': 'Unauthorized access'}), 403)


def run_daemon():
    try:
        options, remainder = getopt.getopt(sys.argv[1:], 'vs', [])
    except getopt.GetoptError as err:
        sys.stderr.write('%s\n' % err)
        sys.exit(1)

    debug = False
    for opt, arg in options:
        if opt == '-v':
            debug = True
            logger.setLevel(logging.DEBUG)
        elif opt == '-s':
            start_daemon_thread()
        else:
            sys.exit(1)

    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGINT, sigterm_handler)

    try:
        if _CONF_.getboolean('general', 'use_ssl'):
            app.run(host=listen_address[0], port=listen_address[1], debug=debug)
        else:
            app.run(host=listen_address[0], port=listen_address[1], debug=debug)
    except KeyboardInterrupt:
        pass
