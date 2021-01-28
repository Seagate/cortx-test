import logging
from libs.csm.cli.cortxcli_test_lib import CortxCliTestLib

logger = logging.getLogger(__name__)


class CortxCliS3BucketOperations(CortxCliTestLib):
    """
    This class has all s3 bucket operations
    """

    def create_bucket_cortx_cli(
            self,
            bucket_name: str) -> tuple:
        """
        This function will create a bucket using CORTX CLI
        :param bucket_name: New bucket's name
        :return: True/False and response returned by CORTX CLI
        """
        create_bucket_cmd = "s3buckets create {}".format(bucket_name)

        logger.info("Creating bucket with name {}".format(bucket_name))
        response = self.execute_cli_commands(cmd=create_bucket_cmd)[1]
        logger.info("Response returned: \n{}".format(response))

        if "Bucket created" in response:
            return True, response
        return False, response

    def list_buckets_cortx_cli(self, op_format: str = None) -> tuple:
        """
        This function will list s3buckets using CORTX CLI
        :param op_format: Format for bucket list (optional) (default value: table)
                       (possible values: table/xml/json)
        :return: response returned by CORTX CLI
        """
        show_bkts_cmd = "s3buckets show"

        if op_format:
            show_bkts_cmd = "{} -f {}".format(show_bkts_cmd, op_format)

        logger.info("Listing buckets with cmd: {}".format(show_bkts_cmd))
        response = self.execute_cli_commands(cmd=show_bkts_cmd)
        logger.info("Response returned: \n{}".format(response))

        return response

    def delete_bucket_cortx_cli(
            self,
            bucket_name: str) -> tuple:
        """
        This function will delete given bucket using CORTX CLI
        :param bucket_name: name of the bucket to be deleted
        :return: True/False and response returned by CORTX CLI
        """
        delete_bucket_cmd = "s3buckets delete {}".format(bucket_name)

        logger.info("Deleting bucket {}".format(bucket_name))
        response = self.execute_cli_commands(cmd=delete_bucket_cmd)[1]
        logger.info("Response returned: \n{}".format(response))

        if "Bucket deleted" in response:
            return True, response
        return False, response
