# -*- coding: utf-8 -*-
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
# (C) 2013 - Tim Lauridsen <timlau@fedoraproject.org>

"""
Common stuff for the yumdaemon dbus services
"""
import dbus
import dbus.service
import dbus.glib
import gobject
import json
import logging
from datetime import datetime
import yum
import yum.Errors as Errors
from yum.callbacks import *
from yum.constants import *
from yum.update_md import UpdateMetadata
from yum.Errors import *
from yum.packageSack import packagesNewestByNameArch


from rpmUtils.arch import canCoinstall

FAKE_ATTR = ['downgrades','action','pkgtags']
NONE = json.dumps(None)


#------------------------------------------------------------------------------ Callback handlers
class DownloadCallback(  DownloadBaseCallback ):
    '''
    Yum Download callback handler class
    the updateProgress will be called while something is being downloaded
    '''
    def __init__(self,base):
        DownloadBaseCallback.__init__(self)
        self.base = base

    def updateProgress(self,name,frac,fread,ftime):
        '''
        Update the progressbar
        :param name: filename
        :param frac: Progress fracment (0 -> 1)
        :param fread: formated string containing BytesRead
        :param ftime : formated string containing remaining or elapsed time
        '''
        # send a DBus signal with progress info
        self.base.UpdateProgress(name,frac,fread,ftime)


logger = logging.getLogger('yumdaemon.service')

def Logger(func):
    """
    This decorator catch yum exceptions and send fatal signal to frontend
    """
    def newFunc(*args, **kwargs):
        logger.debug("%s started args: %s " % (func.__name__, repr(args[1:])))
        rc = func(*args, **kwargs)
        logger.debug("%s ended" % func.__name__)
        return rc

    newFunc.__name__ = func.__name__
    newFunc.__doc__ = func.__doc__
    newFunc.__dict__.update(func.__dict__)
    return newFunc

class YumDaemonBase(dbus.service.Object, DownloadBaseCallback):

    def __init__(self, mainloop):
        DownloadBaseCallback.__init__(self)
        self.logger = logging.getLogger('yumdaemon.base')
        self.mainloop = mainloop # use to terminate mainloop
        self.authorized_sender = set()
        self._lock = None
        self._yumbase = None
        self._can_quit = True
        self._is_working = False
        self._watchdog_count = 0
        self._watchdog_disabled = False
        self._timeout_idle = 20         # time to daemon is closed when unlocked
        self._timeout_locked = 600      # time to daemon is closed when locked and not working
        self._updateMetadata = None     # Cache for yum UpdateMetadata object
        self._updates_list = None       # Cache for updates
        self._obsoletes_list = None     # Cache for obsoletes

    @property
    def yumbase(self):
        '''
        yumbase property so we can auto initialize it if not defined
        '''
        if not self._yumbase:
            self._get_yumbase()
        return self._yumbase


