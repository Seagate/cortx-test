*** Settings ***
Documentation    This suite verifies the testcases for csm login
Library    SeleniumLibrary
Resource   ${RESOURCES}/resources/page_objects/bucket_page.robot
Resource   ${RESOURCES}/resources/page_objects/healthPage.robot
Resource   ${RESOURCES}/resources/page_objects/IAM_UsersPage.robot
Resource   ${RESOURCES}/resources/page_objects/loginPage.robot
Resource   ${RESOURCES}/resources/page_objects/preboardingPage.robot
Resource   ${RESOURCES}/resources/page_objects/s3accountPage.robot
Resource   ${RESOURCES}/resources/page_objects/settingsPage.robot
Resource   ${RESOURCES}/resources/common/common.robot
Variables  ${RESOURCES}/resources/common/common_variables.py
Variables  ${RESOURCES}/resources/common/element_locators.py

Suite Setup  run keywords   check csm admin user status  ${url}  ${browser}  ${headless}  ${username}  ${password}
...  AND  Close Browser
Suite Teardown  Close All Browsers
Force Tags  CSM_GUI  CSM_login
Test Setup  CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
Test Teardown  Close Browser

*** Variables ***
${url}
${browser}  chrome
${headless}  True
${navigate_to_subpage}  False
${Sub_tab}  None
${username}
${password}
${invalid_S3_account_name}  xyz$#%1
${invalid_S3_email_id}  xyz@test
${invalid_S3_account_password}  TestPass

*** Test Cases ***

Check S3 Account Exists
    [Documentation]  This test is to verify that S3 account exists
    [Tags]  Priority_High  S3_test
    Validate CSM Login Success  ${username}
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    Check S3 Account Exists     S3_ACCOUNTS_TABLE_XPATH  ${S3_ACCOUNT}

Test action on table
    [Documentation]  This test case is to verify that user can perform the actions on the table elements.
    [Tags]  Priority_High  S3_test
    Validate CSM Login Success  ${username}
    Navigate To Page    MANAGE_MENU_ID
    wait for page or element to load
    Action on the table     ${CSM_USER}  CSM_USER_EDIT_XPATH

TEST-5268
    [Documentation]  Test S3 account user should only be able to see S3 account details of the accounts which are associated with its account
    [Tags]  Priority_High  Smoke_test  user_role  TEST-5268
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    wait for page or element to load
    Re-login   ${S3_account_name}  ${password}  S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    Check Associated S3 Account Exists  ${S3_account_name}  ${email} 
    Delete S3 Account  ${S3_account_name}  ${password}  True

TEST-1033
    [Documentation]  Test that alerts should not get visible to the s3 user
    [Tags]  Priority_High  Smoke_test  user_role  TEST-1033
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    wait for page or element to load
    Re-login   ${S3_account_name}  ${password}  S3_ACCOUNTS_TAB_ID
    Check Dashboard Option Not Exists
    Delete S3 Account  ${S3_account_name}  ${password}  True  

TEST-1042
    [Documentation]  Test that setting option not available for s3 user
    [Tags]  Priority_High  Smoke_test  user_role  TEST-1042
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    wait for page or element to load
    Re-login   ${S3_account_name}  ${password}  S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    Verify that S3 user can not access setting menu
    Delete S3 Account  ${S3_account_name}  ${password}  True

TEST-6454
    [Documentation]  Test Alert icon should not be visible to s3 account user Verify Alert icon should not be visible to s3 account user
    [Tags]  Priority_High  Smoke_test  user_role  TEST-6454
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    wait for page or element to load
    Re-login   ${S3_account_name}  ${password}  S3_ACCOUNTS_TAB_ID
    Check Alert Icon Not Exists
    Delete S3 Account  ${S3_account_name}  ${password}  True       

TEST-1035
    [Documentation]  Test that maintenance option not available for s3 user
    [Tags]  Priority_High  Smoke_test  user_role  TEST-1035
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    wait for page or element to load
    Re-login   ${S3_account_name}  ${password}  S3_ACCOUNTS_TAB_ID
    Check Maintenance Option Not Exists
    Delete S3 Account  ${S3_account_name}  ${password}  True   

