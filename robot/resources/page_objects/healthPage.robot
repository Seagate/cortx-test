*** Settings ***
Library    SeleniumLibrary
Resource   ${EXECDIR}/resources/page_objects/loginPage.robot
Resource   ${EXECDIR}/resources/common/common.robot
Variables  ${EXECDIR}/resources/common/element_locators.py

*** Keywords ***

Check Health Option Not Exists
    [Documentation]  This keyword is to check that user does not have access to Health page
    Page Should Not Contain Element  ${HEALTH_TAB_ID}

Check Health Option Exists
    [Documentation]  This keyword is to check that user does have access to Health page
    Page Should Contain Element  ${HEALTH_TAB_ID}

Check Health Option URL access
    [Documentation]  This keyword is to check if URL is accessed, 
    Run Keyword If  ${headless} == True  Open URL In Headless  ${url}health  ${browser}
    ...  ELSE  Open URL  ${url}health  ${browser}
    #Page Should Contain 

