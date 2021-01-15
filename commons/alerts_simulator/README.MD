README for Alert Simulation API 
API can be found in eos_test/utility/alerts_simulator/generate_alert.lib

**Input parameters for API:**
1. 'alert_type: AlertType' : This is the type of alert to be generated.
   Type of alerts which can be generated using this API are:
   -----------------------------------------------------------------------------
   |   Alert type string                            |     VM support           |
   -----------------------------------------------------------------------------
   | controller_fault                               |         No               |
   -----------------------------------------------------------------------------
   | controller_fault_resolved                      |         No               |
   -----------------------------------------------------------------------------
   | psu_fault                                      |         No               |
   -----------------------------------------------------------------------------
   | psu_fault_resolved                             |         No               |
   -----------------------------------------------------------------------------

   *Note: Please pass the exact same alert type string.

2. 'host_details' = This is the dictionary which contains credential details of
                    the host on which alert is to be generated.
    This dictionary should contain keys as follows:
    host_details = {"host": "", "host_user": "", "host_password": ""}

    If host_details=None is given, then it will take default parameters.

    *Note: It is recommended, that host_details should be passed with all
    expected values. Please do not pass it as None.

3. 'enclosure_details' = This is the dictionary which contains credential
                         details of the host on which alert is to be generated.
    This dictionary should contain keys as follows:
    host_details = {"enclosure_ip": "", "enclosure_user": "", "enclosure_pwd": ""}

    If enclosure_details=None is given, then it will take default parameters.

    *Note: It is recommended, that enclosure_details should be passed with all
    expected values. Please do not pass it as None.

4. 'input_parameters' = This is the dictionary which contains parameters used
                        for alert generation as per the utility being used.

    This dictionary should contain keys as per the input parameters required by
    the utility being used for alert generation.

    If input_parameters=None is given, then it will take default parameters.
    Default parameters are added in
    eos_test/utility/alerts_simulator/constants.py.

    *Note: Please do not change default parameters give in constants.py file.

**Required Packages**
- Please make sure that python package 'aenum' is installed in your virtual
  environment before running this API.
  If it is not installed, please run following command in you virtual
  environment:
  pip3 install -r requirements.txt

