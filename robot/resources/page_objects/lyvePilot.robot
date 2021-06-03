*** Settings ***
Library    SeleniumLibrary
Resource   ${EXECDIR}/resources/page_objects/loginPage.robot
Resource   ${EXECDIR}/resources/common/common.robot
Variables  ${EXECDIR}/resources/common/element_locators.py

*** Keywords ***

Verify that user can not access Lyve Pilot menu
       [Documentation]  This keyword verifys that user can not access Lyve Pilot menu
       Page Should Not Contain Element  ${LYVE_PILOT_MENU_ID}

Verify that user can access Lyve Pilot menu
       [Documentation]  This keyword verifys that user can access Lyve Pilot menu
       Page Should Contain Element  ${LYVE_PILOT_MENU_ID}
