*** Settings ***
Library    SeleniumLibrary
Resource   ${RESOURCES}/resources/common/common.robot

*** Keywords ***

Click On Add User Button
    [Documentation]  Perform click operation on add user button
    Click button    ${ADD_USER_BUTTON_ID}

Click On Cancel Button
    [Documentation]  Perform click operation on cancel button
    Click button    ${CANCEL_NEW_CSM_USER_BUTTON_ID}

Click On Confirm Button
    [Documentation]  Perform click operation on confirm pop up button
    wait for page or element to load
    Wait Until Element Is Visible  ${NEW_USER_CONFIRM_OK_BUTTON_ID}  timeout=60
    log to console and report  ${NEW_USER_CONFIRM_OK_BUTTON_ID}
    Click element  ${NEW_USER_CONFIRM_OK_BUTTON_ID}

Verify A Form Got Open To Create CSM Users
    [Documentation]  Verify the Form elements should be present
    Page Should Contain Button  ${CREATE_NEW_CSM_USER_BUTTON_ID}
    Page Should Contain Button  ${CANCEL_NEW_CSM_USER_BUTTON_ID}
    Page Should Contain Element  ${ADD_USER_USER_NAME_INPUT_BOX_ID}
    Page Should Contain Element  ${ADD_USER_PASSWORD_INPUT_ID}
    Page Should Contain Element  ${ADD_USER_CONFIRM_PASSWORD_INPUT_ID}
    Page Should Contain Element  ${ADD_USER_EMAIL_ID_INPUT_ID}

Verify The Form Should Get Closed
    [Documentation]  Verify the Form elements should be present
    Page Should Contain Button  ${ADD_USER_BUTTON_ID}
    Page Should Not Contain Button  ${CREATE_NEW_CSM_USER_BUTTON_ID}
    Page Should Not Contain Button  ${CANCEL_NEW_CSM_USER_BUTTON_ID}
    Page Should Not Contain Element  ${ADD_USER_USER_NAME_INPUT_BOX_ID}
    Page Should Not Contain Element  ${ADD_USER_PASSWORD_INPUT_ID}
    Page Should Not Contain Element  ${ADD_USER_CONFIRM_PASSWORD_INPUT_ID}
    Page Should Not Contain Element  ${ADD_USER_EMAIL_ID_INPUT_ID}

Create New CSM User
    [Documentation]  Functionality to create new user
    [Arguments]  ${user_name}  ${password}=${False}  ${user_type}=manage
    ${email}=  Generate New User Email
    ${temp}=  Generate New Password
    ${password}=  Set Variable If  '${password}' == 'False'  ${temp}  ${password}
    log to console and report  user name is ${user_name}
    log to console and report  email-id is ${email}
    log to console and report  user type is ${user_type}
    log to console and report  password is ${password}
    Click On Add User Button
    Input Text  ${ADD_USER_USER_NAME_INPUT_BOX_ID}  ${user_name}
    Input Text  ${ADD_USER_EMAIL_ID_INPUT_ID}  ${email}
    Input Text  ${ADD_USER_PASSWORD_INPUT_ID}  ${password}
    Input Text  ${ADD_USER_CONFIRM_PASSWORD_INPUT_ID}  ${password}
    ${var}=  CATENATE  add  ${user_type}  user  radio  button  id
    Click Element  ${${var}}
    Click button    ${CREATE_NEW_CSM_USER_BUTTON_ID}

Verify New User
    [Documentation]  Functionality to validate correc user name
    [Arguments]  ${user_name}
    wait for page or element to load  6s  #  Reloading take some initial time
    ${users_list}=  Read Table Data  ${CSM_TABLE_ELEMENTS_XPATH}
    List Should Contain Value  ${users_list}  ${user_name}

Delete CSM User
    [Documentation]  Functionality to Delete CSM user
    [Arguments]  ${user_name}
    Action On The Table Element  ${CSM_USER_DELETE_XAPTH}  ${user_name}
    wait until element is visible  ${CONFIRM_DELETE_BOX_BUTTON_ID}  timeout=60
    Click Button  ${CONFIRM_DELETE_BOX_BUTTON_ID}
    click on confirm button

