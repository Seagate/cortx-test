*** Settings ***
Documentation    This suite verifies the testcases for csm user creation
Resource   ${RESOURCES}/resources/page_objects/alertPage.robot
Resource   ${RESOURCES}/resources/page_objects/bucket_page.robot
Resource   ${RESOURCES}/resources/page_objects/loginPage.robot
Resource   ${RESOURCES}/resources/page_objects/preboardingPage.robot
Resource   ${RESOURCES}/resources/page_objects/s3accountPage.robot
Resource   ${RESOURCES}/resources/page_objects/settingsPage.robot
Resource   ${RESOURCES}/resources/page_objects/userSettingsLocalPage.robot

# Suite Setup  run keywords   check csm admin user status  ${url}  ${browser}  ${headless}
# ...  ${username}  ${password}
# ...  AND  Close Browser
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
${Download_File_Path}  /root/Downloads
${server_file_name}  s3server.pem

*** Test Cases ***

TEST-5326
    [Documentation]  Test that "Add new user" should open a form to create new user on the User Settings
    ...  Reference : https://jts.seagate.com/browse/TEST-5326
    [Tags]  Priority_High  TEST-5326
    Navigate To Page  ${page_name}
    Click on add user button
    Log To Console And Report  Verifying the Form To Create CSM Users
    Verify A Form Got Open To Create CSM Users

TEST-1852
    [Documentation]  Test that by clicking on the "cancel" it should close the form without creating new user on the User Settings
    ...  Reference : https://jts.seagate.com/browse/TEST-1852
    [Tags]  Priority_High  TEST-1852
    Navigate To Page  ${page_name}
    Click on add user button
    Click On Cancel Button
    Log To Console And Report  Verify The Form Should Get Closed
    Verify The Form Should Get Closed

TEST-5322
    [Documentation]  Test that Clicking "Create" Button after filling required fields should create a new user
    ...  Reference : https://jts.seagate.com/browse/TEST-5322
    [Tags]  Priority_High  Smoke_test  TEST-5322
    Navigate To Page  ${page_name}
    ${new_user_name}=  Generate New User Name
    Create New CSM User  ${new_user_name}
    Click On Confirm Button
    Verify New User  ${new_user_name}
    Delete CSM User  ${new_user_name}

TEST-1851
    [Documentation]  Test that only valid user name must get added while adding username on the User Settings
    ...  Reference : https://jts.seagate.com/browse/TEST-1851
    [Tags]  Priority_High  TEST-1851
    Navigate To Page  ${page_name}
    Click On Add User Button
    Verify Only Valid User Allowed For Username

TEST-1853
    [Documentation]  Test that "Create" Button must remain disabled until required fields not filled on the User Settings
    ...  Reference : https://jts.seagate.com/browse/TEST-1853
    [Tags]  Priority_High  TEST-1853
    Navigate To Page  ${page_name}
    Click On Add User Button
    Verify Create Button Must Remain disabled

TEST-1854
    [Documentation]  Test that "Password" and "confirm password" field must remain hidden while adding password to user on the User Settings
    ...  Reference : https://jts.seagate.com/browse/TEST-1854
    [Tags]  Priority_High  TEST-1854
    Navigate To Page  ${page_name}
    Click On Add User Button
    Verify Passwords Remain Hidden

TEST-1863
    [Documentation]  Test that error message should show in case of mismatch of "Password" and "confirm password" while adding user on the User Settings
    ...  Reference : https://jts.seagate.com/browse/TEST-1863
    [Tags]  Priority_High  TEST-1863
    Navigate To Page  ${page_name}
    Click On Add User Button
    Verify Mismatch Password Error

TEST-1842
    [Documentation]  Test that root user must present when user navigate to manage page
    ...  Reference : https://jts.seagate.com/browse/TEST-1842
    [Tags]  Priority_High  TEST-1842
    Navigate To Page  ${page_name}
    Verify New User  ${username}

TEST-1864
    [Documentation]  Test that an error message should show in case password does not follow proper guideline
    ...  Reference : https://jts.seagate.com/browse/TEST-1864
    [Tags]  Priority_High  TEST-1864
    Navigate To Page  ${page_name}
    Click On Add User Button
    Verify Only Valid Password Get Added

