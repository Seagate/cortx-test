*** Settings ***
Library    SeleniumLibrary
Resource   ${RESOURCES}/resources/common/common.robot
Variables  ${RESOURCES}/resources/common/element_locators.py

*** Keywords ***

Open URL
    [Documentation]  Test keyword is for opening the URL in the browser, with specific options.
    [Arguments]  ${url}  ${browser}
    open browser  ${url}  ${browser}    options=add_argument('--ignore-ssl-errors');add_argument('--ignore-certificate-errors')
    maximize browser window

Open URL In Headless
    [Documentation]  Test keyword is for opening the URL in the browser in headless mode, with specific options.
    [Arguments]  ${url}  ${browser}
    open browser  ${url}  ${browser}    options=add_argument('--ignore-ssl-errors');add_argument('--ignore-certificate-errors');add_argument('--no-sandbox');add_argument('--headless')
    Set Window Size  ${1366}  ${768}

Enter Username And Password
    [Documentation]  Test keyword is for entering the username and password on login form.
    [Arguments]  ${username}  ${password}
    input text  ${csm username id}  ${username}
    input password  ${csm password id}  ${password}

Click Sigin Button and Verify Button Disabled
    [Documentation]  This keyword is for entering the username and password on login form for Test-6373.
    click button    ${signin_button_id}
    Element Should Be Disabled  ${signin_button_id}

Click Sigin Button
    [Documentation]  This keyword is for entering the username and password on login form.
    Wait Until Element Is Visible  ${signin_button_id}  timeout=30
    click button    ${signin_button_id}
    Sleep  5s  #  Sigin take some initial time

Validate CSM Login Failure
    [Documentation]  Test keyword is for Validating login failure on CSM GUI.
    wait for page or element to load  2s
    Element Should Be Visible  ${CSM_LOGIN_FAIL_MSG_ID}
    ${csm_login_fail_msg}=  get text  ${csm login fail msg id}
    should be equal  ${csm_login_fail_msg}  ${LOGIN_FAILED_MESSAGE}
    [Return]  ${csm_login_fail_msg}

Validate CSM Login Success
    [Documentation]  This keyword is used to validate that user is logged in.
    [Arguments]  ${username}
    wait until element is visible  ${LOGGED_IN_USER_NAME_ID}  timeout=60
    ${csm_dashboard_text}=  get text  ${LOGGED_IN_USER_NAME_ID}
    should be equal  ${csm_dashboard_text}  ${username}
    [Return]  ${csm_dashboard_text}

CSM GUI Login with Incorrect Credentials
    [Documentation]  This keyword is used in Test-535 & Test-4026 to test incorrect credentials.
    [Arguments]  ${url}  ${browser}  ${headless}
    Run Keyword If  ${headless} == True  Open URL In Headless  ${url}  ${browser}
    ...  ELSE  Open URL  ${url}  ${browser}
    ${username}=  Generate New User Name
    ${password}=  Generate New Password
    Enter Username And Password  ${username}  ${password}
    Element Should Be Enabled  ${signin_button_id}
    Click Sigin Button
    Wait Until Element Is Enabled  ${signin_button_id}

CSM GUI Login and Verify Button Enabled Disabled with Incorrect Credentials
    [Documentation]  This keyword is used in Test-6373 for login button validation.
    [Arguments]  ${url}  ${browser}  ${headless}
    Run Keyword If  ${headless} == True  Open URL In Headless  ${url}  ${browser}
    ...  ELSE  Open URL  ${url}  ${browser}
    ${username}=  Generate New User Name
    ${password}=  Generate New Password
    Enter Username And Password  ${username}  ${password}
    Element Should Be Enabled  ${signin_button_id}
    Click Sigin Button and Verify Button Disabled
    Wait Until Element Is Enabled  ${signin_button_id}
    Page Should Contain Element  ${csm_login_fail_msg_id}

CSM GUI Login and Verify Button Enabled Disabled with Correct Credentials
    [Documentation]  This keyword is used in Test-6373 for login button validation.
    [Arguments]  ${url}  ${browser}  ${headless}  ${username}  ${password}
    Run Keyword If  ${headless} == True  Open URL In Headless  ${url}  ${browser}
    ...  ELSE  Open URL  ${url}  ${browser}
    Enter Username And Password  ${username}  ${password}
    Element Should Be Enabled  ${signin_button_id}
    Click Sigin Button and Verify Button Disabled
    sleep  5s
    Log To Console And Report  Waiting for receiving GUI response...

CSM GUI Login
    [Documentation]  This keyword is used to login to CSM GUI.
    [Arguments]  ${url}  ${browser}  ${headless}  ${username}  ${password}
    Run Keyword If  ${headless} == True  Open URL In Headless  ${url}  ${browser}
    ...  ELSE  Open URL  ${url}  ${browser}
    Enter Username And Password  ${username}  ${password}
    Click Sigin Button
    wait for page or element to load  2s
    ${check_first_time_login} =  Run Keyword And Return Status    Element Should Be Visible   ${CHANGE_PASSWORD_ID}
    Run Keyword If  '${check_first_time_login}'=='True'
    ...  Run Keywords
    ...  Change password on login   ${password}     ${password}
    ...  AND  Click on reset password
    Log To Console And Report  Waiting for receiving GUI response...

CSM GUI Logout
    [Documentation]  This keyword is used to logout of CSM GUI.
    click element  ${USER_DROPDOWN_XPATH}
    wait until element is visible  ${LOG_OUT_ID}  timeout=20
    click element  ${LOG_OUT_ID}
    wait until element is visible  ${CSM_USERNAME_ID}  timeout=30

Re-login
    [Documentation]  Functionality to Logout and login again
    [Arguments]  ${user_name}  ${password}  ${page}   ${Logout}=${True}
    Run Keyword If  '${Logout}' == 'True'  CSM GUI Logout
    wait for page or element to load
    Wait Until Element Is Visible  ${csm username id}  timeout=60
    Enter Username And Password  ${username}  ${password}
    Click Sigin Button
    wait for page or element to load
    ${check_first_time_login} =  Run Keyword And Return Status    Element Should Be Visible   ${CHANGE_PASSWORD_ID}
    Run Keyword If  ${check_first_time_login} == True
    ...  Run Keywords
    ...  Change password on login   ${password}     ${password}
    ...  AND  Click on reset password
    Navigate To Page  ${page}

Change password on login
    [Documentation]  Functionality to change password of cortx users for the first time login
    [Arguments]  ${password}  ${confirm_password}
    input password  ${CHANGE_PASSWORD_ID}  ${password}
    input password  ${CONFIRM_PASSWORD_ID}  ${confirm_password}

Click on reset password
    [Documentation]  This keyword is for click on reset password button.
    Wait Until Element Is Visible  ${PASSWORD_RESET_BUTTON_ID}  timeout=30
    click button    ${PASSWORD_RESET_BUTTON_ID}
    wait for page or element to load  2s
    click button  ${PASSWORD_CHANGE_SUCESS_BUTTON_ID}
    wait for page or element to load  #  Sigin take some initial time
