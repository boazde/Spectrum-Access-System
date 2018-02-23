#    Copyright 2017 SAS Project Authors. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

from datetime import datetime
import json
import logging
import os
from os import listdir
from os.path import isfile, join
import sas
import sas_testcase

from util import winnforum_testcase, configurable_testcase, writeConfig, loadConfig, PropagationAntennaModelQuery
  
def cbsddata(device):
    installationParam = device['installationParam']
    if 'antennaAzimuth' not in installationParam:
        installationParam['antennaAzimuth'] = None
        
    cbsd = {'latitude': installationParam['latitude'],
             'longitude': installationParam['longitude'],
              'height': installationParam['height'],
              'heightType': installationParam['heightType'],
              'indoorDeployment': installationParam['indoorDeployment'],
              'antennaAzimuth': installationParam['antennaAzimuth'],
              'antennaGain': installationParam['antennaGain'],
              'antennaBeamwidth': installationParam['antennaBeamwidth'],
              'cbsdCategory': device['cbsdCategory']}
    return cbsd

def fssdata(fss_record, rx_antenna_gain_required=None):
    deploymentParam = fss_record['deploymentParam'][0]
    installationParam = deploymentParam['installationParam']
    if 'antennaAzimuth' not in installationParam:
        installationParam['antennaAzimuth'] = None
        
    fss = {'latitude': installationParam['latitude'],
             'longitude': installationParam['longitude'],
              'height': installationParam['height'],
              'antennaAzimuth': installationParam['antennaAzimuth'],
              'antennaGain': installationParam['antennaGain'],
              'antennaElevation': installationParam['antennaDowntilt']}
    if rx_antenna_gain_required is not None:
        fss['rx_antenna_gain_required'] = rx_antenna_gain_required
    else:
        fss['rx_antenna_gain_required'] = False
    return fss


class PropAndAntennaModelTestcase(sas_testcase.SasTestCase):

  def setUp(self):
    self._sas, self._sas_admin = sas.GetTestingSas()
    #self._sas_admin.Reset()

  def tearDown(self):
      pass

  def generate_FT_S_PAT_default_config(self, filename):
    """Generates the WinnForum configuration for PAT.1."""
    
    # Load Devices
    device_a = json.load(
    open(os.path.join('testcases', 'testdata', 'device_a.json')))

    # load FSS
    fss_record_0 = json.load(
      open(os.path.join('testcases', 'testdata', 'fss_record_0.json')))
    fss_record_0['rxAntennaGainRequired'] = True
    reliability_level = -1
    config = {}
    config[0]= {'reliabilityLevel': reliability_level, 'cbsd': cbsddata(device_a),'fss': fssdata(fss_record_0, True)}

    # Load PPA
    ppa_record = json.load(
        open(os.path.join('testcases', 'testdata', 'ppa_record_3.json')))
     
    reliability_level = -1
    config[1] = {'reliabilityLevel': reliability_level, 'cbsd': cbsddata(device_a),'ppa': ppa_record['zone']['features'][0]}

    writeConfig(filename, config)
      
  @configurable_testcase(generate_FT_S_PAT_default_config)
  def test_WINNF_FT_S_PAT_1(self, config_filename):
    """Query with CBSD and FSS/PPA
   
    If (rxAntennaGainRequired = True)
    The response should have the pathlossDb, txAntennaGainDbi and rxAntennaGainDbi 
 
    If (rxAntennaGainRequired = False or omitted)
    The response should have the pathlossDb, txAntennaGainDbi
    """
    
    propagationAntennaModel = PropagationAntennaModelQuery()

    config = loadConfig(config_filename)
    for configItem in  config:
       request= config[configItem]

       refResponse = propagationAntennaModel.computePropagationAntennaModel(request)

       try:
           sasResponse = self._sas_admin.QueryPropagationAndAntennaModel(request)
           # Check response
           if 'pathlossDb' in refResponse:
               self.assertTrue(sasResponse['pathlossDb'] < refResponse['pathlossDb'] + 1)
               self.assertTrue(sasResponse['txAntennaGainDbi'] < (refResponse['txAntennaGainDbi'] + .2))
           if 'rxAntennaGainDbi' in refResponse:
               self.assertTrue(sasResponse['rxAntennaGainDbi'] < (refResponse['rxAntennaGainDbi'] + .2))
       except AssertionError as e:
           # Allow HTTP status 404
           self.assertEqual(e.args[0], 400)
