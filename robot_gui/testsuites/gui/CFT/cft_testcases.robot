*** Settings ***
Documentation    This suite verifies the testcases for csm login
Library     SeleniumLibrary

Resource    ${RESOURCES}/resources/page_objects/loginPage.robot
Resource    ${RESOURCES}/resources/page_objects/dashboardPage.robot
Resource    ${RESOURCES}/resources/page_objects/alertPage.robot
Resource    ${RESOURCES}/resources/page_objects/s3accountPage.robot
Resource    ${RESOURCES}/resources/page_objects/userSettingsLocalPage.robot
Resource    ${RESOURCES}/resources/page_objects/auditlogPage.robot
Resource    ${RESOURCES}/resources/page_objects/softwareUpdatepage.robot
Resource    ${RESOURCES}/resources/page_objects/firmwareUpdatepage.robot
Resource    ${RESOURCES}/resources/page_objects/preboardingPage.robot
Resource    ${RESOURCES}/resources/common/common.robot
Variables   ${RESOURCES}/resources/common/common_variables.py

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
${Download_File_Path}  /root/Downloads
${sw_version}  891

*** Keywords ***

Create and login with CSM user
    [Documentation]  This keyword is used to Create and login with CSM user
    [Arguments]  ${user_type}  ${test_id}
    ${new_password}=  Generate New Password
    Navigate To Page  MANAGE_MENU_ID
    Create New CSM User  ${user_type}${test_id}  ${new_password}  ${user_type}
    Click On Confirm Button
    Verify New User  ${user_type}${test_id}
    Capture Page Screenshot  ${test_id}_${user_type}_user.png
    Re-login  ${user_type}${test_id}  ${new_password}  DASHBOARD_MENU_ID
    Validate CSM Login Success  ${user_type}${test_id}
    wait for page or element to load  2s  # Took time to load full dashboard
    Verify Presence of Stats And Alerts
    Capture Page Screenshot  ${test_id}_dashboard.png

Delete user
    [Documentation]  This keyword is used to Delete CSM user
    [Arguments]  ${user_type}  ${test_id}
    Delete CSM User  ${user_type}${test_id}

*** Test Cases ***

TEST-1213
    [Documentation]  Test that CSM user with role manager has access to dashboard and perform actions on alerts
    ...  Reference : https://jts.seagate.com/browse/TEST-1213
    [Tags]  Priority_High  CFT_test  user_role  TEST-1213
    ${user_type}    Set Variable    manage
    ${test_id}    Set Variable    TEST-1213
    Create and login with CSM user  ${user_type}  ${test_id}
    Click AlertPage Image
    wait for page or element to load  3s  # Took time to load all alerts
    Verify Presence of Details Comments Acknowledge
    Capture Page Screenshot  ${test_id}_alert.png
    Click Details Button
    wait for page or element to load  6s  # Took time to load alert details
    Capture Page Screenshot  ${test_id}_alert_details.png
    Go Back
    wait for page or element to load  5s  # Took time to load all alerts
    Verify Presence of Details Comments Acknowledge
    Click Comments Button
    wait for page or element to load  3s  # Took time to load comments
    Capture Page Screenshot  ${test_id}_comments_before_add.png
    Add CommentInCommentBox Text
    wait for page or element to load  10s  # Took time to save comments
    Capture Page Screenshot  ${test_id}_comments_during_add.png
    Click CommentsClose Button
    Click Comments Button
    wait for page or element to load  3s  # Took time to load comments
    Capture Page Screenshot  ${test_id}_comments_after_add.png
    Click CommentsClose Image
    Re-login  ${username}  ${password}  MANAGE_MENU_ID
    Delete user  ${user_type}  ${test_id}

TEST-1219
    [Documentation]  Test that monitor user can view alerts and stats.
    ...  Reference : https://jts.seagate.com/browse/TEST-1219
    [Tags]  Priority_High  CFT_test  user_role  TEST-1219
    ${user_type}    Set Variable    monitor
    ${test_id}    Set Variable    TEST-1219
    Create and login with CSM user  ${user_type}  ${test_id}
    Click AlertPageDashboard Image
    wait for page or element to load  3s  # Took time to load all alerts
    Verify Presence of Details Comments
    Verify Absence of Acknowledge
    Capture Page Screenshot  ${test_id}_alert.png
    Click Details Button
    wait for page or element to load  6s  # Took time to load alert details
    Capture Page Screenshot  ${test_id}_alert_details.png
    Go Back
    wait for page or element to load  3s  # Took time to load all alerts
    Verify Presence of Details Comments
    Verify Absence of Acknowledge
    Click Comments Button
    wait for page or element to load  2s  # Took time to save comments
    Capture Page Screenshot  ${test_id}_comments.png
    Click CommentsClose Image
    Re-login  ${username}  ${password}  MANAGE_MENU_ID
    Delete user  ${user_type}  ${test_id}

