*** Settings ***
Documentation    This suite verifies the testcases for csm login
Library     SeleniumLibrary
Resource    ${RESOURCES}/resources/page_objects/IAM_UsersPage.robot
Resource    ${RESOURCES}/resources/page_objects/loginPage.robot
Resource    ${RESOURCES}/resources/page_objects/s3accountPage.robot
Resource    ${RESOURCES}/resources/page_objects/preboardingPage.robot
Variables   ${RESOURCES}/resources/common/common_variables.py

Suite Setup  run keywords   check csm admin user status  ${url}  ${browser}  ${headless}  ${username}  ${password}
...  AND  Close Browser
Suite Teardown  Close All Browsers
Test Setup  Login To S3 Account
Test Teardown  Delete S3 Account And Close Browser
Force Tags  CSM_GUI  CSM_IAM_USER

*** Variables ***
${url}
${browser}  chrome
${headless}  True
${navigate_to_subpage}  False
${Sub_tab}  None
${username}
${password}
${S3_account_name}
${s3password}

*** Keywords ***

Login To S3 Account
    [Documentation]  This key word is for test case setup which create s3 account and login to it
    [Tags]  Priority_High  S3_test
    CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    wait for page or element to load  2s
    ${S3_account_name}  ${email}  ${s3password} =  Create S3 account
    wait for page or element to load  3s
    Re-login  ${S3_account_name}  ${s3password}  S3_ACCOUNTS_TAB_ID
    Navigate To Page   IAM_USER_TAB_ID
    wait for page or element to load  3s
    set suite variable    ${S3_account_name}
    set suite variable    ${s3password}

Delete S3 Account And Close Browser
    [Documentation]  This key word is for test case teardown which delete s3 account and close browsers
    [Tags]  Priority_High  S3_test
    Navigate To Page   S3_ACCOUNTS_TAB_ID
    ${S3_account_name}=  Fetch S3 Account Name
    Delete S3 Account  ${S3_account_name}  ${s3password}  True
    wait for page or element to load  1s
    Close Browser

*** Test Cases ***

TEST-951
    [Documentation]  Test a form appears on clicking "create user" button on IAM user page
    ...  Reference : https://jts.seagate.com/browse/TEST-951
    [Tags]  Priority_High  TEST-951  IAM_user
    Click Create IAM User Button
    Verify A Form Got Open To Create IAM Users

TEST-953
    [Documentation]  Test the form get closed on clicking "cancel" button on IAM user page
    ...  Reference : https://jts.seagate.com/browse/TEST-951
    [Tags]  Priority_High  TEST-953  IAM_user
    Click Create IAM User Button
    Click on IAM User Cancel Button
    Verify Form To Create IAM Users Got Closed

TEST-954
    [Documentation]  Test  tooltip value in IAM user creation
    ...  Reference : https://jts.seagate.com/browse/TEST-954
    [Tags]  Priority_High  TEST-954  IAM_user
    Click Create IAM User Button
    Verify IAM User Username Tooltip
    Verify IAM User Password Tooltip

TEST-955
    [Documentation]  Test error msg shown when user enters different password in "password" and "confirm password"
    ...  Reference : https://jts.seagate.com/browse/TEST-955
    [Tags]  Priority_High  TEST-955  IAM_user
    Click Create IAM User Button
    Verify Mismatch IAMuser Password Error

TEST-957
    [Documentation]  Test "create" button should clickable only after all the mandatory fields are filled
    ...  Reference : https://jts.seagate.com/browse/TEST-957
    [Tags]  Priority_High  TEST-957  IAM_user
    Click Create IAM User Button
    sleep  1s
    Verify Create IAMuser Button Must Remain disabled

TEST-952
    [Documentation]  Test IAMuser should get successfully created
    ...  Reference : https://jts.seagate.com/browse/TEST-952
    [Tags]  Priority_High  TEST-952  IAM_user
    ${username}=  Generate New User Name
    ${password}=  Generate New Password
    Click Create IAM User Button
    sleep  1s
    Create IAMuser  ${username}  ${password}
    wait for page or element to load  # Need to reload the uses
    ${status}=  Is IAMuser Present  ${username}
    Should be equal  ${status}  ${True}
    Delete IAMuser  ${username}
    wait for page or element to load  # To start the teardown process

TEST-956
    [Documentation]  Test duplicate IAMuser should not get created
    ...  Reference : https://jts.seagate.com/browse/TEST-956
    [Tags]  Priority_High  TEST-956  IAM_user
    ${username}=  Generate New User Name
    ${password}=  Generate New Password
    Click Create IAM User Button
    Create IAMuser  ${username}  ${password}
    wait for page or element to load  # Need to reload the uses
    ${status}=  Is IAMuser Present  ${username}
    Should be equal  ${status}  ${True}
    Click Create IAM User Button
    Create IAMuser  ${username}  ${password}  true
    Verify Duplicate User Error MSG
    Delete IAMuser  ${username}
    wait for page or element to load  # Need to reload the uses