TEST-1872
    [Documentation]  Test that Test s3user not able to do system shutdown
    [Tags]  Priority_High  Smoke_test  user_role  TEST-1872
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    wait for page or element to load
    Re-login   ${S3_account_name}  ${password}  S3_ACCOUNTS_TAB_ID
    Check Maintenance Option Not Exists
    Delete S3 Account  ${S3_account_name}  ${password}  True   

TEST-1873
    [Documentation]  Test s3user not able to do any service restart
    [Tags]  Priority_High  Smoke_test  user_role  TEST-1873
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    wait for page or element to load
    Re-login   ${S3_account_name}  ${password}  S3_ACCOUNTS_TAB_ID
    Check Maintenance Option Not Exists
    Delete S3 Account  ${S3_account_name}  ${password}  True   

TEST-1034
    [Documentation]  Test that s3 user should only have access to IAM user and Bucket section in provisoning section
    [Tags]  Priority_High  Smoke_test  user_role  TEST-1034
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    wait for page or element to load
    Re-login   ${S3_account_name}  ${password}  S3_ACCOUNTS_TAB_ID
    Check Dashboard Option Not Exists
    Check Health Option Not Exists
    Verify that S3 user can not access setting menu
    Check Maintenance Option Not Exists
    Delete S3 Account  ${S3_account_name}  ${password}  True

TEST-1036
    [Documentation]  Test that S3 account user have access to create IAM users and buckets
    [Tags]  Priority_High  Smoke_test  user_role  TEST-1036
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${testname}=  generate new User Name
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    wait for page or element to load
    Re-login   ${S3_account_name}  ${password}  S3_ACCOUNTS_TAB_ID
    Navigate To Page  S3_IAM_USER_TAB_ID
    Click Create IAM User Button
    Create IAMuser  ${testname}  ${password}
    wait for page or element to load
    ${status}=  Is IAMuser Present   ${testname}
    Should be equal  ${status}  ${True}
    Delete IAMuser   ${testname}
    wait for page or element to load
    ${status}=  Is IAMuser Present   ${testname}
    Should be equal  ${status}  ${False}
    wait for page or element to load
    Navigate To Page  S3_BUCKET_TAB_ID
    wait for page or element to load
    Click On Create Bucket Form
    wait for page or element to load
    Create Bucket  ${testname}
    wait for page or element to load
    ${status}=  Is Bucket Present   ${testname}
    Should be equal  ${status}  ${True}
    Delete Bucket  ${testname}
    wait for page or element to load
    ${status}=  Is Bucket Present   ${testname}
    Should be equal  ${status}  ${False}
    wait for page or element to load
    Delete S3 Account  ${S3_account_name}  ${password}  True

TEST-99
    [Documentation]  This test case is to verify that create user button remain disabled till required
    ...  fields got filled on s3 configure.
    [Tags]  Priority_High  TEST-99  S3_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    Click on add new s3 account button
    Check create S3 account button disabled

TEST-102
    [Documentation]  This test case is to verify that by clicking on "add new account" button create s3user form is
    ...  getting opened.
    [Tags]  Priority_High  TEST-102  S3_test  Smoke_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    Click on add new s3 account button
    Check s3 account form is opened

TEST-106
    [Documentation]  This test case is to verify that s3 accounts form does not accepts invalid user name.
    [Tags]  Priority_High  TEST-106  S3_test  Smoke_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    Click on add new s3 account button
    Add data to create new S3 account  ${invalid_S3_account_name}  ${invalid_S3_email_id}  ${invalid_S3_account_password}
    ...  ${invalid_S3_account_password}
    Verify message  INVALID_S3_ACCOUNT_NAME_MSG_ID  ${INVALID_S3_ACCOUNT_MESSAGE}

TEST-107
    [Documentation]  This test case is to verify that s3 accounts form does not accepts invalid email id.
    [Tags]  Priority_High  TEST-107  S3_test  Smoke_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    sleep  2s
    Click on add new s3 account button
    Add data to create new S3 account  ${invalid_S3_account_name}  ${invalid_S3_email_id}  ${invalid_S3_account_password}
    ...  ${invalid_S3_account_password}
    Verify message  INVALID_S3_EMAIL_MSG_ID  ${INVALID_S3_EMAIL_MESSAGE}

TEST-109
    [Documentation]  This test case is to verify cancel button functionality on s3 accounts form .
    [Tags]  Priority_High  TEST-109  S3_test  Smoke_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    sleep  2s
    check cancel s3 account form feature

