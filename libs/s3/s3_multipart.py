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

"""Python Library using boto3 module to perform multipart Operations."""

import logging
import os
import sys
import threading
from typing import Union

from boto3.s3.transfer import TransferConfig

from commons.constants import ERR_MSG
from libs.s3.s3_core_lib import S3Lib

LOGGER = logging.getLogger(__name__)


class Multipart(S3Lib):
    """Class containing methods to implement multipart functionality."""

    def create_multipart_upload(self, bucket_name: str = None, obj_name: str = None,
                                m_key: str = None, m_value: str = None) -> dict:
        """
        Request to initiate a multipart upload.

        :param bucket_name: Name of the bucket.
        :param obj_name: Name of the object.
        :param m_key: Key for metadata.
        :param m_value:  Value for metadata.
        :return: response
        """
        if m_key:
            response = self.s3_client.create_multipart_upload(
                Bucket=bucket_name, Key=obj_name, Metadata={m_key: m_value})
        else:
            response = self.s3_client.create_multipart_upload(Bucket=bucket_name, Key=obj_name)
        LOGGER.debug("Response: %s", str(response))

        return response

    def upload_part(self, body: Union[str, bytes] = None, bucket_name: str = None,
                    object_name: str = None, **kwargs) -> dict:
        """
        Upload parts of a specific multipart upload.

        :param body: content of the object.
        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :keyword content_md5: base64-encoded MD5 digest of message
        :return:
        """
        upload_id = kwargs.get("upload_id", None)
        part_number = kwargs.get("part_number", None)
        content_md5 = kwargs.get("content_md5", None)
        if content_md5:
            response = self.s3_client.upload_part(
                Body=body, Bucket=bucket_name, Key=object_name, UploadId=upload_id,
                PartNumber=part_number, ContentMD5=content_md5)
        else:
            response = self.s3_client.upload_part(
                Body=body, Bucket=bucket_name, Key=object_name, UploadId=upload_id,
                PartNumber=part_number)
        logging.debug(response)

        return response

    def list_parts(self, mpu_id: str = None, bucket_name: str = None,
                   object_name: str = None, **kwargs) -> dict:
        """
        list parts of a specific multipart upload.
        :param mpu_id: Multipart upload ID
        :param bucket_name: Name of the bucket
        :param object_name: Name of the object
        :keyword part_number_marker: next part number in case parts greater than 1000.
        :return: response
        """
        part_number_marker = kwargs.get("part_num_marker", 0)
        if part_number_marker:
            response = self.s3_client.list_parts(Bucket=bucket_name, Key=object_name,
                                                 UploadId=mpu_id,
                                                 PartNumberMarker=part_number_marker)
        else:
            response = self.s3_client.list_parts(Bucket=bucket_name, Key=object_name,
                                                 UploadId=mpu_id)
        LOGGER.debug(response)

        return response

    def complete_multipart_upload(self, mpu_id: str = None, parts: list = None, bucket: str = None,
                                  object_name: str = None) -> dict:
        """
        Complete a multipart upload, s3 creates an object by concatenating the parts.

        :param mpu_id: Multipart upload ID
        :param parts: Uploaded parts
        :param bucket: Name of the bucket
        :param object_name: Name of the object
        :return: response
        """
        LOGGER.info("initiated complete multipart upload")
        result = self.s3_client.complete_multipart_upload(
            Bucket=bucket, Key=object_name, UploadId=mpu_id, MultipartUpload={"Parts": parts})
        LOGGER.debug(result)

        return result

    def list_multipart_uploads(self, bucket: str = None) -> dict:
        """
        List all initiated multipart uploads.

        :param bucket: Name of the bucket.
        :return: response.
        """
        result = self.s3_client.list_multipart_uploads(Bucket=bucket)
        LOGGER.debug(result)

        return result

    def list_multipart_uploads_with_keymarker(self, bucket: str = None,
                                              keymarker: str = None) -> dict:
        """
        List all initiated multipart uploads.
        :param bucket: Name of the bucket.
        :param keymarker: key marker of more than >1000 mpu
        :return: response.
        """
        result = self.s3_client.list_multipart_uploads(Bucket=bucket, KeyMarker=keymarker)
        LOGGER.debug(result)

        return result

    def abort_multipart_upload(self, bucket: str = None, object_name: str = None,
                               upload_id: str = None) -> dict:
        """
        Abort multipart upload for given upload_id.

        After aborting a multipart upload, you cannot upload any part using that upload ID again.
        :param bucket: Name of the bucket.
        :param object_name: Name of the object.
        :param upload_id: Name of the object.
        :return: response.
        """
        response = self.s3_client.abort_multipart_upload(
            Bucket=bucket, Key=object_name, UploadId=upload_id)
        LOGGER.debug(response)

        return response

    def get_object(self, bucket: str = None, key: str = None, ranges: str = None) -> dict:
        """
        Getting byte range of the object.

        :param bucket: Name of the bucket.
        :param key: Key of object.
        :param ranges: Range in bytes.
        :return: response.
        """
        response = self.s3_client.get_object(Bucket=bucket, Key=key, Range=ranges)
        LOGGER.debug(response)

        return response

    def upload_part_copy(self, copy_source: str = None, bucket_name: str = None,
                         object_name: str = None, **kwargs) -> dict:
        """
        Upload parts of a specific multipart upload.

        :param copy_source: source of part copy.
        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :upload_id: upload id of the multipart upload
        :part_number: part number to be uploaded
        :**kwargs: optional params dict
        :return:
        """
        content_md5 = kwargs.get("content_md5", None)
        copy_source_range = kwargs.get("copy_source_range", "")
        upload_id = kwargs.get("upload_id", None)
        part_number = kwargs.get("part_number", None)
        if copy_source_range:
            if content_md5:
                response = self.s3_client.upload_part_copy(
                    Bucket=bucket_name, Key=object_name, UploadId=upload_id, PartNumber=part_number,
                    CopySource=copy_source, ContentMD5=content_md5,
                    CopySourceRange=copy_source_range)
            else:
                response = self.s3_client.upload_part_copy(
                    Bucket=bucket_name, Key=object_name, UploadId=upload_id, PartNumber=part_number,
                    CopySource=copy_source, CopySourceRange=copy_source_range)
        else:
            if content_md5:
                response = self.s3_client.upload_part_copy(
                    Bucket=bucket_name, Key=object_name, UploadId=upload_id, PartNumber=part_number,
                    CopySource=copy_source, ContentMD5=content_md5)
            else:
                response = self.s3_client.upload_part_copy(
                    Bucket=bucket_name, Key=object_name, UploadId=upload_id, PartNumber=part_number,
                    CopySource=copy_source)
        logging.debug(response)

        return response


