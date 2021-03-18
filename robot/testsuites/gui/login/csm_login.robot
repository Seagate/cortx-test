*** Settings ***
Documentation    This suite verifies the testcases for csm login
Resource   ${EXECDIR}/resources/page_objects/loginPage.robot
Resource   ${EXECDIR}/resources/common/common.robot
Resource   ${EXECDIR}/resources/page_objects/preboardingPage.robot
Variables  ${EXECDIR}/resources/common/element_locators.py
Variables  ${EXECDIR}/resources/common/common_variables.py


Suite Setup  run keywords   check csm admin user status  ${url}  ${browser}  ${headless}
...  ${username}  ${password}
...  AND  Close Browser
Test Teardown  Close Browser
Suite Teardown  Close All Browsers
Force Tags  CSM_GUI  CSM_login

*** Variables ***
${url}
${browser}  chrome
${headless}  True
${navigate_to_subpage}  False
${Sub_tab}  None
${username}
${password}

*** Test Cases ***

TEST-4242
    [Documentation]  Test that csm user is able to login to CSM UI
    ...  Reference : https://jts.seagate.com/browse/TEST-4242
    [Tags]  Priority_High  Smoke_test  TEST-4242
    CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
    Validate CSM Login Success  ${username}
    CSM GUI Logout

TEST-3586
    [Documentation]  Test Verify the forward and backward oprations after login on login page
    ...  Reference : https://jts.seagate.com/browse/TEST-3586
    [Tags]  Priority_High  TEST-3586
    CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
    Validate CSM Login Success  ${username}
    Go Back
    sleep  3s  # Took time to load full dashboard
    Go Forward
    sleep  3s  # Took time to load full dashboard
    Validate CSM Login Success  ${username}
    CSM GUI Logout

TEST-6373
    [Documentation]  Test that login button should remain disabled until loading is complete after clicking it once
    ...  Reference : https://jts.seagate.com/browse/TEST-6373
    [Tags]  Priority_High  TEST-6373
    CSM GUI Login and Verify Button Enabled Disabled with Incorrect Credentials  ${url}  ${browser}  ${headless}
    Validate CSM Login Failure
    Close Browser
    CSM GUI Login and Verify Button Enabled Disabled with Correct Credentials  ${url}  ${browser}  ${headless}  ${username}  ${password}
    Validate CSM Login Success  ${username}
    sleep  2s  # Took time to load full dashboard
    CSM GUI Logout

TEST-535
    [Documentation]  Test Only valid user request get authenticated and able to login
    ...  Reference : https://jts.seagate.com/browse/TEST-535
    [Tags]  Priority_High  TEST-535
    CSM GUI Login with Incorrect Credentials  ${url}  ${browser}  ${headless}
    Validate CSM Login Failure
    Close Browser
    CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
    Validate CSM Login Success  ${username}
    CSM GUI Logout
