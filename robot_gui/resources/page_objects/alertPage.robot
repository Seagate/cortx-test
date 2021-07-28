*** Settings ***
Library    SeleniumLibrary
Resource   ${RESOURCES}/resources/page_objects/loginPage.robot
Resource   ${RESOURCES}/resources/page_objects/userSettingsLocalPage.robot
Resource   ${RESOURCES}/resources/common/common.robot
Variables  ${RESOURCES}/resources/common/element_locators.py

*** Keywords ***

Click AlertPage Image
    [Documentation]  click on bell icon to open Alert page
    Click Element    ${ALERT_IMAGE_2_ID}

Click AlertPageDashboard Image
    [Documentation]  On Dashboard page, click on '+' image from Alert section to open Alert page
    Click Element    ${ALERT_IMAGE_1_ID}

Click Details Button
    [Documentation]  On Alert Page, click on Details icon
    Click Element    ${ALERT_DETAILS_PAGE_ICON_XPATH}

Click AlertEventDetails Button
    [Documentation]  On Alert Page, click on Details icon
    Click Element    ${ALERT_MORE_DETAILS_ICON_XPATH}

Click AlertEventDetailsClose Button
    [Documentation]  On Alert Page, click on Details icon
    Click Element    ${ALERT_MORE_DETAILS_CLOSE_ICON_XPATH}

Click NewAlert Tab
    [Documentation]  click on New Alert tab on Alert page
    Click Element    ${NEW_ALERT_ID}

Click ActiveAlert Tab
    [Documentation]  click on Active Alert tab on Alert page
    Click Element    ${ACTIVE_ALERT_ID}

Click AlertHistory Tab
    [Documentation]  click on Alert History tab on Alert page
    Click Element    ${ALERT_HISTORY_ID}

Capture AlertEventDetails Screenshot
    [Documentation]  On Alert Details Page, Capture More Alerts Details Screenshot
    [Arguments]  ${filename}
    Capture Element Screenshot  ${ALERT_MORE_DETAILS_BODY_XPATH}  ${filename}

Click Comments Button
    [Documentation]  On Alert Page, click on Comment icon
    wait until element is visible  ${ALERT_COMMENT_ICON_XPATH}  timeout=30
    Click Element    ${ALERT_COMMENT_ICON_XPATH}

Add CommentInCommentBox Text
    [Documentation]  Add Comment in The CommentBox popup
    wait until element is visible  ${ALERT_COMMENT_TEXT_ID}  timeout=30
    input text  ${ALERT_COMMENT_TEXT_ID}  ${TEST_COMMENT}
    Click Element    ${ALERT_COMMENT_SAVE_BUTTON_ID}

Click CommentsClose Button
    [Documentation]  On Alert Comment Pop Up, click on close Button
    Click Element    ${ALERT_COMMENT_CLOSE_BUTTON_ID}

Click CommentsClose Image
    [Documentation]  On Alert Comment Pop Up, click on 'X' icon to close
    Click Element    ${ALERT_COMMENT_CLOSE_IMAGE_ID}

Verify Presence of Details Comments
    [Documentation]  Verify Presence of Details and Comments Buttons on Alert Action for monitor user
    Page Should Contain Element  ${ALERT_DETAILS_PAGE_ICON_XPATH}
    Page Should Contain Element  ${ALERT_COMMENT_ICON_XPATH}

Verify Presence of AlertEventDetails Image
    [Documentation]  Verify Presence of Details Icon on Alert Details Page
    Page Should Contain Element  ${ALERT_MORE_DETAILS_ICON_XPATH}

Verify Presence of AlertEventDetailsBody Close 
    [Documentation]  Verify Presence of More Alert Details and Close Icon
    Page Should Contain Element  ${ALERT_MORE_DETAILS_BODY_XPATH}
    Page Should Contain Element  ${ALERT_MORE_DETAILS_CLOSE_ICON_XPATH}

Verify Absence of Acknowledge
    [Documentation]  Verify Absence of Acknowledge for monitor user
    Page Should Not Contain Element  ${ALERT_ACKNOWLEDGE_ICON_XPATH}

