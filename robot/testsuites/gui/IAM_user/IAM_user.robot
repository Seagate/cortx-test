*** Settings ***
Documentation    This suite verifies the testcases for csm login
Library     SeleniumLibrary
Resource    ../../../resources/page_objects/loginPage.robot
Resource    ../../../resources/page_objects/s3accountPage.robot
Resource    ../../../resources/page_objects/IAM_UsersPage.robot
Variables   ../../../resources/common/common_variables.py


Suite Teardown  Close All Browsers
Force Tags  CSM_GUI  CSM_IAM_USER
Test Setup  Login To S3 Account
Test Teardown  Delete S3 Account And Close Browser

*** Variables ***
${url}
${browser}  chrome
${headless}  True
${navigate_to_subpage}  False
${Sub_tab}  None
${username}
${password}
${S3_account_name}

*** Keywords ***

Login To S3 Account
    [Documentation]  This key word is for test case setup which create s3 account and login to it
    [Tags]  Priority_High  S3_test
    CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    sleep  3s
    Re-login  ${S3_account_name}  ${password}  MANAGE_MENU_ID
    Navigate To Page  MANAGE_MENU_ID  IAM_USER_TAB_ID


Delete S3 Account And Close Browser
    [Documentation]  This key word is for test case teardown which delete s3 account and close browsers
    [Tags]  Priority_High  S3_test
    Navigate To Page  MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    ${S3_account_name}=  Fetch S3 Account Name
    Delete S3 Account  ${S3_account_name}  ${password}  True
    Sleep  1s
    Close Browser


*** Test Cases ***

TEST-951
    [Documentation]  Test a form appears on clicking "create user" button on IAM user page
    ...  Reference : https://jts.seagate.com/browse/TEST-951
    [Tags]  Priority_High
    Click Create IAM User Button
    Verify A Form Got Open To Create IAM Users

TEST-953
    [Documentation]  Test the form get closed on clicking "cancel" button on IAM user page
    ...  Reference : https://jts.seagate.com/browse/TEST-951
    [Tags]  Priority_High
    Click Create IAM User Button
    Click on IAM User Cancel Button
    Verify Form To Create IAM Users Got Closed

TEST-954
    [Documentation]  Test  tooltip value in IAM user creation
    ...  Reference : https://jts.seagate.com/browse/TEST-954
    [Tags]  Priority_High
    Click Create IAM User Button
    Verify IAM User Username Tooltip
    Verify IAM User Passwd Tooltip

TEST-955
    [Documentation]  Test error msg shown when user enters different password in "password" and "confirm password"
    ...  Reference : https://jts.seagate.com/browse/TEST-955
    [Tags]  Priority_High
    Click Create IAM User Button
    Verify Missmatch IAMuser Password Error

TEST-957
    [Documentation]  Test "create" button should clickable only after all the mandatory fields are filled
    ...  Reference : https://jts.seagate.com/browse/TEST-957
    [Tags]  Priority_High
    Click Create IAM User Button
    Verify Create IAMuser Button Must Remain disbaled

TEST-952
    [Documentation]  Test IAMuser should get successfully created
    ...  Reference : https://jts.seagate.com/browse/TEST-952
    [Tags]  Priority_High
    ${username}=  Generate New User Name
    ${password}=  Generate New Password
    Click Create IAM User Button
    Create IAMuser  ${username}  ${password}
    Sleep  5s  # Need to reload the uses
    ${status}=  Is IAMuser Present  ${username}
    Should be equal  ${status}  ${True}
    Delete IAMuser  ${username}
    Sleep  5s  # To start the teardown process

TEST-956
    [Documentation]  Test duplicate IAMuser should not get created
    ...  Reference : https://jts.seagate.com/browse/TEST-956
    [Tags]  Priority_High
    ${username}=  Generate New User Name
    ${password}=  Generate New Password
    Click Create IAM User Button
    Create IAMuser  ${username}  ${password}
    Sleep  5s  # Need to reload the uses
    ${status}=  Is IAMuser Present  ${username}
    Should be equal  ${status}  ${True}
    Click Create IAM User Button
    Create IAMuser  ${username}  ${password}  true
    Verify Duplicate User Error MSG
    Delete IAMuser  ${username}
    Sleep  5s  # Need to reload the uses

TEST-958
    [Documentation]  Test that all mandatory fields are marked with asteric sign
    ...  Reference : https://jts.seagate.com/browse/TEST-958
    [Tags]  Priority_High
    Verify All Mandatory Fields In IAMusers Has astreic sign

TEST-962
    [Documentation]  Test that IAMuser should get deleted successfully
    ...  Reference : https://jts.seagate.com/browse/TEST-962
    [Tags]  Priority_High
    ${username}=  Generate New User Name
    ${password}=  Generate New Password
    Click Create IAM User Button
    Create IAMuser  ${username}  ${password}
    Delete IAMuser  ${username}
    Sleep  5s  # Need to reload the uses
    ${status}=  Is IAMuser Present  ${username}
    Should be equal  ${status}  ${False}
    Sleep  5s  # To start the teardown process

TEST-960
    [Documentation]  Test that no data is retained in the fields when you had canceled iam user creation process
    ...  Reference : https://jts.seagate.com/browse/TEST-960
    [Tags]  Priority_High
    Click Create IAM User Button
    Verify Blank IAMuser Form

TEST-961
    [Documentation]  Test username, arn and user id should be present
    ...  Reference : https://jts.seagate.com/browse/TEST-961
    [Tags]  Priority_High
    ${username}=  Generate New User Name
    ${password}=  Generate New Password
    Click Create IAM User Button
    Create IAMuser  ${username}  ${password}
    Verify ARN Username UserID  ${username}
    Delete IAMuser  ${username}
    Sleep  5s  # Need to reload the uses
