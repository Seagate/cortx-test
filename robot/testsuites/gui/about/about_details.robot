*** Settings ***
Documentation    This suite verifies the testcases for ssl details
Resource    ../../../resources/page_objects/loginPage.robot
Resource    ../../../resources/page_objects/aboutPage.robot
Variables  ../../../resources/common/element_locators.py
Variables  ../../../resources/common/common_variables.py


Suite Teardown  Close All Browsers
Force Tags  CSM_GUI  about_page 

Test Setup  CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
Test Teardown  CSM GUI Logout

*** Variables ***


*** Test Cases ***
test_1111
    [Documentation]  Test that about section has ssl details
    [Tags]  Priority_High  Smoke_test
    Navigate To About 
    Click Issuer Option
    Click Subject Option
    Verify Subject Details
    Click Issuer Option
    Verify Issuer Details

 