Verify Presence of Details Comments Acknowledge
    [Documentation]  Verify Presence of Details, Comments and Acknowledge Buttons on Alert Action
    Page Should Contain Element  ${ALERT_DETAILS_PAGE_ICON_XPATH}
    Page Should Contain Element  ${ALERT_COMMENT_ICON_XPATH}

Verify Absence of comment textbox
    [Documentation]  this keyword Verify that comment textbox is not present for monitor user.
    Page Should Not Contain Element  ${ALERT_COMMENT_TEXT_ID}

Verify comment on alert
     [Documentation]  this keyword adds comments and verifies it
     Click AlertPageDashboard Image
     Click Comments Button
     Add CommentInCommentBox Text
     Click CommentsClose Image
     wait for page or element to load  2s
     Click Comments Button
     wait for page or element to load
     ${comment_text}=  Get text of elements from elements list  ${ALERTS_COMMENT_TEXT_XPATH}
     List Should Contain Value  ${comment_text}  ${TEST_COMMENT}
     Click CommentsClose Image

Verify Presence SSL certificate expires alert
    [Documentation]  Verify Presence of SSL certificate expires alert
    [Arguments]  ${days}
    ${found}=  Set Variable  False
    ${type}=  Set Variable  Resource type: node:iem
    ${Description} =  Set Variable If  ${days} == 0  SSL certificate expired
    ...  ${days} > 0  ${days} day(s) left. Please refer user guide on how to update the certificate.
    Log To Console And Report  ${Description}
    Click AlertPage Image
    wait for page or element to load  10s  # Took time to load all alerts
    Click NewAlert Tab
    wait for page or element to load  10s  # Took time to load all alerts
    ${alert_table_row_data}=  Read Table Data  ${ALERT_TABLE_ROW_XPATH}
    # loop through all alerts row
    FOR    ${item}     IN      @{alert_table_row_data}
        ${found}=  Run Keyword And Return Status  Should Contain  ${item}  ${Description}
        Run Keyword If  ${found} == True  # Description found in the alert
        ...  Run Keywords
        ...  Should Contain  ${item}  ${type}
        ...  AND  Exit For Loop  # as soon as correct Description found, exit from loop, no neet ot check all alaerts
    END
    Run Keyword If  ${found} == False
    ...  Run Keywords
    ...  Log To Console And Report  ${found}
    ...  AND  Capture Page Screenshot
    ...  AND  Fail  # correct Description not found in the alert, failing test

Acknowledge alert
    [Arguments]  ${servicename}
    Action On The Table Element  ${PARTICULAR_ALERT_ACKNOWLEDGE_ICON_XPATH}  ${servicename}

Fail if alert already exists in New alerts tab
    [Documentation]  Find and mark Fail if alert description already exist
    [Arguments]  ${description} 
    ${found}=  Set Variable  False
    Log To Console And Report  ${description}
    Click AlertPage Image
    wait for page or element to load  10s  # Took time to load all alerts
    Click NewAlert Tab
    wait for page or element to load  10s  # Took time to load all alerts
    ${alert_table_row_data}=  Read Table Data  ${ALERT_TABLE_ROW_XPATH}
    # loop through all alerts row
    FOR    ${item}     IN      @{alert_table_row_data}
        ${found}=  Run Keyword And Return Status  Should Contain  ${item}  ${description}
        Run Keyword If  ${found} == True  # Description found in the alert
        ...  Run Keywords
        ...  Log To Console And Report  ${found}
        ...  AND  Capture Page Screenshot
        ...  AND  Fail  # description found in the alert, failing test
    END

Print alert table
    [Documentation]  Verify Presence of any alert with description
    Click AlertPage Image
    wait for page or element to load  10s  # Took time to load all alerts
    Click NewAlert Tab
    wait for page or element to load  10s  # Took time to load all alerts
    ${alert_table_row_data}=  Read Table Data  ${ALERT_TABLE_ROW_XPATH}
    # loop through all alerts row
    FOR    ${item}     IN      @{alert_table_row_data}
        Log To Console And Report  ${item}
    END

