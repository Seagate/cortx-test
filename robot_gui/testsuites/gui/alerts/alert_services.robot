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

*** Variables ***
${url}
${browser}  chrome
${headless}  True
${username}
${password}
${description}

*** Test Cases ***

CHECK_IN_NEW_ALERTS
    [Documentation]  CSM GUI: Check if alert present in new alert table
    [Tags]  Priority_High  R2  CHECK_IN_NEW_ALERTS
    Check if alert exists in New alerts tab  ${description}

ACKNOWLEDGE_ACTIVE_ALERT
    [Documentation]  CSM GUI: acknowledge alert from active alert table
    [Tags]  Priority_High  R2  ACKNOWLEDGE_ACTIVE_ALERT
    Acknowledge if Active alerts exist  ${description}

CHECK_IN_NEW_ALERTS_AND_FAIL
    [Documentation]  CSM GUI: Check if alert present in new alert table and fail if present.
    [Tags]  Priority_High  R2  CHECK_IN_NEW_ALERTS_AND_FAIL
    Fail if alert already exists in New alerts tab  ${description}

CHECK_IN_ACTIVE_ALERTS
    [Documentation]  CSM GUI: Check if alert present in Active alerts table
    [Tags]  Priority_High  R2  CHECK_IN_ACTIVE_ALERTS
    Check if alert exists in Active alerts tab  ${description}

CHECK_IN_ACTIVE_ALERTS_AND_FAIL
    [Documentation]  CSM GUI: Check if alert present in active alert table and fail if present.
    [Tags]  Priority_High  R2  CHECK_IN_ACTIVE_ALERTS_AND_FAIL
    Fail if alert already exists in Active alerts tab  ${description}

CHECK_IN_ALERT_HISTORY
    [Documentation]  CSM GUI: Check if alert present in alert history table
    [Tags]  Priority_High  R2  CHECK_IN_ALERT_HISTORY
    Check if alert exists in Alert history tab  ${description}

CHECK_IN_ALERTS_HISTORY_AND_FAIL
    [Documentation]  CSM GUI: Check if alert present in alert history table and fail if present.
    [Tags]  Priority_High  R2  CHECK_IN_ALERTS_HISTORY_AND_FAIL
    Fail if alert already exists in Alert history tab  ${description}
