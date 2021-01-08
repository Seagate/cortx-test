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

*** Variables ***
${url}  https://10.230.246.58:28100/#/
${browser}  chrome
${headless}  True
${navigate_to_subpage}  False
${Sub_tab}  None

*** Test Cases ***

Check S3 Account Exists
    [Documentation]  This test is to verify that S3 account existes
    [Tags]  Priority_High
    [Setup]   CSM GUI Login  ${url}  ${browser}  ${headless}  ${csm admin user}  ${csm admin password}
    Validate CSM Login Success  ${csm admin user}
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    Check S3 Account Exists     ${S3_ACCOUNTS_TABLE_XPATH}  ${S3_ACCOUNT}
    [Teardown]  Close Browser

Test action on table
    [Documentation]  This test case is to verify that user can perform the actions on the table ements.
    [Tags]  Priority_High
    [Setup]   CSM GUI Login  ${url}  ${browser}  ${headless}  ${csm admin user}  ${csm admin password}
    Validate CSM Login Success  ${csm admin user}
    Navigate To Page    MANAGE_MENU_ID
    sleep  2s
    Action on the table     ${CSM_USER}  CSM_USER_EDIT_XPATH
    [Teardown]  Close Browser