Check if alert exists in New alerts tab
    [Documentation]  Find and mark Fail if alert description not exist
    [Arguments]  ${description}
    ${found}=  Set Variable  False
    Log To Console And Report  ${description}
    wait for page or element to load  2s
    Click AlertPage Image
    wait for page or element to load  10s  # Took time to load all alerts
    Click NewAlert Tab
    wait for page or element to load  10s  # Took time to load all alerts
    ${alert_table_row_data}=  Read Table Data  ${ALERT_TABLE_ROW_XPATH}
    # loop through all alerts row
    FOR    ${item}     IN      @{alert_table_row_data}
        ${found}=  Run Keyword And Return Status  Should Contain  ${item}  ${description}
        Run Keyword If  ${found} == True  # Description found in the alert
        ...  Run Keywords
        ...  Log To Console And Report  ${found}
        ...  AND  Log To Console And Report  ${item}
        ...  AND  Capture Page Screenshot
        ...  AND  Exit For Loop  # as soon as correct Description found, exit from loop, no need to check all alerts
    END
    Run Keyword If  ${found} == False
    ...  Run Keywords
    ...  Log To Console And Report  ${found}
    ...  AND  Capture Page Screenshot
    ...  AND  Fail  # description not found in the alert, failing test

Fail if alert already exists in Active alerts tab
    [Documentation]  Find and mark Fail if alert description already exist
    [Arguments]  ${description}
    ${found}=  Set Variable  False
    Log To Console And Report  ${description}
    Click AlertPage Image
    wait for page or element to load  10s  # Took time to load all alerts
    Click ActiveAlert Tab
    wait for page or element to load  10s  # Took time to load all alerts
    Capture Page Screenshot
    ${alert_table_row_data}=  Read Table Data  ${ALERT_TABLE_ROW_XPATH}
    # loop through all alerts row
    FOR    ${item}     IN      @{alert_table_row_data}
        ${found}=  Run Keyword And Return Status  Should Contain  ${item}  ${description}
        Run Keyword If  ${found} == True  # Description found in the alert
        ...  Run Keywords
        ...  Log To Console And Report  ${found}
        ...  AND  Capture Page Screenshot
        ...  AND  Fail  # description found in the alert, failing test
    END

Check if alert exists in Active alerts tab
    [Documentation]  Find and mark Fail if alert description not exist
    [Arguments]  ${description}
    ${found}=  Set Variable  False
    Log To Console And Report  ${description}
    Click AlertPage Image
    wait for page or element to load  10s  # Took time to load all alerts
    Click ActiveAlert Tab
    wait for page or element to load  10s  # Took time to load all alerts
    Capture Page Screenshot
    ${alert_table_row_data}=  Read Table Data  ${ALERT_TABLE_ROW_XPATH}
    # loop through all alerts row
    FOR    ${item}     IN      @{alert_table_row_data}
        ${found}=  Run Keyword And Return Status  Should Contain  ${item}  ${description}
        Run Keyword If  ${found} == True  # Description found in the alert
        ...  Run Keywords
        ...  Log To Console And Report  ${found}
        ...  AND  Capture Page Screenshot
        ...  AND  Exit For Loop  # as soon as correct Description found, exit from loop, no need to check all alerts
    END
    Run Keyword If  ${found} == False
    ...  Run Keywords
    ...  Log To Console And Report  ${found}
    ...  AND  Capture Page Screenshot
    ...  AND  Fail  # description not found in the alert, failing test

