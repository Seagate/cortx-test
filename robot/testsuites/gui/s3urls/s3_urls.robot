*** Settings ***
Documentation    This suite verifies the testcases for csm login
Library    SeleniumLibrary
Resource   ${RESOURCES}/resources/page_objects/bucket_page.robot
Resource   ${RESOURCES}/resources/page_objects/IAM_UsersPage.robot
Resource   ${RESOURCES}/resources/page_objects/loginPage.robot
Resource   ${RESOURCES}/resources/page_objects/preboardingPage.robot
Resource   ${RESOURCES}/resources/page_objects/s3accountPage.robot
Resource   ${RESOURCES}/resources/page_objects/settingsPage.robot
Resource   ${RESOURCES}/resources/common/common.robot
Variables  ${RESOURCES}/resources/common/common_variables.py
Variables  ${RESOURCES}/resources/common/element_locators.py

Suite Setup  run keywords   check csm admin user status  ${url}  ${browser}  ${headless}  ${username}  ${password}
...  AND  Close Browser
Suite Teardown  Close All Browsers
Force Tags  CSM_GUI  CSM_login
Test Setup  run keywords  CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}  AND
...  Create s3 account and login
Test Teardown  Delete S3 Account And Close Browser

*** Variables ***
${url}
${browser}  chrome
${headless}  True
${navigate_to_subpage}  False
${Sub_tab}  None
${username}
${password}
${s3_account_user_name}
${s3_password}

*** Keywords ***

Create s3 account and login
    [Documentation]  This is test level keyword to create and and login to s3 account
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    ${s3_account_user_name}  ${email}  ${s3_password} =  Create S3 account
    Set test variable    ${s3_account_user}  ${s3_account_user_name}
    Set test variable    ${s3_account_password}  ${s3_password}
    wait for page or element to load
    Re-login  ${s3_account_user_name}  ${s3_password}  S3_ACCOUNTS_TAB_ID

Delete S3 Account And Close Browser
    [Documentation]  This key word is for test case teardown which delete s3 account and close browsers
    Log To Console And Report  ${s3_account_user_name}
    Log To Console And Report  ${s3_password}
    wait for page or element to load
    Navigate To Page   S3_ACCOUNTS_TAB_ID
    ${s3_account_user_name}=  Fetch S3 Account Name
    wait for page or element to load
    Delete S3 Account  ${s3_account_user_name}  ${s3_password}  True
    Close Browser


*** Test Cases ***

TEST-14405
   [Documentation]  Test that tooltip associated with bucket contains bucket_URL.
   [Tags]  Priority_High  TEST-14405  S3_URL
   Navigate To Page  Bucket_TAB_ID
   Click On Create Bucket Form
   ${bucketname}=  Generate New User Name
   Create Bucket  ${bucketname}
   Verify the bucket url in buckets table  ${bucketname}
   Delete Bucket  ${bucketname}
   wait for page or element to load

TEST-14404
   [Documentation]  Verify that bucket URL is shown on popup window after bucket is created
   [Tags]  Priority_High  TEST-14404  S3_URL
   Navigate To Page  Bucket_TAB_ID
   Click On Create Bucket Form
   ${bucketname}=  Generate New User Name
   Create Bucket  ${bucketname}  True
   Delete Bucket  ${bucketname}
   wait for page or element to load

TEST-14402
   [Documentation]  Verify that s3 URL is shown on popup window after IAM user is created
   [Tags]  Priority_High  TEST-14402  S3_URL
   Navigate To Page   IAM_USER_TAB_ID
   ${username}=  Generate New User Name
   ${password}=  Generate New Password
   Click Create IAM User Button
   wait for page or element to load  1s
   Create IAMuser  ${username}  ${password}  False  True
   Delete IAMuser  ${username}
   wait for page or element to load  # Need to reload the uses

TEST-14401
   [Documentation]  Verify that s3 URL is shown IAM user tab
   [Tags]  Priority_High  TEST-14401  S3_URL
   Navigate To Page   IAM_USER_TAB_ID
   wait for page or element to load
   Verify S3 urls are displayed on the IAM user tab

TEST-14403
   [Documentation]  Verify that s3 URLs is displayed on popup which appears after generating new set of access keys
    ...  for IAM user
   [Tags]  Priority_High  TEST-14403  S3_URL
   Navigate To Page   IAM_USER_TAB_ID
   ${username}=  Generate New User Name
   ${password}=  Generate New Password
   Click Create IAM User Button
   wait for page or element to load  1s
   Create IAMuser  ${username}  ${password}  False  True
   Verify s3 urls on access keys popup
   wait for page or element to load
   Delete IAMuser  ${username}
   wait for page or element to load  # Need to reload the uses


TEST-14400
   [Documentation]  Test that both s3 URLs appears above IAM users table on IAM users page
   [Tags]  Priority_High  TEST-14400  S3_URL
   Navigate To Page   IAM_USER_TAB_ID
   wait for page or element to load
   Verify S3 urls are displayed on the IAM user tab

TEST-14399
   [Documentation]  Test that both s3 URLs appears on S3 accounts tab.
   [Tags]  Priority_High  TEST-14399  TEST-14398  S3_URL
   wait for page or element to load
   Verify S3 urls are displayed on the S3accounts tab


TEST-14393
   [Documentation]  Test that appropriate fields are shown on popup that appears after generating
   ...  new access keys for s3 account
   [Tags]  Priority_High  TEST-14393  S3_URL
   wait for page or element to load
   Verify that s3 url is displyed access key popup

TEST-14392
    [Documentation]  Test that appropriate fields are shown on popup that appears after generating
   ...  new s3 account
   [Tags]  Priority_High  TEST-14392  S3_URL
   Re-login  ${username}  ${password}  S3_ACCOUNTS_TAB_ID
   Navigate To Page    S3_ACCOUNTS_TAB_ID
   wait for page or element to load
   Verify that s3 url on s3 account creation
   wait for page or element to load
   Log To Console And Report  ${s3_account_user}
   Log To Console And Report  ${s3_account_password}
   Re-login  ${s3_account_user}  ${s3_account_password}  S3_ACCOUNTS_TAB_ID  false
