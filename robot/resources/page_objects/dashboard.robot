*** Settings ***
Resource  ../../resources/common/common.robot
Resource  userSettingsLocalPage.robot
Resource  loginPage.robot
Library     SeleniumLibrary
Variables  ../common/element_locators.py

*** Keywords ***

Verify Presence of Stats And Alerts
    [Documentation]  Verify Presence of Stats And Alerts Button
    Page Should Contain Element  ${CSM_STATS_CHART_ID}
    Page Should Contain Element  ${DASHBOARD_ALERT_SECTION_ID}

