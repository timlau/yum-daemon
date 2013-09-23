#!/usr/bin/python -tt
#coding: utf-8
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
# (C) 2011 - Tim Lauridsen <timlau@fedoraproject.org>


#
# Yum session bus dBus service (Readonly)
#

import dbus
import dbus.service
import dbus.glib
import gobject
import os
import subprocess
import json
import logging
from datetime import datetime
import yum
import yum.Errors as Errors
from urlgrabber.progress import format_number
from yum.callbacks import *
from yum.rpmtrans import RPMBaseCallback
from yum.constants import *
from yum.update_md import UpdateMetadata
from yum.packageSack import packagesNewestByName
from yum.Errors import *

from rpmUtils.arch import canCoinstall

import argparse

version = 100 # must be integer
DAEMON_ORG = 'org.baseurl.YumSession'
DAEMON_INTERFACE = DAEMON_ORG
FAKE_ATTR = ['downgrades','action','pkgtags']
NONE = json.dumps(None)

def _(msg):
    return msg

#------------------------------------------------------------------------------ DBus Exception
class AccessDeniedError(dbus.DBusException):
    _dbus_error_name = DAEMON_ORG+'.AccessDeniedError'

class YumLockedError(dbus.DBusException):
    _dbus_error_name = DAEMON_ORG+'.YumLockedError'

class YumNotImplementedError(dbus.DBusException):
    _dbus_error_name = DAEMON_ORG+'.YumNotImplementedError'

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

           
logger = logging.getLogger('yumdaemon-session')
           
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