Fail if alert already exists in Alert history tab
    [Documentation]  Find and mark Fail if alert description already exist
    [Arguments]  ${description}
    ${found}=  Set Variable  False
    Log To Console And Report  ${description}
    Click AlertPage Image
    wait for page or element to load  10s  # Took time to load all alerts
    Click AlertHistory Tab
    wait for page or element to load  10s  # Took time to load all alerts
    Capture Page Screenshot
    ${alert_table_row_data}=  Read Table Data  ${ALERT_TABLE_ROW_XPATH}
    # loop through all alerts row
    FOR    ${item}     IN      @{alert_table_row_data}
        ${found}=  Run Keyword And Return Status  Should Contain  ${item}  ${description}
        Run Keyword If  ${found} == True  # Description found in the alert
        ...  Run Keywords
        ...  Log To Console And Report  ${found}
        ...  AND  Capture Page Screenshot
        ...  AND  Fail  # description found in the alert, failing test
    END

Check if alert exists in Alert history tab
    [Documentation]  Find and mark Fail if alert description not exist
    [Arguments]  ${description}
    ${found}=  Set Variable  False
    Log To Console And Report  ${description}
    Click AlertPage Image
    wait for page or element to load  10s  # Took time to load all alerts
    Click AlertHistory Tab
    wait for page or element to load  10s  # Took time to load all alerts
    Capture Page Screenshot
    ${alert_table_row_data}=  Read Table Data  ${ALERT_TABLE_ROW_XPATH}
    # loop through all alerts row
    FOR    ${item}     IN      @{alert_table_row_data}
        ${found}=  Run Keyword And Return Status  Should Contain  ${item}  ${description}
        Run Keyword If  ${found} == True  # Description found in the alert
        ...  Run Keywords
        ...  Log To Console And Report  ${found}
        ...  AND  Capture Page Screenshot
        ...  AND  Exit For Loop  # as soon as correct Description found, exit from loop, no need to check all alerts
    END
    Run Keyword If  ${found} == False
    ...  Run Keywords
    ...  Log To Console And Report  ${found}
    ...  AND  Capture Page Screenshot
    ...  AND  Fail  # description not found in the alert, failing test

Fail if New alerts exist SW Service
    [Documentation]  Find and mark Fail if SW Service alerts exist
    [Arguments]  ${servicename}
    ${found1}=  Set Variable  False
    ${found2}=  Set Variable  False
    ${found3}=  Set Variable  False
    ${Description1} =  Set Variable  ${servicename} in failed state.
    ${Description2} =  Set Variable  ${servicename} in inactive state.
    ${Description3} =  Set Variable  ${servicename} in deactivating state.
    Log To Console And Report  ${Description1}
    Log To Console And Report  ${Description2}
    Log To Console And Report  ${Description3}
    Click AlertPage Image
    wait for page or element to load  10s  # Took time to load all alerts
    Click NewAlert Tab
    wait for page or element to load  10s  # Took time to load all alerts
    ${alert_table_row_data}=  Read Table Data  ${ALERT_TABLE_ROW_XPATH}
    # loop through all alerts row
    FOR    ${item}     IN      @{alert_table_row_data}
        ${found1}=  Run Keyword And Return Status  Should Contain  ${item}  ${Description1}
        Run Keyword If  ${found1} == True  # Description found in the alert
        ...  Run Keywords
        ...  Log To Console And Report  ${found1}
        ...  AND  Capture Page Screenshot
        ...  AND  Fail  # correct Description not found in the alert, failing test
        ${found2}=  Run Keyword And Return Status  Should Contain  ${item}  ${Description2}
        Run Keyword If  ${found2} == True  # Description found in the alert
        ...  Run Keywords
        ...  Log To Console And Report  ${found2}
        ...  AND  Capture Page Screenshot
        ...  AND  Fail  # correct Description not found in the alert, failing test
        ${found3}=  Run Keyword And Return Status  Should Contain  ${item}  ${Description3}
        Run Keyword If  ${found3} == True  # Description found in the alert
        ...  Run Keywords
        ...  Log To Console And Report  ${found2}
        ...  AND  Capture Page Screenshot
        ...  AND  Fail  # correct Description not found in the alert, failing test
    END

