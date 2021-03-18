*** Settings ***
Library    SeleniumLibrary
Resource   ${EXECDIR}/resources/common/common.robot
Variables  ${EXECDIR}/resources/common/element_locators.py

*** Variables ***
${Download_File_Path}  \root\Downloads\
${default_file_name}  s3server.pem

*** Keywords ***

Verify Setting menu item
    [Documentation]  Functionality to verify settings menu items
    Page Should Contain Element  ${SETTINGS_ID}
    Page Should Contain Element  ${SETTINGS_NOTIFICATION_ID}
    Page Should Contain Element  ${SETTINGS_NOTIFICATION_BUTTON_ID}
    Page Should Contain Element  ${SETTINGS_DNS_ID}
    Page Should Contain Element  ${SETTINGS_DNS_BUTTON_ID}
    Page Should Contain Element  ${SETTINGS_NTP_ID}
    Page Should Contain Element  ${SETTINGS_NTP_BUTTON_ID}
    Page Should Contain Element  ${SETTINGS_SSL_ID}
    Page Should Contain Element  ${SETTINGS_SSL_BUTTON_ID}

Verify Setting menu navigating items
    [Documentation]  Functionality to verify settings menu items
    [Arguments]  ${item_ID}
    Page Should Contain Element  ${item_ID}
    Click button  ${item_ID}
    Sleep  10s
    Go Back
    Sleep  1s

Verify Setting menu navigating
    [Documentation]  Functionality to verify settings menu items pages
    Navigate To Page  SETTINGS_ID
    Verify Setting menu navigating items  ${SETTINGS_NOTIFICATION_BUTTON_ID}
    Verify Setting menu navigating items  ${SETTINGS_DNS_BUTTON_ID}
    Verify Setting menu navigating items  ${SETTINGS_NTP_BUTTON_ID}
    Verify Setting menu navigating items  ${SETTINGS_SSL_BUTTON_ID}

Click On Upload New SSL File Button
    [Documentation]  Perform click operation on Upload New Software File Button
    Wait Until Element Is Enabled  ${UPLOAD_SSL_FILE_PEM_ID}  timeout=60
    Click button    ${UPLOAD_SSL_FILE_PEM_ID}

Click On Install New SSL Button
    [Documentation]  Perform click operation on Upload New Software File Button
    Sleep  3s
    Wait Until Element Is Enabled  ${INSTALL_SSL_FILE_PEM_ID}  timeout=60
    Click button    ${INSTALL_SSL_FILE_PEM_ID}

Get Url for SSL Download
    [Documentation]  Return the required URL for download SW file
    [Arguments]  ${version}
    ${url} =  Format String  ${SSL_URL}  ${file_name}
    Log To Console And Report  ${url}
    [Return]  ${url}

Download PEM File
    [Documentation]  This keyword download SSL PEM File
    [Arguments]  ${file_path}  ${server_file_name}=${default_file_name}
    Log To Console And Report  ${SSL_URL}${server_file_name}
    Log To Console And Report  ${file_path}
    Log To Console And Report  ${server_file_name}
    ${file_path}=  download_file_with_name  ${SSL_URL}${server_file_name}  ${file_path}  ${server_file_name}
    [Return]  ${file_path}

Verify SSL status
    [Documentation]  Functionality to verify if the Pem file was installed
    [Arguments]  ${expected_status}  ${file_name}=${default_file_name}
    Navigate To Page  SETTINGS_ID  SETTINGS_SSL_BUTTON_ID
    Sleep  30s  # Took time to load after install
    Page Should Contain Element  ${SSL_PEM_FILE_NAME_XPATH}
    Page Should Contain Element  ${SSL_PEM_FILE_STATUS_XPATH}
    ${page_file_name}=  Get Text  ${SSL_PEM_FILE_NAME_XPATH}
    ${status}=  Get Text  ${SSL_PEM_FILE_STATUS_XPATH}
    Log To Console And Report  ${page_file_name}
    Log To Console And Report  ${status}
    Should Be Equal  ${page_file_name}  ${file_name}
    Should Be Equal  ${status}  ${expected_status}

SSL Upload
    [Documentation]  Functionality to verify 
    [Arguments]  ${Download_File_Path}  ${server_file_name}=${default_file_name}
    ${path}=  Download PEM File  ${Download_File_Path}  ${server_file_name}
    Log To Console And Report  ${path}
    Upload File  CHOOSE_SSL_UPDATE_FILE_BTN_ID  ${path}
    Sleep  3s
    Click On Upload New SSL File Button
    Sleep  5s

Click On Start SSL Update Button
    [Documentation]  Perform click operation on tart Software Update Button
    Wait Until Element Is Enabled  ${INSTALL_SSL_FILE_PEM_ID}  timeout=10
    Click button    ${INSTALL_SSL_FILE_PEM_ID}

Click On Confirmation Button
    [Documentation]  Perform click operation on popup of Confirmation
    Wait Until Element Is Enabled  ${CONFIRMAATION_INSTALL_SSL_ID}  timeout=10
    Click button    ${CONFIRMAATION_INSTALL_SSL_ID}

Install uploaded SSL
    Click On Start SSL Update Button
    Sleep  2s
    Click On Confirmation Button

Verify that CSM manage user can not access setting menu
    [Documentation]  Functionality to verify settings options are not accessable for manage user
    Sleep  1s
    Page Should Not Contain Element  ${SETTINGS_ID}

Verify that S3 user can not access setting menu
    [Documentation]  This keyword is to check that s3 user does not have access to setting page
    Sleep  1s
    Page Should Not Contain Element  ${SETTINGS_ID}

Verify that CSM Admin can access Setting menu
    [Documentation]  Functionality to verify settings options are accessable for admin user
    Sleep  1s
    Page Should Contain Element  ${SETTINGS_ID}
    Navigate To Page  SETTINGS_ID
    Verify Setting menu item
