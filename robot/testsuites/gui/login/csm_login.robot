*** Settings ***
Documentation    This suite verifies the testcases for csm login
Resource   ${EXECDIR}/resources/page_objects/loginPage.robot
Resource   ${EXECDIR}/resources/common/common.robot
Resource   ${EXECDIR}/resources/page_objects/preboardingPage.robot
Variables  ${EXECDIR}/resources/common/element_locators.py
Variables  ${EXECDIR}/resources/common/common_variables.py


Suite Setup  run keywords   check csm admin user status  ${url}  ${browser}  ${headless}
...  ${username}  ${password}
...  AND  Close Browser
Test Setup  CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
Test Teardown  Close Browser
Suite Teardown  Close All Browsers
Force Tags  CSM_GUI  CSM_login

*** Variables ***
${url}
${browser}  chrome
${headless}  True
${navigate_to_subpage}  False
${Sub_tab}  None
${username}
${password}

*** Test Cases ***
TEST-4242
    [Documentation]  Test that csm user is able to login to CSM UI
    [Tags]  Priority_High  Smoke_test  TEST-4242
    Validate CSM Login Success  ${username}
