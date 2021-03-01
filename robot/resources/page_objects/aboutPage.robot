*** Settings ***
Resource  ../common/common.robot
Library     SeleniumLibrary
Variables  ../common/element_locators.py
Variables  ../common/common_variables.py

*** Keywords ***
Navigate To About
    [Documentation]  Test keyword is for navigating to about Section
    Wait Until Element Is Visible  ${MAINTENANCE_MENU_ID}  timeout=10
    Navigate To Page  MAINTENANCE_MENU_ID  ABOUT_VIEW_ID

Click Issuer Option
    [Documentation]  Test keyword is for clicking on Issuer Option
    Wait Until Element Is Visible  ${ISSUER_DETAILS_TAB_ID}  timeout=10
    click Element  ${ISSUER_DETAILS_TAB_ID} 

Click Subject Option
    [Documentation]  Test keyword is for clicking on subject tab option
    Wait Until Element Is Visible  ${SUBJECT_DETAILS_TAB_ID}  timeout=10
    click Element  ${SUBJECT_DETAILS_TAB_ID}  

Verify Issuer Details 
    [Documentation]  Test keyword is for verifying Issuer Tab Details
    sleep  3s
    Wait Until Element Is Visible  ${ISSUER_COMMON_NAME_VALUE_ID}  timeout=10
    Verify message  ISSUER_COMMON_NAME_VALUE_ID  ${COMMON_NAME_SSL_MESSAGE}
    Verify message  ISSUER_COUNTRY_NAME_VALUE_ID  ${COUNTRY_NAME_SSL_MESSAGE}
    Verify message  ISSUER_LOCALITY_NAME_VALUE_ID  ${LOCALITY_NAME_SSL_MESSAGE}
    Verify message  ISSUER_ORGANIZATION_VALUE_ID  ${ORGANIZATION_NAME_SSL_MESSAGE}

Verify Subject Details 
    [Documentation]  Test keyword is for Verifing Subject tab Details
    sleep  3s
    Wait Until Element Is Visible  ${SUBJECT_COMMON_NAME_VALUE_ID}  timeout=10
    Verify message  SUBJECT_COMMON_NAME_VALUE_ID  ${COMMON_NAME_SSL_MESSAGE}
    Verify message  SUBJECT_COUNTRY_NAME_VALUE_ID  ${COUNTRY_NAME_SSL_MESSAGE}
    Verify message  SUBJECT_LOCALITY_NAME_VALUE_ID  ${LOCALITY_NAME_SSL_MESSAGE}
    Verify message  SUBJECT_ORGANIZATION_VALUE_ID  ${ORGANIZATION_NAME_SSL_MESSAGE}
