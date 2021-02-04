*** Settings ***
Resource  ../common/common.robot
Library     SeleniumLibrary
Variables  ../common/element_locators.py
Variables  ../common/common_variables.py

*** Keywords ***
Navigate To About
    Wait Until Element Is Visible  ${MAINTENANCEM_MENU_ID}  timeout=10
    Navigate To Page  MAINTENANCEM_MENU_ID  ABOUT_VIEW_ID

Click Issuer Option
    Wait Until Element Is Visible  ${ISSUER_DETAILS_TAB_ID}  timeout=10
    click Element  ${ISSUER_DETAILS_TAB_ID} 

Click Subject Option
    Wait Until Element Is Visible  ${SUBJECT_DETAILS_TAB_ID}  timeout=10
    click Element  ${SUBJECT_DETAILS_TAB_ID}  

Verify Issuer Details 
    sleep  3s
    Wait Until Element Is Visible  ${ISSUER_COMMON_NAME_VALUE_ID}  timeout=10
    Verify message  ISSUER_COMMON_NAME_VALUE_ID  ${COMMON_NAME_SSL_MESSAGE}
    Verify message  ISSUER_COUNTRY_NAME_VALUE_ID  ${COUNTRY_NAME_SSL_MESSAGE}
    Verify message  ISSUER_LOCALITY_NAME_VALUE_ID  ${LOCALITY_NAME_SSL_MESSAGE}
    Verify message  ISSUER_ORGANIZATION_VALUE_ID  ${ORGANIZATION_NAME_SSL_MESSAGE}

Verify Subject Details 
    sleep  3s
    Wait Until Element Is Visible  ${SUBJECT_COMMON_NAME_VALUE_ID}  timeout=10
    Verify message  SUBJECT_COMMON_NAME_VALUE_ID  ${COMMON_NAME_SSL_MESSAGE}
    Verify message  SUBJECT_COUNTRY_NAME_VALUE_ID  ${COUNTRY_NAME_SSL_MESSAGE}
    Verify message  SUBJECT_LOCALITY_NAME_VALUE_ID  ${LOCALITY_NAME_SSL_MESSAGE}
    Verify message  SUBJECT_ORGANIZATION_VALUE_ID  ${ORGANIZATION_NAME_SSL_MESSAGE}
