import sys, os
sys.path.insert(0,os.path.abspath('client'))
from base import TestBaseReadonly
from yumdaemon import YumLockedError
from nose.exc import SkipTest


class TestAPI(TestBaseReadonly):

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
        self.assertRaises(YumLockedError,self.Unlock)
        # get the Lock again, else tearDown will fail
        self.Lock()


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

    def test_GetPackages(self):
        '''
        Session: GetPackages and GetAttribute
        '''
        print
        for narrow in ['installed','available']:
            print(' Getting packages : %s' % narrow)
            pkgs = self.GetPackages(narrow)
            self.assertIsInstance(pkgs, list)
            self.assertGreater(len(pkgs),0) # the should be more than once
            print('  packages found : %s ' % len(pkgs))
            pkg_id = pkgs[-1] # last pkg in list
            self._show_package(pkg_id)
        for narrow in ['updates','obsoletes','recent','extras']:
            print(' Getting packages : %s' % narrow)
            pkgs = self.GetPackages(narrow)
            self.assertIsInstance(pkgs, list)
            print('  packages found : %s ' % len(pkgs))
            if len(pkgs) > 0:
                pkg_id = pkgs[0] # last pkg in list
                self._show_package(pkg_id)
        for narrow in ['notfound']: # Dont exist, but it should not blow up
            print(' Getting packages : %s' % narrow)
            pkgs = self.GetPackages(narrow)
            self.assertIsInstance(pkgs, list)
            self.assertEqual(len(pkgs),0) # the should be notting
            print('  packages found : %s ' % len(pkgs))

    def test_GetConfig(self):
        '''
        Session: GetConfig
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

    def test_GetRepositories(self):
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

    def test_Search(self):
        '''
        Session: Search
        '''
        fields = ['name','summary']
        keys = ['yum','plugin']
        pkgs = self.Search(fields, keys ,True,True,False)
        self.assertIsInstance(pkgs, list)
        for p in pkgs:
            summary = self.GetAttribute(p,'summary')
            print str(p),summary
            self.assertTrue(keys[0] in str(p) or keys[0] in summary)
            self.assertTrue(keys[1] in str(p) or keys[1] in summary)
        keys = ['yum','zzzzddddsss'] # second key should not be found
        pkgs = self.Search(fields, keys ,True,True, False)
        self.assertIsInstance(pkgs, list)
        print "found %i packages" % len(pkgs)
        self.assertEqual(len(pkgs), 0) # when should not find any matches
        keys = ['yum','zzzzddddsss'] # second key should not be found
        pkgs = self.Search(fields, keys ,False, True, False)
        self.assertIsInstance(pkgs, list)
        print "found %i packages" % len(pkgs)
        self.assertGreater(len(pkgs), 0) # we should find some matches
        # retro should match some pkgtags        
        keys = ['retro'] # second key should not be found
        pkgs = self.Search(fields, keys ,True, True, True)
        self.assertIsInstance(pkgs, list)
        print "found %i packages" % len(pkgs)
        self.assertGreater(len(pkgs), 0) # we should find some matches

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
                print "   tag: %s name: %s \n   desc: %s \n   installed : %s " % tuple(grp)

    def test_GetPackageWithAttributes(self):
        """
        Session: GetPackageWithAttributes
        """
        print()
        for pkg_filter in ['installed','available','updates','obsoletes','recent','extras']:
            print(" --> Checking filter : %s" % pkg_filter)
            result = self.GetPackageWithAttributes(pkg_filter, ['summary','size'])
            self.assertIsInstance(result, list) # cat is a list
            print("     Got %i packages" % len(result))
            if len(result) > 1:
                self.assertIsInstance(result[1], list) # cat is a list
                self.assertEqual(len(result[1]),3)


