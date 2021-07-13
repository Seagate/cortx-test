*** Settings ***
Documentation    This suite verifies the testcases for ssl details
Resource    ${RESOURCES}/resources/page_objects/alertPage.robot
Resource    ${RESOURCES}/resources/page_objects/loginPage.robot
Resource    ${RESOURCES}/resources/page_objects/preboardingPage.robot
Variables   ${RESOURCES}/resources/common/element_locators.py
Variables   ${RESOURCES}/resources/common/common_variables.py

Test Setup  CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
Test Teardown  Close Browser
Suite Teardown  Close All Browsers

*** Test Cases ***

CHECK_IN_NEW_ALERTS
    [Documentation]  CSM GUI: Check if alert present in new alert table
    [Tags]  Priority_High  R2  CHECK_IN_NEW_ALERTS
    Check if alert exists in New alerts tab  ${description}

TEST-21262
    [Documentation]  CSM GUI: Verify Alerts for SW Service : HAProxy
    ...  Reference : https://jts.seagate.com/browse/TEST-21262
    [Tags]  Priority_High  R2 TEST-21262
    ${servicename} =  Set Variable  haproxy
    Fail if New alerts exist SW Service  ${servicename}
    Acknowledge if Active alerts exist SW Service  ${servicename}
    # fail service
    Verify failed alerts exist SW Service  ${servicename}
    # start service
    Verify failed resolved alerts exist SW Service  ${servicename}
    # inactive service
    Verify inactive alerts exist SW Service  ${servicename}
    # start service
    Verify inactive resolved alerts exist SW Service  ${servicename}
    Verify failed alerts exist SW Service  ${servicename}

TEST-21267
    [Documentation]  CSM GUI: Verify Alerts for SW Service : Multipathd
    ...  Reference : https://jts.seagate.com/browse/TEST-TEST-21267
    [Tags]  Priority_High  R2 TEST-TEST-21267
    ${servicename} =  Set Variable  multipathd
    Fail if New alerts exist SW Service  ${servicename}
    Acknowledge if Active alerts exist SW Service  ${servicename}
    # fail service
    Verify failed alerts exist SW Service  ${servicename}
    # start service
    Verify failed resolved alerts exist SW Service  ${servicename}
    # inactive service
    Verify inactive alerts exist SW Service  ${servicename}
    # start service
    Verify inactive resolved alerts exist SW Service  ${servicename}
    Verify failed alerts exist SW Service  ${servicename}

TEST-21266
    [Documentation]  CSM GUI: Verify Alerts for SW Service : GlusterFS
    ...  Reference : https://jts.seagate.com/browse/TEST-21266
    [Tags]  Priority_High  R2 TEST-21266
    ${servicename} =  Set Variable  glusterd
    Fail if New alerts exist SW Service  ${servicename}
    Acknowledge if Active alerts exist SW Service  ${servicename}
    # fail service
    Verify failed alerts exist SW Service  ${servicename}
    # start service
    Verify failed resolved alerts exist SW Service  ${servicename}
    # inactive service
    Verify inactive alerts exist SW Service  ${servicename}
    # start service
    Verify inactive resolved alerts exist SW Service  ${servicename}
    Verify failed alerts exist SW Service  ${servicename}

TEST-21265
    [Documentation]  CSM GUI: Verify Alerts for SW Service : SaltStack
    ...  Reference : https://jts.seagate.com/browse/TEST-21265
    [Tags]  Priority_High  R2 TEST-21265
    ${servicename} =  Set Variable  salt-master
    Fail if New alerts exist SW Service  ${servicename}
    Acknowledge if Active alerts exist SW Service  ${servicename}
    # fail service
    Verify failed alerts exist SW Service  ${servicename}
    # start service
    Verify failed resolved alerts exist SW Service  ${servicename}
    # inactive service
    Verify inactive alerts exist SW Service  ${servicename}
    # start service
    Verify inactive resolved alerts exist SW Service  ${servicename}
    Verify failed alerts exist SW Service  ${servicename}
    ${servicename} =  Set Variable  salt-minion
    Fail if New alerts exist SW Service  ${servicename}
    Acknowledge if Active alerts exist SW Service  ${servicename}
    # fail service
    Verify failed alerts exist SW Service  ${servicename}
    # start service
    Verify failed resolved alerts exist SW Service  ${servicename}
    # inactive service
    Verify inactive alerts exist SW Service  ${servicename}
    # start service
    Verify inactive resolved alerts exist SW Service  ${servicename}
    Verify failed alerts exist SW Service  ${servicename}

TEST-21264
    [Documentation]  CSM GUI: Verify Alerts for SW Service : Lustre
    ...  Reference : https://jts.seagate.com/browse/TEST-21264
    [Tags]  Priority_High  R2 TEST-21264
    ${servicename} =  Set Variable  lnet
    Fail if New alerts exist SW Service  ${servicename}
    Acknowledge if Active alerts exist SW Service  ${servicename}
    # fail service
    Verify failed alerts exist SW Service  ${servicename}
    # start service
    Verify failed resolved alerts exist SW Service  ${servicename}
    # inactive service
    Verify inactive alerts exist SW Service  ${servicename}
    # start service
    Verify inactive resolved alerts exist SW Service  ${servicename}
    Verify failed alerts exist SW Service  ${servicename}

