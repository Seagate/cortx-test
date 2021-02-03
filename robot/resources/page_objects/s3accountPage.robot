*** Settings ***
Resource  ../../resources/common/common.robot
Library     SeleniumLibrary
Variables  ../common/element_locators.py

*** Variables ***

*** Keywords ***

Check S3 Account Exists
    [Documentation]  This keyword is used to check S3 account exists.
    [Arguments]  ${S3_account_table}    ${expected_s3_account}
    wait until element is visible  ${${S3_account_table}}  timeout=10
    ${s3_account_table_data}=   Read Table Data   ${${S3_account_table}}
    List Should Contain Value      ${s3_account_table_data}     ${expected_s3_account}

Action on the table
    [Documentation]  This keyword is to check user can perform action on the user table.
    [Arguments]  ${USER_NAME}  ${ACTION_ELEMENT_XPATH}
    ${CSM_account_table_data}=   Action On The Table Element   ${${ACTION_ELEMENT_XPATH}}  ${USER_NAME}

Click on add new s3 account button
    [Documentation]  This keyword is to click on the add new s3 account.
    click button  ${ADD_S3_ACCOUNT_BUTTON_ID}

Click on create new S3 account button
    [Documentation]  This keyword is to click on the create new s3 account.
    click button  ${CREATE_S3_ACCOUNT_BUTTON_ID}

Click on download and close button
    [Documentation]  This keyword is to click on the downlaod and close button on s3 account.
    sleep  3s
    wait until element is visible  ${DOWNLOAD_AND_CLOSE_BUTTON_ID}  timeout=10
    click element  ${DOWNLOAD_AND_CLOSE_BUTTON_ID}

Click on calcle button on s3 account
    [Documentation]  This keyword is to click on the calcel button on s3 account.
    click button  ${CANCEL_S3_ACCOUNT_ID}

Click on edit s3 account option
    [Documentation]  This keyword is to click on edit s3 account option.
    wait until element is visible  ${EDIT_S3_ACCOUNT_OPTION_ID}  timeout=10
    click element  ${EDIT_S3_ACCOUNT_OPTION_ID}

Click on update s3 account button
    [Documentation]  This keyword is to click on edit s3 account option.
    wait until element is visible  ${UPDATE_S3_ACCOUNT_BTN_ID}  timeout=10
    click element  ${UPDATE_S3_ACCOUNT_BTN_ID}


Add data to create new S3 account
    [Documentation]  This keyword is to add data in s3 account form.
    [Arguments]  ${s3_account_name}  ${email_id}  ${password}  ${confirm_password}
    Input Text  ${S3_ACCOUNT_NAME_FIELD_ID}  ${s3_account_name}
    Input Text  ${S3_ACCOUNT_EMAIL_FIELD_ID}  ${email_id}
    Input Text  ${S3_ACCOUNT_PASSWORD_FIELD_ID}  ${password}
    Input Text  ${S3_ACCOUNT_CONFIRM_PASSWORD_FIELD_ID}  ${confirm_password}

Create S3 account
    [Documentation]  This keyword is to create new s3 account.
    Click on add new s3 account button
    ${S3_account_name}=  Generate New User Name
    ${email}=  Generate New User Email
    ${password}=  Generate New Password
    log to console and report  S3 account user name is ${S3_account_name}
    log to console and report  email-id is ${email}
    log to console and report  password is ${password}
    Add data to create new S3 account  ${S3_account_name}  ${email}  ${password}  ${password}
    Click on create new S3 account button
    Click on download and close button
    [Return]    ${S3_account_name}  ${email}  ${password}

Delete S3 Account
    [Documentation]  This keyword is to delete s3 account.
    [Arguments]  ${s3_account_name}  ${password}  ${already_logged_in}=False
    ${user_logged_in}=  Convert To Boolean  ${already_logged_in}
    Run Keyword If  ${user_logged_in}  log to console and report  user already loggedin
    ...  ELSE
    ...  Run Keywords
    ...  Enter Username And Password    ${s3_account_name}  ${password}
    ...  AND
    ...  Click Sigin Button
    Validate CSM Login Success  ${s3_account_name}
    log to console and report   deleting S3 account ${s3_account_name}
    wait until element is visible  ${DELETE_S3_ACCOUNT_ID}  timeout=10
    sleep  2s
    click element  ${DELETE_S3_ACCOUNT_ID}
    sleep  2s
    click element  ${CONFIRM_DELETE_S3_ACCOUNT_ID}
    wait until element is visible  ${csm username id}  timeout=10
    log to console and report  S3 account Deleted.

