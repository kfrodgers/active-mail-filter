# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import os
import sys
import logging
import time

from active_mail_filter import get_logger, read_configuration_file, trace
from active_mail_filter.imapuser import ImapUser
from active_mail_filter.mboxfolder import MboxFolder
from active_mail_filter.user_records import UserRecords
from active_mail_filter.stoppable_thread import StoppableThread
from active_mail_filter.user_records import UUID, USER, PASSWORD, MAILSERVER, EMAIL, SOURCE, TARGET

_CONF_ = read_configuration_file()

logger = get_logger()


def _get_userdb():
    if not hasattr(_get_userdb, 'userdb'):
        host = os.getenv('AMF_REDIS_SERVER', _CONF_['redis_server']['redis_server_address'])
        _get_userdb.userdb = UserRecords(host=host,
                                         key=_CONF_['redis_server']['redis_key'],
                                         cipher=_CONF_['redis_server']['cipher_key'])
    return _get_userdb.userdb


def worker_thread(rule_records):
    my_thread = StoppableThread.current_thread()
    mailbox = None if len(rule_records) == 0 else MboxFolder(rule_records[0][MAILSERVER],
                                                             rule_records[0][USER],
                                                             rule_records[0][PASSWORD])
    for rule in rule_records:
        if my_thread.is_stopped():
            break

        logger.debug('%s: moving %s to %s on %s', rule[USER], rule[SOURCE], rule[TARGET], rule[MAILSERVER])
        imap = ImapUser(mailbox, to_folder=rule[TARGET], from_folder=rule[SOURCE])
        cnt, moved_uids = imap.filter_mail()
        if cnt > 0:
            logger.info('%s: moved %d messages %s', my_thread.getName(), cnt, str(moved_uids))
        del imap

    if mailbox is not None:
        mailbox.disconnect()


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
                if th.elapsed_time() > 900:
                    th.kill()
                    logger.error('%s: Thread appears hung, killing', th.getName())
                    mail_threads.remove(th)
                break
        else:
            is_alive = False


def run_mail_daemon():
    my_thread = StoppableThread.current_thread()
    while not my_thread.is_stopped():
        users = _get_userdb().get_all_users()
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


def get_server_status():
    return {'data': list_all_threads()}


def server_status_update(debug='false'):
    debug_flag = debug.lower() in ['1', 'true', 't', 'yes', 'y']
    logger.info('debug set to %s', str(debug))
    if debug_flag:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    return {'data': list_all_threads()}, 201


def server_start():
    try:
        start_daemon_thread()
    except DaemonAlreadyRunning:
        return 'server already running', 400

    return {'data': list_all_threads()}, 201


def server_stop():
    try:
        th = stop_daemon_thread()
        th.join()
    except DaemonAlreadyStopped:
        return 'server already stopped', 400

    return {'data': list_all_threads()}, 201


def user_records_list():
    users = _get_userdb().get_all_users()
    email_info = {}
    for u in users:
        email = u[EMAIL]
        if email not in email_info:
            email_info[email] = []
        del u[PASSWORD]
        email_info[email].append(u)
    return {'data': email_info}


def user_record_get_by_uuid(uuid):
    try:
        user_record = _get_userdb().get_user_by_uuid(uuid)
        del user_record[PASSWORD]
    except Exception as e:
        logger.error('get failed, %s', e.message)
        return 'get failed, {}'.format(e.message), 404
    
    return {'data': user_record}


def user_record_add(user, email, password, mail_server, source, target):
    try:
        mbox = MboxFolder(mail_server, user, password)
        mbox.disconnect()

        uuid = _get_userdb().add_user(user=user, email=email, password=password,
                                      mail_server=mail_server, source=source, target=target)
        user_record = _get_userdb().get_user_by_uuid(uuid)
        del user_record[PASSWORD]
    except Exception as e:
        logger.error('add failed, %s', e.message)
        return 'add failed, {}'.format(e.message), 400

    return {'data': user_record}, 201


def user_record_delete(uuid, password):
    try:
        user_record = _get_userdb().get_user_by_uuid(uuid)
        mbox = MboxFolder(user_record[MAILSERVER], user_record[USER], password)
        mbox.disconnect()
        logger.debug('delete %s/%s', user_record[USER], user_record[UUID])
        _get_userdb().del_record(uuid)
    except Exception as e:
        logger.error('delete failed, %s', e.message)
        return 'delete failed, {}'.format(e.message), 400

    return {'data': uuid}, 201


def user_record_update(uuid, **kwargs):
    try:
        user_record = _get_userdb().get_user_by_uuid(uuid)
        for key in kwargs.keys():
            user_record[key] = kwargs[key]

        mbox = MboxFolder(user_record[MAILSERVER], user_record[USER], user_record[PASSWORD])
        mbox.disconnect()

        _get_userdb().update_user(record_uuid=uuid, user_record=user_record)
        del user_record[PASSWORD]
    except Exception as e:
        logger.error('update failed, %s', e.message)
        return 'update failed, {}'.format(e.message), 400

    return {'data': user_record}, 201


def folder_list_by_uuid(uuid):
    try:
        user_record = _get_userdb().get_user_by_uuid(uuid)
        mbox = MboxFolder(user_record[MAILSERVER], user_record[USER], user_record[PASSWORD])
        folder_dict = mbox.list_folder_counts()
        mbox.disconnect()
    except Exception as e:
        logger.error('get folders failed, %s', e.message)
        return 'get folders failed, {}'.format(e.message), 404

    return {'data': folder_dict}


def folder_list_by_user(user, password, mail_server):
    try:
        mbox = MboxFolder(mail_server, user, password)
        folder_dict = mbox.list_folder_counts()
        mbox.disconnect()
    except Exception as e:
        logger.error('list folders failed, %s', str(e.message))
        return 'list folders failed, {}'.format(str(e.message)), 404

    return {'data': folder_dict}