TEST-21263
    [Documentation]  CSM GUI: Verify Alerts for SW Service : OpenLDAP
    ...  Reference : https://jts.seagate.com/browse/TEST-21263
    [Tags]  Priority_High  R2 TEST-21263
    ${servicename} =  Set Variable  slapd
    Fail if New alerts exist SW Service  ${servicename}
    Acknowledge if Active alerts exist SW Service  ${servicename}
    # fail service
    Verify failed alerts exist SW Service  ${servicename}
    # start service
    Verify failed resolved alerts exist SW Service  ${servicename}
    # inactive service
    Verify inactive alerts exist SW Service  ${servicename}
    # start service
    Verify inactive resolved alerts exist SW Service  ${servicename}
    Verify failed alerts exist SW Service  ${servicename}


TEST-21261
    [Documentation]  CSM GUI: Verify Alerts for SW Service : Rsyslog
    ...  Reference : https://jts.seagate.com/browse/TEST-21261
    [Tags]  Priority_High  R2 TEST-21261
    ${servicename} =  Set Variable  rsyslog
    Fail if New alerts exist SW Service  ${servicename}
    Acknowledge if Active alerts exist SW Service  ${servicename}
    # fail service
    Verify failed alerts exist SW Service  ${servicename}
    # start service
    Verify failed resolved alerts exist SW Service  ${servicename}
    # inactive service
    Verify inactive alerts exist SW Service  ${servicename}
    # start service
    Verify inactive resolved alerts exist SW Service  ${servicename}
    Verify failed alerts exist SW Service  ${servicename}

TEST-21260
    [Documentation]  CSM GUI: Verify Alerts for SW Service : Statsd
    ...  Reference : https://jts.seagate.com/browse/TEST-21260
    [Tags]  Priority_High  R2 TEST-21260
    ${servicename} =  Set Variable  statsd
    Fail if New alerts exist SW Service  ${servicename}
    Acknowledge if Active alerts exist SW Service  ${servicename}
    # fail service
    Verify failed alerts exist SW Service  ${servicename}
    # start service
    Verify failed resolved alerts exist SW Service  ${servicename}
    # inactive service
    Verify inactive alerts exist SW Service  ${servicename}
    # start service
    Verify inactive resolved alerts exist SW Service  ${servicename}
    Verify failed alerts exist SW Service  ${servicename}


TEST-21259
    [Documentation]  CSM GUI: Verify Alerts for SW Service : Kafka
    ...  Reference : https://jts.seagate.com/browse/TEST-21259
    [Tags]  Priority_High  R2 TEST-21259
    ${servicename} =  Set Variable  kafka
    Fail if New alerts exist SW Service  ${servicename}
    Acknowledge if Active alerts exist SW Service  ${servicename}
    # fail service
    Verify failed alerts exist SW Service  ${servicename}
    # start service
    Verify failed resolved alerts exist SW Service  ${servicename}
    # inactive service
    Verify inactive alerts exist SW Service  ${servicename}
    # start service
    Verify inactive resolved alerts exist SW Service  ${servicename}
    Verify failed alerts exist SW Service  ${servicename}

TEST-21258
    [Documentation]  CSM GUI: Verify Alerts for SW Service : Scsi-network-relay
    ...  Reference : https://jts.seagate.com/browse/TEST-21258
    [Tags]  Priority_High  R2 TEST-21258
    ${servicename} =  Set Variable  scsi-network-relay
    Fail if New alerts exist SW Service  ${servicename}
    Acknowledge if Active alerts exist SW Service  ${servicename}
    # fail service
    Verify failed alerts exist SW Service  ${servicename}
    # start service
    Verify failed resolved alerts exist SW Service  ${servicename}
    # inactive service
    Verify inactive alerts exist SW Service  ${servicename}
    # start service
    Verify inactive resolved alerts exist SW Service  ${servicename}
    Verify failed alerts exist SW Service  ${servicename}

TEST-21256
    [Documentation]  CSM GUI: Verify Alerts for SW Service : Consul
    ...  Reference : https://jts.seagate.com/browse/TEST-21256
    [Tags]  Priority_High  R2 TEST-21256
    ${servicename} =  Set Variable  hare-consul-agent
    Fail if New alerts exist SW Service  ${servicename}
    Acknowledge if Active alerts exist SW Service  ${servicename}
    # fail service
    Verify failed alerts exist SW Service  ${servicename}
    # start service
    Verify failed resolved alerts exist SW Service  ${servicename}
    # inactive service
    Verify inactive alerts exist SW Service  ${servicename}
    # start service
    Verify inactive resolved alerts exist SW Service  ${servicename}
    Verify failed alerts exist SW Service  ${servicename}

TEST-21257
    [Documentation]  CSM GUI: Verify Alerts for SW Service : ElasticSearch-OSS
    ...  Reference : https://jts.seagate.com/browse/TEST-21257
    [Tags]  Priority_High  R2 TEST-21257
    ${servicename} =  Set Variable  elasticsearch
    Fail if New alerts exist SW Service  ${servicename}
    Acknowledge if Active alerts exist SW Service  ${servicename}
    # fail service
    Verify failed alerts exist SW Service  ${servicename}
    # start service
    Verify failed resolved alerts exist SW Service  ${servicename}
    # inactive service
    Verify inactive alerts exist SW Service  ${servicename}
    # start service
    Verify inactive resolved alerts exist SW Service  ${servicename}
    Verify failed alerts exist SW Service  ${servicename}

#TEST-19878
#    [Documentation]  CSM GUI: Verify Alerts for SW Service
#    ...  Reference : https://jts.seagate.com/browse/TEST-19878
#    [Tags]  Priority_High  R2 TEST-19878
