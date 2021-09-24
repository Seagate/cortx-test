*** Settings ***
Library    SeleniumLibrary
Resource   ${RESOURCES}/resources/common/common.robot
Variables  ${RESOURCES}/resources/common/element_locators.py

*** Keywords ***

Check System Maintenance Section Not Exists
    [Documentation]  This keyword verifys that user can not access System Maintenance Section
    Navigate To Page  MAINTENANCE_MENU_ID
    wait for page or element to load
    Page Should Not Contain Element  ${SYSTEM_MAINTENANCE_BUTTON_ID}

Check System Maintenance Section Exists
    [Documentation]  This keyword verifys that user can access System Maintenance Section
    Navigate To Page  MAINTENANCE_MENU_ID
    wait for page or element to load
    Page Should Contain Element  ${SYSTEM_MAINTENANCE_BUTTON_ID}

Check Start Service Option Not Exists
    [Documentation]  This keyword verifys that user can not access System Maintenance Section
    Navigate To Page  MAINTENANCE_MENU_ID  SYSTEM_MAINTENANCE_BUTTON_ID
    wait for page or element to load
    Page Should Not Contain Element  ${START_SERVICE_BUTTON_ID}

Check Start Service Option Exists
    [Documentation]  This keyword verifys that user can access System Maintenance Section
    Navigate To Page  MAINTENANCE_MENU_ID  SYSTEM_MAINTENANCE_BUTTON_ID
    wait for page or element to load
    Page Should Contain Element  ${START_SERVICE_BUTTON_ID}

Check Stop Service Option Not Exists
    [Documentation]  This keyword verifys that user can not access System Maintenance Section
    Navigate To Page  MAINTENANCE_MENU_ID  SYSTEM_MAINTENANCE_BUTTON_ID
    wait for page or element to load
    Page Should Not Contain Element  ${STOP_SERVICE_BUTTON_ID}

Check Stop Service Option Exists
    [Documentation]  This keyword verifys that user can access System Maintenance Section
    Navigate To Page  MAINTENANCE_MENU_ID  SYSTEM_MAINTENANCE_BUTTON_ID
    wait for page or element to load
    Page Should Contain Element  ${STOP_SERVICE_BUTTON_ID}

Check Shutdown Option Not Exists
    [Documentation]  This keyword verifys that user can not access System Maintenance Section
    Navigate To Page  MAINTENANCE_MENU_ID  SYSTEM_MAINTENANCE_BUTTON_ID
    wait for page or element to load
    Page Should Not Contain Element  ${SHUTDOWN_SERVICE_BUTTON_ID}

Check Shutdown Option Exists
    [Documentation]  This keyword verifys that user can not access System Maintenance Section
    Navigate To Page  MAINTENANCE_MENU_ID  SYSTEM_MAINTENANCE_BUTTON_ID
    wait for page or element to load
    Page Should Contain Element  ${SHUTDOWN_SERVICE_BUTTON_ID}
