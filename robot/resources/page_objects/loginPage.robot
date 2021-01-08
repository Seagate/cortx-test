*** Settings ***
Resource  ../common/common.robot
Library     SeleniumLibrary
Variables  ../common/element_locators.py

*** Variables ***

*** Keywords ***
Open URL
    [Arguments]  ${url}  ${browser}
    open browser  ${url}  ${browser}    options=add_argument('--ignore-ssl-errors');add_argument('--ignore-certificate-errors')
    maximize browser window

Open URL In Headless
    [Arguments]  ${url}  ${browser}
    open browser  ${url}  ${browser}    options=add_argument('--ignore-ssl-errors');add_argument('--ignore-certificate-errors');add_argument('--no-sandbox');add_argument('--headless')
    maximize browser window


Enter Username And Password
    [Arguments]  ${username}  ${password}
    input text  ${csm username id}  ${username}
    input password  ${csm password id}  ${password}

Click Sigin Button
    click button    ${signin_button_id}

Validate CSM Login Failure
    ${csm_login_fail_msg}=  get text  ${csm login fail msg id}
    should be equal  ${csm_login_fail_msg} ${LOGIN_FAILED_MSG}
    [Return]  ${csm_login_fail_msg}

Validate CSM Login Success
    [Documentation]  This keyword is used to validate that user is loggied in.
    [Arguments]  ${username}
    wait until element is visible  ${LOGGED_IN_USER_NAME_ID}  timeout=60
    ${csm_dashboard_text}=  get text  ${LOGGED_IN_USER_NAME_ID}
    should be equal  ${csm_dashboard_text}  ${username}
    [Return]  ${csm_dashboard_text}

CSM GUI Login
    [Documentation]  This keyword is used to login to CSM GUI.
    [Arguments]  ${url}  ${browser}  ${headless}  ${username}  ${password}
    Run Keyword If  ${headless} == True  Open URL In Headless  ${url}  ${browser}
    ...  ELSE  Open URL  ${url}  ${browser}
    Enter Username And Password  ${username}  ${password}
    Click Sigin Button
    sleep   5s
    Log To Console And Report  Waiting for receiving GUI responce...