#------------------------------------------------------------------------------ Main class
class YumDaemon(dbus.service.Object, DownloadBaseCallback):

    def __init__(self, mainloop):
        DownloadBaseCallback.__init__(self)
        self.logger = logging.getLogger('yumdaemon-session')
        self.mainloop = mainloop # use to terminate mainloop
        self.authorized_sender = set()
        self._lock = None
        bus_name = dbus.service.BusName(DAEMON_ORG, bus = dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, '/')
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
# DBus Methods
#===============================================================================

    @Logger
    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='', 
                                          out_signature='i')
    def GetVersion(self):
        '''
        Get the daemon version
        '''
        return version

    @Logger
    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='', 
                                          out_signature='b',
                                          sender_keyword='sender')
    def Exit(self, sender=None):
        '''
        Exit the daemon
        :param sender:
        '''
        if self._can_quit:
            self._reset_yumbase()            
            self.mainloop.quit()
            return True
        else:
            return False

    @Logger
    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='', 
                                          out_signature='b',
                                          sender_keyword='sender')
    def Lock(self, sender=None):
        '''
        Get the yum lock
        :param sender:
        '''
        if not self._lock:
            self._lock = sender
            self.logger.info('LOCK: Locked by : %s' % sender)
            return True
        return False

    @Logger
    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='b', 
                                          out_signature='b',
                                          sender_keyword='sender')

    def SetWatchdogState(self,state, sender=None):
        '''
        Set the Watchdog state 
        :param state: True = Watchdog active, False = Watchdog disabled
        :type state: boolean (b)
        '''
        self._watchdog_disabled = not state
        return state


    @Logger
    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='s', 
                                          out_signature='as',
                                          sender_keyword='sender')

    def GetRepositories(self, filter, sender=None):
        '''
        Get the value a list of repo ids
        :param filter: filter to limit the listed repositories
        :param sender:
        '''
        self.working_start(sender)
        repos = []
        repos = self.yumbase.repos
        if filter == '' or filter == 'enabled':
            repos = [repo.id for repo in repos.listEnabled()]
        else:
            repos = [repo.id for repo in repos.findRepos(filter)]
        return self.working_ended(repos)
            
        
    @Logger
    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='s', 
                                          out_signature='s',
                                          sender_keyword='sender')
    def GetConfig(self, setting ,sender=None):
        '''
        Get the value of a yum config setting
        it will return a JSON string of the config
        :param setting: name of setting (debuglevel etc..)
        :param sender:
        '''
        self.working_start(sender)
        if setting == '*': # Return all config
            cfg = self.yumbase.conf
            all_conf = dict([(c,getattr(cfg,c)) for c in cfg.iterkeys()])
            value =  json.dumps(all_conf)            
        elif hasattr(self.yumbase.conf, setting):
            value = json.dumps(getattr(self.yumbase.conf, setting))
        else:
            value = json.dumps(None)
        return self.working_ended(value)
        
    @Logger
    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='s', 
                                          out_signature='s',
                                          sender_keyword='sender')
    def GetRepo(self, repo_id ,sender=None):
        '''
        Get information about a give repo_id
        the repo setting will be returned as dictionary in JSON format
        :param repo_id:
        :param sender:
        '''
        self.working_start(sender)
        try:
            repo = self.yumbase.repos.getRepo(repo_id)
            repo_conf = dict([(c,getattr(repo,c)) for c in repo.iterkeys()])
            value = json.dumps(repo_conf)            
        except Errors.RepoError:
            value = json.dumps(None)
        return self.working_ended(value)

    @Logger
    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='s', 
                                          out_signature='as',
                                          sender_keyword='sender')
    def GetPackages(self, pkg_filter, sender=None):
        '''
        Get a list of package ids, based on a package pkg_filterer
        :param pkg_filter: pkg pkg_filter string ('installed','updates' etc)
        :param sender:
        '''
        self.working_start(sender)
        if pkg_filter in ['installed','available','updates','obsoletes','recent','extras']:
            yh = self.yumbase.doPackageLists(pkgnarrow=pkg_filter)
            pkgs = getattr(yh,pkg_filter)
            value = self._to_package_id_list(pkgs)
        else:
            value = []
        return self.working_ended(value)

    @Logger
    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='sas', 
                                          out_signature='s',
                                          sender_keyword='sender')
    def GetPackageWithAttributes(self, pkg_filter, fields, sender=None):
        '''
        Get a list of package ids, based on a package pkg_filterer
        :param pkg_filter: pkg pkg_filter string ('installed','updates' etc)
        :param sender:
        '''
        self.working_start(sender)
        value = []
        if pkg_filter in ['installed','available','updates','obsoletes','recent','extras']:
            yh = self.yumbase.doPackageLists(pkgnarrow=pkg_filter)
            pkgs = getattr(yh,pkg_filter)
            value = [self._get_po_list(po,fields) for po in pkgs]
            return self.working_ended(json.dumps(value))
        
    @Logger
    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='sb', 
                                          out_signature='as',
                                          sender_keyword='sender')
    def GetPackagesByName(self, name, newest_only, sender=None):
        '''
        Get a list of packages from a name pattern
        :param name: name pattern
        :param newest_only: True = get newest packages only
        :param sender:
        '''
        self.working_start(sender)
        try:
            if newest_only:
                pkgs = self.yumbase.pkgSack.returnNewestByName(patterns=[name], ignore_case=False)
            else:
                pkgs = self.yumbase.pkgSack.returnPackages(patterns=[name], ignore_case=False)
            value = self._to_package_id_list(pkgs) 
        except PackageSackError,e:
            value = []
        return self.working_ended(value)
        
        
    @Logger
    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='ss', 
                                          out_signature='s',
                                          sender_keyword='sender')
    def GetAttribute(self, id, attr,sender=None):
        '''
        Get an attribute from a yum package id
        it will return a python repr string of the attribute
        :param id: yum package id
        :param attr: name of attribute (summary, size, description, changelog etc..)
        :param sender:
        '''
        self.working_start(sender)
        po = self._get_po(id)
        if po:
            if attr in FAKE_ATTR: # is this a fake attr:
                value = json.dumps(self._get_fake_attributes(po, attr))
            elif hasattr(po, attr):
                value = json.dumps(getattr(po,attr))
            else:
                value = json.dumps(None)
        else:
            value = json.dumps(None)        
        return self.working_ended(value)
            
    @Logger
    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='s', 
                                          out_signature='s',
                                          sender_keyword='sender')
    def GetUpdateInfo(self, id,sender=None):
        '''
        Get an Update Infomation e from a yum package id
        it will return a python repr string of the attribute
        :param id: yum package id
        :param sender:
        '''
        self.working_start(sender)
        po = self._get_po(id)
        if po:
            md = self.update_metadata
            notices = md.get_notices(po.name)
            result = []
            for notice in notices:
                result.append(notice._md)
            value = json.dumps(result)
        else:
            value = json.dumps(None)        
        return self.working_ended(value)
    
    @Logger
    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='', 
                                          out_signature='b',
                                          sender_keyword='sender')
    def Unlock(self, sender=None):
        ''' release the lock'''
        if self.check_lock(sender):
            self._reset_yumbase()
            self.logger.info('UNLOCK: Lock Release by %s' % self._lock)
            self._lock = None
            return True

    @Logger
    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='asasbb', 
                                          out_signature='as',
                                          sender_keyword='sender')
    def Search(self, fields, keys, match_all, newest_only, sender=None ):
        '''
        Search for for packages, where given fields contain given key words
        :param fields: list of fields to search in
        :param keys: list of keywords to search for
        :param match_all: match all flag, if True return only packages matching all keys
        :param newest_only: return only the newest version of a package
        '''
        self.working_start(sender)
        result = []
        for found in self.yumbase.searchGenerator(fields, keys, keys=True): 
            pkg = found[0]
            fkeys = found[1]
            if match_all and not len(fkeys) == len(keys): # skip the result if not all keys matches
                continue
            result.append(pkg)
        pkgs = self._limit_package_list(result, skip_old=not match_all) # remove dupes and optional old ones
        if newest_only:
            pkgs = packagesNewestByName(pkgs)
        result = [self._get_id(pkg) for pkg in pkgs]
        return self.working_ended(result)

    @Logger
    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='', 
                                          out_signature='s',
                                          sender_keyword='sender')
    def GetGroups(self, sender=None ):
        '''
        Return a category/group tree
        '''
        self.working_start(sender)
        value = self._get_groups()
        return self.working_ended(value)




