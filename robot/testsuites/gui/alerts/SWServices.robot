*** Settings ***
Documentation    This suite verifies the testcases for ssl details
Resource    ${RESOURCES}/resources/page_objects/alertPage.robot
Resource    ${RESOURCES}/resources/page_objects/loginPage.robot
Resource    ${RESOURCES}/resources/page_objects/preboardingPage.robot
Variables   ${RESOURCES}/resources/common/element_locators.py
Variables   ${RESOURCES}/resources/common/common_variables.py

Suite Setup  run keywords   check csm admin user status  ${url}  ${browser}  ${headless}
...  ${username}  ${password}
...  AND  Close Browser
Test Setup  CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
#Test Teardown   CSM GUI Logout
Test Teardown  Close Browser
Suite Teardown  Close All Browsers
Force Tags  CSM_GUI  SWServicesAlerts

*** Test Cases ***


TEST-21262
    [Documentation]  CSM GUI: Verify Alerts for SW Service : HAProxy
    ...  Reference : https://jts.seagate.com/browse/TEST-21262
    [Tags]  Priority_High  R2 TEST-21262
    Fail if New alerts exist SW Service  haproxy
    Acknowledge if Active alerts exist SW Service  haproxy
    #test_21194_deactivating_alerts(self)
    #Fail if New alerts exist SW Service  haproxy
    #test_21194_activating_alertsself
    #Fail if New alerts exist SW Service  haproxy

TEST-21267
    [Documentation]  CSM GUI: Verify Alerts for SW Service : Multipathd
    ...  Reference : https://jts.seagate.com/browse/TEST-TEST-21267
    [Tags]  Priority_High  R2 TEST-TEST-21267
    Fail if New alerts exist SW Service  multipathd
    Acknowledge if Active alerts exist SW Service  multipathd

TEST-21266
    [Documentation]  CSM GUI: Verify Alerts for SW Service : GlusterFS
    ...  Reference : https://jts.seagate.com/browse/TEST-21266
    [Tags]  Priority_High  R2 TEST-21266
    Fail if New alerts exist SW Service  glusterd
    Acknowledge if Active alerts exist SW Service  glusterd

TEST-21265
    [Documentation]  CSM GUI: Verify Alerts for SW Service : SaltStack
    ...  Reference : https://jts.seagate.com/browse/TEST-21265
    [Tags]  Priority_High  R2 TEST-21265
    Fail if New alerts exist SW Service  salt-master
    Fail if New alerts exist SW Service  salt-minion
    Acknowledge if Active alerts exist SW Service  salt-master
    Acknowledge if Active alerts exist SW Service  salt-minion

TEST-21264
    [Documentation]  CSM GUI: Verify Alerts for SW Service : Lustre
    ...  Reference : https://jts.seagate.com/browse/TEST-21264
    [Tags]  Priority_High  R2 TEST-21264
    Fail if New alerts exist SW Service  lnet
    Acknowledge if Active alerts exist SW Service  lnet

TEST-21263
    [Documentation]  CSM GUI: Verify Alerts for SW Service : OpenLDAP
    ...  Reference : https://jts.seagate.com/browse/TEST-21263
    [Tags]  Priority_High  R2 TEST-21263
    Fail if New alerts exist SW Service  slapd
    Acknowledge if Active alerts exist SW Service  slapd

TEST-21261
    [Documentation]  CSM GUI: Verify Alerts for SW Service : Rsyslog
    ...  Reference : https://jts.seagate.com/browse/TEST-21261
    [Tags]  Priority_High  R2 TEST-21261
    Fail if New alerts exist SW Service  rsyslog
    Acknowledge if Active alerts exist SW Service  rsyslog

TEST-21260
    [Documentation]  CSM GUI: Verify Alerts for SW Service : Statsd
    ...  Reference : https://jts.seagate.com/browse/TEST-21260
    [Tags]  Priority_High  R2 TEST-21260
    Fail if New alerts exist SW Service  statsd
    Acknowledge if Active alerts exist SW Service  statsd

