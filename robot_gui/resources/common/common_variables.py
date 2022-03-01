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
"""
# File for maintaining common variables
"""

# Common variables required for GUI access
# URL's required to connect to the CSM GUI
CSM_URL = "https://10.230.246.58:28100/#/"
SW_UPDATE_URL = "http://cortx-storage.colo.seagate.com/releases/eos/github/main/centos-7.8.2003/{0}/prod/iso/cortx-2.0.0-{0}-single.iso"
FW_UPDATE_URL = "http://ssc-nfs-srvr2.pun.seagate.com/sw-installs/5U84-FW/GN265R008-04.bin"
SSL_URL = "http://cftic2.pun.seagate.com/tools/SSL/"

#  Login page msg.
LOGIN_FAILED_MESSAGE = 'Login failed !'

# Add Infra variables
BROWSER = "chrome"

# Expected value
S3_ACCOUNT = 'tests3account'
CSM_USER = 'monitoruser'
INVALID_LOCAL_USER = ["abc", "account@123", "!@#$%^&*()~", "user"*15]
HIDDEN_TYPE_ELEMENT = "password"
INVALID_USER_TYPE_MSG = "Invalid username."
INVALID_PASSWORDS_LIST = ["abc", "QWERTYUIIOP",
                          "qwertyuiop", "1234567890", "abcDFG1234", "!@#$%^&*()~"]
INVALID_PASSWORD_MSG = "Invalid password."
INVALID_USER_TYPE_MESSAGE = "Invalid username."
MISSMATCH_PASSWORD_MESSAGE = "Passwords do not match."

# S3 Expected Messages
INVALID_S3_ACCOUNT_MESSAGE = 'Invalid account name.'
INVALID_S3_EMAIL_MESSAGE = 'Invalid email id.'
INVALID_S3_PASSWORD_MESSAGE = 'Invalid password.'
INVALID_IAM_PASSWORD_MESSAGE = 'Invalid password.'
INVALID_S3_CONFIRM_PASSWORD_MESSAGE = 'Passwords do not match'
DUPLICATE_S3_ACCOUNT_ALERT_MESSAGE = 'The request was rejected because it attempted to create an account that already exists.'
PASSWORD_REQUIRED_MESSAGE = 'Password is required.'
NON_EMPTY_S3_ACCOUNT_MESSAGE = 'Account cannot be deleted as it owns some resources.'

# About Section
COMMON_NAME_SSL_MESSAGE = 'seagate.com'
COUNTRY_NAME_SSL_MESSAGE = 'IN'
LOCALITY_NAME_SSL_MESSAGE = 'Pune'
ORGANIZATION_NAME_SSL_MESSAGE = 'Seagate Tech'
S3_ACCOUNT_NAME_SAME_AS_CSM_USER_MESSAGE = "CSM user with same username already exists."\
                                           " S3 account name cannot be similar to an existing CSM user name"
S3_TABLE_HEADER_ACCOUNTNAME = 'Access key'
S3_TABLE_HEADER_SECRET_KEY = 'Secret key'
S3_TABLE_HEADER_ACTION = 'Action'
ACCESS_KEY_GENERATED_MESSAGE = 'Access key created'

# IAM Users Messages
IAM_USER_USERNAME_TOOLTIP_MSG = "The username must be of minimum 1 characters and maximum 64 characters"
IAM_USER_PASSWD_TOOLTIP_MSG = "Password must contain: Minimum 8 characters"
IAM_USER_PASSWD_MISSMATCH_MSG = "Passwords do not match"
SECRET_KEY_VALUE = "XXXX"
IAMUSER_ACCESS_KEY_HEADERS = ['Access key', 'Secret key', 'Key Status', 'Action']
DUPLICATE_IAM_USER_ERROR_MSG = "The request was rejected because it attempted to create or update a resource that already exists."
IAM_USER_LIMIT_ERROR_MSG = "The request was rejected because maximum limit(i.e 1000) of user creation has exceeded."

# Alerts
TEST_COMMENT = "Test Comment"

# Pre-boarding
EMAIL_DOMAIN = "@seagate.com"

# Buckets
BUCKET_NAME_POLICY_TEXT = "The bucket name must be of minimum 4 characters and maximum 56 characters."\
                          " Only lowercase, numbers, dash(-) and dot (.) are allowed."\
                          " The bucket name cannot start and end with a dash (-) or dot(.)."
DUPLICATE_BUCKET_NAME_ALERT_MESSAGE = "The bucket you tried to create already exists, and you own" \
                                      " it."
POLICY_FORM_HEADING = "JSON policy"
INVALID_POLICY_MSG = "Policy has invalid resource"

# Desktop
TOTAL_CAPACITY_LABEL_VALUE = "Total"
TOTAL_AVAILABLE_LABEL_VALUE = "Available"
TOTAL_USED_LABEL_VALUE = "Used"
CAPACITY_WIDGET_LABEL_VALUE = "Capacity"

#Audit Logs
Audit_log_days = ["One day", "Two days", "Three days",
                  "Four days", "Five days", "Six days", "Seven days"]

#Health Table
HEALTH_STATUS_COLUMN = 3
HEALTH_CLUSTER_OFFSET = 1
HEALTH_NODE_OFFSET = 4

#CSM User Table
CSM_ROLE_COLUMN = 2
CSM_USERNAME_COLUMN = 3
CSM_TEST_ROW_VALUE = "20 rows"
CSM_TEST_DEFAULT_COUNT = "11"
CSM_TEST_ROW_FIVE = "5 rows"
CSM_TEST_DEFAULT_DROPDOWN_VALUE = "10 rows"
CSM_MAX_ROW_VALUE = "200 rows"
CSM_SEARCH_CONTENTS = ['Role', 'Username']
