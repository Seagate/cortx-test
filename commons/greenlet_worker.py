# -*- coding: utf-8 -*-
# !/usr/bin/python
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#
"""Module to support greenlet threading and pool capabilities. """
import logging
import sys

from typing import List, Tuple, Any, Optional
import gevent

from gevent import Greenlet
from gevent.queue import Queue
from gevent.pool import Pool
from gevent.pool import Group


logger = logging.getLogger(__name__)
if sys.platform == "win32":
    # Add stdout handler, with level DEBUG
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

threads = list()


class GreenletThread(Greenlet):
    """Class to Create Greenlet Multi-threading Objects and used to further extending child classes. """
    queue = Queue()

    def __init__(
            self,
            *args: Optional,
            run: Any = None,
            **kwargs: Optional) -> None:
        """
        if run is None then _run will be executed
        *args and *kwargs will be passed to super constructor to execute thread method
        :type kwargs: object
        :param args: collection of function parameter.
        :type tuple:  packed in tuple.
        :param run: name of the function passed in thread for execution.
        :type object:  The callable object to run. If not given, this object's
            `_run` method will be invoked (typically defined by subclasses)..
        :param thread_id: thread number associated with thread in execution.
        :type integer:  assigned as per sequence of execution.
        :param thread_q: collection of thread data in fifo .
        :type Queue:  Gevent queue.
        :param kwargs: collection of keyword function parameter.
        :type dict:  packed in dictionary.
        :return: None.
        :rtype: None.

        """
        super().__init__(run, *args, **kwargs)
        logger.debug("Creating GThread Object")
        self.responses = dict()  # Collecting Thread name and Thread Result/Return response
        self.feed() # Adding thread in queue for keeping track of threads execution

    def _run(self, message=None) -> Any:
        """Build some IO Bound tasks to run via multithreading here.
        and Return some information back.
        Subclasses may override this method to take any number of
        arguments and keyword arguments.
        """
        logger.info(message)

    def feed(self) -> None:
        """
         self.name is an attribute of thread
        """
        GreenletThread.queue.put(
            "Thread name is: '{0}'".format(self.name))

    @staticmethod
    def receive() -> Any:
        """
        :return: None.
        :rtype: None.
        """
        return GreenletThread.queue.get()

    def observer(self):
        """
        Define observer thread capabilities in subclass
        """
        raise NotImplementedError("observer needs to be implemented")

    def worker(self):
        """
        :return: None.
        :rtype: None.
        """
        raise NotImplementedError("worker needs to be implemented")

    @staticmethod
    def join() -> None:
        """
        Operating on list/collection of executing thread objects
        Waiting for all threads to complete.
        Collecting list of finished threads and their results.
        :return: None.
        :rtype: None.
        """
        logger.debug("Waiting for all threads to complete\n")
        logger.debug(threads)
        gevent.joinall(threads)
        logger.debug("All Threads execution is completed")
        GreenletThread.responses = {thread.name: thread.value for thread in threads}

    @staticmethod
    def terminate() -> Tuple[bool, List]:
        """ wait until queue is empty and terminate threads

        :return: Collection of Boolean with list of thread responses
        :rtype: tuple containing bool and List
        """
        GreenletThread.join()
        logger.debug(
            "Terminating all processes once they finished with task\n")
        while not GreenletThread.queue.empty():
            # get results from the queue...
            logger.info("RESULT: {0}".format(GreenletThread.receive()))
        if GreenletThread.queue.empty():
            return True, GreenletThread.responses

        return False, GreenletThread.responses


class GeventPool(object):

    def __init__(self, no_of_threads: int) -> None:
        """
        :param no_of_threads: size of thread pool
        """
        self.pool = Pool(no_of_threads)
        self.group = Group()
        self.responses = dict()

    def add_handler(self, func: Any, args: Any) -> None:
        """
        method to check pool capability and spawn/group threads
        :param func: function need to be spawned
        :param args: function arguments needs to be passed to work on
        :return: None
        """
        if not self.pool.full():
            self.spawn(func, args)
        else:
            raise Exception("At maximum pool size")

    def spawn(self, func: Any, args: Any) -> None:
        """
        :param func: method need to be operated with threads
        :param args: function arguments
        :return: None
        """
        g_obj = self.pool.spawn(func, args)
        threads.append(g_obj)
        self._group(g_obj)

    def _group(self, g_obj: object) -> None:
        """
        :param g: spawn object needs to be added in group
        :return: None
        """
        self.group.add(g_obj)

    def join_group(self) -> None:
        """
        waiting all threads to complete
        :return: None
        """
        logger.debug("Waiting for all threads to complete\n")
        self.group.join()
        logger.debug("All Threads execution is completed")
        self.responses = {g.name: g.value for g in threads}

    def pool_map(self,func: object, args: Any) -> None:
        """
        :param func: method need to be operated in thread
        :param args: function arguments
        :return: None
        """
        self.pool.imap_unordered(func, args)

    def shutdown(self) -> None:
        """
        Shutdown or kill thread pool
        :return: None
        """
        self.pool.kill()

    def result(self) -> dict:
        """
        :return: thread execution result
        """
        return self.responses

