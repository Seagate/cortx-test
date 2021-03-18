*** Settings ***
Library    SeleniumLibrary
Resource   ${EXECDIR}/resources/common/common.robot

*** Keywords ***

Fetch S3 Account Name
    [Documentation]  This keyword will fetch logged s3 account user name
    wait until element is visible  ${LOGGED_IN_USER_NAME_ID}  timeout=60
    ${text}=  get text  ${LOGGED_IN_USER_NAME_ID}
    [Return]  ${text}

Click IAMuser Download CSV Button
    [Documentation]  This keyword click on Download CSV Button
    Sleep  5s  # element need to load
    wait until element is visible  ${IAM_USER_DOWNLOAD_CSV_BUTTON_ID}  timeout=60
    Click Element  ${IAM_USER_DOWNLOAD_CSV_BUTTON_ID}

Close IAMuser Error Box Button
    [Documentation]  This keyword will click on IAMuser Error Box Button
    Sleep  5s  # element need to load
    wait until element is visible  ${CLOSE_DUPLICATE_ACCOUNT_ALERT_MESSAGE_ID}  timeout=60
    Click Element  ${CLOSE_DUPLICATE_ACCOUNT_ALERT_MESSAGE_ID}

Click Create IAM User Button
    [Documentation]  This keyword will click on create IAM user button
    wait until element is visible  ${ADD_IAM_USER_BUTTON_ID}  timeout=60
    click button    ${ADD_IAM_USER_BUTTON_ID}

Click on IAM User Cancel Button
    [Documentation]  This keyword will click on cancel IAM user button
    wait until element is visible  ${CANCEL_IAM_USER_BUTTON_ID}  timeout=60
    click button    ${CANCEL_IAM_USER_BUTTON_ID}

Verify Duplicate User Error MSG
    [Documentation]  This keyword will Verify Duplicate User Error MSG
    wait until element is visible  ${DUPLICATE_USER_MSG_ID}  timeout=60
    ${text}=  get text  ${DUPLICATE_USER_MSG_ID}
    Close IAMuser Error Box Button
    Log To Console And Report  ${text}
    should be equal  ${text}  ${DUPLICATE_IAM_USER_ERROR_MSG}

Verify A Form Got Open To Create IAM Users
    [Documentation]  Verify the Form elements should be present
    Page Should Contain Button  ${CREATE_IAM_USER_USERNAME_ID}
    Page Should Contain Button  ${CREATE_IAM_USER_PASSWORD_ID}
    Page Should Contain Element  ${CREATE_IAM_USER_CONFIRM_PASSWORD_ID}
    Page Should Contain Element  ${CREATE_IAM_USER_BUTTON_ID}
    Page Should Contain Element  ${CANCEL_IAM_USER_BUTTON_ID}
    Element Should Be Disabled  ${CREATE_IAM_USER_BUTTON_ID}


Verify Form To Create IAM Users Got Closed
    [Documentation]  Verify the Form elements should not be present
    Page Should Not Contain Button  ${CREATE_IAM_USER_USERNAME_ID}
    Page Should Not Contain Button  ${CREATE_IAM_USER_PASSWORD_ID}
    Page Should Not Contain Element  ${CREATE_IAM_USER_CONFIRM_PASSWORD_ID}
    Page Should Not Contain Element  ${CREATE_IAM_USER_BUTTON_ID}
    Page Should Not Contain Element  ${CANCEL_IAM_USER_BUTTON_ID}
    Element Should Be Enabled  ${ADD_IAM_USER_BUTTON_ID}

Verify IAM User Username Tooltip
    [Documentation]  This keyword will fetch tooltip for IAMuser username
    wait until element is visible  ${IAM_USER_TOOLTIP_USER_IMAGE_ID}  timeout=60
    Mouse Over  ${IAM_USER_TOOLTIP_USER_IMAGE_ID}
    wait until element is visible  ${IAM_USER_TOOLTIP_ID}  timeout=60
    ${text}=  Get Text  ${IAM_USER_TOOLTIP_ID}
    Log To Console And Report  ${text}
    Should Contain    ${text}  ${IAM_USER_USERNAME_TOOLTIP_MSG}

Verify IAM User Password Tooltip
    [Documentation]  This keyword will fetch tooltip for IAMuser Password
    wait until element is visible  ${IAM_USER_PASSWD_TOOLTIP_IMAGE_ID}  timeout=60
    Mouse Over  ${IAM_USER_PASSWD_TOOLTIP_IMAGE_ID}
    wait until element is visible  ${IAM_USER_TOOLTIP_ID}  timeout=60
    ${text}=  Get Text  ${IAM_USER_TOOLTIP_ID}
    Log To Console And Report  ${text}
    Should Contain    ${text}  ${IAM_USER_PASSWD_TOOLTIP_MSG}

Verify Mismatch IAMuser Password Error
    [Documentation]  Functionality to verify error msg at mismatch IAMuser password
    Log To Console And Report  Verifying miss match pasword
    ${password}=  Generate New Password
    Input Text  ${CREATE_IAM_USER_PASSWORD_ID}  ${password}
    ${value}=  CATENATE  ${password}  new
    Log To Console And Report  ${value}
    Input Text  ${CREATE_IAM_USER_CONFIRM_PASSWORD_ID}  ${value}
    Page Should Contain Element  ${IAM_USER_PASSWD_MISSMATCH_ID}
    ${text}=  get text  ${IAM_USER_PASSWD_MISSMATCH_ID}
    should be equal  ${text}  ${IAM_USER_PASSWD_MISSMATCH_MSG}


