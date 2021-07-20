*** Settings ***
Documentation    This suite provides test cases for service alert validation
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
${servicename}  statsd.service

*** Test Cases ***

SW_SERVICE_VERIFY_INIT
    [Documentation]  CSM GUI: Verify Alerts for SW Service : init
    [Tags]  PYTEST  SW_SERVICE_VERIFY_INIT
    Fail if New alerts exist SW Service  ${servicename}
    Acknowledge if Active alerts exist SW Service  ${servicename}

SW_SERVICE_VERIFY_FAIL
    [Documentation]  CSM GUI: Verify Alerts for SW Service : fail
    [Tags]  PYTEST  SW_SERVICE_VERIFY_FAIL
    # fail service
    Verify failed alerts exist SW Service  ${servicename}

SW_SERVICE_VERIFY_FAIL_RESOLVED
    [Documentation]  CSM GUI: Verify Alerts for SW Service : failed resolved
    [Tags]  PYTEST  SW_SERVICE_VERIFY_FAIL_RESOLVED
    # start fail service
    Verify and Acknowledge failed resolved alerts exist SW Service  ${servicename}

SW_SERVICE_VERIFY_INACTIVATE
    [Documentation]  CSM GUI: Verify Alerts for SW Service : inactive
    [Tags]  PYTEST  SW_SERVICE_VERIFY_INACTIVATE
    # inactive service
    Verify inactive alerts exist SW Service  ${servicename}

SW_SERVICE_VERIFY_INACTIVATE_RESOLVED
    [Documentation]  CSM GUI: Verify Alerts for SW Service : inactive resolved
    [Tags]  PYTEST  SW_SERVICE_VERIFY_INACTIVATE_RESOLVED
    # start inactive service
    Verify and Acknowledge inactive resolved alerts exist SW Service  ${servicename}

SW_SERVICE_VERIFY_DEACTIVATE
    [Documentation]  CSM GUI: Verify Alerts for SW Service : deactivat
    [Tags]  PYTEST  SW_SERVICE_VERIFY_DEACTIVATE
    # deactivat service
    Check if alert exists in New alerts tab  ${description}
    Verify deactivating alerts exist SW Service  ${servicename}

SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED
    [Documentation]  CSM GUI: Verify Alerts for SW Service : deactivated resolved
    [Tags]  PYTEST  SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED
    # start deactivated service
    Check if alert exists in Active alerts tab  ${description}
    Verify and Acknowledge deactivating resolved alerts exist SW Service  ${servicename}
