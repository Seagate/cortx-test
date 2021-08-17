*** Settings ***
Resource  ../../resources/common/common.robot
Library     SeleniumLibrary
Variables  ../common/element_locators.py

*** Variables ***

*** Keywords ***

Check S3 Account Exists
    [Documentation]  This keyword is used to check S3 account exists.
    [Arguments]  ${S3_account_table}    ${expected_s3_account}
    ${s3_account_table_data}=   Read Table Data   ${S3_account_table}
    List Should Contain Value      ${s3_account_table_data}     ${expected_s3_account}

Action on the table
    [Documentation]  This keyword is to check user can perform action on the user table.
    [Arguments]  ${USER_NAME}  ${ACTION_ELEMENT_XPATH}
    ${CSM_account_table_data}=   Action On The Table Element   ${${ACTION_ELEMENT_XPATH}}  ${USER_NAME}

