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
import json
import logging
import yum
import yum.Errors as Errors
from yum.callbacks import *
from yum.constants import *
from yum.packageSack import packagesNewestByName
from yum.Errors import *

import argparse

from common import YumDaemonBase, doTextLoggerSetup, Logger, DownloadCallback, FAKE_ATTR, NONE

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


logger = logging.getLogger('yumdaemon.session')

#------------------------------------------------------------------------------ Main class
class YumDaemon(YumDaemonBase):

    def __init__(self, mainloop):
        YumDaemonBase.__init__(self,  mainloop)
        self.logger = logging.getLogger('yumdaemon-session')
        bus_name = dbus.service.BusName(DAEMON_ORG, bus = dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, '/')

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
                                          in_signature='as',
                                          out_signature='',
                                          sender_keyword='sender')

    def SetEnabledRepos(self, repo_ids, sender=None):
        '''
        Enabled a list of repositories, disabled all other repos
        :param repo_ids: list of repo ids to enable
        :param sender:
        '''
        self.working_start(sender)
        self._get_yumbase(repo_ids) # we need a new instance of YumBase, with the selected repos
        return self.working_ended()


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
            pkgs = self._limit_package_list(pkgs)    
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
                                          in_signature='asasbbb',
                                          out_signature='as',
                                          sender_keyword='sender')
    def Search(self, fields, keys, match_all, newest_only, tags, sender=None ):
        '''
        Search for for packages, where given fields contain given key words
        :param fields: list of fields to search in
        :param keys: list of keywords to search for
        :param match_all: match all flag, if True return only packages matching all keys
        :param newest_only: return only the newest version of a package
        :param tags: seach pkgtags
        '''
        self.working_start(sender)
        result = []
        for found in self.yumbase.searchGenerator(fields, keys, keys=True, searchtags=tags):
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

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='ss',
                                          out_signature='as',
                                          sender_keyword='sender')
    def GetGroupPackages(self, grp_id, grp_flt, sender=None ):
        '''
        Get packages in a group by grp_id and grp_flt
        :param grp_id: The Group id
        :param grp_flt: Group Filter (all or default)
        :param sender:
        '''
        self.working_start(sender)
        pkg_ids = self._get_group_pkgs(grp_id, grp_flt)
        return self.working_ended(pkg_ids)



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
    
    def check_lock(self, sender):
        '''
        Check that the current sender is owning the yum lock
        :param sender:
        '''
        if self._lock == sender:
            return True
        else:
            raise YumLockedError('Yum is locked by another application')
    

    def _get_yumbase(self, repos = []):
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
        if repos:
            self._enable_repos_from_list(repos)                    
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


def main():
    parser = argparse.ArgumentParser(description='Yum D-Bus Session Daemon')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('--notimeout', action='store_true')
    args = parser.parse_args()
    if args.verbose:
        if args.debug:
            doTextLoggerSetup(logroot='yumdaemon',loglvl=logging.DEBUG)
        else:
            doTextLoggerSetup(logroot='yumdaemon')

    # setup the DBus mainloop
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    mainloop = gobject.MainLoop()
    yd = YumDaemon(mainloop)
    if not args.notimeout:
        yd._setup_watchdog()
    mainloop.run()

if __name__ == '__main__':
    main()