TEST-110
    [Documentation]  This test case is to verify that user is able to create new s3 account.
    [Tags]  Priority_High  TEST-110  S3_test  Smoke_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    sleep  3s
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    CSM GUI Logout
    sleep  2s
    Delete S3 Account  ${S3_account_name}  ${password}

TEST-111
    [Documentation]  This test case is to verify that user is able to delete s3 account.
    [Tags]  Priority_High  TEST-111  S3_test  Smoke_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    sleep  3s
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    CSM GUI Logout
    sleep  2s
    Delete S3 Account  ${S3_account_name}  ${password}

TEST-123
    [Documentation]  This test case is to verify that user should not be able to create duplicate s3 account.
    [Tags]  Priority_High  TEST-123  S3_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    sleep  3s
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    Click on add new s3 account button
    Add data to create new S3 account  ${S3_account_name}  ${email}  ${password}  ${password}
    Click on create new S3 account button
    sleep  1s
    Verify message  DUPLICATE_S3_ACCOUNT_MSG_ID  ${DUPLICATE_S3_ACCOUNT_ALERT_MESSAGE}
    click element  ${CLOSE_DUPLICATE_ACCOUNT_ALERT_MESSAGE_ID}
    sleep  1s
    CSM GUI Logout
    sleep  2s
    Delete S3 Account  ${S3_account_name}  ${password}

TEST-1528
    [Documentation]  This test case is to verify that edit s3 account form is getting opened.
    [Tags]  Priority_High  TEST-1528  TEST-112  S3_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    sleep  3s
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    CSM GUI Logout
    Enter Username And Password  ${S3_account_name}  ${password}
    Click Sigin Button
    sleep  2s
    Verify edit s3 account form getting opened
    Delete S3 Account  ${S3_account_name}  ${password}  True

TEST-116
    [Documentation]  This test case is to verify that update s3 account button remains disabled if data is not entered
    ...  in required fields.
    [Tags]  Priority_High  TEST-116  S3_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    sleep  5s
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    CSM GUI Logout
    Enter Username And Password  ${S3_account_name}  ${password}
    Click Sigin Button
    sleep  2s
    Verify update s3 account button remains disabled
    Delete S3 Account  ${S3_account_name}  ${password}  True

TEST-1530
    [Documentation]  This test case is to verify that user is able to update s3 account password.
    [Tags]  Priority_High  TEST-1530  S3_test  Smoke_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    wait for page or element to load
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    CSM GUI Logout
    Enter Username And Password  ${S3_account_name}  ${password}
    Click Sigin Button
    wait for page or element to load  2s
    ${new_password}=  Generate New Password
    Edit S3 account  ${S3_account_name}  ${new_password}  ${new_password}
    Delete S3 Account  ${S3_account_name}  ${new_password}  True

TEST-1531
    [Documentation]  This test case is to verify update s3 account password field accepts only valid data.
    [Tags]  Priority_High  TEST-1531   S3_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    sleep  5s
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    CSM GUI Logout
    Enter Username And Password  ${S3_account_name}  ${password}
    Click Sigin Button
    sleep  2s
    Verify update s3 account accepts only valid password  ${invalid_S3_account_password}  ${invalid_S3_account_password}
    Delete S3 Account  ${S3_account_name}  ${password}  True

TEST-1532
    [Documentation]  This test case is to verify that update button must remain disable in case password field
    ...  is blank while updating s3 account user
    [Tags]  Priority_High  TEST-1532   S3_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    sleep  5s
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    CSM GUI Logout
    Enter Username And Password  ${S3_account_name}  ${password}
    Click Sigin Button
    sleep  2s
    Verify update s3 account accepts only valid password  ${SPACE*10}   ${SPACE*10}  True
    Delete S3 Account  ${S3_account_name}  ${password}  True

TEST-1533
    [Documentation]  This test case is to verify that update button must remain disable in case confirm password field
    ...  is blank while updating s3 account user
    [Tags]  Priority_High  TEST-1533   S3_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    sleep  5s
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    CSM GUI Logout
    Enter Username And Password  ${S3_account_name}  ${password}
    Click Sigin Button
    sleep  2s
    ${new_password}=  Generate New Password
    Verify update s3 account accepts only valid password  ${new_password}  ${SPACE*10}  False  True
    Delete S3 Account  ${S3_account_name}  ${password}  True

