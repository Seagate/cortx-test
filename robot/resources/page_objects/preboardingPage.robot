*** Settings ***
Library    SeleniumLibrary
Resource   ${EXECDIR}/resources/page_objects/loginPage.robot
Resource   ${EXECDIR}/resources/common/common.robot
Variables  ${EXECDIR}/resources/common/element_locators.py

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
    [Documentation]  On EULA Pop Up, click on Cancle Button
    click button    ${license_cancle_button_id}

Click LicenseCancle Image
    [Documentation]  On EULA Pop Up, click on 'X' icon to close
    click image    ${license_cancle_image_id}

check admin user already exists
    [Documentation]  This key word checks that admin user already exists
    Verify message  ADMIN_USER_ALREADY_EXISTS_ID  ${ADMIN_USER_ALREADY_EXISTS_MESSAGE}
    log to console and report  Admin user already exists

Verify Presence of Elements on EULA Page
    [Documentation]  On EULA, Verify Presence of diffren emelnets
    Page Should Contain Button  ${license_cancle_button_id}
    Page Should Contain Image  ${license_cancle_image_id}
    Page Should Contain Button  ${license_accept_button_id}
    Page Should Contain Element  ${license_title_id}
    Page Should Contain Element  ${license_data_id}
    Capture Element Screenshot  ${license_data_id}  eula_data.png

Validate ELUA Success
    [Documentation]  This keyword is used to validate that Preboarding page is accessable.
    sleep  1s
    Capture Page Screenshot  preboarding.png
    Click Accept Button
    sleep  1s
    Capture Page Screenshot  eula.png
    Verify Presence of Elements on EULA Page
    Click LicenseCancle Button
    Click Accept Button
    Verify Presence of Elements on EULA Page
    Click LicenseCancle Image
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
    Page Should Contain Button  ${welcome_start_button_id}
    Click Start Button
    sleep  3s
    Page Should Contain Button  ${elua_button_id}
    sleep  3s
    Log To Console And Report  Waiting for receiving GUI response...

navigate to csm admin creation page
    [Documentation]  This keyword is for navigavagating to creationg CSM Admin User page.
    [Arguments]  ${url}  ${browser}  ${headless}
    Preboarding  ${url}  ${browser}  ${headless}
    Click Accept Button
    Click LicenseCancle Button
    Click Accept Button
    wait for page or element to load  2s
    Click License Button
    wait for page or element to load  2s

create csm admin user
    [Documentation]  This keyword is for creationg CSM Admin User.
    [Arguments]  ${username}  ${password}
    log to console and report  ${EMAIL_DOMAIN}
    log to console and report  ${username}
    ${admin_email_id} =  Catenate  SEPARATOR=  ${username}  ${EMAIL_DOMAIN}
    input text  ${ADMIN_USER_FIELD_ID}  ${username}
    input text  ${ADMIN_USER_EMAIL_ID_FIELD_ID}  ${admin_email_id}
    input text  ${ADMIN_PASSWORD_FIELD_ID}  ${password}
    input text  ${ADMIN_CONFIRM_PASSWORD_FIELD_ID}  ${password}
    click button  ${APPLY_AND_CONTINUE_BUTTON_ID}


check csm admin user status
    [Documentation]  This keyword is to check CSM Admin User status.
    [Arguments]  ${url}  ${browser}  ${headless}  ${username}  ${password}
    navigate to csm admin creation page  ${url}  ${browser}  ${headless}
    create csm admin user  ${username}  ${password}
    wait for page or element to load  20s
    ${current_url}=   Get Location
    ${sucess_url_check}=   Catenate  SEPARATOR=  ${url}  preboarding/login
    Run Keyword If  "${current_url}" == "${sucess_url_check}"
    ...  Log To Console And Report  Admin user created
    ...  ELSE IF  "${current_url}" == "${url}preboarding/adminuser"  check admin user already exists
    ...  ELSE  Log To Console And Report  Admin user created Failed
