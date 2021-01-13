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
from gevent import Timeout
from gevent.queue import Queue
from gevent.pool import Pool
#from queue import Queue
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

    def __init__(self,*args, run=None, thread_id=None, thread_name=None, thread_q=None):
        """
        Constructor
        """
        super().__init__(run,args)
        if thread_q is not None:
            self.queue = thread_q
        else:
            self.queue = Queue()
        self.thread_id = thread_id
        # self.threads = list()
        self.thread_name = thread_name

    def _run(self):
        """Build some CPU-intensive tasks to run via multiprocessing here.
        and Return some information back through multiprocessing.Queue
        """
        #result = connection_io()
        self._action()

    def _action(self) -> None:
        """
         self.thread_id is id of thread passed from calling function.
         self.name is an attribute of multiprocessing.Process
        """
        self.queue.put("Thread id={0} is called '{1}'".format(self.thread_id, self.name))

    def terminate(self) -> None:
        """ wait until queue is empty and terminate threads """
        self.queue.join()
        for p in self.threads:
            p.terminate()


class GThread(Multithreading):
    queue = Queue()

    def __init__(self, thread_id=None):
        super(GThread, self).__init__(thread_id)
        logger.debug("Creating GThread Object")

    def _run(self,message=None):
        logger.debug(message)
        super()._run()

    @staticmethod
    def join() -> List:
        """
        Waiting for all threads to complete
        return: List of finished threads
        """
        logger.debug(threads)
        logger.debug("Waiting for all threads to complete\n")
        gevent.joinall(threads)

    @staticmethod
    def terminate() -> Tuple:
        """ wait until queue is empty and terminate threads """
        GThread.join()
        logger.debug(threads)
        logger.debug("Terminating all processes once they finished with task\n")

        while not GThread.queue.empty():
            response = GThread.queue.get()
            logger.info("RESULT: {0}".format(GThread.queue.get()))  # get results from the queue...
        if GThread.queue.empty():
            return True, "Threading Finished"
        else:
            return False, "Error"

