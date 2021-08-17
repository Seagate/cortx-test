*** Settings ***
Library    OperatingSystem
Library    SeleniumLibrary
Resource   ${RESOURCES}/resources/common/common.robot
Variables  ${RESOURCES}/resources/common/element_locators.py
Variables  ${RESOURCES}/resources/common/common_variables.py

*** Keywords ***

Navigate To Audit Log Section
    [Documentation]  Test keyword is for navigating to Audit Log Section
    Wait Until Element Is Visible  ${MAINTENANCE_MENU_ID}  timeout=30
    Navigate To Page  MAINTENANCE_MENU_ID  AUDIT_LOG_TAB_ID

Click On View Audit Log Button
    [Documentation]  Test keyword is for clicking on View Audit Log Button
    Wait Until Element Is Visible  ${AUDIT_LOG_VIEW_BUTTON_ID}  timeout=30
    Click Button  ${AUDIT_LOG_VIEW_BUTTON_ID}

Click On Download Audit Log Button
    [Documentation]  Test keyword is for clicking on Download Audit Log Button
    Wait Until Element Is Visible  ${AUDIT_LOG_DOWNLOAD_BUTTON_ID}  timeout=30
    Click Button  ${AUDIT_LOG_DOWNLOAD_BUTTON_ID}

Select Audit Log Details
    [Documentation]  Test keyword is for generating audit log of given details
    [Arguments]  ${component}
    ${component}=  Convert To Upper Case  ${component}
    Log To Console And Report  generating audit log for ${component}
    Wait Until Element Is Visible  ${AUDIT_LOG_COMPONENT_DROP_DOWN_ID}  timeout=30
    Click Element  ${AUDIT_LOG_COMPONENT_DROP_DOWN_ID}
    Click Element  ${component}
    Wait Until Element Is Visible  ${AUDIT_LOG_TIME_PERIOD_DROP_DOWN_ID}  timeout=30
    Click Element  ${AUDIT_LOG_TIME_PERIOD_DROP_DOWN_ID}
    wait for page or element to load  2s
    Wait Until Element Is Visible  ${AUDIT_LOG_CURRENT_DATE_XPATH}
    Click Element  ${AUDIT_LOG_CURRENT_DATE_XPATH}
    Click Element  ${AUDIT_LOG_AVAILABLE_DATE_XPATH}

View Audit Log
    [Documentation]  Test keyword is for viewing audit log of given details
    [Arguments]  ${component}
    Select Audit Log Details  ${component}
    Click On View Audit Log Button

Download Audit Log
    [Documentation]  Test keyword is for downloading audit log of given details
    [Arguments]  ${component}
    Select Audit Log Details  ${component}
    Click On Download Audit Log Button

Verify Audit Log Generated
    [Documentation]  Test keyword is to verify that audit log details has shown
    wait for page or element to load  #  Audit log need time to load
    ${text}=  get text  ${CSM_AUDIT_LOG_TABLE_XPATH}
    Should Not Be Empty  ${text}

Verify Audit Log Downloaded
    [Documentation]  Test keyword is to verify that audit log details has downloaded
    [Arguments]  ${path}  ${audit_type}
    Sleep  5s  #  Audit log need time to load
    ${files}=  List Files In Directory  ${path}  ${audit_type}*.gz
    Log To Console And Report  ${files}
    Should Not Be Empty  ${files}

Verify CSM Audit Log In Tabular format
    [Documentation]  Test keyword is to verify that csm audit log details has shown in tabular format
     View Audit Log  CSM
     wait for page or element to load  #  Audit log need time to load
     Page Should Contain Element  ${CSM_AUDIT_LOG_TABLE_XPATH}
     ${csm_audit_log_table_data}=  Read Table Data  ${CSM_AUDIT_LOG_TABLE_XPATH}
     Should Not Be Empty  ${csm_audit_log_table_data}

Select Audit Log Component
    [Documentation]  Test keyword is for Select Audit Log for given component
    [Arguments]  ${component}
    ${component}=  Convert To Upper Case  ${component}
    Log To Console And Report  generating audit log for ${component}
    Wait Until Element Is Visible  ${AUDIT_LOG_COMPONENT_DROP_DOWN_ID}  timeout=30
    Click Element  ${AUDIT_LOG_COMPONENT_DROP_DOWN_ID}
    Click Element  ${component}

Select current date
    [Documentation]  Test keyword is to select current date as audit log's duration
    Wait Until Element Is Visible  ${AUDIT_LOG_TIME_PERIOD_DROP_DOWN_ID}  timeout=30
    Click Element  ${AUDIT_LOG_TIME_PERIOD_DROP_DOWN_ID}
    Wait Until Element Is Visible  ${CURRENT_DATE_IN_DATE_PICKER_XPATH}  timeout=30
    Double Click Element  ${CURRENT_DATE_IN_DATE_PICKER_XPATH}

Search Audit Log Data
    [Documentation]  Test keyword is to select current date as audit log's duration
    [Arguments]  ${data}
    Wait Until Element Is Visible  ${AUDIT_LOG_SEARCH_BAR_XPATH}  timeout=30
    input text  ${AUDIT_LOG_SEARCH_BAR_XPATH}  ${data}
    Click Element  ${AUDIT_LOG_SEARCH_ICON_XPATH}

Select filter for Audit Log
    [Documentation]  Test keyword is to select current date as audit log's duration
    [Arguments]  ${filter}
    wait for page or element to load
    Click Element  ${AUDIT_LOG_FILTER_DROPDOWN_BUTTON_XPATH}
    wait for page or element to load  2s
    ${element}=  Format String  ${AUDIT_LOG_ROLE_SELECT_XPATH}  ${filter}
    Click Element  ${element}
    wait for page or element to load

Verify Search Operation Is Working
    [Documentation]  Test keyword is to select current date as audit log's duration
    [Arguments]  ${data}
    ${all data}=  Get WebElements  ${AUDIT_LOG_FETCH_ALL_LOG_XPATH}
    ${element}=  Format String  ${AUDIT_LOG_FETCH_SEARCHED_LOG_XPATH}  ${data}
    ${elements}=  Get WebElements  ${element}
    ${valid_data}=  Get Length  ${all data}
    ${count}=  Get Length  ${elements}
    ${valid_data}=  Evaluate  ${valid_data} / int(8)
    should be equal as integers  ${valid_data}  ${count}
