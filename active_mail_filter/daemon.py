# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import os
import sys
import getopt
import logging
import signal
import threading
from flask import Flask, make_response, jsonify
from flask_restful import Resource, Api, abort, reqparse
from flask_httpauth import HTTPBasicAuth

from active_mail_filter import amf_config
from active_mail_filter.imapuser import ImapUser
from active_mail_filter.mboxfolder import MboxFolder
from active_mail_filter.user_records import UserRecords
from active_mail_filter.user_records import UUID, USER, PASSWORD, MAILSERVER, EMAIL, SOURCE, TARGET

HOST = os.getenv('AMF_REDIS_SERVER', amf_config.redis_server.redis_server)

logger = logging.getLogger(amf_config.logging.logger)

userdb = UserRecords(host=HOST,
                     key=amf_config.redis_server.redis_key,
                     cipher=amf_config.redis_server.cipher_key)

app = Flask(__name__)
api = Api(app)
auth = HTTPBasicAuth()
ssl_context = (amf_config.http_server.cert_file, amf_config.http_server.pkey_file)

STOP_EVENT = threading.Event()
ARGUMENTS = [USER, PASSWORD, MAILSERVER, EMAIL, SOURCE, TARGET]


@auth.get_password
def get_password(username):
    password = None
    if username == amf_config.http_server.http_user:
        password = amf_config.http_server.http_password
    return password


@auth.error_handler
def unauthorized():
    return make_response(jsonify({'message': 'Unauthorized access'}), 403)


def get_decarators():
    decarators = []
    if amf_config.http_server.enable_auth.lower() in ['true', 'yes', 'on', '1']:
        decarators.append(auth.login_required)

    return decarators


def worker_thread(records):
    for rec in records:
        logger.debug('%s: moving %s to %s on %s', rec[USER], rec[SOURCE], rec[TARGET], rec[MAILSERVER])
        imap = ImapUser(rec[MAILSERVER], rec[USER], rec[PASSWORD],
                        to_folder=rec[TARGET], from_folder=rec[SOURCE])
        cnt, uids = imap.filter_mail()
        if cnt > 0:
            logger.info('%s: moved %d messages %s', threading.currentThread().getName(), cnt, str(uids))
        del imap


def sort_by_user(records):
    sorted_users = {}
    for rec in records:
        if rec[USER] not in sorted_users:
            sorted_users[rec[USER]] = [rec]
        else:
            sorted_users[rec[USER]].append(rec)

    logger.debug('found %d keys == %s', len(sorted_users), str(sorted_users.keys()))
    return sorted_users


def run_all_workers(users_jobs):
    mail_threads = []
    for u in users_jobs.keys():
        th = threading.Thread(name=u, target=worker_thread, args=(users_jobs[u],))
        mail_threads.append(th)
        th.start()

    is_alive = True
    while is_alive:
        for th in mail_threads:
            th.join(5)
            if th.isAlive():
                logger.debug('%s: is still alive' % th.getName())
                break
        else:
            is_alive = False


def run_mail_daemon():
    global STOP_EVENT
    while not STOP_EVENT.is_set():
        users = userdb.get_all_users()
        if len(users) > 0:
            mail_users = sort_by_user(users)
            run_all_workers(mail_users)
        else:
            logger.warning('No user records found')
        STOP_EVENT.wait(60.0)
    logger.info('filter_daemon: exiting')


def start_daemon_thread():
    global STOP_EVENT
    thread_list = list_all_threads()
    if 'filter_daemon' in thread_list:
        raise DaemonAlreadyRunning()

    logger.info('Starting filter process')
    STOP_EVENT.clear()
    th = threading.Thread(name='filter_daemon', target=run_mail_daemon)
    th.setDaemon(True)
    th.start()
    return th


def stop_daemon_thread():
    global STOP_EVENT
    thread_list = list_all_threads()
    if 'filter_daemon' not in thread_list:
        raise DaemonAlreadyStopped()

    logger.info('Stopping filter process')
    STOP_EVENT.set()


def list_all_threads():
    current_thread = threading.currentThread()
    thread_dict = {}
    for th in threading.enumerate():
        if th is current_thread:
            continue
        thread_dict[th.getName()] = str(th.isAlive())
    return thread_dict


