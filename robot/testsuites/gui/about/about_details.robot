*** Settings ***
Documentation    This suite verifies the testcases for ssl details
Resource    ${EXECDIR}/resources/page_objects/aboutPage.robot
Resource    ${EXECDIR}/resources/page_objects/loginPage.robot
Resource    ${EXECDIR}/resources/page_objects/preboardingPage.robot
Variables   ${EXECDIR}/resources/common/element_locators.py
Variables   ${EXECDIR}/resources/common/common_variables.py

Suite Setup  run keywords   check csm admin user status  ${url}  ${browser}  ${headless}
...  ${username}  ${password}
...  AND  Close Browser
Test Setup  CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
Test Teardown   CSM GUI Logout
Suite Teardown  Close All Browsers
Force Tags  CSM_GUI  CSM_login

*** Test Cases ***

TEST-17997
    [Documentation]  Test that about section has ssl details
    [Tags]  Priority_High  R2 TEST-17997
    Navigate To About
    Click Issuer Option
    Click Subject Option
    Verify Subject Details
    Click Issuer Option
    Verify Issuer Details