Delete Logged In CSM User
    [Documentation]  Functionality to Delete the logged in csm user
    [Arguments]  ${user_name}
    Action On The Table Element  ${CSM_USER_DELETE_XAPTH}  ${user_name}
    wait until element is visible  ${CONFIRM_DELETE_BOX_BUTTON_ID}  timeout=30
    Click Button  ${CONFIRM_DELETE_BOX_BUTTON_ID}

Verify Only Valid User Allowed For Username
    [Documentation]  Functionality to validate correc user name
    FOR    ${value}    IN    @{INVALID_LOCAL_USER}
      Log To Console And Report  Inserting values ${value}
      Sleep  1s
      Input Text  ${ADD_USER_USER_NAME_INPUT_BOX_ID}  ${value}
      Page Should Contain Element  ${INVALID_LOCAL_USER_MSG_ID}
      ${invalid_user_msg}=  get text  ${INVALID_LOCAL_USER_MSG_ID}
      should be equal  ${invalid_user_msg}  ${invalid user type msg}
      Click On Cancel Button
      Click On Add User Button
    END
    ${value}=  Generate New User Name
    Log To Console And Report  Checking for a valid input ${value}
    Input Text  ${ADD_USER_USER_NAME_INPUT_BOX_ID}  ${value}
    Page Should Not Contain Element  ${INVALID_LOCAL_USER_MSG_ID}

Verify Create Button Must Remain disabled
    [Documentation]  Functionality to verify create button status at different scenario
    ${password}=  Generate New Password
    Element Should Be Disabled  ${CREATE_NEW_CSM_USER_BUTTON_ID}
    ${value}=  Generate New User Name
    Log To Console And Report  Inserting username ${value}
    Input Text  ${ADD_USER_USER_NAME_INPUT_BOX_ID}  ${value}
    Element Should Be Disabled  ${CREATE_NEW_CSM_USER_BUTTON_ID}
    ${value}=  Generate New User Email
    Log To Console And Report  Inserting email ${value}
    Input Text  ${ADD_USER_EMAIL_ID_INPUT_ID}  ${value}
    Element Should Be Disabled  ${CREATE_NEW_CSM_USER_BUTTON_ID}
    Log To Console And Report  Insrting password
    Input Text  ${ADD_USER_PASSWORD_INPUT_ID}  ${password}
    Element Should Be Disabled  ${CREATE_NEW_CSM_USER_BUTTON_ID}
    Log To Console And Report  Insrting confirm password
    Input Text  ${ADD_USER_CONFIRM_PASSWORD_INPUT_ID}  ${password}
    Element Should Be Enabled  ${CREATE_NEW_CSM_USER_BUTTON_ID}

Verify Passwords Remain Hidden
    [Documentation]  Functionality to verify  password and confirm password type
    Log To Console And Report  Verifying pasword
    ${attribute}=  Get Element Attribute  ${ADD_USER_PASSWORD_INPUT_ID}  type
    should be equal  ${attribute}  ${hidden type element}
    Log To Console And Report  Verifying confirm pasword
    ${attribute}=  Get Element Attribute  ${ADD_USER_CONFIRM_PASSWORD_INPUT_ID}  type
    should be equal  ${attribute}  ${hidden type element}

Verify Mismatch Password Error
    [Documentation]  Functionality to verify error msg at mismatch password
    Log To Console And Report  Verifying miss match pasword
    ${password}=  Generate New Password
    Input Text  ${ADD_USER_PASSWORD_INPUT_ID}  ${password}
    ${value}=  CATENATE  ${password}  new
    Log To Console And Report  ${value}
    Input Text  ${ADD_USER_CONFIRM_PASSWORD_INPUT_ID}  ${value}
    Page Should Contain Element  ${PASSWORD_MISS_MATCH_MSG_ID}
    ${text}=  get text  ${PASSWORD_MISS_MATCH_MSG_ID}
    should be equal  ${text}  ${MISSMATCH_PASSWORD_MESSAGE}