def sigterm_handler(signum, frame):
    logger.info('Caught %d signal, shutting down', signum)
    if frame is not None and hasattr(frame, 'f_code'):
        logger.debug('Frame == %s', str(frame.f_code))
    try:
        stop_daemon_thread()
        logger.info('Stopping worker threads')
    except DaemonAlreadyStopped:
        pass

    for th in threading.enumerate():
        if 'filter_daemon' == th.getName():
            logger.info('Waiting for filter process to exit')
            th.join()
    sys.exit(0)


class DaemonAlreadyRunning(Exception):
    pass


class DaemonAlreadyStopped(Exception):
    pass


class ServerStatus(Resource):
    decorators = get_decarators()

    def __init__(self):
        self.counters = {'get': 0, 'put': 0, 'post': 0, 'delete': 0}
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('debug')
        super(ServerStatus, self).__init__()

    def get(self):
        self.counters['get'] += 1
        return {'data': list_all_threads()}

    def post(self):
        self.counters['post'] += 1
        args = self.parser.parse_args()
        settings = {}
        try:
            debug = args['debug'].lower() in ['1', 'true', 't', 'yes', 'y']
            settings['debug'] = debug
            logger.info('debug set to %s', str(debug))
            if debug:
                logger.setLevel(logging.DEBUG)
            else:
                logger.setLevel(logging.INFO)
        except AttributeError:
            pass

        return {'data': settings}, 201


class ServerStart(Resource):
    decorators = get_decarators()

    def __init__(self):
        self.counters = {'get': 0, 'put': 0, 'post': 0, 'delete': 0}
        super(ServerStart, self).__init__()

    def post(self):
        self.counters['post'] += 1
        try:
            start_daemon_thread()
        except DaemonAlreadyRunning:
            abort(400, message='server already running')

        return {'data': list_all_threads()}, 201


class ServerStop(Resource):
    decorators = get_decarators()

    def __init__(self):
        self.counters = {'get': 0, 'put': 0, 'post': 0, 'delete': 0}
        super(ServerStop, self).__init__()

    def post(self):
        self.counters['post'] += 1
        try:
            stop_daemon_thread()
        except DaemonAlreadyStopped:
            abort(400, message='server already stopped')

        return {'data': list_all_threads()}, 201


class RecordList(Resource):
    decorators = get_decarators()

    def __init__(self):
        self.counters = {'get': 0, 'put': 0, 'post': 0, 'delete': 0}
        super(RecordList, self).__init__()

    def get(self):
        self.counters['get'] += 1
        users = userdb.get_all_users()
        name_uuid = {}
        for u in users:
            if u[USER] not in name_uuid:
                name_uuid[u[USER]] = []
            name_uuid[u[USER]].append(u[UUID])
        return {'data': name_uuid}


class RecordInfo(Resource):
    decorators = get_decarators()

    def __init__(self):
        self.counters = {'get': 0, 'put': 0, 'post': 0, 'delete': 0}
        super(RecordInfo, self).__init__()

    def get(self, uuid):
        self.counters['get'] += 1
        try:
            user_record = userdb.get_user_by_uuid(uuid)
            del user_record[PASSWORD]
        except Exception as e:
            user_record = {}
            logger.error('get failed, %s', e.message)
            abort(404, message="get failed, {}".format(e.message))

        return {'data': user_record}

    def delete(self, uuid):
        self.counters['delete'] += 1
        try:
            user_record = userdb.get_user_by_uuid(uuid)
            logger.debug('delete %s/%s', user_record[USER], user_record[UUID])
            userdb.del_record(uuid)
        except Exception as e:
            logger.error('delete failed, %s', e.message)
            abort(404, message="delete failed, {}".format(e.message))

        return '', 204


