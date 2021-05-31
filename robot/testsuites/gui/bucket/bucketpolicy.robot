*** Settings ***
Documentation    This suite verifies the testcases for create bucket
Library     SeleniumLibrary
Resource    ${EXECDIR}/resources/page_objects/bucket_page.robot
Resource    ${EXECDIR}/resources/page_objects/loginPage.robot
Resource    ${EXECDIR}/resources/page_objects/preboardingPage.robot
Resource    ${EXECDIR}/resources/page_objects/s3accountPage.robot

Suite Setup  run keywords   check csm admin user status  ${url}  ${browser}  ${headless}
...  ${username}  ${password}
...  AND  Close Browser
Suite Teardown  Close All Browsers
Force Tags  CSM_GUI  CSM_BUCKET_POLICY
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
${bucket_name}

*** Keywords ***

Login To S3 Account
    [Documentation]  This key word is for test case setup which create s3 account and login to it
    [Tags]  Priority_High  S3_test
    CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    ${S3_account_name}  ${email}  ${s3password} =  Create S3 account
    wait for page or element to load
    Re-login  ${S3_account_name}  ${s3password}  BUCKET_TAB_ID
    Click On Create Bucket Form
    ${bucketname}=  Generate New User Name
    Create Bucket  ${bucketname}
    Click On Edit Bucket Icon
    set suite variable  ${bucketname}
    set suite variable  ${S3_account_name}
    set suite variable  ${s3password}


Delete S3 Account And Close Browser
    [Documentation]  This key word is for test case teardown which delete s3 account and close browsers
    [Tags]  Priority_High  S3_test
    Click On Cancel Bucket Policy
    wait for page or element to load
    Delete Bucket  ${bucketname}
    wait for page or element to load
    CSM GUI Logout
    wait for page or element to load
    Delete S3 Account  ${S3_account_name}  ${s3password}
    wait for page or element to load
    Close Browser

*** Test Cases ***

TEST-4226
    [Documentation]  Test that json policy heading should be present in the form's heading
    ...  Reference : https://jts.seagate.com/browse/TEST-4226
    [Tags]  Priority_High  TEST-4226
    Verify Heading on Bucket Policy Form

TEST-4223
    [Documentation]  Test that popup window appears for bucket policy
    ...  Reference : https://jts.seagate.com/browse/TEST-4223
    [Tags]  Priority_High  TEST-4223
    Verify Update Bucket Policy Form Should Appear

TEST-4225
    [Documentation]  Test that "Update" button will remain disabled At first
    ...  Reference : https://jts.seagate.com/browse/TEST-4225
    [Tags]  Priority_High  TEST-4225
    Verify Update Button Must Remain Disabled

TEST-4228
    [Documentation]  Test that bucket policy is not updated when user cancel it
    ...  Reference : https://jts.seagate.com/browse/TEST-4228
    [Tags]  Priority_High  TEST-4228
    ${policy}=  generate_json_policy  ${bucket_name}
    Log To Console And Report  ${policy}
    Add Json Policy To Bucket  ${policy}
    Click On Cancel Bucket Policy
    Verify Bucket Policy Not Added

TEST-4230
    [Documentation]  Test that appropriate error msg is shown for invalid json
    ...  Reference : https://jts.seagate.com/browse/TEST-4230
    [Tags]  Priority_High  TEST-4230
    ${policy}=  generate_json_policy  "Invalid"
    Log To Console And Report  ${policy}
    Add Json Policy To Bucket  ${policy}
    Click On Update Bucket Policy
    Verify Error Msg is Shown For Invalid Json
    Click On Edit Bucket Icon

TEST-4224
    [Documentation]  Test that s3 user can add policy to the bucket
    ...  Reference : https://jts.seagate.com/browse/TEST-4224
    [Tags]  Priority_High  TEST-4224
    ${policy}=  generate_json_policy  ${bucket_name}
    Log To Console And Report  ${policy}
    Add Json Policy To Bucket  ${policy}
    Click On Update Bucket Policy
    Verify Bucket Policy Got Added  ${policy}

TEST-4229
    [Documentation]  Test that bucket policy get deleted clicks on "Delete" button
    ...  Reference : https://jts.seagate.com/browse/TEST-4229
    [Tags]  Priority_High  TEST-4229
    ${policy}=  generate_json_policy  ${bucket_name}
    Log To Console And Report  ${policy}
    Add Json Policy To Bucket  ${policy}
    Click On Update Bucket Policy
    Refresh To Bucket Page
    Click On Edit Bucket Icon
    Click On Delete Bucket Policy
    Verify Bucket Policy Not Added

TEST-4227
    [Documentation]  Test that bucket policy is updated "Update" button
    ...  Reference : https://jts.seagate.com/browse/TEST-4227
    [Tags]  Priority_High  TEST-4227
    ${policy}=  generate_json_policy  ${bucket_name}
    Log To Console And Report  ${policy}
    Add Json Policy To Bucket  ${policy}
    Click On Update Bucket Policy
    ${new_policy}=  update_json_policy  ${policy}
    Log To Console And Report  ${new_policy}
    wait for page or element to load
    Click On Edit Bucket Icon
    Add Json Policy To Bucket  ${new_policy}
    Click On Update Bucket Policy
    Verify Bucket Policy Got Added  ${new_policy}
