import json
import threading
import getpass
from collections import deque
from typing import Any


def get_jira_credential() :
    jira_id = ''
    jira_pwd = ''
    try :
        jira_id = os.environ['JIRA_ID']
        jira_pwd = os.environ['JIRA_PASSWORD']
    except KeyError :
        print("JIRA credentials not found in environment")
        jira_id = input("JIRA username: ")
        jira_pwd = getpass.getpass("JIRA password: ")
    return jira_id, jira_pwd


def parse_json(json_file) :
    """
    Parse given json file
    """
    with open(json_file, "r") as read_file :
        json_dict = json.load(read_file)

    cmd = ''
    run_using = ''
    # Execution priority is given to test name first then to file name and at last to tag.
    if json_dict['test_name'] != '' :
        cmd = json_dict['test_name']
        run_using = 'test_name'
    elif json_dict['file_name'] != '' :
        cmd = json_dict['file_name']
        run_using = 'file_name'
    elif json_dict['tag'] != '' :
        cmd = json_dict['tag']
        run_using = 'tag'
    return json_dict, cmd, run_using


def get_cmd_line(cmd, run_using, html_report, log_cli_level) :
    if run_using == 'tag' :
        cmd = '-m ' + cmd
    result_html_file = '--html={}'.format(html_report)
    log_cli_level_str = '--log-cli-level={}'.format(log_cli_level)
    cmd_line = ['pytest', log_cli_level_str, result_html_file, cmd]
    return cmd_line


class LRUCache:
    """
    Inmemory cache for storing test id and test node information
    """
    def __init__(self, size: int) -> None:
        self.maxsize = size
        self.fifo = deque()
        self.table = dict()
        self._lock = threading.Lock()

    def store(self, key: str, value: str) -> None:
        self._lock.acquire()
        if not self.table.has_key(key):
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
