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
""" This File contains web element locators for all pages. """


class CommonLocators:
    """Common Locators for All Pages"""
    dashboard_icon = "//*[@id='app']//label[text()='Dashboard']"
    provisioning_menu = "//label[text()= 'Provisioning']"


class AlertLocators:
    """Locators for Alerts feature"""
    notification_count = "alert-count"
    notification = "alert-img"
    see_all_alerts = "//*[contains(@class, 'green--text pointer')]"


class LargeAlertModule:
    """Locators for Large Alerts feature"""
    back_to_overview = "//*[contains(@class, 'pl-2 backoverviewtxt')]"


class Login:
    """Locators for Login feature"""
    user_name = "username"
    pass_word = "password"
    login_button = "//*[@id='app']//button[contains(text(),'Login')]"
    failed_login_message = "//*[text() = 'Login failed !']"
    log_out_icon = "//*[@src = '/img/logout.07bb1732.svg']"
    logged_in_user_element = "//*[@class='eos-username-label']"


class Dashboard:
    """Locators for Dashboard feature"""
    alert_count = "alert-count"
    alert_notification = "//*[@src = '/img/alerts-white.dff24886.svg']"


class s3config:
    """Locators for s3 config feature"""
    create_button = "//*[@class='header-margin navbar-margin']//button[contains(text(),'Create')]"
    s3_account_name = 'accountName'
    s3_account_password = 'accountPassword'
    s3_account_confirm_password = 'confirmPassword'
    s3_account_email_name = 'accountEmail'
    s3_create_account_btn = "//*[@id='app']//button[contains(text(), 'Create account')]"
    s3_account_cancel_btn = "//*[@id='app']//button[contains(text(), 'Cancel')]"
    create_s3_account_loader = "//*[@id='app']/div/div/div[1]/div[2]/div/div[3]/div[1]/div[2]/div/div/div[1]/label"
    manage_s3_menu = "//*[@class='eos-menu-card-layout']//label[contains(text(), 'S3')]//following-sibling::button"
    s3_account_created_text = "//*[@id='app']//span[contains(text(),'Account created: access key and secret')]"
    ok_button_on_account_creation_pop_up = "//*[@id='app']//button[contains(text(),'Ok')]"
    account_table = "//*[@id='app']/div[1]/div/div/table"
    existing_accounts = "//*[@id='app']//table"
    invalid_account_name_message = "//*[@id='app']//label[contains(text(), 'Invalid account name')]"
    invalid_password_message = "//*[@id='app']//label[contains(text(), 'Invalid password')]"
    invalid_confirm_password_message = "//*[@id='app']//span[contains(text() , 'Passwords do not match')]"
    invalid_email_account_message = "//*[@id='app']//label[contains(text(), 'Invalid email id')]"
    first_time_user_msg = "//*[text()='No data available']"
    s3_accounts_table = "//*[@class='v-data-table__wrapper']/table/tbody"
    edit_s3_password = "accountPasswordEdit"
    edit_s3_confirm_password = "confirmPasswordEdit"
    update_btn_s3_details = "btnEditPassword"
    cancel_edit_s3_account_button = "btncancelEditpass"
    delete_s3_account_button = "//table//tr//img[contains(@src,'/img/delete-green.1de8a7f3.svg')]"
    edit_s3_account_button = "//table//tr//img[contains(@src,'/img/edit-green.f0f29592.svg')]"
    success_message_edit_s3_account = ""
    success_message_deleted_s3_account = ""
    confirm_delete_s3_account_button = "//*[@class= 'v-card v-sheet theme--light']//button[contains(text(),'Yes')]"
    cancel_delete_s3_accpint = "//*[@class= 'v-card v-sheet theme--light']//button[contains(text(),'No')]"
    duplicate_account_error_message = "//*[@class='eos-msg-dialog-container']//label[text()='Bad Request']"


