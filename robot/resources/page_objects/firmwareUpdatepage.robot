*** Settings ***
Resource    ${EXECDIR}/resources/common/common.robot
Library     SeleniumLibrary

*** Keywords ***

Click On Upload New Firmware File Button
    [Documentation]  Perform click operation on Upload New Firmware File Button
    Sleep  3s
    Wait Until Element Is Enabled  ${UPLOAD_FW_FILE_BTN_ID}  timeout=60
    Click button    ${UPLOAD_FW_FILE_BTN_ID}

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
