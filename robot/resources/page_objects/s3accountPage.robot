*** Settings ***
Library    SeleniumLibrary
Resource   ${RESOURCES}/resources/page_objects/loginPage.robot
Resource   ${RESOURCES}/resources/page_objects/userSettingsLocalPage.robot
Resource   ${RESOURCES}/resources/common/common.robot
Variables  ${RESOURCES}/resources/common/element_locators.py

*** Keywords ***

Check S3 Account Exists
    [Documentation]  This keyword is used to check S3 account exists.
    [Arguments]  ${S3_account_table}    ${expected_s3_account}
    wait until element is visible  ${SELECT_FROM_PAGINATION_XPATH}  timeout=30
    click element  ${SELECT_FROM_PAGINATION_XPATH}
    click element  ${SELECT_ALL_RECORDS_FROM_PAGINATION_XPATH}
    wait until element is visible  ${${S3_account_table}}  timeout=30
    ${s3_account_table_data}=   Read Table Data   ${${S3_account_table}}
    List Should Contain Value      ${s3_account_table_data}     ${expected_s3_account}

Action on the table
    [Documentation]  This keyword is to check user can perform action on the user table.
    [Arguments]  ${USER_NAME}  ${ACTION_ELEMENT_XPATH}
    ${CSM_account_table_data}=   Action On The Table Element   ${${ACTION_ELEMENT_XPATH}}  ${USER_NAME}

Click on add new s3 account button
    [Documentation]  This keyword is to click on the add new s3 account.
    wait until element is visible  ${ADD_S3_ACCOUNT_BUTTON_ID}  timeout=30
    Execute JavaScript    window.scrollTo(200,0)
    click button  ${ADD_S3_ACCOUNT_BUTTON_ID}

Click on create new S3 account button
    [Documentation]  This keyword is to click on the create new s3 account.
    click button  ${CREATE_S3_ACCOUNT_BUTTON_ID}

Click on download and close button
    [Documentation]  This keyword is to click on the download and close button on s3 account.
    sleep  3s
    wait until element is visible  ${DOWNLOAD_AND_CLOSE_BUTTON_ID}  timeout=30
    click element  ${DOWNLOAD_AND_CLOSE_BUTTON_ID}

Click on cancel button on s3 account
    [Documentation]  This keyword is to click on the cancel button on s3 account.
    click button  ${CANCEL_S3_ACCOUNT_ID}

Click on edit s3 account option
    [Documentation]  This keyword is to click on edit s3 account option.
    wait until element is visible  ${EDIT_S3_ACCOUNT_OPTION_ID}  timeout=60
    click element  ${EDIT_S3_ACCOUNT_OPTION_ID}

Click on update s3 account button
    [Documentation]  This keyword is to click on update s3 account button
    wait for page or element to load
    ${status}=  Run Keyword And Return Status  Element Should Be Visible  ${UPDATE_S3_ACCOUNT_BUTTON_ID}
    Run Keyword If  '${status}' == 'True'  click element  ${UPDATE_S3_ACCOUNT_BUTTON_ID}
    ${status}=  Run Keyword And Return Status  Element Should Be Visible  ${S3_ACCOUNT_RESET_PASSWORD_BUTTON_ID}
    Run Keyword If  '${status}' == 'True'  click element  ${S3_ACCOUNT_RESET_PASSWORD_BUTTON_ID}
    wait for page or element to load
    ${status}=  Run Keyword And Return Status  Element Should Be Visible  ${S3_ACCOUNT_SUCCESS_MESSAGE_BUTTON_ID}
    Run Keyword If  '${status}' == 'True'  click element  ${S3_ACCOUNT_SUCCESS_MESSAGE_BUTTON_ID}


Click on add new access key button
    [Documentation]  This keyword is to click on the add new access key button.
    Reload Page
    wait for page or element to load
    wait until element is visible  ${ADD_S3_ACCOUNT_ACCESS_KEY_ID}  timeout=30
    click element  ${ADD_S3_ACCOUNT_ACCESS_KEY_ID}

