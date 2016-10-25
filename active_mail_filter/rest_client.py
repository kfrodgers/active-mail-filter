# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import os
import requests
import json
from active_mail_filter import read_configuration_file, get_logger

conf = read_configuration_file()
HOST = os.getenv('AMF_HTTP_SERVER', conf.general.http_server_address)
PORT = os.getenv('AMF_HTTP_PORT', conf.general.http_server_port)
AUTH = (conf.general.http_user, conf.general.http_password)
CERT = (conf.http_server.cert_file, conf.http_server.pkey_file)
USE_SSL = conf.getboolean('general', 'use_ssl')
VERIFY_SSL = conf.getboolean('general', 'verify_ssl')

logger = get_logger()

requests.packages.urllib3.disable_warnings()


def _build_url(url_route='/'):
    prefix = 'http'
    if USE_SSL:
        prefix = 'https'
    return '%s://%s:%s%s' % (prefix, HOST, PORT, url_route)


def post_url(url_route, params):
    headers = {'content-type': 'application/json;charset=UTF-8',
               'Accept': 'application/json'}
    try:
        url = _build_url(url_route=url_route)
        datastr = json.dumps(params).replace(' ', '')
        req = requests.post(url, data=datastr, headers=headers, auth=AUTH, verify=VERIFY_SSL, cert=CERT)
        status_code = req.status_code
        if req.headers['content-type'].find("json") < 0:
            response = req.text
        else:
            response = req.json()
    except Exception as e:
        response = {'message': str(e)}
        status_code = 401
    return status_code, response


def put_url(url_route, params):
    headers = {'content-type': 'application/json'}
    try:
        url = _build_url(url_route=url_route)
        req = requests.put(url, data=json.dumps(params), headers=headers, auth=AUTH, verify=VERIFY_SSL, cert=CERT)
        status_code = req.status_code
        if req.headers['content-type'].find("json") < 0:
            response = req.text
        else:
            response = req.json()
    except Exception as e:
        response = {'message': str(e)}
        status_code = 400
    return status_code, response


def get_url(url_route):
    try:
        url = _build_url(url_route=url_route)
        data = requests.get(url, auth=AUTH, verify=VERIFY_SSL, cert=CERT)
        status_code = data.status_code
        if data.headers['content-type'].find("json") < 0:
            response = data.text
        else:
            response = data.json()
    except Exception as e:
        response = {'message': str(e)}
        status_code = 404
    return status_code, response


def delete_url(url_route):
    try:
        url = _build_url(url_route=url_route)
        data = requests.delete(url, auth=AUTH, verify=VERIFY_SSL, cert=CERT)
        status_code = data.status_code
        if data.status_code != 204:
            if data.headers['content-type'].find("json") < 0:
                response = data.text
            else:
                response = data.json()
        else:
            response = {'data': ''}
    except Exception as e:
        response = {'message': str(e)}
        status_code = 401
    return status_code, response
