*** Settings ***
Documentation  This is the common resources file containing common keywords
Library    SeleniumLibrary    screenshot_root_directory=reports/screenshots
Library    String
Library    DateTime
Library    Collections
Library    ${RESOURCES}/utils/Download.py
Library    ${RESOURCES}/utils/create-SSL.py
Library    ${RESOURCES}/utils/generate_bucket_policy.py
Library    ${RESOURCES}/utils/general_utility.py
Variables  ${RESOURCES}/resources/common/common_variables.py
Variables  ${RESOURCES}/resources/common/element_locators.py

*** Keywords ***

Log To Console And Report
    [Documentation]  This Keyword is for logging the same string to console and report.
    [Arguments]  ${log_message}
    log  ${log_message}
    Log To Console  ${\n}${log_message}

Navigate To Page
    [Documentation]  This Keyword is for navigating to certain page
    [Arguments]  ${page_name}  ${sub_page}=False
    log to console and report  Navigating to ${page_name}
    wait until element is visible  ${${page_name}}  timeout=60
    wait for page or element to load
    Click Element  ${${page_name}}
    wait for page or element to load
    ${value}=  Convert To Boolean  ${sub_page}
    Run Keyword If  ${value}
    ...  Click Element  ${${sub_page}}

Read Table Data
    [Documentation]  This Keyword is for reading the data from the html table and it returns the data in list format.
    [Arguments]  ${table_element}
    @{table_data}=    Create List
    @{table_elements}=  Get WebElements  ${table_element}
    sleep  2s
    FOR  ${elements}  IN  @{table_elements}
            ${text}=    Get Text    ${elements}
            Append To List  ${table_data}  ${text}
    END
    Log To Console And Report   ${table_data}
    [Return]   @{table_data}

Read Selective Table Data
    [Documentation]   Return list of target column values if reference column has reference value
    [Arguments]  ${table_column_xpath}  ${reference_value}  ${reference_column}  ${target_column}
    @{output}=    Create List
    @{reference_list}=  Get Column Data  ${table_column_xpath}  ${reference_column}
    @{target_list}=  Get Column Data  ${table_column_xpath}  ${target_column}
    FOR  ${reference}  ${target}  IN ZIP  ${reference_list}  ${target_list}
        Run Keyword If  "${reference}" == "${reference_value}"  Append To List  ${output}  ${target}
    END
    [Return]   @{output}

Get Column Data
    [Documentation]  Returns column data from given table data
    [Arguments]  ${column_element}  ${column_no}
    @{column_data}=    Create List
    ${column_xpath}=  Format String  ${column_element}  ${column_no}
    @{table_elements}=  Get WebElements  ${column_xpath}
    sleep  2s
    FOR  ${elements}  IN  @{table_elements}
            ${text}=    Get Text    ${elements}
            Append To List  ${column_data}  ${text}
    END
    [Return]   @{column_data}

Action On The Table Element
    [Documentation]  This Keyword is for performing actions like edit/delete on particular user/element in html table.
    [Arguments]  ${Element_for_action}  ${USER_NAME}
    sleep  2s
    Log To Console And Report   ${Element_for_action}
    ${Action_element} =  Format String  ${Element_for_action}  ${USER_NAME}
    Log To Console And Report   ${Action_element}
    ${table_elements}=  Get WebElement  ${Action_element}
    sleep  2s
    click element   ${table_elements}
    sleep  2s

Verify Action Disabled On The Table Element
    [Documentation]  This Keyword is for verifying actions e.g. edit/delete on particular user/element in html table are not present.
    [Arguments]  ${Element_for_action}  ${USER_NAME}
    sleep  2s
    Log To Console And Report   ${Element_for_action}
    ${Action_element} =  Format String  ${Element_for_action}  ${USER_NAME}
    Log To Console And Report   ${Action_element}
    Element Should Not Be Visible  ${Action_element}

Verify Action Enabled On The Table Element
    [Documentation]  This Keyword is for verifying actions e.g. edit/delete on particular user/element in html table is present.
    [Arguments]  ${Element_for_action}  ${USER_NAME}
    sleep  2s
    Log To Console And Report   ${Element_for_action}
    ${Action_element} =  Format String  ${Element_for_action}  ${USER_NAME}
    Log To Console And Report   ${Action_element}
    Element Should Be Visible  ${Action_element}

Generate New User Name
    [Documentation]  Functionality to generate new user name
    ${str}=  Get Current Date
    ${str}=  Replace String  ${str}  :  ${EMPTY}
    ${str}=  Replace String  ${str}  .  ${EMPTY}
    ${str}=  Replace String  ${str}  -  ${EMPTY}
    ${str}=  Replace String  ${str}  ${space}  ${EMPTY}
    ${str}=  catenate  SEPARATOR=  testuser  ${str}
    [Return]  ${str}

Generate New User Email
    [Documentation]  Functionality to generate new user email
    ${name}=  Generate New User Name
    ${email}=  catenate  SEPARATOR=  ${name}  @seagate.com
    [Return]  ${email}

Generate New Password
    [Documentation]  Functionality to generate valid password
    ${upper_case}=  Generate Random String  2  [UPPER]
    ${lower_case}=  Generate Random String  2  [LOWER]
    ${numbers}=  Generate Random String  2  [NUMBERS]
    ${special_char}=  Generate random string    2    !@#$%^&*()
    ${password}=  Catenate  SEPARATOR=  ${upper_case}  ${lower_case}  ${numbers}  ${special_char}
    Log To Console And Report  ${password}
    [Return]  ${password}

Verify message
    [Documentation]  This keyword verifies error messages for provided element with expected message.
    [Arguments]  ${element_locator}  ${message_to_verify}
    wait until element is visible  ${${element_locator}}  timeout=30
    ${msg_from_gui}=  get text  ${${element_locator}}
    Log To Console And Report  message from guI is ${msg_from_gui}
    should be equal  ${msg_from_gui}  ${message_to_verify}

Upload File
    [Documentation]  This keyword upload files to required webelement
    [Arguments]  ${element_locator}  ${file_path}
    Sleep  5s
    wait until element is visible  ${${element_locator}}  timeout=60
    Choose File  id=${${element_locator}}  ${file_path}

Get element list
    [Documentation]  This keyword returns the list of elements.
    [Arguments]  ${locator}
    wait until element is visible  ${locator}  timeout=30
    @{element_list}=  Get WebElements  ${locator}
    Log To Console And Report  ${locator}
    [Return]  @{element_list}

Get text of elements from elements list
    [Documentation]  This keyword returns the list of element text from the element list.
    [Arguments]  ${locator}
    ${text_list}=    Create List
    @{text_elements}=  Get element list  ${locator}
    FOR  ${elements}  IN  @{text_elements}
            ${text}=    Get Text    ${elements}
            Append To List  ${text_list}  ${text}
    END
    Log To Console And Report  ${text_list}
    [Return]  ${text_list}

wait for page or element to load
    [Documentation]  This keyword is to wait for page or element to wait for provided time.
    [Arguments]  ${time}=5s
    sleep  ${time}

Go Forward
    Execute Javascript  history.forward()

Check element is not visiable
    [Documentation]  This kaeyword is to verify that provided web element is not visiable on screen
    [Arguments]  ${element_locator}
    Element Should Not Be Visible  ${${element_locator}}
