*** Settings ***
Documentation    This suite verifies the testcases for csm user creation
Resource    ${RESOURCES}/resources/page_objects/alertPage.robot
Resource    ${RESOURCES}/resources/page_objects/bucket_page.robot
Resource    ${RESOURCES}/resources/page_objects/loginPage.robot
Resource    ${RESOURCES}/resources/page_objects/s3accountPage.robot
Resource    ${RESOURCES}/resources/page_objects/lyvePilotPage.robot
Resource    ${RESOURCES}/resources/page_objects/userSettingsLocalPage.robot
Resource    ${RESOURCES}/resources/page_objects/dashboardPage.robot
Resource    ${RESOURCES}/resources/page_objects/preboardingPage.robot

Test Setup  CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
Test Teardown  Close Browser
Suite Teardown  Close All Browsers
Force Tags  CSM_GUI  CSM_USER

*** Variables ***
${browser}  chrome
${headless}  True
${navigate_to_subpage}  False
${Sub_tab}  ADMINISTRATIVE_USER_TAB_ID
${page_name}  MANAGE_MENU_ID
${url}
${username}
${password}

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
    wait for page or element to load
    Click Comments Button
    wait for page or element to load
    Verify Absence of comment textbox
    Click CommentsClose Image
    wait for page or element to load
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-1239
    [Documentation]  Test that CSM user with role monitor cannot create, delete Any CSM users and can not edit user other than itself.
    [Tags]  Priority_High  user_role  TEST-1239
    ${new_user_name}  ${new_password}=  Create and login with CSM monitor user
    wait for page or element to load
    Verify that monitor user is not able to create delete csm user
    @{users_list}=  Get Column Data  ${CSM_TABLE_COLUMN_XPATH}  3
    FOR    ${user}    IN    @{users_list}
        Run Keyword If  "${user}" == "${new_user_name}"  Verify Delete Action Disabled On The Table Element  ${user}
        ...  ELSE  Verify Edit Action Disabled On The Table Element  ${user}
    END
    ${changed_password}=  Generate New Password
    ${new_email}=  Generate New User Email
    Edit CSM User Details  ${new_user_name}  ${changed_password}  ${new_email}  ${new_password}
    Re-login  ${new_user_name}  ${changed_password}  ${page_name}
    Validate CSM Login Success  ${new_user_name}
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-1838
    [Documentation]  Test that monitor user can't able to delete any user
    ...  Reference : https://jts.seagate.com/browse/TEST-1838
    [Tags]  Priority_High  TEST-1838
    ${new_user_name}  ${new_password}=  Create and login with CSM monitor user
    wait for page or element to load
    Navigate To Page  DASHBOARD_MENU_ID
    Verify Absence of Edit And Delete Button on S3account
    Navigate To Page  DASHBOARD_MENU_ID
    Verify Absence of Delete Button on CSM users
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-1234
    [Documentation]  Test that monitor user cannot create, update or delete s3 accounts.
    [Tags]  Priority_High  user_role  TEST-1234
    ${new_user_name}  ${new_password}=  Create and login with CSM monitor user
    wait for page or element to load
    Navigate To Page  DASHBOARD_MENU_ID
    Verify Absence of Edit And Delete Button on S3account
    wait for page or element to load
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-1233
    [Documentation]  Test that CSM user with role monitor cannot acknowledge or comment on alerts.
    [Tags]  Priority_High  user_role  TEST-1233
    ${new_user_name}  ${new_password}=  Create and login with CSM monitor user
    Click AlertPage Image
    wait for page or element to load
    Click Comments Button
    wait for page or element to load
    Verify Absence of comment textbox
    Click CommentsClose Image
    Verify Absence of Acknowledge
    wait for page or element to load
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-1224
    [Documentation]  Test that CSM user with role monitor don't have access to Lyve Pilot menu
    [Tags]  Priority_High  user_role  TEST-1224
    ${new_user_name}  ${new_password}=  Create and login with CSM monitor user
    wait for page or element to load
    Verify that user can not access Lyve Pilot menu
    wait for page or element to load
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-1223
    [Documentation]  Test that CSM user with role monitor can view CSM users.
    [Tags]  Priority_High  user_role  TEST-1223
    ${new_user_name}  ${new_password}=  Create and login with CSM monitor user
    Verify New User  ${new_user_name}
    wait for page or element to load
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-1222
    [Documentation]  Test that monitor user cannot view, create, update or delete IAM users.
    [Tags]  Priority_High  user_role  TEST-1222
    ${new_user_name}  ${new_password}=  Create and login with CSM monitor user
    wait for page or element to load
    Navigate To Page  DASHBOARD_MENU_ID
    Verify IAM User Section Not Present
    Navigate To Page  DASHBOARD_MENU_ID
    Verify bucket Section Not Present
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-1221
    [Documentation]  Test that CSM user with role monitor can view s3 accounts
    [Tags]  Priority_High  user_role  TEST-1221
    ${new_user_name}  ${new_password}=  Create and login with CSM monitor user
    wait for page or element to load
    Navigate To Page  DASHBOARD_MENU_ID
    Verify Absence of Edit And Delete Button on S3account
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-18329
    [Documentation]  Test that csm user with monitor role is not able to reset is passwrod of s3 account user through csm GUI.
    ...  Reference : https://jts.seagate.com/browse/TEST-18329
    [Tags]  Priority_High  user_role  TEST-18329
    ${new_user_name}  ${new_password}=  Create and login with CSM monitor user
    wait for page or element to load
    Navigate To Page  DASHBOARD_MENU_ID
    Verify Absence of Reset Passwrod Button on S3account
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-22768
    [Documentation]  Test that CSM user with role monitor cannot delete empty or non-empty s3 account
    ...  Reference : https://jts.seagate.com/browse/TEST-22768
    [Tags]  Priority_High  TEST-22768  S3_test
    ${S3_account_name}  ${email}  ${S3_password} =  Create S3 account
    wait for page or element to load
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    Navigate To Page  DASHBOARD_MENU_ID
    ${new_user_name}  ${new_password}=  Create and login with CSM monitor user
    wait for page or element to load
    Navigate To Page   CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    Verify Absence of Delete Button on S3account
    Re-login  ${username}  ${password}  DASHBOARD_MENU_ID
    wait for page or element to load
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    Delete s3 account using csm user  ${S3_account_name}
    Navigate To Page  ADMINISTRATIVE_USER_TAB_ID
    Delete CSM User  ${new_user_name}

TEST-23046
    [Documentation]  Test that CSM user with role monitor cannot create user with admin role.
    [Tags]  Priority_High  user_role  TEST-23046
    ${new_user_name}  ${new_password}=  Create and login with CSM monitor user
    wait for page or element to load
    Verify Monitor User Is Not Able To Create Csm User
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-23053
    [Documentation]  Test that monitor user should not able to reset other uses password with  admin role from csm UI
    ...  Reference : https://jts.seagate.com/browse/TEST-23053
    [Tags]  Priority_High  TEST-23053
    Log To Console And Report  Create Account with role: monitor
    ${monitor_user_name}  ${monitor_user_password}=  Create and login with CSM monitor user
    wait for page or element to load
    @{admin_users}=  Read Selective Table Data  ${CSM_TABLE_COLUMN_XPATH}  admin  ${CSM_ROLE_COLUMN}  ${CSM_USERNAME_COLUMN}
    FOR    ${user}    IN    @{admin_users}
        Log To Console And Report  Verify Edit Action Disable for ${user}
        Verify Edit Action Disabled On The Table Element  ${user}
    END
    Re-login  ${user_name}  ${password}  MANAGE_MENU_ID
    Delete CSM User  ${monitor_user_name}
