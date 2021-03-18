*** Settings ***
Documentation    This suite verifies the testcases for csm login
Library     SeleniumLibrary
Resource    ${EXECDIR}/resources/page_objects/loginPage.robot
Resource    ${EXECDIR}/resources/page_objects/dashboard.robot
Resource    ${EXECDIR}/resources/page_objects/alertPage.robot
Resource    ${EXECDIR}/resources/page_objects/s3accountPage.robot
Resource    ${EXECDIR}/resources/common/common.robot
Resource    ${EXECDIR}/resources/page_objects/userSettingsLocalPage.robot
Resource    ${EXECDIR}/resources/page_objects/auditlogPage.robot
Resource    ${EXECDIR}/resources/page_objects/softwareUpdatepage.robot
Resource    ${EXECDIR}/resources/page_objects/firmwareUpdatepage.robot
Variables   ${EXECDIR}/resources/common/common_variables.py
Resource    ${EXECDIR}/resources/page_objects/preboardingPage.robot
Variables   ${EXECDIR}/resources/common/common_variables.py

Suite Setup  run keywords   check csm admin user status  ${url}  ${browser}  ${headless}
...  ${username}  ${password}
...  AND  Close Browser
Test Setup  CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
Test Teardown  Close Browser
Suite Teardown  Close All Browsers

Force Tags  CSM_GUI  CFT_Test

*** Variables ***
${url}
${browser}  chrome
${headless}  True
${navigate_to_subpage}  False
${Sub_tab}  None
${username}
${password}
${Download_File_Path}  \root\Downloads\
${sw_version}  683

*** Test Cases ***

TEST-1226
    [Documentation]  Test that CSM user with role manager cannot update or delete s3 accounts
    ...  Reference : https://jts.seagate.com/browse/TEST-1226
    [Tags]  Priority_High  CFT_test  TEST-1226
    ${new_password}=  Generate New Password
    Navigate To Page  MANAGE_MENU_ID
    Create New CSM User  manage1226  ${new_password}  manage
    Click On Confirm Button
    Verify New User  manage1226
    Capture Page Screenshot  test_1226_manager_user.png
    Re-login  manage1226  ${new_password}  MANAGE_MENU_ID
    Validate CSM Login Success  manage1226
    Verify Absence of Edit And Delete Button on S3account
    Capture Page Screenshot  test_1226_absence_of_edit_and_delete_button_on_s3account.png
    Re-login  ${username}  ${password}  MANAGE_MENU_ID
    Delete CSM User  manage1226

TEST-1213
    [Documentation]  Test that CSM user with role manager has access to dashboard and perform actions on alerts
    ...  Reference : https://jts.seagate.com/browse/TEST-1213
    [Tags]  Priority_High  CFT_test  user_role  TEST-1213
    ${new_password}=  Generate New Password
    Navigate To Page  MANAGE_MENU_ID
    Create New CSM User  manage1213  ${new_password}  manage
    Click On Confirm Button
    Verify New User  manage1213
    Capture Page Screenshot  test_1213_manage_user.png
    Re-login  manage1213  ${new_password}  DASHBOARD_MENU_ID
    Validate CSM Login Success  manage1213
    sleep  2s  # Took time to load full dashboard
    Verify Presence of Stats And Alerts
    Capture Page Screenshot  test_1213_dashboard.png
    Click AlertPage Image
    sleep  3s  # Took time to load all alerts
    Verify Presence of Details Comments Acknowledge
    Capture Page Screenshot  test_1213_alert.png
    Click Details Button
    sleep  6s  # Took time to load alert details
    Capture Page Screenshot  test_1213_alert_details.png
    Go Back
    sleep  3s  # Took time to load all alerts
    Verify Presence of Details Comments Acknowledge
    Click Comments Button
    sleep  2s  # Took time to load comments
    Capture Page Screenshot  test_1213_comments_before_add.png
    Add CommentInCommentBox Text
    sleep  2s  # Took time to save comments
    Capture Page Screenshot  test_1213_comments_during_add.png
    Click CommentsClose Button
    Click Comments Button
    sleep  2s  # Took time to load comments
    Capture Page Screenshot  test_1213_comments_after_add.png
    Click CommentsClose Image
    Re-login  ${username}  ${password}  MANAGE_MENU_ID
    Delete CSM User  manage1213

TEST-1219
    [Documentation]  Test that monitor user can view alerts and stats.
    ...  Reference : https://jts.seagate.com/browse/TEST-1219
    [Tags]  Priority_High  CFT_test  user_role  TEST-1219
    ${new_password}=  Generate New Password
    Navigate To Page  MANAGE_MENU_ID
    Create New CSM User  monitor1219  ${new_password}  monitor
    Click On Confirm Button
    Verify New User  monitor1219
    Capture Page Screenshot  test_1219_monitor_user.png
    Re-login  monitor1219  ${new_password}  DASHBOARD_MENU_ID
    Validate CSM Login Success  monitor1219
    sleep  2s  # Took time to load full dashboard
    Capture Page Screenshot  test_1219_dashboard.png
    Verify Presence of Stats And Alerts
    Click AlertPageDashboard Image
    sleep  3s  # Took time to load all alerts
    Verify Presence of Details Comments
    Verify Absence of Acknowledge
    Capture Page Screenshot  test_1219_alert.png
    Click Details Button
    sleep  6s  # Took time to load alert details
    Capture Page Screenshot  test_1219_alert_details.png
    Go Back
    sleep  3s  # Took time to load all alerts
    Verify Presence of Details Comments
    Verify Absence of Acknowledge
    Click Comments Button
    sleep  2s  # Took time to save comments
    Capture Page Screenshot  test_1219_comments.png
    Click CommentsClose Image
    Re-login  ${username}  ${password}  MANAGE_MENU_ID
    Delete CSM User  monitor1219