Click on download and close button for new access key
    [Documentation]  This keyword is to click on download and close button for new access key
    #Reload Page
    wait for page or element to load
    wait until element is visible  ${ACCESS_KEY_DOWNLOAD_AND_CLOSE_BUTTON_ID}  timeout=30
    click element  ${ACCESS_KEY_DOWNLOAD_AND_CLOSE_BUTTON_ID}

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
    sleep  1s
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
    Navigate To Page    S3_ACCOUNTS_TAB_ID
    Validate CSM Login Success  ${s3_account_name}
    log to console and report   deleting S3 account ${s3_account_name}
    wait until element is visible  ${DELETE_S3_ACCOUNT_ID}  timeout=30
    sleep  2s
    click element  ${DELETE_S3_ACCOUNT_ID}
    sleep  2s
    click element  ${CONFIRM_DELETE_S3_ACCOUNT_ID}
    wait until element is visible  ${csm username id}  timeout=30
    log to console and report  S3 account Deleted.

Check create S3 account button disabled
    [Documentation]  This keyword returns State of create S3 account button.
    sleep  2s
    ${state_of_create_s3_account}=  Get Element Attribute  ${CREATE_S3_ACCOUNT_BUTTON_ID}  disabled
    Run Keyword If  ${${state_of_create_s3_account}} == True  log to console and report  create S3 account button is disabled.

Check s3 account form is opened
    [Documentation]  This keyword checks whether s3 account form is opened or not.
    wait until element is visible  ${S3_ACCOUNT_NAME_FIELD_ID}  timeout=30

check cancel s3 account form feature
    [Documentation]  This keyword checks whether s3 account form is getting closed by clicking on the cancel button.
    Click on add new s3 account button
    Click on cancel button on s3 account
    sleep  2s
    Element Should Not Be Visible  ${S3_ACCOUNT_NAME_FIELD_ID}

Verify edit s3 account form getting opened
    [Documentation]  This keyword to verify that edit s3 account form is getting opened.
    Click on edit s3 account option
    wait until element is visible  ${UPDATE_S3_ACCOUNT_PASSWORD_FIELD_ID}  timeout=30
    wait until element is visible  ${UPDATE_S3_ACCOUNT_CONFIRM_PASSWORD_FIELD_ID}  timeout=30


Verify update s3 account button remains disabled
    [Documentation]  This keyword is to chceck the update S3 account button remains disabled when there is no data.
    Click on edit s3 account option
    sleep  2s
    ${state_of_update_s3_account}=  Get Element Attribute  ${UPDATE_S3_ACCOUNT_BUTTON_ID}  disabled
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
    wait for page or element to load
    ${status}=  Run Keyword And Return Status  Element Should Be Visible  ${UPDATE_S3_ACCOUNT_PASSWORD_FIELD_ID}
    Run Keyword If  '${status}' == 'True'  input text  ${UPDATE_S3_ACCOUNT_PASSWORD_FIELD_ID}  ${password}
    ${status}=  Run Keyword And Return Status  Element Should Be Visible  ${S3_ACCOUNT_RESET_NEW_PASSWORD_ID}
    Run Keyword If  '${status}' == 'True'  input text  ${S3_ACCOUNT_RESET_NEW_PASSWORD_ID}  ${password}
    ${status}=  Run Keyword And Return Status  Element Should Be Visible  ${UPDATE_S3_ACCOUNT_CONFIRM_PASSWORD_FIELD_ID}
    Run Keyword If  '${status}' == 'True'  input text  ${UPDATE_S3_ACCOUNT_CONFIRM_PASSWORD_FIELD_ID}  ${confirm_password}
    ${status}=  Run Keyword And Return Status  Element Should Be Visible  ${S3_ACCOUNT_RESET_CONFIRM_PASSWORD_ID}
    Run Keyword If  '${status}' == 'True'  input text  ${S3_ACCOUNT_RESET_CONFIRM_PASSWORD_ID}  ${confirm_password}

