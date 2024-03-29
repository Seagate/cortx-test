*** Settings ***
Library    SeleniumLibrary
Resource   ${RESOURCES}/resources/common/common.robot

*** Keywords ***

Click On Add User Button
    [Documentation]  Perform click operation on add user button
    Press Keys  None  HOME
    wait for page or element to load
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
    Select The Number of Rows To Display  ${CSM_MAX_ROW_VALUE}
    wait for page or element to load  20s
    ${users_list}=  Read Table Data  ${CSM_TABLE_ELEMENTS_XPATH}
    List Should Contain Value  ${users_list}  ${user_name}

Delete CSM User
    [Documentation]  Functionality to Delete CSM user
    [Arguments]  ${user_name}
    Select The Number of Rows To Display  ${CSM_MAX_ROW_VALUE}
    wait for page or element to load  20s
    Action On The Table Element  ${CSM_USER_DELETE_XAPTH}  ${user_name}
    wait until element is visible  ${CONFIRM_DELETE_BOX_BUTTON_ID}  timeout=60
    Click Button  ${CONFIRM_DELETE_BOX_BUTTON_ID}
    click on confirm button

Delete Logged In CSM User
    [Documentation]  Functionality to Delete the logged in csm user
    [Arguments]  ${user_name}
    Select The Number of Rows To Display  ${CSM_MAX_ROW_VALUE}
    wait for page or element to load  20s
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
    [Arguments]  ${user_type}
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
    Element Should Be Disabled  ${CREATE_NEW_CSM_USER_BUTTON_ID}
    ${var}=  CATENATE  add  ${user_type}  user  radio  button  id
    Click Element  ${${var}}
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
    Navigate To Page  MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    Page Should Not Contain Element  ${EDIT_S3_ACCOUNT_OPTION_ID}
    Page Should Not Contain Element  ${DELETE_S3_ACCOUNT_ID}

Verify Absence of Reset Passwrod Button on S3account
    [Documentation]  Verify Absence of Reset Passwrod Button Button on S3account
    Navigate To Page  MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load
    Page Should Not Contain Element  ${EDIT_S3_ACCOUNT_OPTION_ID}

Verify Absence of Admin User Section
    [Documentation]  Verify Absence of Admin User Section
    ${csm_tab_text}=  get text  ${ADMINISTRATIVE_USER_TAB_ID}
    Should Not Contain  ${csm_tab_text}  Administrative user
    Page Should Not Contain Button  ${ADD_USER_BUTTON_ID}

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
    Select The Number of Rows To Display  ${CSM_MAX_ROW_VALUE}
    wait for page or element to load  20s
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
    Select The Number of Rows To Display  ${CSM_MAX_ROW_VALUE}
    wait for page or element to load  20s
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
    Select The Number of Rows To Display  ${CSM_MAX_ROW_VALUE}
    wait for page or element to load  20s
    ${user_list}=  Read Table Data  ${CSM_TABLE_ELEMENTS_XPATH}
    List Should Not Contain Value  ${user_list}  ${user_name}

Verify Presence of Pagination on Administrative Page
    [Documentation]  Functionality to validate correc user name
    wait for page or element to load  2s
    Page Should Contain Element  ${CSM_PAGINATION_BAR_XPATH}

Read Pagination Options on Administrative Page
    [Documentation]  This Keyword is for reading all available function for pagination
    @{data_list}=    Create List
    Click Element  ${CSM_PAGINATION_LIST_ICON_XPATH}
    Sleep  3s
    @{elements}=  Get WebElements  ${CSM_PAGINATION_PAGE_OPTIONS_XPATH}
    FOR  ${element}  IN  @{elements}
            ${text}=    Get Text    ${element}
            Append To List  ${data_list}  ${text}
    END
    Log To Console And Report   ${data_list}
    [Return]   @{data_list}

Verify Change User Type Radio Button Disabled
    [Documentation]  Functionality to verify Change User Type Radio Button Disabled
    [Arguments]  ${user_name}
    Select The Number of Rows To Display  ${CSM_MAX_ROW_VALUE}
    wait for page or element to load  20s
    Action On The Table Element  ${CSM_USER_EDIT_XPATH}  ${user_name}
    Element Should Be Disabled  ${RADIO_BTN_VALUE_XPATH}