TEST-4409
    [Documentation]  Test that on click of details option on Alerts detail page all the alerts related details gets displayed in the pop-up
    ...  Reference : https://jts.seagate.com/browse/TEST-4409
    [Tags]  Priority_High  CFT_test  TEST-4409
    ${new_password}=  Generate New Password
    Navigate To Page  MANAGE_MENU_ID
    Create New CSM User  monitor4409  ${new_password}  monitor
    Click On Confirm Button
    Verify New User  monitor4409
    Capture Page Screenshot  test_4409_monitor_user.png
    Re-login  monitor4409  ${new_password}  DASHBOARD_MENU_ID
    Validate CSM Login Success  monitor4409
    sleep  2s  # Took time to load full dashboard
    Capture Page Screenshot  test_4409_dashboard.png
    Verify Presence of Stats And Alerts
    Click AlertPageDashboard Image
    sleep  3s  # Took time to load all alerts
    Verify Presence of Details Comments
    Verify Absence of Acknowledge
    Capture Page Screenshot  test_4409_alert.png
    Click Details Button
    sleep  6s  # Took time to load alert details
    Verify Presence of AlertEventDetails Image
    Capture Page Screenshot  test_4409_alert_details.png
    Click AlertEventDetails Button
    sleep  3s  # Took time to load more alert details
    Verify Presence of AlertEventDetailsBody Close
    Capture Page Screenshot  test_4409_more_alert_details.png
    Capture AlertEventDetails Screenshot  test_4409_more_alert_details_full.png
    Click AlertEventDetailsClose Button
    Go Back
    sleep  3s  # Took time to load all alerts
    Re-login  ${username}  ${password}  MANAGE_MENU_ID
    Delete CSM User  monitor4409

TEST-1037
    [Documentation]  Test that S3 account user must not have access to create CSM user
    ...  Reference : https://jts.seagate.com/browse/TEST-1037
    [Tags]  Priority_High  CFT_Test  TEST-1037
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    sleep  3s
    Capture Page Screenshot  test_1037_s3_user.png
    Re-login  ${S3_account_name}  ${password}  MANAGE_MENU_ID
    sleep  3s  # Took time to load s3 account
    Verify Absence of Admin User Section
    Verify Presence of Edit And Delete
    Capture Page Screenshot  test_1037_absence_of_CSM_and_presence_of_edit_and_delete.png
    Delete S3 Account  ${S3_account_name}  ${password}  True

TEST-4932
    [Documentation]  Verify the audit log data for the logs seen/downloaded from audit log UI
    ...  Reference : https://jts.seagate.com/browse/TEST-4932
    [Tags]  Priority_High  CFT_test  TEST-4932
    Navigate To Audit Log Section
    Capture Page Screenshot  test_4932_audit_log_section.png
    View Audit Log  CSM  One day
    Verify Audit Log Generated
    Capture Page Screenshot  test_4932_CSM_audit_log_generated.png
    Download Audit Log  CSM  One day
    Verify Audit Log Downloaded  ${Download_File_Path}  csm
    Capture Page Screenshot  test_4932_CSM_audit_log_downloaded.png
    View Audit Log  S3  One day
    Sleep  5s  #S3 Audit takes a while
    Verify Audit Log Generated
    Capture Page Screenshot  test_4932_S3_audit_log_generated.png
    Download Audit Log  S3  One day
    Sleep  5s  #S3 Audit takes a while
    Verify Audit Log Downloaded  ${Download_File_Path}  s3
    Capture Page Screenshot  test_4932_S3_audit_log_downloaded.png

TEST-7820
    [Documentation]  Test that after software update is done, appropriate last update status, last update version
    ...  and last update description is displayed
    ...  Reference : https://jts.seagate.com/browse/TEST-7820
    [Tags]  Priority_High  CFT_test  TEST-7820
    Navigate To Page  MAINTENANCE_MENU_ID  SW_UPDATE_TAB_ID
    Click On Upload New Software File Button
    ${path}=  Download SW ISO File  ${sw_version}  ${Download_File_Path}
    Upload File  CHOOSE_SW_UPDATE_FILE_BTN_ID  ${path}
    # These following lines should be executed in case you have the proper machine
    #Click On Upload New Software File Button
    #Click On Start Software Update Button

TEST-6150
    [Documentation]  est that appropriate success message is getting
    ...  displayed in cases of FW update is successful.
    ...  Reference : https://jts.seagate.com/browse/TEST-6150
    [Tags]  Priority_High  CFT_test  TEST-6150
    Navigate To Page  MAINTENANCE_MENU_ID  FW_UPDATE_TAB_ID
    Click On Upload New Firmware File Button
    ${path}=  Download Firmware Binary  ${Download_File_Path}
    Upload File  CHOOSE_FW_UPDATE_FILE_BTN_ID  ${path}
    # These following lines should be executed in case you have the proper machine
    #Click On Upload New Firmware File Button
    #Click On Start Firmware Update Button
