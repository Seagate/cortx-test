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
# -*- coding: utf-8 -*-
# !/usr/bin/python

"""All common error constants string from cortx-test."""

# S3 errors for Cortx s3 and RGW S3
RGW_ERR_LONG_OBJ_NAME = ("An error occurred (InvalidObjectName) when calling the PutObject "
                        "operation: Unknown")
CORTX_ERR_LONG_OBJ_NAME = ("An error occurred (KeyTooLongError) when calling the PutObject "
                          "operation: Your key is too long.")
RGW_ERR_WRONG_JSON = ("An error occurred (InvalidPart) when calling the CompleteMultipartUpload "
                     "operation: Unknown")
CORTX_ERR_WRONG_JSON = ("An error occurred (InvalidPart) when calling the CompleteMultipartUpload "
                        "operation: One or more of the specified parts could not be found. The "
                        "part might not have been uploaded, or the specified entity tag might not "
                        "have matched the part's entity tag.")
RGW_ERR_DUPLICATE_BKT_NAME = ("An error occurred (BucketAlreadyExists) when calling the "
                             "CreateBucket operation: Unknown")
CORTX_ERR_DUPLICATE_BKT_NAME = ("An error occurred (BucketAlreadyOwnedByYou) when calling"
                               "the CreateBucket operation: Your previous request to create "
                               "the named bucket succeeded and you already own it.")
RGW_ERR_COPY_OBJ = ("An error occurred (InvalidRequest) when calling the CopyObject operation:"
                    " The specified copy source is larger than the maximum allowable size for a "
                    "copy source: 5368709120")
CORTX_ERR_COPY_OBJ = ("An error occurred (InvalidRequest) when calling the CopyObject operation:"
                     " The specified copy source is larger than the maximum allowable size for a "
                     "copy source: 5368709120")
RGW_ERR_COPY_OBJ_METADATA = ("An error occurred (InvalidRequest) when calling the CopyObject "
                            "operation: This copy request is illegal because it is trying to "
                            "copy an object to itself without changing the object's metadata, "
                            "storage class, website redirect location or encryption attributes.")
CORTX_ERR_COPY_OBJ_METADATA = ("An error occurred (InvalidRequest) when calling the CopyObject "
                              "operation: This copy request is illegal because it is trying to "
                              "copy an object to itself without changing the object's metadata, "
                              "storage class, website redirect location or encryption attributes.")
RGW_HEAD_OBJ_ERR = ("An error occurred (404) when calling the HeadObject operation: Not Found")
CORTX_HEAD_OBJ_ERR = ("An error occurred (404) when calling the HeadObject operation: Not Found")

ACCOUNT_ERR = "attempted to create an account that already exists"
ACCESS_DENIED_ERR_KEY = "AccessDenied"
CANNED_ACL_GRANT_ERR = "Specifying both Canned ACLs and Header Grants is not allowed"
DOWNLOAD_OBJ_ERR_KEY = "404"
DUPLICATE_USER_ERR_KEY = "EntityAlreadyExists"
INVALID_ACCESSKEY_ERR_KEY = "InvalidAccessKeyId"
NO_BUCKET_OBJ_ERR_KEY = "NoSuchBucket"
NO_SUCH_KEY_ERR = "NoSuchKey"
NO_SUCH_UPLOAD_ERR = "NoSuchUpload"
NO_BUCKET_NAME_ERR = "Required parameter bucket_name not set"

#S3 Bucket Tagging
BKT_SET_TAG_ERR = "NoSuchTagSetError"
BKT_INVALID_TAG_ERR = "InvalidTagError"
BKT_TAG_DUPLICATE_KEY_ERR = "MalformedXML"
BKT_INVALID_NAME_ERR = "InvalidBucketName"
BKT_SPECIAL_CHARACTER_ERR = "Parameter validation failed"
OBJ_ACL_INVALID_ARGUMENT_ERR = "Invalid Argument"
INVALID_ACL_ERR = "InvalidACL"
BKT_NOT_EMPTY_ERR = "BucketNotEmpty"
BKT_HEAD_NOT_FOUND = "Not Found"
ACC_NOT_EMPTY_ERR = "AccountNotEmpty"
MAX_DUR_EXCEED_ERR = "MaxDurationIntervalExceeded"
CRED_EXPIRE_ERR = "ExpiredCredential"
CRED_INVALID_ERR = "InvalidCredentials"
NO_SUCH_ENTITY_ERR = "NoSuchEntity"
MULTIPART_INVALID_PART_ERR = "InvalidPart"
MULTIPART_LIST_PART_LESS_ERR = "EntityTooSmall"
MULTIPART_LIST_PART_LARGE_ERR = "EntityTooLarge"
META_DATA_HEADER_EXCEED_ERR = "MetadataTooLarge"
MULTI_BUCKET_DELETE_ERR ="MaxMessageLengthExceeded"

#BucketPolicy
BKT_POLICY_RESOURCE_ERR = "Action does not apply to any resource(s) in statement"
BKT_POLICY_INVALID_RESOURCE_ERR = "Policy has invalid resource"
BKT_POLICY_INVALID_PRINCIPAL_ERR = "Invalid principal in policy"
BKT_POLICY_MISSING_FIELD_ERR = "Missing required field"
BKT_POLICY_UNKNOWN_FIELD_ERR = "Unknown field"
BKT_POLICY_INVALID_ACTION_ERR = "invalid action"
BKT_POLICY_EMPTY_ACTION_ERR = "Action cannot be empty"
BKT_POLICY_INVALID_JSON_ERR = "This policy contains invalid Json"
BKT_POLICY_NO_SUCH_ERR = "NoSuchBucketPolicy"

#S3 versioning head obj error
S3_VERSION_NOT_FOUND_GET_OBJ = "The specified version does not exist"
S3_VERSION_NOT_FOUND_HEAD_OBJ = "Not Found"
S3_VERSION_INVALID_GET_OBJ = "The specified version does not exist"
S3_VERSION_EMPTY_ID_GET_OBJ = "Version id cannot be the empty string"
S3_VERSION_ID_HEAD_OBJ = "Bad Request"
