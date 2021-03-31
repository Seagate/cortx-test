*** Settings ***
Library    SeleniumLibrary
Resource    ${EXECDIR}/resources/common/common.robot

*** Keywords ***

Verify Presence of Stats And Alerts
    [Documentation]  Verify Presence of Stats And Alerts Button
    Page Should Contain Element  ${CSM_STATS_CHART_ID}
    Page Should Contain Element  ${DASHBOARD_ALERT_SECTION_ID}

Verify Presence of capacity graph in capacity widget
    [Documentation]  Verify Presence of capacity graph in capacity widget
    wait for page or element to load
    Page Should Contain Element  ${CAPACITY_GRAPH_ID}

Verify Presence of Total label on dashboard capacity widget
    [Documentation]  Verify Presence of Total label on dashboard capacity widget
    wait for page or element to load
    Page Should Contain Element  ${CAPACITY_TOTAL_LABEL_ID}
    ${total_label_msg}=  get text  ${CAPACITY_TOTAL_LABEL_ID}
    Log To Console And Report  ${total_label_msg}
    should be equal  ${total_label_msg}  ${TOTAL_CAPACITY_LABEL_VALUE}

Verify Presence of Available label on dashboard capacity widget
    [Documentation]  Verify Presence of Available label on dashboard capacity widget
    wait for page or element to load
    Page Should Contain Element  ${CAPACITY_AVAILABLE_LABEL_ID}
    ${available_label_msg}=  get text  ${CAPACITY_AVAILABLE_LABEL_ID}
    Log To Console And Report  ${available_label_msg}
    should be equal  ${available_label_msg}  ${TOTAL_AVAILABLE_LABEL_VALUE}

Verify Presence of Used label on dashboard capacity widget
    [Documentation]  Verify Presence of Used label on dashboard capacity widget
    wait for page or element to load
    Page Should Contain Element  ${CAPACITY_USED_LABEL_ID}
    ${used_label_msg}=  get text  ${CAPACITY_USED_LABEL_ID}
    Log To Console And Report  ${used_label_msg}
    should be equal  ${used_label_msg}  ${TOTAL_USED_LABEL_VALUE}

Verify Presence of dashboard capacity widget
    [Documentation]  Verify Presence of dashboard capacity widget
    wait for page or element to load
    Page Should Contain Element  ${CAPACITY_WIDGET_ID}
    ${capacity_label_msg}=  get text  ${CAPACITY_WIDGET_LABEL_ID}
    Log To Console And Report  ${capacity_label_msg}
    should be equal  ${capacity_label_msg}  ${CAPACITY_WIDGET_LABEL_VALUE}

Verify Total Capacity Should Be Addition Of Used And Available
    [Documentation]  Verify Presence of dashboard capacity widget
    wait for page or element to load
    ${used_value}=  get text  ${USED_CAPACITY_VALUE_XPATH}
    ${available_value}=  get text  ${AVAILABLE_CAPACITY_VALUE_XPATH}
    ${total_value}=  get text  ${TOTAL_CAPACITY_VALUE_XPATH}
    ${used_value_bytes}=  size_conversion_to_byte  ${used_value}
    ${available_value_bytes}=  size_conversion_to_byte  ${available_value}
    ${total_value_bytes}=  size_conversion_to_byte  ${total_value}
    ${sum_value}=  Evaluate    float(${used_value_bytes}) + float(${available_value_bytes})
    Log To Console And Report  ${sum_value}
    Log To Console And Report  ${total_value_bytes}
    should be equal as integers  ${total_value_bytes}  ${sum_value}