Verify Create IAMuser Button Must Remain disabled
    [Documentation]  Functionality to verify create button status at different scenario
    ${password}=  Generate New Password
    Element Should Be Disabled  ${CREATE_IAM_USER_BUTTON_ID}
    ${value}=  Generate New User Name
    Log To Console And Report  Inserting username ${value}
    Input Text  ${CREATE_IAM_USER_USERNAME_ID}  ${value}
    Element Should Be Disabled  ${CREATE_IAM_USER_BUTTON_ID}
    Log To Console And Report  Insrting password
    Input Text  ${CREATE_IAM_USER_PASSWORD_ID}  ${password}
    Element Should Be Disabled  ${CREATE_IAM_USER_BUTTON_ID}
    Log To Console And Report  Insrting confirm password
    Input Text  ${CREATE_IAM_USER_CONFIRM_PASSWORD_ID}  ${password}
    Element Should Be Enabled  ${CREATE_IAM_USER_BUTTON_ID}

Create IAMuser
    [Documentation]  Functionality to create IAM user
    [Arguments]  ${username}  ${password}  ${duplicate}=${False}
    Log To Console And Report  Inserting username ${username}
    Input Text  ${CREATE_IAM_USER_USERNAME_ID}  ${username}
    Log To Console And Report  Insrting password
    Input Text  ${CREATE_IAM_USER_PASSWORD_ID}  ${password}
    Element Should Be Disabled  ${CREATE_IAM_USER_BUTTON_ID}
    Log To Console And Report  Insrting confirm password
    Input Text  ${CREATE_IAM_USER_CONFIRM_PASSWORD_ID}  ${password}
    Click Element  ${CREATE_IAM_USER_BUTTON_ID}
    Run Keyword If  '${duplicate}' == 'False'  Click IAMuser Download CSV Button

Delete IAMuser
    [Documentation]  Functionality to Delete IAMuser
    [Arguments]  ${user_name}
    Log To Console And Report  Deleting IAMuser ${user_name}
    Action On The Table Element  ${IAM_USER_DELETE_ICON_XPATH}  ${user_name}
    Sleep  5s
    wait until element is visible  ${CONFIRM_DELETE_BOX_BTN_ID}  timeout=60
    Click Button  ${CONFIRM_DELETE_BOX_BTN_ID}
    
Reset Password IAMuser
    [Documentation]  Functionality to Reset IAMuser Password
    [Arguments]  ${user_name}
    Log To Console And Report  Resetting password for IAMuser ${user_name}
    Action On The Table Element  ${IAM_USER_RESET_PASSWORD_XPATH}  ${user_name}
    Sleep  5s
    wait until element is visible  ${IAM_USER_RESET_NEW_PASSWORD_ID}  timeout=60
    ${new_password} =  Generate New Password
    input text  ${IAM_USER_RESET_NEW_PASSWORD_ID}  ${new_password}
    input text  ${IAM_USER_RESET_CONFIRM_PASSWORD_ID}  ${new_password}
    Click Button  ${IAM_USER_RESET_PAWWSORD_BUTTON_ID}
    Sleep  5s
    wait until element is visible  ${IAM_USER_SUCCESS_MESSAGE_ID}  timeout=60
    Sleep  2s
    Click Button  ${IAM_USER_SUCCESS_MESSAGE_BUTTON_ID}

Is IAMuser Present
    [Documentation]  Check the IAMuser present or not
    [Arguments]  ${user_name}
    ${element}=  Format String  ${IAM_USER_ROW_ELEMENT_XPATH}  ${USER_NAME}
    Log To Console And Report  Element path ${element}
    ${status}=  Run Keyword And Return Status  Element Should Be Visible  ${element}
    [Return]  ${status}

Verify All Mandatory Fields In IAMusers Has astreic sign
    [Documentation]  Verify All Mandatory Fields In IAMusers Has astreic sign
    Click Create IAM User Button
    ${username}=  get text  ${IAM_USER_USERNAME_LABEL_ID}
    Log To Console And Report  ${username}
    Should Contain  ${username}  *
    ${password}=  get text  ${IAM_USER_PASSWORD_LABEL_ID}
    Log To Console And Report  ${password}
    Should Contain  ${password}  *
    ${confirm_password}=  get text  ${IAM_USER_CONFIRM_PASSWORD_LABEL_ID}
    Log To Console And Report  ${confirm_password}
    Should Contain  ${confirm_password}  *

Verify No Data Retains After Cancel IAMuser
    [Documentation]  Verify Blank IAMuser Form opens after IAM user got canceled
    Verify Create IAMuser Button Must Remain disabled
    Click on IAM User Cancel Button
    Click Create IAM User Button
    ${value} =  Get Element Attribute  ${CREATE_IAM_USER_USERNAME_ID}  value
    Should Be Empty  ${value}
    ${value} =  Get Element Attribute  ${CREATE_IAM_USER_PASSWORD_ID}  value
    Should Be Empty  ${value}
    ${value} =  Get Element Attribute  ${CREATE_IAM_USER_CONFIRM_PASSWORD_ID}  value
    Should Be Empty  ${value}

Verify ARN Username UserID
    [Documentation]  Verify ARN, username and UserID of IAMuser
    [Arguments]  ${user_name}
    Sleep  5s  # Need to reload the uses
    ${status}=  Is IAMuser Present  ${username}
    Should be equal  ${status}  ${True}
    ${base}=  Format String  ${IAM_USER_ROW_ELEMENT_XPATH}  ${USER_NAME}
    ${element}=  CATENATE  SEPARATOR=  ${base}  //td[2]
    ${data}=  get text  ${element}
    Log To Console And Report  ${data}
    Should Not Be Empty  ${data}
    ${element}=  CATENATE  SEPARATOR=  ${base}  //td[3]
    ${data}=  get text  ${element}
    Log To Console And Report  ${data}
    Should Not Be Empty  ${data}
