*** Settings ***
Documentation    This suite verifies the testcases for csm login
Resource    ../../../resources/page_objects/loginPage.robot
Resource  ../../../resources/common/common.robot
Variables  ../../../resources/common/element_locators.py
Variables  ../../../resources/common/common_variables.py


Suite Teardown  Close All Browsers
Force Tags  CSM_GUI  CSM_login

*** Variables ***
${url}  https://10.230.246.58:28100/#/
${browser}  chrome
${headless}  True
${navigate_to_subpage}  False
${Sub_tab}  None

*** Test Cases ***
test_4242
    [Documentation]  Test that csm user is able to login to CSM UI
    [Tags]  Priority_High
    [Setup]   CSM GUI Login  ${url}  ${browser}  ${headless}  ${csm admin user}  ${csm admin password}
    Validate CSM Login Success  ${csm admin user}
    [Teardown]  Close Browser
