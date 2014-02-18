import sys, os
sys.path.insert(0,os.path.abspath('client'))
#from base import TestBaseReadonly as TestBase
from base import TestBase, TestBaseReadonly
from dnfdaemon import LockedError
from subprocess import check_output, call
from nose.exc import SkipTest

"""
This module is used for testing new unit tests
When the test method is completted it is move som test-api.py

use 'nosetest -v -s unit-devel.py' to run the tests
"""

class TestAPIDevel(TestBaseReadonly):

    def __init__(self, methodName='runTest'):
        TestBaseReadonly.__init__(self, methodName)
        
    def test_Locking(self):
        '''
        Session: Unlock and Lock
        '''
        print
        # release the lock (grabbed by setUp)
        self.Unlock()
        # calling a method without a lock should raise a YumLockedError
        # self.assertRaises(YumLockedError,self.Install, '0xFFFF')
        # trying to unlock method without a lock should raise a YumLockedError
        self.assertRaises(LockedError,self.Unlock)
        # get the Lock again, else tearDown will fail
        self.Lock()

    def test_GetPackages(self):
        '''
        Session: GetPackages & GetAttribute
        '''
        print
        for narrow in ['installed','available']:
            print(' Getting packages : %s' % narrow)
            pkgs = self.GetPackages(narrow)
            self.assertIsInstance(pkgs, list)
            self.assertGreater(len(pkgs),0) # the should be more than once
            print('  packages found : %s ' % len(pkgs))
            pkg_id = pkgs[-1] # last pkg in list
            print(pkg_id)
            self._show_package(pkg_id)
        for narrow in ['updates','obsoletes','recent','extras']:
            print(' Getting packages : %s' % narrow)
            pkgs = self.GetPackages(narrow)
            self.assertIsInstance(pkgs, list)
            print('  packages found : %s ' % len(pkgs))
            if len(pkgs) > 0:
                pkg_id = pkgs[0] # last pkg in list
                print(pkg_id)
                self._show_package(pkg_id)
        for narrow in ['notfound']: # Dont exist, but it should not blow up
            print(' Getting packages : %s' % narrow)
            pkgs = self.GetPackages(narrow)
            self.assertIsInstance(pkgs, list)
            self.assertEqual(len(pkgs),0) # the should be notting
            print('  packages found : %s ' % len(pkgs))
            
    def test_GetPackagesByName(self):
        '''
        Session: GetPackagesByName
        '''
        print
        print "Get all available versions of yum"
        pkgs = self.GetPackagesByName('yum', newest_only=False)
        # pkgs should be a list instance
        self.assertIsInstance(pkgs, list)
        num1 = len(pkgs)
        self.assertNotEqual(num1, 0) # yum should always be there
        for pkg in pkgs:
            print "  Package : %s" % pkg
            (n, e, v, r, a, repo_id) = self.to_pkg_tuple(pkg)
            self.assertEqual(n,"yum")
        print "Get newest versions of yum"
        pkgs = self.GetPackagesByName('yum', newest_only=True)
        # pkgs should be a list instance
        self.assertIsInstance(pkgs, list)
        num2 = len(pkgs)
        self.assertEqual(num2, 1) # there can only be one :)
        for pkg in pkgs:
            print "  Package : %s" % pkg
            (n, e, v, r, a, repo_id) = self.to_pkg_tuple(pkg)
            self.assertEqual(n,"yum")
        print "Get the newest packages starting with yum-plugin-"
        pkgs = self.GetPackagesByName('yum-plugin-*', newest_only=True)
        # pkgs should be a list instance
        self.assertIsInstance(pkgs, list)
        num3 = len(pkgs)
        self.assertGreater(num3, 1) # there should be more than one :)
        for pkg in pkgs:
            print "  Package : %s" % pkg
            (n, e, v, r, a, repo_id) = self.to_pkg_tuple(pkg)
            self.assertTrue(n.startswith('yum'))
