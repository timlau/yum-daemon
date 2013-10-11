import sys, os
sys.path.insert(0,os.path.abspath('client'))
#from base import TestBaseReadonly as TestBase
from base import TestBase
from yumdaemon import YumLockedError
from subprocess import check_output, call
from nose.exc import SkipTest

"""
This module is used for testing new unit tests
When the test method is completted it is move som test-api.py

use 'nosetest -v -s unit-devel.py' to run the tests
"""

class TestAPIDevel(TestBase):

    def __init__(self, methodName='runTest'):
        TestBase.__init__(self, methodName)
        
            


    def test_GPGKeyInstall(self):
        '''
        System: GPG Key installation
        '''
        print "\n"
        # make sure yum-plugins-keys is installed
        self.Unlock()                
        rc = call('sudo yum -y install yum-plugin-keys &>/dev/null', shell=True)
        self.Lock()                
        output = check_output("yum keys | grep Fedora", shell=True)
        # uninstall the Fedora GPG key
        if output.startswith('Fedora'):
            hexkey = output.split(' installed ')[-1][:17]
            print '\nhexkey : [%s]' % hexkey
            self.Unlock()                
            rc = call('sudo yum -y keys-remove %s &>/dev/null' % hexkey, shell=True)
            self.Lock()       
        # Make sure test package is not installed            
        rc, output = self.Remove('0xFFFF')
        if rc == 2:
            retcode = self.RunTransaction()
            self.assertEqual(retcode, 0)
        # Both test packages should be uninstalled now
        self.assertFalse(self._is_installed('0xFFFF'))
        self.reset_signals()
        rc, output = self.Install('0xFFFF')
        self.assertEqual(rc,2)
        self.show_transaction_result(output)
        retcode = self.RunTransaction()
        self.assertEqual(retcode, 1) # we should get a retcode=1 for gpg key needed
        self.assertTrue(self.check_signal('GPGImport')) # check if we got a GPGImport signal
        print "GPG Info : ",repr(self._gpg_confirm)
        self.assertEqual(len(self._gpg_confirm), 5)
        (pkg_id, userid, hexkeyid, keyurl, timestamp) = self._gpg_confirm
        self.ConfirmGPGImport(hexkeyid, True) # confirm the gpg key import
        retcode = self.RunTransaction() # run the transaction again
        self.assertEqual(retcode, 0) # we should get a retcode=0 now
        self.assertTrue(self._is_installed('0xFFFF'))
        # cleanup remove the test package again
        rc, output = self.Remove('0xFFFF')
        self.assertEqual(rc,2)
        retcode = self.RunTransaction()
        self.assertEqual(retcode, 0)
        
