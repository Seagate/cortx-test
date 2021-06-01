*** Settings ***
Documentation    This suite verifies the testcases for csm login
Library     SeleniumLibrary
Resource    ${RESOURCES}/resources/page_objects/dashboardPage.robot
Resource    ${RESOURCES}/resources/page_objects/loginPage.robot
Resource    ${RESOURCES}/resources/page_objects/preboardingPage.robot

Suite Setup  run keywords   check csm admin user status  ${url}  ${browser}  ${headless}
...  ${username}  ${password}
...  AND  Close Browser
Test Setup  CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
Test Teardown  Close Browser
Suite Teardown  Close All Browsers

Force Tags  CSM_GUI

*** Variables ***
${url}
${browser}  chrome
${headless}  True
${username}
${password}

*** Test Cases ***

TEST-4195
    [Documentation]  Test that total capacity should be equal to `Used` + `Available` capacity
    ...  Reference : https://jts.seagate.com/browse/TEST-4195
    [Tags]  Priority_High  TEST-4195
    Verify Total Capacity Should Be Addition Of Used And Available

TEST-5185
    [Documentation]  Test that username of user who is logged into the
    ...  system is getting displayed on the top right side of the screen.
    ...  Reference : https://jts.seagate.com/browse/TEST-5185
    [Tags]  Priority_High  TEST-5185
    Validate CSM Login Success  ${username}

TEST-4193
    [Documentation]  Test that Dashboard must have a capacity section in it
    ...  Reference : https://jts.seagate.com/browse/TEST-4193
    [Tags]  Priority_High  TEST-4193
    Verify Presence of capacity graph in capacity widget

TEST-13559
    [Documentation]  Test that Dashboard must have a capacity section in it
    ...  Reference : https://jts.seagate.com/browse/TEST-13559
    [Tags]  Priority_High  TEST-13559
    Verify Presence of dashboard capacity widget

TEST-13561
    [Documentation]  Test that capacity section should have `used` labels on it
    ...  Reference : https://jts.seagate.com/browse/TEST-13561
    [Tags]  Priority_High  TEST-13561
    Verify Presence of Used label on dashboard capacity widget

TEST-13562
    [Documentation]  Test that capacity section should have `Available` labels on it
    ...  Reference : https://jts.seagate.com/browse/TEST-13563
    [Tags]  Priority_High  TEST-13562
    Verify Presence of Available label on dashboard capacity widget

TEST-13563
    [Documentation]  Test that capacity section should have `Total` labels on it
    ...  Reference : https://jts.seagate.com/browse/TEST-13563
    [Tags]  Priority_High  TEST-13563
    Verify Presence of Total label on dashboard capacity widget
