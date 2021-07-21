*** Settings ***
Documentation    This suite provides test cases for node & cluster alert validation
Resource    ${RESOURCES}/resources/page_objects/alertPage.robot
Resource    ${RESOURCES}/resources/page_objects/healthPage.robot
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
${node_id}  0

*** Test Cases ***

CHECK_IN_HEALTH_NODE_ONLINE
    [Documentation]  CSM GUI: Check node is online state on health page
    [Tags]  PYTEST  CHECK_IN_HEALTH_NODE_ONLINE
    Check if Node status  ${node_id}  online

CHECK_IN_HEALTH_NODE_FAILED
    [Documentation]  CSM GUI: Check node is failed state on health page
    [Tags]  PYTEST  CHECK_IN_HEALTH_NODE_FAILED
    Check if Node status  ${node_id}  failed

CHECK_IN_HEALTH_CLUSTER_ONLINE
    [Documentation]  CSM GUI: Check cluster is online state on health page
    [Tags]  PYTEST  CHECK_IN_HEALTH_CLUSTER_ONLINE
    Check if Cluster status  online

CHECK_IN_HEALTH_CLUSTER_DEGRADED
    [Documentation]  CSM GUI: Check cluster is failed state on health page
    [Tags]  PYTEST  CHECK_IN_HEALTH_CLUSTER_DEGRADED
    Check if Cluster status  degraded
