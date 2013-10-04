import sys, os
sys.path.insert(0,os.path.abspath('client'))
from base import TestBaseReadonly
from yumdaemon import YumLockedError
#from nose.exc import SkipTest

"""
This module is used for testing new unit tests
When the test method is completted it is move som test-api.py

use 'nosetest -v -s unit-devel.py' to run the tests
"""

class TestAPIDevel(TestBaseReadonly):

    def __init__(self, methodName='runTest'):
        TestBaseReadonly.__init__(self, methodName)


    def test_GetGroups(self):
        """
        Session: GetGroups
        """
        
        result = self.GetGroups()
        for cat, grps in result:
            # cat: [category_id, category_name, category_desc]
            self.assertIsInstance(cat, list) # cat is a list
            self.assertIsInstance(grps, list) # grps is a list
            self.assertEqual(len(cat),3) # cat has 3 elements
            print " --> %s" % cat[0]
            for grp in grps:
                # [group_id, group_name, group_desc, group_is_installed]
                self.assertIsInstance(grp, list) # grp is a list
                self.assertEqual(len(grp),4) # grp has 4 elements
                print "   tag: %s name: %s \n       desc: %s \n       installed : %s " % tuple(grp)
                # Test GetGroupPackages
                grp_id = grp[0]
                pkgs = self.GetGroupPackages(grp_id,'all')
                self.assertIsInstance(pkgs, list) # cat is a list
                print "       # of Packages in group         : ",len(pkgs)
                pkgs = self.GetGroupPackages(grp_id,'default')
                self.assertIsInstance(pkgs, list) # cat is a list
                print "       # of Default Packages in group : ",len(pkgs)
