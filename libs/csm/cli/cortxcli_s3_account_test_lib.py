import logging
from libs.csm.cli.cortxcli_test_lib import CortxCliTestLib

logger = logging.getLogger(__name__)


class CortxCliS3AccountOperations(CortxCliTestLib):
    """
    This class has all s3 account operations
    """

    def create_s3account_cortxcli(self, account_name, account_email, password):
        """
        This function will create s3 account with specified name using CORTX CLI.
        :param str account_name: Name of s3 account user to be created.
        :param str account_email: Account email for account creation.
        :param str password: Password to create s3 account user.
        :return: (True/False, Response)
        :rtype: tuple
        """
        create_s3acc_cmd = "s3accounts create"
        command = " ".join([create_s3acc_cmd, account_name, account_email])
        logger.info("Creating S3 account with name {0}".format(account_name))
        response = self.execute_cli_commands(cmd=command)[1]

        if "Password:" in response:
            response = self.execute_cli_commands(cmd=password)[1]
            if "Confirm Password:" in response:
                response = self.execute_cli_commands(cmd=password)[1]
                if "[Y/n]" in response:
                    response = self.execute_cli_commands(cmd="Y")[1]
        self.cli_client.execute_csm_cli_command(
            self.session_obj, password, verify_statement=consts.CHECK)
        # Conforming s3 account user creation operation
        response = self.cli_client.execute_csm_cli_command(
            self.session_obj, commands.affirmative)
        self._log.info(response)
        # Checking for error response
        if self.error_statement_in_response(response):
            self._log.error(
                "Creating S3 account user with name {0} is failed with error: {1}".format(
                    account_name, response))
            return False, response
        # Verifying if s3 account user is created
        verify_acc_created = self.verify_s3account_user_created(account_name, account_email)
