*** Settings ***
Documentation    This suite verifies the testcases for csm user creation
Resource   ${EXECDIR}/resources/page_objects/loginPage.robot
Resource   ${EXECDIR}/resources/page_objects/s3accountPage.robot
Resource   ${EXECDIR}/resources/page_objects/settingsPage.robot
Resource   ${EXECDIR}/resources/page_objects/userSettingsLocalPage.robot
Resource   ${EXECDIR}/resources/page_objects/preboardingPage.robot

Suite Setup  run keywords   check csm admin user status  ${url}  ${browser}  ${headless}
...  ${username}  ${password}
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
${Download_File_Path}  \root\Downloads\
${server_file_name}  s3server.pem

*** Keywords ***

SSL certificate expiration alert Verification
    [Documentation]  This keyword is used to test SSL related alerts for  diffrent expiry days
    [Arguments]  ${days}
    Navigate To Page  SETTINGS_ID  SETTINGS_SSL_BUTTON_ID
    Sleep  20s
    ${installation_status_init} =  Format String  not_installed
    ${installation_status_success} =  Format String  installation_successful
    ${file_path}=  SSL Gennerate and Upload  ${days}  ${Download_File_Path}
    ${file_name}=  Set Variable  stx_${days}.pem
    Verify SSL status  ${installation_status_init}  ${file_name}
    # # These following lines should be executed in case you have the proper machine
    # Install uploaded SSL
    # Sleep  5 minutes  #will re-start all service
    # Close Browser
    # CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
    # Sleep  20s  # Took time to load dashboard after install
    # Reload Page
    # Sleep  10s  # Took time to load dashboard after install
    # Verify SSL status  ${installation_status_success}  ${file_name}
    ## TODO : find the alert and verifiy

*** Test Cases ***

TEST-5326
    [Documentation]  Test that "Add new user" should open a form to create new user on the User Settings
    ...  Reference : https://jts.seagate.com/browse/TEST-5326
    [Tags]  Priority_High
    Sleep  1s
    Navigate To Page  ${page name}
    Click on add user button
    Log To Console And Report  Verifying the Form To Create CSM Users
    Verify A Form Got Open To Create CSM Users

TEST-1852
    [Documentation]  Test that by clicking on the "cancel" it should close the form without creating new user on the User Settings
    ...  Reference : https://jts.seagate.com/browse/TEST-1852
    [Tags]  Priority_High
    Navigate To Page  ${page name}
    Click on add user button
    Click On Cancel Button
    Log To Console And Report  Verify The Form Should Get Closed
    Verify The Form Should Get Closed

TEST-5322
    [Documentation]  Test that Clicking "Create" Button after filling required fields should create a new user
    ...  Reference : https://jts.seagate.com/browse/TEST-5322
    [Tags]  Priority_High  Smoke_test
    Navigate To Page  ${page name}
    ${new_user_name}=  Generate New User Name
    Create New CSM User  ${new_user_name}
    Click On Confirm Button
    Verify New User  ${new_user_name}
    Delete CSM User  ${new_user_name}

TEST-1851
    [Documentation]  Test that only valid user name must get added while adding username on the User Settings
    ...  Reference : https://jts.seagate.com/browse/TEST-1851
    [Tags]  Priority_High
    Navigate To Page  ${page name}
    Click On Add User Button
    Verify Only Valid User Allowed For Username

TEST-1853
    [Documentation]  Test that "Create" Button must remain disabled until required fields not filled on the User Settings
    ...  Reference : https://jts.seagate.com/browse/TEST-1853
    [Tags]  Priority_High
    Navigate To Page  ${page name}
    Click On Add User Button
    Verify Create Button Must Remain disabled

TEST-1854
    [Documentation]  Test that "Password" and "confirm password" field must remain hidden while adding password to user on the User Settings
    ...  Reference : https://jts.seagate.com/browse/TEST-1854
    [Tags]  Priority_High
    Navigate To Page  ${page name}
    Click On Add User Button
    Verify Passwords Remain Hidden

TEST-1863
    [Documentation]  Test that error message should show in case of mismatch of "Password" and "confirm password" while adding user on the User Settings
    ...  Reference : https://jts.seagate.com/browse/TEST-1863
    [Tags]  Priority_High
    Navigate To Page  ${page name}
    Click On Add User Button
    Verify Mismatch Password Error

