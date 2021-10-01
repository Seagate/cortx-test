#!/usr/bin/python
# -*- coding: utf-8 -*-
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
#
"""Python library contains methods for s3 multipart upload."""

import os
import logging

from commons import errorcodes as err
from commons.exceptions import CTException
from commons.utils.system_utils import create_file, cal_percent
from libs.s3 import S3_CFG, ACCESS_KEY, SECRET_KEY
from libs.s3.s3_core_lib import Multipart

LOGGER = logging.getLogger(__name__)


class S3MultipartTestLib(Multipart):
    """Class initialising s3 connection and including methods for multipart operations."""

    def __init__(self,
                 access_key: str = ACCESS_KEY,
                 secret_key: str = SECRET_KEY,
                 endpoint_url: str = S3_CFG["s3_url"],
                 s3_cert_path: str = S3_CFG["s3_cert_path"],
                 **kwargs) -> None:
        """
        This method initializes members of S3MultipartTestLib and its parent class.

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
        super().__init__(
            access_key,
            secret_key,
            endpoint_url,
            s3_cert_path,
            **kwargs)

    def create_multipart_upload(self,
                                bucket_name: str = None,
                                obj_name: str = None,
                                m_key: str = None,
                                m_value: str = None) -> tuple:
        """
        Request to initiate a multipart upload.

        :param bucket_name: Name of the bucket.
        :param obj_name: Name of the object.
        :param m_key: Key for metadata.
        :param m_value:  Value for metadata.
        :return: (Boolean, response)
        """
        try:
            LOGGER.info("Creating multipart upload....")
            response = super().create_multipart_upload(
                bucket_name, obj_name, m_key, m_value)
            LOGGER.debug(
                "Response: %s Upload id: %s", response, response["UploadId"])
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         S3MultipartTestLib.create_multipart_upload.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def upload_part(self,
                    body: bytes = None,
                    bucket_name: str = None,
                    object_name: str = None,
                    **kwargs) -> tuple:
        """
        Upload parts of a specific multipart upload.

        :param body: content of the object.
        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :keyword upload_id: Id of complete multipart upload.
        :keyword part_number: upload part no.
        :keyword content_md5: base64-encoded MD5 digest of message
        :return: (Boolean, response)
        """
        try:
            upload_id = kwargs.get("upload_id", None)
            part_number = kwargs.get("part_number", None)
            content_md5 = kwargs.get("content_md5", None)
            LOGGER.info("uploading part")
            if content_md5:
                response = super().upload_part(body, bucket_name, object_name,
                                               upload_id=upload_id, part_number=part_number, content_md5=content_md5)
            else:
                response = super().upload_part(body, bucket_name, object_name,
                                               upload_id=upload_id, part_number=part_number)
            LOGGER.info(response)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         S3MultipartTestLib.upload_part.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def upload_parts(self,
                     mpu_id: int = None,
                     bucket_name: str = None,
                     object_name: str = None,
                     multipart_obj_size: int = None,
                     **kwargs) -> tuple:
        """
        Upload parts for a specific multipart upload ID.

        :param mpu_id: Multipart Upload ID.
        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :param multipart_obj_size: Size of object need to be uploaded.
        :param total_parts: No. of parts to be uploaded.
        :param multipart_obj_path: Path of object file.
        :return: (Boolean, List of uploaded parts).
        """
        try:
            total_parts = kwargs.get("total_parts", None)
            multipart_obj_path = kwargs.get("multipart_obj_path", None)
            parts = list()
            uploaded_bytes = 0
            single_part_size = int(multipart_obj_size) // int(total_parts)
            if os.path.exists(multipart_obj_path):
                os.remove(multipart_obj_path)
            create_file(multipart_obj_path, multipart_obj_size)
            with open(multipart_obj_path, "rb") as file_pointer:
                i = 1
                while True:
                    data = file_pointer.read(1048576 * single_part_size)
                    LOGGER.info("data_len %s", str(len(data)))
                    if not data:
                        break
                    part = super().upload_part(
                        data, bucket_name, object_name, upload_id=mpu_id, part_number=i)
                    LOGGER.debug("Part : %s", str(part))
                    parts.append({"PartNumber": i, "ETag": part["ETag"]})
                    uploaded_bytes += len(data)
                    LOGGER.debug(
                        "{0} of {1} uploaded ({2:.2f}%)".format(
                            uploaded_bytes,
                            multipart_obj_size *
                            1048576,
                            cal_percent(
                                uploaded_bytes,
                                multipart_obj_size *
                                1048576)))
                    i += 1
            LOGGER.info(parts)

            return True, parts
        except BaseException as error:
            LOGGER.error("Error in %s: %s",
                         S3MultipartTestLib.upload_parts.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

    def list_parts(
            self,
            mpu_id: str = None,
            bucket_name: str = None,
            object_name: str = None) -> tuple:
        """
        List parts of a specific multipart upload.

        :param mpu_id: Id of complete multipart upload.
        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :return: (Boolean, response)
        """
        try:
            LOGGER.info("Listing uploaded parts.")
            response = super().list_parts(mpu_id, bucket_name, object_name)
            LOGGER.info(response)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         S3MultipartTestLib.list_parts.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def complete_multipart_upload(
            self,
            mpu_id: str = None,
            parts: list = None,
            bucket: str = None,
            object_name: str = None) -> tuple:
        """
        Complete a multipart upload, s3 creates an object by concatenating the parts.

        :param mpu_id: Id of complete multipart upload.
        :param parts: Upload parts.
        :param bucket: Name of the bucket.
        :param object_name: Name of the object.
        :return: (Boolean, response).
        """
        try:
            LOGGER.info("initiated complete multipart upload.")
            response = super().complete_multipart_upload(mpu_id, parts, bucket, object_name)
            LOGGER.info(response)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         S3MultipartTestLib.complete_multipart_upload.__name__,
                         error)

            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def list_multipart_uploads(self, bucket: str = None):
        """
        List all initiated multipart uploads.

        :param bucket: Name of the bucket.
        :return: (Boolean, response)
        """
        try:
            LOGGER.info("Listing multipart uploads.")
            response = super().list_multipart_uploads(bucket)
            LOGGER.info(response)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         S3MultipartTestLib.list_multipart_uploads.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def abort_multipart_upload(
            self,
            bucket: str = None,
            object_name: str = None,
            upload_id: str = None) -> tuple:
        """
        Abort multipart upload for given upload_id.

        After aborting a multipart upload, you cannot upload any part using that upload ID again.
        :param bucket: Name of the bucket.
        :param object_name: Name of the object.
        :param upload_id: Name of the object.
        :return: (Boolean, response)
        """
        try:
            LOGGER.info("Abort a multipart upload.")
            response = super().abort_multipart_upload(bucket, object_name, upload_id)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         S3MultipartTestLib.abort_multipart_upload.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def abort_multipart_all(
            self,
            bucket: str = None,
            object_name: str = None) -> tuple:
        """
        Abort all the multipart uploads.

        After aborting a multipart upload, you cannot upload any part using that upload ID again.
        :param bucket: Name of the bucket.
        :param object_name: Name of the object.
        :return: (Boolean, response)
        """
        try:
            LOGGER.info("Abort all multipart uploads.")
            mpus = super().list_multipart_uploads(bucket)
            response = []
            LOGGER.info("Aborting %d uploads", len(mpus))
            if "Uploads" in mpus:
                for upload in mpus["Uploads"]:
                    upload_id = upload["UploadId"]
                    response.append(
                        super().abort_multipart_upload(
                            bucket, object_name, upload_id))
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         S3MultipartTestLib.abort_multipart_all.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def get_byte_range_of_object(
            self,
            bucket_name: str = None,
            my_key: str = None,
            start_byte: int = None,
            stop_byte: int = None) -> tuple:
        """
        Getting byte range of the object.

        :param bucket_name: Name of the bucket.
        :param my_key: Key of object.
        :param start_byte: Start byte range.
        :param stop_byte: Stop byte range.
        :return: (Boolean, response)
        """
        try:
            LOGGER.info("Getting byte range of the object.")
            range_byte = "bytes={}-{}".format(start_byte, stop_byte)
            response = self.get_object(bucket_name, my_key, range_byte)
            LOGGER.info(response)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         S3MultipartTestLib.get_byte_range_of_object.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def simple_multipart_upload(
            self,
            bucket_name: str,
            object_name: str,
            file_size: int,
            file_path: str,
            parts: int):
        """
        Do multipart upload for given object by dividing it into given parts.
        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :param file_size: Object size.
        :param file_path: File path.
        :param parts: Number of parts the objects needs to be divided.
        """
        try:
            LOGGER.info("Initiating multipart upload")
            res = self.create_multipart_upload(bucket_name, object_name)
            mpu_id = res[1]["UploadId"]
            LOGGER.info("Multipart Upload initiated with mpu_id %s", mpu_id)
            LOGGER.info("Uploading parts into bucket")
            res = self.upload_parts(mpu_id, bucket_name, object_name, file_size,
                                    total_parts=parts, multipart_obj_path=file_path)
            parts = res[1]
            LOGGER.info("Uploaded parts into bucket: %s", parts)
            LOGGER.info("Completing multipart upload")
            self.complete_multipart_upload(mpu_id, parts, bucket_name, object_name)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         S3MultipartTestLib.simple_multipart_upload.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])