Check create S3 account button disabled
    [Documentation]  This keyword returns State of create S3 account button.
    sleep  2s
    ${state_of_create_s3_account}=  Get Element Attribute  ${CREATE_S3_ACCOUNT_BUTTON_ID}  disabled
    Run Keyword If  ${${state_of_create_s3_account}} == True  log to console and report  create S3 account button is disabled.

Check s3 account form is opened
    [Documentation]  This keyword checks whether s3 account form is opened or not.
    wait until element is visible  ${S3_ACCOUNT_NAME_FIELD_ID}  timeout=10

check cancel s3 account form feature
    [Documentation]  This keyword checks whether s3 account form is getting closed by clicking on the calcle button.
    Click on add new s3 account button
    Click on calcle button on s3 account
    sleep  2s
    Element Should Not Be Visible  ${S3_ACCOUNT_NAME_FIELD_ID}

Verify edit s3 account form getting opened
    [Documentation]  This keyword to verify that edit s3 account form is getting opened.
    Click on edit s3 account option
    wait until element is visible  ${UPDATE_S3_ACCOUNT_PASSWORD_FIELD_ID}  timeout=10
    wait until element is visible  ${UPDATE_S3_ACCOUNT_CONFIRM_PASSWORD_FIELD_ID}  timeout=10


Verify update s3 account button remains disabled
    [Documentation]  This keyword is to chceck the update S3 account button remains disabled when there is no data.
    Click on edit s3 account option
    sleep  2s
    ${state_of_update_s3_account}=  Get Element Attribute  ${UPDATE_S3_ACCOUNT_BTN_ID}  disabled
    Run Keyword If  ${${state_of_update_s3_account}} == True  log to console and report  create S3 account button is disabled.

Edit S3 account
    [Documentation]  This keyword is to edit s3 account.
    [Arguments]  ${s3_account_name}  ${password}  ${confirm_password}
    log to console and report   editing S3 account ${s3_account_name}
    Click on edit s3 account option
    update s3 account password  ${password}  ${confirm_password}
    Click on update s3 account button
    sleep  5s
    wait until element is visible  ${LOG_OUT_ID}  timeout=20
    CSM GUI Logout
    Run Keywords
    ...  Enter Username And Password    ${s3_account_name}  ${password}
    ...  AND
    ...  Click Sigin Button
    Validate CSM Login Success  ${s3_account_name}

update s3 account password
    [Documentation]  This keyword is to update data in s3 account.
    [Arguments]  ${password}  ${confirm_password}
    log to console and report   updating S3 account password
    input text  ${UPDATE_S3_ACCOUNT_PASSWORD_FIELD_ID}  ${password}
    input text  ${UPDATE_S3_ACCOUNT_CONFIRM_PASSWORD_FIELD_ID}  ${confirm_password}

Verify update s3 account accepts only valid password
    [Documentation]  This keyword is validate password fields on update s3 account form along with error messages.
    [Arguments]  ${invalid_password}  ${confirm_password}  ${check_blank_password}=False  ${invalid_confirm_password}=False
    ${check_blank_password}=  Convert To Boolean  ${check_blank_password}
    ${invalid_confirm_password}=  Convert To Boolean  ${invalid_confirm_password}
    Click on edit s3 account option
    Log To Console And Report   ${invalid_password}
    Log To Console And Report   ${confirm_password}
    update s3 account password  ${invalid_password}  ${confirm_password}
    Run Keyword If  ${check_blank_password}
    ...  Verify message  PASSWORD_REQUIRED_MSG_ID  ${PASSWORD_REQUIRED_MESSAGE}
    ...  ELSE IF    ${invalid_confirm_password}  Verify message  CONFIRM_PASSWORD_ERROR_MSG_ID  ${INVALID_S3_CONFIRM_PASSWORD_MESSAGE}
    ...  ELSE  Verify message  INVALID_S3_ACCOUNT_PASSWORD_MSG_ID  ${INVALID_S3_PASSWORD_MESSAGE}
    Verify update s3 account button remains disabled

Verify Presence of Stats And Alerts
    [Documentation]  Verify Presence of Edit And Delete Button on S3account
    Page Should Contain Element  ${CSM_STATS_CHART_ID}
    Page Should Contain Element  ${DASHBOARD_ALERT_SECTION_ID}