TEST-1842
    [Documentation]  Test that root user must present when user navigate to manage page
    ...  Reference : https://jts.seagate.com/browse/TEST-1842
    [Tags]  Priority_High
    Navigate To Page  ${page name}
    Verify New User  ${username}

TEST-1864
    [Documentation]  Test that an error message should show in case password does not follow proper guideline
    ...  Reference : https://jts.seagate.com/browse/TEST-1864
    [Tags]  Priority_High
    Navigate To Page  ${page name}
    Click On Add User Button
    Verify Only Valid Password Get Added

TEST-7396
    [Documentation]  Test that Root user should able to change other users password without specifying old_password through csm GUI
    ...  Reference : https://jts.seagate.com/browse/TEST-7396
    [Tags]  Priority_High
    ${new_password}=  Generate New Password
    ${users_type}=  Create List  manage  monitor
    Navigate To Page  ${page name}
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
    [Tags]  Priority_High
    ${new_password}=  Generate New Password
    Navigate To Page  ${page name}
    Edit CSM User Password  ${username}  ${new_password}  ${password}
    Re-login  ${username}  ${new_password}  ${page_name}
    Edit CSM User Password  ${username}  ${password}  ${new_password}

TEST-5325
    [Documentation]  Test that user should able to edit after create a new user on the User Settings.
    ...  Reference : https://jts.seagate.com/browse/TEST-5325
    [Tags]  Priority_High  Smoke_test
    ${new_password}=  Generate New Password
    Navigate To Page  ${page name}
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
    [Tags]  Priority_High  Smoke_test
    ${new_password}=  Generate New Password
    Navigate To Page  ${page name}
    ${new_user_name}=  Generate New User Name
    Create New CSM User  ${new_user_name}  ${new_password}
    Click On Confirm Button
    Verify New User  ${new_user_name}
    Delete CSM User  ${new_user_name}
    Verify Deleted User  ${new_user_name}

TEST-1865
    [Documentation]  Test that user should select roles from manage and monitor on the User Settings
    ...  Reference : https://jts.seagate.com/browse/TEST-1865
    [Tags]  Priority_High
    ${new_password}=  Generate New Password
    ${users_type}=  Create List  manage  monitor
    Navigate To Page  ${page name}
    FOR    ${value}    IN    @{users_type}
        Create New CSM User  ${value}  ${new_password}  ${value}
        Log To Console And Report  operation for ${value}
        Click On Confirm Button
        Verify New User  ${value}
        Delete CSM User  ${value}
    END

TEST-5327
    [Documentation]  Test that pagination bar must present on the manage user page
    ...  Reference : https://jts.seagate.com/browse/TEST-1865
    [Tags]  Priority_High
    Navigate To Page  ${page name}
    Verify Presence of Pagination

TEST-5328
    [Documentation]  Test that pagination bar must have 5/10/15/All rows per page option
    ...  Reference : https://jts.seagate.com/browse/TEST-5328
    [Tags]  Priority_High
    Navigate To Page  ${page name}
    ${fetched_values}=  Read Pagination Options
    ${actual_values}=  Create List  5  10  15  All
    Lists Should Be Equal  ${fetched_values}  ${actual_values}

TEST-3583
    [Documentation]  Test that csm user is able to login to CSM UI via manage and monitor user
    ...  Reference : https://jts.seagate.com/browse/TEST-3583
    [Tags]  Priority_High
    ${new_password}=  Generate New Password
    ${users_type}=  Create List  manage  monitor
    Navigate To Page  ${page name}
    FOR    ${value}    IN    @{users_type}
        Create New CSM User  ${value}  ${new_password}  ${value}
        Log To Console And Report  operation for ${value}
        Click On Confirm Button
        Verify New User  ${value}
        Re-login  ${value}  ${new_password}  ${page_name}
        Validate CSM Login Success  ${value}
        Re-login  ${username}  ${password}  ${page_name}
        Delete CSM User  ${value}
    END

