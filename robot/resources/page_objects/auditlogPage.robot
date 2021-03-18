*** Settings ***
Library    OperatingSystem
Library    SeleniumLibrary
Resource   ${EXECDIR}/resources/common/common.robot
Variables  ${EXECDIR}/resources/common/element_locators.py
Variables  ${EXECDIR}/resources/common/common_variables.py

*** Keywords ***

Navigate To Audit Log Section
    [Documentation]  Test keyword is for navigating to Audit Log Section
    Wait Until Element Is Visible  ${MAINTENANCE_MENU_ID}  timeout=30
    Navigate To Page  MAINTENANCE_MENU_ID  AUDIT_LOG_TAB_ID
    ${CHROME_OPTIONS}=  Evaluate  sys.modules['selenium.webdriver'].ChromeOptions()  sys, selenium.webdriver
    Log To Console And Report  ${CHROME_OPTIONS}

Click On View Audit Log Button
    [Documentation]  Test keyword is for clicking on View Audit Log Button
    Wait Until Element Is Visible  ${AUDIT_LOG_VIEW_BUTTON_ID}  timeout=30
    Click Button  ${AUDIT_LOG_VIEW_BUTTON_ID}

Click On Download Audit Log Button
    [Documentation]  Test keyword is for clicking on Download Audit Log Button
    Wait Until Element Is Visible  ${AUDIT_LOG_DOWNLOAD_BUTTON_ID}  timeout=30
    Click Button  ${AUDIT_LOG_DOWNLOAD_BUTTON_ID}

Select Audit Log Details
    [Documentation]  Test keyword is for generatting audit log of given details
    [Arguments]  ${component}  ${duration}
    ${component}=  Convert To Upper Case  ${component}
    Log To Console And Report  generating audit log for ${component}
    Log To Console And Report  generating audit log since ${duration}
    Wait Until Element Is Visible  ${AUDIT_LOG_COMPONENT_DROP_DOWN_ID}  timeout=30
    Click Element  ${AUDIT_LOG_COMPONENT_DROP_DOWN_ID}
    Click Element  ${component}
    Wait Until Element Is Visible  ${AUDIT_LOG_TIME_PERIOD_DROP_DOWN_ID}  timeout=30
    Click Element  ${AUDIT_LOG_TIME_PERIOD_DROP_DOWN_ID}
    Click Element  ${duration}

View Audit Log
    [Documentation]  Test keyword is for viewing audit log of given details
    [Arguments]  ${component}  ${duration}
    Select Audit Log Details  ${component}  ${duration}
    Click On View Audit Log Button

Download Audit Log
    [Documentation]  Test keyword is for downloading audit log of given details
    [Arguments]  ${component}  ${duration}
    Select Audit Log Details  ${component}  ${duration}
    Click On Download Audit Log Button

Verify Audit Log Generated
    [Documentation]  Test keyword is to verify that audit log details has shown
    Sleep  5s  #  Audit log need time to load
    ${text}=  get text  ${LOGGED_IN_USER_NAME_ID}
    Should Not Be Empty  ${AUDIT_LOG_DATA_ID}

Verify Audit Log Downloaded
    [Documentation]  Test keyword is to verify that audit log details has downloaded
    [Arguments]  ${path}  ${audit_type}
    Sleep  5s  #  Audit log need time to load
    ${files}=  List Files In Directory  ${path}  ${audit_type}*.gz
    Log To Console And Report  ${files}
    Should Not Be Empty  ${files}
