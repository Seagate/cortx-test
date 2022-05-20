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
 File for maintaining web locators
"""
# Login page locators
CSM_USERNAME_ID = 'username'
CSM_PASSWORD_ID = 'password'
SIGNIN_BUTTON_ID = 'login-userbtn'
CSM_LOGIN_FAIL_MSG_ID = 'login-failsmsg'
CHANGE_PASSWORD_ID = 'user-password'
CONFIRM_PASSWORD_ID = 'confirm-password'
PASSWORD_RESET_BUTTON_ID = 'reset-password-button'
PASSWORD_CHANGE_SUCESS_BUTTON_ID= 'confirmation-dialogbox-btn'

# CSM Dashboard Locators
LOGGED_IN_USER_NAME_ID = 'header-username'
USER_DROPDOWN_XPATH = "//*[@class='cortx-dropdown-container']"
LOG_OUT_ID = 'logout-link'
CAPACITY_TOTAL_LABEL_ID = 'capacity-total-text'
CAPACITY_AVAILABLE_LABEL_ID = 'capacity-available-text'
CAPACITY_USED_LABEL_ID = 'capacity-used-text'
CAPACITY_WIDGET_ID = 'capacityContainer'
CAPACITY_WIDGET_LABEL_ID = 'capacity-title'
CAPACITY_GRAPH_ID = 'gauge_capacity'
USED_CAPACITY_VALUE_XPATH = "//*[@id='capacity-used']/td[3]"
AVAILABLE_CAPACITY_VALUE_XPATH = "//*[@id='capacity-available']/td[3]"
TOTAL_CAPACITY_VALUE_XPATH = "//*[@id='capacity-total']/td[3]"

# Menus
MANAGE_MENU_ID = '//*[@class="v-application--wrap"]//*[contains(@id,"Manage")]'
ADMINISTRATIVE_USER_TAB_ID = "tab-1"
CSM_S3_ACCOUNTS_TAB_ID = 'tab-2'
SETTINGS_ID = 'Settings'
EMAIL_NOTIFICATION_ID = 'goToNotifications'
S3_ACCOUNTS_TAB_ID = 'tab-1'
S3_IAM_USER_TAB_ID = 'tab-2'
S3_BUCKET_TAB_ID   = 'tab-3'
DASHBOARD_MENU_ID = "Dashboard"
MAINTENANCE_MENU_ID = 'Maintenance'
AUDIT_LOG_TAB_ID = "goToAuditLog"
HEALTH_MENU_ID = 'Health'
SW_UPDATE_TAB_ID = "goToSoftware"
FW_UPDATE_TAB_ID = "goToFirmware"
LYVE_PILOT_MENU_ID= "Lyve Pilot"

# Health
GRAPHICAL_TAB_ID = 'tab-1'
TABULAR_TAB_ID = 'tab-2'
RESOURCE_TABLE_ROW_XPATH = '//*[@class="v-data-table cortx-table theme--light"]//table//tbody//tr'
RESOURCE_STATUS_XPATH = '//*[@class="v-data-table cortx-table theme--light"]//table//tbody//tr[{0}]//td[{1}]//div'
GRAPH_NODE_ID = 'g_0000'
GRAPH_NODE_ACTION_ID = 'show_actions_icon_0000'
GRAPH_NODE_ACTION_MENU_ID = 'g_action_menu_0000'
GRAPH_NODE_STOP_ID = 'rect_0000_stop'
GRAPH_NODE_SUCCESS_MSG_ID = 'prompt-dialog-message-label'
GRAPH_NODE_YES_ID = 'prompt-dialog-btn-yes'
GRAPH_NODE_INFO_MSG_ID = 'info-dialog-message-label'
GRAPH_NODE_OK_ID = 'info-dialog-btn-ok'
GRAPH_NODE_START_ID = 'rect_0000_start'
GRAPH_NODE_POWEROFF_ID = 'rect_0000_poweroff'
GRAPH_NODE_POWER_STORAGEOFF_ID = 'rect_0000_powerandstorageoff'
GRAPH_NODE_ACTION_TABLE_CLASS = '//div[@class="cortx-icon-btn cortx-option-icon"]'
GRAPH_NODE_STOP_TABLE_CLASS = '//span[@class="cortx-menu-icon cortx-stop-node-icon-online"]'
GRAPH_NODE_START_TABLE_CLASS = '//span[@class="cortx-menu-icon cortx-start-node-icon-online"]'
GRAPH_NODE_POWEROFF_TABLE_CLASS = '//span[@class="cortx-menu-icon' \
                                    ' cortx-power-off-node-icon-online"]'
GRAPH_NODE_POWER_STORAGEOFF_TABLE_CLASS = '//span[@class="cortx-menu-icon' \
                                            ' cortx-power-storage-off-node-icon-online"]'

# Settings
SETTINGS_NOTIFICATION_ID = 'menu-Email Notifications'
SETTINGS_NOTIFICATION_BUTTON_ID = 'goToNotifications'
SETTINGS_DNS_ID = 'menu-DNS'
SETTINGS_DNS_BUTTON_ID = 'goToDNS'
SETTINGS_NTP_ID = 'menu-NTP'
SETTINGS_NTP_BUTTON_ID = 'goToNTP'
SETTINGS_SSL_ID = 'menu-SSL Certificate'
SETTINGS_SSL_BUTTON_ID = 'goToSSL'
CHOOSE_SSL_UPDATE_FILE_BUTTON_ID = 'file'
UPLOAD_SSL_FILE_PEM_ID = 'btnUploadSSL'
INSTALL_SSL_FILE_PEM_ID = 'btnInstallFirmware'
CONFIRMAATION_INSTALL_SSL_ID = 'confirmation-dialogbox-btn'
SSL_PEM_FILE_NAME_XPATH = '//*[@id="app"]//div[@class ="container mt-0 ml-0"]/div[1]/div[1]/table/tr[2]/td[2]/label'
SSL_PEM_FILE_STATUS_XPATH= '//*[@id="app"]//div[@class ="container mt-0 ml-0"]/div[1]/div[1]/table/tr[1]/td[2]/label'

# Alerts
ALERT_IMAGE_1_ID = 'alert-zoom'  # from Dashbard
ALERT_COMMENT_SAVE_BUTTON_ID = 'alert-save-commnetbtn'
ALERT_COMMENT_CLOSE_BUTTON_ID = 'alert-close-comment-dialogbtn'
ALERT_COMMENT_CLOSE_IMAGE_ID = 'alert-closeadd-comment-dialog'
ALERT_MORE_DETAILS_CLOSE_ICON_ID = 'alert-showalert-details-dialogbox'
ALERT_COMMENT_TEXT_ID = 'alert-comment-textarea'
ALERT_TABLE_ID = 'tblAlertLarge'
NEW_ALERT_ID     = 'tab-1'
ACTIVE_ALERT_ID  = 'tab-2'
ALERT_HISTORY_ID = 'tab-3'
ALERT_IMAGE_XPATH = '//*[@class="cortx-logout-icon-container pr-9"]//div[1]//img'  # from All pages
ALERT_TABLE_XPATH = '//*[@id="tblAlertLarge"]//table//tbody//tr//td'
ALERT_TABLE_ROW_XPATH = '//*[@id="tblAlertLarge"]//table//tbody//tr'
ALERT_DETAILS_PAGE_ICON_XPATH = '//*[@id="tblAlertLarge"]/div/table/tbody/tr[1]/td[5]/img'
ALERT_MORE_DETAILS_ICON_XPATH = '//label[@class="cortx-text-md cortx-cursor-pointer"]'
ALERT_MORE_DETAILS_BODY_XPATH = '//*[@id="app"]//div[@class ="cortx-modal-container"]/div[1]/div[2]'
ALERT_MORE_DETAILS_CLOSE_ICON_XPATH = '//*[@id="app"]//div[@class ="cortx-modal-container"]/div[1]/div[1]/img[1]'
ALERT_COMMENT_ICON_XPATH = '//*[@id="tblAlertLarge"]/div/table/tbody/tr[1]/td[5]/div/div'
ALERT_ACKNOWLEDGE_ICON_XPATH = '//*[@id="tblAlertLarge"]/div/table/tbody/tr[1]/td[5]/div/span[2]/div'
ALERTS_COMMENT_TEXT_XPATH = '//*[@class="cortx-comment"]//span[@class="cortx-text-md"]'
PARTICULAR_ALERT_ACKNOWLEDGE_ICON_XPATH = "//td[contains(text(), '{0}')]//following-sibling::td//div[@class='cortx-icon-btn cortx-acknowledge-icon']"

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
UPDATE_S3_ACCOUNT_BUTTON_ID = 'btnEditPassword'
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
ACCESS_KEY_DOWNLOAD_AND_CLOSE_BUTTON_ID = 'download-csv-dialog-btn'
DELETE_ACCESS_KEY_ID = 's3-accesskey-datatable-delete-{0}'
NEW_ACCESS_KEY_TABLE_XPATH = '//*[@id="download-csv-dialog-datatable"]/tr/td'
CONFIRM_DELET_ACCESS_KEY_ID = 'confirmation-dialogbox-btn'
EDIT_S3_ACCOUNT_OPTIONS_XPATH = '//*[@id="app"]//div[@class ="py-0 col-5 col"]//input'
S3_ACCOUNT_RESET_PASSWORD_XPATH = '//td[contains(text(), "{0}")]//following-sibling::td//img[@id="iam-reset-password"]'
S3_ACCOUNT_REST_OPTION_ID = 'iam-reset-password'
S3_ACCOUNT_RESET_NEW_PASSWORD_ID = 'user-password'
S3ACCOUNT_INVALID_PASSWORD_ERROR_MSG_ID = 'iam-password-invalid-error'
S3ACCOUNT_MISS_MATCH_PASSWORD_ERROR_MSG_ID = 'iam-confirmpass-notmatch-error'
S3_ACCOUNT_POP_UP_CANCEL_BUTTON_ID = 'cancel-button'
S3_ACCOUNT_RESET_CONFIRM_PASSWORD_ID = 'confirm-password'
S3_ACCOUNT_RESET_PASSWORD_BUTTON_ID = 'reset-password-button'
S3_ACCOUNT_SUCCESS_MESSAGE_ID = 's3-success-dialog'
S3_ACCOUNT_SUCCESS_MESSAGE_BUTTON_ID = 'confirmation-dialogbox-btn'
S3_ACCOUNTS_TAB_S3_URL_TEXT_ID = "s3-account-manage-lbl"
S3_ACCOUNTS_TAB_COPY_S3_URL_ONE_ID = "copy-url-btn-0"
S3_ACCOUNTS_TAB_COPY_S3_URL_TWO_ID = "copy-url-btn-1"
S3_ACCOUNT_CREATION_POP_UP_TABLE_XPATH = "//*[@id='s3-secretekey-data']/tr/td"

# Preboarding
WELCOME_START_BUTTON_ID = 'welcome-startbtn'
ELUA_BUTTON_ID = 'show-license-agreement-dialogbtn'
LICENSE_ACCEPT_BUTTON_ID = 'license-acceptagreement'
LICENSE_CANCLE_BUTTON_ID = 'license-cancelagreementbtn'
LICENSE_CANCLE_IMAGE_ID = 'license-cancelagreementicon'
LICENSE_TITLE_ID = 'agreement-title'
LICENSE_DATA_ID = 'agreement-data'
EULA_CONTENT_MSG_XPATH = "//p[@data-v-1ad3de5e]"

#  CSM User section
CSM_USERS_TABLE_XPATH = '//*[@id="localuser-tabledata"]//table'
CSM_USERS_NUMBER_OF_ROWS_XPATH = '//*[@id="localuser-tabledata"]//table/tbody/tr[2]'
CSM_USERS_NUMBER_OF_COLUMNS_XPATH = '//*[@id="localuser-tabledata"]//table/tbody/tr[1]/td'
CSM_USER_EDIT_XPATH = '//td[3]//div[text()="{0}"]//parent::td//parent::tr//td[4]//div[@class="cortx-icon-btn cortx-edit-icon"]'
CSM_USER_DELETE_XAPTH = '//td[3]//div[text()="{0}"]//parent::td//parent::tr//td[4]//div[@class="cortx-icon-btn cortx-delete-icon"]'
CSM_TABLE_ELEMENTS_XPATH = '//*[@class="v-data-table cortx-table theme--light"]' \
                           '//table//tbody//tr//td'
CSM_TABLE_ROW_XPATH = '//*[@class="v-data-table cortx-table theme--light"]//table//tbody//tr'
CSM_TABLE_COLUMN_XPATH = '//*[@class="v-data-table cortx-table theme--light"]//table//tbody//tr[*]//td[{0}]'
ADD_USER_BUTTON_ID = "btnLocalAddNewUser"
ADD_USER_USER_NAME_INPUT_BOX_ID = 'txtUsername'
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
CONFIRM_DELETE_BOX_BUTTON_ID = "confirmation-dialogbox-btn"
UPDATE_USER_EMAIL_ID_INPUT_ID = "email"
UPDATE_USER_CONFIRM_PASSWORD_INPUT_ID = "txtLocalConfirmNewPass"
DELETE_ICON_MANAGE_USER_ID = "localuser-deleteadmin"
DELETE_S3_ACCOUNT_BY_CSM_USER_XPATH = "//td[contains(text(), '{0}')]//following-sibling::td//img[@id='s3-delete-account']"
CONFIRM_S3_ACCOUNT_DELETE_ID = "confirmation-dialogbox-btn"
ADD_ADMIN_USER_RADIO_BUTTON_ID = "lblLocalAdmin"
CSM_USER_SEARCH_BOX_XPATH = '//input[@placeholder="Search"]'
CSM_USER_SEARCH_ICON_ACTIVE_XPATH = '//div[@class="search-image active"]'
CSM_USER_SEARCH_ICON_XPATH = '//div[@class="search-image"]'
CSM_USER_FILTER_DROPDOWN_BUTTON_XPATH = '//div[@aria-haspopup="listbox"]'
CSM_FILTER_LIST_BUTTON_XPATH = '//*[@class="v-select-list v-card theme--light"]/div'
CSM_FILTER_LIST_CONTENT_XPATH = '//*[@class="v-list-item__title"]'
CSM_FILTER_ROLE_SELECTED_XPATH = '//div[contains(@aria-labelledby,"role-list")]'
CSM_FILTER_USERNAME_SELECTED_XPATH = '//div[contains(@aria-labelledby,"username-list")]'
CSM_FILTER_ROLE_SELECT_XPATH = '//div[contains(@id,"list-")]//div[contains(text(), "Role")]'
CSM_FILTER_USERNAME_SELECT_XPATH = '//div[contains(@id,"list-")]//div[contains(text(), "Username")]'

# CFT
CSM_STATS_CHART_ID = 'line_chart'
DASHBOARD_ALERT_SECTION_ID = 'alertMediumContainer'
INVALID_PASSWORD_MSG_ID = "localuser-password-invalid"
CHANGE_PASSWORD_BUTTON_ID = "change-password-text"
UPDATE_USER_BUTTON_ID = "lblLocalApplyInterface"
CONFIRM_NEW_PASSWORD_INPUT_ID = "txtLocalConfirmNewPass"
OLD_PASSWORD_INPUT_ID = "txtLocalOldPass"
PAGINATION_BAR_XPATH =  "//div[@class='v-data-footer']"
RADIO_BTN_VALUE_XPATH = "//*[@type='radio']"
CSM_PAGINATION_LIST_ICON_XPATH = '//*[@class="cortx-dropdown-title"]'
CSM_PAGINATION_BAR_XPATH = "//div[@class='container']"
CSM_PAGINATION_PAGE_OPTIONS_XPATH = '//*[@class="cortx-dropdown-container menu-on-top"]' \
                                    '//div[@class="cortx-dropdown-menu-item"]'
CSM_PAGINATION_PAGE_FIRST_LAST = "//*[@class='v-pagination__navigation " \
                                 "v-pagination__navigation--disabled']"
CSM_PAGINATION_PAGE_XPATH = "//*[@class='my-1 font-weight-bold v-pagination theme--light']" \
                            "//following::button"

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
IAM_USER_RESET_PASSWORD_ID = "iam-reset-password"
IAM_USER_RESET_PASSWORD_XPATH = '//tr[@id="{0}"]//*[@id="iam-reset-password"]'
IAM_USER_RESET_PASSWORD_DIALOG_ID = "s3-resetaccount-form"
IAM_USER_RESET_PAWWSORD_BUTTON_ID = "reset-password-button"
IAM_USER_RESET_NEW_PASSWORD_ID = "user-password"
IAM_USER_RESET_CONFIRM_PASSWORD_ID = "confirm-password"
IAM_USER_SUCCESS_MESSAGE_ID = 'iam-success-dialog'
INVALID_IAM_USER_RESET_PASSWORD_MSG_ID = 'iam-password-invalid-error'
IAM_USER_RESET_PASSWORD_CLOSE_IMAGE_ID = 'close-reset-password-dialog'
IAM_USER_RESET_PASSWORD_CANCEL_BUTTON_ID = 'cancel-button'
IAM_USER_SUCCESS_MESSAGE_BUTTON_ID = 'confirmation-dialogbox-btn'
IAM_USER_TABLE_ID = "iam-datatable"
IAM_USER_ACCESS_KEY_ID = "iam-accesskey-datatable"
ACCESS_KEY_TABLE_NAME_ID = "iam-accesskey-datatable-title"
IAM_USER_ACCESS_KEY_DATA_XPATH = "//td[contains(@id, 'iam-accesskey')]"
ADD_IAM_USER_ACCESS_KEY_BUTTON_ID = "iam-accesskey-add-btn"
DOWNLOAD_IAM_USER_ACCESS_KEY_BUTTON_ID = "download-csv-dialog-btn"
IAM_USER_SECRET_KEY_XPATH = "//div[@id='iam-accesskey-datatable']//td[2]"
IAM_USER_ACCESS_KEY_TABLE_HEADERS_XPATH = "//div[@id='iam-accesskey-datatable']//th"
DELETE_IAM_USER_ACCESS_KEY_BUTTON_ID = "//img[contains(@id, 'iam-accesskey-datatable-delete')]"
IAM_USER_DATA_TABLE_XPATH = "//*[@id='iam-user-data']/tr/td"
IAM_USER_TAB_S3_URL_TEXT_ID = "s3-account-manage-lbl"
IAM_USER_TAB_COPY_S3_URL_ONE_ID = "copy-url-btn-0"
IAM_USER_TAB_COPY_S3_URL_TWO_ID = "copy-url-btn-1"
IAM_USER_ACCESS_KEY_TABLE_XPATH = "//*[@id='download-csv-dialog-datatable']/tr/td"
IAM_USER_LIMIT_MSG_ID = "dialog-message-label"

# About Section
ABOUT_VIEW_ID = 'menu-actionmanagebtn'
ISSUER_DETAILS_TAB_ID = 'tab-2'
SUBJECT_DETAILS_TAB_ID = 'tab-3'
ISSUER_COMMON_NAME_VALUE_ID = 'issuer_common_name_value'
ISSUER_COUNTRY_NAME_VALUE_ID = 'issuer_country_name_value'
ISSUER_LOCALITY_NAME_VALUE_ID = 'issuer_locality_name_value'
ISSUER_ORGANIZATION_VALUE_ID = 'issuer_organization_name_value'
SUBJECT_COMMON_NAME_VALUE_ID = 'subject_common_name_value'
SUBJECT_COUNTRY_NAME_VALUE_ID = 'subject-country_name_value'
SUBJECT_LOCALITY_NAME_VALUE_ID = 'subject_locality_name_value'
SUBJECT_ORGANIZATION_VALUE_ID = 'subject_organization_name_value'
SERIAL_NO_XPATH	= "//*[contains(text(),'Serial No')]"

# Audit Log Section
AUDIT_LOG_VIEW_BUTTON_ID = "auditlog-viewbtn"
AUDIT_LOG_DOWNLOAD_BUTTON_ID = "auditlog-downlodbtn"
AUDIT_LOG_COMPONENT_DROP_DOWN_ID = "auditlog-component"
AUDIT_LOG_TIME_PERIOD_DROP_DOWN_ID = "auditlog-timeperiod"
AUDIT_LOG_DATA_ID = "auditlog-data"
CSM_AUDIT_LOG_TABLE_XPATH = "//*[@class='v-data-table__wrapper']//table//tr//td"
CURRENT_DATE_IN_DATE_PICKER_XPATH = '//button[@class="v-btn v-btn--rounded v-btn--outlined theme--light"]'
AUDIT_LOG_SEARCH_BAR_XPATH = '//input[@placeholder="Search"]'
AUDIT_LOG_SEARCH_ICON_XPATH = '//div[@class="search-image active"]'
AUDIT_LOG_FILTER_DROPDOWN_BUTTON_XPATH = '//div[@aria-haspopup="listbox"]'
AUDIT_LOG_ROLE_SELECT_XPATH = '//div[contains(@id,"list-")]//div[contains(text(), "{0}")]'
AUDIT_LOG_FETCH_ALL_LOG_XPATH = '//tbody//tr//td[@class="data-cell"]//div'
AUDIT_LOG_FETCH_SEARCHED_LOG_XPATH = '//tbody//tr//td[@class="data-cell"]//div[contains(text(),"{0}")]'
AUDIT_LOG_CURRENT_DATE_XPATH = '//*[@class="v-btn v-btn--rounded v-btn--outlined theme--light"]'
AUDIT_LOG_AVAILABLE_DATE_XPATH = '//*[@class="v-btn v-btn--active v-btn--text v-btn--rounded' \
                                 ' theme--light"]//ancestor::table//tr//td//button//div'

# Bucket
ADD_BUCKET_FORM_ID = "bucket-addbucket-formbtn"
BUCKET_NAME_ID = "bucketName"
BUCKET_CREATE_BUTTON_ID = "bucket-create-btn"
DELETE_BUCKET_XPATH = '//tr[@id="{0}"]//*[@id="bucket-delete-icon"]'
CONFIRM_CREATE_BUTTON_ID = "bucket-closedialodbox"
BUCKET_ROW_ELEMENT_XPATH = '//tr[@id="{0}"]'
BUCKET_NAME_POLICY_TOOLTIP_ID = "tooltip-msg"
BUCKET_NAME_POLICY_TOOLTIP_ICON_ID = "Bucket name*"
CANCEL_BUCKET_CREATION_BUTTON_ID = "bucket-cancel-btn"
DUPLICATE_BUCKET_MESSAGE_ID = "dialog-message-label"
CLOSE_DUPLICATE_BUCKET_MESSAGE_ID = "close-msg-dialogbox"
CANCEL_BUCKET_DELETION_ID = "confirmation-dialog-cancel-btn"
CANCEL_BUCKET_DELITION_ICON_ID = "confirmation-dialogclose"
EDIT_BUCKET_ICON_ID = "bucket-edit-icon"
UPDATE_BUCKET_POLICY_BUTTON_ID = "update-bucketpolicy"
BUCKET_POLICY_FORM_ID = "bucket-policy"
BUCKET_POLICY_FORM_HEADING_ID = "bucket-json-policy-lbl"
CANCEL_BUCKET_POLICY_FORM_ID = "cancel-bucket-policy"
ADD_POLICY_TEXT_AREA_ID = "policyJSONTextarea"
ERROR_MSG_POP_UP_ID = "dialog-message-label"
DELETE_BUCKET_POLICY = "delete-bucket-policy"
BUCKET_URL_TOOLTIP_XPATH = "//*[@id='copy-bucket-url-{0}']"
BUCKET_URL_TOOLTIP_TEXT_ID = "copy-tooltip"
BUCKET_URL_ON_BUCKET_CREATION_XPATH = "//*[@id='bucket-url-td-value']"

# Software Update Page
UPLOAD_SW_FILE_BUTTON_ID = "btnInstallHotfix"
CHOOSE_SW_UPDATE_FILE_BUTTON_ID = "file"
CANCEL_SW_UPDATE_UPLOAD_BUTTON_ID = "btnCancelInstallHotfix"
START_SW_UPDATE_BUTTON_ID = "btnStartUpgrade"
PAGE_LOADING_MSG_ID = "lblLoaderMessage"

#Buckets Tab
BUCKETS_TAB_ID = "s3bucketstab"

# Firmware Update
UPLOAD_FW_FILE_BUTTON_ID = "btnInstallFirmware"
CHOOSE_FW_UPDATE_FILE_BUTTON_ID = "file"
START_FW_UPDATE_BUTTON_ID = "btnStartUpgrade"

# System maintenance
SYSTEM_MAINTENANCE_BUTTON_ID = "goToSystemMaintenance"
START_SERVICE_BUTTON_ID = "btnStartResource"
STOP_SERVICE_BUTTON_ID = "btnStopResource"
SHUTDOWN_SERVICE_BUTTON_ID = "btnShutdownResource"

# onboarding
SYSTEM_NAME_TEXT_ID = 'txtappliancename'

