import sys, os
sys.path.insert(0,os.path.abspath('client'))
from base import TestBase
from yumdaemon import YumLockedError
#from nose.exc import SkipTest

"""
This module is used for testing new unit tests
When the test method is completted it is move som test-api.py

use 'nosetest -v -s unit-devel.py' to run the tests
"""

class TestAPIDevel(TestBase):

    def __init__(self, methodName='runTest'):
        TestBase.__init__(self, methodName)


    def test_GetConfig(self):
        '''
        System: GetConfig & SetConfig
        '''
        all_conf = self.GetConfig('*')
        self.assertIsInstance(all_conf, dict)
        for key in all_conf:
            print "   %s = %s" % (key,all_conf[key])
        kpn = self.GetConfig('kernelpkgnames')
        self.assertIsInstance(kpn, list)
        print "kernelpkgnames : %s" % kpn
        skip_broken = self.GetConfig('skip_broken')
        self.assertIn(skip_broken, [True,False])
        print "skip_broken : %s" % skip_broken
        not_found = self.GetConfig('not_found')
        print "not_found : %s" % not_found
        self.assertIsNone(not_found)
        rc = self.SetConfig("skip_broken", not skip_broken)
        self.assertTrue(rc)
        sb = self.GetConfig('skip_broken')
        self.assertIs(sb, not skip_broken)
        rc = self.SetConfig("skip_broken",skip_broken)
        self.assertTrue(rc)
        sb = self.GetConfig('skip_broken')
        self.assertIs(sb, skip_broken)