TEST-7396
    [Documentation]  Test that Root user should able to change other users password without specifying old_password through csm GUI
    ...  Reference : https://jts.seagate.com/browse/TEST-7396
    [Tags]  Priority_High  TEST-7396
    ${new_password}=  Generate New Password
    ${users_type}=  Create List  manage  monitor
    Navigate To Page  ${page_name}
    FOR    ${value}    IN    @{users_type}
        ${new_user_name}=  Generate New User Name
        Create New CSM User  ${new_user_name}  ${new_password}  ${value}
        Log To Console And Report  operation for ${value}
        Click On Confirm Button
        Verify New User  ${new_user_name}
        ${new_password}=  Generate New Password
        Edit CSM User Password  ${new_user_name}  ${new_password}
        Re-login  ${new_user_name}  ${new_password}  ${page_name}
        Validate CSM Login Success  ${new_user_name}
        Re-login  ${username}  ${password}  ${page_name}
        Delete CSM User  ${new_user_name}
    END

TEST-7393
    [Documentation]  Test that root user should able to modify self password through csm GUI
    ...  Reference : https://jts.seagate.com/browse/TEST-7393
    [Tags]  Priority_High  TEST-7393
    ${new_password}=  Generate New Password
    Navigate To Page  ${page_name}
    Edit CSM User Password  ${username}  ${new_password}  ${password}
    Re-login  ${username}  ${new_password}  ${page_name}
    Edit CSM User Password  ${username}  ${password}  ${new_password}

TEST-5325
    [Documentation]  Test that user should able to edit after create a new user on the User Settings.
    ...  Reference : https://jts.seagate.com/browse/TEST-5325
    [Tags]  Priority_High  Smoke_test  TEST-5325
    ${new_password}=  Generate New Password
    Navigate To Page  ${page_name}
    ${new_user_name}=  Generate New User Name
    Create New CSM User  ${new_user_name}  ${new_password}  manage
    Click On Confirm Button
    Verify New User  ${new_user_name}
    ${new_password}=  Generate New Password
    Edit CSM User Password  ${new_user_name}  ${new_password}
    Edit CSM User Type  ${new_user_name}  monitor
    Re-login  ${new_user_name}  ${new_password}  ${page_name}
    Validate CSM Login Success  ${new_user_name}
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_user_name}

TEST-5323
    [Documentation]  Test that User should able to delete after create a new user on the User Settings
    ...  Reference : https://jts.seagate.com/browse/TEST-5323
    [Tags]  Priority_High  Smoke_test  TEST-5323
    ${new_password}=  Generate New Password
    Navigate To Page  ${page_name}
    ${new_user_name}=  Generate New User Name
    Create New CSM User  ${new_user_name}  ${new_password}
    Click On Confirm Button
    Verify New User  ${new_user_name}
    Delete CSM User  ${new_user_name}
    Verify Deleted User  ${new_user_name}

TEST-1865
    [Documentation]  Test that user should select roles from manage and monitor on the User Settings
    ...  Reference : https://jts.seagate.com/browse/TEST-1865
    [Tags]  Priority_High  TEST-1865
    ${new_password}=  Generate New Password
    ${users_type}=  Create List  manage  monitor
    Navigate To Page  ${page_name}
    FOR    ${value}    IN    @{users_type}
        ${new_user_name}=  Generate New User Name
        Create New CSM User  ${new_user_name}  ${new_password}  ${value}
        Log To Console And Report  operation for ${value}
        Click On Confirm Button
        Verify New User  ${new_user_name}
        Delete CSM User  ${new_user_name}
    END

TEST-5327
    [Documentation]  Test that pagination bar must present on the manage user page
    ...  Reference : https://jts.seagate.com/browse/TEST-1865
    [Tags]  Priority_High  TEST-5327
    Navigate To Page  ${page_name}
    Verify Presence of Pagination

