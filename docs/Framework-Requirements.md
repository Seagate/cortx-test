# Functional test automation requirements
* It should be Easy to write tests in framework
* Multiple targets support for faster execution. It should be possible to specify Object Store targets from Jenkins  
* Most of the  libraries and utilities should be built in the framework and should be well structured and organized for readability. 
* Layered architectural pattern for test framework stack and loosely coupled components. Test execution framework should also be loosely coupled from test faremwork
* Local test runner with parallel test execution capabilities (should utilize parallel execution capabilites of test engine `pytest`)
* Distributed execution which intelligently distributes tests among multiple test runners (peers), peers execute tests and collective reports are generated and published to Reporting Server (Mongo DB backend). Peers should execute tests in parallel where ever possible for faster execution.  
* The test environment setup should not be tied to CTP or any OS or Hardware platform. It should run on virtualized platforms and commodity hardware. However it should utilize enterprise hardware capability in case physical machines or high end Vms are available. 
* Pluggable reporting components/formats
* Logging Framework should support Logs per test case, framework logs, html reports for local test run 
* Build over Build Result Analysis and leverage ML Models to do impact analysis and regional regression
* Server-side log and and Crash dump collection per test 
* Integration with Jenkins as a top level scheduler
* Web based reports should be available for each test execution cycle. In automatic Jenkins execution evironment test runners should take care of keeping older logs for suites or tags. All logs can be collected at an NAS share for future.
* Integration with Github/Build server to determine changesets in build
* Dockerized runner environment for local and distributed runner
* Integration with ELK stack or Splunk for easier log analysis of past and present builds.
* CFT combinational and DI test support
* Tagging support

These requirements will be implemented as milestones complying to R2. 
