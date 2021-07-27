*** Settings ***
Documentation    This suite verifies the testcases for csm user creation
Resource   ${RESOURCES}/resources/page_objects/alertPage.robot
Resource   ${RESOURCES}/resources/page_objects/bucket_page.robot
Resource   ${RESOURCES}/resources/page_objects/dashboardPage.robot
Resource   ${RESOURCES}/resources/page_objects/lyvePilotPage.robot
Resource   ${RESOURCES}/resources/page_objects/loginPage.robot
Resource   ${RESOURCES}/resources/page_objects/preboardingPage.robot
Resource   ${RESOURCES}/resources/page_objects/s3accountPage.robot
Resource   ${RESOURCES}/resources/page_objects/settingsPage.robot
Resource   ${RESOURCES}/resources/page_objects/userSettingsLocalPage.robot

#Suite Setup  run keywords   check csm admin user status  ${url}  ${browser}  ${headless}  ${username}  ${password}
#...  AND  Close Browser
Test Setup  CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
Test Teardown  Close Browser
Suite Teardown  Close All Browsers
Force Tags  CSM_GUI  CSM_USER

*** Variables ***
${browser}  chrome
${headless}  True
${navigate_to_subpage}  False
${Sub_tab}  None
${page_name}  MANAGE_MENU_ID
${url}
${username}
${password}

*** Keywords ***

Create and login with CSM manage user
    [Documentation]  This keyword is to create and login with csm manage user
    ${new_user_name}=  Generate New User Name
    ${new_password}=  Generate New Password
    Navigate To Page  ${page_name}
    wait for page or element to load
    Create New CSM User  ${new_user_name}  ${new_password}  manage
    Click On Confirm Button
    Verify New User  ${new_user_name}
    Re-login  ${new_user_name}  ${new_password}  ${page_name}
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

TEST-1218
    [Documentation]  Test manager user don't have access to Lyve Pilot menu
    [Tags]  Priority_High  user_role  TEST-1218
    ${new_user_name}  ${new_password}=  Create and login with CSM manage user
    wait for page or element to load
    Verify that user can not access Lyve Pilot menu
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-1216
    [Documentation]  Test manager user can not access IAM user and buckets tab.
    [Tags]  Priority_High  user_role  TEST-1216
    ${new_user_name}  ${new_password}=  Create and login with CSM manage user
    wait for page or element to load
    Verify IAM User Section Not Present
    Verify bucket Section Not Present
    wait for page or element to load
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-1215
    [Documentation]  Test that CSM user with role manager can view and create s3 accounts.
    [Tags]  Priority_High  user_role  TEST-1215
    ${new_user_name}  ${new_password}=  Create and login with CSM manage user
    wait for page or element to load
    Navigate To Page  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    ${S3_account_name}  ${email}  ${s3_password} =  Create S3 account
    wait for page or element to load  3s
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    CSM GUI Logout
    wait for page or element to load
    Delete S3 Account  ${S3_account_name}  ${s3_password}
    Re-login  ${username}  ${password}  MANAGE_MENU_ID  False
    Delete CSM User  ${new_user_name}

TEST-1217
    [Documentation]  Test that manager user can view and create CSM users and should be able to edit his own email
    [Tags]  Priority_High  user_role  TEST-1217
    ${new_user_name}  ${new_password}=  Create and login with CSM manage user
    wait for page or element to load
    ${new_csm_user_name}=  Generate New User Name
    ${new_csm_user_password}=  Generate New Password
    ${updated_password}=  Generate New Password
    ${updated_email}=  Generate New User Email
    Create New CSM User  ${new_csm_user_name}  ${new_csm_user_password}  manage
    Click On Confirm Button
    wait for page or element to load
    Edit CSM User Details  ${new_user_name}  ${updated_password}  ${updated_email}  ${new_password}
    Re-login  ${new_user_name}  ${updated_password}  ${page_name}
    Delete Logged In CSM User  ${new_user_name}
    wait for page or element to load
    Enter Username And Password  ${new_user_name}  ${updated_password}
    Click Sigin Button
    Validate CSM Login Failure
    Close Browser
    CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
    Navigate To Page  ${page_name}
    Delete CSM User  ${new_csm_user_name}