class iamconfig:
    """Locators for IAM config feature"""
    iam_tab = "//*[@class='eos-tabs-container']/div[2]"
    iam_page_content_label = "//*[@id='s3-configuration-title-container']/span/div/label"
    create_iam_user_btn = "//button[@class='mt-2 mb-2 eos-btn-primary']"
    iam_username_text_label = "//label[@for='userName']/span"
    iam_password_text_label = "//label[@for='userPassword']/span"
    iam_confirm_password_text_label = "//label[@for='confirmPassword']"
    iam_username_field = "//*[@id='userName']"
    iam_password_field = "//*[@id='userPassword']"
    iam_confirm_password_field = "//*[@id='confirmPassword']"
    iam_user_create_btn = "//button[@class='eos-btn-primary']"
    iam_user_cancel_btn = "//button[@class='eos-btn-tertiary']"
    iam_account_created_text = "//span[contains(text(),'User created')]"
    iam_account_table = "//*[@id='app']/div[1]/div/div/table"
    iam_account_created_ok_btn = "//button[@class='ma-5 eos-btn-primary']"
    existing_iam_user_account_field = "//table[@class='mx-7 mb-7']"


class UserSettings:
    """Locators for User settings page"""
    manage_user_menu = "//*[@class='eos-menu-card-layout']//label[contains(text(), 'User')]//following-sibling::button"
    new_user_add_btn = "//button[contains(text(),'Add new user')]"
    new_user_ip = "//input[@name='txtCreateUsername']"
    new_password_ip = "//input[@name='txtCreatePassword']"
    new_confirm_password_ip = "//input[@name='txtCreateConfirmPassword']"
    new_manage_btn = "//*[@id='lblLocalManage']"
    new_monitor_btn = "//*[@id='lblLocalMonitor']"
    new_cancel_btn = "//button[contains(text(),'Cancel')]"
    new_create_btn = "//button[contains(text(),'Create')]"
    invalid_username_msg = "//*[@id='app']//label[contains(text(), 'Invalid username')]"
    invalid_password_msg = "//*[@id='app']//label[contains(text(), 'Invalid password')]"
    invalid_confirm_password_msg = "//*[@id='app']//label[contains(text(), 'Passwords do not match')]"
    user_table = "//*[@id='app']//table"
    expand_button = "//table//tr//img[contains(@src,'/img/caret-right.bd531b05.svg')]"
    drop_down_btn = "//*[@class='v-input__icon v-input__icon--append']"
    select_all = "//*[contains(text(),'All')]"
    edit_user_btn = "//table//tr//img[contains(@src,'/img/edit-green.f0f29592.svg')]"
    edit_old_password_ip = "//input[@id='txtLocalOldPass']"
    edit_password_ip = "//input[@id='txtLocalPass']"
    edit_confirm_password_ip = "//input[@id='txtLocalConfirmNewPass']"
    edit_manage_btn = "//*[@id='lblLocalManageInterface']"
    edit_monitor_btn = "//*[@id='lblLocalMonitorInterface']"

    edit_apply_btn = "//button[contains(text(),'Apply')]"
    edit_cancel_btn = "//*[@id='lblLocalCancelInterface']"
    delete_user_btn = "//table//tr//img[contains(@src,'/img/delete-green.1de8a7f3.svg')]"
    duplicate_user_error_msg = "//*[@class='eos-msg-dialog-container']//label[text()='Such user already exists']"
    select_row = "//*[@id='list-364']"
    old_password_input = "//input[@name='txtEditOldPassword']"
    next_page = "//*[@aria-label='Next page']"
    prev_page = "//*[@aria-label='Previous page']"


class Preboarding:
    start_btn = "welcome-startbtn"
    terms_btn = "show-license-agreement-dialogbtn"
    accept_btn = "license-acceptagreement"
    username_ip = "adminUsername"
    password_ip = "adminPassword"
    confirmpwd_ip = "confirmAdminPassword"
    email_ip = "adminEmail"
    create_btn = "admin-createadminuser"
    err_msg = "admin-invalidmsg"
    userlogin_ip = "username"


class Onboarding:
    username_ip = "username"
    password_ip = "password"
    login_btn = "login-userbtn"
    continue_btn = "//*[contains(text(),'Continue')]"
    ssl_choose_file = '//*[@id="file"]'
    sys_ip = "txtappliancename"
    dns_server_ip = "0txtDnsServer"
    dns_search_ip = "0txtSearchDomain"
    ntp_server_ip = "txtDTHostname"
    ntp_timezone_ip = "closedropdown"
    skip_step_chk = "//label[contains(text(), 'Skip')]/span"
    confirm_btn = "confirmation-dialogbox-btn"
    finish_btn = "finish-onboarding-setting"
