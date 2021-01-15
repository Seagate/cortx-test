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
# -*- coding: utf-8 -*-
# !/usr/bin/python

#: NWORKERS specifies number of worker (python) threads  in a worker pool.
NWORKERS = 32

#: NGREENLETS specifies number of greenlets in a thread. These greenlets will run in parallel.
NGREENLETS = 32

class Rest():
    # REST LIB
    EXCEPTION_ERROR = "Error in"
    SSL_CERTIFIED = "https://"
    NON_SSL = "http://"
    JOSN_FILE = "json_report.json"
    DELETE_SUCCESS_MSG = "Account Deleted Successfully."
    S3_ACCOUNTS = "s3_accounts"
    ACC_NAME = "account_name"
    ACC_EMAIL = "account_email"
    SECRET_KEY = "secret_key"
    IAMUSERS = "iam_users"
    ACCESS_KEY = "access_key"
    USER_NAME = "user_name"
    USER_ID = "user_id"
    IAM_USER = "test_iam_user"
    IAM_PASSWORD = "Seagate@123"
    ARN = "arn"
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    CONFLICT = 409
    SUCCESS_STATUS = 200
    FORBIDDEN = 403
    METHOD_NOT_FOUND = 404
    SUCCESS_STATUS_FOR_POST = 201
    USER_DATA = "{\"username\": \"testusername\", \"password\": \"Testuser@123\", \"roles\": [\"user_role\"],\"email\":\"testmonitoruser@seagate.com\",\"alert_notification\":true}"
    MISSING_USER_DATA = "{\"username\": \"testusername\", \"roles\": [\"user_role\"]}"
    CONTENT_TYPE = {'Content-Type': 'application/json'}
    BUCKET_NAME = "bucket_name"
    BUCKET = "buckets"
    NAME = "name"
    LOGIN_PAYLOAD = "{\"username\":\"$username\",\"password\":\"$password\"}"
    BUCKET_PAYLOAD = "{\"bucket_name\":\"buk$value\"}"
    BUCKET_POLICY_PAYLOAD = "{\"Statement\": [{\"Action\": [\"s3:$s3operation\"],\"Effect\": \"$effect\",\"Resource\": \"arn:aws:s3:::$value/*\",\"Principal\": \"$principal\"}]}"
    BUCKET_POLICY_PAYLOAD_IAM = "{\"Statement\": [{\"Action\": [\"s3:$s3operation\"],\"Effect\": \"$effect\",\"Resource\": \"arn:aws:s3:::$value/*\",\"Principal\": {\"AWS\":\"$principal\"}}]}"
    IAM_USER_DATA_PAYLOAD = "{\"user_name\": \"$iamuser\",\"password\": \"$iampassword\",\"require_reset\": $requireresetval}"
    IAM_USER_LOGIN_PAYLOAD = "{\"username\":\"$username\",\"password\":\"$password\"}"
    MULTI_BUCKET_POLICY_PAYLOAD = "{\"Statement\": [{\"Action\": [\"s3:$s3operation1\",\"s3:$s3operation2\"],\"Effect\": \"$effect\",\"Resource\": \"arn:aws:s3:::$value/*\",\"Principal\": {\"AWS\":\"$principal\"}}]}"
    SORT_BY_ERROR = "{\'sort_by\': [\'Must be one of: user_id, username, user_type, created_time, updated_time.\']}"
    CSM_USER_LIST_OFFSET = 1
    CSM_USER_LIST_LIMIT = 5
    CSM_USER_LIST_SORT_BY = "username"
    CSM_USER_LIST_SORT_DIR = "asc"
    CSM_NUM_OF_USERS_TO_CREATE = 5
    RANDOM_NUM_START = 3
    RANDOM_NUM_END = 9
    SORT_DIR_ERROR = "{\'sort_dir\': [\'Must be one of: desc, asc.\']}"
    CSM_USER_LIST_OFFSET = 1
    CSM_USER_LIST_LIMIT = 5
    CSM_USER_LIST_SORT_BY = "username"
    CSM_USER_LIST_SORT_DIR = "asc"
    CSM_NUM_OF_USERS_TO_CREATE = 5
    SORT_BY_EMPTY_PARAM_ERROR_RESPONSE = {
        'error_code': '4099', 'message_id': "{'sort_by': ['Must be one of: user_id, username, user_type, created_time, updated_time.']}", 'message': 'Invalid Parameter for alerts', 'error_format_args': None}
    NODE_ID_OPTIONS= {"storage": "storage_encl", "node": "node:{}{}"}
    HEALTH_SUMMARY_INSTANCE = "health_summary"
    HEALTH_SUMMARY_SCHEMA = {
        "type": "object",
        "properties": {
            "total": { "type": "number" },
            "fault": { "type": "number" },
            "good":  { "type": "number" }
        },
        "required": ["total", "good"]
    }