#
#  Template for new method
#
#    @dbus.service.method(DAEMON_INTERFACE, 
#                                          in_signature='', 
#                                          out_signature='',
#                                          sender_keyword='sender')
#    def NewMethod(self, sender=None ):
#        '''
#        
#        '''
#        self.working_start(sender)
#        value = True
#        return self.working_ended(value)
#

        
#===============================================================================
# DBus signals
#===============================================================================
    @dbus.service.signal(DAEMON_INTERFACE)
    def UpdateProgress(self,name,frac,fread,ftime):
        '''
        DBus signal with download progress information
        will send dbus signals with download progress information
        :param name: filename
        :param frac: Progress fracment (0 -> 1)
        :param fread: formated string containing BytesRead
        :param ftime : formated string containing remaining or elapsed time
        '''
        pass

#===============================================================================
# Helper methods
#===============================================================================
    def working_start(self,sender):
        self.check_lock(sender)        
        self._is_working = True
        self._watchdog_count = 0

    def working_ended(self, value=None):
        self._is_working = False
        return value
    
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
        '''
        all_groups = []
        try:
            cats = self.yumbase.comps.get_categories()
            for category in cats:
                cat = (category.categoryid, category.ui_name, category.ui_description)
                cat_grps = []
                grps = [self.yumbase.comps.return_group(g) for g in category.groups if self.yumbase.comps.has_group(g)]
                for grp in grps:
                    elem = (grp.groupid, grp.ui_name, grp.ui_description, grp.installed)
                    cat_grps.append(elem)
                cat_grps.sort()
                all_groups.append((cat, cat_grps))
        except Errors.GroupsError, e:
            print str(e)
        all_groups.sort()
        return json.dumps(all_groups)
    
    def _get_history_by_days(self, start, end):
        '''
        Get the yum history transaction member located in a date interval from today
        :param start: start days from today
        :param end: end days from today
        '''
        now = datetime.now()
        history = self.yumbase.history.old()
        i = 0
        result = []
        while i < len(history):
            ht = history[i]
            i += 1
            tm = datetime.fromtimestamp(ht.end_timestamp)
            delta = now-tm
            if delta.days < start: # before start days
                continue
            elif delta.days > end: # after end days
                break
            result.append(ht)
        return self._get_id_time_list(result)

    def _history_search(self, pattern):
        '''
        search in yum history
        :param pattern: list of search patterns
        :type pattern: list
        '''
        tids = self.yumbase.history.search(pattern)
        result = self.yumbase.history.old(tids)
        return self._get_id_time_list(result)

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

    def check_lock(self, sender):
        '''
        Check that the current sender is owning the yum lock
        :param sender:
        '''
        if self._lock == sender:
            return True
        else:
            raise YumLockedError('Yum is locked by another application')


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
        
def doTextLoggerSetup(logroot='yumdaemon-session', logfmt='%(asctime)s: %(message)s', loglvl=logging.INFO):
    ''' Setup Python logging  '''
    logger = logging.getLogger(logroot)
    logger.setLevel(loglvl)
    formatter = logging.Formatter(logfmt, "%H:%M:%S")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.propagate = False
    logger.addHandler(handler)
        

def main():
    parser = argparse.ArgumentParser(description='Yum D-Bus Session Daemon')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('--notimeout', action='store_true')
    args = parser.parse_args()
    if args.verbose:
        if args.debug:
            doTextLoggerSetup(loglvl=logging.DEBUG)
        else:
            doTextLoggerSetup()
    
    # setup the DBus mainloop
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    mainloop = gobject.MainLoop()
    yd = YumDaemon(mainloop)
    if not args.notimeout:
        yd._setup_watchdog()
    mainloop.run()

if __name__ == '__main__':
    main()
