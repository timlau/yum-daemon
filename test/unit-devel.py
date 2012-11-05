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


    def test_Locking(self):
        '''
        Test Unlock and Lock
        '''
        print
        # release the lock (grabbed by setUp)
        self.Unlock()
        # calling a method without a lock should raise a YumLockedError
        # self.assertRaises(YumLockedError,self.Install, '0xFFFF')
        # trying to unlock method without a lock should raise a YumLockedError
        self.assertRaises(YumLockedError,self.Unlock)
        # get the Lock again, else tearDown will fail
        self.Lock()
