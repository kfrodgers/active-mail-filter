# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import os
import requests
import json
import logging
from active_mail_filter import amf_config

HOST = os.getenv('AMF_HTTP_SERVER', amf_config.http_client.server_address)
PORT = os.getenv('AMF_HTTP_PORT', amf_config.http_server.listen_port)
AUTH = (amf_config.http_server.http_user, amf_config.http_server.http_password)
CERT = (amf_config.http_server.cert_file, amf_config.http_server.pkey_file)
USE_SSL = amf_config.getboolean('http_server', 'use_ssl')

logger = logging.getLogger(amf_config.logging.logger)


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
        req = requests.post(url, data=datastr, headers=headers, auth=AUTH, verify=USE_SSL, cert=CERT)
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
        req = requests.put(url, data=json.dumps(params), headers=headers, auth=AUTH, verify=USE_SSL, cert=CERT)
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
        data = requests.get(url, auth=AUTH, verify=USE_SSL, cert=CERT)
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
        data = requests.delete(url, auth=AUTH, verify=USE_SSL, cert=CERT)
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
