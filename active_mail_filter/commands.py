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
    sys.stderr.write('Usage: %s %s\n' % (PROGNAME, usage))
    return 2


def list_rules():
    usage = '[-u <username>] '

    format_string = '%-37s %-20s %-15s %-10s %-10s\n'

    try:
        options, remainder = getopt.getopt(sys.argv[1:], 'u:', [])
    except getopt.GetoptError as err:
        sys.stderr.write('%s\n' % err)
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
            sys.stderr.write('Error: %s\n' % str(data['message']))
        else:
            sys.stderr.write('Error: %s\n' % str(data))
        sys.exit(status)
    users = data['data']

    sys.stdout.write(format_string % ('UUID', 'User', 'Server', 'Source', 'Target'))
    for name in users.keys():
        if user is not None and user != name:
            continue
        for uuid in users[name]:
            url_route = '/show/%s' % uuid
            status, data = get_url(url_route=url_route)
            if status != 200:
                sys.stderr.write('%s\n' % str(data))
                sys.exit(status)
            rec = data['data']
            sys.stdout.write(format_string % (rec['uuid'], rec['user'],
                                              rec['mail_server'], rec['source'], rec['target']))


def start_daemon():
    do_start_stop_daemon(command='/start')


def stop_daemon():
    do_start_stop_daemon(command='/stop')


def do_start_stop_daemon(command):
    usage = '[-v] '

    try:
        options, remainder = getopt.getopt(sys.argv[1:], 'v', [])
    except getopt.GetoptError as err:
        sys.stderr.write('%s\n' % err)
        sys.exit(print_usage(usage))

    for opt, arg in options:
        if opt == '-v':
            logger.setLevel(logging.DEBUG)
        else:
            sys.exit(print_usage(usage))

    status, data = post_url(url_route=command, params={})
    if status != 201:
        sys.stderr.write('Error: %s\n' % str(data['message']))

    status, data = get_url(url_route='/')
    if status != 200:
        sys.stderr.write('Error: %s\n' % str(data['message']))
    else:
        procs = data['data']
        for p in procs.keys():
            sys.stdout.write('%s thread is running\n' % str(p))


def print_folders(folders):
    sys.stderr.write('Valid folders are...\n')
    for f in sorted(folders):
        sys.stderr.write('\t%s\n' % f)


def check_folders(user, password, mail_server, source, target):
    params = {'user': user,
              'password': password,
              'mail_server': mail_server}

    status, data = post_url(url_route='/folders', params=params)
    if status != 201:
        sys.stderr.write('Error: %s\n' % str(data['message']))
        sys.exit(status)

    # Special checks because inbox folder name is case insensitive
    folders = data['data'][params['user']]
    if source.lower() != 'inbox' and source not in folders:
        sys.stderr.write('%s: Invalid source folder\n' % source)
        print_folders(folders)
        sys.exit(1)

    # can't use inbox, trash, sent or drafts as target folder
    excluded_folders = ['inbox', 'trash', 'sent', 'sent mail', 'draft', 'drafts']
    if target.lower() in excluded_folders or target not in folders:
        sys.stderr.write('%s: Invalid target folder\n' % target)
        print_folders(folders)
        sys.exit(1)


def add_rule():
    usage = ('-u <username> '
             '-p <password> '
             '-e <email> '
             '-i <imap-server> '
             '-s <source-folder> '
             '-t <target-folder> ')

    try:
        options, remainder = getopt.getopt(sys.argv[1:], 'du:p:e:i:s:t:', [])
    except getopt.GetoptError as err:
        sys.stderr.write('%s\n' % err)
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
        sys.stderr.write('Error: %s\n' % str(data['message']))
        sys.exit(status)

    sys.stdout.write('%s\n' % data['data']['uuid'])


def modify_rule():
    usage = ('-U <uuid> '
             '-u <username> '
             '-p <password> '
             '-e <email> '
             '-i <imap-server> '
             '-s <source-folder> '
             '-t <target-folder> ')

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
        sys.stderr.write('%s\n' % str(data))
        sys.exit(status)

    old_params = data['data']
    for key in params.keys():
        if key in old_params and params[key] is None:
            params[key] = old_params[key]

    check_folders(params['user'], params['password'], params['mail_server'],
                  params['source'], params['target'])

    url_route = '/update/%s' % uuid
    status, data = put_url(url_route=url_route, params=params)
    if status != 201:
        sys.stderr.write('Error: %s\n' % str(data['message']))
        sys.exit(status)

    sys.stdout.write('%s\n' % data['data']['uuid'])


def delete_rule():
    usage = 'uuid [uuid2 uuid3 ...] '
    try:
        options, remainder = getopt.getopt(sys.argv[1:], 'd', [])
    except getopt.GetoptError as err:
        sys.stderr.write('%s\n' % err)
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
            sys.stderr.write('Error: %s\n' % str(data['message']))


def update_config():
    usage = ('[-v] '
             '[-i <http-client-address> ] '
             '[-u <http-user>:<http-password>] '
             '[-r <redis-server>] '
             '[-k <redis-key>] '
             '[-l <log-level>] '
             '[-c <cipher-key> ')

    try:
        options, remainder = getopt.getopt(sys.argv[1:], 'vi:u:r:k:l:c:', [])
    except getopt.GetoptError as err:
        sys.stderr.write('%s\n' % err)
        sys.exit(print_usage(usage))

    verbose = False
    for opt, arg in options:
        if opt == '-v':
            verbose = True
        elif opt == '-i':
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

    if verbose:
        amf_config.write(sys.stdout)

    try:
        with open(CONF_FILE, 'w+') as handle:
            amf_config.write(handle)
        handle.close()
    except IOError as e:
        sys.stderr.write('Error: %s\n' % str(e))
