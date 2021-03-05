"""
# File for maintaining common variables
"""

# Common variables required for GUI access
# URL's required to connect to the CSM GUI
CSM_URL = "https://10.230.246.58:28100/#/"
SW_UPDATE_URL = "http://cortx-storage.colo.seagate.com/releases/eos/github/main/centos-7.8.2003/{0}/prod/iso/cortx-2.0.0-{0}-single.iso"

#  Login page msg.
LOGIN_FAILED_MESSAGE = 'Login failed !'

# Add Infra variables
BROWSER = "chrome"

#  Expected value
S3_ACCOUNT = 'tests3account'
CSM_USER = 'monitoruser'
INVALID_LOCAL_USER = ["abc", "account@123", "!@#$%^&*()~", "user"*15]
HIDDEN_TYPE_ELEMENT = "password"
INVALID_USER_TYPE_MSG = "Invalid username."
MISSMATCH_PASSWORD_MSG = "Passwords do not match."
INVALID_PASSWORDS_LIST = ["abc", "QWERTYUIIOP",
                          "qwertyuiop", "1234567890", "abcDFG1234", "!@#$%^&*()~"]
INVALID_PASSWORD_MSG = "Invalid password."
INVALID_USER_TYPE_MESSAGE = "Invalid username."
MISSMATCH_PASSWORD_MESSAGE = "Passwords do not match."

# S3 Expected Messages
INVALID_S3_ACCOUNT_MESSAGE = 'Invalid account name.'
INVALID_S3_EMAIL_MESSAGE = 'Invalid email id.'
INVALID_S3_PASSWORD_MESSAGE = 'Invalid password.'
INVALID_S3_CONFIRM_PASSWORD_MESSAGE = 'Passwords do not match'
DUPLICATE_S3_ACCOUNT_ALERT_MESSAGE = 'The request was rejected because it ' \
                                     'attempted to create an account that already exists.'
PASSWORD_REQUIRED_MESSAGE = 'Password is required.'


# About Section
COMMON_NAME_SSL_MESSAGE = 'seagate.com'
COUNTRY_NAME_SSL_MESSAGE = 'IN'
LOCALITY_NAME_SSL_MESSAGE = 'Pune'
ORGANIZATION_NAME_SSL_MESSAGE = 'Seagate Tech'
S3_ACCOUNT_NAME_SAME_AS_CSM_USER_MESSAGE = 'CSM user with same username as ' \
                                           'passed S3 account name already exists'
S3_TABLE_HEADER_ACCOUNTNAME = 'Access key'
S3_TABLE_HEADER_SECRET_KEY = 'Secret key'
S3_TABLE_HEADER_ACTION = 'common.action'
ACCESS_KEY_GENERATED_MESSAGE = 'Access key created'

#  IAM Users Messages
IAM_USER_USERNAME_TOOLTIP_MSG = "The username must be of minimum 4 characters and maximum 56 characters"
IAM_USER_PASSWD_TOOLTIP_MSG = "Password must contain: Minimum 8 characters"
IAM_USER_PASSWD_MISSMATCH_MSG = "Passwords do not match"
DUPLICATE_IAM_USER_ERROR_MSG = "The request was rejected because it attempted to create or update a resource that already exists."