Verify Admin User Should Not Contain Delete Icon
    [Documentation]  Functionality to verify Admin User Should Not Contain Delete Icon
    [Arguments]  ${user_name}
    Select The Number of Rows To Display  ${CSM_MAX_ROW_VALUE}
    wait for page or element to load  20s
    ${Delete_icon} =  Format String  ${CSM_USER_DELETE_XAPTH}  ${user_name}
    Log To Console And Report  ${delete_icon}
    Page Should Not Contain Button  ${delete_icon}

Verify IAM User Section Not Present
    [Documentation]  Functionality to verify IAM User Section Not Present
    Navigate To Page  MANAGE_MENU_ID  CSM_S3_ACCOUNTS_TAB_ID
    wait for page or element to load  3s
    ${s3_iam_tab_text}=  get text  ${S3_IAM_USER_TAB_ID}
    Should Not Contain  ${s3_iam_tab_text}  IAM user

Edit CSM User Details
    [Documentation]  Functionality to Edit given user email id
    [Arguments]  ${user_name}  ${new_password}  ${new_email}  ${old_password}
    Select The Number of Rows To Display  ${CSM_MAX_ROW_VALUE}
    wait for page or element to load  20s
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
    wait until element is visible  ${USER_DROPDOWN_XPATH}  timeout=20
    CSM GUI Logout
    Reload Page
    wait for page or element to load  3s
    Run Keywords
    ...  Enter Username And Password    ${s3_account_name}  ${password}
    ...  AND
    ...  Click Sigin Button
    Validate CSM Login Success  ${s3_account_name}

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
    Click Element  ${CSM_USER_SEARCH_ICON_ACTIVE_XPATH}
    wait for page or element to load

Select from filter
    [Documentation]  Functionality to filter in manage page for dropdown.
    [Arguments]  ${filter_entry}
    wait for page or element to load
    ${present}=  Run Keyword And Return Status    Element Should Be Visible   ${CSM_FILTER_LIST_BUTTON_XPATH}
    Run Keyword If  ${present} == False  Click Element  ${CSM_USER_FILTER_DROPDOWN_BUTTON_XPATH}
    wait for page or element to load  2s
    ${var}=  CATENATE  csm filter ${filter_entry} select xpath
    Log To Console And Report  ${${var}}  
    Element Should Be Enabled  ${${var}}
    Click Element  ${${var}}
    wait for page or element to load

Verify Filter and Search option present
    [Documentation]  Verify Filter and Search option present for users.
    wait for page or element to load
    Page Should Contain Element   ${CSM_USER_SEARCH_ICON_XPATH}
    Page Should Contain Element   ${CSM_USER_SEARCH_BOX_XPATH}
    Page Should Contain Element   ${CSM_USER_SEARCH_ICON_XPATH}
    input text  ${CSM_USER_SEARCH_BOX_XPATH}  test
    Page Should Contain Element   ${CSM_USER_SEARCH_ICON_ACTIVE_XPATH}
    Page Should Contain Element   ${CSM_USER_FILTER_DROPDOWN_BUTTON_XPATH}
    Click Element  ${CSM_USER_FILTER_DROPDOWN_BUTTON_XPATH}
    wait for page or element to load  2s
    ${filters}=  Create List  role  username
    FOR    ${filter_entry}    IN    @{filters}
        ${var}=  CATENATE  csm filter ${filter_entry} select xpath
        Log To Console And Report  ${${var}}
        Element Should Be Enabled  ${${var}}
    END

Verify Pagination Present on Administrative Page Search results
    [Documentation]  Verify Pagination present on Search results for CSM user
    input text  ${CSM_USER_SEARCH_BOX_XPATH}  admin
    Click Element  ${CSM_USER_SEARCH_ICON_ACTIVE_XPATH}
    wait for page or element to load
    ${fetched_values}=  Read Pagination Options on Administrative Page
    ${actual_values}=  Create List  5 rows  10 rows  20 rows  30 rows  50 rows  100 rows  150 rows  200 rows
    Lists Should Be Equal  ${fetched_values}  ${actual_values}

Get CSM table row count
    [Documentation]  Return number of rows present on CSM user table
    Select The Number of Rows To Display  ${CSM_MAX_ROW_VALUE}
    wait for page or element to load  20s
    ${users_list}=  Read Table Data  ${CSM_TABLE_ROW_XPATH}
    ${users_list_length}=  Get Length  ${users_list}
    Capture Page Screenshot
    [Return]  ${users_list_length}

