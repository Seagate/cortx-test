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
"""Runner base file."""
import datetime
import getpass
import json
import os
import pathlib
import threading
import logging
from collections import deque
from typing import Tuple
from typing import Optional
from typing import Any
from config import CMN_CFG
from commons import params

LOGGER = logging.getLogger(__name__)


def get_jira_credential() -> Tuple[str, Optional[str]]:
    """
    Adapter function to get Jira Credentials.
    :return: Credentials Tuple
    """
    try:
        jira_id = os.environ['JIRA_ID']
        jira_pd = os.environ['JIRA_PASSWORD']
    except KeyError:
        print("JIRA credentials not found in environment")
        jira_id = input("JIRA username: ")
        jira_pd = getpass.getpass("JIRA password: ")
        os.environ['JIRA_ID'] = jira_id
        os.environ['JIRA_PASSWORD'] = jira_pd
    return jira_id, jira_pd


def get_db_credential() -> Tuple[str, Optional[str]]:
    """ Function to get DB credentials from env or common config or secret.json."""
    db_user = None
    db_pwd = None
    try:
        db_user = os.environ['DB_USER']
        db_pwd = os.environ['DB_PASSWORD']
    except KeyError:
        print("DB credentials not found in environment")
        try:
            getattr(CMN_CFG, 'db_user') and getattr(CMN_CFG, 'db_password')
            db_user, db_pwd = CMN_CFG.db_user, CMN_CFG.db_password
        except AttributeError as attr_err:
            LOGGER.exception(str(attr_err))
            db_user = input("DB username: ")
            db_pwd = getpass.getpass("DB password: ")
        os.environ['DB_USER'] = db_user
        os.environ['DB_PASSWORD'] = db_pwd
    return db_user, db_pwd


def parse_json(json_file):
    """
    Parse given json file.
    """
    with open(json_file, "r") as read_file:
        json_dict = json.load(read_file)

    cmd = ''
    run_using = ''
    # Execution priority is given to test name first then to file name and at last to tag.
    if json_dict['test_name'] != '':
        cmd = json_dict['test_name']
        run_using = 'test_name'
    elif json_dict['file_name'] != '':
        cmd = json_dict['file_name']
        run_using = 'file_name'
    elif json_dict['tag'] != '':
        cmd = json_dict['tag']
        run_using = 'tag'
    return json_dict, cmd, run_using


def get_cmd_line(cmd, run_using, html_report, log_cli_level):
    """
    Builds pytest command line
    :param cmd:
    :param run_using:
    :param html_report:
    :param log_cli_level:
    :return:
    """
    if run_using == 'tag':
        cmd = '-m ' + cmd
    result_html_file = '--html={}'.format(html_report)
    log_cli_level_str = '--log-cli-level={}'.format(log_cli_level)
    cmd_line = ['pytest', log_cli_level_str, result_html_file, cmd]
    return cmd_line


def cleanup():
    """
    This Fixture renames the the log/latest folder to a name with current timestamp
    and creates a folder named latest.
    :return:
    """
    cd = os.getcwd()
    root_dir = pathlib.Path(cd)
    log_dir = os.path.join(root_dir, 'log')
    now = str(datetime.datetime.now())
    now = now.replace(' ', '-')  # now has a space in timestamp
    now = now.replace(':', '_')
    if os.path.exists(log_dir) and os.path.isdir(log_dir):
        latest = os.path.join(log_dir, 'latest')
        if os.path.isdir(latest) and os.path.exists(latest):
            os.rename(latest, os.path.join(log_dir, now))
        os.makedirs(latest)
    else:
        os.makedirs(os.path.join(log_dir, 'latest'))


def create_test_details_file(te_ticket, test_tuple):
    """
    Create test details file
    """
    tp_details = dict()

    tp_details_file = os.path.join(os.getcwd(),
                                   params.LOG_DIR_NAME,
                                   params.JIRA_TEST_DETAILS_JSON)
    import pdb
    pdb.set_trace()
    with open(tp_details_file, 'w') as t_meta:
        # test_name, test_run_id
        item = dict()
        for test, run_id in test_tuple:
            item[test] = run_id
        tp_details[te_ticket] = item
        json.dump(tp_details, t_meta, ensure_ascii=False)


class LRUCache:
    """
    In memory cache for storing test id and test node information
    """

    def __init__(self, size: int) -> None:
        self.maxsize = size
        self.fifo = deque()
        self.table = dict()
        self._lock = threading.Lock()

    def store(self, key: str, value: str) -> None:
        """
        Stores the key and value and evicts left most old entry.
        :param key:
        :param value:
        """
        self._lock.acquire()
        if key not in self.table:
            self.fifo.append(key)
        self.table[key] = value

        if len(self.fifo) > self.maxsize:
            del_key = self.fifo.popleft()
            try:
                del self.table[del_key]
            except KeyError as ke:
                pass
        self._lock.release()

    def lookup(self, key: str) -> str:
        """
        Lookup cache for key.
        :param key:
        :return: val of entry
        """
        self._lock.acquire()
        try:
            val = self.table[key]
        finally:
            self._lock.release()
        return val

    def delete(self, key: str) -> None:
        """
        Removes the table entry. The fifo list entry is removed whenever we
        cache is full.
        """
        self._lock.acquire()
        try:
            del self.table[key]
        except KeyError as ke:
            pass
        try:
            self.fifo.remove(key)
        except ValueError as ve:
            pass
        finally:
            self._lock.release()
