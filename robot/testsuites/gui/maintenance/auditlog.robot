*** Settings ***
Documentation    This suite verifies the testcases for csm login
Library     SeleniumLibrary
Resource    ${RESOURCES}/resources/page_objects/loginPage.robot
Resource    ${RESOURCES}/resources/page_objects/auditlogPage.robot
Resource    ${RESOURCES}/resources/page_objects/preboardingPage.robot
Resource    ${RESOURCES}/resources/common/common.robot
Variables   ${RESOURCES}/resources/common/common_variables.py
Variables   ${RESOURCES}/resources/common/common_variables.py

Suite Setup  run keywords   check csm admin user status  ${url}  ${browser}  ${headless}
...  ${username}  ${password}
...  AND  Close Browser
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
${Download_File_Path}  \root\Downloads\



*** Test Cases ***

TEST-21212
    [Documentation]  Test that CSM Audit logs are getting displayed in the Tabular format
    ...  Reference : https://jts.seagate.com/browse/TEST-21212
    [Tags]  Priority_High  Audit_log  TEST-21212  CSM_Audit_Log
    ${test_id}    Set Variable    TEST-21212
    wait for page or element to load
    Navigate To Audit Log Section
    Capture Page Screenshot  ${test_id}_audit_log_section.png
    Verify CSM Audit Log In Tabular format
    Capture Page Screenshot  ${test_id}_CSM_audit_log_generated.png