#===============================================================================
# Helper methods
#===============================================================================

    def _enable_repos_from_list(self, repo_ids):
        for repo in self.yumbase.repos.repos.values():
            if repo.id in repo_ids: # is in the positive list
                self.yumbase.repos.enableRepo(repo.id)
            else:
                self.yumbase.repos.disableRepo(repo.id)

    def _get_po_list(self, pkg, fields):

        id = ",".join([pkg.name, pkg.epoch, pkg.ver, pkg.rel, pkg.arch, pkg.ui_from_repo])
        po_list = [id]
        for field in fields:
            if hasattr(pkg,field):
                po_list.append(getattr(pkg,field))
        return po_list



    def _get_groups(self):
        '''
        make a list with categoties and there groups
        This is the old way of yum groups, where a group is a collection of mandatory, default and optional pacakges
        and the group is installed when all mandatory & default packages is installed.
        '''
        all_groups = []
        comps = self.yumbase.comps
        # this is the old way, so grp.installed is set if all mandatory/default packages is installed.
        comps.compile(self.yumbase.rpmdb.simplePkgList())  
        try:
            cats = comps.get_categories()
            for category in cats:
                cat = (category.categoryid, category.ui_name, category.ui_description)
                cat_grps = []
                grps = [comps.return_group(g) for g in category.groups if comps.has_group(g)]
                for grp in grps:
                    elem = (grp.groupid, grp.ui_name, grp.ui_description, grp.installed)
                    cat_grps.append(elem)
                cat_grps.sort()
                all_groups.append((cat, cat_grps))
        except Errors.GroupsError, e:
            print str(e)
        all_groups.sort()
        return json.dumps(all_groups)


    def _get_group_pkgs(self, grp_id, grp_flt):
        '''
        Get packages for a given grp_id and group filter
        '''
        pkgs = []
        try:
            grp = self.yumbase.comps.return_group(grp_id)
            if grp:
                if grp_flt == 'all':
                    best_pkgs = self._group_names2aipkgs(grp.packages)
                else:
                    best_pkgs = self._group_names2aipkgs(grp.mandatory_packages.keys() + grp.default_packages.keys())
                for key in best_pkgs:
                    # Sort the matching packages and take the last one (the best match for current arch)
                    (apkg, ipkg) = sorted(best_pkgs[key], key=lambda x: x[1] or x[0])[-1]
                    if ipkg:
                        pkgs.append(ipkg)
                    else:
                        pkgs.append(apkg)
            else:
                pass
        except Errors.GroupsError, e:
            print str(e)
        pkg_ids = self._to_package_id_list(pkgs)
        return pkg_ids

    def _get_id_time_list(self, hist_trans):
        '''
        return a list of (tid, isodate) pairs from a list of yum history transactions
        '''
        result = []
        for ht in hist_trans:
            tm = datetime.fromtimestamp(ht.end_timestamp)
            result.append((ht.tid, tm.isoformat()))
        return result

    def _get_history_transaction_pkgs(self, tid):
        '''
        return a list of (pkg_id, tx_state, installed_state) pairs from a given
        yum history transaction id
        '''
        tx = self.yumbase.history.old([tid])
        result = []
        for pkg in tx[0].trans_data:
            values = [pkg.name, pkg.epoch, pkg.version, pkg.release, pkg.arch, pkg.ui_from_repo]
            id = ",".join(values)
            elem = (id, pkg.state, pkg.state_installed)
            result.append(elem)
        return result


    def _get_fake_attributes(self,po, attr):
        '''
        Get Fake Attributes, a whey to useful stuff for a package there is not real
        attritbutes to the yum package object.
        :param attr: Fake attribute
        :type attr: string
        '''
        if attr == "action":
            return self._get_action(po)
        elif attr == 'downgrades':
            return self._get_downgrades(po)
        elif attr == 'pkgtags':
            return self._get_pkgtags(po)

    def _get_downgrades(self,pkg):
        pkg_ids = []
        if self._is_installed(pkg): # is installed , we must find available downgrade
            apkgs = self.yumbase.pkgSack.returnPackages(patterns=[pkg.name], ignore_case=False)
            for po in apkgs:
                if self._is_valid_downgrade(pkg, po):
                    pkg_ids.append(self._get_id(po))
        else: # Not installed, this is the package to downgrade to, find the installed one
            ipkgs = self.yumbase.rpmdb.searchNevra(name=pkg.name, arch = pkg.arch)
            if ipkgs:
                pkg_ids.append(self._get_id(ipkgs[0]))
        return pkg_ids

    def _get_pkgtags(self, po):
        '''
        Get pkgtags from a given po
        '''
        pkgtags = self.yumbase.pkgtags
        po_dict = pkgtags.search_names(po.name)
        if po.name in po_dict:
            return po_dict[po.name]
        else:
            return []



    def _is_installed(self, po):
        '''
        Check if a package is installed
        :param po: package to check for
        '''
        (n, a, e, v, r) = po.pkgtup
        po = self.yumbase.rpmdb.searchNevra(name=n, arch=a, ver=v, rel=r, epoch=e)
        if po:
            return True
        else:
            return False

    def _is_valid_downgrade(self, po, down_po):
        '''
        Check if down_po is a valid downgrade to po
        @param po:
        @param down_po:
        '''
        valid = True
        if not po.verGT(down_po):   # po must be > down_po
            valid = False
        elif canCoinstall(po.arch, down_po.arch): # po must not be coinstallable with down_po
            valid = False
        elif self.yumbase.allowedMultipleInstalls(po): # po must not be a multiple installable (ex. kernels )
            valid = False
        return valid

    def _limit_package_list(self, pkgs, skip_old=False):
        '''
        Limit a list of packages so we dont get the one twice
        optional remove packages with a smaller version than the installed one

        :param pkgs:    packages to process
        :type pkgs:    list of yum package objects
        :param skip_old: skip older packages (default = False)
        :type skip_old: boolean
        '''
        good_pkgs = set()
        good_tups = {}
        for po in pkgs:
            valid = True
            if po.pkgtup in good_tups: # dont process the same po twice
                continue
            elif self.yumbase.rpmdb.contains(po=po): # if the po is installed, then return the installed po
                (n, a, e, v, r) = po.pkgtup
                po = self.yumbase.rpmdb.searchNevra(name=n, arch=a, ver=v, rel=r, epoch=e)[0]
                self.logger.info("%s is installed " % str(po))
            elif skip_old:
                ipkgs = self.yumbase.rpmdb.searchNevra(name=po.name)
                if ipkgs:
                    ipkg = ipkgs[0]
                    if ipkg.verGT(po) and not self.yumbase.allowedMultipleInstalls(po): # inst > po
                        valid = False
            if valid:
                good_pkgs.add(po)
                good_tups[po.pkgtup] = 1
        return good_pkgs

    @property
    def update_metadata(self):
        if not self._updateMetadata:
            self._updateMetadata = UpdateMetadata(self.yumbase.repos.listEnabled())
        return self._updateMetadata
    
    def _limit_package_list(self, pkgs, skip_old=True):
        good_pkgs = set()
        good_tups = {}
        for po in pkgs:
            valid = True
            if po.pkgtup in good_tups: # dont process the same po twice
                continue
            if skip_old:
                ipkgs = self.yumbase.rpmdb.searchNevra(name=po.name)
                if ipkgs:
                    ipkg = ipkgs[0]
                    if ipkg.verGT(po) and not self.yumbase.allowedMultipleInstalls(po): # inst > po
                        valid = False
            if valid:
                good_pkgs.add(po)
                good_tups[po.pkgtup] = 1
        return good_pkgs
    

    def _to_package_id_list(self, pkgs):
        '''
        return a sorted list of package ids from a list of packages
        if and po is installed, the installed po id will be returned
        :param pkgs:
        '''
        result = set()
        for po in sorted(pkgs):
            if self.yumbase.rpmdb.contains(po=po): # if the po is installed, then return the installed po
                (n, a, e, v, r) = po.pkgtup
                po = self.yumbase.rpmdb.searchNevra(name=n, arch=a, ver=v, rel=r, epoch=e)[0]
            result.add(self._get_id(po))
        return result

    def _get_po(self,id):
        ''' find the real package from an package id'''
        n, e, v, r, a, repo_id = id.split(',')
        if repo_id == 'installed' or repo_id.startswith('@'):
            pkgs = self.yumbase.rpmdb.searchNevra(n, e, v, r, a)
        else:
            repo = self.yumbase.repos.getRepo(repo_id) # Used the repo sack, it will be faster
            if repo:
                pkgs = repo.sack.searchNevra(n, e, v, r, a)
            else: # fallback to the use the pkgSack, just in case
                pkgs = self.pkgSack.searchNevra(n, e, v, r, a)
        if pkgs:
            return pkgs[0]
        else:
            return None

    def _get_id(self,pkg):
        '''
        convert a yum package obejct to an id string containing (n,e,v,r,a,repo)
        :param pkg:
        '''
        values = [pkg.name, pkg.epoch, pkg.ver, pkg.rel, pkg.arch, pkg.ui_from_repo]
        return ",".join(values)


    def _get_updates(self):
        if not self._updates_list:
            ygh = self.yumbase.doPackageLists(pkgnarrow='updates')
            self._updates_list = ygh.updates
        return self._updates_list

    def _get_obsoletes(self):
        if not self._obsoletes_list:
            ygh = self.yumbase.doPackageLists(pkgnarrow='obsoletes')
            self._obsoletes_list = ygh.obsoletes
        return self._obsoletes_list

    def _get_action(self, po):
        '''
        Return the available action for a given pkg_id
        The action is what can be performed on the package
        an installed package will return as 'remove' as action
        an available update will return 'update'
        an available package will return 'install'
        :param po: yum package
        :type po: yum package object
        :return: action (remove, install, update, downgrade, obsolete)
        :rtype: string
        '''
        updates = self._get_updates()
        obsoletes = self._get_obsoletes()
        action = 'install'
        if self.yumbase.rpmdb.contains(po=po): # if the best po is installed, then return the installed po
            (n, a, e, v, r) = po.pkgtup
            po = self.yumbase.rpmdb.searchNevra(name=n, arch=a, ver=v, rel=r, epoch=e)[0]
            action = 'remove'
        else:
            if po in updates:
                action = 'update'
            elif po in obsoletes:
                action = 'obsolete'
            else:
                # Check if po is and older version of a installed package
                ipkgs = self.yumbase.rpmdb.searchNevra(name=po.name)
                if ipkgs:
                    ipkg = ipkgs[0]
                    if ipkg.verGT(po) and not self.yumbase.allowedMultipleInstalls(po): # inst > po
                        action = 'downgrade'
        return action


    def _get_yumbase(self):
        '''
        Get a YumBase object to work with
        '''
        self._yumbase = yum.YumBase()
        # make yum silent
        self._yumbase.preconf.errorlevel=0
        self._yumbase.preconf.debuglevel=0
        self._yumbase.setCacheDir()
        # setup the download callback handler
        self._yumbase.repos.setProgressBar( DownloadCallback(self) )
        # Disable parallel down for this repo, we dont support it
        for repo in self._yumbase.repos.listEnabled():
            repo._async = False
        self.logger.debug(' --> YUM LOCKED: Lockfile = %s' % self._yumbase._lockfile)


    def _reset_yumbase(self):
        '''
        destroy the current YumBase object
        '''
        if self._yumbase:
            self._yumbase.close()
            self._yumbase.closeRpmDB()
            self._yumbase.doUnlock()
            self.logger.debug(' --> YUM UNLOCKED : Lockfile = %s' % self._yumbase._lockfile)
            del self._yumbase
            self._yumbase = None


    def _setup_watchdog(self):
        '''
        Setup the watchdog to run every second when idle
        '''
        gobject.timeout_add(1000, self._watchdog)

    def _watchdog(self):
        terminate = False
        if self._watchdog_disabled or self._is_working: # is working
            return True
        if not self._lock: # is locked
            if self._watchdog_count > self._timeout_idle:
                terminate = True
        else:
            if self._watchdog_count > self._timeout_locked:
                terminate = True
        if terminate: # shall we quit
            if self._can_quit:
                self._reset_yumbase()
                self.mainloop.quit()
        else:
            self._watchdog_count += 1
            self.logger.debug("Watchdog : %i" % self._watchdog_count )
            return True

