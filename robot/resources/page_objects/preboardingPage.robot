*** Settings ***
Resource  ../common/common.robot
Resource  ./loginPage.robot
Library     SeleniumLibrary
Variables  ../common/element_locators.py

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

Validate ELUA Success
    [Documentation]  This keyword is used to validate that Preboarding page is accessable.
    sleep   1s
    Click Accept Button
    Page Should Contain Button  ${license_cancle_button_id}
    Page Should Contain Image  ${license_cancle_image_id}
    Page Should Contain Button  ${license_accept_button_id}
    Page Should Contain Element  ${license_title_id}
    Page Should Contain Element  ${license_data_id}
    Click LicenseCancle Button
    Click Accept Button
    Page Should Contain Button  ${license_cancle_button_id}
    Page Should Contain Image  ${license_cancle_image_id}
    Page Should Contain Button  ${license_accept_button_id}
    Page Should Contain Element  ${license_title_id}
    Page Should Contain Element  ${license_data_id}
    Click LicenseCancle Image
    Click Accept Button
    Click License Button

Preboarding
    [Documentation]  This keyword is used to login to CSM GUI.
    [Arguments]  ${url}  ${browser}  ${headless}
    Run Keyword If  ${headless} == True  Open URL In Headless  ${url}  ${browser}
    ...  ELSE  Open URL  ${url}preboarding/welcome  ${browser}
    Page Should Contain Button  ${welcome_start_button_id}
    Click Start Button
    sleep   3s
    Page Should Contain Button  ${elua_button_id}
    sleep   3s
    Log To Console And Report  Waiting for receiving GUI response...
