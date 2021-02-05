""" This is a core library which will execute commands on interactive cortxcli"""

import logging
import time
from commons.helpers.host import Host


class CortxCliClient:
    """
    This class is responsible to establish connection  to CSM server and execute commands on interactive cortxcli
    """

    def __init__(self, host, username, password, port=22):
        """
        Initialize credentials of CSM server
        :param str host: host/ip of CSM server
        :param str username: username of CSM server
        :param str password: password of CSM server
        :param int port: port number
        """
        self.log = logging.getLogger(__name__)
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.host_obj = Host(
            hostname=self.host,
            username=self.username,
            password=self.password)
        self.host_obj.connect(shell=True, port=self.port)
        self.session_obj = self.host_obj.shell_obj

    def execute_cli_commands(self, cmd: str, time_out: int = 300) -> str:
        """
        This function executes command on interactive shell on csm server and returns output
        :param str cmd: command to execute on shell
        :param int time_out: max time to wait for command execution output
        :return: output of executed command
        """
        output = ""
        self.log.info("Sending command: {}".format("".join([cmd, "\n"])))
        self.session_obj.send("".join([cmd, "\n"]))
        poll = time.time() + time_out  # max timeout
        while poll > time.time():
            time.sleep(2)
            if self.session_obj.recv_ready():
                output = output + \
                    self.session_obj.recv(9999).decode("utf-8")
            else:
                break

        return output

    def close_connection(self):
        """
        This function will close the ssh connection created in init
        :return: None
        """
        self.session_obj.close()
        self.host_obj.disconnect()
