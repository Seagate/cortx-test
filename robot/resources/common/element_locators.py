"""
 File for maintaining web locators
"""
# Login page locators
CSM_USERNAME_ID = 'username'
CSM_PASSWORD_ID = 'password'
SIGNIN_BUTTON_ID = 'login-userbtn'
CSM_LOGIN_FAIL_MSG_ID = 'login-failsmsg'

# CSM Dashboard Locators
LOGGED_IN_USER_NAME_ID = 'header-username'

# Menus
MANAGE_MENU_ID = 'Manage'
S3_ACCOUNTS_TAB_ID = 's3accountstab'
SETTINGS_ID = 'Settings'
EMAIL_NOTIFICATION_ID = 'goToNotifications'

#S3 Config
S3_ACCOUNTS_TABLE_XPATH = '//*[@id="s3-datatable"]//table/tbody/tr/td'
S3_Account_NUMBER_OF_ROWS = '//*[@id="s3-datatable"]//table/tbody/tr'
S3_Account_NUMBER_OF_COLUMNS = '//*[@id="s3-datatable"]//table/tbody/tr[1]/td'

#CSM User section
CSM_USERS_TABLE_XPATH = '//*[@id="localuser-tabledata"]//table'
CSM_USERS_NUMBER_OF_ROWS_XPATH = '//*[@id="localuser-tabledata"]//table/tbody/tr[2]'
CSM_USERS_NUMBER_OF_COLUMNS_XPATH = '//*[@id="localuser-tabledata"]//table/tbody/tr[1]/td'
CSM_USER_EDIT_XPATH = '//*[@id="localuser-tabledata"]//table//td[contains(text(), "{0}")]//following-sibling::td//img[@id="localuser-editicon"]'
CSM_USER_DELETE_XAPTH = '//*[@id="localuser-tabledata"]//table//td[contains(text(), "{0}")]//following-sibling::td//img[@id="localuser-deleteicon"]'
CSM_TABLE_ELEMENTS_XPATH = '//*[@id="localuser-tabledata"]//table//tbody//tr//td'
ADMINISTRATIVE_USER_TAB_ID = "userstab"
ADD_USER_BUTTON_ID = "btnLocalAddNewUser"
ADD_USER_USER_NAME_INPUT_BOX_ID = "txtLocalHostname"
ADD_USER_PASSWORD_INPUT_ID = "txtLocalPass"
ADD_USER_CONFIRM_PASSWORD_INPUT_ID = "txtLocalConfirmPass"
ADD_USER_EMAIL_ID_INPUT_ID = "useremail"
CREATE_NEW_CSM_USER_BUTTON_ID = "btnLocalCreateUser"
CANCEL_NEW_CSM_USER_BUTTON_ID = "lblLocalCancel"
ADD_MANAGE_USER_RADIO_BUTTON_ID = "lblLocalManage"
ADD_MONITOR_USER_RADIO_BUTTON_ID = "lblLocalMonitor"
NEW_USER_CONFIRM_OK_BUTTON_ID = "user-dialog-close-btn"
INVALID_LOCAL_USER_MSG_ID = "localuser-invalid"
PASSWORD_MISS_MATCH_MSG_ID = "localuser-confirmpassword-notmatch"
CONFIRM_DELETE_BOX_BTN_ID = "confirmation-dialogbox-btn"
