*** Settings ***
Documentation    This suite verifies the testcases for health page details
Resource    ${RESOURCES}/resources/page_objects/healthPage.robot
Resource    ${RESOURCES}/resources/page_objects/loginPage.robot
Variables   ${RESOURCES}/resources/common/element_locators.py
Variables   ${RESOURCES}/resources/common/common_variables.py

Test Setup  CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
Test Teardown   CSM GUI Logout
Suite Teardown  Close All Browsers
Force Tags  CSM_GUI  CSM_login

*** Test Cases ***

TEST-22645
    [Documentation]  Test node stop scenario for health graph
    [Tags]  Priority_High  R2  TEST-22645
    Navigate To Health
    Click Graphical Tab
    Click Node Stop

TEST-22645_POWEROFF
    [Documentation]  Test node poweroff scenario for health graph
    [Tags]  Priority_High  R2  TEST-22645
    Navigate To Health
    Click Graphical Tab
    Click Node Poweroff

TEST-22645_POWER_AND_STORAGE_OFF
    [Documentation]  Test node Power And Storageoff scenario for health graph
    [Tags]  Priority_High  R2  TEST-22645
    Navigate To Health
    Click Graphical Tab
    Click Node Power And Storageoff