Verify failed alerts exist SW Service
    [Documentation]  Find and mark Fail if SW Service alerts not exist
    [Arguments]  ${servicename}
    ${found}=  Set Variable  False
    ${Description} =  Set Variable  ${servicename} in failed state.
    Log To Console And Report  ${Description}
    Click AlertPage Image
    wait for page or element to load  10s  # Took time to load all alerts
    Click NewAlert Tab
    wait for page or element to load  10s  # Took time to load all alerts
    ${alert_table_row_data}=  Read Table Data  ${ALERT_TABLE_ROW_XPATH}
    # loop through all alerts row
    FOR    ${item}     IN      @{alert_table_row_data}
        ${found}=  Run Keyword And Return Status  Should Contain  ${item}  ${Description}
        Run Keyword If  ${found} == True  # Description found in the alert
        ...  Run Keywords
        ...  Log To Console And Report  ${found}
        ...  AND  Capture Page Screenshot
    END
    Run Keyword If  ${found} == False
    ...  Run Keywords
    ...  Log To Console And Report  ${found}
    ...  AND  Capture Page Screenshot
    ...  AND  Fail  # description not found in the alert, failing

Verify inactive alerts exist SW Service
    [Documentation]  Find and mark Fail if SW Service alerts not exist
    [Arguments]  ${servicename}
    ${found}=  Set Variable  False
    ${Description} =  Set Variable  ${servicename}.service in inactive state.
    Log To Console And Report  ${Description}
    Click AlertPage Image
    wait for page or element to load  10s  # Took time to load all alerts
    Click NewAlert Tab
    wait for page or element to load  10s  # Took time to load all alerts
    ${alert_table_row_data}=  Read Table Data  ${ALERT_TABLE_ROW_XPATH}
    # loop through all alerts row
    FOR    ${item}     IN      @{alert_table_row_data}
        ${found}=  Run Keyword And Return Status  Should Contain  ${item}  ${Description}
        Run Keyword If  ${found} == True  # Description found in the alert
        ...  Run Keywords
        ...  Log To Console And Report  ${found}
        ...  AND  Capture Page Screenshot
    END
    Run Keyword If  ${found} == False
    ...  Run Keywords
    ...  Log To Console And Report  ${found}
    ...  AND  Capture Page Screenshot
    ...  AND  Fail  # description not found in the alert, failing

Verify deactivating alerts exist SW Service
    [Documentation]  Find and mark Fail if SW Service alerts not exist
    [Arguments]  ${servicename}
    ${found}=  Set Variable  False
    ${Description} =  Set Variable  ${servicename} in deactivating state.
    Log To Console And Report  ${Description}
    Click AlertPage Image
    wait for page or element to load  10s  # Took time to load all alerts
    Click NewAlert Tab
    wait for page or element to load  10s  # Took time to load all alerts
    ${alert_table_row_data}=  Read Table Data  ${ALERT_TABLE_ROW_XPATH}
    # loop through all alerts row
    FOR    ${item}     IN      @{alert_table_row_data}
        ${found}=  Run Keyword And Return Status  Should Contain  ${item}  ${Description}
        Run Keyword If  ${found} == True  # Description found in the alert
        ...  Run Keywords
        ...  Log To Console And Report  ${found}
        ...  AND  Capture Page Screenshot
    END
    Run Keyword If  ${found} == False
    ...  Run Keywords
    ...  Log To Console And Report  ${found}
    ...  AND  Capture Page Screenshot
    ...  AND  Fail  # description not found in the alert, failing

