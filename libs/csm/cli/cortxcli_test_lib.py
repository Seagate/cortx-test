import logging
import json
import xmltodict
import commons.errorcodes as err
from commons.exceptions import CTException
from commons.utils import config_utils
from libs.csm.cli.cortxcli_core_lib import CortxCliClient

common_cfg = config_utils.read_yaml("config/common_config.yaml")[1]


class CortxCliTestLib(CortxCliClient):
    """This class has all common methods that will be used by all test libraries"""

    def __init__(
            self,
            host: str = common_cfg["csm"]["mgmt_vip"],
            username: str = common_cfg["csm"]["admin_user"],
            password: str = common_cfg["csm"]["admin_pass"],
            port: int = 22):
        """
        This method initializes members of CortxCliTestLib and its parent class
        :param str host: host/ip of CSM server
        :param str username: username of CSM server
        :param str password: password of CSM server
        :param int port: port number
        """
        self.log = logging.getLogger(__name__)
        super().__init__(host=host, username=username, password=password, port=port)

    def execute_cli_commands(self, cmd: str, time_out: int = 300) -> tuple:
        """
        This function executes command on interactive shell on csm server and returns output
        :param str cmd: command to execute on shell
        :param int time_out: max time to wait for command execution output
        :return: output of executed command
        """
        try:
            output = super().execute_cli_commands(cmd=cmd, time_out=time_out)
            if "error" in output.lower() or "exception" in output.lower():
                return False, output
            return True, output
        except Exception as error:
            self.log.error("An error in {0}: {1}:".format(
                CortxCliTestLib.execute_cli_commands.__name__,
                error))
            raise CTException(err.CLI_ERROR, error.args[0])

    def login_cortx_cli(
            self,
            username: str = common_cfg["csm"]["admin_user"],
            password: str = common_cfg["csm"]["admin_pass"]) -> tuple:
        """
        This function will be used to login to CORTX CLI with given credentials
        :param str username: User name to login
        :param str password: User password
        :return: True/False and output
        """
        login_cmd = "cortxcli"
        self.log.info("Opening interactive CORTX CLI session....")
        output = self.execute_cli_commands(login_cmd)[1]

        if "Username:" in output:
            self.log.info("Logging in CORTX CLI as user {}".format(username))
            output = self.execute_cli_commands(cmd=username)[1]
            if "Password:" in output:
                output = self.execute_cli_commands(cmd=password)[1]
                if "CORTX Interactive Shell" in output:
                    self.log.info(
                        "Logged in CORTX CLI as user {} successfully".format(username))
                    return True, output

        return False, output

    def logout_cortx_cli(self) -> tuple:
        """
        This function will be used to logout of CORTX CLI
        :return: True/False and output
        """
        logout_cmd = "exit"
        self.log.info("Logging out of CORTX CLI")
        output = self.execute_cli_commands(logout_cmd)[1]
        if "Successfully logged out" in output:
            return True, output

        return False, output

    def format_str_to_dict(self, input_str: str) -> dict:
        """
        This function will convert the given string into dictionary.
        :param str input_str: Input string which will be converted to dictionary.
        :return: Dictionary created from given input string.
        :rtype: dict
        """
        start_index = 0
        end_index = 0
        if not input_str:
            self.log.error("Empty string received!!")
            return None
        self.log.debug("Data received \n {0}".format(input_str))
        for i in range(len(input_str)):
            if input_str[i] == "{":
                start_index = i
                break
        count = 0
        for j in input_str[::-1]:
            if j == "}":
                end_index = count
                break
            count += 1
        json_data = json.loads(input_str[start_index:-(end_index)])
        self.log.debug("JSON output \n {0}".format(json_data))
        return json_data

    def xml_data_parsing(self, input_str: str) -> list:
        """
        This is a helper method which will parse the given XML formatted string
        :param str input_str: XML formatted string to be converted
        :return: List of dictionary
        """
        resp_list = []
        if not input_str:
            self.log.error("String is empty")
            return resp_list
        self.log.debug("Data received \n {0}".format(input_str))
        formatted_data = input_str.replace("\r\n  ", "").replace(
            "\r\n", ",").replace(",</", "</").split(",")[1:-1]
        for node in formatted_data:
            dict = json.dumps(xmltodict.parse(node))
            json_format = json.loads(dict)
            resp_list.append(json_format)
        self.log.debug("Extracted output \n {0}".format(resp_list))
        return resp_list

    def split_table_response(self, response: str) -> list:
        """
        This function will split response into list making it suitable for verification
        :param response: response which is to be split
        :return: List formed after splitting response
        """
        # Splitting response row-wise
        response = str(response).split('\r\n')

        # Splitting values of each row column-wise
        for i in range(len(response)):
            response[i] = response[i].split('|')
            for j in range(len(response[i])):
                response[i][j] = response[i][j].strip()
        response = response[4:len(response) - 2]
        self.log.info(response)
        return response

    def close_connection(self):
        """
        This function will close the ssh connection created in init
        :return: None
        """
        try:
            super().close_connection()
        except Exception as error:
            self.log.error("An error in {0}: {1}:".format(
                CortxCliTestLib.close_connection.__name__,
                error))
            raise CTException(err.CLI_ERROR, error.args[0])
