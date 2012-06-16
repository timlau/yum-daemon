import sys, os
sys.path.insert(0,os.path.abspath('client'))
import dbus
from base import TestBase
from yumdaemon2 import YumLockedError
import unittest
import json

"""
This module is used for testing new unit tests
When the test method is completted it is move som test-api.py

use 'nosetest -v -s unit-devel.py' to run the tests
"""

class TestAPIDevel(TestBase):
    
    def __init__(self, methodName='runTest'):
        TestBase.__init__(self, methodName)

#    def test_UpdateAll(self):
#        '''
#        Test Update All
#        '''
#        print
#        # Test if more then one version if yumex is available
#        # use the fedora-yumex repo to get more than one (http:/repos.fedorapeople.org)
#        pkgs = self.client.GetPackages('updates')
#        if not len(pkgs) > 0:
#            unittest.skip('this test need som available updates to work')
#        print("Number of updates : %i" % len(pkgs))
#        result = self.client.Update('')
#        self.assertIsInstance(result, dbus.String)
#        rc, output = json.loads(result)
#        print('  Return Code : %i' % rc)
#        self.assertEqual(rc,2)
#        self.show_transaction_result(output)
#        self.assertGreater(len(output),0)
#        for action, pkgs in output:
#            self.assertEqual(action,u'Updating')                    
#            self.assertGreater(len(pkgs),0)
#        self.client.RunTransaction()


#    def test_History(self):
#        result = self.client.GetHistoryByDays(0, 5)
#        self.assertIsInstance(result, list)
#        for tx_mbr in result:
#            tid, dt = tx_mbr
#            print("%-4i - %s" % (tid, dt))
#            self.assertIsInstance(dt, unicode)
#            pkgs = self.client.GetHistoryPackages(tid)
#            self.assertIsInstance(pkgs, list)
#            for (id, state, is_installed) in pkgs:
#                print id, state, is_installed
#                self.assertIsInstance(id, unicode)
#                self.assertIsInstance(state, unicode)                
#                self.assertIsInstance(is_installed, bool)
                
            
        