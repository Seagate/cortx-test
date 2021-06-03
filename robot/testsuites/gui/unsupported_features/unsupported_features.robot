*** Settings ***
Documentation    This suite verifies the testcases for csm login
Library     SeleniumLibrary
Resource    ${EXECDIR}/resources/page_objects/firmwareUpdatepage.robot
Resource    ${EXECDIR}/resources/page_objects/healthPage.robot
Resource    ${EXECDIR}/resources/page_objects/lyvePilot.robot
Resource    ${EXECDIR}/resources/page_objects/preboardingPage.robot
Resource    ${EXECDIR}/resources/page_objects/settingsPage.robot
Resource    ${EXECDIR}/resources/page_objects/softwareUpdatepage.robot
Resource    ${EXECDIR}/resources/page_objects/userSettingsLocalPage.robot
Resource    ${EXECDIR}/resources/common/common.robot
Variables   ${EXECDIR}/resources/common/common_variables.py


Suite Setup  run keywords   check csm admin user status  ${url}  ${browser}  ${headless}
...  ${username}  ${password}
...  AND  Close Browser
Test Setup  CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
Test Teardown  Close Browser
Suite Teardown  Close All Browsers

Force Tags  CSM_GUI  Unsupported Features

*** Variables ***
${url}
${browser}  chrome
${headless}  True
${navigate_to_subpage}  False
${Sub_tab}  None
${username}
${password}

*** Test Cases ***

TEST-21268
    [Documentation]  CSM GUI: Verify Unsupported Features : Health Tab should not be accessible
    ...  Reference : https://jts.seagate.com/browse/TEST-21268
    [Tags]  Priority_High  user_role  TEST-21268
    Check Health Option Not Exists
    Capture Page Screenshot  TEST-21268.png

TEST-22591
    [Documentation]  CSM GUI: Verify Unsupported Features : Lyve Pilot Tab should not be accessible
    ...  Reference : https://jts.seagate.com/browse/TEST-22591
    [Tags]  Priority_High  user_role  TEST-22591
    Verify that user can not access Lyve Pilot menu
    Capture Page Screenshot  TEST-22591.png

TEST-22592
    [Documentation]  CSM GUI: Verify Unsupported Features : System Maintenance section under Maintenance​ Tab should not be accessible
    ...  Reference : https://jts.seagate.com/browse/TEST-22592
    [Tags]  Priority_High  user_role  TEST-22592
    Check System Maintenance Section Not Exists
    Capture Page Screenshot  TEST-22592.png

TEST-22593
    [Documentation]  CSM GUI: Verify Unsupported Features : Firmware update section under Maintenance​ Tab should not be accessible
    ...  Reference : https://jts.seagate.com/browse/TEST-22593
    [Tags]  Priority_High  user_role  TEST-22593
    Check Firmware Update Section Not Exists
    Capture Page Screenshot  TEST-22593.png

TEST-22594
    [Documentation]  CSM GUI: Verify Unsupported Features : Software update section under Maintenance​ Tab should not be accessible
    ...  Reference : https://jts.seagate.com/browse/TEST-22594
    [Tags]  Priority_High  user_role  TEST-22594
    Check Software Update Section Not Exists
    Capture Page Screenshot  TEST-22594.png

TEST-22654
    [Documentation]  CSM GUI: Verify Unsupported Features : Start Service Option under system maintenance​ should not be accessible
    ...  Reference : https://jts.seagate.com/browse/TEST-22654
    [Tags]  Priority_High  user_role  TEST-22654
    Check Start Service Option Not Exists
    Capture Page Screenshot  TEST-22654.png

TEST-22655
    [Documentation]  CSM GUI: Verify Unsupported Features : Stop Service Option under system maintenance​ should not be accessible
    ...  Reference : https://jts.seagate.com/browse/TEST-22655
    [Tags]  Priority_High  user_role  TEST-22655
    Check Stop Service Option Not Exists
    Capture Page Screenshot  TEST-22655.png

TEST-22656
    [Documentation]  CSM GUI: Verify Unsupported Features : Shutdown option under system maintenance​ should not be accessible
    ...  Reference : https://jts.seagate.com/browse/TEST-22656
    [Tags]  Priority_High  user_role  TEST-22656
    Check Shutdown Option Not Existss
    Capture Page Screenshot  TEST-22656.png

TEST-22595
    [Documentation]  CSM GUI: Verify Unsupported Features : Health Tab should be accessible
    ...  Reference : https://jts.seagate.com/browse/TEST-22595
    [Tags]  Priority_High  user_role  TEST-22595
    Check Health Option Exists
    Capture Page Screenshot  TEST-22595.png

TEST-22596
    [Documentation]  CSM GUI: Verify Unsupported Features : Lyve Pilot Tab should be accessible
    ...  Reference : https://jts.seagate.com/browse/TEST-22596
    [Tags]  Priority_High  user_role  TEST-22596
    Verify that user can access Lyve Pilot menu
    Capture Page Screenshot  TEST-22596.png

TEST-22597
    [Documentation]  CSM GUI: Verify Unsupported Features : System Maintenance section under Maintenance​ Tab should be accessible
    ...  Reference : https://jts.seagate.com/browse/TEST-22597
    [Tags]  Priority_High  user_role  TEST-22597
    Check System Maintenance Section Exists
    Capture Page Screenshot  TEST-22597.png

TEST-22598
    [Documentation]  CSM GUI: Verify Unsupported Features : Firmware update section under Maintenance​ Tab should be accessible
    ...  Reference : https://jts.seagate.com/browse/TEST-22598
    [Tags]  Priority_High  user_role  TEST-22598
    Check Firmware Update Section Exists
    Capture Page Screenshot  TEST-22598.png

TEST-22599
    [Documentation]  CSM GUI: Verify Unsupported Features : Software update section under Maintenance​ Tab should be accessible
    ...  Reference : https://jts.seagate.com/browse/TEST-22599
    [Tags]  Priority_High  user_role  TEST-22599
    Check Software Update Section Exists
    Capture Page Screenshot  TEST-22599.png

TEST-22660
    [Documentation]  CSM GUI: Verify Unsupported Features : Start Service Option under system maintenance​ should be accessible
    ...  Reference : https://jts.seagate.com/browse/TEST-22660
    [Tags]  Priority_High  user_role  TEST-22660
    Check Start Service Option Exists
    Capture Page Screenshot  TEST-22660.png

TEST-22659
    [Documentation]  CSM GUI: Verify Unsupported Features : Stop Service Option under system maintenance​ should be accessible
    ...  Reference : https://jts.seagate.com/browse/TEST-22659
    [Tags]  Priority_High  user_role  TEST-22659
    Check Stop Service Option Exists
    Capture Page Screenshot  TEST-22659.png

TEST-22658
    [Documentation]  CSM GUI: Verify Unsupported Features : Shutdown option under system maintenance​ should be accessible
    ...  Reference : https://jts.seagate.com/browse/TEST-22658
    [Tags]  Priority_High  user_role  TEST-22658
    Check Shutdown Option Exists
    Capture Page Screenshot  TEST-22658.png
