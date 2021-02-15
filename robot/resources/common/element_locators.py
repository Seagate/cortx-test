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
LOG_OUT_ID = 'logout-icon'

# Menus
MANAGE_MENU_ID = 'Manage'
S3_ACCOUNTS_TAB_ID = 's3accountstab'
SETTINGS_ID = 'Settings'
EMAIL_NOTIFICATION_ID = 'goToNotifications'
IAM_USER_TAB_ID = "s3iamuserstab"
DASHBOARD_MENU_ID = "Dashboard"
MAINTENANCE_MENU_ID = 'Maintenance'

# Alerts
ALERT_IMAGE_ID_1='alert-zoom'  # from Dashbard
ALERT_IMAGE_ID_2='alert-dotwhite'  # from All pages
ALERT_COMMENT_SAVE_BUTTON_ID = 'alert-save-commnetbtn'
ALERT_COMMENT_CLOSE_BUTTON_ID = 'alert-close-comment-dialogbtn'
ALERT_COMMENT_CLOSE_IMAGE_ID = 'alert-closeadd-comment-dialog'
ALERT_COMMENT_TEXT_ID= 'alert-comment-textarea'
ALERT_DETAILS_PAGE_ICON_XPATH = '//*[@id="tblAlertLarge"]/div/table/tbody/tr[1]/td[5]/img'
ALERT_COMMENT_ICON_XPATH = '//*[@id="tblAlertLarge"]/div/table/tbody/tr[1]/td[5]/div/div'
ALERT_ACKNOWLEDGE_ICON_XPATH = '//*[@id="tblAlertLarge"]/div/table/tbody/tr[1]/td[5]/div/span[2]/div'

#  S3 Config
S3_ACCOUNTS_TABLE_XPATH = '//*[@id="s3-datatable"]//table/tbody/tr/td'
S3_ACCOUNT_NUMBER_OF_ROWS = '//*[@id="s3-datatable"]//table/tbody/tr'
S3_ACCOUNT_NUMBER_OF_COLUMNS = '//*[@id="s3-datatable"]//table/tbody/tr[1]/td'
ADD_S3_ACCOUNT_BUTTON_ID = 's3-addnewuserbtn'
CREATE_S3_ACCOUNT_BUTTON_ID = 's3-crete-accountbtn'
CANCEL_S3_ACCOUNT_ID = 's3-account-cancelbtn'
S3_ACCOUNT_NAME_FIELD_ID = 'accountName'
S3_ACCOUNT_EMAIL_FIELD_ID = 'accountEmail'
S3_ACCOUNT_PASSWORD_FIELD_ID = 'accountPassword'
S3_ACCOUNT_CONFIRM_PASSWORD_FIELD_ID = 'confirmPassword'
DOWNLOAD_AND_CLOSE_BUTTON_ID = 's3-download-csv'
DELETE_S3_ACCOUNT_ID = 's3-delete-account'
CONFIRM_DELETE_S3_ACCOUNT_ID = 'confirmation-dialogbox-btn'
INVALID_S3_ACCOUNT_NAME_MSG_ID = 's3account-invalid'
INVALID_S3_EMAIL_MSG_ID = 's3-email-invalid'
INVALID_S3_PASSWORD_MSG_ID = 's3-password-invalid'
INVALID_S3_CONFIRM_PASS_MSG_ID = 's3-password-notmatch'
DUPLICATE_S3_ACCOUNT_MSG_ID = 'dialog-message-label'
CLOSE_DUPLICATE_ACCOUNT_ALERT_MESSAGE_ID = 'close-msg-dialogbox'
EDIT_S3_ACCOUNT_OPTION_ID = 's3-edit-account'
UPDATE_S3_ACCOUNT_PASSWORD_FIELD_ID = 'accountPasswordEdit'
UPDATE_S3_ACCOUNT_CONFIRM_PASSWORD_FIELD_ID = 'confirmPasswordEdit'
UPDATE_S3_ACCOUNT_BTN_ID = 'btnEditPassword'
INVALID_S3_ACCOUNT_PASSWORD_MSG_ID = 's3-editpassword-invalid'
PASSWORD_REQUIRED_MSG_ID = 's3-editpassword-required'
CONFIRM_PASSWORD_ERROR_MSG_ID = 's3-editpassword-notmatch'
SELECT_FROM_PAGINATION_XPATH = "//*[@id='s3-datatable']//i[contains(@class,'mdi-menu-down')]"
SELECT_ALL_RECORDS_FROM_PAGINATION_XPATH = "//*[contains(@id,'all-list-item-')]"
S3_ACCOUNT_NAME_SAME_AS_CSM_USER_ID = 'dialog-message-label'
CLOSE_ALERT_BOX_FOR_DUPLICATE_USER_ID = 'close-msg-dialogbox'
ACCESS_KEY_TABLE_HEADERS_XPATH = '//*[@id="s3-accesskey-datatable"]//table/tr/th/span'
ACCESS_KEY_TABLE_DATA_XPATH = '//*[@id="s3-accesskey-datatable"]//table/tbody/tr/td'
ADD_S3_ACCOUNT_ACCESS_KEY_ID = 's3-accesskey-add-btn'
ACCESS_KEY_GENERATE_MEG_XPATH = '//*[@id="app"]//div[@class="v-card v-sheet theme--light"]//span'
ACCESS_KEY_DOWNLOAD_AND_CLOSE_BTN_ID = 'download-csv-dialog-btn'
DELETE_ACCESS_KEY_ID = 's3-accesskey-datatable-delete-{0}'
NEW_ACCESS_KEY_TABLE_XPATH = '//*[@id="download-csv-dialog-datatable"]/tr/td'
CONFIRM_DELET_ACCESS_KEY_ID = 'confirmation-dialogbox-btn'
EDIT_S3_ACCOUNT_OPTIONS_XPATH = '//*[@id="app"]//div[@class ="py-0 col-5 col"]//input'