TEST-5328
    [Documentation]  Test that pagination bar must have 5/10/15/All rows per page option
    ...  Reference : https://jts.seagate.com/browse/TEST-5328
    [Tags]  Priority_High  TEST-5328
    Navigate To Page  ${page_name}
    ${fetched_values}=  Read Pagination Options
    ${actual_values}=  Create List  5  10  15  All
    Lists Should Be Equal  ${fetched_values}  ${actual_values}

TEST-3583
    [Documentation]  Test that csm user is able to login to CSM UI via manage and monitor user
    ...  Reference : https://jts.seagate.com/browse/TEST-3583
    [Tags]  Priority_High  TEST-3583
    ${new_password}=  Generate New Password
    ${users_type}=  Create List  manage  monitor
    Navigate To Page  ${page_name}
    FOR    ${value}    IN    @{users_type}
        ${new_user_name}=  Generate New User Name
        Create New CSM User  ${new_user_name}  ${new_password}  ${value}
        Log To Console And Report  operation for ${value}
        Click On Confirm Button
        Verify New User  ${new_user_name}
        Re-login  ${new_user_name}  ${new_password}  ${page_name}
        Validate CSM Login Success  ${new_user_name}
        Re-login  ${username}  ${password}  ${page_name}
        Delete CSM User  ${new_user_name}
    END

TEST-5186
    [Documentation]  Test that root user is not getting deleted from the system
    ...  Reference : https://jts.seagate.com/browse/TEST-5186
    [Tags]  Priority_High  TEST-5186
    Navigate To Page  ${page_name}
    Verify Admin User Should Not Contain Delete Icon  ${username}

TEST-5229
    [Documentation]  Test that csm user should not able to visualize the iam user created
    ...  Reference : https://jts.seagate.com/browse/TEST-5229
    [Tags]  Priority_High  TEST-5229
    Verify IAM User Section Not Present

TEST-6338
    [Documentation]  Test that on 'Create Local User' form, role section should never be empty
    ...  Reference : https://jts.seagate.com/browse/TEST-6338
    [Tags]  Priority_High  TEST-6338
    Navigate To Page  ${page_name}
    ${value}=  Fetch Radio Button Value
    Should Not Be Empty  ${value}
    Should be equal  ${value}  manage

TEST-1214
    [Documentation]  Test that CSM user with admin role can view, add, or edit Settings
    ...  Reference : https://jts.seagate.com/browse/TEST-1214
    [Tags]  Priority_High  user_role  TEST-1214
    Verify that CSM Admin can access Setting menu

TEST-5389
    [Documentation]  Test that CSM user with admin role can view, add, or edit Settings
    ...  Reference : https://jts.seagate.com/browse/TEST-5389
    [Tags]  Priority_High  user_role  TEST-5389
    Navigate To Page  SETTINGS_ID
    wait for page or element to load
    Verify Setting menu item
    Verify Setting menu navigating

TEST-18326
    [Documentation]  Test that csm Admin user is able to reset the s3 account users password through CSM GUI
    ...  Reference : https://jts.seagate.com/browse/TEST-18326
    [Tags]  Priority_High  TEST-18326  S3_test  Smoke_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    ${S3_account_name}  ${email}  ${S3_password} =  Create S3 account
    wait for page or element to load
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    ${S3_new_password}=  Generate New Password
    Edit S3 User Password  ${S3_account_name}  ${S3_new_password}  ${S3_new_password}
    Re-login  ${S3_account_name}  ${S3_new_password}  S3_ACCOUNTS_TAB_ID
    Delete S3 Account  ${S3_account_name}  ${S3_new_password}  True

TEST-4871
    [Documentation]  Test that SSl certificate get uploaded on SSl certificate upload page	
    ...  Reference : https://jts.seagate.com/browse/TEST-4871
    [Tags]  Priority_High  CFT_Test  TEST-4871
    ${test_id}    Set Variable    TEST-4871
    ${installation_status_init} =  Format String  not_installed
    Navigate To Page  SETTINGS_ID  SETTINGS_SSL_BUTTON_ID
    wait for page or element to load
    SSL Upload  ${Download_File_Path}  ${server_file_name}
    Verify SSL status  ${installation_status_init}  ${server_file_name}
    Capture Page Screenshot  ${test_id}_ssl_uploaded.png