TEST-1534
    [Documentation]  This test case is to verify that s3 account should provide proper error message in case
    ...  user provide miss-match password while updating its user name
    [Tags]  Priority_High  TEST-1534   S3_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    sleep  5s
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    CSM GUI Logout
    Enter Username And Password  ${S3_account_name}  ${password}
    Click Sigin Button
    sleep  2s
    ${new_password}=  Generate New Password
    Verify update s3 account accepts only valid password  ${new_password}  ${password}  False  True
    Delete S3 Account  ${S3_account_name}  ${password}  True

TEST-4025
    [Documentation]  This test case is to verify that s3 account user is able to login to csm GUI
    ...  user provide miss-match password while updating its user name
    [Tags]  Priority_High  TEST-4025  S3_test  Smoke_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    sleep  3s
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    CSM GUI Logout
    sleep  2s
    Delete S3 Account  ${S3_account_name}  ${password}

TEST-4027
    [Documentation]  This test case is to verify that s3 account user is able to perform s3 operations.
    ...  user provide miss-match password while updating its user name
    [Tags]  Priority_High  TEST-4027  S3_test  Smoke_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    sleep  5s
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    CSM GUI Logout
    Enter Username And Password  ${S3_account_name}  ${password}
    Click Sigin Button
    sleep  2s
    ${new_password}=  Generate New Password
    Edit S3 account  ${S3_account_name}  ${new_password}  ${new_password}
    Delete S3 Account  ${S3_account_name}  ${new_password}  True

TEST-5198
    [Documentation]  This test case is to verify that duplicate users should not be created between csm
    ...  users and s3 account users in CSM UI
    [Tags]  Priority_High  TEST-5198  S3_test
    Verify unique username for csm and s3 account

TEST-5199
    [Documentation]  This test case is to verify that s3 accounts form does not accepts invalid password.
    [Tags]  Priority_High  TEST-5199  S3_test  Smoke_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    sleep  2s
    Click on add new s3 account button
    Add data to create new S3 account  ${invalid_S3_account_name}  ${invalid_S3_email_id}  ${invalid_S3_account_password}
    ...  ${invalid_S3_account_password}
    Verify message  INVALID_S3_PASSWORD_MSG_ID  ${INVALID_S3_PASSWORD_MESSAGE}

TEST-5200
    [Documentation]  This test case is to verify that s3 accounts form does not accepts
    ...  miss-match password while creating s3 account.
    [Tags]  Priority_High  TEST-5200  S3_test  Smoke_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    ${new_password}=  Generate New Password
    Click on add new s3 account button
    Add data to create new S3 account  ${invalid_S3_account_name}  ${invalid_S3_email_id}  ${invalid_S3_account_password}
    ...  ${new_password}
    Verify message  INVALID_S3_CONFIRM_PASS_MSG_ID  ${INVALID_S3_CONFIRM_PASSWORD_MESSAGE}

TEST-13101
    [Documentation]  This test case is to verify table for access keys is shown below s3 accounts table
    ...  with required columns.
    [Tags]  Priority_High  TEST-13101  S3_test
    verify the table headers for s3 account access key

TEST-13102
    [Documentation]  This test case is to verify new access key is getting generated.
    ...  with required columns.
    [Tags]  Priority_High  TEST-13102  S3_test
    verify new access key is getting added

TEST-13103
    [Documentation]  This test case is to verify access key is getting deleted.
    [Tags]  Priority_High  TEST-13103  S3_test
    verify delete access key

TEST-13107
    [Documentation]  This test case is to verify data in access key table.
    [Tags]  Priority_High  TEST-13107  S3_test
    verify access key table data

TEST-13108
    [Documentation]  This test case verify that add access key button disables after limit exceeded
    [Tags]  Priority_High  TEST-13108  S3_test
    verify that add access key button disables after limit exceeded

TEST-1529
    [Documentation]  This test case verify that update s3 account has only password options
    [Tags]  Priority_High  TEST-1529  S3_test
    verify update s3 account has only password options


TEST-4026
    [Documentation]  Test User should not able to login using invalid s3 credentials on CSM UI
    ...  Reference : https://jts.seagate.com/browse/TEST-4026
    [Tags]  Priority_High  TEST-4026
    CSM GUI Login with Incorrect Credentials  ${url}  ${browser}  ${headless}
    Validate CSM Login Failure
    Close Browser
