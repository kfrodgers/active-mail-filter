# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import os
import sys
import getopt
from active_mail_filter import read_configuration_file, write_configuration_file
from active_mail_filter.rest_client import get_url, put_url, post_url

PROGNAME = os.path.basename(sys.argv[0])


def print_usage(usage):
    sys.stderr.write('Usage: %s %s\n' % (PROGNAME, usage))
    return 2


def print_to_out(message):
    sys.stdout.write(message)


def print_to_err(message):
    sys.stderr.write(message)


def list_rules():
    usage = '[-u <username>] '

    format_string = '%-37s %-20s %-15s %-10s %-10s\n'

    try:
        options, remainder = getopt.getopt(sys.argv[1:], 'u:', [])
    except getopt.GetoptError as err:
        print_to_err('%s\n' % err)
        sys.exit(print_usage(usage))

    user = None
    for opt, arg in options:
        if opt == '-u':
            user = arg
        else:
            sys.exit(print_usage(usage))

    status, data = get_url(url_route='/api/users')
    if status != 200:
        if 'message' in data:
            print_to_err('Error: %s\n' % str(data['message']))
        else:
            print_to_err('Error: %s\n' % str(data))
        sys.exit(status)
    users = data['data']

    print_to_out(format_string % ('UUID', 'User', 'Server', 'Source', 'Target'))
    for name in users.keys():
        if user is not None and user != name:
            continue
        for rec in users[name]:
            print_to_out(format_string % (rec['uuid'], rec['user'],
                                          rec['mail_server'], rec['source'], rec['target']))


def start_daemon():
    do_start_stop_daemon(command='/api/start')


def stop_daemon():
    do_start_stop_daemon(command='/api/stop')


def do_start_stop_daemon(command):
    if len(sys.argv) > 1:
        sys.exit(print_usage(''))

    status, data = post_url(url_route=command, params={})
    if status != 201:
        print_to_err('Error: %r\n' % data)
    status, data = post_url(url_route='/api/status', params=dict(debug='true'))
    if status != 201:
        print_to_err('Error: %r\n' % data)
    else:
        procs = data['data']
        for p in procs.keys():
            print_to_out('%s thread is running\n' % str(p))


def print_folders(folders):
    print_to_err('Valid folders are...\n')
    for f in sorted(folders):
        print_to_err('\t%s\n' % f)


def check_folders(user, password, mail_server, source, target):
    params = {'user': user,
              'password': password,
              'mail_server': mail_server}

    status, data = get_url(url_route='/api/folders', params=params)
    if status != 201:
        print_to_err('Error: %s\n' % str(data['message']))
        sys.exit(status)

    # Special checks because inbox folder name is case insensitive
    folders = data['data'].keys()
    if source.lower() != 'inbox' and source not in folders:
        print_to_err('%s: Invalid source folder\n' % source)
        print_folders(folders)
        sys.exit(1)

    # can't use inbox, trash, sent or drafts as target folder
    excluded_folders = ['inbox', 'trash', 'sent', 'sent mail', 'draft', 'drafts']
    if target.lower() in excluded_folders or target not in folders:
        print_to_err('%s: Invalid target folder\n' % target)
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
        options, remainder = getopt.getopt(sys.argv[1:], 'u:p:e:i:s:t:', [])
    except getopt.GetoptError as err:
        print_to_err('%s\n' % err)
        sys.exit(print_usage(usage))

    user = None
    password = None
    email = None
    mail_server = None
    source = None
    target = None
    for opt, arg in options:
        if opt == '-u':
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

    status, data = put_url(url_route='/api/add', params=params)
    if status != 201:
        print_to_err('Error: %s\n' % str(data['message']))
        sys.exit(status)

    print_to_out('%s\n' % data['data']['uuid'])


