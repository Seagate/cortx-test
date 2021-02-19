*** Settings ***
Documentation    This suite verifies the testcases for csm login
Library     SeleniumLibrary
Resource    ../../../resources/page_objects/loginPage.robot
Resource    ../../../resources/page_objects/s3accountPage.robot
Resource    ../../../resources/common/common.robot
Resource    ../../../resources/page_objects/userSettingsLocalPage.robot
Resource    ../../../resources/page_objects/auditlogPage.robot
Variables   ../../../resources/common/common_variables.py


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

*** Test Cases ***

TEST-1226
    [Documentation]  Test that CSM user with role manager cannot update or delete s3 accounts
    ...  Reference : https://jts.seagate.com/browse/TEST-1226
    [Tags]  Priority_High  CFT_test
    ${new_password}=  Generate New Password
    Navigate To Page  MANAGE_MENU_ID
    Create New CSM User  manage  ${new_password}  manage
    Click On Confirm Button
    Verify New User  manage
    Re-login  manage  ${new_password}  MANAGE_MENU_ID
    Validate CSM Login Success  manage
    Verify Absence of Edit And Delete Button on S3account
    Re-login  ${username}  ${password}  MANAGE_MENU_ID
    Delete CSM User  manage

TEST-1219
    [Documentation]  Test that monitor user can view alerts and stats.
    ...  Reference : https://jts.seagate.com/browse/TEST-1219
    [Tags]  Priority_High  CFT_test
    ${new_password}=  Generate New Password
    Navigate To Page  MANAGE_MENU_ID
    Create New CSM User  monitor  ${new_password}  monitor
    Click On Confirm Button
    Verify New User  monitor
    Re-login  monitor  ${new_password}  DASHBOARD_MENU_ID
    Validate CSM Login Success  monitor
    Verify Presence of Stats And Alerts
    Re-login  ${username}  ${password}  MANAGE_MENU_ID
    Delete CSM User  monitor

TEST-1037
    [Documentation]  Test that S3 account user must not have access to create CSM user
    ...  Reference : https://jts.seagate.com/browse/TEST-1037
    [Tags]  Priority_High  CFT_Test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    sleep  3s
    Re-login  ${S3_account_name}  ${password}  MANAGE_MENU_ID
    Verify Absence of Admin User Section
    sleep  2s
    Delete S3 Account  ${S3_account_name}  ${password}  True

TEST-4932
    [Documentation]  Verify the audit log data for the logs seen/downloaded from audit log UI
    ...  Reference : https://jts.seagate.com/browse/TEST-4932
    [Tags]  Priority_High  CFT_test
    Navigate To Audit Log Section
    View Audit Log  CSM  One day
    Verify Audit Log Generated
    Download Audit Log  CSM  One day
    Verify Audit Log Downloaded  ${Download_File_Path}  csm
    View Audit Log  S3  One day
    Sleep  5s  #S3 Audit takes a while
    Verify Audit Log Generated
    Download Audit Log  S3  One day
    Sleep  5s  #S3 Audit takes a while
    Verify Audit Log Downloaded  ${Download_File_Path}  s3
