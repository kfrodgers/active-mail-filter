# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import os
import sys
import getopt
import logging
from active_mail_filter import amf_config, CONF_FILE
from active_mail_filter.rest_client import get_url, put_url, delete_url, post_url

logger = logging.getLogger(amf_config.logging.logger)

PROGNAME = os.path.basename(sys.argv[0])


def print_usage(usage):
    sys.stderr.write(usage)
    return 2


def list_rules():
    usage = ('Usage: {0} '
             '[-u <username>]\n'.format(PROGNAME))

    format_string = '%-37s %-20s %-15s %-10s %-10s'

    try:
        options, remainder = getopt.getopt(sys.argv[1:], 'u:', [])
    except getopt.GetoptError as err:
        sys.stderr.write('{0!s}\n'.format(err))
        sys.exit(print_usage(usage))

    user = None
    for opt, arg in options:
        if opt == '-u':
            user = arg
        else:
            sys.exit(print_usage(usage))

    status, data = get_url(url_route='/list')
    if status != 200:
        if 'message' in data:
            print 'Error: ' + str(data['message'])
        else:
            print 'Error: ' + str(data)
        sys.exit(status)
    users = data['data']

    print format_string % ('UUID', 'User', 'Server', 'Source', 'Target')
    for name in users.keys():
        if user is not None and user != name:
            continue
        for uuid in users[name]:
            url_route = '/show/%s' % uuid
            status, data = get_url(url_route=url_route)
            if status != 200:
                print str(data)
                sys.exit(status)
            rec = data['data']
            print format_string % (rec['uuid'], rec['user'], rec['mail_server'], rec['source'], rec['target'])


def start_daemon():
    do_start_stop_daemon(command='/start')


def stop_daemon():
    do_start_stop_daemon(command='/stop')


def do_start_stop_daemon(command):
    usage = ('Usage: {0}\n'.format(PROGNAME))

    try:
        options, remainder = getopt.getopt(sys.argv[1:], 'd', [])
    except getopt.GetoptError as err:
        sys.stderr.write('{0!s}\n'.format(err))
        sys.exit(print_usage(usage))

    for opt, arg in options:
        if opt == '-d':
            logger.setLevel(logging.DEBUG)
        else:
            sys.exit(print_usage(usage))

    status, data = post_url(url_route=command, params={})
    if status != 201:
        print 'Error: %s' % str(data['message'])

    status, data = get_url(url_route='/')
    if status != 200:
        print 'Error: %s' % str(data['message'])
    else:
        procs = data['data']
        for p in procs.keys():
            print str(p) + ' thread is running'


def print_folders(folders):
    print 'Valid folders are...'
    for f in sorted(folders):
        print '\t' + f


def check_folders(user, password, mail_server, source, target):
    params = {'user': user,
              'password': password,
              'mail_server': mail_server}

    status, data = post_url(url_route='/folders', params=params)
    if status != 201:
        print 'Error: %s' % str(data['message'])
        sys.exit(status)

    # Special checks because inbox folder name is case insensitive
    folders = data['data'][params['user']]
    if source.lower() != 'inbox' and source not in folders:
        print '%s: Invalid source folder' % source
        print_folders(folders)
        sys.exit(1)

    # can't use inbox as target folder
    if target.lower() == 'inbox' or target not in folders:
        print '%s: Invalid target folder' % target
        print_folders(folders)
        sys.exit(1)


def add_rule():
    usage = ('Usage: {0} '
             '-u <username> '
             '-p <password> '
             '-e <email> '
             '-i <imap-server> '
             '-s <source-folder> '
             '-t <target-folder>\n'.format(PROGNAME))

    try:
        options, remainder = getopt.getopt(sys.argv[1:], 'du:p:e:i:s:t:', [])
    except getopt.GetoptError as err:
        sys.stderr.write('{0!s}\n'.format(err))
        sys.exit(print_usage(usage))

    user = None
    password = None
    email = None
    mail_server = None
    source = None
    target = None
    for opt, arg in options:
        if opt == '-d':
            logger.setLevel(logging.DEBUG)
        elif opt == '-u':
            user = arg
        elif opt == '-p':
            password = arg
        elif opt == '-e':
            email = arg
        elif opt == '-i':
            mail_server = arg
        elif opt == '-s':
            source = arg
        elif opt == '-t':
            target = arg
        else:
            sys.exit(print_usage(usage))

    if None in [user, password, email, mail_server, source, target]:
        sys.exit(print_usage(usage))

    params = {'user': user,
              'email': email,
              'password': password,
              'mail_server': mail_server,
              'source': source,
              'target': target}

    check_folders(user, password, mail_server, source, target)

    status, data = put_url(url_route='/add', params=params)
    if status != 201:
        print 'Error: %s' % str(data['message'])
        sys.exit(status)

    print data['data']['uuid']


