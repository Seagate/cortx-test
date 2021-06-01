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

check admin user already exists
    [Documentation]  This key word checks that admin user already exists
    Verify message  ADMIN_USER_ALREADY_EXISTS_ID  ${ADMIN_USER_ALREADY_EXISTS_MESSAGE}
    log to console and report  Admin user already exists

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
    Page Should Contain Button  ${welcome_start_button_id}
    Click Start Button
    sleep  3s
    Page Should Contain Button  ${elua_button_id}
    sleep  3s
    Log To Console And Report  Waiting for receiving GUI response...

navigate to csm admin creation page
    [Documentation]  This keyword is for navigating to creating CSM Admin User page.
    [Arguments]  ${url}  ${browser}  ${headless}
    Preboarding  ${url}  ${browser}  ${headless}
    Click Accept Button
    Click LicenseCancle Button
    Click Accept Button
    wait for page or element to load  2s
    Click License Button
    wait for page or element to load  2s

create csm admin user
    [Documentation]  This keyword is for creating CSM Admin User.
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

Validate EULA Data
    [Documentation]  This keyword will validate the content of the EULA
    wait until element is visible  ${elua_button_id}  timeout=20
    Click Element  ${elua_button_id}
    ${data}=  get text  ${EULA_CONTENT_MSG_XPATH}
    Log To Console And Report  ${data}
    Should Not Be Empty  ${data}

Verify User Has Naviagted to Admin User Create Page
    [Documentation]  This keyword will verify user is in admin page
    Validate ELUA Success
    Page Should Contain Element  ${ADMIN_USER_FIELD_ID}
    Page Should Contain Element  ${ADMIN_USER_EMAIL_ID_FIELD_ID}
    Page Should Contain Element  ${ADMIN_PASSWORD_FIELD_ID}
    Page Should Contain Element  ${ADMIN_CONFIRM_PASSWORD_FIELD_ID}
    Page Should Contain Element  ${APPLY_AND_CONTINUE_BUTTON_ID}

Verify User Has Not Naviagted to Admin User Create Page
    [Documentation]  This keyword will verify user is in EULA page
    wait until element is visible  ${elua_button_id}  timeout=20
    Click Element  ${elua_button_id}
    Click LicenseCancle Button
    Page Should Contain Element  ${elua_button_id}

Verify Miss-Match Password Error Message
    [Documentation]  This keyword will verify missmatch error msg for Admin user
    ${password}=  Generate New Password
    wait until element is visible  ${ADMIN_PASSWORD_FIELD_ID}  timeout=20
    Input Text  ${ADMIN_PASSWORD_FIELD_ID}  ${password}
    ${new_passowrd}=  CATENATE  ${password}  new
    wait until element is visible  ${ADMIN_CONFIRM_PASSWORD_FIELD_ID}  timeout=20
    Input Text  ${ADMIN_CONFIRM_PASSWORD_FIELD_ID}  ${new_passowrd}
    ${value}=  get text  ${ADMIN_USER_MISSMATCH_PASSWORD_MSG_ID}
    Log To Console And Report  ${value}
    Should be Equal  ${MISSMATCH_PASSWORD_MESSAGE}  ${value}

Validate Password for Admin User
    [Documentation]  Functionality to validate password and error msg
    FOR    ${value}    IN    @{INVALID_PASSWORDS_LIST}
      Log To Console And Report  Inserting values ${value}
      wait until element is visible  ${ADMIN_PASSWORD_FIELD_ID}  timeout=20
      Input Text  ${ADMIN_PASSWORD_FIELD_ID}  ${value}
      Page Should Contain Element  ${ADMIN_USER_INVALID_PASSWORD_MSG_ID}
      ${text_msg}=  get text  ${ADMIN_USER_INVALID_PASSWORD_MSG_ID}
      should be equal  ${text_msg}  ${invalid password msg}
      Reload Page
    END

Validate Usernames for Admin User
    [Documentation]  Functionality to validate username and error msg
    FOR    ${value}    IN    @{INVALID_LOCAL_USER}
      Log To Console And Report  Inserting values ${value}
      wait until element is visible  ${ADMIN_USER_FIELD_ID}  timeout=20
      Input Text  ${ADMIN_USER_FIELD_ID}  ${value}
      Page Should Contain Element  ${ADMIN_USER_INVALID_USERNAME_MSG_ID}
      ${text_msg}=  get text  ${ADMIN_USER_INVALID_USERNAME_MSG_ID}
      should be equal  ${text_msg}  ${INVALID_USER_TYPE_MESSAGE}
      Reload Page
    END

Verify fields for Admin User creation
    [Documentation]  This keyword will verify username, password, email
    ...  and confirm password fields
    ${validate_data}=  Create Dictionary  ${ADMIN_USER_FIELD_ID}=text
    ...  ${ADMIN_USER_EMAIL_ID_FIELD_ID}=email
    ...  ${ADMIN_PASSWORD_FIELD_ID}=password
    ...  ${ADMIN_CONFIRM_PASSWORD_FIELD_ID}=password
    FOR    ${key}    IN    @{validate_data.keys()}
      ${type}=  Get Element Attribute  ${key}  type
      Log To Console And Report  ${type}
      Should be equal  ${type}  ${validate_data['${key}']}
    END

Verify mandatory fields for Admin User
    [Documentation]  This keyword will verify all mandatory fields have asterisk symbol(*) mark
    ${mandatory_fields}=  Create List  ${ADMIN_USER_USERNAME_LABEL_ID}
    ...  ${ADMIN_USER_PASSWORD_LABEL_ID}
    ...  ${ADMIN_USER_CONFIRM_PASSWORD_LABEL_ID}
    FOR    ${value}    IN    @{mandatory_fields}
      ${text}=  Get Text  ${value}
      Log To Console And Report  ${text}
      Should Contain  ${text}  *
    END

Verify Admin User Creation Page Should have tooltip
    [Documentation]  This keyword will verify Admin user page must have tooltip
    wait for page or element to load  2s
    Click Element  ${ADMIN_USER_TOOLTIP_ICON_ID}
    Page Should Contain Element  ${ADMIN_USER_PAGE_TOOLTIP_ID}
    Click Element  ${ADMIN_USER_PASSWORD_TOOLTIP_ICON_ID}
    Page Should Contain Element  ${ADMIN_USER_PAGE_TOOLTIP_ID}

Validate Admin User Tooltip
    [Documentation]  This keyword will verify Admin user tooltip must have correct info
    wait until element is visible  ${ADMIN_USER_FIELD_ID}  timeout=20
    Click Element  ${ADMIN_USER_TOOLTIP_ICON_ID}
    Verify message  ADMIN_USER_PAGE_TOOLTIP_ID  ${ADMIN_USER_TOOLTIP_MSG_ID}

