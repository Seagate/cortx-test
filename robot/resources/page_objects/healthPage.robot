*** Settings ***
Library    SeleniumLibrary
Resource   ${RESOURCES}/resources/page_objects/loginPage.robot
Resource   ${RESOURCES}/resources/common/common.robot
Variables  ${RESOURCES}/resources/common/element_locators.py

*** Keywords ***

Check Health Option Not Exists
    [Documentation]  This keyword is to check that user does not have access to Health page
    wait for page or element to load
    Page Should Not Contain Element  ${HEALTH_TAB_ID}

Check Health Option Exists
    [Documentation]  This keyword is to check that user does have access to Health page
    wait for page or element to load
    Page Should Contain Element  ${HEALTH_TAB_ID}