TEST-18327
    [Documentation]  Test that csm user with Manage rights is able to reset the s3 account users password through CSM GUI.
    ...  Reference : https://jts.seagate.com/browse/TEST-18327
    [Tags]  Priority_High  TEST-18327  S3_test  Smoke_test
    ${new_user_name}  ${new_password}=  Create and login with CSM manage user
    wait for page or element to load
    Navigate To Page  CSM_S3_ACCOUNTS_TAB_ID
    ${S3_account_name}  ${email}  ${S3_password} =  Create S3 account
    wait for page or element to load
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    ${S3_new_password}=  Generate New Password
    Edit S3 User Password  ${S3_account_name}  ${S3_new_password}  ${S3_new_password}
    Re-login  ${S3_account_name}  ${S3_new_password}  S3_ACCOUNTS_TAB_ID
    Delete S3 Account  ${S3_account_name}  ${S3_new_password}  True
    Re-login  ${username}  ${password}  ${page_name}  False
    wait for page or element to load
    Delete CSM User  ${new_user_name}

TEST-21591
    [Documentation]  Test that CSM user with role manager can delete empty s3 account
    ...  Reference : https://jts.seagate.com/browse/TEST-21591
    [Tags]  Priority_High  TEST-21591  S3_test
    ${new_csm_user_name}  ${new_password}=  Create and login with CSM manage user
    wait for page or element to load
    Navigate To Page  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    ${S3_account_name}  ${email}  ${S3_password} =  Create S3 account
    wait for page or element to load
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    Delete s3 account using csm user  ${S3_account_name}
    wait for page or element to load
    Re-login  ${username}  ${password}  ${page_name}
    wait for page or element to load
    Delete CSM User  ${new_csm_user_name}

TEST-21592
    [Documentation]  Test that CSM user with role manager cannot delete non-empty s3 account
    ...  Reference : https://jts.seagate.com/browse/TEST-21592
    [Tags]  Priority_High  TEST-21592  S3_test
    ${new_csm_user_name}  ${new_password}=  Create and login with CSM manage user
    wait for page or element to load
    Navigate To Page  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    ${S3_account_name}  ${email}  ${S3_password} =  Create S3 account
    wait for page or element to load
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    Re-login  ${S3_account_name}  ${S3_password}  S3_ACCOUNTS_TAB_ID
    Navigate To Page  S3_BUCKET_TAB_ID
    Click On Create Bucket Form
    ${bucketname}=  Generate New User Name
    Create Bucket  ${bucketname}
    wait for page or element to load
    Re-login  ${new_csm_user_name}  ${new_password}  MANAGE_MENU_ID
    wait for page or element to load
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    Verify Error Msg is Shown For Non Empty S3account delete  ${S3_account_name}
    wait for page or element to load
    Re-login  ${S3_account_name}  ${S3_password}  S3_ACCOUNTS_TAB_ID
    Navigate To Page  S3_BUCKET_TAB_ID
    Delete Bucket  ${bucketname}
    Delete S3 Account  ${S3_account_name}  ${password}  True
    wait for page or element to load
    Re-login  ${username}  ${password}  ${page_name}  False
    wait for page or element to load
    Delete CSM User  ${new_csm_user_name}

TEST-23782
    [Documentation]  Test that manage user should be able to create and not able to delete users with monitor role from csm UI
    [Tags]  Priority_High  user_role  TEST-23782
    ${new_user_name}  ${new_password}=  Create and login with CSM manage user
    wait for page or element to load
    ${new_csm_user_password}=  Generate New Password
    ${new_csm_user_name}=  Generate New User Name
    Create New CSM User  ${new_csm_user_name}  ${new_csm_user_password}  monitor
    Click On Confirm Button
    wait for page or element to load
    Verify Delete Action Disabled On The Table Element  ${new_csm_user_name}
    wait for page or element to load
    Re-login  ${username}  ${password}  MANAGE_MENU_ID
    Delete CSM User  ${new_csm_user_name}

