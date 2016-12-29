# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import os
import sys
import getopt
import logging
import time
import signal
from flask import Flask, make_response, jsonify
from flask_cors import CORS
from flask_restful import Resource, Api, abort, reqparse
from flask_httpauth import HTTPBasicAuth

from active_mail_filter import get_logger, read_configuration_file, trace
from active_mail_filter.imapuser import ImapUser
from active_mail_filter.mboxfolder import MboxFolder
from active_mail_filter.user_records import UserRecords
from active_mail_filter.stoppable_thread import StoppableThread
from active_mail_filter.user_records import UUID, USER, PASSWORD, MAILSERVER, EMAIL, SOURCE, TARGET

_CONF_ = read_configuration_file()
HOST = os.getenv('AMF_REDIS_SERVER', _CONF_.redis_server.redis_server_address)

logger = get_logger()

userdb = UserRecords(host=HOST,
                     key=_CONF_.redis_server.redis_key,
                     cipher=_CONF_.redis_server.cipher_key)

app = Flask(__name__)
cors = CORS(app)
api = Api(app)
auth = HTTPBasicAuth()
ssl_context = (_CONF_.http_server.cert_file, _CONF_.http_server.pkey_file)

ARGUMENTS = [USER, PASSWORD, MAILSERVER, EMAIL, SOURCE, TARGET]


@auth.get_password
def get_password(username):
    password = None
    if username == _CONF_.general.http_user:
        password = _CONF_.general.http_password
    return password


@auth.error_handler
def unauthorized():
    return make_response(jsonify({'message': 'Unauthorized access'}), 403)


def get_decarators():
    decarators = []
    if _CONF_.general.http_enable_auth.lower() in ['true', 'yes', 'on', '1']:
        decarators.append(auth.login_required)

    return decarators


def worker_thread(rule_records):
    my_thread = StoppableThread.current_thread()
    for rule in rule_records:
        if my_thread.is_stopped():
            break

        logger.debug('%s: moving %s to %s on %s', rule[USER], rule[SOURCE], rule[TARGET], rule[MAILSERVER])
        imap = ImapUser(rule[MAILSERVER], rule[USER], rule[PASSWORD],
                        to_folder=rule[TARGET], from_folder=rule[SOURCE])
        cnt, moved_uids = imap.filter_mail()
        if cnt > 0:
            logger.info('%s: moved %d messages %s', my_thread.getName(), cnt, str(moved_uids))
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
        th = StoppableThread(name=u, target=worker_thread, args=(users_jobs[u],))
        mail_threads.append(th)
        th.start()

    is_alive = True
    while is_alive:
        for th in mail_threads:
            th.join(5)
            if th.is_alive():
                trace('%s: is still alive' % th.getName())
                if th.elapsed_time() > 300:
                    th.kill()
                    logger.error('%s: Thread appears hung, killing', th.getName())
                    mail_threads.remove(th)
                break
        else:
            is_alive = False


def run_mail_daemon():
    my_thread = StoppableThread.current_thread()
    while not my_thread.is_stopped():
        users = userdb.get_all_users()
        if len(users) > 0:
            mail_users = sort_by_user(users)
            start = time.time()
            run_all_workers(mail_users)
            logger.debug('run_all_workers elaspsed time = %f', time.time() - start)
        else:
            logger.debug('No user records found')
        my_thread.wait(60.0)
    logger.info('filter_daemon: exiting')


def start_daemon_thread():
    try:
        StoppableThread.find_by_name('filter_daemon')
        raise DaemonAlreadyRunning()
    except LookupError:
        pass

    logger.info('Starting filter process')
    daemon_thread = StoppableThread(name='filter_daemon', target=run_mail_daemon)
    daemon_thread.setDaemon(True)
    daemon_thread.start()
    return daemon_thread


def stop_daemon_thread():
    try:
        daemon_thread = StoppableThread.find_by_name('filter_daemon')
        logger.info('Stopping filter process')
        for th in StoppableThread.enumerate():
            th.stop()

    except LookupError:
        raise DaemonAlreadyStopped()

    return daemon_thread


def list_all_threads():
    thread_dict = {}
    for th in StoppableThread.enumerate():
        thread_dict[th.getName()] = str(th.isAlive())
    return thread_dict


def sigterm_handler(signum, frame):
    logger.info('Caught signal %d, shutting down', signum)
    trace('Frame = %s', str(frame))
    try:
        daemon_thread = stop_daemon_thread()
        logger.info('Waiting for filter process to exit')

        daemon_thread.join(15)
        for th in StoppableThread.enumerate():
            if th != daemon_thread and th.is_alive():
                logger.warning('Killing thread %s', th.getName())
                th.kill()

        if daemon_thread.is_alive():
            logger.info('Waiting for filter process to die')
            daemon_thread.join()
    except DaemonAlreadyStopped:
        pass

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
            th = stop_daemon_thread()
            th.join()
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
        email_info = {}
        for u in users:
            email = u[EMAIL]
            if email not in email_info:
                email_info[email] = []
            del u[PASSWORD]
            email_info[email].append(u)
        return {'data': email_info}


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


class RecordDelete(Resource):
    decorators = get_decarators()

    def __init__(self):
        self.counters = {'get': 0, 'put': 0, 'post': 0, 'delete': 0}
        self.parser = reqparse.RequestParser()
        for arg in ARGUMENTS:
            self.parser.add_argument(arg)
        super(RecordDelete, self).__init__()

    def post(self, uuid):
        self.counters['delete'] += 1
        try:
            args = self.parser.parse_args()
            if args[PASSWORD] is None:
                logger.error('Missing %s keyword', PASSWORD)
                raise Exception('Missing {} keyword'.format(PASSWORD))

            user_record = userdb.get_user_by_uuid(uuid)
            mbox = MboxFolder(user_record[MAILSERVER], user_record[USER], args[PASSWORD])
            mbox.disconnect()
            logger.debug('delete %s/%s', user_record[USER], user_record[UUID])
            userdb.del_record(uuid)
        except Exception as e:
            logger.error('delete failed, %s', e.message)
            abort(400, message="delete failed, {}".format(e.message))

        return {'data': uuid}, 201


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
    api.add_resource(RecordDelete, '/delete/<string:uuid>')
    api.add_resource(RecordUpdate, '/update/<string:uuid>')
    api.add_resource(FolderList, '/folders', '/folders/<string:uuid>')
    api.add_resource(ServerStatus, '/')
    api.add_resource(ServerStart, '/start')
    api.add_resource(ServerStop, '/stop')

    if _CONF_.getboolean('general', 'use_ssl'):
        app.run(host=_CONF_.http_server.listen_address, ssl_context=ssl_context,
                port=_CONF_.getint('general', 'http_server_port'))
    else:
        app.run(host=_CONF_.http_server.listen_address,
                port=_CONF_.getint('general', 'http_server_port'))