Reset Password S3 Account
    [Documentation]  Functionality to Reset S3 accounts Password
    [Arguments]  ${user_name}
    Log To Console And Report  Resetting password for S3 accounts ${user_name}
    Action On The Table Element  ${S3_ACCOUNT_RESET_PASSWORD_XPATH}  ${user_name}
    Sleep  5s
    wait until element is visible  ${S3_ACCOUNT_RESET_NEW_PASSWORD_ID}  timeout=60
    ${new_password} =  Generate New Password
    input text  ${S3_ACCOUNT_RESET_NEW_PASSWORD_ID}  ${new_password}
    input text  ${S3_ACCOUNT_RESET_CONFIRM_PASSWORD_ID}  ${new_password}
    wait until element is visible  ${S3_ACCOUNT_RESET_PASSWORD_BUTTON_ID}  timeout=60
    Click element  ${S3_ACCOUNT_RESET_PASSWORD_BUTTON_ID}
    Sleep  5s
    wait until element is visible  ${S3_ACCOUNT_SUCCESS_MESSAGE_ID}  timeout=60
    Sleep  2s
    Click element  ${S3_ACCOUNT_SUCCESS_MESSAGE_BUTTON_ID}

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

Verify Presence of Edit And Delete
    [Documentation]  Verify Presence of Edit And Delete Button on S3account
    Page Should Contain Element  ${EDIT_S3_ACCOUNT_OPTION_ID}
    Page Should Contain Element  ${DELETE_S3_ACCOUNT_ID}

Verify unique username for csm and s3 account
    [Documentation]  This keyword verify that s3 account user name is unique and can not be same as csm user.
    ${user_name}=  Generate New User Name
    ${email}=  Generate New User Email
    ${new_password}=  Generate New Password
    Navigate To Page  MANAGE_MENU_ID
    Create New CSM User  ${user_name}  ${new_password}  monitor
    Click On Confirm Button
    wait for page or element to load
    Navigate To Page   S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    Click on add new s3 account button
    Add data to create new S3 account  ${user_name}  ${email}  ${new_password}  ${new_password}
    Click on create new S3 account button
    wait for page or element to load
    Verify message  S3_ACCOUNT_NAME_SAME_AS_CSM_USER_ID  ${S3_ACCOUNT_NAME_SAME_AS_CSM_USER_MESSAGE}
    click element  ${CLOSE_ALERT_BOX_FOR_DUPLICATE_USER_ID}
    Reload Page
    Delete CSM User  ${user_name}

verify the table headers for s3 account access key
    [Documentation]  This keyword verify the table headers for s3 account access key table.
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    wait for page or element to load
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    wait for page or element to load
    Re-login  ${S3_account_name}  ${password}  S3_ACCOUNTS_TAB_ID
    wait until element is visible  ${ACCESS_KEY_TABLE_HEADERS_XPATH}  timeout=30
    ${access_key_table_headers} =  Read Table Data   ${ACCESS_KEY_TABLE_HEADERS_XPATH}
    log to console and report  ${access_key_table_headers}
    ${expected_headers} =	Create List  ${S3_TABLE_HEADER_ACCOUNTNAME}  ${S3_TABLE_HEADER_SECRET_KEY}  ${S3_TABLE_HEADER_ACTION}
    log to console and report  ${expected_headers}
    Lists Should Be Equal  ${access_key_table_headers}  ${expected_headers}
    Delete S3 Account  ${S3_account_name}  ${password}  True

generate new access key
     [Documentation]  This keyword generate new access key.
     Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
     wait for page or element to load
     ${S3_account_name}  ${email}  ${password} =  Create S3 account
     wait for page or element to load
     Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
     wait for page or element to load
     Re-login  ${S3_account_name}  ${password}  S3_ACCOUNTS_TAB_ID
     Click on add new access key button
     [Return]  ${S3_account_name}  ${password}

verify new access key is getting added
    [Documentation]  This keyword verify that new access key is getting added.
    ${S3_account_name}  ${password} =  generate new access key
    Verify message  ACCESS_KEY_GENERATE_MEG_XPATH  ${ACCESS_KEY_GENERATED_MESSAGE}
    Click on download and close button for new access key
    sleep  2s
    Delete S3 Account  ${S3_account_name}  ${password}  True

get new access key
     [Documentation]  This keyword get the newly generated access key.
     wait until element is visible  ${NEW_ACCESS_KEY_TABLE_XPATH}  timeout=30
     ${new_access_key_data} =  Read Table Data   ${NEW_ACCESS_KEY_TABLE_XPATH}
     log to console and report  ${new_access_key_data}
     ${new_access_key} =  Get From List  ${new_access_key_data}  1
     log to console and report  ${new_access_key}
     [Return]   ${new_access_key}