Verify Blank Table on Search operation
    [Documentation]  Verify user will get blank table for unavailable search
    ${random_search}=  Generate New Password
    input text  ${CSM_USER_SEARCH_BOX_XPATH}  ${random_search}
    Click Element  ${CSM_USER_SEARCH_ICON_ACTIVE_XPATH}
    wait for page or element to load
    Capture Page Screenshot
    ${search_result}=  Read Table Data  ${CSM_TABLE_ELEMENTS_XPATH}
    Should Contain  ${search_result}  No data available

Verify Clean Search operation
    [Documentation]  Verify Clean Search operation working
    ${length1}=  Get CSM table row count
    input text  ${CSM_USER_SEARCH_BOX_XPATH}  test
    Click Element  ${CSM_USER_SEARCH_ICON_ACTIVE_XPATH}
    wait for page or element to load
    ${length2}=  Get CSM table row count
    Press Keys  ${CSM_USER_SEARCH_BOX_XPATH}  CTRL+a+BACKSPACE
    Page Should Contain Element      ${CSM_USER_SEARCH_ICON_XPATH}
    Page Should Not Contain Element  ${CSM_USER_SEARCH_ICON_ACTIVE_XPATH}
    Press Keys  None  TAB+TAB
    ${length3}=  Get CSM table row count
    Should Not Be Equal As Integers  ${length1}  ${length2}
    Should Be Equal As Integers  ${length1}  ${length3}

Verify Delete Action Enabled On The Table Element
    [Documentation]  Verify delete action enabled on the table element for given user.
    [Arguments]  ${username}
    Verify Action Enabled On The Table Element  ${CSM_USER_DELETE_XAPTH}  ${username}

Verify Delete Action Disabled On The Table Element
    [Documentation]  Verify delete action disbled on the table element for given user.
    [Arguments]  ${username}
    Verify Action Disabled On The Table Element  ${CSM_USER_DELETE_XAPTH}  ${username}

Verify Edit Action Enabled On The Table Element
    [Documentation]  Verify edit action enabled on the table element for given user.
    [Arguments]  ${username}
    Verify Action Enabled On The Table Element  ${CSM_USER_EDIT_XPATH}  ${username}

Verify Edit Action Disabled On The Table Element
    [Documentation]  Verify edit action disbled on the table element for given user.
    [Arguments]  ${username}
    Verify Action Disabled On The Table Element  ${CSM_USER_EDIT_XPATH}  ${username}

SSL certificate expiration alert Verification
    [Documentation]  This keyword is used to test SSL related alerts for  diffrent expiry days
    [Arguments]  ${days}
    Navigate To Page  SETTINGS_ID  SETTINGS_SSL_BUTTON_ID
    wait for page or element to load  20s
    ${installation_status_init} =  Format String  not_installed
    ${installation_status_success} =  Format String  installation_successful
    ${file_path}=  SSL Gennerate and Upload  ${days}  ${Download_File_Path}
    ${file_name}=  Set Variable  stx_${days}.pem
    Verify SSL status  ${installation_status_init}  ${file_name}
    Install uploaded SSL
    wait for page or element to load  5 minutes  #will re-start all service
    Close Browser
    CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
    wait for page or element to load  20s  # Took time to load dashboard after install
    Reload Page
    wait for page or element to load  10s  # Took time to load dashboard after install
    Verify SSL status  ${installation_status_success}  ${file_name}
    # Find the alert and verifiy
    Verify Presence SSL certificate expires alert  ${days}

Create account with input Role and Change Role from Admin account
    [Documentation]  This keyword is used to create user with given input role and then change it to other possible roles
    [Arguments]  ${cur_role}
    FOR   ${new_role}  IN  admin  manage  monitor
        ${new_password}=  Generate New Password
        ${new_user_name}=  Generate New User Name
        Run Keyword If  "${cur_role}" == "${new_role}"  Log To Console And Report  match, skipping
        ...  ELSE
        ...  Run Keywords
        ...  Log To Console And Report  Create Account with role: ${cur_role}
        ...  AND  Create New CSM User  ${new_user_name}  ${new_password}  ${cur_role}
        ...  AND  Click On Confirm Button
        ...  AND  Verify New User  ${new_user_name}
        ...  AND  Edit CSM User Type  ${new_user_name}  ${new_role}
        ...  AND  Delete CSM User  ${new_user_name}
    END

