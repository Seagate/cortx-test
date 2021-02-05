*** Settings ***
Documentation    This suite verifies the testcases for csm login
Library     SeleniumLibrary
Resource    ../../../resources/page_objects/loginPage.robot
Resource    ../../../resources/page_objects/s3accountPage.robot
Resource   ../../../resources/common/common.robot
#Variables  ../../../resources/common/element_locators.py
Variables  ../../../resources/common/common_variables.py


Suite Teardown  Close All Browsers
Force Tags  CSM_GUI  CSM_login
Test Setup  CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
Test Teardown  Close Browser

*** Variables ***
${url}  https://10.230.246.58:28100/#/
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
    [Documentation]  This test is to verify that S3 account existes
    [Tags]  Priority_High  S3_test
    Validate CSM Login Success  ${username}
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    Check S3 Account Exists     S3_ACCOUNTS_TABLE_XPATH  ${S3_ACCOUNT}

Test action on table
    [Documentation]  This test case is to verify that user can perform the actions on the table elements.
    [Tags]  Priority_High  S3_test
    Validate CSM Login Success  ${username}
    Navigate To Page    MANAGE_MENU_ID
    sleep  2s
    Action on the table     ${CSM_USER}  CSM_USER_EDIT_XPATH

test_99
    [Documentation]  This test case is to verify that create user button remain disabled till required
    ...  fields got filled on s3 configure.
    [Tags]  Priority_High  test_99  S3_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    Click on add new s3 account button
    Check create S3 account button disabled

test_102
    [Documentation]  This test case is to verify that by clicking on "add new account" button create s3user form is
    ...  getting opened.
    [Tags]  Priority_High  test_102  S3_test  Somoke_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    Click on add new s3 account button
    Check s3 account form is opened

test_106
    [Documentation]  This test case is to verify that s3 accounts form does not accepts invalid user name.
    [Tags]  Priority_High  test_106  S3_test  Somoke_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    Click on add new s3 account button
    Add data to create new S3 account  ${invalid_S3_account_name}  ${invalid_S3_email_id}  ${invalid_S3_account_password}
    ...  ${invalid_S3_account_password}
    Verify message  INVALID_S3_ACCOUNT_NAME_MSG_ID  ${INVALID_S3_ACCOUNT_MESSAGE}

test_107
    [Documentation]  This test case is to verify that s3 accounts form does not accepts invalid email id.
    [Tags]  Priority_High  test_107  S3_test  Somoke_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    Click on add new s3 account button
    Add data to create new S3 account  ${invalid_S3_account_name}  ${invalid_S3_email_id}  ${invalid_S3_account_password}
    ...  ${invalid_S3_account_password}
    Verify message  INVALID_S3_EMAIL_MSG_ID  ${INVALID_S3_EMAIL_MESSAGE}

test_109
    [Documentation]  This test case is to verify cancle button functionality on s3 accounts form .
    [Tags]  Priority_High  test_109  S3_test  Somoke_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    check cancel s3 account form feature

test_110
    [Documentation]  This test case is to verify that user is able to create new s3 account.
    [Tags]  Priority_High  test_110  S3_test  Somoke_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    sleep  3s
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    CSM GUI Logout
    sleep  2s
    Delete S3 Account  ${S3_account_name}  ${password}

test_111
    [Documentation]  This test case is to verify that user is able to delete s3 account.
    [Tags]  Priority_High  test_111  S3_test  Somoke_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    sleep  3s
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    CSM GUI Logout
    sleep  2s
    Delete S3 Account  ${S3_account_name}  ${password}

test_123
    [Documentation]  This test case is to verify that user should not be able to create duplicate s3 account.
    [Tags]  Priority_High  test_123  S3_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
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

test_1528
    [Documentation]  This test case is to verify that edit s3 account form is getting opened.
    [Tags]  Priority_High  test_1528  test_112  S3_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
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

