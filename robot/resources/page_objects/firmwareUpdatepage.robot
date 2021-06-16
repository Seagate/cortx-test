*** Settings ***
Resource    ${RESOURCES}/resources/common/common.robot
Library     SeleniumLibrary

*** Keywords ***

Check Firmware Update Section Not Exists
    [Documentation]  This keyword is to check that user does not have access to Firmware Update Section
    Navigate To Page  MAINTENANCE_MENU_ID
    wait for page or element to load
    Page Should Not Contain Element  ${FW_UPDATE_TAB_ID}

Check Firmware Update Section Exists
    [Documentation]  This keyword is to check that user have access to Firmware Update Section
    Navigate To Page  MAINTENANCE_MENU_ID
    wait for page or element to load
    Page Should Contain Element  ${FW_UPDATE_TAB_ID}

Click On Upload New Firmware File Button
    [Documentation]  Perform click operation on Upload New Firmware File Button
    Sleep  3s
    Wait Until Element Is Enabled  ${UPLOAD_FW_FILE_BUTTON_ID}  timeout=60
    Click button    ${UPLOAD_FW_FILE_BUTTON_ID}

Click On Start Firmware Update Button
    [Documentation]  Perform click operation on tart Firmware Update Button
    Wait Until Element Is Not Visible  ${PAGE_LOADING_MSG_ID}  timeout=600
    Wait Until Element Is Enabled  ${START_FW_UPDATE_BUTTON_ID}  timeout=60
    Click button    ${START_FW_UPDATE_BUTTON_ID}

Download Firmware Binary
    [Documentation]  This keyword download Firmware Binary File
    [Arguments]  ${file_path}
    ${file_path}=  download_file  ${FW_UPDATE_URL}  ${file_path}  fwfile.bin
    Log To Console And Report  ${file_path}
    [Return]  ${file_path}
