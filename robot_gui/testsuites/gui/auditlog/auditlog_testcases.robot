*** Settings ***
Documentation    This suite verifies the testcases for csm login
Library     SeleniumLibrary

Resource    ${RESOURCES}/resources/page_objects/loginPage.robot
Resource    ${RESOURCES}/resources/page_objects/auditlogPage.robot
Resource    ${RESOURCES}/resources/page_objects/preboardingPage.robot
Resource    ${RESOURCES}/resources/common/common.robot
Variables   ${RESOURCES}/resources/common/common_variables.py

Test Setup  CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
Test Teardown  Close Browser
Suite Teardown  Close All Browsers

Force Tags  CSM_GUI  CFT_Test

*** Variables ***
${url}
${browser}  chrome
${headless}  True
${navigate_to_subpage}  False
${Sub_tab}  None
${username}
${password}

*** Test Cases ***

TEST-23833
    [Documentation]  Test that cortx user has option search and filter the audit logs on CSM GUI
    ...  Reference : https://jts.seagate.com/browse/TEST-23833
    [Tags]  Priority_High   TEST-23833
    Navigate To Audit Log Section
    Select current date
    Select Audit Log Component  CSM
    Click On View Audit Log Button
    wait for page or element to load
    Select filter for Audit Log  Method
    Search Audit Log Data  POST
    Verify Search Operation Is Working  POST