class RecordAdd(Resource):
    decorators = get_decarators()

    def __init__(self):
        self.counters = {'get': 0, 'put': 0, 'post': 0, 'delete': 0}
        self.parser = reqparse.RequestParser()
        for arg in ARGUMENTS:
            self.parser.add_argument(arg)
        super(RecordAdd, self).__init__()

    def put(self):
        self.counters['put'] += 1
        args = self.parser.parse_args()
        for key in [USER, PASSWORD, MAILSERVER, EMAIL, SOURCE, TARGET]:
            if args[key] is None:
                logger.error('Missing [%s] keyword', key)
                abort(400, message='Missing [{}] keyword'.format(key))

        try:
            uuid = userdb.add_user(user=args[USER], email=args[EMAIL], password=args[PASSWORD],
                                   mail_server=args[MAILSERVER], source=args[SOURCE], target=args[TARGET])
            user_record = userdb.get_user_by_uuid(uuid)
            del user_record[PASSWORD]
        except Exception as e:
            user_record = None
            logger.error('add failed, %s', e.message)
            abort(400, message='add failed, {}'.format(e.message))

        return {'data': user_record}, 201


class RecordUpdate(Resource):
    decorators = get_decarators()

    def __init__(self):
        self.counters = {'get': 0, 'put': 0, 'post': 0, 'delete': 0}
        self.parser = reqparse.RequestParser()
        for arg in ARGUMENTS:
            self.parser.add_argument(arg)
        super(RecordUpdate, self).__init__()

    def put(self, uuid):
        self.counters['put'] += 1
        args = self.parser.parse_args()
        try:
            user_record = userdb.get_user_by_uuid(uuid)
            for key in args.keys():
                if args[key] is not None:
                    user_record[key] = args[key]

            userdb.update_user(record_uuid=uuid, user_record=user_record)
            del user_record[PASSWORD]
        except Exception as e:
            user_record = {}
            logger.error('update failed, %s', e.message)
            abort(400, message='update failed, {}'.format(e.message))

        return {'data': user_record}, 201


class FolderList(Resource):
    decorators = get_decarators()

    def __init__(self):
        self.counters = {'get': 0, 'put': 0, 'post': 0, 'delete': 0}
        self.parser = reqparse.RequestParser()
        for arg in ARGUMENTS:
            self.parser.add_argument(arg)
        super(FolderList, self).__init__()

    def get(self, uuid):
        self.counters['get'] += 1
        try:
            user_record = userdb.get_user_by_uuid(uuid)
            mbox = MboxFolder(user_record[MAILSERVER], user_record[USER], user_record[PASSWORD])
            folder_list = mbox.list_folders()
            mbox.disconnect()
        except Exception as e:
            folder_list = []
            logger.error('get folders failed, %s', e.message)
            abort(404, message='get folders failed, {}'.format(e.message))

        return {'data': {uuid: folder_list}}, 201

    def post(self):
        self.counters['post'] += 1
        args = self.parser.parse_args()
        for key in [USER, PASSWORD, MAILSERVER]:
            if args[key] is None:
                logger.error('Missing %s keyword', key)
                abort(400, message='Missing {} keyword'.format(key))

        try:
            mbox = MboxFolder(args[MAILSERVER], args[USER], args[PASSWORD])
            folder_list = mbox.list_folders()
            mbox.disconnect()
        except Exception as e:
            folder_list = []
            logger.error('list folders failed, %s', str(e.message))
            abort(400, message='list folders failed, {}'.format(str(e.message)))

        return {'data': {args[USER]: folder_list}}, 201


def run_daemon():
    try:
        options, remainder = getopt.getopt(sys.argv[1:], 'vs', [])
    except getopt.GetoptError as err:
        sys.stderr.write('%s\n' % err)
        sys.exit(1)

    for opt, arg in options:
        if opt == '-v':
            logger.setLevel(logging.DEBUG)
        elif opt == '-s':
            start_daemon_thread()
        else:
            sys.exit(1)

    signal.signal(signal.SIGTERM, sigterm_handler)

    api.add_resource(RecordInfo, '/show/<string:uuid>')
    api.add_resource(RecordList, '/list')
    api.add_resource(RecordAdd, '/add')
    api.add_resource(RecordUpdate, '/update/<string:uuid>')
    api.add_resource(FolderList, '/folders', '/folders/<string:uuid>')
    api.add_resource(ServerStatus, '/')
    api.add_resource(ServerStart, '/start')
    api.add_resource(ServerStop, '/stop')

    if amf_config.getboolean('http_server', 'use_ssl'):
        app.run(host=amf_config.http_server.listen_address, ssl_context=ssl_context,
                port=amf_config.getint('http_server', 'listen_port'))
    else:
        app.run(host=amf_config.http_server.listen_address,
                port=amf_config.getint('http_server', 'listen_port'))
