*** Settings ***
Documentation    This suite verifies the testcases for create bucket
Library     SeleniumLibrary
Resource    ${RESOURCES}/resources/page_objects/bucket_page.robot
Resource    ${RESOURCES}/resources/page_objects/IAM_UsersPage.robot
Resource    ${RESOURCES}/resources/page_objects/loginPage.robot
Resource    ${RESOURCES}/resources/page_objects/preboardingPage.robot
Resource    ${RESOURCES}/resources/page_objects/s3accountPage.robot
Variables   ${RESOURCES}/resources/common/common_variables.py

Suite Setup  run keywords   check csm admin user status  ${url}  ${browser}  ${headless}
...  ${username}  ${password}
...  AND  Close Browser
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
${invalid_bucket_name}  TestBucket

*** Keywords ***

Login To S3 Account
    [Documentation]  This key word is for test case setup which create s3 account and login to it
    [Tags]  Priority_High  S3_test
    CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    wait for page or element to load
    Re-login  ${S3_account_name}  ${password}  S3_ACCOUNTS_TAB_ID
    Navigate To Page  S3_BUCKET_TAB_ID

Delete S3 Account And Close Browser
    [Documentation]  This key word is for test case teardown which delete s3 account and close browsers
    [Tags]  Priority_High  S3_test
    wait for page or element to load
    Navigate To Page   S3_ACCOUNTS_TAB_ID
    ${S3_account_name}=  Fetch S3 Account Name
    wait for page or element to load
    Delete S3 Account  ${S3_account_name}  ${password}  True
    Close Browser

*** Test Cases ***

TEST-939
   [Documentation]  Test that buckets is created
   [Tags]  Priority_High  Smoke_test  TEST-939
   Click On Create Bucket Form
   ${bucketname}=  Generate New User Name
   Create Bucket  ${bucketname}
   Delete Bucket  ${bucketname}

TEST-937
   [Documentation]  Test that buckets are getting listed.
   [Tags]  Priority_High  TEST-937  Smoke_test
   Click On Create Bucket Form
   ${bucketname}=  Generate New User Name
   Create Bucket  ${bucketname}
   Is Bucket Present  ${bucketname}
   Delete Bucket  ${bucketname}

TEST-938
   [Documentation]  Test that on click of create button, form for create bucket is getting opened.
   [Tags]  Priority_High  TEST-938
   verify that create buttn functionality on buckets tab

TEST-940
   [Documentation]  Test that after bucket is created, form to create new bucket is getting closed.
   [Tags]  Priority_High  TEST-940
   Click On Create Bucket Form
   ${bucketname}=  Generate New User Name
   Create Bucket  ${bucketname}
   Is Bucket Present  ${bucketname}
   Check element is not visiable  BUCKET_NAME_ID
   Delete Bucket  ${bucketname}

TEST-941
   [Documentation]  Test that bucket name policy tooltip show correct content.
   [Tags]  Priority_High  TEST-941
   Click On Create Bucket Form
   verify the tooptip for the bucket name policy

TEST-942
   [Documentation]  Test that "Create bucket" button remains disabled when entered invalid name.
   [Tags]  Priority_High  TEST-942
   Click On Create Bucket Form
   Verify that create bucket button remains disabled  ${invalid_bucket_name}

TEST-943
   [Documentation]  Test that "cancel" button for bucket creation is working properly
   [Tags]  Priority_High  TEST-943
   Click On Create Bucket Form
   Verfiy the cancel create bucket functionality

TEST-944
   [Documentation]  Test that alert appear on screen when try to create bucket with bucketname
    ...  with existing buckets
   [Tags]  Priority_High  TEST-944
   Click On Create Bucket Form
   ${bucketname}=  Generate New User Name
   Create Bucket  ${bucketname}
   Is Bucket Present  ${bucketname}
   Click On Create Bucket Form
   Verify the message for duplicate bucket name  ${bucketname}
   Delete Bucket  ${bucketname}


TEST-945
   [Documentation]  Test that bucket is getting deleted.
    ...  with existing buckets
   [Tags]  Priority_High  TEST-945  Smoke_test
   Click On Create Bucket Form
   ${bucketname}=  Generate New User Name
   Create Bucket  ${bucketname}
   Is Bucket Present  ${bucketname}
   Delete Bucket  ${bucketname}

TEST-946
   [Documentation]  Test that csncle delete bucket works.
   [Tags]  Priority_High  TEST-946
   Click On Create Bucket Form
   ${bucketname}=  Generate New User Name
   Create Bucket  ${bucketname}
   Verify cancel opration of delete bucket  ${bucketname}
   Delete Bucket  ${bucketname}






