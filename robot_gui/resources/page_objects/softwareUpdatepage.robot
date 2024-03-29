*** Settings ***
Library    SeleniumLibrary
Resource   ${RESOURCES}/resources/common/common.robot

*** Keywords ***

Check Software Update Section Not Exists
    [Documentation]  This keyword verifys that user can not access Software Update Section
    Navigate To Page  MAINTENANCE_MENU_ID
    Page Should Not Contain Element  ${SW_UPDATE_TAB_ID}

Check Software Update Section Exists
    [Documentation]  This keyword verifys that user can access Software Update Section
    Navigate To Page  MAINTENANCE_MENU_ID
    Page Should Contain Element  ${SW_UPDATE_TAB_ID}

Click On Upload New Software File Button
    [Documentation]  Perform click operation on Upload New Software File Button
    Sleep  3s
    Wait Until Element Is Enabled  ${UPLOAD_SW_FILE_BUTTON_ID}  timeout=60
    Click button    ${UPLOAD_SW_FILE_BUTTON_ID}

Click On Start Software Update Button
    [Documentation]  Perform click operation on tart Software Update Button
    Wait Until Element Is Not Visible  ${PAGE_LOADING_MSG_ID}  timeout=600
    Wait Until Element Is Enabled  ${START_SW_UPDATE_BUTTON_ID}  timeout=60
    Click button    ${START_SW_UPDATE_BUTTON_ID}

Get Url for Software Download
    [Documentation]  Return the required URL for download SW file
    [Arguments]  ${version}
    ${url} =  Format String  ${SW_UPDATE_URL}  ${version}
    Log To Console And Report  ${url}
    [Return]  ${url}

Download SW ISO File
    [Documentation]  This keyword download SW ISO File
    [Arguments]  ${version}  ${file_path}
    ${url}=  Get Url for Software Download  ${version}
    ${file_path}=  download_file  ${url}  ${file_path}  swfile.iso
    Log To Console And Report  ${file_path}
    [Return]  ${file_path}