TEST-9045
    [Documentation]  Test that user should able to see latest changes on settings page : SSL certificate
    ...  Reference : https://jts.seagate.com/browse/TEST-9045
    [Tags]  Priority_High  CFT_Test  TEST-9045
    ${test_id}    Set Variable    TEST-9045
    ${installation_status_init} =  Format String  not_installed
    ${installation_status_success} =  Format String  installation_successful
    Navigate To Page  SETTINGS_ID  SETTINGS_SSL_BUTTON_ID
    wait for page or element to load  3s
    SSL Upload  ${Download_File_Path}  ${server_file_name}
    Verify SSL status  ${installation_status_init}  ${server_file_name} 
    Capture Page Screenshot  ${test_id}_ssl_uploaded.png
    Install uploaded SSL
    wait for page or element to load  5 minutes  #will re-start all service
    Close Browser
    CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
    wait for page or element to load  20s  # Took time to load dashboard after install
    Reload Page
    wait for page or element to load  10s  # Took time to load dashboard after install
    Verify SSL status  ${installation_status_success}  ${server_file_name}
    Capture Page Screenshot  ${test_id}_ssl_installed.png

TEST-11152
    [Documentation]  Test that IEM alerts should be generated for number of days mentioned in /etc/csm/csm.conf prior to SSL certificate expiration
    ...  Reference : https://jts.seagate.com/browse/TEST-11152
    [Tags]  Priority_High  CFT_Test  TEST-11152
    SSL certificate expiration alert Verification  0
    SSL certificate expiration alert Verification  1
    SSL certificate expiration alert Verification  5
    SSL certificate expiration alert Verification  30

TEST-18330
    [Documentation]  Test that reset password for s3 account does not accept invalid password
    ...  Reference : https://jts.seagate.com/browse/TEST-18330
    [Tags]  Priority_High  TEST-18330  S3_test  Smoke_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    ${S3_account_name}  ${email}  ${S3_password} =  Create S3 account
    wait for page or element to load
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    Verify Invalid Password Not Accepted By Edit S3 Account
    CSM GUI Logout
    Enter Username And Password  ${S3_account_name}  ${S3_password}
    Click Sigin Button
    wait for page or element to load
    Delete S3 Account  ${S3_account_name}  ${S3_password}  True

TEST-18332
    [Documentation]  Test that confirm rest password button remains
    ...  disabled for password and confirm password does not match.
    ...  Reference : https://jts.seagate.com/browse/TEST-18332
    [Tags]  Priority_High  TEST-18332  S3_test  Smoke_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    ${S3_account_name}  ${email}  ${S3_password} =  Create S3 account
    wait for page or element to load
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    Verify Mismatch Password Error For Edit S3account
    CSM GUI Logout
    Enter Username And Password  ${S3_account_name}  ${S3_password}
    Click Sigin Button
    wait for page or element to load
    Delete S3 Account  ${S3_account_name}  ${S3_password}  True

TEST-21589
    [Documentation]  Test that CSM Admin user can delete empty s3 account
    ...  Reference : https://jts.seagate.com/browse/TEST-21589
    [Tags]  Priority_High  TEST-21589  S3_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    ${S3_account_name}  ${email}  ${S3_password} =  Create S3 account
    wait for page or element to load
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    Delete s3 account using csm user  ${S3_account_name}

TEST-21590
    [Documentation]  Test that CSM Admin user cannot delete non-empty s3 account
    ...  Reference : https://jts.seagate.com/browse/TEST-21590
    [Tags]  Priority_High  TEST-21590  S3_test
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
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
    Re-login  ${username}  ${password}  MANAGE_MENU_ID
    wait for page or element to load
    Navigate To Page    MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    Verify Error Msg is Shown For Non Empty S3account delete  ${S3_account_name}
    wait for page or element to load
    Re-login  ${S3_account_name}  ${S3_password}  MANAGE_MENU_ID
    Navigate To Page  S3_BUCKET_TAB_ID
    Delete Bucket  ${bucketname}
    Delete S3 Account  ${S3_account_name}  ${password}  True

