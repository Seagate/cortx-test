*** Settings ***
Documentation    This suite verifies the test-cases for Pre-boarding and EULA
Resource    ${EXECDIR}/resources/page_objects/preboardingPage.robot
Resource  ${EXECDIR}/resources/common/common.robot
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