Verify Absence of Edit And Delete Button on S3account
    [Documentation]  Verify Absence of Edit And Delete Button on S3account
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    Page Should Not Contain Element  ${EDIT_S3_ACCOUNT_OPTION_ID}
    Page Should Not Contain Element  ${DELETE_S3_ACCOUNT_ID}

Verify Absence of Reset Passwrod Button on S3account
    [Documentation]  Verify Absence of Reset Passwrod Button Button on S3account
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    Page Should Not Contain Element  ${EDIT_S3_ACCOUNT_OPTION_ID}

Verify Absence of Admin User Section
    [Documentation]  Verify Absence of Admin User Section
    Page Should Not Contain Element  ${ADMINISTRATIVE_USER_TAB_ID}
    Page Should Not Contain Button  ${ADD_USER_BUTTON_ID}

Verify Absence of Delete Button on CSM users
    [Documentation]  Verify Absence of delete icon
    Navigate To Page    MANAGE_MENU_ID  ADMINISTRATIVE_USER_TAB_ID
    wait for page or element to load  3s  # Took time to load CSM accounts
    Page Should Not Contain Button  ${DELETE_USER_BUTTON_ID}

Verify Only Valid Password Get Added
    [Documentation]  Functionality to validate correct pawwsord
    FOR    ${value}    IN    @{INVALID_PASSWORDS_LIST}
      Log To Console And Report  Inserting values ${value}
      Sleep  1s
      Input Text  ${ADD_USER_PASSWORD_INPUT_ID}  ${value}
      Page Should Contain Element  ${INVALID_PASSWORD_MSG_ID}
      ${text_msg}=  get text  ${INVALID_PASSWORD_MSG_ID}
      should be equal  ${text_msg}  ${invalid password msg}
      Click On Cancel Button
      Click On Add User Button
    END
    ${value}=  Generate New Password
    Log To Console And Report  Checking for a valid input ${value}
    Input Text  ${ADD_USER_PASSWORD_INPUT_ID}  ${value}
    Page Should Not Contain Element  ${INVALID_PASSWORD_MSG_ID}

Edit CSM User Password
    [Documentation]  Functionality to Edit given user password
    [Arguments]  ${user_name}  ${password}  ${old_password}=${False}
    Action On The Table Element  ${CSM_USER_EDIT_XPATH}  ${user_name}
    Sleep  1s
    Click Button  ${CHANGE_PASSWORD_BUTTON_ID}
    Sleep  1s
    Input Text  ${ADD_USER_PASSWORD_INPUT_ID}  ${password}
    Input Text  ${CONFIRM_NEW_PASSWORD_INPUT_ID}  ${password}
    Run Keyword If  '${old_password}' != 'False'
    ...  Input Text  ${OLD_PASSWORD_INPUT_ID}  ${old_password}
    Click Button  ${UPDATE_USER_BUTTON_ID}
    Sleep  3s
    click on confirm button

Edit CSM User Type
    [Documentation]  Functionality to Edit given user type
    [Arguments]  ${user_name}  ${user_type}
    Action On The Table Element  ${CSM_USER_EDIT_XPATH}  ${user_name}
    Sleep  1s
    ${var}=  CATENATE  add  ${user_type}  user  radio  button  id
    ${var}=  Catenate  SEPARATOR=  ${${var}}  Interface
    Sleep  2s
    Click Element  ${var}
    Click Button  ${UPDATE_USER_BUTTON_ID}
    Sleep  3s
    click on confirm button

Verify Deleted User
    [Documentation]  Functionality to check user get deleted successfully
    [Arguments]  ${user_name}
    Sleep  2s
    ${user_list}=  Read Table Data  ${CSM_TABLE_ELEMENTS_XPATH}
    List Should Not Contain Value  ${user_list}  ${user_name}

Verify Presence of Pagination
    [Documentation]  Functionality to validate correc user name
    wait for page or element to load  2s
    Page Should Contain Element  ${PAGINATION_BAR_XPATH}