Verify and Acknowledge failed resolved alerts exist SW Service
    [Documentation]  Find and mark Fail if SW Service alerts not exist
    [Arguments]  ${servicename}
    ${found}=  Set Variable  False
    ${Description} =  Set Variable  ${servicename} in failed state.
    Log To Console And Report  ${Description}
    Click AlertPage Image
    wait for page or element to load  10s  # Took time to load all alerts
    Click NewAlert Tab
    wait for page or element to load  10s  # Took time to load all alerts
    ${alert_table_row_data}=  Read Table Data  ${ALERT_TABLE_ROW_XPATH}
    # loop through all alerts row
    FOR    ${item}     IN      @{alert_table_row_data}
        ${found}=  Run Keyword And Return Status  Should Contain  ${item}  ${Description}
        Run Keyword If  ${found} == True  # Description found in the alert
        ...  Run Keywords
        ...  Log To Console And Report  ${found}
        ...  AND  Capture Page Screenshot
        ...  AND  Acknowledge alert  ${servicename}
        ...  AND  Click AlertHistory Tab
        ...  AND  Capture Page Screenshot
    END
    Run Keyword If  ${found} == False
    ...  Run Keywords
    ...  Log To Console And Report  ${found}
    ...  AND  Capture Page Screenshot
    ...  AND  Fail  # description not found in the alert, failing

Verify and Acknowledge inactive resolved alerts exist SW Service
    [Documentation]  Find and mark Fail if SW Service alerts not exist
    [Arguments]  ${servicename}
    ${found}=  Set Variable  False
    ${Description} =  Set Variable  ${servicename} in inactive state.
    Log To Console And Report  ${Description}
    Click AlertPage Image
    wait for page or element to load  10s  # Took time to load all alerts
    Click NewAlert Tab
    wait for page or element to load  10s  # Took time to load all alerts
    ${alert_table_row_data}=  Read Table Data  ${ALERT_TABLE_ROW_XPATH}
    # loop through all alerts row
    FOR    ${item}     IN      @{alert_table_row_data}
        ${found}=  Run Keyword And Return Status  Should Contain  ${item}  ${Description}
        Run Keyword If  ${found} == True  # Description found in the alert
        ...  Run Keywords
        ...  Log To Console And Report  ${found}
        ...  AND  Capture Page Screenshot
        ...  AND  Acknowledge alert  ${servicename}
        ...  AND  Click AlertHistory Tab
        ...  AND  Capture Page Screenshot
    END
    Run Keyword If  ${found} == False
    ...  Run Keywords
    ...  Log To Console And Report  ${found}
    ...  AND  Capture Page Screenshot
    ...  AND  Fail  # description not found in the alert, failing

Verify and Acknowledge deactivating resolved alerts exist SW Service
    [Documentation]  Find and mark Fail if SW Service alerts not exist
    [Arguments]  ${servicename}
    ${found}=  Set Variable  False
    ${Description} =  Set Variable  ${servicename} in deactivating state.
    Log To Console And Report  ${Description}
    Click AlertPage Image
    wait for page or element to load  10s  # Took time to load all alerts
    Click NewAlert Tab
    wait for page or element to load  10s  # Took time to load all alerts
    ${alert_table_row_data}=  Read Table Data  ${ALERT_TABLE_ROW_XPATH}
    # loop through all alerts row
    FOR    ${item}     IN      @{alert_table_row_data}
        ${found}=  Run Keyword And Return Status  Should Contain  ${item}  ${Description}
        Run Keyword If  ${found} == True  # Description found in the alert
        ...  Run Keywords
        ...  Log To Console And Report  ${found}
        ...  AND  Capture Page Screenshot
        ...  AND  Acknowledge alert  ${servicename}
        ...  AND  Click AlertHistory Tab
        ...  AND  Capture Page Screenshot
    END
    Run Keyword If  ${found} == False
    ...  Run Keywords
    ...  Log To Console And Report  ${found}
    ...  AND  Capture Page Screenshot
    ...  AND  Fail  # description not found in the alert, failing

Acknowledge if Active alerts exist
    [Documentation]  Acknowledge if alerts exist in Active Alert Tab
    [Arguments]  ${description}
    ${found}=  Set Variable  False
    Log To Console And Report  ${description}
    Click AlertPage Image
    wait for page or element to load  10s  # Took time to load all alerts
    Click ActiveAlert Tab
    wait for page or element to load  10s  # Took time to load all alerts
    Capture Page Screenshot
    ${alert_table_row_data}=  Read Table Data  ${ALERT_TABLE_ROW_XPATH}
    # loop through all alerts row
    FOR    ${item}     IN      @{alert_table_row_data}
        ${found}=  Run Keyword And Return Status  Should Contain  ${item}  ${description}
        Run Keyword If  ${found} == True  # Description found in the alert
        ...  Run Keywords
        ...  Log To Console And Report  ${found}
        ...  AND  Capture Page Screenshot
        ...  AND  Acknowledge alert  ${description}
        ...  AND  Capture Page Screenshot
    END

