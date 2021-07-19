*** Settings ***
Documentation    This suite verifies the testcases for SWServices
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
    [Tags]  Priority_High  R2  SW_SERVICE_INIT
    Fail if New alerts exist SW Service  ${servicename}
    Acknowledge if Active alerts exist SW Service  ${servicename}

SW_SERVICE_VERIFY_FAIL
    [Documentation]  CSM GUI: Verify Alerts for SW Service : fail
    [Tags]  Priority_High  R2  SW_SERVICE_VERIFY_FAIL
    # fail service
    Verify failed alerts exist SW Service  ${servicename}

SW_SERVICE_VERIFY_FAIL_RESOLVED
    [Documentation]  CSM GUI: Verify Alerts for SW Service : failed resolved
    [Tags]  Priority_High  R2  SW_SERVICE_VERIFY_FAIL_RESOLVED
    # start fail service
    Verify and Acknowledge failed resolved alerts exist SW Service  ${servicename}

SW_SERVICE_VERIFY_INACTIVATE
    [Documentation]  CSM GUI: Verify Alerts for SW Service : inactive
    [Tags]  Priority_High  R2  SW_SERVICE_VERIFY_INACTIVATE
    # inactive service
    Verify inactive alerts exist SW Service  ${servicename}

SW_SERVICE_VERIFY_INACTIVATE_RESOLVED
    [Documentation]  CSM GUI: Verify Alerts for SW Service : inactive resolved
    [Tags]  Priority_High  R2  SW_SERVICE_VERIFY_INACTIVATE_RESOLVED
    # start inactive service
    Verify and Acknowledge inactive resolved alerts exist SW Service  ${servicename}

SW_SERVICE_VERIFY_DEACTIVATE
    [Documentation]  CSM GUI: Verify Alerts for SW Service : deactivat
    [Tags]  Priority_High  R2  SW_SERVICE_VERIFY_DEACTIVATE
    # deactivat service
    Check if alert exists in New alerts tab  ${description}
    Verify deactivating alerts exist SW Service  ${servicename}

SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED
    [Documentation]  CSM GUI: Verify Alerts for SW Service : deactivated resolved
    [Tags]  Priority_High  R2  SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED
    # start deactivated service
    Check if alert exists in Active alerts tab  ${description}
    Verify and Acknowledge deactivating resolved alerts exist SW Service  ${servicename}

# TEST-21262
#     [Documentation]  CSM GUI: Verify Alerts for SW Service : HAProxy
#     ...  Reference : https://jts.seagate.com/browse/TEST-21262
#     [Tags]  Priority_High  R2 TEST-21262
#     Fail if New alerts exist SW Service  ${servicename}
#     Acknowledge if Active alerts exist SW Service  ${servicename}
#     # fail service
#     Verify failed alerts exist SW Service  ${servicename}
#     # start service
#     Verify failed resolved alerts exist SW Service  ${servicename}
#     # inactive service
#     Verify inactive alerts exist SW Service  ${servicename}
#     # start service
#     Verify inactive resolved alerts exist SW Service  ${servicename}
#     Verify failed alerts exist SW Service  ${servicename}
