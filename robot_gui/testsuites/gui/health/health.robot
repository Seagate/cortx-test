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

TEST-22645_TABULAR
    [Documentation]  Test node stop scenario for health table
    [Tags]  Priority_High  R2  TEST-22645
    Navigate To Health
    Click Tablular Tab
    Click Node Stop for health table

TEST-22645_POWEROFF_TABULAR
    [Documentation]  Test node poweroff scenario for health table
    [Tags]  Priority_High  R2  TEST-22645
    Navigate To Health
    Click Tablular Tab
    Click Node Poweroff for health table

TEST-22645_POWER_AND_STORAGE_OFF_TABULAR
    [Documentation]  Test node Power And Storageoff scenario for health table
    [Tags]  Priority_High  R2  TEST-22645
    Navigate To Health
    Click Tablular Tab
    Click Node Power And Storageoff for health table

TEST-22646
    [Documentation]  Test node stop scenario for health graph
    [Tags]  Priority_High  R2  TEST-22646
    Navigate To Health
    Click Graphical Tab
    Click Node Start
	
TEST-22646_NODE_START_TABULAR
    [Documentation]  Test node stop scenario for health graph
    [Tags]  Priority_High  R2  TEST-22646
    Navigate To Health
    Click Tablular Tab
    Click Node Start for health table