TEST-21259
    [Documentation]  CSM GUI: Verify Alerts for SW Service : Kafka
    ...  Reference : https://jts.seagate.com/browse/TEST-21259
    [Tags]  Priority_High  R2 TEST-21259
    Fail if New alerts exist SW Service  kafka
    Acknowledge if Active alerts exist SW Service  kafka

TEST-21258
    [Documentation]  CSM GUI: Verify Alerts for SW Service : Scsi-network-relay
    ...  Reference : https://jts.seagate.com/browse/TEST-21258
    [Tags]  Priority_High  R2 TEST-21258
    Fail if New alerts exist SW Service  scsi-network-relay
    Acknowledge if Active alerts exist SW Service  scsi-network-relay

TEST-21256
    [Documentation]  CSM GUI: Verify Alerts for SW Service : Consul
    ...  Reference : https://jts.seagate.com/browse/TEST-21256
    [Tags]  Priority_High  R2 TEST-21256
    Fail if New alerts exist SW Service  hare-consul-agent
    Fail if New alerts exist SW Service  hare-consul-agent-c1
    Fail if New alerts exist SW Service  hare-consul-agent-c2
    Acknowledge if Active alerts exist SW Service  hare-consul-agent
    Acknowledge if Active alerts exist SW Service  hare-consul-agent-c1
    Acknowledge if Active alerts exist SW Service  hare-consul-agent-c2

TEST-21257
    [Documentation]  CSM GUI: Verify Alerts for SW Service : ElasticSearch-OSS
    ...  Reference : https://jts.seagate.com/browse/TEST-21257
    [Tags]  Priority_High  R2 TEST-21257
    Fail if New alerts exist SW Service  elasticsearch
    Acknowledge if Active alerts exist SW Service  elasticsearch

TEST-19878
    [Documentation]  CSM GUI: Verify Alerts for SW Service
    ...  Reference : https://jts.seagate.com/browse/TEST-19878
    [Tags]  Priority_High  R2 TEST-19878
    Fail if New alerts exist SW Service  haproxy
    Fail if New alerts exist SW Service  multipathd
    Fail if New alerts exist SW Service  glusterd
    Fail if New alerts exist SW Service  salt-master
    Fail if New alerts exist SW Service  salt-minion
    Fail if New alerts exist SW Service  lnet
    Fail if New alerts exist SW Service  slapd
    Fail if New alerts exist SW Service  rsyslog
    Fail if New alerts exist SW Service  statsd
    Fail if New alerts exist SW Service  kafka
    Fail if New alerts exist SW Service  scsi-network-relay
    Fail if New alerts exist SW Service  hare-consul-agent
    Fail if New alerts exist SW Service  hare-consul-agent-c1
    Fail if New alerts exist SW Service  hare-consul-agent-c2
    Fail if New alerts exist SW Service  elasticsearch
	Acknowledge if Active alerts exist SW Service  haproxy
    Acknowledge if Active alerts exist SW Service  multipathd
    Acknowledge if Active alerts exist SW Service  glusterd
    Acknowledge if Active alerts exist SW Service  salt-master
    Acknowledge if Active alerts exist SW Service  salt-minion
    Acknowledge if Active alerts exist SW Service  lnet
    Acknowledge if Active alerts exist SW Service  slapd
    Acknowledge if Active alerts exist SW Service  rsyslog
    Acknowledge if Active alerts exist SW Service  statsd
    Acknowledge if Active alerts exist SW Service  kafka
    Acknowledge if Active alerts exist SW Service  scsi-network-relay
    Acknowledge if Active alerts exist SW Service  hare-consul-agent
    Acknowledge if Active alerts exist SW Service  hare-consul-agent-c1
    Acknowledge if Active alerts exist SW Service  hare-consul-agent-c2
    Acknowledge if Active alerts exist SW Service  elasticsearch
