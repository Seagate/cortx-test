import logging
from typing import Tuple
from libs.csm.cli.cortxcli_test_lib import CortxCliTestLib

log = logging.getLogger(__name__)


class CortxCliIAMLib(CortxCliTestLib):
    """This class has all IAM methods"""

    def create_iam_user(
            self,
            user_name: str = None,
            password: str = None,
            confirm_password: str = None,
            confirm: str = "Y",
            help_param: bool = False) -> Tuple[bool, str]:
        """
        This function will create new IAM user
        :param user_name: Name of IAM user to be created
        :param password: Password to create s3 IAM user.
        :param confirm_password: Confirm password to create s3 IAM user.
        :param confirm: Confirm option for creating a IAM user
        :param help_param: True for displaying help/usage
        :return: (Boolean/Response)
        """
        create_iam_user = "s3iamusers create"
        if help_param:
            cmd = " ".join([create_iam_user, "-h"])
        else:
            cmd = " ".join(
                [create_iam_user, user_name])
        output = self.execute_cli_commands(cmd=cmd)[1]
        if help_param:
            log.info("Displaying usage for create iam users")
            return True, output

        if "Password" in output:
            output = self.execute_cli_commands(cmd=password)[1]
            if "Confirm Password" in output:
                output = self.execute_cli_commands(cmd=confirm_password)[1]
                if "[Y/n]" in output:
                    output = self.execute_cli_commands(cmd=confirm)[1]
                    if ("User Name" in output) and (
                            "User ID" in output) and ("ARN" in output):

                        return True, output

        return False, output

    def list_iam_user(self, output_format: str = None, help_param: bool = False):
        """
        This function will list IAM users with given format
        (CLI will list IAM users in table format if format is set to None)
        :param output_format: Format of Output(table,xml,json)
        :param help_param: True for displaying help/usage
        :return: List of IAM users in given format
        """
        list_iam_user = "s3iamusers show"
        if help_param:
            list_iam_user = " ".join([list_iam_user, "-h"])
        if output_format:
            list_iam_user = " ".join(
            [list_iam_user, "-f", output_format])
        output = self.execute_cli_commands(cmd=list_iam_user)[1]
        if help_param:
            log.info("Displaying usage for show iam users")
            return True, output
        if not ("user_name" in output or
                "user_id" in output or
                "arn" in output):
            return False, output
        if output_format == "json":
            output = self.format_str_to_dict(output)
        if output_format == "xml":
            output = self.xml_data_parsing(output)
        if output_format == "table":
            output = self.split_table_response(output)

        return True, output

    def delete_iam_user(self, user_name: str = None, confirm: str = "Y", help_param: bool = False):
        """
        This function will delete IAM user
        :param user_name: Name of IAM user to be created
        :param confirm: Confirm option for deleting a IAM user
        :param help_param: True for displaying help/usage
        """
        delete_iam_user = "s3iamusers delete"
        if help_param:
            cmd = " ".join([delete_iam_user, "-h"])
        else:
            cmd = " ".join([delete_iam_user, user_name])
        output = self.execute_cli_commands(cmd=cmd)[1]
        if help_param:
            log.info("Displaying usage for delete iam user")
            return True, output

        if "[Y/n]" in output:
            output = self.execute_cli_commands(cmd=confirm)[1]

            return True, output
        return False, output