# from yum output.py        
    def _group_names2aipkgs(self, pkg_names):
        """ Convert pkg_names to installed pkgs or available pkgs, return
            value is a dict on pkg.name returning (apkg, ipkg). """
        ipkgs = self.yumbase.rpmdb.searchNames(pkg_names)
        apkgs = self.yumbase.pkgSack.searchNames(pkg_names)
        apkgs = packagesNewestByNameArch(apkgs)

        # This is somewhat similar to doPackageLists()
        pkgs = {}
        for pkg in ipkgs:
            pkgs[(pkg.name, pkg.arch)] = (None, pkg)
        for pkg in apkgs:
            key = (pkg.name, pkg.arch)
            if key not in pkgs:
                pkgs[(pkg.name, pkg.arch)] = (pkg, None)
            elif pkg.verGT(pkgs[key][1]):
                pkgs[(pkg.name, pkg.arch)] = (pkg, pkgs[key][1])

        # Convert (pkg.name, pkg.arch) to pkg.name dict
        ret = {}
        for (apkg, ipkg) in pkgs.itervalues():
            pkg = apkg or ipkg
            ret.setdefault(pkg.name, []).append((apkg, ipkg))
        return ret
        

def doTextLoggerSetup(logroot='yumdaemon', logfmt='%(asctime)s: %(message)s', loglvl=logging.INFO):
    ''' Setup Python logging  '''
    logger = logging.getLogger(logroot)
    logger.setLevel(loglvl)
    formatter = logging.Formatter(logfmt, "%H:%M:%S")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.propagate = False
    logger.addHandler(handler)