TEST-23042
    [Documentation]  Test that admin user should able to create users with admin role from csm UI.
    ...  Reference : https://jts.seagate.com/browse/TEST-23042
    [Tags]  Priority_High  Smoke_test  TEST-23042
    ${new_password}=  Generate New Password
    Navigate To Page  ${page_name}
    ${new_user_name}=  Generate New User Name
    Create New CSM User  ${new_user_name}  ${new_password}  admin
    Click On Confirm Button
    Verify New User  ${new_user_name}
    Delete CSM User  ${new_user_name}

TEST-23047
    [Documentation]  Test that admin user should able to delete users with admin role from csm UI.
    ...  Reference : https://jts.seagate.com/browse/TEST-23047
    [Tags]  Priority_High  Smoke_test  TEST-23047
    ${new_password}=  Generate New Password
    Navigate To Page  ${page_name}
    ${new_user_name}=  Generate New User Name
    Create New CSM User  ${new_user_name}  ${new_password}  admin
    Click On Confirm Button
    Delete CSM User  ${new_user_name}
    Verify Deleted User  ${new_user_name}

TEST-23608
    [Documentation]  Test that User should able to search username, role from search icon.
    ...  Reference : https://jts.seagate.com/browse/TEST-23608
    [Tags]  Priority_High  Smoke_test  TEST-23608
    ${new_password}=  Generate New Password
    Navigate To Page  ${page_name}
    ${new_user_name}=  Generate New User Name
    Create New CSM User  ${new_user_name}  ${new_password}  admin
    Click On Confirm Button
    Search username and role  ${new_user_name}
    Verify New User  ${new_user_name} 
    Delete CSM User  ${new_user_name}
    Verify Deleted User  ${new_user_name}

TEST-23612
    [Documentation]  Test that user should able to filter the search operation.
    ...  Reference : https://jts.seagate.com/browse/TEST-23612
    [Tags]  Priority_High  Smoke_test  TEST-23612
    ${new_password}=  Generate New Password
    Navigate To Page  ${page_name}
    ${new_user_name}=  Generate New User Name
    Create New CSM User  ${new_user_name}  ${new_password}  admin
    Click On Confirm Button
    Select from filter  role
    Search username and role  admin
    Verify New User  ${new_user_name}
    Reload Page
    wait for page or element to load
    Select from filter  username
    Search username and role  ${new_user_name}
    Verify New User  ${new_user_name} 
    Reload Page
    wait for page or element to load
    Delete CSM User  ${new_user_name}
    Verify Deleted User  ${new_user_name}

TEST-11153
    [Documentation]  CSM GUI: Test that appropriate IEM alert is generated after SSL certificate has expired
    ...  Reference : https://jts.seagate.com/browse/TEST-11153
    [Tags]  full    TEST-11153
    SSL certificate expiration alert Verification  0

TEST-23050
    [Documentation]  Test that admin user should not able to delete all users with admin role from csm UI
    ...  Reference : https://jts.seagate.com/browse/TEST-23050
    [Tags]  full    TEST-23050
    Navigate To Page  ${page_name}
    FOR  ${index}  IN RANGE  3
        ${new_password}=  Generate New Password
        ${new_user_name}=  Generate New User Name
        Create New CSM User  ${new_user_name}  ${new_password}  admin
        Click On Confirm Button
    END
    Verify Action Enabled On The Table Element  ${CSM_USER_EDIT_XPATH}  ${username}
    ${admin_users}=  Read Selective Table Data  ${CSM_TABLE_COLUMN_XPATH}  admin  ${CSM_ROLE_COLUMN}  ${CSM_USERNAME_COLUMN}
    Log To Console And Report  ${admin_users}
    Remove Values From List  ${admin_users}  ${username}
    Log To Console And Report  ${admin_users}
    FOR  ${user}  IN  @{admin_users}
        Delete CSM User  ${user}
    END
    Verify Delete Action Disabled On The Table Element  ${username}

