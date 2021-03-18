*** Settings ***
Library    SeleniumLibrary
Resource   ${EXECDIR}/resources/common/common.robot
Variables  ${EXECDIR}/resources/common/element_locators.py

*** Keywords ***

Create Bucket
    [Documentation]  Test keyword is for create bucket
    [Arguments]  ${bucketname} 
    Log To Console And Report  Inserting bucketname ${bucketname}
    Input Text  ${BUCKET_NAME_ID}  ${bucketname}
    Click Element  ${BUCKET_CREATE_BUTTON_ID}
    Sleep  2s
    wait until element is visible  ${CONFIRM_CREATE_BUTTON_ID}  timeout=60
    Click Button  ${CONFIRM_CREATE_BUTTON_ID}

Click On Create Bucket Form
    [Documentation]  Test keyword is for open create bucket form 
    wait until element is visible  ${ADD_BUCKET_FORM_ID}  timeout=60
    Click Button  ${ADD_BUCKET_FORM_ID}
    
Delete Bucket
    [Documentation]  Functionality to Delete Bucket
    [Arguments]  ${bucketname}
    Log To Console And Report  Deleting Bucket ${bucketname}
    Action On The Table Element  ${DELETE_BUCKET_XPATH}  ${bucketname}
    Sleep  5s
    wait until element is visible  ${CONFIRM_DELETE_BOX_BTN_ID}  timeout=60
    Click Button  ${CONFIRM_DELETE_BOX_BTN_ID}

Is Bucket Present
    [Documentation]  Check the Bucket present or not
    [Arguments]  ${bucketname}
    ${element}=  Format String  ${BUCKET_ROW_ELEMENT_XPATH}  ${bucketname}
    Log To Console And Report  Element path ${element}
    ${status}=  Run Keyword And Return Status  Element Should Be Visible  ${element}
    [Return]  ${status}
