# -*- coding: utf-8 -*-
# !/usr/bin/python
#
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
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
import secrets
import threading
import random
import uuid
import logging
from collections import deque
from typing import Tuple
from typing import Optional
from typing import Any
from config import CMN_CFG
from libs.di.di_run_man import RunDataCheckManager
from libs.di.di_mgmt_ops import ManagementOPs

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


def run_global_io_async(args, event):
    mgm_ops = ManagementOPs()
    secret_range = random.SystemRandom()
    prefs_dict = {'prefix_dir': f"global_io_{uuid.uuid4().hex}"}
    while not event.is_set():
        try:
            users = mgm_ops.create_account_users(
                nusers=5, use_cortx_cli=False)
            users_buckets = mgm_ops.create_buckets(
                nbuckets=2, users=users)
        except BaseException as error:
            continue
        file_counts = secret_range.randint(10, 15)
        run_data_check_obj = RunDataCheckManager(users=users_buckets)
        run_data_check_obj.start_io_async(
            users=users_buckets, buckets=None, files_count=file_counts,
            prefs=prefs_dict)
        run_data_check_obj.stop_io_async(
            users=users_buckets, di_check=args.data_integrity_chk,
            eventual_stop=True)


def start_parallel_io(args):
    """
    Function to start DI using RunDataManager in parallel
    :param args: contains testrunner args
    :return: threading event object to stop loop of run_gloabal_io_async
    """
    event = threading.Event()
    thread = threading.Thread(
        target=run_global_io_async, args=(args, event))
    thread.start()
    return thread, event


def stop_parallel_io(io_thread, stop):
    """
    Function to set stop event and join testrunner parallel IO thread
    :param io_thread: thread object
    :param stop: threading event object
    """
    stop.set()
    io_thread.join()


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


class InMemoryDB(LRUCache):
    """In memory storage"""

    def pop_one(self) -> tuple:
        """
        Pop one table entry randomly.
        """
        self._lock.acquire()
        keys = list(self.table.keys())
        if len(keys) == 0:
            self._lock.release()
            return False, False
        key = secrets.choice(keys)
        try:
            val = self.table.pop(key)
        finally:
            self._lock.release()
        return key, val