Acknowledge if New alerts exist
    [Documentation]  Acknowledge if alerts exist in New Alert tab
    [Arguments]  ${description}
    ${found}=  Set Variable  False
    Log To Console And Report  ${description}
    Click AlertPage Image
    wait for page or element to load  10s  # Took time to load all alerts
    Click NewAlert Tab
    wait for page or element to load  10s  # Took time to load all alerts
    Capture Page Screenshot
    ${alert_table_row_data}=  Read Table Data  ${ALERT_TABLE_ROW_XPATH}
    # loop through all alerts row
    FOR    ${item}     IN      @{alert_table_row_data}
        ${found}=  Run Keyword And Return Status  Should Contain  ${item}  ${description}
        Run Keyword If  ${found} == True  # Description found in the alert
        ...  Run Keywords
        ...  Log To Console And Report  ${found}
        ...  AND  Capture Page Screenshot
        ...  AND  Acknowledge alert  ${description}
        ...  AND  Capture Page Screenshot
    END

Acknowledge if Active alerts exist SW Service
    [Documentation]  Acknowledge if SW Service alerts exist
    [Arguments]  ${servicename}
    ${found1}=  Set Variable  False
    ${found2}=  Set Variable  False
    ${found3}=  Set Variable  False
    ${Description1} =  Set Variable  ${servicename} in failed state.
    ${Description2} =  Set Variable  ${servicename} in inactive state.
    ${Description3} =  Set Variable  ${servicename} in deactivating state.
    Log To Console And Report  ${Description1}
    Log To Console And Report  ${Description2}
    Log To Console And Report  ${Description3}
    Click AlertPage Image
    wait for page or element to load  10s  # Took time to load all alerts
    Click ActiveAlert Tab
    wait for page or element to load  10s  # Took time to load all alerts
    Capture Page Screenshot
    ${alert_table_row_data}=  Read Table Data  ${ALERT_TABLE_ROW_XPATH}
    # loop through all alerts row
    FOR    ${item}     IN      @{alert_table_row_data}
        ${found1}=  Run Keyword And Return Status  Should Contain  ${item}  ${Description1}
        Run Keyword If  ${found1} == True  # Description found in the alert
        ...  Run Keywords
        ...  Log To Console And Report  ${found1}
        ...  AND  Capture Page Screenshot
        ...  AND  Acknowledge alert  ${servicename}
        ...  AND  wait for page or element to load  5s
        ...  AND  Click AlertHistory Tab
        ...  AND  wait for page or element to load  5s
        ...  AND  Capture Page Screenshot
        ${found2}=  Run Keyword And Return Status  Should Contain  ${item}  ${Description2}
        Run Keyword If  ${found2} == True  # Description found in the alert
        ...  Run Keywords
        ...  Log To Console And Report  ${found2}
        ...  AND  Capture Page Screenshot
        ...  AND  Acknowledge alert  ${servicename}
        ...  AND  wait for page or element to load  5s
        ...  AND  Click AlertHistory Tab
        ...  AND  wait for page or element to load  5s
        ...  AND  Capture Page Screenshot
        ${found3}=  Run Keyword And Return Status  Should Contain  ${item}  ${Description3}
        Run Keyword If  ${found3} == True  # Description found in the alert
        ...  Run Keywords
        ...  Log To Console And Report  ${found3}
        ...  AND  Capture Page Screenshot
        ...  AND  Acknowledge alert  ${servicename}
        ...  AND  wait for page or element to load  5s
        ...  AND  Click AlertHistory Tab
        ...  AND  wait for page or element to load  5s
        ...  AND  Capture Page Screenshot
    END
