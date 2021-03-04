*** Settings ***
Documentation    This suite verifies the testcases for ssl details
Resource    ../../../resources/page_objects/loginPage.robot
Resource    ../../../resources/page_objects/s3accountPage.robot
Resource    ../../../resources/page_objects/userRollPage.robot
Resource    ../../../resources/page_objects/IAM_UsersPage.robot
Resource    ../../../resources/page_objects/bucket_page.robot
Resource   ../../../resources/common/common.robot
Variables  ../../../resources/common/element_locators.py
Variables  ../../../resources/common/common_variables.py


Suite Teardown  Close All Browsers
Force Tags  CSM_GUI  user_roll 

Test Setup  CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
Test Teardown  Close Browser

*** Variables ***
${browser}  chrome
${headless}  True
${navigate_to_subpage}  False
${Sub_tab}  None
${username}
${password}
${invalid_S3_account_name}  xyz$#%1
${invalid_S3_email_id}  xyz@test
${invalid_S3_account_password}  TestPass


*** Test Cases ***

TEST-5268
    [Documentation]  Test S3 account user should only be able to see S3 account details of the accounts which are associated with its account
    [Tags]  Priority_High  Smoke_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    Re-login   ${S3_account_name}  ${password}  MANAGE_MENU_ID
    sleep  5s
    Check Associated S3 Account Exists  ${S3_account_name}  ${email} 
    Delete S3 Account  ${S3_account_name}  ${password}  True

TEST-1042
    [Documentation]  Test that setting option not available for s3 user
    [Tags]  Priority_High  Smoke_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    Re-login   ${S3_account_name}  ${password}  MANAGE_MENU_ID
    Check Setting Option Not Exists
    Delete S3 Account  ${S3_account_name}  ${password}  True

EST-6454
    [Documentation]  Test Alert icon should not be visible to s3 account user Verify Alert icon should not be visible to s3 account user
    [Tags]  Priority_High  Smoke_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    Re-login   ${S3_account_name}  ${password}  MANAGE_MENU_ID
    Check Alert Icon Not Exists
    Delete S3 Account  ${S3_account_name}  ${password}  True       

EST-1037
    [Documentation]  Test that maintenance option not available for s3 user
    [Tags]  Priority_High  Smoke_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    Re-login   ${S3_account_name}  ${password}  MANAGE_MENU_ID
    Check Create CSM User Option Not Exists
    Delete S3 Account  ${S3_account_name}  ${password}  True     

EST-1035
    [Documentation]  Test that maintenance option not available for s3 user
    [Tags]  Priority_High  Smoke_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    Re-login   ${S3_account_name}  ${password}  MANAGE_MENU_ID
    Check Maintenance Option Not Exists
    Delete S3 Account  ${S3_account_name}  ${password}  True   

EST-1034
    [Documentation]  Test that s3 user should only have access to IAM user and Bucket section in provisoning section
    [Tags]  Priority_High  Smoke_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    Re-login   ${S3_account_name}  ${password}  MANAGE_MENU_ID
    Check Dashboard Option Not Exists
    Check Health Option Not Exists
    Check Setting Option Not Exists
    Check Maintenance Option Not Exists
    Delete S3 Account  ${S3_account_name}  ${password}  True    
 
EST-1033
    [Documentation]  Test that alerts should not get visible to the s3 user
    [Tags]  Priority_High  Smoke_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    Re-login   ${S3_account_name}  ${password}  MANAGE_MENU_ID
    Check Dashboard Option Not Exists
    Delete S3 Account  ${S3_account_name}  ${password}  True    
 

TEST-1036
    [Documentation]  Test that S3 account user have access to create IAM users and buckets
    [Tags]  Priority_High  Smoke_test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${testname}=  generate new User Name
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    Re-login   ${S3_account_name}  ${password}  MANAGE_MENU_ID
    Navigate To Page  MANAGE_MENU_ID  IAM_USER_TAB_ID
    Click Create IAM User Button
    Create IAMuser  ${testname}  ${password}
    sleep  5s
    ${status}=  Is IAMuser Present   ${testname}
    Should be equal  ${status}  ${True}
    Delete IAMuser   ${testname}
    sleep  5s
    ${status}=  Is IAMuser Present   ${testname}
    Should be equal  ${status}  ${False}
    sleep  3s
    Navigate To Page  MANAGE_MENU_ID  BUCKET_TAB_ID
    sleep  2s
    Click On Create Bucket Form
    sleep  2s
    Create Bucket  ${testname}
    sleep  5s
    ${status}=  Is Bucket Present   ${testname}
    Should be equal  ${status}  ${True}
    Delete Bucket  ${testname}
    sleep  5s
    ${status}=  Is Bucket Present   ${testname}
    Should be equal  ${status}  ${False}