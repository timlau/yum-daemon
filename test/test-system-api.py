import sys, os
sys.path.insert(0,os.path.abspath('client'))
from base import TestBase
from yumdaemon import YumLockedError
from nose.exc import SkipTest


class TestAPI(TestBase):

    def __init__(self, methodName='runTest'):
        TestBase.__init__(self, methodName)

    def test_Locking(self):
        '''
        System: Unlock and Lock
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

    def test_InstallRemove(self):
        '''
        System: Install and Remove
        '''
        print
        # Make sure that the test packages is not installed
        rc, output = self.Remove('0xFFFF Hermes')
        if rc == 2:
            self.show_transaction_result(output)
            self.RunTransaction()
        # Both test packages should be uninstalled now
        self.assertFalse(self._is_installed('0xFFFF'))
        self.assertFalse(self._is_installed('Hermes'))
        # Install the test packages
        print "Installing Test Packages : 0xFFFF Hermes"
        rc, output = self.Install('0xFFFF Hermes')
        print('  Return Code : %i' % rc)
        self.assertEqual(rc,2)
        self.show_transaction_result(output)
        self.assertGreater(len(output),0)
        for action, pkgs in output:
            self.assertEqual(action,u'install')
            self.assertGreater(len(pkgs),0)
        self.RunTransaction()
        # Both test packages should be installed now
        self.assertTrue(self._is_installed('0xFFFF'))
        self.assertTrue(self._is_installed('Hermes'))
        # Remove the test packages
        print "Removing Test Packages : 0xFFFF Hermes"
        rc, output = self.Remove('0xFFFF Hermes')
        print('  Return Code : %i' % rc)
        self.assertEqual(rc,2)
        self.show_transaction_result(output)
        self.assertGreater(len(output),0)
        for action, pkgs in output:
            self.assertEqual(action,u'remove')
            self.assertGreater(len(pkgs),0)
        self.RunTransaction()

    def test_Reinstall(self):
        '''
        System: Reinstall
        '''
        # install test package
        rc, output = self.Install('0xFFFF')
        if rc == 2:
            self.show_transaction_result(output)
            self.RunTransaction()
        self.assertTrue(self._is_installed('0xFFFF'))
        rc, output = self.Reinstall('0xFFFF')
        print('  Return Code : %i' % rc)
        self.assertEqual(rc,2)
        self.show_transaction_result(output)
        self.assertGreater(len(output),0)
        for action, pkgs in output:
            self.assertEqual(action,u'install')
            self.assertEqual(len(pkgs),1)
        self.RunTransaction()
        self.assertTrue(self._is_installed('0xFFFF'))
        # cleanup again
        rc, output = self.Remove('0xFFFF')
        if rc == 2:
            self.show_transaction_result(output)
            self.RunTransaction()
        self.assertFalse(self._is_installed('0xFFFF'))

    def test_DowngradeUpdate(self):
        '''
        System: DownGrade & Update
        '''
        print
        # Test if more then one version if yumex is available
        # use the fedora-yumex repo to get more than one (http:/repos.fedorapeople.org)
        pkgs = self.GetPackagesByName('yumex',False)
        print(pkgs)
        if not len(pkgs) > 1:
            raise SkipTest('more than one available version of yumex is needed for downgrade test')
        rc, output = self.Downgrade('yumex')
        print('  Return Code : %i' % rc)
        print('  output : %s' % output)
        if rc == 0:
            raise SkipTest('nothing to do in Downgrade(\'yumex\')')
        self.assertEqual(rc,2)
        self.show_transaction_result(output)
        self.assertGreater(len(output),0)
        for action, pkgs in output:
            # old version of yumex might need python-enum
            self.assertIn(action,[u'install',u'remove',u'install'])
            self.assertGreater(len(pkgs),0)
        self.RunTransaction()
        rc, output = self.Update('yumex')
        print('  Return Code : %i' % rc)
        self.assertEqual(rc,2)
        self.show_transaction_result(output)
        self.assertGreater(len(output),0)
        for action, pkgs in output:
            self.assertEqual(action,u'update')
            self.assertGreater(len(pkgs),0)
        self.RunTransaction()


    def test_GetPackagesByName(self):
        '''
        System: GetPackagesByName
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



    def test_AddTransaction(self):
        '''
        System: AddTransaction
        '''
        print
        txmbrs = self._add_to_transaction('0xFFFF')
        self.assertEqual(len(txmbrs),1)
        self.show_transaction_list(txmbrs)
        (n, e, v, r, a, repo_id, ts_state) = self.to_txmbr_tuple(txmbrs[0])
        if repo_id[0] == '@': # is installed ?
            self.assertEqual(ts_state,'e') # if package is install, then remove
        else:
            self.assertEqual(ts_state,'u') # if package is not install, then install

    def test_GetTransaction(self):
        '''
        System: GetTransaction
        '''
        print
        self._add_to_transaction('0xFFFF')
        txmbrs = self.GetTransaction()
        self.assertIsInstance(txmbrs, list)
        self.assertEqual(len(txmbrs),1)
        (n, e, v, r, a, repo_id, ts_state) = self.to_txmbr_tuple(txmbrs[0])
        self.assertEqual(n,'0xFFFF')
        # clear the transaction
        self.ClearTransaction()
        txmbrs = self.GetTransaction()
        self.assertIsInstance(txmbrs, list)
        self.assertEqual(len(txmbrs),0) # Transaction should be empty


    def test_RunTransaction(self):
        '''
        System: RunTransaction
        '''
        print
        # Do it twice to revert it
        for x in range(2):
            txmbrs = self._add_to_transaction('0xFFFF')
            self.assertEqual(len(txmbrs),1)
            self.show_transaction_list(txmbrs)
            self._run_transaction()


    def test_GetPackages(self):
        '''
        System: GetPackages and GetAttribute
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
        

    def test_Repositories(self):
        '''
        System: GetRepository and GetRepo
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
 
    def test_Search(self):
        '''
        System: Search
        '''
        fields = ['name','summary']
        keys = ['yum','plugin']
        pkgs = self.Search(fields, keys ,True,True, False)
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
        

    def test_Groups(self):
        """
        System: Groups (GetGroups & GetGroupPackages)
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



    def test_GetPackageWithAttributes(self):
        '''
        System: GetPackageWithAttributes
        '''
        
        print()
        for pkg_filter in ['installed','available','updates','obsoletes','recent','extras']:
            print(" --> Checking filter : %s" % pkg_filter)
            result = self.GetPackageWithAttributes(pkg_filter, ['summary','size'])
            self.assertIsInstance(result, list) # cat is a list
            print("     Got %i packages" % len(result))
            if len(result) > 1:
                self.assertIsInstance(result[1], list) # cat is a list
                self.assertEqual(len(result[1]),3)


    def test_History(self):
        '''
        System: History
        '''
        result = self.GetHistoryByDays(0, 5)
        self.assertIsInstance(result, list)
        for tx_mbr in result:
            tid, dt = tx_mbr
            print("%-4i - %s" % (tid, dt))
            self.assertIsInstance(dt, unicode)
            pkgs = self.GetHistoryPackages(tid)
            self.assertIsInstance(pkgs, list)
            for (id, state, is_installed) in pkgs:
                print id, state, is_installed
                self.assertIsInstance(id, unicode)
                self.assertIsInstance(state, unicode)
                self.assertIsInstance(is_installed, bool)
