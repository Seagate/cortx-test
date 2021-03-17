*** Settings ***
Documentation    This suite verifies the testcases for csm user creation
Resource    ${EXECDIR}/resources/page_objects/loginPage.robot
Resource    ${EXECDIR}/resources/page_objects/userSettingsLocalPage.robot
Resource    ${EXECDIR}/resources/page_objects/alertPage.robot
Resource    ${EXECDIR}/resources/page_objects/dashboard.robot
Resource    ${EXECDIR}/resources/page_objects/preboardingPage.robot

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

Create and login with CSM monitor user
    [Documentation]  This keyword is to create and login with csm monitor user
    ${new_user_name}=  Generate New User Name
    ${new_password}=  Generate New Password
    Navigate To Page  ${page name}
    Create New CSM User  ${new_user_name}  ${new_password}  monitor
    Click On Confirm Button
    Verify New User  ${new_user_name}
    Re-login  ${new_user_name}  ${new_password}  ${page name}
    [Return]  ${new_user_name}  ${new_password}



*** Test Cases ***
TEST-5321
    [Documentation]  Test that user with monitor privilege should be able to edit his own email
    ...  id and password.
    [Tags]  Priority_High  user_role  TEST-5321
    ${new_user_name}  ${new_password}=  Create and login with CSM monitor user
    ${updated_password}=  Generate New Password
    ${updated_email}=  Generate New User Email
    Edit CSM User Details  ${new_user_name}  ${updated_password}  ${updated_email}  ${new_password}
    Re-login  ${new_user_name}  ${updated_password}  ${page_name}
    Validate CSM Login Success  ${new_user_name}
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-5269
    [Documentation]  Test user with monitor privilege should not able to provide comment on alert.
    [Tags]  Priority_High  user_role  TEST-5269
    ${new_user_name}  ${new_password}=  Create and login with CSM monitor user
    Click AlertPage Image
    wait for page or element to load  5s
    Click Comments Button
    wait for page or element to load  2s
    Verify Absence of comment textbox
    Click CommentsClose Image
    wait for page or element to load  2s
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-1239
    [Documentation]  Test that CSM user with role monitor cannot create, delete Any CSM users.
    [Tags]  Priority_High  user_role  TEST-1239
    ${new_user_name}  ${new_password}=  Create and login with CSM monitor user
    Verify that monitor user is not able to create delete csm user
    wait for page or element to load  2s
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-1234
    [Documentation]  Test that monitor user cannot create, update or delete s3 accounts.
    [Tags]  Priority_High  user_role  TEST-1234
    ${new_user_name}  ${new_password}=  Create and login with CSM monitor user
    Verify Absence of Edit And Delete Button on S3account
    wait for page or element to load  2s
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-1233
    [Documentation]  Test that CSM user with role monitor cannot acknowledge or comment on alerts.
    [Tags]  Priority_High  user_role  TEST-1233
    ${new_user_name}  ${new_password}=  Create and login with CSM monitor user
    Click AlertPage Image
    wait for page or element to load  5s
    Click Comments Button
    wait for page or element to load  2s
    Verify Absence of comment textbox
    Click CommentsClose Image
    Verify Absence of Acknowledge
    wait for page or element to load  2s
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-1224
    [Documentation]  Test that CSM user with role monitor don't have access to Lyve Pilot menu
    [Tags]  Priority_High  user_role  TEST-1224
    ${new_user_name}  ${new_password}=  Create and login with CSM monitor user
    wait for page or element to load  2s
    Verify that user can not access Lyve Pilot menu
    wait for page or element to load  2s
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-1223
    [Documentation]  Test that CSM user with role monitor can view CSM users.
    [Tags]  Priority_High  user_role  TEST-1223
    ${new_user_name}  ${new_password}=  Create and login with CSM monitor user
    Verify New User  ${new_user_name}
    sleep  2s
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-1222
    [Documentation]  Test that monitor user cannot view, create, update or delete IAM users.
    [Tags]  Priority_High  user_role  TEST-1222
    ${new_user_name}  ${new_password}=  Create and login with CSM monitor user
    Verify IAM User Section Not Present
    Verify bucket Section Not Present
    wait for page or element to load  2s
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-1221
    [Documentation]  Test that CSM user with role monitor can view s3 accounts
    [Tags]  Priority_High  user_role  TEST-1221
    ${new_user_name}  ${new_password}=  Create and login with CSM monitor user
    Verify Absence of Edit And Delete Button on S3account
    wait for page or element to load  2s
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}