# pylint: disable=too-few-public-methods
class ProgressPercentage:
    """Call back for sending progress"""

    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        # To simplify we'll assume this is hooked up
        # to a single filename.
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write("\r%s  %s / %s  (%.2f%%)" % (self._filename, self._seen_so_far,
                                                          self._size, percentage))
            sys.stdout.flush()


class MultipartUsingBoto(S3Lib):
    """Multipart lib using boto3 high level multi part functionality."""

    @staticmethod
    def get_transfer_config():
        """Create a transfer config."""
        config = TransferConfig(multipart_threshold=1024 * 1024,
                                max_concurrency=10,
                                multipart_chunksize=1024 * 1024,
                                use_threads=True)

        return config

    def multipart_upload(self, **kwargs):
        """Multipart upload with HL API."""
        bucket_name = kwargs.get('bucket')
        file_path = kwargs.get('file_path')
        s3_prefix = kwargs.get('s3prefix')  # s3prefix should not start with /
        config = self.get_transfer_config()
        assert bucket_name
        assert file_path
        assert config
        key = os.path.split(file_path)[-1]
        if s3_prefix is not None:
            key = '/'.join([s3_prefix, key])
        self.s3_resource.Object(bucket_name, key). \
            upload_file(file_path, ExtraArgs={'ContentType': 'text/plain'},
                        Config=config, Callback=ProgressPercentage(file_path))
        return key

    def multipart_download(self, **kwargs):
        """Download file using high level download API."""
        bucket_name = kwargs.get('bucket')
        file_path = kwargs.get('file_path')  # Local download file path
        config = self.get_transfer_config()
        key = kwargs.get('key')  # key is s3 server side name with prefix.
        assert key
        try:
            self.s3_resource.Object(bucket_name, key). \
                download_file(file_path, Config=config, Callback=ProgressPercentage(file_path))
        except Exception as error:
            LOGGER.exception(ERR_MSG, "multipart_download", str(error))
            raise error
