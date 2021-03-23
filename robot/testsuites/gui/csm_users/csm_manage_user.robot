*** Settings ***
Documentation    This suite verifies the testcases for csm user creation
Resource   ${EXECDIR}/resources/page_objects/alertPage.robot
Resource   ${EXECDIR}/resources/page_objects/dashboard.robot
Resource   ${EXECDIR}/resources/page_objects/loginPage.robot
Resource   ${EXECDIR}/resources/page_objects/preboardingPage.robot
Resource   ${EXECDIR}/resources/page_objects/s3accountPage.robot
Resource   ${EXECDIR}/resources/page_objects/settingsPage.robot
Resource   ${EXECDIR}/resources/page_objects/userSettingsLocalPage.robot

Suite Setup  run keywords   check csm admin user status  ${url}  ${browser}  ${headless}  ${username}  ${password}
...  AND  Close Browser
Test Setup  CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
Test Teardown  Close Browser
Suite Teardown  Close All Browsers
Force Tags  CSM_GUI  CSM_USER

*** Variables ***
${browser}  chrome
${headless}  True
${navigate_to_subpage}  False
${Sub_tab}  None
${page name}  MANAGE_MENU_ID
${url}
${username}
${password}

*** Keywords ***

Create and login with CSM manage user
    [Documentation]  This keyword is to create and login with csm monitor user
    ${new_user_name}=  Generate New User Name
    ${new_password}=  Generate New Password
    Navigate To Page  ${page name}
    Create New CSM User  ${new_user_name}  ${new_password}  manage
    Click On Confirm Button
    Verify New User  ${new_user_name}
    Re-login  ${new_user_name}  ${new_password}  ${page name}
    [Return]  ${new_user_name}  ${new_password}


*** Test Cases ***

TEST-1220
    [Documentation]  Test manager user don't have access to setting menu.
    [Tags]  Priority_High  user_role  TEST-1220
    ${new_user_name}  ${new_password}=  Create and login with CSM manage user
    Navigate To Page  DASHBOARD_MENU_ID
    Sleep  1s
    Verify that CSM manage user can not access setting menu
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-1226
    [Documentation]  Test manager user can not edit or delete s3 account.
    [Tags]  Priority_High  user_role  TEST-1226
    ${new_user_name}  ${new_password}=  Create and login with CSM manage user
    Verify Absence of Edit And Delete Button on S3account
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-1218
    [Documentation]  Test manager user don't have access to Lyve Pilot menu
    [Tags]  Priority_High  user_role  TEST-1218
    ${new_user_name}  ${new_password}=  Create and login with CSM manage user
    wait for page or element to load  2s
    Verify that user can not access Lyve Pilot menu
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-1216
    [Documentation]  Test manager user can not access IAM user and buckets tab.
    [Tags]  Priority_High  user_role  TEST-1216
    ${new_user_name}  ${new_password}=  Create and login with CSM manage user
    wait for page or element to load  2s
    Verify IAM User Section Not Present
    Verify bucket Section Not Present
    wait for page or element to load  2s
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-1215
    [Documentation]  Test that CSM user with role manager can view and create s3 accounts.
    [Tags]  Priority_High  user_role  TEST-1215
    ${new_user_name}  ${new_password}=  Create and login with CSM manage user
    wait for page or element to load  2s
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    wait for page or element to load  2s
    ${S3_account_name}  ${email}  ${s3_password} =  Create S3 account
    wait for page or element to load  3s
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    CSM GUI Logout
    wait for page or element to load  2s
    Delete S3 Account  ${S3_account_name}  ${s3_password}
    wait for page or element to load  2s
    Enter Username And Password  ${username}  ${password}
    Click Sigin Button
    Navigate To Page    MANAGE_MENU_ID
    Delete CSM User  ${new_user_name}

TEST-1217
    [Documentation]  Test that manager user can view and create CSM users.
    [Tags]  Priority_High  user_role  TEST-1217
    ${new_user_name}  ${new_password}=  Create and login with CSM manage user
    wait for page or element to load  2s
    ${new_csm_user_password}=  Generate New Password
    ${new_csm_user_name}=  Generate New User Name
    Create New CSM User  ${new_csm_user_name}  ${new_csm_user_password}  manage
    Click On Confirm Button
    wait for page or element to load  2s
    Click Element  ${DELETE_ICON_MANAGE_USER_ID}
    wait for page or element to load  2s
    Click button    ${IAM_USER_SUCCESS_MESSAGE_BUTTON_ID }
    wait for page or element to load  2s
    Enter Username And Password  ${username}  ${password}
    Click Sigin Button
    wait for page or element to load  2s
    Navigate To Page    MANAGE_MENU_ID
    Delete CSM User  ${new_csm_user_name}
