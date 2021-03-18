*** Settings ***
Library    SeleniumLibrary
Resource   ${EXECDIR}/resources/page_objects/loginPage.robot
Resource   ${EXECDIR}/resources/page_objects/userSettingsLocalPage.robot
Resource   ${EXECDIR}/resources/common/common.robot
Variables  ${EXECDIR}/resources/common/element_locators.py

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

Capture AlertEventDetails Screenshot
    [Documentation]  On Alert Details Page, Capture More Alerts Details Screenshot
    [Arguments]  ${filename}
    Capture Element Screenshot  ${ALERT_MORE_DETAILS_BODY_XPATH}  ${filename}

Click Comments Button
    [Documentation]  On Alert Page, click on Comment icon
    wait until element is visible  ${ALERT_COMMENT_ICON_XPATH}  timeout=10
    Click Element    ${ALERT_COMMENT_ICON_XPATH}

Add CommentInCommentBox Text
    [Documentation]  Add Comment in The CommentBox popup
    wait until element is visible  ${ALERT_COMMENT_TEXT_ID}  timeout=10
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
     [Documentation]  this keyword adds comments and verifys it
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