Get List of Page
    [Documentation]  This Keyword is for Fetching the list of Pages avaialble on Administrative User Page.
    [Arguments]  ${page_element}
    @{page_data}=    Create List
    @{page_elements}=  Get WebElements  ${page_element}
    Log To Console And Report  ${page_elements}
    sleep  2s
    FOR  ${elements}  IN  @{page_elements}
         ${text}=    Get Text    ${elements}
         Append To List  ${page_data}  ${text}
    END
    Log To Console And Report   ${page_data}
    ${page_list_length}=  Get Length  ${page_data}
    [Return]   @{page_data}    ${page_list_length}

Select The Number of Rows To Display
    [Documentation]  This Keyword is for selecting the no. of rows to display in table
    [Arguments]  ${row_number}
    @{x_elements}=    Create List
    Click Element  ${CSM_PAGINATION_LIST_ICON_XPATH}
    Sleep  3s
    @{x_elements}=  Get WebElements   ${CSM_PAGINATION_PAGE_OPTIONS_XPATH}
    Log To Console And Report   ${x_elements}
    sleep  2s
    FOR  ${element}  IN  @{x_elements}
            ${text}=    Get Text    ${element}
        Run Keyword If   "${text}" == "${row_number}"    Click Element   ${element}
    END

Delete Multiple CSM User
     [Documentation]    This Keyword is used to delete multiple CSM USers.
     [Arguments]    ${new_user_list}
     FOR  ${user_name}  IN  @{new_user_list}
            Delete CSM User  ${user_name}
     END

Create Multiple CSM User
     [Documentation]    This Keyword is used to create multiple CSM USers.
     [Arguments]    ${user_count}
     @{new_user_list}=    Create List
     FOR    ${i}    IN RANGE    ${user_count}
         ${new_password}=  Generate New Password
         ${new_user_name}=  Generate New User Name
         Log To Console And Report  Create Account with role: manage
         Create New CSM User  ${new_user_name}  ${new_password}  manage
         Click On Confirm Button
         Verify New User  ${new_user_name}
         Append To List  ${new_user_list}  ${new_user_name}
     END
     [Return]   @{new_user_list}

Navigate To First Page On Administrative Users Page
    [Documentation]  This Keyword is for navigating to Last page
    ${new_user_list}=  Check List Of CSM User And Create New Users
    Select The Number of Rows To Display   ${CSM_TEST_ROW_FIVE}
    wait for page or element to load  10s
    @{Page_list}    ${Page_count}    Get List of Page    ${CSM_PAGINATION_PAGE_XPATH}
    ${New_Page_list}=    Get Slice From List	${Page_list}	end=-1
    ${Page}=    Get From List   ${New_Page_list}   1
    Navigate To The Desired Page    ${CSM_PAGINATION_PAGE_XPATH}   ${Page}
    ${Page}=    Get From List   ${New_Page_list}   0
    Navigate To The Desired Page    ${CSM_PAGINATION_PAGE_XPATH}   ${Page}
    Capture Page Screenshot
    Delete Multiple CSM User  ${new_user_list}

Navigate To Last Page On Administrative Users Page
    [Documentation]  This Keyword is for navigating to Last page
    ${new_user_list}=  Check List Of CSM User And Create New Users
    Select The Number of Rows To Display   ${CSM_TEST_ROW_FIVE}
    wait for page or element to load  10s
    @{Page_list}    ${Page_count}    Get List of Page    ${CSM_PAGINATION_PAGE_XPATH}
    ${New_Page_list}=    Get Slice From List	${Page_list}	end=-1
    ${Page}=    Get From List   ${New_Page_list}   -1
    Navigate To The Desired Page    ${CSM_PAGINATION_PAGE_XPATH}   ${Page}
    Capture Page Screenshot
    Delete Multiple CSM User  ${new_user_list}

Navigate To The Desired Page
    [Documentation]   This Keyword is used to Navigate to the Desired Page on User Administrative Page
    [Arguments]    ${page_element}    ${page_Number}
    @{page_data}=    Create List
    @{page_elements}=  Get WebElements  ${page_element}
    Log To Console And Report  ${page_elements}
    Log To Console And Report  ${page_number}
    sleep  2s
    FOR  ${elements}  IN  @{page_elements}
         ${text}=    Get Text    ${elements}
         Run Keyword If   "${text}" == "${page_number}"    Click Element   ${elements}
    END

