"""
# File for maintaining common variables
"""

# Common variables required for GUI access
# URL's required to connect to the CSM GUI
CSM_URL = "https://10.230.246.58:28100/#/"

#Login page msg.
LOGIN_FAILED_MSG = 'Login failed !'

# Add Infra variables
BROWSER = "chrome"

#Expected value
S3_ACCOUNT = 'tests3account'
CSM_USER = 'monitoruser'
COMMON_PASSWORD = "Seagate@123"
INVALID_LOCAL_USER = ["abc", "account@123", "!@#$%^&*()~", "user"*15]
HIDDEN_TYPE_ELEMENT = "password"
INVALID_USER_TYPE_MSG = "Invalid username."
MISSMATCH_PASSWORD_MSG = "Passwords do not match."