*** Settings ***
Documentation    This suite verifies the testcases for create bucket
Library     SeleniumLibrary
Resource    ../../../resources/page_objects/loginPage.robot
Resource    ../../../resources/page_objects/s3accountPage.robot
Resource    ../../../resources/page_objects/IAM_UsersPage.robot
Resource    ../../../resources/page_objects/bucket_page.robot
Variables   ../../../resources/common/common_variables.py


Suite Teardown  Close All Browsers
Force Tags  CSM_GUI  CSM_BUCKET_CREATE
Test Setup  Login To S3 Account
Test Teardown  Delete S3 Account And Close Browser

*** Variables ***
${url}
${browser}  chrome
${headless}  True
${navigate_to_subpage}  False
${Sub_tab}  None
${username}
${password}
${S3_account_name}

*** Keywords ***

Login To S3 Account
    [Documentation]  This key word is for test case setup which create s3 account and login to it
    [Tags]  Priority_High  S3_test
    CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    sleep  3s
    Re-login  ${S3_account_name}  ${password}  MANAGE_MENU_ID
    Navigate To Page  MANAGE_MENU_ID  BUCKET_TAB_ID


Delete S3 Account And Close Browser
    [Documentation]  This key word is for test case teardown which delete s3 account and close browsers
    [Tags]  Priority_High  S3_test
    sleep  3s
    Navigate To Page  MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    ${S3_account_name}=  Fetch S3 Account Name
    Sleep  3s
    Delete S3 Account  ${S3_account_name}  ${password}  True
    Close Browser

*** Test Cases ***
TEST-939
   [Documentation]  Test that buckets is created
   [Tags]  Priority_High  Smoke_test
   Click On Create Bucket Form
   ${bucketname}=  Generate New User Name
   Create Bucket  ${bucketname}
   Delete Bucket  ${bucketname}