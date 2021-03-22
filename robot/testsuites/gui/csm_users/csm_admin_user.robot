*** Settings ***
Documentation    This suite verifies the testcases for csm user creation
Resource    ${EXECDIR}/resources/page_objects/loginPage.robot
Resource    ${EXECDIR}/resources/page_objects/userSettingsLocalPage.robot
Resource    ${EXECDIR}/resources/page_objects/preboardingPage.robot

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
    Verify Create Button Must Remain disbaled

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
    Verify Missmatch Password Error

TEST-1838
    [Documentation]  Test that monitor user can't able to delete any user
    ...  Reference : https://jts.seagate.com/browse/TEST-1838
    [Tags]  Priority_High
    ${new_user_name}=  Generate New User Name
    ${new_password}=  Generate New Password
    Navigate To Page  ${page name}
    #  Checking for manage
    Create New CSM User  ${new_user_name}  ${new_password}  monitor
    Click On Confirm Button
    Verify New User  ${new_user_name}
    Re-login  ${new_user_name}  ${new_password}  ${page name}
    Verify No Delete Button Present
    Re-login  ${username}  ${password}  ${page name}
    Delete CSM User  ${new_user_name}

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
    Verify Presence of Pagiantion

TEST-5328
    [Documentation]  Test that pagination bar must have 5/10/15/All rows per page option
    ...  Reference : https://jts.seagate.com/browse/TEST-5328
    [Tags]  Priority_High
    Navigate To Page  ${page name}
    ${fetched_values}=  Read Pagiantion Options
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
    [Documentation]  TTest that on 'Create Local User' form, role section should never be empty
    ...  Reference : https://jts.seagate.com/browse/TEST-6338
    [Tags]  Priority_High
    Navigate To Page  ${page name}
    ${value}=  Fetch Radio Button Value
    Should Not Be Empty  ${value}
    Should be equal  ${value}  manage
