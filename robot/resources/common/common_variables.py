"""
# File for maintaining common variables
"""

# Common variables required for GUI access
# URL's required to connect to the CSM GUI
CSM_URL = "https://10.230.246.58:28100/#/"

#  Login page msg.
LOGIN_FAILED_MSG = 'Login failed !'

# Add Infra variables
BROWSER = "chrome"

#  Expected value
S3_ACCOUNT = 'tests3account'
CSM_USER = 'monitoruser'
INVALID_LOCAL_USER = ["abc", "account@123", "!@#$%^&*()~", "user"*15]
HIDDEN_TYPE_ELEMENT = "password"
INVALID_USER_TYPE_MSG = "Invalid username."
MISSMATCH_PASSWORD_MSG = "Passwords do not match."
INVALID_PASSWORDS_LIST = ["abc", "QWERTYUIIOP", "qwertyuiop", "1234567890", "abcDFG1234", "!@#$%^&*()~"]
INVALID_PASSWORD_MSG = "Invalid password."
