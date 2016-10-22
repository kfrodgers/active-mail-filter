# Copyright (c) 2016, Kevin Rodgers
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import logging
import threading
import time
import ctypes
from active_mail_filter import amf_config

logger = logging.getLogger(amf_config.logging.logger)


class StoppableThread(threading.Thread):
    def __init__(self, **kwargs):
        self.event = threading.Event()
        self.counter = 0
        self.has_been_killed = False
        self.lock = threading.Lock()
        threading.Thread.__init__(self, **kwargs)

    @staticmethod
    def current_thread():
        th = threading.currentThread()
        if not isinstance(th, StoppableThread):
            raise ValueError('%s: invalid type', str(type(th)))
        return th

    @staticmethod
    def enumerate():
        stoppable_threads = []
        for th in threading.enumerate():
            if isinstance(th, StoppableThread):
                stoppable_threads.append(th)
        return stoppable_threads

    @staticmethod
    def find_by_name(name):
        for th in threading.enumerate():
            if name == th.getName() and isinstance(th, StoppableThread):
                break
        else:
            raise LookupError('%s: thread not found', name)
        return th

    @staticmethod
    def sleep(seconds):
        time.sleep(seconds)

    def stop(self):
        self.event.set()

    def wait(self, timeout=None):
        self.event.wait(timeout=timeout)

    def set_active(self):
        self.lock.acquire()
        self.counter = 0
        self.lock.release()

    def is_active(self, intervals):
        self.lock.acquire()
        is_active = self.counter < intervals
        self.counter += 1
        self.lock.release()
        return is_active and self.is_alive()

    def kill(self):
        self.lock.acquire()
        if self.is_alive() and not self.has_been_killed:
            self.has_been_killed = True
            self.lock.release()

            self.stop()
            exc = ctypes.py_object(SystemExit)
            res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(self.ident), exc)
            if res == 0:
                raise SystemError("PyThreadState_SetAsyncExc bad thread, id=%s" % str(self.ident))
            elif res > 1:
                ctypes.pythonapi.PyThreadState_SetAsyncExc(self.ident, None)
                raise SystemError("PyThreadState_SetAsyncExc failed, res=%d" % res)
        else:
            self.lock.release()

    def is_stopped(self):
        return self.event.isSet()