Check List Of CSM User And Create New Users
    [Documentation]   This Keyword is to verfiry the no. of CSM users
    Navigate To Page  ${page_name}
    Select The Number of Rows To Display  ${CSM_TEST_ROW_VALUE}
    wait for page or element to load  10s
    ${User_list}=   Get CSM table row count
    Run Keyword If    ${User_list} < ${CSM_TEST_DEFAULT_COUNT}    Evaluate    ${CSM_TEST_DEFAULT_COUNT} - ${User_list}
    ${count}=    Evaluate    ${CSM_TEST_DEFAULT_COUNT} - ${User_list}
    Log To Console And Report    ${count}
    ${new_user_list}=  Create Multiple CSM User  ${count}
    [Return]   @{new_user_list}

Create and login with CSM manage user
    [Documentation]  This keyword is to create and login with csm manage user
    ${new_user_name}=  Generate New User Name
    ${new_password}=  Generate New Password
    Reload Page
    wait for page or element to load
    Navigate To Page  MANAGE_MENU_ID  ADMINISTRATIVE_USER_TAB_ID
    wait for page or element to load
    Create New CSM User  ${new_user_name}  ${new_password}  manage
    Click On Confirm Button
    Verify New User  ${new_user_name}
    Re-login  ${new_user_name}  ${new_password}  MANAGE_MENU_ID
    [Return]  ${new_user_name}  ${new_password}

Create and login with CSM monitor user
    [Documentation]  This keyword is to create and login with csm monitor user
    ${new_user_name}=  Generate New User Name
    ${new_password}=  Generate New Password
    Reload Page
    wait for page or element to load
    Navigate To Page  MANAGE_MENU_ID  ADMINISTRATIVE_USER_TAB_ID
    wait for page or element to load
    Create New CSM User  ${new_user_name}  ${new_password}  monitor
    Click On Confirm Button 
    Verify New User  ${new_user_name}
    Re-login  ${new_user_name}  ${new_password}  MANAGE_MENU_ID
    [Return]  ${new_user_name}  ${new_password}

Verify Filter options got selected
    [Documentation]  This keyword is to verify that filter drop down menu contents role and username
    [Arguments]  ${filter_entry}
    ${var}=  CATENATE  CSM_FILTER ${filter_entry} SELECTED_XPATH
    Log To Console And Report  ${${var}}
    ${attrib}=  Get Element Attribute  ${${var}}  aria-selected
    Should be equal  ${attrib}  true

Verify Filter options Contents
    [Documentation]  This keyword is to verify that filter drop down menu contents role and username
    Click Element  ${CSM_USER_FILTER_DROPDOWN_BUTTON_XPATH}
    wait for page or element to load
    Element Should Be Visible  ${CSM_FILTER_LIST_BUTTON_XPATH}
    Element Should Be Visible  ${CSM_FILTER_LIST_CONTENT_XPATH}
    ${filter_list}=  Read Drop Down Data  ${CSM_FILTER_LIST_CONTENT_XPATH}
    Lists Should Be Equal  ${filter_list}  ${CSM_SEARCH_CONTENTS}

Verify Filter drop down Appear For User Search
    [Documentation]  This keyword is to verify that filter drop down menu appears for user search
    Click Element  ${CSM_USER_FILTER_DROPDOWN_BUTTON_XPATH}
    wait for page or element to load
    Element Should Be Visible  ${CSM_FILTER_LIST_BUTTON_XPATH}
    Element Should Be Visible  ${CSM_FILTER_LIST_CONTENT_XPATH}

Verify Filter drop down Appear Correctly Over Filters
    [Documentation]  This keyword is to verify that filter drop down menu appears over the filters selection
    ${X}=  Get Horizontal Position    ${CSM_USER_FILTER_DROPDOWN_BUTTON_XPATH}
    Log To Console And Report  ${${X}}
    ${Y}=  Get Vertical Position    ${CSM_USER_FILTER_DROPDOWN_BUTTON_XPATH}
    Log To Console And Report  ${${Y}}
    Click Element  ${CSM_USER_FILTER_DROPDOWN_BUTTON_XPATH}
    wait for page or element to load  10s
    ${X1}=  Get Horizontal Position    ${CSM_FILTER_LIST_BUTTON_XPATH}
    Log To Console And Report  ${${X1}}
    ${Y1}=  Get Vertical Position    ${CSM_FILTER_LIST_BUTTON_XPATH}
    Log To Console And Report  ${${Y1}}
    Run Keyword If  ${X}== ${X1} and ${Y}== ${Y1}  log to console and report  ${CSM_FILTER_LIST_BUTTON_XPATH}
    ...  ELSE
    ...  Fail