TEST-23044
    [Documentation]  Test that CSM user with role manage cannot create user with admin role.
    [Tags]  Priority_High  user_role  TEST-23044
    ${new_user_name}  ${new_password}=  Create and login with CSM manage user
    wait for page or element to load
    Click On Add User Button
    Page Should Not Contain Element  ${ADD_ADMIN_USER_RADIO_BUTTON_ID}
    Click On Cancel Button
    Re-login  ${username}  ${password}  ${page_name}
    wait for page or element to load
    Delete CSM User  ${new_user_name}

TEST-23889
    [Documentation]  Test that manager user is able to change role of other manage role user (NOT self) from manage role to monitor role from csm UI.
    ...  Reference : https://jts.seagate.com/browse/TEST-23889
    [Tags]  Priority_High  TEST-23889
    ${new_user_name}  ${new_password}=  Create and login with CSM manage user
    wait for page or element to load
    ${new_csm_user_password}=  Generate New Password
    ${new_csm_user_name}=  Generate New User Name
    Create New CSM User  ${new_csm_user_name}  ${new_csm_user_password}  manage
    Click On Confirm Button
    Edit CSM User Type  ${new_csm_user_name}  monitor
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}
    Delete CSM User  ${new_csm_user_name}

TEST-23888
    [Documentation]  Test: CSM GUI: Test that manage user should be able to change role of user with monitor role to manage role from csm UI.
    ...  Reference : https://jts.seagate.com/browse/TEST-23888
    [Tags]  Priority_High  TEST-23888
    ${new_user_name}  ${new_password}=  Create and login with CSM manage user
    wait for page or element to load
    ${new_csm_user_password}=  Generate New Password
    ${new_csm_user_name}=  Generate New User Name
    Create New CSM User  ${new_csm_user_name}  ${new_csm_user_password}  monitor
    Click On Confirm Button
    Edit CSM User Type  ${new_csm_user_name}  manage
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}
    Delete CSM User  ${new_csm_user_name}

TEST-23886
    [Documentation]  Test: CSM GUI: Test that manage user should NOT be able to change role of self to any other role from csm UI.
    ...  Reference : https://jts.seagate.com/browse/TEST-23886
    [Tags]  Priority_High  TEST-23886
    ${new_user_name}  ${new_password}=  Create and login with CSM manage user
    Verify Change User Type Radio Button Disabled  ${new_user_name}
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-23843
    [Documentation]  Test that csm user with Manage rights is able to reset passwords of users with manage and monitor roles from csm UI.
    ...  Reference : https://jts.seagate.com/browse/TEST-23843
    [Tags]  Priority_High  TEST-23843
    ${new_user_name}  ${new_password}=  Create and login with CSM manage user
    ${new_csm_user_password}=  Generate New Password
    ${new_csm_user_name}=  Generate New User Name
    Create New CSM User  ${new_csm_user_name}  ${new_csm_user_password}  manage
    Click on confirm button
    wait for page or element to load
    ${new_csm_user_password1}=  Generate New Password
    ${new_csm_user_name1}=  Generate New User Name
    Create New CSM User  ${new_csm_user_name1}  ${new_csm_user_password1}  monitor
    Click on confirm button
    wait for page or element to load
    ${new_csm_password}=  Generate New Password        #for new manage user
    Edit CSM User Password  ${new_csm_user_name}  ${new_csm_password}
    ${new_csm_password1}=  Generate New Password       #for new monitor user
    Edit CSM User Password  ${new_csm_user_name1}  ${new_csm_password1}
    Re-login  ${new_csm_user_name}  ${new_csm_password}  ${page_name} #relogin using new manage user and changed password
    Validate CSM Login Success  ${new_csm_user_name}
    Re-login  ${new_csm_user_name1}  ${new_csm_password1}  ${page_name}  #relogin using new monitor user and changed password
    Validate CSM Login Success  ${new_csm_user_name1}

TEST-23859
    [Documentation]  Test user should be able to select number of rows to be displayed per page in administrative users CSM UI page
    ...  Reference : https://jts.seagate.com/browse/TEST-23859
    [Tags]  Priority_High  TEST-23859
    Navigate To Page  ${page_name}
    ${fetched_values}=  Read Pagination Options
    ${actual_values}=  Create List  5 rows  10 rows  20 rows  30 rows  50 rows  100 rows  150 rows  200 rows
    Lists Should Be Equal  ${fetched_values}  ${actual_values}
