#!/usr/bin/python
# -*- coding: utf-8 -*-
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
#

"""Library contains methods which allows to perform bucket tagging operations using boto3."""

import os
import base64
import logging
import string
import secrets
from botocore.exceptions import ClientError
from commons import errorcodes as err
from commons.exceptions import CTException
from commons.exceptions import EncodingNotSupported
from commons.utils.system_utils import create_file
from commons.utils.s3_utils import poll
from config.s3 import S3_CFG
from libs.s3 import ACCESS_KEY, SECRET_KEY
from libs.s3.s3_tagging import Tagging

LOGGER = logging.getLogger(__name__)


class S3TaggingTestLib(Tagging):
    """Initialising s3 connection and including methods for bucket, object tagging operations."""

    def __init__(
            self,
            access_key: str = ACCESS_KEY,
            secret_key: str = SECRET_KEY,
            endpoint_url: str = S3_CFG["s3_url"],
            s3_cert_path: str = S3_CFG["s3_cert_path"],
            **kwargs) -> None:
        """
        The method initializes members of S3TaggingTestLib and its parent class.

        :param access_key: access key.
        :param secret_key: secret key.
        :param endpoint_url: endpoint url.
        :param s3_cert_path: s3 certificate path.
        :param region: region.
        :param aws_session_token: aws_session_token.
        :param debug: debug mode.
        """
        kwargs["region"] = kwargs.get("region", S3_CFG["region"])
        kwargs["aws_session_token"] = kwargs.get("aws_session_token", None)
        kwargs["debug"] = kwargs.get("debug", S3_CFG["debug"])
        self.sync_delay = S3_CFG["sync_delay"]
        super().__init__(
            access_key,
            secret_key,
            endpoint_url,
            s3_cert_path,
            **kwargs)

    def set_bucket_tag(
            self,
            bucket_name: str = None,
            key: str = None,
            value: str = None,
            tag_count: int = 1) -> tuple:
        """
        Set one or multiple tags to a bucket.

        :param bucket_name: Name of the bucket.
        :param key: Key for bucket tagging.
        :param value: Value for bucket tagging.
        :param tag_count: Tag count.
        :return: (Boolean, response)
        """
        LOGGER.info("Set bucket tagging")
        try:
            tag_set = list()
            for num in range(tag_count):
                tag = dict()
                tag.update([("Key", "{}{}".format(key, str(num))),
                            ("Value", "{}{}".format(value, str(num)))])
                tag_set.append(tag)
            LOGGER.debug(tag_set)
            response = super().set_bucket_tags(
                bucket_name, tag_set={'TagSet': tag_set})
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TaggingTestLib.set_bucket_tag.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def get_bucket_tags(self, bucket_name: str = None) -> tuple:
        """
        List all bucket tags if any.

        :param bucket_name: Name of the bucket.
        :return: (Boolean, list of tags)
        """
        try:
            LOGGER.info("Getting bucket tagging")
            bucket_tagging = poll(self.get_bucket_tagging, bucket_name, timeout=self.sync_delay)
            LOGGER.debug(bucket_tagging)
            tag_set = bucket_tagging["TagSet"]
            for tag in tag_set:
                LOGGER.info(tag)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TaggingTestLib.get_bucket_tags.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, tag_set

    def delete_bucket_tagging(self, bucket_name: str = None) -> tuple:
        """
        Delete all bucket tags.

        :param bucket_name: Name of the bucket.
        :return: (Boolean, response).
        """
        try:
            LOGGER.info("Deleting bucket tagging")
            response = poll(super().delete_bucket_tagging, bucket_name, timeout=self.sync_delay)
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TaggingTestLib.delete_bucket_tagging.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def set_object_tag(
            self,
            bucket_name: str = None,
            obj_name: str = None,
            key: str = None,
            value: str = None,
            **kwargs) -> tuple:
        """
        Set the supplied tag-set to an object that already exists in a bucket.

        :param bucket_name: Name of the bucket.
        :param obj_name: Name of the object.
        :param key: Key for object tagging.
        :param value: Value for object tagging.
        :keyword tags: Value for {"TagSet": [{"Key": key_val, "Value": value_val},.. ]}
        :return: (Boolean, response)
        """
        tag_count = kwargs.get("tag_count", 1)
        tags = kwargs.get("tags", None)
        try:
            if tags is None:
                LOGGER.info("Set object tagging")
                tag_set = list()
                for num in range(tag_count):
                    tag = dict()
                    tag.update([("Key", "{}{}".format(key, str(num))),
                                ("Value", "{}{}".format(value, str(num)))])
                    tag_set.append(tag)
                LOGGER.debug(tag_set)
                tags = {"TagSet": tag_set}
            response = self.put_object_tagging(bucket_name, obj_name, tags)
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TaggingTestLib.set_object_tag.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def get_object_tags(self, bucket_name: str = None, obj_name: str = None) -> tuple:
        """
        Return the tag-set of an object.

        :param bucket_name: Name of the bucket.
        :param obj_name: Name of the object.
        :return: (Boolean, list of object tags)
        """
        try:
            LOGGER.info("Getting object tags")
            obj_tagging = poll(self.get_object_tagging,
                               bucket_name, obj_name, timeout=self.sync_delay)
            LOGGER.debug(obj_tagging)
            tag_set = obj_tagging["TagSet"]
            LOGGER.info(tag_set)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TaggingTestLib.get_object_tags.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, tag_set

    def delete_object_tagging(
            self,
            bucket_name: str = None,
            obj_name: str = None) -> tuple:
        """
        Remove the tag-set from an existing object.

        :param bucket_name: Name of the bucket.
        :param obj_name: Name of the object.
        :return: (Boolean, response)
        """
        try:
            LOGGER.info("Deleting object tagging")
            response = poll(super().delete_object_tagging,
                            bucket_name, obj_name, timeout=self.sync_delay)
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TaggingTestLib.delete_object_tagging.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def create_multipart_upload_with_tagging(
            self,
            bucket_name: str = None,
            obj_name: str = None,
            tag: str = None) -> tuple:
        """
        request to initiate a multipart upload.

        :param bucket_name: Name of the bucket.
        :param obj_name: Name of the object.
        :param tag: Tag value(eg: "aaa=bbb").
        :return: (Boolean, response)
        """
        try:
            LOGGER.info("Creating multipart upload with tagging....")
            response = self.s3_client.create_multipart_upload(
                Bucket=bucket_name, Key=obj_name, Tagging=tag)
            mpu_id = response["UploadId"]
            LOGGER.info("Upload id : %s", str(mpu_id))
        except (ClientError, Exception) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3TaggingTestLib.create_multipart_upload_with_tagging.__name__,
                error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def put_object_with_tagging(self,
                                bucket_name: str = None,
                                object_name: str = None,
                                file_path: str = None,
                                tag: str = None,
                                **kwargs) -> tuple:
        """
        Putting Object to the Bucket (mainly small file) with tagging and metadata.

        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :param file_path: Path of the file.
        :param tag: Tag value(eg: "aaa=bbb").
        :return: (Boolean, response)
        """
        key = kwargs.get("key", None)
        value = kwargs.get("value", None)
        try:
            LOGGER.info("put %s into %s with %s",
                        object_name,
                        bucket_name,
                        tag)
            if not os.path.exists(file_path):
                create_file(file_path, 1)
            LOGGER.info("Putting object with tagging")
            with open(file_path, "rb") as data:
                if key:
                    meta = {key: value}
                    response = super().put_object_with_tagging(
                        bucket_name, object_name, data=data, tag=tag, meta=meta)
                else:
                    response = super().put_object_with_tagging(
                        bucket_name, object_name, data=data, tag=tag)
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TaggingTestLib.put_object_with_tagging.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def set_bucket_tag_duplicate_keys(
            self,
            bucket_name: str = None,
            key: str = None,
            value: str = None) -> tuple:
        """
        Set tags to a bucket with duplicate keys.

        :param bucket_name: Name of bucket.
        :param key: Key for bucket tagging.
        :param value: Value for bucket tagging.
        :return: True or False and response.
        """
        try:
            LOGGER.info("Set bucket tag with duplicate key")
            tag_set = list()
            for num in range(2):
                tag = dict()
                tag.update([("Key", "{}".format(key)),
                            ("Value", "{}{}".format(value, str(num)))])
                tag_set.append(tag)
            LOGGER.info("Put bucket tagging with TagSet: %s", str(tag_set))
            response = super().set_bucket_tags(
                bucket_name, tag_set={"TagSet": tag_set})
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3TaggingTestLib.set_bucket_tag_duplicate_keys.__name__,
                error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def set_bucket_tag_invalid_char(
            self,
            bucket_name: str = None,
            key: str = None,
            value: str = None) -> tuple:
        """
        Set tag to a bucket with invalid special characters(convert tag to encode base64).

        :param bucket_name: Name of bucket.
        :param key: Key for bucket tagging.
        :param value: Value for bucket tagging.
        :return: True or False and response.
        """
        try:
            LOGGER.info("Set bucket tag with invalid special chars in key.")
            tag_set = list()
            encoded = base64.b64encode(b'?')
            encoded_str = encoded.decode('utf-8')
            tag = dict()
            tag.update([("Key", "{}{}".format(key, encoded_str)),
                        ("Value", "{}{}".format(value, encoded_str))])
            tag_set.append(tag)
            LOGGER.info(
                "Put bucket tagging with invalid TagSet: %s", str(tag_set))
            response = super().set_bucket_tags(
                bucket_name, tag_set={'TagSet': tag_set})
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TaggingTestLib.set_bucket_tag_invalid_char.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def set_duplicate_object_tags(
            self,
            bucket_name: str = None,
            obj_name: str = None,
            key: str = None,
            value: str = None,
            **kwargs) -> tuple:
        """
        Set the duplicate tag-set to an object that already exists in a bucket.

        :param bucket_name: Name of bucket.
        :param obj_name: Name of object.
        :param key: Key for object tagging.
        :param value: Value for object tagging.
        :return: True or False and response.
        """
        LOGGER.info("Set duplicate tag set to an object.")
        duplicate_key = kwargs.get("duplicate_key", True)
        try:
            tag_set = list()
            for num in range(2):
                tag = dict()
                if duplicate_key:
                    tag.update([("Key", "{}".format(key)),
                                ("Value", "{}{}".format(value, str(num)))])
                    tag_set.append(tag)
                else:
                    tag.update([("Key", "{}{}".format(key, str(num))),
                                ("Value", "{}".format(value))])
                    tag_set.append(tag)
            LOGGER.info("Put object tagging with TagSet: %s", str(tag_set))
            response = super().put_object_tagging(
                bucket_name, obj_name, tags={'TagSet': tag_set})
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TaggingTestLib.set_duplicate_object_tags.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def set_object_tag_invalid_char(
            self,
            bucket_name: str = None,
            obj_name: str = None,
            key: str = None,
            value: str = None) -> tuple:
        """
        Set tag to a object with invalid special characters(convert tag to encode base64).

        :param bucket_name: Name of bucket.
        :param obj_name: Name of object.
        :param key: Key for object tagging.
        :param value: Value for object tagging.
        :return: True or False and response.
        :rtype: (Boolean, dict/str).
        """
        try:
            LOGGER.info("Set object tag with invalid special char in key.")
            tag_set = list()
            encoded = base64.b64encode(b'?')
            encoded_str = encoded.decode('utf-8')
            tag = dict()
            tag.update([("Key", "{}{}".format(key, encoded_str)),
                        ("Value", "{}{}".format(value, encoded_str))])
            tag_set.append(tag)
            LOGGER.info("Put object tagging with TagSet: %s", str(tag_set))
            response = super().put_object_tagging(
                bucket_name, obj_name, tags={'TagSet': tag_set, })
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TaggingTestLib.set_object_tag_invalid_char.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def get_object_with_tagging(
            self,
            bucket_name: str = None,
            key: str = None) -> tuple:
        """
        Get object using tag key.

        :param bucket_name: Name of bucket.
        :param key: tag key of the object.
        :return: True or False and response.
        """
        try:
            LOGGER.info("Getting object with tag key: %s", key)
            response = poll(
                self.s3_client.get_object, Bucket=bucket_name, Key=key, timeout=self.sync_delay)
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3TaggingTestLib.get_object_with_tagging.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def set_encoded_tag_values(
            self,
            bucket_name: str = None,
            encoding_type: str = "utf-8") -> tuple:
        """
        Set tag to a bucket with encoded tag values.

        :param bucket_name: Name of bucket.
        :param encoding_type: encoding type e.g. base64,utf-8
        :return: True or False, response and encoded tag set.
        """
        LOGGER.info("Set bucket tag with encoded key value pair.")
        if encoding_type not in ("utf-8", "base64"):
            raise EncodingNotSupported(f"Encoding {encoding_type} is not supported")
        key = ''.join((secrets.choice(string.printable) for i in range(8)))
        value = ''.join((secrets.choice(string.printable) for i in range(8)))
        tag_set = list()
        if encoding_type == 'utf-8':
            key_encode = key.encode('utf-8')
            value_encode = value.encode('utf-8')
        elif encoding_type == 'base64':
            key_encode = base64.b64encode(key.encode())
            value_encode = base64.b64encode(value.encode())
        tag = dict()
        tag.update([("Key", "{}".format(key_encode)),
                    ("Value", "{}".format(value_encode))])
        tag_set.append(tag)
        LOGGER.info(
            "Put bucket tagging with encoded value of TagSet: %s", str(tag_set))
        response = super().set_bucket_tags(
            bucket_name, tag_set={'TagSet': tag_set})

        return True, response, tag_set
