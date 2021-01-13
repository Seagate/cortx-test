*** Settings ***
Documentation    This suite verifies the testcases for csm user creation
Resource    ../../../resources/page_objects/loginPage.robot
Resource    ../../../resources/page_objects/userSettingsLocalPage.robot

Suite Teardown  Close All Browsers
Force Tags  CSM_GUI  CSM_USER

*** Variables ***
${url}  https://10.230.246.58:28100/#/
${browser}  chrome
${headless}  True
${navigate_to_subpage}  False
${Sub_tab}  None
${page name}  MANAGE_MENU_ID
${username}
${password}

*** Test Cases ***
TEST-5326
    [Documentation]  Test that "Add new user" should open a form to create new user on the User Settings
    ...  Reference : https://jts.seagate.com/browse/TEST-5326
    [Tags]  Priority_High
    [Setup]   CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
    Sleep  1s
    Navigate To Page  ${page name}
    Click on add user button
    Log To Console And Report  Verifying the Form To Create CSM Users
    Verify A Form Got Open To Create CSM Users
    [Teardown]  Close Browser

TEST-1852
    [Documentation]  Test that by clicking on the "cancel" it should close the form without creating new user on the User Settings
    ...  Reference : https://jts.seagate.com/browse/TEST-1852
    [Tags]  Priority_High
    [Setup]   CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
    Sleep  1s
    Navigate To Page  ${page name}
    Click on add user button
    Click On Cancel Button
    Log To Console And Report  Verify The Form Should Get Closed
    Verify The Form Should Get Closed
    [Teardown]  Close Browser

TEST-5322
    [Documentation]  Test that Clicking "Create" Button after filling required fields should create a new user
    ...  Reference : https://jts.seagate.com/browse/TEST-5322
    [Tags]  Priority_High
    [Setup]   CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
    Navigate To Page  ${page name}
    ${new_user_name}=  Generate New User Name
    Create New CSM User  ${new_user_name}
    Click On Confirm Button
    Verify New User  ${new_user_name}
    Delete CSM User  ${new_user_name}
    [Teardown]  Close Browser

TEST-1851
    [Documentation]  Test that only valid user name must get added while adding username on the User Settings
    ...  Reference : https://jts.seagate.com/browse/TEST-1851
    [Tags]  Priority_High
    [Setup]   CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
    Navigate To Page  ${page name}
    Click On Add User Button
    Verify Only Valid User Allowed For Username
    [Teardown]  Close Browser

TEST-1853
    [Documentation]  Test that "Create" Button must remain disabled until required fields not filled on the User Settings
    ...  Reference : https://jts.seagate.com/browse/TEST-1853
    [Tags]  Priority_High
    [Setup]   CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
    Navigate To Page  ${page name}
    Click On Add User Button
    Verify Create Button Must Remain disbaled
    [Teardown]  Close Browser

TEST-1854
    [Documentation]  Test that "Password" and "confirm password" field must remain hidden while adding password to user on the User Settings
    ...  Reference : https://jts.seagate.com/browse/TEST-1854
    [Tags]  Priority_High
    [Setup]   CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
    Navigate To Page  ${page name}
    Click On Add User Button
    Verify Passwords Remain Hidden
    [Teardown]  Close Browser

TEST-1863
    [Documentation]  Test that error message should show in case of mismatch of "Password" and "confirm password" while adding user on the User Settings
    ...  Reference : https://jts.seagate.com/browse/TEST-1863
    [Tags]  Priority_High
    [Setup]   CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
    Navigate To Page  ${page name}
    Click On Add User Button
    Verify Missmatch Password Error
    [Teardown]  Close Browser