TEST-958
    [Documentation]  Test that all mandatory fields are marked with asteric sign
    ...  Reference : https://jts.seagate.com/browse/TEST-958
    [Tags]  Priority_High  TEST-958  IAM_user
    Verify All Mandatory Fields In IAMusers Has astreic sign

TEST-962
    [Documentation]  Test that IAMuser should get deleted successfully
    ...  Reference : https://jts.seagate.com/browse/TEST-962
    [Tags]  Priority_High  TEST-962  IAM_user
    ${username}=  Generate New User Name
    ${password}=  Generate New Password
    Click Create IAM User Button
    Create IAMuser  ${username}  ${password}
    Delete IAMuser  ${username}
    wait for page or element to load  # Need to reload the uses
    ${status}=  Is IAMuser Present  ${username}
    Should be equal  ${status}  ${False}
    wait for page or element to load  # To start the teardown process

TEST-960
    [Documentation]  Test that no data is retained in the fields when you had canceled iam user creation process
    ...  Reference : https://jts.seagate.com/browse/TEST-960
    [Tags]  Priority_High  TEST-960  IAM_user
    Click Create IAM User Button
    Verify No Data Retains After Cancel IAMuser

TEST-961
    [Documentation]  Test username, arn and user id should be present
    ...  Reference : https://jts.seagate.com/browse/TEST-961
    [Tags]  Priority_High  TEST-961  IAM_user
    ${username}=  Generate New User Name
    ${password}=  Generate New Password
    Click Create IAM User Button
    Create IAMuser  ${username}  ${password}
    Verify ARN Username UserID  ${username}
    Delete IAMuser  ${username}
    wait for page or element to load  # Need to reload the uses

TEST-18328
    [Documentation]  Test that S3 account user is able to reset password of it's Child IAM user
    ...  Reference : https://jts.seagate.com/browse/TEST-18328
    [Tags]  Priority_High  TEST-18328  R2  IAM_user
    ${username}=  Generate New User Name
    ${password}=  Generate New Password
    Click Create IAM User Button
    Create IAMuser  ${username}  ${password}
    wait for page or element to load
    Reset Password IAMuser  ${username}
    wait for page or element to load
    Delete IAMuser  ${username}
    wait for page or element to load

TEST-18331
    [Documentation]  Test that reset password for IAM user does not accept invalid password.
    ...  Reference : https://jts.seagate.com/browse/TEST-18331
    [Tags]  Priority_High  TEST-18331  R2  IAM_user
    ${username}=  Generate New User Name
    ${password}=  Generate New Password
    Click Create IAM User Button
    Create IAMuser  ${username}  ${password}
    wait for page or element to load
    Reset Password IAMuser with invalid password  ${username}
    wait for page or element to load
    Delete IAMuser  ${username}

TEST-18333
    [Documentation]  Test that confirm rest password button remains disabled for reset IAM user password in case password and confirm password does not match.
    ...  Reference : https://jts.seagate.com/browse/TEST-18333
    [Tags]  Priority_High  TEST-18333  R2  IAM_user
    ${username}=  Generate New User Name
    ${password}=  Generate New Password
    Click Create IAM User Button
    Create IAMuser  ${username}  ${password}
    wait for page or element to load
    Verify Reset Password IAMuser button remains disabled  ${username}
    wait for page or element to load
    Delete IAMuser  ${username}


TEST-13109
    [Documentation]  Verify that two empty tables are shown on IAM users page
    ...  Reference : https://jts.seagate.com/browse/TEST-13109
    [Tags]  Priority_High  TEST-13109  IAM_user
    Verify Presence of Two Tables

TEST-1021
    [Documentation]  Test that IAM user is not able to log-in and access the CSM GUI.
    ...  Reference : https://jts.seagate.com/browse/TEST-1021
    [Tags]  Priority_High  TEST-1021  IAM_user
    ${iamusername}=  Generate New User Name
    ${iampassword}=  Generate New Password
    Click Create IAM User Button
    Create IAMuser  ${iamusername}  ${iampassword}
    wait for page or element to load  # Need to reload the uses
    ${status}=  Is IAMuser Present  ${iamusername}
    Should be equal  ${status}  ${True}
    Try to Login As IAMUser  ${iamusername}  ${iampassword}
    Validate CSM Login Failure
    Reload Page
    wait for page or element to load
    Re-login  ${S3_account_name}  ${s3password}  IAM_USER_TAB_ID  False
    Delete IAMuser  ${iamusername}
    wait for page or element to load  # Need to reload the uses

