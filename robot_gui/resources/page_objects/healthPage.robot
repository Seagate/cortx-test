*** Settings ***
Library    SeleniumLibrary
Resource   ${RESOURCES}/resources/page_objects/loginPage.robot
Resource   ${RESOURCES}/resources/common/common.robot
Variables  ${RESOURCES}/resources/common/element_locators.py

*** Keywords ***

Check Health Option Not Exists
    [Documentation]  This keyword is to check that user does not have access to Health page
    wait for page or element to load
    Page Should Not Contain Element  ${HEALTH_MENU_ID}

Check Health Option Exists
    [Documentation]  This keyword is to check that user does have access to Health page
    wait for page or element to load
    Page Should Contain Element  ${HEALTH_MENU_ID}

Verify State
    [Documentation]  This Keyword is to verify status on health resource in table.
    [Arguments]  ${status}  ${row}  ${column}
    sleep  2s
    Log To Console And Report   ${RESOURCE_STATUS_XPATH} ${status} ${row} ${column}
    ${Action_element} =  Format String  ${RESOURCE_STATUS_XPATH}  ${row}  ${column}
    Log To Console And Report   ${Action_element}
    ${text}=   Get Element Attribute  ${Action_element}  attribute=title
    Log To Console And Report  ${text}
    Should Contain  ${text}  ${status}

Check if Node status
    [Documentation]  Find and mark Fail if alert description already exist
    [Arguments]  ${ID}  ${status}
    ${found}=  Set Variable  False
    ${row}=  Evaluate  ${ID} + 4
    ${column}=  Set Variable  3
    Log To Console And Report  id = ${ID} state = ${status} row = ${row} column = ${column}
    Navigate To Page  HEALTH_MENU_ID  TABULAR_TAB_ID
    wait for page or element to load  3s  # Took time to load status
    Capture Page Screenshot
    ${resource_table_row_data}=  Read Table Data  ${RESOURCE_TABLE_ROW_XPATH}
    # loop through all alerts row
    FOR    ${item}     IN      @{resource_table_row_data}
        ${found}=  Run Keyword And Return Status  Should Contain  ${item}  node\n${ID}
        Run Keyword If  ${found} == True  # found
        ...  Run Keywords
        ...  Verify State  ${status}  ${row}  ${column}
        ...  AND  Capture Page Screenshot
        ...  AND  Exit For Loop
    END
    Run Keyword If  ${found} == False
    ...  Run Keywords
    ...  AND  Log To Console And Report  node ${ID} not found, failing
    ...  AND  Capture Page Screenshot
    ...  AND  Fail  # node not found, failing

Check if Cluster status
    [Documentation]  Find and mark Fail if alert description already exist
    [Arguments]  ${status}
    ${found}=  Set Variable  False
    ${row}=  Set Variable  1
    ${column}=  Set Variable  3
    Log To Console And Report  state = ${status} row = ${row} column = ${column}
    Navigate To Page  HEALTH_MENU_ID  TABULAR_TAB_ID
    wait for page or element to load  3s  # Took time to load status
    Capture Page Screenshot
    ${resource_table_row_data}=  Read Table Data  ${RESOURCE_TABLE_ROW_XPATH}
    # loop through all alerts row
    FOR    ${item}     IN      @{resource_table_row_data}
        ${found}=  Run Keyword And Return Status  Should Contain  ${item}  cluster\n
        Run Keyword If  ${found} == True  # found
        ...  Run Keywords
        ...  Verify State  ${status}  ${row}  ${column}
        ...  AND  Capture Page Screenshot
        ...  AND  Exit For Loop
    END
    Run Keyword If  ${found} == False
    ...  Run Keywords
    ...  AND  Log To Console And Report  cluster not found, failing
    ...  AND  Capture Page Screenshot
    ...  AND  Fail  # cluster not found, failing