TEST-4409
    [Documentation]  Test that on click of details option on Alerts detail page all the alerts related details gets displayed in the pop-up
    ...  Reference : https://jts.seagate.com/browse/TEST-4409
    [Tags]  Priority_High  CFT_test  TEST-4409
    ${user_type}    Set Variable    monitor
    ${test_id}    Set Variable    TEST-4409
    Create and login with CSM user  ${user_type}  ${test_id}
    Click AlertPageDashboard Image
    wait for page or element to load  3s  # Took time to load all alerts
    Verify Presence of Details Comments
    Verify Absence of Acknowledge
    Capture Page Screenshot  ${test_id}_alert.png
    Click Details Button
    wait for page or element to load  6s  # Took time to load alert details
    Verify Presence of AlertEventDetails Image
    Capture Page Screenshot  ${test_id}_alert_details.png
    Click AlertEventDetails Button
    wait for page or element to load  3s  # Took time to load more alert details
    Verify Presence of AlertEventDetailsBody Close
    Capture Page Screenshot  ${test_id}_more_alert_details.png
    Capture AlertEventDetails Screenshot  ${test_id}_more_alert_details_full.png
    Click AlertEventDetailsClose Button
    Go Back
    wait for page or element to load  3s  # Took time to load all alerts
    Re-login  ${username}  ${password}  MANAGE_MENU_ID
    Delete user  ${user_type}  ${test_id}

TEST-1037
    [Documentation]  Test that S3 account user must not have access to create CSM user
    ...  Reference : https://jts.seagate.com/browse/TEST-1037
    [Tags]  Priority_High  CFT_Test  TEST-1037
    ${test_id}    Set Variable    TEST-1037
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    wait for page or element to load
    Capture Page Screenshot  ${test_id}_s3_user.png
    Re-login  ${S3_account_name}  ${password}  S3_ACCOUNTS_TAB_ID
    wait for page or element to load  # Took time to load s3 account
    Verify Absence of Admin User Section
    Capture Page Screenshot  ${test_id}_absence_of_CSM_and_presence_of_edit_and_delete.png
    Delete S3 Account  ${S3_account_name}  ${password}  True

TEST-4932
    [Documentation]  Verify the audit log data for the logs seen/downloaded from audit log UI
    ...  Reference : https://jts.seagate.com/browse/TEST-4932
    [Tags]  Priority_High  CFT_test  TEST-4932
    ${test_id}    Set Variable    TEST-4932
    Navigate To Audit Log Section
    Capture Page Screenshot  ${test_id}_audit_log_section.png
    View Audit Log  CSM
    Verify Audit Log Generated
    Capture Page Screenshot  ${test_id}_CSM_audit_log_generated.png
    Download Audit Log  CSM
    Verify Audit Log Downloaded  ${Download_File_Path}  csm
    Capture Page Screenshot  ${test_id}_CSM_audit_log_downloaded.png
    View Audit Log  S3
    wait for page or element to load
    Verify Audit Log Generated
    Capture Page Screenshot  ${test_id}_S3_audit_log_generated.png
    Download Audit Log  S3
    wait for page or element to load
    Verify Audit Log Downloaded  ${Download_File_Path}  s3
    Capture Page Screenshot  ${test_id}_S3_audit_log_downloaded.png

TEST-7820
    [Documentation]  Test that after software update is done, appropriate last update status, last update version
    ...  and last update description is displayed
    ...  Reference : https://jts.seagate.com/browse/TEST-7820
    [Tags]  SW_Update  TEST-7820
    Navigate To Page  MAINTENANCE_MENU_ID  SW_UPDATE_TAB_ID
    # The below code shall now work on VM
    #Click On Upload New Software File Button
    #${path}=  Download SW ISO File  ${sw_version}  ${Download_File_Path}
    #Upload File  CHOOSE_SW_UPDATE_FILE_BUTTON_ID  ${path}
    # These following lines should be executed in case you have the proper machine
    #Click On Upload New Software File Button
    #Click On Start Software Update Button

TEST-6150
    [Documentation]  est that appropriate success message is getting
    ...  displayed in cases of FW update is successful.
    ...  Reference : https://jts.seagate.com/browse/TEST-6150
    [Tags]  FW_Update  TEST-6150
    Navigate To Page  MAINTENANCE_MENU_ID  FW_UPDATE_TAB_ID
    # The below code shall now work on VM
    #Click On Upload New Firmware File Button
    #${path}=  Download Firmware Binary  ${Download_File_Path}
    #Upload File  CHOOSE_FW_UPDATE_FILE_BUTTON_ID  ${path}
    # These following lines should be executed in case you have the proper machine
    #Click On Upload New Firmware File Button
    #Click On Start Firmware Update Button
