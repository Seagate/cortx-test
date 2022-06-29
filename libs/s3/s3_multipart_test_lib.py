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
"""Python library contains methods for s3 multipart upload."""

import logging
import os
from hashlib import md5
from time import perf_counter_ns

from botocore.exceptions import ClientError
from numpy.random import permutation

from commons import errorcodes as err
from commons.constants import ERR_MSG
from commons.exceptions import CTException
from commons.greenlet_worker import GeventPool
from commons.utils import s3_utils
from commons.utils.system_utils import cal_percent
from commons.utils.system_utils import create_file
from config.s3 import S3_CFG
from libs.s3 import ACCESS_KEY, SECRET_KEY
from libs.s3.s3_multipart import Multipart

LOGGER = logging.getLogger(__name__)


class S3MultipartTestLib(Multipart):
    """Class initialising s3 connection and including methods for multipart operations."""

    def __init__(self, access_key: str = ACCESS_KEY, secret_key: str = SECRET_KEY,
                 endpoint_url: str = S3_CFG["s3_url"], s3_cert_path: str = S3_CFG["s3_cert_path"],
                 **kwargs) -> None:
        """
        Method initializes members of S3MultipartTestLib and its parent class.

        :param access_key: access key.
        :param secret_key: secret key.
        :param endpoint_url: endpoint url.
        :param s3_cert_path: s3 certificate path.
        :keyword region: region.
        :keyword aws_session_token: aws_session_token.
        :keyword debug: debug mode.
        """
        kwargs["region"] = kwargs.get("region", S3_CFG["region"])
        kwargs["aws_session_token"] = kwargs.get("aws_session_token", None)
        kwargs["debug"] = kwargs.get("debug", S3_CFG["debug"])
        super().__init__(access_key, secret_key, endpoint_url, s3_cert_path, **kwargs)

    def create_multipart_upload(self, bucket_name: str = None, obj_name: str = None,
                                m_key: str = None, m_value: str = None) -> tuple:
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
            response = super().create_multipart_upload(bucket_name, obj_name, m_key, m_value)
            LOGGER.debug("Response: %s Upload id: %s", response, response["UploadId"])
        except (ClientError, Exception) as error:
            LOGGER.exception(ERR_MSG, S3MultipartTestLib.create_multipart_upload.__name__, error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def upload_part(self, body: bytes = None, bucket_name: str = None, object_name: str = None,
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
                                               upload_id=upload_id, part_number=part_number,
                                               content_md5=content_md5)
            else:
                response = super().upload_part(body, bucket_name, object_name,
                                               upload_id=upload_id, part_number=part_number)
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.exception(ERR_MSG, S3MultipartTestLib.upload_part.__name__, error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    # pylint: disable-msg=too-many-locals
    def upload_parts(self, mpu_id: int = None, bucket_name: str = None, object_name: str = None,
                     multipart_obj_size: int = None, **kwargs) -> tuple:
        """
        Upload parts for a specific multipart upload ID.

        :param mpu_id: Multipart Upload ID.
        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :param multipart_obj_size: Size of object need to be uploaded.
        :keyword total_parts: No. of parts to be uploaded.
        :keyword multipart_obj_path: Path of object file.
        :return: (Boolean, List of uploaded parts).
        """
        try:
            b_size = kwargs.get("block_size", "1M")
            total_parts = kwargs.get("total_parts", None)
            multipart_obj_path = kwargs.get("multipart_obj_path", None)
            parts = []
            uploaded_bytes = 0
            single_part_size = int(multipart_obj_size) // int(total_parts)
            if kwargs.get('create_file', True):
                if os.path.exists(multipart_obj_path):
                    os.remove(multipart_obj_path)
                create_file(multipart_obj_path, multipart_obj_size, b_size=b_size)
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
                    LOGGER.debug("%s of %s uploaded %.2f%%", uploaded_bytes, multipart_obj_size *
                                 1048576, cal_percent(uploaded_bytes, multipart_obj_size * 1048576))
                    i += 1
            LOGGER.info(parts)

            return True, parts
        except (ClientError, Exception) as error:
            LOGGER.exception(ERR_MSG, S3MultipartTestLib.upload_parts.__name__, error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

    # pylint: disable-msg=too-many-locals
    def upload_precalculated_parts(self, upload_id: int = None, bucket_name: str = None,
                                   object_name: str = None, **kwargs) -> tuple:
        """
        Upload precalculated part sizes for a specific multipart uploadID one part at a time.

        :param upload_id: Multipart Upload ID.
        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :return: (Boolean, Dict of uploaded parts and expected multipart ETag).
        """
        try:
            multipart_obj_path = kwargs.get("multipart_obj_path", None)
            part_sizes = kwargs.get("part_sizes", None)
            chunk_size = kwargs.get("chunk_size", None)
            uploaded_parts = []
            total_part_list = []
            for part in part_sizes:
                total_part_list.extend([part['part_size']] * part['count'])
            md5_digests = [None] * len(total_part_list)
            with open(multipart_obj_path, "rb") as file_pointer:
                for i, partnum in enumerate(permutation(len(total_part_list))):
                    data = file_pointer.read(int(chunk_size * total_part_list[i]))
                    LOGGER.info("data_len %s", str(len(data)))
                    part = super().upload_part(data, bucket_name, object_name, upload_id=upload_id,
                                               part_number=int(partnum) + 1)
                    LOGGER.debug("Part : %s", str(part))
                    uploaded_parts.append({"PartNumber": int(partnum) + 1, "ETag": part["ETag"]})
                    md5_digests[int(partnum)] = md5(data).digest()  # nosec
            multipart_etag = f'''"{md5(b''.join(md5_digests)).hexdigest() + '-' + str(len(
                md5_digests))}"'''  # nosec
            return True, {'uploaded_parts': uploaded_parts, 'expected_etag': multipart_etag}
        except BaseException as error:
            LOGGER.exception(ERR_MSG, S3MultipartTestLib.upload_parts.__name__, error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

    def upload_parts_parallel(self, upload_id: int = None, bucket_name: str = None,
                              object_name: str = None, **kwargs) -> tuple:
        """
        Upload parts for a specific multipart upload ID in parallel.

        :param upload_id: Multipart Upload ID.
        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :return: (Boolean, List of uploaded parts).
        """
        try:
            parts = kwargs.get("parts", None)
            parallel_thread = kwargs.get("parallel_thread", 5)
            gevent_pool = GeventPool(parallel_thread)
            part_number_list = list(parts.keys())

            for part_number in part_number_list:
                part = parts.get(part_number, None)
                gevent_pool.wait_available()
                gevent_pool.spawn(super().upload_part,
                                  part[0], bucket_name,
                                  object_name, upload_id=upload_id,
                                  part_number=part_number, content_md5=part[1])
            gevent_pool.join_group()
            response = self.list_parts(upload_id, bucket_name, object_name)
            return response
        except BaseException as error:
            LOGGER.exception(ERR_MSG, S3MultipartTestLib.upload_parts_parallel.__name__, error)
            raise CTException(err.S3_CLIENT_ERROR, error) from error

    def upload_parts_sequential(self, upload_id: int = None, bucket_name: str = None,
                                object_name: str = None, **kwargs) -> tuple:
        """
        Upload parts(ordered/unordered) for a specific multipart upload ID in sequential.

        :param upload_id: Multipart Upload ID.
        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        # :param chunks: No. of parts to be uploaded with details.
        :return: (Boolean, List of uploaded parts).
        """
        try:
            parts = kwargs.get("parts", None)
            parts_details = []
            for part_number in parts:
                LOGGER.info("Uploading part: %s", part_number)
                resp = super().upload_part(parts[part_number][0], bucket_name, object_name,
                                           upload_id=upload_id, part_number=part_number,
                                           content_md5=parts[part_number][1])
                parts_details.append({"PartNumber": part_number, "ETag": resp["ETag"]})

            return True, parts_details
        except BaseException as error:
            LOGGER.exception(ERR_MSG, S3MultipartTestLib.upload_parts_sequential.__name__, error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

    def upload_multipart(self, body: str = None, bucket_name: str = None, object_name: str = None,
                         **kwargs) -> tuple:
        """
        Upload single part of a specific multipart upload.

        :param body: content of the object.
        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :keyword content_md5: base64-encoded MD5 digest of message
        :return:
        """
        upload_id = kwargs.get("upload_id", None)
        part_number = kwargs.get("part_number", None)
        content_md5 = kwargs.get("content_md5", None)
        try:
            part = super().upload_part(body, bucket_name, object_name, upload_id=upload_id,
                                       part_number=part_number, content_md5=content_md5)

            return True, part
        except BaseException as error:
            LOGGER.exception(ERR_MSG, S3MultipartTestLib.upload_multipart.__name__, error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

    def list_parts(self, mpu_id: str = None, bucket_name: str = None, object_name: str = None,
                   **kwargs) -> tuple:
        """
        List parts of a specific multipart upload.

        :param mpu_id: ID of complete multipart upload.
        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :keyword part_number_marker: next part number in case parts greater than 1000.
        :return: (Boolean, response)
        """
        try:
            LOGGER.info("Listing uploaded parts.")
            part_num_marker = kwargs.get("PartNumberMarker", 0)
            response = super().list_parts(
                mpu_id, bucket_name, object_name, part_num_marker=part_num_marker)
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.exception(ERR_MSG, S3MultipartTestLib.list_parts.__name__, error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def complete_multipart_upload(self, mpu_id: str = None, parts: list = None, bucket: str = None,
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
        except (ClientError, Exception) as error:
            LOGGER.exception(ERR_MSG, S3MultipartTestLib.complete_multipart_upload.__name__, error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

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
        except (ClientError, Exception) as error:
            LOGGER.exception(ERR_MSG, S3MultipartTestLib.list_multipart_uploads.__name__, error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def abort_multipart_upload(self, bucket: str = None, object_name: str = None,
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
        except (ClientError, Exception) as error:
            LOGGER.exception(ERR_MSG, S3MultipartTestLib.abort_multipart_upload.__name__, error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def upload_part_copy(self, copy_source: str = None, bucket_name: str = None,
                         object_name: str = None, **kwargs) -> tuple:
        """
        Upload part using uploadPartCopy.

        :param copy_source: source of part copy.
        # CopySource='/bucketname/sourceobjectkey'
        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :keyword upload_id: Id of complete multipart upload.
        :keyword part_number: upload part no.
        :keyword content_md5: base64-encoded MD5 digest of message
        :return: (Boolean, response)
        """
        try:
            content_md5 = kwargs.get("content_md5", None)
            # CopySourceRange='bytes=1-100000'
            copy_source_range = kwargs.get("copy_source_range", None)
            part_number = kwargs.get("part_number", None)
            upload_id = kwargs.get("upload_id", None)
            LOGGER.info("uploading part copy")
            response = super().upload_part_copy(copy_source, bucket_name, object_name,
                                                upload_id=upload_id, part_number=part_number,
                                                copy_source_range=copy_source_range,
                                                content_md5=content_md5)
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.exception(ERR_MSG, S3MultipartTestLib.upload_part_copy.__name__, error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error
        return True, response

    def abort_multipart_all(self, bucket: str = None, object_name: str = None) -> tuple:
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
                    response.append(super().abort_multipart_upload(bucket, object_name, upload_id))
        except (ClientError, Exception) as error:
            LOGGER.exception(ERR_MSG, S3MultipartTestLib.abort_multipart_all.__name__, error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def get_byte_range_of_object(self, bucket_name: str = None, my_key: str = None,
                                 start_byte: int = None, stop_byte: int = None) -> tuple:
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
            range_byte = f"bytes={start_byte}-{stop_byte}"
            response = self.get_object(bucket_name, my_key, range_byte)
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.exception(ERR_MSG, S3MultipartTestLib.get_byte_range_of_object.__name__, error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    # pylint: disable = too-many-arguments
    def simple_multipart_upload(self, bucket_name: str, object_name: str, file_size: int,
                                file_path: str, parts: int):
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
            LOGGER.exception(ERR_MSG, S3MultipartTestLib.simple_multipart_upload.__name__, error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

    # pylint: disable-msg=too-many-locals
    def complete_multipart_upload_with_di(self, bucket_name: str, object_name: str, file_path: str,
                                          total_parts: int, **kwargs):
        """
        Complete the Multipart upload and do DI check for uploaded object.

        1. Initiate multipart upload.
        2. Upload parts with aligned, unaligned part size.
        3. ListParts to see the parts uploaded.
        4. complete multipart upload.
        5. Compare the ETag.
        6. Download object and validate it with checksum.
        :param bucket_name: Name of the s3 bucket.
        :param object_name: Name of the s3 object.
        :param file_path: Absolute file path.
        :param total_parts: Number of parts that get uploaded.
        """
        download_path = os.path.join(
            os.path.split(file_path)[0], f"mp-download-{perf_counter_ns()}.txt")
        try:
            random = kwargs.get("random", False)
            file_size = kwargs.get("file_size", 10)  # should be multiple of 1MB
            LOGGER.info("Create multipart upload.")
            response = self.create_multipart_upload(bucket_name, object_name)
            mpu_id = response[1]["UploadId"]
            LOGGER.info("Upload the multipart.")
            if random:
                chunks = s3_utils.get_unaligned_parts(
                    file_path, total_parts=total_parts, random=random)
                _, parts = self.upload_parts_sequential(
                    mpu_id, bucket_name, object_name, parts=chunks)
                parts = sorted(parts, key=lambda x: x['PartNumber'])
            else:
                _, parts = self.upload_parts(
                    mpu_id, bucket_name, object_name, file_size, total_parts=total_parts,
                    multipart_obj_path=file_path)
            uploaded_checksum = s3_utils.calc_checksum(file_path)
            LOGGER.info("Do ListParts to see the parts uploaded.")
            self.list_parts(mpu_id, bucket_name, object_name)
            LOGGER.info("Get the part details and perform CompleteMultipartUpload.")
            LOGGER.info("parts: %s", parts)
            response = self.complete_multipart_upload(mpu_id, parts, bucket_name, object_name)
            upload_etag = response[1]["ETag"]
            LOGGER.info("Get the uploaded object")
            resp = self.get_object(bucket_name, object_name, ranges="bytes=1-")
            get_etag = resp['ETag']
            LOGGER.info("Compare ETags")
            if upload_etag != get_etag:
                raise Exception(f"Failed to match ETag: {upload_etag}, {get_etag}")
            LOGGER.info("Matched ETag: %s, %s", upload_etag, get_etag)
            LOGGER.info("Compare checksum by downloading object.")
            resp = self.object_download(bucket_name, object_name, download_path)
            LOGGER.info(resp)
            downloaded_checksum = s3_utils.calc_checksum(download_path)
            if uploaded_checksum != downloaded_checksum:
                raise Exception(f"Failed to match checksum: "
                                f"{uploaded_checksum}, {downloaded_checksum}")
            LOGGER.info("Matched checksum: %s, %s", uploaded_checksum, downloaded_checksum)
        except Exception as error:
            LOGGER.exception(ERR_MSG, S3MultipartTestLib.simple_multipart_upload.__name__, error)
            raise CTException(err.S3_CLIENT_ERROR, error) from error
        finally:
            if os.path.exists(download_path):
                os.remove(download_path)

        return response
