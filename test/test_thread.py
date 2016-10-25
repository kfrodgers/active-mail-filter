#! /usr/bin/python
# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import logging
from active_mail_filter import get_logger
from active_mail_filter.stoppable_thread import StoppableThread

logger = get_logger()
logger.setLevel(logging.DEBUG)


def worker(counter, interval):
    try:
        my_thread = StoppableThread.current_thread()
        for i in range(0, counter):
            my_thread.set_active()
            if my_thread.is_stopped():
                logger.debug('caught stop event')
                break
            logger.debug('worker counter == %d', i)
            my_thread.wait(interval)
    except Exception as e:
        logger.debug(e)


def test_nokill():
    counter = 10
    interval = 2
    th = StoppableThread(name='worker', target=worker, args=(counter, interval, ))
    logger.debug('starting thread')
    th.start()
    while th.is_alive():
        if not th.is_active(5):
            th.kill()
        th.join(1)
    logger.debug('thread done')


def test_kill():
    counter = 10
    interval = 10
    th = StoppableThread(name='worker', target=worker, args=(counter, interval, ))
    logger.debug('starting thread')
    th.start()

    th = StoppableThread.find_by_name('worker')
    while th.is_alive():
        if not th.is_active(2):
            th.kill()
        th.join(1)
    logger.debug('thread done')


def test_stop():
    counter = 10
    interval = 10
    th = StoppableThread(name='worker', target=worker, args=(counter, interval, ))
    logger.debug('starting thread')
    th.start()
    th = StoppableThread.find_by_name('worker')
    while th.is_alive():
        if not th.is_active(2):
            th.stop()
        th.join(1)
    logger.debug('thread done')

if __name__ == '__main__':
    try:
        test_kill()
        test_stop()
        test_nokill()
    except KeyboardInterrupt:
        pass