def modify_rule():
    usage = ('Usage: {0} '
             '-U <uuid> '
             '-u <username> '
             '-p <password> '
             '-e <email> '
             '-i <imap-server> '
             '-s <source-folder> '
             '-t <target-folder>\n'.format(PROGNAME))

    try:
        options, remainder = getopt.getopt(sys.argv[1:], 'dU:u:p:e:i:s:t:', [])
    except getopt.GetoptError as err:
        sys.stderr.write('{0!s}\n'.format(err))
        sys.exit(print_usage(usage))

    uuid = None
    user = None
    password = None
    email = None
    mail_server = None
    source = None
    target = None
    for opt, arg in options:
        if opt == '-d':
            logger.setLevel(logging.DEBUG)
        elif opt == '-U':
            uuid = arg
        elif opt == '-u':
            user = arg
        elif opt == '-p':
            password = arg
        elif opt == '-e':
            email = arg
        elif opt == '-i':
            mail_server = arg
        elif opt == '-s':
            source = arg
        elif opt == '-t':
            target = arg
        else:
            sys.exit(print_usage(usage))

    if uuid is None:
        sys.exit(print_usage(usage))

    params = {'user': user,
              'email': email,
              'password': password,
              'mail_server': mail_server,
              'source': source,
              'target': target}

    url_route = '/show/%s' % uuid
    status, data = get_url(url_route=url_route)
    if status != 200:
        print str(data)
        sys.exit(status)

    old_params = data['data']
    for key in params.keys():
        if key in old_params and params[key] is None:
            params[key] = old_params[key]
        if params[key] is None:
            del params[key]

    check_folders(params['user'], params['password'], params['mail_server'],
                  params['source'], params['target'])

    url_route = '/update/%s' % uuid
    status, data = put_url(url_route=url_route, params=params)
    if status != 201:
        print 'Error: %s' % str(data['message'])
        sys.exit(status)

    print data['data']['uuid']


def delete_rule():
    usage = ('Usage: {0} '
             'uuid [uuid2 uuid3 ...]\n'.format(PROGNAME))
    try:
        options, remainder = getopt.getopt(sys.argv[1:], 'd', [])
    except getopt.GetoptError as err:
        sys.stderr.write('{0!s}\n'.format(err))
        sys.exit(print_usage(usage))

    for opt, arg in options:
        if opt == '-d':
            logger.setLevel(logging.DEBUG)
        else:
            sys.exit(print_usage(usage))

    for uuid in remainder:
        url_route = '/show/%s' % uuid
        status, data = delete_url(url_route=url_route)
        if status != 204:
            print 'Error: %s' % str(data['message'])


def update_config():
    usage = ('Usage: {0} '
             '[-i <http-client-address> ] '
             '[-u <http-user>:<http-password>] '
             '[-r <redis-server>] '
             '[-k <redis-key>] '
             '[-l <log-level>] '
             '[-c <cipher-key>\n'.format(PROGNAME))

    try:
        options, remainder = getopt.getopt(sys.argv[1:], 'i:u:r:k:l:c:', [])
    except getopt.GetoptError as err:
        sys.stderr.write('{0!s}\n'.format(err))
        sys.exit(print_usage(usage))

    for opt, arg in options:
        if opt == '-i':
            amf_config.http_client.server_address = arg
        elif opt == '-u':
            info = arg.split(':')
            amf_config.http_server.http_user = info[0]
            amf_config.http_server.http_password = info[1]
        elif opt == '-r':
            amf_config.redis_server.redis_server = arg
        elif opt == '-k':
            amf_config.redis_server.redis_key = arg
        elif opt == '-c':
            amf_config.redis_server.cipher_key = arg
        elif opt == '-l':
            amf_config.logger.log_level = arg
        else:
            sys.exit(print_usage(usage))

    with open(CONF_FILE, 'w+') as handle:
        amf_config.write(handle)
    handle.close()
