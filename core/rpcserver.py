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
import sys
import threading
import traceback
import socketserver
from typing import Callable
from typing import Tuple
from xmlrpc.server import SimpleXMLRPCServer


class DispatchException(Exception):
    """
    Exception class for dispatch failures.
    """
    def __init__(self, msg):
        """
        Raise a DispatchException when method dispatching fails.
        """
        super(DispatchException).__init__(type(self))
        self.msg = "E: %s" % msg

    def __str__(self):
        return self.msg


class XMLRPCServer(socketserver.ThreadingMixIn, SimpleXMLRPCServer):
    """RPC Server attached to Drunner or Test Runner."""
    def __init__(self, *args, **kwargs):
        SimpleXMLRPCServer.__init__(self, *args, **kwargs)

    def _dispatch(self, method, params):
        """
        Dispatch method resolves the calling path to mapped function.
        :param method: method mapped
        :param params: Arguments of the method
        :return: returns the returns the serialized return value of dispatched method
        """
        try:
            return SimpleXMLRPCServer._dispatch(self, method, params)
        except DispatchException:
            print("".join(traceback.format_exception(*sys.exc_info())))
            raise


class Server(threading.Thread):
    """Server Thread to bootstrap XMLRPcServer"""
    def __init__(self, addr: Tuple, register_cb: Callable):
        self.port = addr[1]
        self.bind_int = addr[0]
        self.register_cb = register_cb
        self.server = XMLRPCServer((self.bind_int, int(self.port)),
                                   allow_none=True,
                                   logRequests=False)
        threading.Thread.__init__(self)

    def run(self):
        """Register the RPC methods and start the RPC server."""
        try:
            self.registercb(self.server)
            self.server.serve_forever()
        except Exception as error:
            print(str(error))
            traceback.print_exception(*sys.exc_info())
            sys.exit(0)  # used in child process and exits rpc process

