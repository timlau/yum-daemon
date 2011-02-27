import sys
import os.path
sys.path.insert(0,os.path.abspath('../'))
import unittest
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
        
        