def list_folders():
    usage = ('-u <username> '
             '-p <password> '
             '-i <imap-server> ')

    try:
        options, remainder = getopt.getopt(sys.argv[1:], 'u:p:i:', [])
    except getopt.GetoptError as err:
        print_to_err('%s\n' % err)
        sys.exit(print_usage(usage))

    user = None
    password = None
    mail_server = None
    for opt, arg in options:
        if opt == '-u':
            user = arg
        elif opt == '-p':
            password = arg
        elif opt == '-i':
            mail_server = arg
        else:
            sys.exit(print_usage(usage))

    if None in [user, password, mail_server]:
        sys.exit(print_usage(usage))

    params = {'user': user,
              'password': password,
              'mail_server': mail_server}

    status, data = get_url(url_route='/api/folders', params=params)
    if status != 201:
        print_to_err('Error: %s\n' % str(data['message']))
        sys.exit(status)

    for folder in sorted(data['data'], reverse=True):
        if data['data'][folder]:
            print_to_out('%s\n' % folder)
        else:
            print_to_out('%s (empty)\n' % folder)


def modify_rule():
    usage = ('-U <uuid> '
             '-u <username> '
             '-p <password> '
             '-e <email> '
             '-i <imap-server> '
             '-s <source-folder> '
             '-t <target-folder> ')

    try:
        options, remainder = getopt.getopt(sys.argv[1:], 'U:u:p:e:i:s:t:', [])
    except getopt.GetoptError as err:
        print_to_err('{0!s}\n'.format(err))
        sys.exit(print_usage(usage))

    uuid = None
    user = None
    password = None
    email = None
    mail_server = None
    source = None
    target = None
    for opt, arg in options:
        if opt == '-U':
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
        print_to_err('%s\n' % str(data))
        sys.exit(status)

    old_params = data['data']
    for key in params.keys():
        if key in old_params and params[key] is None:
            params[key] = old_params[key]

    check_folders(params['user'], params['password'], params['mail_server'],
                  params['source'], params['target'])

    url_route = '/api/update/%s' % uuid
    status, data = put_url(url_route=url_route, params=params)
    if status != 201:
        print_to_err('Error: %s\n' % str(data['message']))
        sys.exit(status)

    print_to_out('%s\n' % data['data']['uuid'])


def delete_rule():
    usage = ('-p <password> '
             'uuid [uuid2 uuid3 ...] ')

    try:
        options, remainder = getopt.getopt(sys.argv[1:], 'U:u:p:e:i:s:t:', [])
    except getopt.GetoptError as err:
        print_to_err('{0!s}\n'.format(err))
        sys.exit(print_usage(usage))

    password = None
    for opt, arg in options:
        if opt == '-p':
            password = arg
        else:
            sys.exit(print_usage(usage))

    if password is None or len(remainder) < 1:
        sys.exit(print_usage(usage))

    params = {'password': password}
    for uuid in remainder:
        url_route = '/api/delete/%s' % uuid
        status, data = post_url(url_route=url_route, params=params)
        if status != 201:
            print_to_err('Error: %s\n' % str(data['message']))


def update_config():
    usage = ('[-s] '
             '[-i <http-client-address> ] '
             '[-u <http-user>:<http-password>] '
             '[-r <redis-server>] '
             '[-k <redis-key>] '
             '[-l <log-level>] '
             '[-c <cipher-key> ')

    try:
        options, remainder = getopt.getopt(sys.argv[1:], 'vi:u:r:k:l:c:', [])
    except getopt.GetoptError as err:
        print_to_err('%s\n' % err)
        sys.exit(print_usage(usage))

    conf = read_configuration_file()

    verbose = True
    for opt, arg in options:
        if opt == '-s':
            verbose = False
        elif opt == '-i':
            conf.general.http_server_address = arg
        elif opt == '-u':
            info = arg.split(':')
            conf.general.http_user = info[0]
            conf.general.http_password = info[1]
        elif opt == '-r':
            conf.redis_server.redis_server_address = arg
        elif opt == '-k':
            conf.redis_server.redis_key = arg
        elif opt == '-c':
            conf.redis_server.cipher_key = arg
        elif opt == '-l':
            conf.general.log_level = arg
        else:
            sys.exit(print_usage(usage))

    if verbose:
        conf.write(sys.stdout)

    try:
        write_configuration_file(conf=conf)
    except IOError as e:
        print_to_err('Error: %s\n' % str(e))