TEST-13110
    [Documentation]  Verify that if IAM user exist, first IAM user is selected by
    ...  default and its access keys are shown in keys table
    ...  Reference : https://jts.seagate.com/browse/TEST-13110
    [Tags]  Priority_High  TEST-13110  IAM_user
    ${iamusername}=  Generate New User Name
    ${iampassword}=  Generate New Password
    Click Create IAM User Button
    Create IAMuser  ${iamusername}  ${iampassword}
    wait for page or element to load  # Need to reload the uses
    Verify the IAMuser of the Access Key Table  ${iamusername}
    Delete IAMuser  ${iamusername}
    wait for page or element to load  # Need to reload the uses

TEST-13111
    [Documentation]  Verify that keys table gets updated according to the selected IAM user
    ...  Reference : https://jts.seagate.com/browse/TEST-13111
    [Tags]  Priority_High  TEST-13111  IAM_user
    ${iamusername1}=  Generate New User Name
    ${iamusername2}=  Generate New User Name
    ${iampassword}=  Generate New Password
    Click Create IAM User Button
    Create IAMuser  ${iamusername1}  ${iampassword}
    Verify the IAMuser of the Access Key Table  ${iamusername1}
    Click Create IAM User Button
    Create IAMuser  ${iamusername2}  ${iampassword}
    Click On IAMuser  ${iamusername2}
    Verify the IAMuser of the Access Key Table  ${iamusername2}
    Delete IAMuser  ${iamusername1}
    Delete IAMuser  ${iamusername2}
    wait for page or element to load  # Need to reload the uses

TEST-13112
    [Documentation]  Test that s3 account user can generate keys for IAM users
    ...  Reference : https://jts.seagate.com/browse/TEST-13112
    [Tags]  Priority_High  TEST-13112  IAM_user
    ${iamusername}=  Generate New User Name
    ${iampassword}=  Generate New Password
    Click Create IAM User Button
    Create IAMuser  ${iamusername}  ${iampassword}
    Click On IAMuser  ${iamusername}
    Generate IAM User Add Access Key
    ${count}=  Get IAMUser Access Key Count
    Should be equal  '${count}'  '2'
    Delete IAMuser  ${iamusername}
    wait for page or element to load  # Need to reload the uses

TEST-13113
    [Documentation]  Test that s3 account user can delete keys for IAM users
    ...  Reference : https://jts.seagate.com/browse/TEST-13113
    [Tags]  Priority_High  TEST-13113  IAM_user
    ${iamusername}=  Generate New User Name
    ${iampassword}=  Generate New Password
    Click Create IAM User Button
    Create IAMuser  ${iamusername}  ${iampassword}
    Click On IAMuser  ${iamusername}
    Generate IAM User Add Access Key
    Delete IAM User Add Access Key
    wait for page or element to load
    ${count}=  Get IAMUser Access Key Count
    Should be equal  '${count}'  '1'
    Delete IAMuser  ${iamusername}
    wait for page or element to load  # Need to reload the uses

TEST-13114
    [Documentation]  Verify that table for IAM user keys contains data in appropriate format
    ...  Reference : https://jts.seagate.com/browse/TEST-13114
    [Tags]  Priority_High  TEST-13114  IAM_user
    ${iamusername}=  Generate New User Name
    ${iampassword}=  Generate New Password
    Click Create IAM User Button
    Create IAMuser  ${iamusername}  ${iampassword}
    Verify IAMuser Access Key table content
    Delete IAMuser  ${iamusername}
    wait for page or element to load  # Need to reload the uses

TEST-13115
    [Documentation]  Verify that a table for IAM user's access keys is
    ...  shown below IAM users table with required columns
    ...  Reference : https://jts.seagate.com/browse/TEST-13115
    [Tags]  Priority_High  TEST-13115  IAM_user
    ${iamusername}=  Generate New User Name
    ${iampassword}=  Generate New Password
    Click Create IAM User Button
    Create IAMuser  ${iamusername}  ${iampassword}
    Click On IAMuser  ${iamusername}
    Verify Access Key Table Headers
    Delete IAMuser  ${iamusername}
    wait for page or element to load  # Need to reload the uses

TEST-13116
    [Documentation]  Verify that table for IAM user keys contains data in appropriate format
    ...  Reference : https://jts.seagate.com/browse/TEST-13116
    [Tags]  Priority_High  TEST-13116  IAM_user
    ${iamusername}=  Generate New User Name
    ${iampassword}=  Generate New Password
    Click Create IAM User Button
    Create IAMuser  ${iamusername}  ${iampassword}
    Click On IAMuser  ${iamusername}
    Generate IAM User Add Access Key
    wait for page or element to load
    Verify Generate Access Key Button Must Remain Disable
    Delete IAMuser  ${iamusername}
    wait for page or element to load  # Need to reload the uses
