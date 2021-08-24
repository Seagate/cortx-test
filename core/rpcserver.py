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
"""Threaded RPC Server implementation."""
import rpyc
from rpyc.utils.server import ThreadedServer
import sys
import threading
from threading import Thread
import time
import trace
import traceback

from core.runner import get_jira_credential
from commons.utils import jira_utils
from commons import constants as common_cnst


class RpcCalls(rpyc.Service):
    """
    RPC class to define functions which needs to be called as async rpc
    """

    @staticmethod
    def exposed_test_status_update(te_tkt, test_id, test_status):
        """
        Function to update test status in jira
        """
        jira_id, jira_pwd = get_jira_credential()
        task = jira_utils.JiraTask(jira_id, jira_pwd)
        task.update_test_jira_status(te_tkt, test_id, test_status)
        print('done ')

    @staticmethod
    def exposed_test_comment_update(test_run_id, test_id, comment):
        """
        Function to update log path as comment in jira
        """
        jira_id, jira_pwd = get_jira_credential()
        task = jira_utils.JiraTask(jira_id, jira_pwd)
        task.update_execution_details(test_run_id, test_id, comment)


def threaded_function():
    """
    Threaded server to start rpc
    """
    server = ThreadedServer(RpcCalls, port=common_cnst.RPC_PORT)
    server.start()


def get_rpc_server():
    """
    Get rpc server thread
    """
    thread = Thread(target=threaded_function)
    return thread