# Preboarding 
WELCOME_START_BUTTON_ID = 'welcome-startbtn'
ELUA_BUTTON_ID = 'show-license-agreement-dialogbtn'
LICENSE_BUTTON_ID = 'license-acceptagreement'
LICENSE_CANCLE_BUTTON_ID = 'license-cancelagreementbtn'
LICENSE_CANCLE_IMAGE_ID = 'license-cancelagreementicon'
LICENSE_TITLE_ID = 'agreement-title'
LICENSE_DATA_ID = 'agreement-data'

#  CSM User section
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
# CFT
CSM_STATS_CHART_ID = 'line_chart'
DASHBOARD_ALERT_SECTION_ID = 'alertMediumContainer'
DELETE_USER_BTN_ID = "localuser-deleteicon"
INVALID_PASSWORD_MSG_ID = "localuser-password-invalid"
CHANGE_PASSWORD_BTN_ID = "change-password-text"
UPDATE_USER_BTN_ID = "lblLocalApplyInterface"
CONFIRM_NEW_PASSWORD_INPUT_ID = "txtLocalConfirmNewPass"
OLD_PASSWORD_INPUT_ID = "txtLocalOldPass"
PAGINATION_BAR_XPATH = "//div[@class='v-data-footer']"
PAGIANTION_PAGE_OPTIONS_XPATH = "//*[@role='option']"
RADIO_BTN_VALUE_XPATH = "//*[@type='radio']"
PAGINATION_LIST_ICON_XPATH = "//*[@class='v-select__selection v-select__selection--comma']"

#  IAM Users
ADD_IAM_USER_BUTTON_ID = "iam-user-create-formbtn"
CREATE_IAM_USER_USERNAME_ID = "userName"
CREATE_IAM_USER_PASSWORD_ID = "userPassword"
CREATE_IAM_USER_CONFIRM_PASSWORD_ID = "confirmPassword"
CREATE_IAM_USER_BUTTON_ID = "iam-create-userbtn"
CANCEL_IAM_USER_BUTTON_ID = "iam-usercancelbtn"
IAM_USER_TOOLTIP_ID = "tooltip-msg"
IAM_USER_TOOLTIP_USER_IMAGE_ID = "Username*"
IAM_USER_PASSWD_TOOLTIP_IMAGE_ID = "Password*"
IAM_USER_PASSWD_MISSMATCH_ID = "iam-confirmpass-notmatch"
IAM_USER_DOWNLOAD_CSV_BUTTON_ID = "iam-downloadcsvfile"
IAM_USER_DELETE_ICON_XPATH = '//tr[@id="{0}"]//*[@id="iam-delete-user"]'
IAM_USER_ROW_ELEMENT_XPATH = '//tr[@id="{0}"]'
DUPLICATE_USER_MSG_ID = "dialog-message-label"
IAM_USER_USERNAME_LABEL_ID = "iam-userlbl"
IAM_USER_PASSWORD_LABEL_ID = "iam-passwordlbl"
IAM_USER_CONFIRM_PASSWORD_LABEL_ID = "iam-confirmpasslbl"

#About Section
ABOUT_VIEW_ID = 'menu-actionmanagebtn'
ISSUER_DETAILS_TAB_ID = 'Issuertab'
SUBJECT_DETAILS_TAB_ID = 'Subjecttab'
ISSUER_COMMON_NAME_VALUE_ID = 'issuer_common_name_value'
ISSUER_COUNTRY_NAME_VALUE_ID = 'issuer_country_name_value'
ISSUER_LOCALITY_NAME_VALUE_ID = 'issuer_locality_name_value'
ISSUER_ORGANIZATION_VALUE_ID = 'issuer_organization_name_value'
SUBJECT_COMMON_NAME_VALUE_ID = 'subject_common_name_value'
SUBJECT_COUNTRY_NAME_VALUE_ID = 'subject-country_name_value'
SUBJECT_LOCALITY_NAME_VALUE_ID = 'subject_locality_name_value'
SUBJECT_ORGANIZATION_VALUE_ID = 'subject_organization_name_value'