get access key table data
     [Documentation]  This keyword get data from access key table
     wait until element is visible  ${ACCESS_KEY_TABLE_DATA_XPATH}  timeout=30
     ${access_key_table_data} =  Read Table Data   ${ACCESS_KEY_TABLE_DATA_XPATH}
     log to console and report  ${access_key_table_data}
     [Return]   ${access_key_table_data}

verify delete access key
     [Documentation]  This keyword deletes and verify access key.
     ${S3_account_name}  ${password} =  generate new access key
     ${new_access_key} =  get new access key
     Click on download and close button for new access key
     Action On The Table Element  ${DELETE_ACCESS_KEY_ID}  ${new_access_key}
     click button  ${CONFIRM_DELET_ACCESS_KEY_ID}
     sleep  2s
     ${access_key_table_data}=  get access key table data
     List Should Not Contain Value  ${access_key_table_data}  ${new_access_key}
     sleep  2s
     Delete S3 Account  ${S3_account_name}  ${password}  True

verify access key table data
     [Documentation]  This keyword verify data from access key table.
     ${S3_account_name}  ${password} =  generate new access key
     ${new_access_key} =  get new access key
     Click on download and close button for new access key
     ${expected_data} =	Create List  ${new_access_key}  XXXX  ${SPACE*0}
     log to console and report  ${expected_data}
     ${data_from_access_key_table} =  get access key table data
     log to console and report  ${data_from_access_key_table}
     List Should Contain Sub List  ${data_from_access_key_table}  ${expected_data}
     Delete S3 Account  ${S3_account_name}  ${password}  True

verify that add access key button disables after limit exceeded
    [Documentation]  This keyword verify that add access key button disables after limit exceeded
    ${S3_account_name}  ${password} =  generate new access key
    sleep  1s
    Click on download and close button for new access key
    sleep  1s
    ${state_add_access_key_btn}=  Get Element Attribute  ${ADD_S3_ACCOUNT_ACCESS_KEY_ID}  disabled
    Run Keyword If  ${${state_add_access_key_btn}} == True  log to console and report  add access key button disables.
    Delete S3 Account  ${S3_account_name}  ${password}  True

verify update s3 account has only password options
    [Documentation]  This keyword verify that update s3 account has only password options for update.
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    wait for page or element to load
    Check S3 Account Exists  S3_ACCOUNTS_TABLE_XPATH  ${S3_account_name}
    wait for page or element to load
    Re-login  ${S3_account_name}  ${password}  S3_ACCOUNTS_TAB_ID
    Click on edit s3 account option
    ${password_fields} =  Get Element Count  ${EDIT_S3_ACCOUNT_OPTIONS_XPATH}
    Should Be True  ${password_fields} == 2
    Delete S3 Account  ${S3_account_name}  ${password}  True

Check Maintenance Option Not Exists
    [Documentation]  This keyword is to check that s3 user does not have access to Maintenance page
    Page Should Not Contain Element  ${MAINTENANCE_MENU_ID}    

Check Dashboard Option Not Exists
    [Documentation]  This keyword is to check that s3 user does not have access to Dashboard page
    Page Should Not Contain Element  ${DASHBOARD_MENU_ID}    

Check Create CSM User Option Not Exists
    [Documentation]  This keyword is to check that s3 user does not have access to create csm user page
    Page Should Not Contain Element  ${ADMINISTRATIVE_USER_TAB_ID}

Check Alert Icon Not Exists
    [Documentation]   This keyword is to check that s3 user does not have access to Alert page
    Page Should Not Contain Element  ${ALERT_IMAGE_2_ID}

Check Associated S3 Account Exists
    [Documentation]   This keyword is to check that s3 user does associated s3 account 
    [Arguments]  ${expected_s3_account}  ${email}
    wait until element is visible  ${S3_ACCOUNTS_TABLE_XPATH}  timeout=60
    ${s3_account_table_data}=   Read Table Data  ${S3_ACCOUNTS_TABLE_XPATH}
    ${expected_list}=  Create List  ${expected_s3_account}  ${email}
    Remove From List  ${s3_account_table_data}  2
    Log To Console And Report  ${s3_account_table_data}
    Log To Console And Report  ${expected_list}
    Lists Should Be Equal  ${s3_account_table_data}  ${expected_list}