Read Pagination Options
    [Documentation]  This Keyword is for reading all available function for pagination
    @{data_list}=    Create List
    Click Element  ${PAGINATION_LIST_ICON_XPATH}
    Sleep  3s
    @{elements}=  Get WebElements  ${PAGINATION_PAGE_OPTIONS_XPATH}
    Log To Console And Report   ${elements}
    FOR  ${element}  IN  @{elements}
            ${text}=    Get Text    ${element}
            Append To List  ${data_list}  ${text}
    END
    Log To Console And Report   ${data_list}
    [Return]   @{data_list}

Fetch Radio Button Value
    [Documentation]  This Keyword is to fetch radio button value
    Click On Add User Button
    ${value}=  Get Element Attribute  ${RADIO_BTN_VALUE_XPATH}  value
    Log To Console And Report  Fetched value is ${value}
    [Return]  ${value}

Verify Change User Type Radio Button Disabled
    [Documentation]  Functionality to verify Change User Type Radio Button Disabled
    [Arguments]  ${user_name}
    Action On The Table Element  ${CSM_USER_EDIT_XPATH}  ${user_name}
    ${status}=  Get Element Attribute  ${RADIO_BTN_VALUE_XPATH}  disabled
    Log To Console And Report  ${status}
    Should be equal  ${status}  true

Verify Admin User Should Not Contain Delete Icon
    [Documentation]  Functionality to verify Admin User Should Not Contain Delete Icon
    [Arguments]  ${user_name}
    ${Delete_icon} =  Format String  ${CSM_USER_DELETE_XAPTH}  ${user_name}
    Log To Console And Report  ${delete_icon}
    Page Should Not Contain Button  ${delete_icon}

Verify IAM User Section Not Present
    [Documentation]  Functionality to verify IAM User Section Not Present
    Navigate To Page  MANAGE_MENU_ID
    wait for page or element to load  3s
    Page Should Not Contain Element  ${S3_IAM_USER_TAB_ID}

Edit CSM User Details
    [Documentation]  Functionality to Edit given user email id
    [Arguments]  ${user_name}  ${new_password}  ${new_email}  ${old_password}
    Action On The Table Element  ${CSM_USER_EDIT_XPATH}  ${user_name}
    Sleep  1s
    Click Button  ${CHANGE_PASSWORD_BUTTON_ID}
    Sleep  1s
    Press Keys  ${UPDATE_USER_EMAIL_ID_INPUT_ID}  CTRL+a+BACKSPACE
    Input Text  ${UPDATE_USER_EMAIL_ID_INPUT_ID}  ${new_email}
    Input Text  ${ADD_USER_PASSWORD_INPUT_ID}  ${new_password}
    Input Text  ${UPDATE_USER_CONFIRM_PASSWORD_INPUT_ID}  ${new_password}
    Input Text  ${OLD_PASSWORD_INPUT_ID}  ${old_password}
    Click Button  ${UPDATE_USER_BUTTON_ID}
    Sleep  3s
    click on confirm button
    sleep  1s
    ${users_list}=  Read Table Data  ${CSM_TABLE_ELEMENTS_XPATH}
    List Should Contain Value  ${users_list}  ${new_email}

Edit S3 User Password
    [Documentation]  This keyword is to edit s3 account password.
    [Arguments]  ${s3_account_name}  ${password}  ${confirm_password}
    log to console and report   editing S3 account ${s3_account_name}
    Action On The Table Element  ${S3_ACCOUNT_RESET_PASSWORD_XPATH}  ${s3_account_name}
    update s3 account password  ${password}  ${confirm_password}
    Click on update s3 account button
    wait for page or element to load
    wait until element is visible  ${USER_DROPDOWN_ID}  timeout=20
    CSM GUI Logout
    Reload Page
    wait for page or element to load  3s
    Run Keywords
    ...  Enter Username And Password    ${s3_account_name}  ${password}
    ...  AND
    ...  Click Sigin Button
    Validate CSM Login Success  ${s3_account_name}

Verify that monitor user is not able to create delete csm user
       [Documentation]  this keyword verifys that monitor user not able to edit or delete csm user
       Page Should Not Contain Element  ${ADD_USER_BUTTON_ID}
       Page Should Not Contain Element  ${DELETE_USER_BUTTON_ID}

