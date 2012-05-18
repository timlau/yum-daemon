import sys
import os.path
sys.path.insert(0,os.path.abspath('../'))
import unittest
import dbus
import json
from datetime import date
from client import YumDaemonClient

class TestBase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        self.client = YumDaemonClient()
    
    def setUp(self):
        self.client.Lock()
    
    def tearDown(self):
        self.client.Unlock()
        
    def show_changelog(self, changelog, max_elem=3):
        i = 0
        for (c_date, c_ver, msg) in changelog:
            i += 1
            if i > max_elem:
                return
            print("* %s %s" % (date.fromtimestamp(c_date).isoformat(), c_ver))
            for line in msg.split('\n'):
                print("%s" % line)
    
    def show_package_list(self, pkgs):    
        for id in pkgs:
            (n, e, v, r, a, repo_id) = self.client.to_pkg_tuple(id)
            print " --> %s-%s:%s-%s.%s (%s)" % (n, e, v, r, a, repo_id)
    
    def show_transaction_list(self, pkgs):    
        for id in pkgs:
            id = str(id)
            (n, e, v, r, a, repo_id, ts_state) = self.client.to_txmbr_tuple(id)
            print " --> %s-%s:%s-%s.%s (%s) - %s" % (n, e, v, r, a, repo_id, ts_state)
    
    def show_transaction_result(self, output):
        for action, pkgs in output:
            print "  %s" % action
            for pkg in pkgs:
                print "  --> %s" % str(pkg)
        
# ======================== Helpers =======================        
    def _add_to_transaction(self, name):
        '''
        Helper to add a package to transaction
        '''
        pkgs = self.client.GetPackagesByName(name, newest_only=True)
        # pkgs should be a dbus.Array instance
        self.assertIsInstance(pkgs, dbus.Array)
        self.assertEqual(len(pkgs),1)
        pkg = pkgs[0]
        (n, e, v, r, a, repo_id) = self.client.to_pkg_tuple(pkg)
        if repo_id[0] == '@':
            action='remove'
        else:
            action='install'
        txmbrs = self.client.AddTransaction(pkg,action)
        self.assertIsInstance(txmbrs, dbus.Array)
        return txmbrs
        
    def _run_transaction(self, build=True):
        '''
        Desolve deps and run the current transaction
        '''
        print('************** Running the current transaction *********************')
        if build:
            result = self.client.BuildTransaction()
            self.assertIsInstance(result, dbus.String)
            rc, output = json.loads(result)
            self.assertEqual(rc,2)
            self.show_transaction_result(output)
            self.assertGreater(len(output),0)
        self.client.RunTransaction()
        
    def _is_installed(self, name):
        pkgs = self.client.GetPackagesByName(name, newest_only=True)
        # pkgs should be a dbus.Array instance
        self.assertIsInstance(pkgs, dbus.Array)
        self.assertTrue(len(pkgs)>0)
        for pkg in pkgs:
            (n, e, v, r, a, repo_id) = self.client.to_pkg_tuple(pkg)
            if repo_id[0] == '@':
                return True
        return False
        
    def _show_package(self, id):
        (n, e, v, r, a, repo_id) = self.client.to_pkg_tuple(id)
        print "\nPackage attributes"
        self.assertIsInstance(n, str)             
        print "Name : %s " % n
        summary = self.client.GetAttribute(id, 'summary')
        self.assertIsInstance(summary, unicode)             
        print "Summary : %s" % summary     
        print "\nDescription:"     
        desc = self.client.GetAttribute(id, 'description')         
        self.assertIsInstance(desc, unicode)             
        print desc                
        print "\nChangelog:"             
        changelog = self.client.GetAttribute(id, 'changelog')
        self.assertIsInstance(changelog, list)             
        self.show_changelog(changelog, max_elem=2)
        # Check a not existing attribute dont make it blow up   
        notfound = self.client.GetAttribute(id, 'notfound')
        self.assertIsNone(notfound)      
        print " Value of attribute 'notfound' : %s" % notfound
               
        