*** Settings ***
Resource  ../common/common.robot
Library     SeleniumLibrary
Variables  ../common/element_locators.py
Variables  ../common/common_variables.py

*** Keywords ***
Check Setting Option Not Exists
    [Documentation]  Test keyword is for setting  Section
    Page Should Not Contain Element  ${SETTINGS_ID}
  
Check Maintenance Option Not Exists
    [Documentation]  Test keyword is for maintenance  Section
    Page Should Not Contain Element  ${MAINTENANCE_MENU_ID}
  
Check Dashboard Option Not Exists
    [Documentation]  Test keyword is for dashboard  Section
    Page Should Not Contain Element  ${DASHBOARD_MENU_ID}

Check Health Option Not Exists
    [Documentation]  Test keyword is for health  Section
    Page Should Not Contain Element  ${HEALTH}

Check Create CSM User Option Not Exists
    [Documentation]  Test that S3 account user must not have access to create CSM user
    Page Should Not Contain Element  ${ADMINISTRATIVE_USER_TAB_ID}
    
Check Alert Icon Not Exists
    [Documentation]  Test Alert icon should not be visible to s3 account user Verify Alert icon should not be visible to s3 account user
    Page Should Not Contain Element  ${ALERT_IMAGE_2_ID}

Check Associated S3 Account Exists
    [Documentation]  Test S3 account user should only be able to see S3 account details of the accounts which are associated with its account
    [Arguments]  ${expected_s3_account}  ${email}
    wait until element is visible  ${S3_ACCOUNTS_TABLE_XPATH}  timeout=60
    ${s3_account_table_data}=   Read Table Data  ${S3_ACCOUNTS_TABLE_XPATH}
    List Should Contain Value  ${s3_account_table_data}  ${expected_s3_account}
	List Should Contain Value  ${s3_account_table_data}  ${email}