TEST-23872
    [Documentation]  Test verify default number of rows to be displayed per page in administrative users CSM UI page
    ...  Reference : https://jts.seagate.com/browse/TEST-23872
    [Tags]  Priority_High  TEST-23872
    Navigate To Page  ${page_name}
    wait for page or element to load
    ${text}=  get text  ${CSM_TABLE_DROPDOWN_XPATH}
    Should Be Equal  "${text}"  "${CSM_DROPDOWN_VALUE}"

TEST-23837
    [Documentation]  Test that any user with any role should be able to delete themselves except monitor role user.
    ...  Reference : https://jts.seagate.com/browse/TEST-23837
    [Tags]  Priority_High  TEST-23837
    Navigate To Page  ${page_name}
    wait for page or element to load
    ${new_password}=  Generate New Password
    ${new_user_name}=  Generate New User Name
    Create New CSM User  ${new_user_name}  ${new_password}  admin
    Click on confirm button
    ${new_password1}=  Generate New Password
    ${new_user_name1}=  Generate New User Name
    Create New CSM User  ${new_user_name1}  ${new_password1}  manage
    Click on confirm button
    ${new_csm_user_password}=  Generate New Password
    ${new_csm_user_name}=  Generate New User Name
    Create New CSM User  ${new_csm_user_name}  ${new_csm_user_password}  monitor
    Click on confirm button
    Re-login  ${new_user_name}  ${new_password}  ${page_name}
    Delete Logged In CSM User  ${new_user_name}
    Re-login  ${new_user_name1}  ${new_password1}  ${page_name}
    Delete Logged In CSM User  ${new_user_name1}
    Re-login  ${new_csm_user_name}  ${new_csm_user_password}  ${page_name}
    Verify Delete Action Disabled On The Table Element  ${new_csm_user_name}
    Re-login  ${username}  ${password}  ${page_name}
    Delete CSM User  ${new_csm_user_name}
    Verify Deleted User  {new_csm_user_name}
    Verify Deleted User  {new_user_name1}
    Verify Deleted User  {new_user_name}

TEST-23859
    [Documentation]  Test user should be able to select number of rows to be displayed per page in administrative users CSM UI page
    ...  Reference : https://jts.seagate.com/browse/TEST-23859
    [Tags]  Priority_High  TEST-23859
    Navigate To Page  ${page_name}
    ${fetched_values}=  Read Pagination Options
    ${actual_values}=  Create List  5 rows  10 rows  20 rows  30 rows  50 rows  100 rows  150 rows  200 rows
    Lists Should Be Equal  ${fetched_values}  ${actual_values}

TEST-23502
    [Documentation]  Test that admin user should able to reset other users role from csm UI
    ...  Reference : https://jts.seagate.com/browse/TEST-23502
    [Tags]  Priority_High  TEST-23502
    Navigate To Page  ${page_name}
    FOR   ${cur_role}  IN   admin  manage  monitor
        Create account with input Role and Change Role from Admin account  ${cur_role}
    END

TEST-23051
    [Documentation]  Test that admin user should able to reset other uses password with admin role from csm UI
    ...  Reference : https://jts.seagate.com/browse/TEST-23051
    [Tags]  Priority_High  TEST-23051
    Navigate To Page  ${page_name}
    ${new_password}=  Generate New Password
    ${new_user_name}=  Generate New User Name
    Log To Console And Report  Create Account with role: admin
    Create New CSM User  ${new_user_name}  ${new_password}  admin
    Click On Confirm Button
    Verify New User  ${new_user_name}
    ${change_password}=  Generate New Password
    Edit CSM User Password  ${new_user_name}  ${change_password}
    Re-login  ${new_user_name}  ${change_password}  MANAGE_MENU_ID
    Re-login  ${user_name}  ${password}  MANAGE_MENU_ID
    Delete CSM User  ${new_user_name}

TEST-23500
    [Documentation]  Test that admin user should not able to reset own role from csm UI
    ...  Reference : https://jts.seagate.com/browse/TEST-23500
    [Tags]  Priority_High  TEST-23500
    Navigate To Page  ${page_name}
    Verify Change User Type Radio Button Disabled  ${username}

