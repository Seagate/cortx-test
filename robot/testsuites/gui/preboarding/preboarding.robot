*** Settings ***
Documentation    This suite verifies the test-cases for Pre-boarding and EULA
Resource   ${EXECDIR}/resources/page_objects/preboardingPage.robot
Resource   ${EXECDIR}/resources/common/common.robot
Variables  ${EXECDIR}/resources/common/element_locators.py
Variables  ${EXECDIR}/resources/common/common_variables.py

Test Setup  Preboarding  ${url}  ${browser}  ${headless}
Test Teardown  Close Browser
Suite Teardown  Close All Browsers
Force Tags  CSM_GUI  Preboarding

*** Variables ***
${url}
${browser}  chrome
${headless}  True
${Sub_tab}  None

*** Test Cases ***

TEST-4906
    [Documentation]  Test that pop-up with GDPR compliance content is getting displayed on click of Get Started button on first page of onboarding.
    [Tags]  Priority_High  TEST-4906
    Validate ELUA Success  

TEST-3594
    [Documentation]  Test that on preboarding "EULA" is documentation related information is getting displayed.
    [Tags]  Priority_High  TEST-3594
    Validate ELUA Success

TEST-4909
    [Documentation]  Test that content in the GDPR compliance pop-up appropriate.
    ...  Reference : https://jts.seagate.com/browse/TEST-4909
    [Tags]  TEST-4909
    Validate EULA Data

TEST-4908
    [Documentation]  TTest that user navigates to admin user creation page after EULA page
    ...  Reference : https://jts.seagate.com/browse/TEST-4908
    [Tags]  TEST-4908
    Verify User has Naviagted to Admin User Create Page

TEST-4907
    [Documentation]  TTest that user stays on EULA page after canceling the agreement
    ...  Reference : https://jts.seagate.com/browse/TEST-4907
    [Tags]  TEST-4907
    Verify User Has Not Naviagted to Admin User Create Page

TEST-3600
    [Documentation]  Test Verify whether UI have four fields visible
    ...  i.e. "Admin username","Password" , "email-id", "Confirm password", "apply and continue" button
    ...  Reference : https://jts.seagate.com/browse/TEST-3600
    [Tags]  TEST-3600
    Verify User has Naviagted to Admin User Create Page

TEST-3602
    [Documentation]  Test that miss-match ‏password error msg. should be shown for Admin user
    ...  Reference : https://jts.seagate.com/browse/TEST-3602
    [Tags]  TEST-3602
    Validate ELUA Success
    Verify Miss-Match Password Error Message

TEST-3603
    [Documentation]  Test incorrect password shows error message
    ...  Reference : https://jts.seagate.com/browse/TEST-3603
    [Tags]  TEST-3603
    Validate ELUA Success
    Validate Password for Admin User

TEST-3604
    [Documentation]  Test incorrect username shows error message
    ...  Reference : https://jts.seagate.com/browse/TEST-3604
    [Tags]  TEST-3604
    Validate ELUA Success
    Validate Usernames for Admin User

TEST-3605
    [Documentation]  Test admin user crate Form have correct elemets
    ...  Reference : https://jts.seagate.com/browse/TEST-3605
    [Tags]  TEST-3605
    Validate ELUA Success
    Verify elements for Admin User

TEST-3606
    [Documentation]  Test admin user crate Form all mandatory fields have astreak(*) mark
    ...  Reference : https://jts.seagate.com/browse/TEST-3606
    [Tags]  TEST-3606
    Validate ELUA Success
    Verify mandatory elements of Admin User have asterisk mark

TEST-11425
    [Documentation]  Test that Admin page should have tooltips
    ...  Reference : https://jts.seagate.com/browse/TEST-11425
    [Tags]  TEST-11425
    Validate ELUA Success
    Verify Admin User Creation Page Should have tooltip

TEST-11426
    [Documentation]  Test that Admin page should have proper msg. for tooltips
    ...  Reference : https://jts.seagate.com/browse/TEST-11426
    [Tags]  TEST-11426
    Validate ELUA Success
    Validate Admin User Tooltip
