*** Settings ***
Documentation    This suite provides test cases for alert validation
Resource    ${RESOURCES}/resources/page_objects/alertPage.robot
Resource    ${RESOURCES}/resources/page_objects/loginPage.robot
Resource    ${RESOURCES}/resources/page_objects/preboardingPage.robot
Variables   ${RESOURCES}/resources/common/element_locators.py
Variables   ${RESOURCES}/resources/common/common_variables.py

Test Setup  CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
Test Teardown  Close Browser
Suite Teardown  Close All Browsers

*** Test Cases ***

CHECK_IN_NEW_ALERTS
    [Documentation]  CSM GUI: Check if alert present in new alert table
    [Tags]  Priority_High  R2  CHECK_IN_NEW_ALERTS
    Check if alert exists in New alerts tab  ${description}

