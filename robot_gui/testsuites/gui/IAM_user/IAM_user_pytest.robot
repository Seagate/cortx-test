*** Settings ***
Documentation    This suite verifies the testcases for csm login
Library     SeleniumLibrary
Resource    ${RESOURCES}/resources/page_objects/IAM_UsersPage.robot
Resource    ${RESOURCES}/resources/page_objects/loginPage.robot
Variables   ${RESOURCES}/resources/common/common_variables.py

*** Variables ***
${url}
${browser}  chrome
${headless}  True
${username}
${password}

*** Test Cases ***

CREATE_LAST_IAM_USER_VERIFY_POPUP
    [Documentation]  This key word is for verifying error popup after creating more than limit of IAM users
    [Tags]  PYTEST  CREATE_LAST_IAM_USER_VERIFY_POPUP
    CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
    Navigate To Page   S3_IAM_USER_TAB_ID
    wait for page or element to load  3s
    ${username}=  Generate New User Name
    ${password}=  Generate New Password
    Click Create IAM User Button
    sleep  1s
    Create IAMuser  ${username}  ${password}  True
    wait until element is visible  ${IAM_USER_LIMIT_MSG_ID}  timeout=30
    Capture Page Screenshot
    ${err_msg}=  get text  ${IAM_USER_LIMIT_MSG_ID}
    Log To Console And Report  ${err_msg}
    Should be Equal  ${IAM_USER_LIMIT_ERROR_MSG}  ${err_msg}
