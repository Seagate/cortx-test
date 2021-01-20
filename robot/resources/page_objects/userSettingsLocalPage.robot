*** Settings ***
Resource  ../common/common.robot
Library     SeleniumLibrary

*** Keywords ***
Click On Add User Button
    [Documentation]  Perform click operation on add user button
    Click button    ${add user button id}

Click On Cancel Button
    [Documentation]  Perform click operation on cancel button
    Click button    ${CANCEL_NEW_CSM_USER_BUTTON_ID}

Click On Confirm Button
    [Documentation]  Perform click operation on confirm pop up button
    Sleep  3s
    Click button    ${NEW_USER_CONFIRM_OK_BUTTON_ID}

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
    ${users_list}=  Read Table Data  ${CSM_TABLE_ELEMENTS_XPATH}
    List Should Contain Value  ${users_list}  ${user_name}

Delete CSM User
    [Documentation]  Functionality to validate correc user name
    [Arguments]  ${user_name}
    Action On The Table Element  ${CSM_USER_DELETE_XAPTH}  ${user_name}
    Sleep  3s
    Click Button  ${CONFIRM_DELETE_BOX_BTN_ID}
    Sleep  3s
    click on confirm button

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

Verify Create Button Must Remain disbaled
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

Verify Missmatch Password Error
    [Documentation]  Functionality to verify error msg at missmatch password
    Log To Console And Report  Verifying miss match pasword
    ${password}=  Generate New Password
    Input Text  ${ADD_USER_PASSWORD_INPUT_ID}  ${password}
    ${value}=  CATENATE  ${password}  new
    Log To Console And Report  ${value}
    Input Text  ${ADD_USER_CONFIRM_PASSWORD_INPUT_ID}  ${value}
    Page Should Contain Element  ${PASSWORD_MISS_MATCH_MSG_ID}
    ${text}=  get text  ${PASSWORD_MISS_MATCH_MSG_ID}
    should be equal  ${text}  ${missmatch password msg}

Verify No Delete Button Present
    [Documentation]  Verify No delete icon should be present
    Page Should Not Contain Button  ${CREATE_NEW_CSM_USER_BUTTON_ID}


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
    Click Button  ${CHANGE_PASSWORD_BTN_ID}
    Sleep  1s
    Input Text  ${ADD_USER_PASSWORD_INPUT_ID}  ${password}
    Input Text  ${CONFIRM_NEW_PASSWORD_INPUT_ID}  ${password}
    Run Keyword If  '${old_password}' != 'False'
    ...  Input Text  ${OLD_PASSWORD_INPUT_ID}  ${old_password}
    Click Button  ${UPDATE_USER_BTN_ID}
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
    Click Button  ${UPDATE_USER_BTN_ID}
    Sleep  3s
    click on confirm button

Verify Deleted User
    [Documentation]  Functionality to check user get deleted successfully
    [Arguments]  ${user_name}
    Sleep  2s
    ${user_list}=  Read Table Data  ${CSM_TABLE_ELEMENTS_XPATH}
    List Should Not Contain Value  ${user_list}  ${user_name}

Verify Presence of Pagiantion
    [Documentation]  Functionality to validate correc user name
    Sleep  1s
    Page Should Contain Element  ${PAGINATION_BAR_XPATH}

Read Pagiantion Options
    [Documentation]  This Keyword is for reading all available function for pagiantion
    @{data_list}=    Create List
    Click Element  ${PAGINATION_LIST_ICON_XPATH}
    Sleep  3s
    @{elements}=  Get WebElements  ${PAGIANTION_PAGE_OPTIONS_XPATH}
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
    Sleep  1s
    Page Should Not Contain Element  ${IAM_USER_TAB_ID}