test_116
    [Documentation]  This test case is to verify that update s3 account button remains disabled if data is not entered
    ...  in required fields.
    [Tags]  Priority_High  test_116  S3_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
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

test_1530
    [Documentation]  This test case is to verify that user is able to update s3 account password.
    [Tags]  Priority_High  test_1530  S3_test  Somoke_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
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

test_1531
    [Documentation]  This test case is to verify update s3 account password field accepts only valid data.
    [Tags]  Priority_High  test_1531   S3_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
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


test_1532
    [Documentation]  This test case is to verify that update button must remain disable in case password field
    ...  is blank while updating s3 account user
    [Tags]  Priority_High  test_1532   S3_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
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


test_1533
    [Documentation]  This test case is to verify that update button must remain disable in case confirm password field
    ...  is blank while updating s3 account user
    [Tags]  Priority_High  test_1533   S3_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
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

test_1534
    [Documentation]  This test case is to verify that s3 account should provide proper error message in case
    ...  user provide miss-match password while updating its user name
    [Tags]  Priority_High  test_1534   S3_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
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

test_4025
    [Documentation]  This test case is to verify that s3 account user is able to login to csm GUI
    ...  user provide miss-match password while updating its user name
    [Tags]  Priority_High  test_4025  S3_test  Somoke_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    sleep  3s
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    CSM GUI Logout
    sleep  2s
    Delete S3 Account  ${S3_account_name}  ${password}


test_4027
    [Documentation]  This test case is to verify that s3 account user is able to perform s3 oprations.
    ...  user provide miss-match password while updating its user name
    [Tags]  Priority_High  test_4027  S3_test  Somoke_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
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

test_5198
    [Documentation]  This test case is to verify that duplicate users should not be created between csm
    ...  users and s3 account users in CSM UI
    [Tags]  Priority_High  test_5198  S3_test
    Verify unique username for csm and s3 account


test_5199
    [Documentation]  This test case is to verify that s3 accounts form does not accepts invalid password.
    [Tags]  Priority_High  test_5199  S3_test  Somoke_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    Click on add new s3 account button
    Add data to create new S3 account  ${invalid_S3_account_name}  ${invalid_S3_email_id}  ${invalid_S3_account_password}
    ...  ${invalid_S3_account_password}
    Verify message  INVALID_S3_PASSWORD_MSG_ID  ${INVALID_S3_PASSWORD_MESSAGE}

test_5200
    [Documentation]  This test case is to verify that s3 accounts form does not accepts
    ...  miss-match password while creating s3 account.
    [Tags]  Priority_High  test_5200  S3_test  Somoke_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${new_password}=  Generate New Password
    Click on add new s3 account button
    Add data to create new S3 account  ${invalid_S3_account_name}  ${invalid_S3_email_id}  ${invalid_S3_account_password}
    ...  ${new_password}
    Verify message  INVALID_S3_CONFIRM_PASS_MSG_ID  ${INVALID_S3_CONFIRM_PASSWORD_MESSAGE}

test_13101
    [Documentation]  This test case is to verify table for access keys is shown below s3 accounts table
    ...  with required columns.
    [Tags]  Priority_High  test_13101  S3_test
    verify the table eders for s3 account access key

test_13102
    [Documentation]  This test case is to verify new access key is getting generated.
    ...  with required columns.
    [Tags]  Priority_High  test_13102  S3_test
    verify new access key is getting added

test_13103
    [Documentation]  This test case is to verify access key is getting deleted.
    [Tags]  Priority_High  test_13103  S3_test
    verify delete access key

test_13107
    [Documentation]  This test case is to verify data in access key table.
    [Tags]  Priority_High  test_13107  S3_test
    verify access key table data

test_13108
    [Documentation]  This test case verify that add access key button disables after limit exceeded
    [Tags]  Priority_High  test_13108  S3_test
    verify that add access key button disables after limit exceeded

test_1529
    [Documentation]  This test case verify that update s3 account has only password options
    [Tags]  Priority_High  test_1529  S3_test
    verify update s3 account has only password options
