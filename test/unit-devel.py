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


    def test_Repositories(self):
        '''
        Session: GetRepository and GetRepo
        '''
        print
        print "  Getting source repos"
        repos = self.GetRepositories('*-source')
        self.assertIsInstance(repos, list)
        for repo_id in repos:
            print "    Repo : %s" % repo_id
            self.assertTrue(repo_id.endswith('-source'))
        print "  \nGetting fedora repository"
        repo = self.GetRepo('fedora')
        self.assertIsInstance(repo, dict)
        print "  Repo: fedora"
        print "  Name : %s " % repo['name']
        print "  Mirrorlist :\n  %s " % repo['mirrorlist']
        # check for a repo not there
        repo = self.GetRepo('XYZCYZ')
        self.assertIsNone(repo)
        enabled_pre = self.GetRepositories('enabled')
        print("before : ", enabled_pre)
        self.SetEnabledRepos(['fedora'])
        enabled = self.GetRepositories('enabled')
        print("after : ", enabled)
        self.assertEqual(len(enabled),1) # the should only be one :)
        self.assertEqual(enabled[0],'fedora') # and it should be 'fedora'
        self.SetEnabledRepos(enabled_pre)
        enabled = self.GetRepositories('enabled')
        print("bact to start : ", enabled)
        self.assertEqual(len(enabled),len(enabled_pre)) # the should only be one :)
        self.assertEqual(enabled,enabled_pre) # and it should be 'fedora'
 