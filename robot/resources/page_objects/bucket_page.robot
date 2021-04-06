*** Settings ***
Library    SeleniumLibrary
Resource   ${EXECDIR}/resources/common/common.robot
Variables  ${EXECDIR}/resources/common/element_locators.py

*** Keywords ***

Create Bucket
    [Documentation]  Test keyword is for create bucket
    [Arguments]  ${bucketname}  ${check_bucket_url}=False
    ${bucket_url_check}=  Convert To Boolean  ${check_bucket_url}
    Log To Console And Report  Inserting bucketname ${bucketname}
    Input Text  ${BUCKET_NAME_ID}  ${bucketname}
    Click Element  ${BUCKET_CREATE_BUTTON_ID}
    Sleep  2s
    Run Keyword If  ${bucket_url_check}  Verify bucket url after bucket creation  ${bucketname}
    ...  ELSE  Log To Console And Report  Bucket URL not displayed
    wait until element is visible  ${CONFIRM_CREATE_BUTTON_ID}  timeout=60
    Click Button  ${CONFIRM_CREATE_BUTTON_ID}

Click On Create Bucket Form
    [Documentation]  Test keyword is for open create bucket form
    wait until element is visible  ${ADD_BUCKET_FORM_ID}  timeout=60
    Click Button  ${ADD_BUCKET_FORM_ID}

Click On Edit Bucket Icon
    [Documentation]  Test keyword is for clicking on Edit Bucket
    wait until element is visible  ${EDIT_BUCKET_ICON_ID}  timeout=60
    Click Element  ${EDIT_BUCKET_ICON_ID}

Click On Cancel Bucket Policy
    [Documentation]  This keyword is to perform Click action on cancel button
    ...  of the bucket policy form
    wait until element is visible  ${CANCEL_BUCKET_POLICY_FORM_ID}  timeout=60
    Click Element  ${CANCEL_BUCKET_POLICY_FORM_ID}

Click On Update Bucket Policy
    [Documentation]  This keyword is to perform Click action on update button
    ...  of the bucket policy form
    wait until element is visible  ${UPDATE_BUCKET_POLICY_BTN_ID}  timeout=60
    Click Element  ${UPDATE_BUCKET_POLICY_BTN_ID}

Click On Delete Bucket Policy
    [Documentation]  This keyword is to perform Click action on delete button
    ...  of the bucket policy form
    wait until element is visible  ${DELETE_BUCKET_POLICY}  timeout=60
    Click Element  ${DELETE_BUCKET_POLICY}

Click On cancel button for bucket creation
    [Documentation]  Test keyword is for open create bucket form
    wait until element is visible  ${CANCEL_BUCKET_CREATION_BUTTON_ID }  timeout=60
    Click Button  ${CANCEL_BUCKET_CREATION_BUTTON_ID }
    
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

verify that create buttn functionality on buckets tab
    [Documentation]  This keyword verifys that create button functionality on the buckets tab
    Click On Create Bucket Form
    wait until element is visible  ${BUCKET_NAME_ID}  timeout=10
    ${bucket_name} =   Get WebElements  ${BUCKET_NAME_ID}

verify the tooptip for the bucket name policy
    [Documentation]  This keyword verifys the tooltip for the bucket name policy
    Mouse Over  ${BUCKET_NAME_POLICY_TOOLTIP_ICON_ID}
    wait for page or element to load
    Verify message  BUCKET_NAME_POLICY_TOOLTIP_ID  ${BUCKET_NAME_POLICY_TEXT}

Verify that create bucket button remains disabled
    [Documentation]  This keyword verifys that create bucket button remains disabled when
    ...  entered invalid bucket name.
    [Arguments]  ${bucketname}
    Log To Console And Report  Inserting bucketname ${bucketname}
    Input Text  ${BUCKET_NAME_ID}  ${bucketname}
    ${state_of_create_bucket_button}=  Get Element Attribute  ${BUCKET_CREATE_BUTTON_ID}  disabled
    Run Keyword If  ${${state_of_create_bucket_button}} == True  log to console and report
    ...  create bucket button is disabled.

Verfiy the cancel create bucket functionality
    [Documentation]  This keyword verifys cancel button for create bucket.
    Click On cancel button for bucket creation
    Check element is not visiable  BUCKET_NAME_ID

Verify the message for duplicate bucket name
    [Documentation]  This keyword verifys the message for duplicate bucket name.
    [Arguments]  ${bucketname}
    Log To Console And Report  Inserting bucketname ${bucketname}
    Input Text  ${BUCKET_NAME_ID}  ${bucketname}
    Click Element  ${BUCKET_CREATE_BUTTON_ID}
    Verify message  DUPLICATE_BUCKET_MESSAGE_ID  ${DUPLICATE_BUCKET_NAME_ALERT_MESSAGE}
    click element   ${CLOSE_DUPLICATE_BUCKET_MESSAGE_ID}