TEST-7406
    [Documentation]  Test that Non root user cannot change roles through csm GUI
    ...  Reference : https://jts.seagate.com/browse/TEST-7406
    [Tags]  Priority_High
    ${new_password}=  Generate New Password
    ${new_user_name}=  Generate New User Name
    ${users_type}=  Create List  manage  monitor
    Navigate To Page  ${page name}
    FOR    ${value}    IN    @{users_type}
        Create New CSM User  ${new_user_name}  ${new_password}  ${value}
        Log To Console And Report  operation for ${value}
        Click On Confirm Button
        Verify New User  ${new_user_name}
        Re-login  ${new_user_name}  ${new_password}  ${page_name}
        Validate CSM Login Success  ${new_user_name}
        Verify Change User Type Radio Button Disabled  ${new_user_name}
        Re-login  ${username}  ${password}  ${page_name}
        Delete CSM User  ${new_user_name}
    END

TEST-5186
    [Documentation]  Test that root user is not getting deleted from the system
    ...  Reference : https://jts.seagate.com/browse/TEST-5186
    [Tags]  Priority_High
    Navigate To Page  ${page name}
    Verify Admin User Should Not Contain Delete Icon  ${username}

TEST-5229
    [Documentation]  Test that csm user should not able to visualize the iam user created
    ...  Reference : https://jts.seagate.com/browse/TEST-5229
    [Tags]  Priority_High
    Verify IAM User Section Not Present

TEST-6338
    [Documentation]  Test that on 'Create Local User' form, role section should never be empty
    ...  Reference : https://jts.seagate.com/browse/TEST-6338
    [Tags]  Priority_High
    Navigate To Page  ${page name}
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
    Sleep  5s
    Verify Setting menu item
    Verify Setting menu navigating

TEST-18326
    [Documentation]  Test that csm Admin user is able to reset the s3 account users password through CSM GUI
    ...  Reference : https://jts.seagate.com/browse/TEST-18326
    [Tags]  Priority_High  TEST-18326  S3_test  Smoke_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${S3_password} =  Create S3 account
    sleep  5s
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    CSM GUI Logout
    Enter Username And Password  ${S3_account_name}  ${S3_password}
    Click Sigin Button
    sleep  2s
    Validate CSM Login Success  ${s3_account_name}
    CSM GUI Logout
    wait for page or element to load  2s
    Enter Username And Password  ${username}  ${password}
    Click Sigin Button
    wait for page or element to load  2s
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    ${S3_new_password}=  Generate New Password
    Edit S3 User Password  ${S3_account_name}  ${S3_new_password}  ${S3_new_password}
    Delete S3 Account  ${S3_account_name}  ${S3_new_password}  True

TEST-4871
    [Documentation]  Test that SSl certificate get uploaded on SSl certificate upload page	
    ...  Reference : https://jts.seagate.com/browse/TEST-4871
    [Tags]  Priority_High  CFT_Test  TEST-4871
    ${installation_status_init} =  Format String  not_installed
    Navigate To Page  SETTINGS_ID  SETTINGS_SSL_BUTTON_ID
    Sleep  3s
    SSL Upload  ${Download_File_Path}  ${server_file_name}
    Verify SSL status  ${installation_status_init}  ${server_file_name}

TEST-9045
    [Documentation]  Test that user should able to see latest changes on settings page : SSL certificate
    ...  Reference : https://jts.seagate.com/browse/TEST-9045
    [Tags]  Priority_High  CFT_Test  TEST-9045
    ${installation_status_init} =  Format String  not_installed
    ${installation_status_success} =  Format String  installation_successful
    Navigate To Page  SETTINGS_ID  SETTINGS_SSL_BUTTON_ID
    Sleep  3s
    SSL Upload  ${Download_File_Path}  ${server_file_name}
    Verify SSL status  ${installation_status_init}  ${server_file_name} 
    # # These following lines should be executed in case you have the proper machine
    # Install uploaded SSL
    # Sleep  5 minutes  #will re-start all service
    # Close Browser
    # CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
    # Sleep  20s  # Took time to load dashboard after install
    # Reload Page
    # Sleep  10s  # Took time to load dashboard after install
    # Verify SSL status  ${installation_status_success}  ${server_file_name}

TEST-11152
    [Documentation]  Test that IEM alerts should be generated for number of days mentioned in /etc/csm/csm.conf prior to SSL certificate expiration
    ...  Reference : https://jts.seagate.com/browse/TEST-9045
    [Tags]  Priority_High  CFT_Test  TEST-11152
    SSL certificate expiration alert Verification  30
    SSL certificate expiration alert Verification  5
    SSL certificate expiration alert Verification  1