Verify S3 urls are displayed on the S3accounts tab
    [Documentation]  Verify S3 urls are displayed on the S3accounts tab
    Page Should Contain Element  ${S3_ACCOUNTS_TAB_S3_URL_TEXT_ID}
    Page Should Contain Element  ${S3_ACCOUNTS_TAB_COPY_S3_URL_ONE_ID}
    Page Should Contain Element  ${S3_ACCOUNTS_TAB_COPY_S3_URL_TWO_ID}
    ${S3_url_element_text}=  get text  ${S3_ACCOUNTS_TAB_S3_URL_TEXT_ID}
    Should Contain  ${S3_url_element_text}  S3 URL

Verify that s3 url is displyed access key popup
    [Documentation]  Verify s3 url is displyed access key popup
    Click on add new access key button
    wait until element is visible  ${NEW_ACCESS_KEY_TABLE_XPATH}  timeout=30
    ${new_access_key_data} =  Read Table Data   ${NEW_ACCESS_KEY_TABLE_XPATH}
    List Should Contain Value  ${new_access_key_data}  S3 URL
    Click on download and close button for new access key
    wait for page or element to load  2s

Verify that s3 url on s3 account creation
    [Documentation]  Verify s3 url is displyed access key popup
    Click on add new s3 account button
    ${S3_account}=  Generate New User Name
    ${email}=  Generate New User Email
    ${s3_account_password}=  Generate New Password
    log to console and report  S3 account user name is ${S3_account}
    log to console and report  email-id is ${email}
    log to console and report  password is ${s3_account_password}
    Add data to create new S3 account  ${S3_account}  ${email}  ${s3_account_password}  ${s3_account_password}
    Click on create new S3 account button
    wait for page or element to load  2s
    wait until element is visible  ${S3_ACCOUNT_CREATION_POP_UP_TABLE_XPATH}  timeout=30
    ${new_s3_account_data} =  Read Table Data   ${S3_ACCOUNT_CREATION_POP_UP_TABLE_XPATH}
    Should Contain  ${new_s3_account_data}  S3 URL:
    Click on download and close button
    Re-login  ${S3_account}  ${s3_account_password}  S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    Delete S3 Account  ${S3_account}  ${s3_account_password}  True

Delete s3 account using csm user
    [Documentation]  Delete s3 account using csm user and very it.
    [Arguments]  ${S3_account_name}
    Action On The Table Element  ${DELETE_S3_ACCOUNT_BY_CSM_USER_XPATH}  ${S3_account_name}
    click button  ${CONFIRM_S3_ACCOUNT_DELETE_ID}
    wait for page or element to load
    ${s3_accouts} =  Read Table Data   ${S3_ACCOUNTS_TABLE_XPATH}
    List Should Not Contain Value  ${s3_accouts}  ${S3_account_name}

Verify Absence of Delete Button on S3account
    [Documentation]  Verify Absence of Delete Button on S3account
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    Page Should Not Contain Element  ${DELETE_S3_ACCOUNT_ID}

Verify Error Msg is Shown For Non Empty S3account delete
    [Documentation]  This keyword will Verify Error Msg is Shown if delete performed on Non Empty account
    [Arguments]  ${S3_account_name}
    Action On The Table Element  ${DELETE_S3_ACCOUNT_BY_CSM_USER_XPATH}  ${S3_account_name}
    click button  ${CONFIRM_S3_ACCOUNT_DELETE_ID}
    wait until element is visible  ${ERROR_MSG_POP_UP_ID}  timeout=30
    ${err_msg}=  get text  ${ERROR_MSG_POP_UP_ID}
    Log To Console And Report  ${err_msg}
    Should be Equal  ${NON_EMPTY_S3_ACCOUNT_MESSAGE}  ${err_msg}
    Wait Until Element Is Not Visible  ${ERROR_MSG_POP_UP_ID}  timeout=30
