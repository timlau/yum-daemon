import sys, os
sys.path.insert(0,os.path.abspath('../'))
import dbus
from base import TestBase
from client import YumLockedError
from unittest import skipIf
import json


class TestAPI(TestBase):
    
    def __init__(self, methodName='runTest'):
        TestBase.__init__(self, methodName)
        
    def _run_transaction(self):
        pass
        
    def test_Locking(self):
        print
        # release the lock (grabbed by setUp)
        self.client.Unlock()
        # calling a method without a lock should raise a YumLockedError
        self.assertRaises(YumLockedError,self.client.Install, '0xFFFF')
        # trying to unlock method without a lock should raise a YumLockedError
        self.assertRaises(YumLockedError,self.client.Unlock)
        # get the Lock again, else tearDown will fail
        self.client.Lock()
        
    def test_InstallRemove(self):
        print
        for x in range(2): # Do it twice to revert the action
            if not self._is_installed('0xFFFF'):
                is_installed = False
                result = self.client.Install('0xFFFF')
            else:
                is_installed = True
                result = self.client.Remove('0xFFFF')                
            # result should be a dbus.String instance
            self.assertIsInstance(result, dbus.String)
            rc, output = json.loads(result)
            self.assertEqual(rc,2)
            self.show_transaction_result(output)
            self.assertGreater(len(output),0)
            for action, pkgs in output:
                if is_installed:
                    self.assertEqual(action,u'Removing')
                else:
                    self.assertEqual(action,u'Installing')                    
                self.assertGreater(len(pkgs),0)
                name,arch, ver, repoid, size, replace = pkgs[0]
                self.assertEqual(name,"0xFFFF")
                self.assertEqual(replace,[])
            self._run_transaction()

    def test_GetPackagesByName(self):
        print
        print "Get all available versions of yum"
        pkgs = self.client.GetPackagesByName('yum', newest_only=False)
        # pkgs should be a dbus.Array instance
        self.assertIsInstance(pkgs, dbus.Array)
        num1 = len(pkgs)            
        self.assertNotEqual(num1, 0) # yum should always be there
        for pkg in pkgs:
            print "  Package : %s" % pkg
            (n, e, v, r, a, repo_id) = self.client.to_pkg_tuple(pkg)
            self.assertEqual(n,"yum")
        print "Get newest versions of yum"
        pkgs = self.client.GetPackagesByName('yum', newest_only=True)
        # pkgs should be a dbus.Array instance
        self.assertIsInstance(pkgs, dbus.Array)
        num2 = len(pkgs)            
        self.assertEqual(num2, 1) # there can only be one :)
        for pkg in pkgs:
            print "  Package : %s" % pkg
            (n, e, v, r, a, repo_id) = self.client.to_pkg_tuple(pkg)
            self.assertEqual(n,"yum")
        print "Get the newest packages starting with yum-plugin-"
        pkgs = self.client.GetPackagesByName('yum-plugin-*', newest_only=True)
        # pkgs should be a dbus.Array instance
        self.assertIsInstance(pkgs, dbus.Array)
        num3 = len(pkgs)            
        self.assertGreater(num3, 1) # there should be more than one :)
        for pkg in pkgs:
            print "  Package : %s" % pkg
            (n, e, v, r, a, repo_id) = self.client.to_pkg_tuple(pkg)
            self.assertTrue(n.startswith('yum'))


    
    def test_AddTransaction(self):
        print
        txmbrs = self._add_to_transaction('0xFFFF')
        self.assertEqual(len(txmbrs),1)
        self.show_transaction_list(txmbrs)
        (n, e, v, r, a, repo_id, ts_state) = self.client.to_txmbr_tuple(txmbrs[0])
        if repo_id[0] == '@': # is installed ?
            self.assertEqual(ts_state,'e') # if package is install, then remove
        else:                                        
            self.assertEqual(ts_state,'u') # if package is not install, then install
            
    def test_GetTransaction(self):
        print
        self._add_to_transaction('0xFFFF')
        txmbrs = self.client.GetTransaction()
        self.assertIsInstance(txmbrs, dbus.Array)
        self.assertEqual(len(txmbrs),1)
        (n, e, v, r, a, repo_id, ts_state) = self.client.to_txmbr_tuple(txmbrs[0])
        self.assertEqual(n,'0xFFFF')
        # clear the transaction
        self.client.ClearTransaction()
        txmbrs = self.client.GetTransaction()
        self.assertIsInstance(txmbrs, dbus.Array)
        self.assertEqual(len(txmbrs),0) # Transaction should be empty
        
        
    def test_RunTransaction(self):
        print
        # Do it twice to revert it 
        for x in range(2):
            txmbrs = self._add_to_transaction('0xFFFF')
            self.assertEqual(len(txmbrs),1)
            self.show_transaction_list(txmbrs)
            self._run_transaction()
            

    def test_GetPackages(self):
        '''
        Tesing GetPackages and GetAttribute
        '''
        print
        for narrow in ['installed','available']:
            print(' Getting packages : %s' % narrow)
            pkgs = self.client.GetPackages(narrow)
            self.assertIsInstance(pkgs, dbus.Array)
            self.assertGreater(len(pkgs),0) # the should be more than once
            print('  packages found : %s ' % len(pkgs))
            id = pkgs[-1] # last pkg in list
            self._show_package(id)
        for narrow in ['updates','obsoletes','recent','extras']:
            print(' Getting packages : %s' % narrow)
            pkgs = self.client.GetPackages(narrow)
            self.assertIsInstance(pkgs, dbus.Array)
            print('  packages found : %s ' % len(pkgs))
            if len(pkgs) > 0:
                id = pkgs[0] # last pkg in list
                self._show_package(id)
        for narrow in ['notfound']: # Dont exist, but it should not blow up
            print(' Getting packages : %s' % narrow)
            pkgs = self.client.GetPackages(narrow)
            self.assertIsInstance(pkgs, dbus.Array)
            self.assertEqual(len(pkgs),0) # the should be notting
            print('  packages found : %s ' % len(pkgs))

    def test_GetConfig(self):
        ''' Testing GetConfig'''
        all_conf = self.client.GetConfig('*')
        self.assertIsInstance(all_conf, dict)
        for key in all_conf:
            print "   %s = %s" % (key,all_conf[key])
        kpn = self.client.GetConfig('kernelpkgnames')
        self.assertIsInstance(kpn, list)
        print "kernelpkgnames : %s" % kpn        
        skip_broken = self.client.GetConfig('skip_broken')
        self.assertIn(skip_broken, [True,False])
        print "skip_broken : %s" % skip_broken
        not_found = self.client.GetConfig('not_found')
        print "not_found : %s" % not_found
        self.assertIsNone(not_found)
    
    def test_GetRepositories(self):
        '''
        *** Testing Repository Methods ***
        '''
        print
        print "  Getting source repos"
        repos = self.client.GetRepositories('*-source')
        self.assertIsInstance(repos, list)
        for repo_id in repos:
            print "    Repo : %s" % repo_id
            self.assertTrue(repo_id.endswith('-source'))
        print "  \nGetting fedora repository"
        repo = self.client.GetRepo('fedora')
        self.assertIsInstance(repo, dict)
        print "  Repo: fedora"
        print "  Name : %s " % repo['name']
        print "  Mirrorlist :\n  %s " % repo['mirrorlist']
        # check for a repo not there
        repo = self.client.GetRepo('XYZCYZ')
        self.assertIsNone(repo)
    

        