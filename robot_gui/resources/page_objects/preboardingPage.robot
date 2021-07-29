*** Settings ***
Library    SeleniumLibrary
Resource   ${RESOURCES}/resources/page_objects/loginPage.robot
Resource   ${RESOURCES}/resources/common/common.robot
Variables  ${RESOURCES}/resources/common/element_locators.py

*** Keywords ***

Click Start Button
    [Documentation]  On preboarding/welcome page, click on Start Button
    click button    ${welcome_start_button_id}

Click Accept Button
    [Documentation]  On preboarding/gdpr page, click on "Accept Terms & Condition" Button
    click Element    ${elua_button_id}

Click License Button
    [Documentation]  On EULA Pop Up, click on Accept Button
    click button    ${license_accept_button_id}

Click LicenseCancle Button
    [Documentation]  On EULA Pop Up, click on Cancel Button
    wait until element is visible  ${license_cancle_button_id}  timeout=20
    click button    ${license_cancle_button_id}

Click LicenseCancle Image
    [Documentation]  On EULA Pop Up, click on 'X' icon to close
    click image    ${license_cancle_image_id}

Verify Presence of Elements on EULA Page
    [Documentation]  On EULA, Verify Presence of different elements
    Page Should Contain Button  ${license_cancle_button_id}
    Page Should Contain Image  ${license_cancle_image_id}
    Page Should Contain Button  ${license_accept_button_id}
    Page Should Contain Element  ${license_title_id}
    Page Should Contain Element  ${license_data_id}
    Capture Element Screenshot  ${license_data_id}  eula_data.png

Validate ELUA Success
    [Documentation]  This keyword is used to validate that Preboarding page is accessible.
    sleep  1s
    Capture Page Screenshot  preboarding.png
    Click Accept Button
    sleep  1s
    Capture Page Screenshot  eula.png
    Verify Presence of Elements on EULA Page
    Click LicenseCancle Button
    Click Accept Button
    Verify Presence of Elements on EULA Page
    #Click LicenseCancle Image
    Click LicenseCancle Button
    Click Accept Button
    sleep  1s
    Click License Button
    sleep  1s
    Capture Page Screenshot  admin_config.png

Preboarding
    [Documentation]  This keyword is used to login to CSM GUI.
    [Arguments]  ${url}  ${browser}  ${headless}
    Run Keyword If  ${headless} == True  Open URL In Headless  ${url}preboarding/welcome  ${browser}
    ...  ELSE  Open URL  ${url}preboarding/welcome  ${browser}
    wait for page or element to load  3s
    Page Should Contain Button  ${welcome_start_button_id}
    Click Start Button
    wait for page or element to load  3s
    Page Should Contain Button  ${elua_button_id}
    wait for page or element to load  3s
    Log To Console And Report  Waiting for receiving GUI response...

Validate EULA Data
    [Documentation]  This keyword will validate the content of the EULA
    wait until element is visible  ${elua_button_id}  timeout=20
    Click Element  ${elua_button_id}
    ${data}=  get text  ${EULA_CONTENT_MSG_XPATH}
    Log To Console And Report  ${data}
    Should Not Be Empty  ${data}

admin user preboarding
   [Documentation]  This keyword will change the password for admin user for first time login.
   [Arguments]  ${username}  ${password}  ${new_password}=${password}
   Click Accept Button
   Click License Button
   Enter Username And Password  ${username}  ${password}
   Click Sigin Button
   wait for page or element to load  2s
   ${check_first_time_login} =  Run Keyword And Return Status    Element Should Be Visible   ${CHANGE_PASSWORD_ID}
   Log To Console And Report  ${new_password}
   Run Keyword If  '${check_first_time_login}'=='True'
   ...  Run Keywords
   ...  Change password on login   ${new_password}     ${new_password}
   ...  AND  Click on reset password
   Log To Console And Report  Waiting for receiving GUI response...
   Page Should Contain Element  ${SYSTEM_NAME_TEXT_ID}
   Re-login   ${username}  ${new_password}  DASHBOARD_MENU_ID


