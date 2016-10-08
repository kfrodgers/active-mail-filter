# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import requests
import json
import logging
from active_mail_filter import amf_config

logger = logging.getLogger(amf_config.logging.logger)


def post_url(url, params, auth=None):
    headers = {'content-type': 'application/json;charset=UTF-8',
               'Accept': 'application/json'}
    try:
        datastr = json.dumps(params).replace(' ', '')
        req = requests.post(url, data=datastr, headers=headers, auth=auth)
        status_code = req.status_code
        if req.headers['content-type'].find("json") < 0:
            response = req.text
        else:
            response = req.json()
    except Exception as e:
        response = {'message': str(e)}
        status_code = 401
    return status_code, response


def put_url(url, params, auth=None):
    headers = {'content-type': 'application/json'}
    try:
        req = requests.put(url, data=json.dumps(params), headers=headers, auth=auth)
        status_code = req.status_code
        if req.headers['content-type'].find("json") < 0:
            response = req.text
        else:
            response = req.json()
    except Exception as e:
        response = {'message': str(e)}
        status_code = 400
    return status_code, response


def get_url(url, auth=None):
    try:
        data = requests.get(url, auth=auth)
        status_code = data.status_code
        if data.headers['content-type'].find("json") < 0:
            response = data.text
        else:
            response = data.json()
    except Exception as e:
        response = {'message': str(e)}
        status_code = 404
    return status_code, response


def delete_url(url, auth=None):
    try:
        data = requests.delete(url, auth=auth)
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
