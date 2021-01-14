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
# -*- coding: utf-8 -*-
# !/usr/bin/python

import sys
import logging
import gevent
from gevent import Greenlet
from gevent.queue import Queue
from typing import List, Tuple, Any, Optional

logger = logging.getLogger(__name__)
if sys.platform == "win32":
    # Add stdout handler, with level DEBUG
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

threads = list()


class Multithreading(Greenlet):
    """
    Class to Create Greenlet Multi-threading Objects and used to further extending child classes
    """

    def __init__(
            self,
            *args : Optional,
            run: Any = None,
            thread_id: int = None,
            thread_q: object = None,
            **kwargs : Optional) -> None:
        """
        if run is None then _run will be executed
        *args and *kwargs will be passed to super constructor to execute thread method
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
        if thread_q is not None:
            self.queue = thread_q
        else:
            self.queue = Queue()
        self.thread_id = thread_id
        self._q_put()

    def _run(self) -> Any:
        """Build some CPU-intensive tasks to run via multiprocessing here.
        and Return some information back
        Subclasses may override this method to take any number of
        arguments and keyword arguments.
        """
        logger.info("Running GThrads")

    def _q_put(self) -> None:
        """
         self.thread_id is id of thread passed from calling function.
         self.name is an attribute of multiprocessing.Process
        """
        self.queue.put(
            "Thread id={0} and Thread name is: '{1}'".format(
                self.thread_id, self.name))

    def terminate(self) -> None:
        """ wait until queue is empty and terminate threads
            Method to overide and extend for child classes
         """
        pass


class GThread(Multithreading):
    queue = Queue()

    def __init__(self, *args, run=None, thread_id=None, **kwargs) -> None:
        super(
            GThread,
            self).__init__(
            *args,
            run=run,
            thread_id=thread_id,
            thread_q=GThread.queue,
            **kwargs)
        logger.debug("Creating GThread Object")
        self.responses = dict()  # Collecting Thread name and Thread Result/Return response

    def _run(self, message=None) -> Any:
        logger.debug(message)
        super()._run()

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
        GThread.responses = {thread.name: thread.value for thread in threads}

    @staticmethod
    def terminate() -> Tuple[bool, List]:
        """ wait until queue is empty and terminate threads """
        GThread.join()
        logger.debug(
            "Terminating all processes once they finished with task\n")
        while not GThread.queue.empty():
            # get results from the queue...
            logger.info("RESULT: {0}".format(GThread.queue.get()))
        if GThread.queue.empty():
            return True, GThread.responses
        else:
            return False, GThread.responses
