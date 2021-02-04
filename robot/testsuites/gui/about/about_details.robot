*** Settings ***
Documentation    This suite verifies the testcases for csm login
Resource    ../../../resources/page_objects/loginPage.robot
Resource    ../../../resources/page_objects/aboutPage.robot
Variables  ../../../resources/common/element_locators.py
Variables  ../../../resources/common/common_variables.py


Suite Teardown  Close All Browsers
Force Tags  CSM_GUI  CSM_login

Test Setup  CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
Test Teardown  CSM GUI Logout

*** Variables ***
${url}
${browser}  chrome
${headless}  True
${navigate_to_subpage}  False
${Sub_tab}  None
${username}
${password}

*** Test Cases ***
test_1111
    [Documentation]  Test that about section has ssl details
    [Tags]  Priority_High  Smoke_test
   Navigate To About 
    sleep  5s
    Click Issuer Option
    sleep  5s
    Click Subject Option
    sleep  2s
    Verify Subject Details
    sleep  2s
    Click Issuer Option
    sleep  2s
    Verify Issuer Details

    
 