Verify cancel opration of delete bucket
    [Documentation]  This keyword verifys the cancel opration of delete bucket.
    [Arguments]  ${bucketname}
    Log To Console And Report  Deleting Bucket ${bucketname}
    Action On The Table Element  ${DELETE_BUCKET_XPATH}  ${bucketname}
    wait for page or element to load
    Click Button  ${CANCEL_BUCKET_DELETION_ID}
    Is Bucket Present  ${bucketname}
    Action On The Table Element  ${DELETE_BUCKET_XPATH}  ${bucketname}
    Click Element  ${CANCEL_BUCKET_DELITION_ICON_ID}
    Is Bucket Present  ${bucketname}

Verify Update Button Must Remain Disabled
    [Documentation]  This keyword checks update Button status should remain disabled
    wait until element is visible  ${UPDATE_BUCKET_POLICY_BTN_ID}  timeout=30
    ${status}=  Get Element Attribute  ${UPDATE_BUCKET_POLICY_BTN_ID}  disabled
    Log To Console And Report  Status of update policy is ${status}
    Should be equal  ${status}  true

Verify Update Bucket Policy Form Should Appear
    [Documentation]  This keyword Verify Update Bucket Policy Form
    ...  Should be visible to user
    wait for page or element to load
    Element Should Be Visible  ${BUCKET_POLICY_FORM_ID}

Verify Heading on Bucket Policy Form
    [Documentation]  This keyword Verify the heading value of the bucket policy form
    ...  to its expected value
    wait for page or element to load
    ${policy_heading_fetched}=  get text  ${BUCKET_POLICY_FORM_HEADING_ID}
    Log To Console And Report  ${policy form heading}
    Should be Equal  ${policy form heading}  ${policy_heading_fetched}

Add Json Policy To Bucket
    [Documentation]  This keyword will Add Json Policy To Bucket
    [Arguments]  ${policy}
    wait until element is visible  ${ADD_POLICY_TEXT_AREA_ID}  timeout=30
    Input Text  ${ADD_POLICY_TEXT_AREA_ID}  ${policy}

Fetch Json Policy To Bucket
    [Documentation]  This keyword will fetch exhisting Json Policy of the Bucket
    wait until element is visible  ${ADD_POLICY_TEXT_AREA_ID}  timeout=30
    ${policy}=  Get Element Attribute  ${ADD_POLICY_TEXT_AREA_ID}  value
    Log To Console And Report  exhisting policy : ${policy}
    [Return]  ${policy}

Verify Error Msg is Shown For Invalid Json
    [Documentation]  This keyword will Verify Error Msg is Shown For Invalid Json
    wait until element is visible  ${ERROR_MSG_POP_UP_ID}  timeout=30
    ${err_msg}=  get text  ${ERROR_MSG_POP_UP_ID}
    Log To Console And Report  ${err_msg}
    Should be Equal  ${INVALID_POLICY_MSG}  ${err_msg}
    Wait Until Element Is Not Visible  ${ERROR_MSG_POP_UP_ID}  timeout=30

Verify Bucket Policy Not Added
    [Documentation]  This keyword will Verify Bucket Policy Not Added
    Click On Edit Bucket Icon
    ${data}=  Fetch Json Policy To Bucket
    Should Be Empty  ${data}

Verify Bucket Policy Got Added
    [Documentation]  This keyword will Verify Bucket Policy Got Added
    [Arguments]  ${policy}
    Click On Edit Bucket Icon
    wait for page or element to load
    ${data}=  Fetch Json Policy To Bucket
    ${result}=  match_json_policy  ${data}  ${policy}
    Should Be Equal  '${result}'  '${True}'

Refresh To Bucket Page
    [Documentation]  This keyword will refresh the page to Bucket page
    Reload Page
    wait for page or element to load
    Navigate To Page  BUCKET_TAB_ID

Verify the bucket url in buckets table
    [Documentation]  This keyword verifys the bucket url in buckets table.
    [Arguments]  ${bucketname}
     Log To Console And Report  Bucket ${bucketname}
     ${tool_tip_element} =  Format String  ${BUCKET_URL_TOOLTIP_XPATH}  ${bucketname}
     wait for page or element to load  10s
     Mouse Over  ${tool_tip_element}
     wait for page or element to load
     wait until element is visible  ${BUCKET_URL_TOOLTIP_TEXT_ID}  timeout=10
     ${tooltip_from_gui}=  get text  ${BUCKET_URL_TOOLTIP_TEXT_ID}
     Should Contain  ${tooltip_from_gui}  ${bucketname}

Verify bucket url after bucket creation
    [Documentation]  This keyword verifys the bucket url after bucket creation.
    [Arguments]  ${bucketname}
    Log To Console And Report  Bucket ${bucketname}
    wait for page or element to load
    ${bucket_url_element_text}=  get text  ${BUCKET_URL_ON_BUCKET_CREATION_XPATH}
    Should Contain  ${bucket_url_element_text}  ${bucketname}