Verify Monitor User Is Not Able To Create Csm User
       [Documentation]  this keyword verifys that monitor user not able to add new csm user
       Page Should Not Contain Element  ${ADD_USER_BUTTON_ID}

Verify bucket Section Not Present
    [Documentation]  Functionality to verify bucket User Section Not Present.
    Navigate To Page  MANAGE_MENU_ID
    wait for page or element to load  3s
    Page Should Not Contain Element  ${BUCKETS_TAB_ID}

Verify Invalid Password Not Accepted By Edit S3 Account
    [Documentation]  Functionality to validate only correct pawwsord allowed
    FOR    ${value}    IN    @{INVALID_PASSWORDS_LIST}
      wait until element is visible  ${S3_ACCOUNT_REST_OPTION_ID}  timeout=30
      Click Element  ${S3_ACCOUNT_REST_OPTION_ID}
      Log To Console And Report  Inserting values ${value}
      wait for page or element to load  1s
      Input Text  ${S3_ACCOUNT_RESET_NEW_PASSWORD_ID}  ${value}
      Verify message  S3ACCOUNT_INVALID_PASSWORD_ERROR_MSG_ID  ${INVALID_PASSWORD_MSG}
      Click Element  ${S3_ACCOUNT_POP_UP_CANCEL_BUTTON_ID}
    END

Verify Mismatch Password Error For Edit S3account
    [Documentation]  Functionality to erify Mismatch Password Error For Edit S3account
    wait until element is visible  ${S3_ACCOUNT_REST_OPTION_ID}  timeout=30
    Click Element  ${S3_ACCOUNT_REST_OPTION_ID}
    ${password}=  Generate New Password
    Log To Console And Report  Verifying miss match pasword
    Input Text  ${S3_ACCOUNT_RESET_NEW_PASSWORD_ID}  ${password}
    ${value}=  CATENATE  ${password}  new
    Log To Console And Report  ${value}
    Input Text  ${S3_ACCOUNT_RESET_CONFIRM_PASSWORD_ID}  ${value}
    Verify message  S3ACCOUNT_MISS_MATCH_PASSWORD_ERROR_MSG_ID  ${INVALID_S3_CONFIRM_PASSWORD_MESSAGE}
    ${status}=  Get Element Attribute  ${S3_ACCOUNT_RESET_PASSWORD_BUTTON_ID}  disabled
    Log To Console And Report  Status of S3_ACCOUNT_RESET_PASSWORD_BUTTON_ID is ${status}
    Should be equal  ${status}  true
    Click Element  ${S3_ACCOUNT_POP_UP_CANCEL_BUTTON_ID}

Search username and role
    [Documentation]  Functionality to search an entry in manage page.
    [Arguments]  ${search_entry}
    wait for page or element to load
    input text  ${CSM_USER_SEARCH_BOX_XPATH}  ${search_entry}
    Click Element  ${CSM_USER_SEARCH_ICON_XPATH}
    wait for page or element to load

Select from filter
    [Documentation]  Functionality to filter in manage page for dropdown.
    [Arguments]  ${filter_entry}
    wait for page or element to load
    Click Element  ${CSM_USER_FILTER_DROPDOWN_BUTTON_XPATH}
    wait for page or element to load  2s
    ${var}=  CATENATE  csm filter ${filter_entry} select xpath
    Log To Console And Report  ${${var}}  
    Element Should Be Enabled  ${${var}}
    Click Element  ${${var}}
    wait for page or element to load

Verify Delete Action Disabled On The Table Element
    [Documentation]  Verify delete action disbled on the table element for given user.
    [Arguments]  ${username}
    Verify Action Disabled On The Table Element  ${CSM_USER_DELETE_XAPTH}  ${username}

Verify Edit Action Disabled On The Table Element
    [Documentation]  Verify edit action disbled on the table element for given user.
    [Arguments]  ${username}
    Verify Action Disabled On The Table Element  ${CSM_USER_EDIT_XPATH}  ${username}
