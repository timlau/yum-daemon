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
# (C) 2013 - Tim Lauridsen <timlau@fedoraproject.org>

import dbus
import dbus.service
import dbus.glib
import gobject
import json
import logging
from datetime import datetime
import yum
import yum.Errors as Errors
from urlgrabber.progress import format_number
from yum.callbacks import *
from yum.rpmtrans import RPMBaseCallback
from yum.constants import *
from yum.packageSack import packagesNewestByName
from yum.Errors import *

import argparse

from common import YumDaemonBase, doTextLoggerSetup, Logger, DownloadCallback, NONE, FAKE_ATTR

version = 902 #  (00.09.02) must be integer
DAEMON_ORG = 'org.baseurl.YumSystem'
DAEMON_INTERFACE = DAEMON_ORG

def _(msg):
    return msg

#------------------------------------------------------------------------------ DBus Exception
class AccessDeniedError(dbus.DBusException):
    _dbus_error_name = DAEMON_ORG+'.AccessDeniedError'

class YumLockedError(dbus.DBusException):
    _dbus_error_name = DAEMON_ORG+'.YumLockedError'

class YumTransactionError(dbus.DBusException):
    _dbus_error_name = DAEMON_ORG+'.YumTransactionError'

class YumNotImplementedError(dbus.DBusException):
    _dbus_error_name = DAEMON_ORG+'.YumNotImplementedError'

#------------------------------------------------------------------------------ Callback handlers

class ProcessTransCallback:
    STATES = { PT_DOWNLOAD      : "download",
               PT_DOWNLOAD_PKGS : "pkg-to-download",
               PT_GPGCHECK      : "signature-check",
               PT_TEST_TRANS    : "run-test-transaction",
               PT_TRANSACTION   : "run-transaction"}

    def __init__(self, base):
        self.base = base

    def event(self,state,data=NONE):
        if state in ProcessTransCallback.STATES:
            if data != NONE:
                data = [self.base._get_id(po) for po in data]
            self.base.TransactionEvent(ProcessTransCallback.STATES[state], data)

class RPMCallback(RPMBaseCallback):
    '''
    RPMTransaction display callback class
    '''
    ACTIONS = { TS_UPDATE : 'update',
                TS_ERASE: 'erase',
                TS_INSTALL: 'install',
                TS_TRUEINSTALL : 'install',
                TS_OBSOLETED: 'obsolete',
                TS_OBSOLETING: 'install',
                TS_UPDATED: 'cleanup',
                'repackaging': 'repackage'}

    def __init__(self, base):
        RPMBaseCallback.__init__(self)
        self.base = base

    def event(self, package, action, te_current, te_total, ts_current, ts_total):
        """
        :param package: A yum package object or simple string of a package name
        :param action: A yum.constant transaction set state or in the obscure
                       rpm repackage case it could be the string 'repackaging'
        :param te_current: Current number of bytes processed in the transaction
                           element being processed
        :param te_total: Total number of bytes in the transaction element being
                         processed
        :param ts_current: number of processes completed in whole transaction
        :param ts_total: total number of processes in the transaction.
        """
        if not isinstance(package, str): # package can be both str or yum package object
            id = self.base._get_id(package)
        else:
            id = package
        if action in RPMCallback.ACTIONS:
            action = RPMCallback.ACTIONS[action]
        self.base.RPMProgress(id, action, te_current, te_total, ts_current, ts_total)

    def scriptout(self, package, msgs):
        """package is the package.  msgs is the messages that were
        output (if any)."""
        pass
    
    
class DaemonYumBase(yum.YumBase):
    
    def __init__(self, daemon):
        yum.YumBase.__init__(self)
        self._daemon = daemon    
        
    def _checkSignatures(self,pkgs,callback):
        ''' The the signatures of the downloaded packages '''
        for po in pkgs:
            result, errmsg = self.sigCheckPkg(po)
            if result == 0:
                # Verified ok, or verify not req'd
                continue            
            elif result == 1:
                self.getKeyForPackage(po, fullaskcb=self._daemon.handle_gpg_import)
            else:
                raise Errors.YumGPGCheckError, errmsg
    
        return 0        
    

logger = logging.getLogger('yumdaemon')

#------------------------------------------------------------------------------ Main class
class YumDaemon(YumDaemonBase):

    def __init__(self, mainloop):
        YumDaemonBase.__init__(self,  mainloop)
        self.logger = logging.getLogger('yumdaemon.system')
        bus_name = dbus.service.BusName(DAEMON_ORG, bus = dbus.SystemBus())
        dbus.service.Object.__init__(self, bus_name, '/')
        self._gpg_confirm = {}

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
        self.check_permission(sender)
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
        self.check_permission(sender)
        if not self._lock:
            try:
                self.yumbase.doLock()
                self._lock = sender
                self.logger.info('LOCK: Locked by : %s' % sender)
                return True
            except Errors.LockError, e:
                raise YumLockedError(str(e))
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
        self.check_permission(sender)
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
        repos = self._get_repositories(filter)
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
        value = self._get_config(setting)
        return self.working_ended(value)

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='ss',
                                          out_signature='b',
                                          sender_keyword='sender')
    def SetConfig(self, setting, value ,sender=None):
        '''
        Set yum config setting for the running session
        :param setting: yum conf setting to set
        :param value: value to set
        :param sender:
        '''
        self.working_start(sender)
        rc = self._set_option(setting, json.loads(value))
        return self.working_ended(rc)

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
        value = self._get_repo(repo_id)
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
        value = self._get_packages(pkg_filter)
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
        value = self._get_package_with_attributes(pkg_filter, fields)
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
        pkg_ids = self._get_packages_by_name(name, newest_only)
        return self.working_ended(pkg_ids)


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
        value = self._get_attribute( id, attr)
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
        value = self._get_updateInfo(id)
        return self.working_ended(value)


    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='i',
                                          out_signature='s',
                                          sender_keyword='sender')
    def GetHistoryPackages(self, tid,sender=None):
        '''
        Get packages from a given yum history transaction id

        :param tid: history transaction id
        :type tid: integer
        :return: list of (pkg_id, state, installed) pairs
        :rtype: json encoded string
        '''
        self.working_start(sender)
        value = json.dumps(self._get_history_transaction_pkgs(tid))
        return self.working_ended(value)


    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='ii',
                                          out_signature='s',
                                          sender_keyword='sender')
    def GetHistoryByDays(self, start_days, end_days ,sender=None):
        '''
        Get History transaction in a interval of days from today

        :param start_days: start of interval in days from now (0 = today)
        :type start_days: integer
        :param end_days:end of interval in days from now
        :type end_days: integer
        :return: a list of (transaction is, date-time) pairs
        :type sender: json encoded string
        '''
        self.working_start(sender)
        value = json.dumps(self._get_history_by_days(start_days, end_days))
        return self.working_ended(value)

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='as',
                                          out_signature='s',
                                          sender_keyword='sender')
    def HistorySearch(self, pattern ,sender=None):
        '''
        Search the history for transaction matching a pattern
        :param pattern: patterne to match
        :type pattern: string
        :return: list of (tid,isodates)
        :type sender: json encoded string
        '''
        self.working_start(sender)
        value = json.dumps(self._history_search(pattern))
        return self.working_ended(value)


    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='',
                                          out_signature='b',
                                          sender_keyword='sender')
    def Unlock(self, sender=None):
        ''' release the lock'''
        self.check_permission(sender)
        if self.check_lock(sender):
            self._reset_yumbase()
            self.logger.info('UNLOCK: Lock Release by %s' % self._lock)
            self._lock = None
            return True

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='s',
                                          out_signature='s',
                                          sender_keyword='sender')
    def Install(self, cmds, sender=None):
        '''
        Install packages based on command patterns separated by spaces
        sinulate what 'yum install <arguments>' does
        :param cmds: command patterns separated by spaces
        :param sender:
        '''
        self.working_start(sender)
        for cmd in cmds.split(' '):
            if cmd.endswith('.rpm'):
                self.yumbase.installLocal(cmd)
            else:        
                self.yumbase.install(pattern=cmd)
        value = self._build_transaction()
        return self.working_ended(value)

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='s',
                                          out_signature='s',
                                          sender_keyword='sender')
    def Remove(self, cmds, sender=None):
        '''
        Remove packages based on command patterns separated by spaces
        sinulate what 'yum remove <arguments>' does
        :param cmds: command patterns separated by spaces
        :param sender:
        '''
        self.working_start(sender)
        for cmd in cmds.split(' '):
            self.yumbase.remove(pattern=cmd)
        value = self._build_transaction()
        return self.working_ended(value)

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='s',
                                          out_signature='s',
                                          sender_keyword='sender')
    def Update(self, cmds, sender=None):
        '''
        Update packages based on command patterns separated by spaces
        sinulate what 'yum update <arguments>' does
        :param cmds: command patterns separated by spaces
        :param sender:
        '''
        self.working_start(sender)
        if cmds == "":
            txmbrs = self.yumbase.update()
            self.logger.debug([str(txmbr.po) for txmbr in txmbrs])
        else:
            for cmd in cmds.split(' '):
                self.yumbase.update(pattern=cmd)
        value = self._build_transaction()
        return self.working_ended(value)

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='s',
                                          out_signature='s',
                                          sender_keyword='sender')
    def Reinstall(self, cmds, sender=None):
        '''
        Reinstall packages based on command patterns separated by spaces
        sinulate what 'yum reinstall <arguments>' does
        :param cmds: command patterns separated by spaces
        :param sender:
        '''
        self.working_start(sender)
        for cmd in cmds.split(' '):
            self.yumbase.reinstall(pattern=cmd)
        value = self._build_transaction()
        return self.working_ended(value)

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='s',
                                          out_signature='s',
                                          sender_keyword='sender')
    def Downgrade(self, cmds, sender=None):
        '''
        Downgrade packages based on command patterns separated by spaces
        sinulate what 'yum downgrade <arguments>' does
        :param cmds: command patterns separated by spaces
        :param sender:
        '''
        self.working_start(sender)
        for cmd in cmds.split(' '):
            self.yumbase.downgrade(pattern=cmd)
        value = self._build_transaction()
        return self.working_ended(value)


    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='ss',
                                          out_signature='as',
                                          sender_keyword='sender')

    def AddTransaction(self, id, action, sender=None):
        '''
        Add an package to the current transaction

        :param id: package id for the package to add
        :param action: the action to perform ( install, update, remove, obsolete, reinstall, downgrade, localinstall )
        '''
        self.working_start(sender)
        if action != 'localinstall': # Dont get a po if it is at local package
            po = self._get_po(id)
            logger.debug("Add: %s " % str(po))
        txmbrs = []
        if action == "install":
            txmbrs = self.yumbase.install(po)
        elif action == "update" or action == "obsolete":
            txmbrs = self.yumbase.update(po)
        elif action == "remove":
            txmbrs = self.yumbase.remove(po)
        elif action == "reinstall":
            txmbrs = self.yumbase.reinstall(po)
        elif action == "downgrade":
            txmbrs = self.yumbase.downgrade(po)
        elif action == "localinstall":
            txmbrs = self.yumbase.installLocal(id)
        value = self._to_transaction_id_list(txmbrs)
        return self.working_ended(value)

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='',
                                          out_signature='',
                                          sender_keyword='sender')
    def ClearTransaction(self, sender):
        '''
        Clear the transactopm
        '''
        self.working_start(sender)
        # Reset the transaction
        self.yumbase._tsInfo = None
        return self.working_ended()


    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='',
                                          out_signature='as',
                                          sender_keyword='sender')

    def GetTransaction(self, sender=None):
        '''
        Return the members of the current transaction
        '''
        self.working_start(sender)
        txmbrs = self.yumbase.tsInfo
        value = self._to_transaction_id_list(txmbrs)
        return self.working_ended(value)


    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='',
                                          out_signature='s',
                                          sender_keyword='sender')
    def BuildTransaction(self, sender):
        '''
        Resolve dependencies of current transaction
        '''
        self.working_start(sender)
        value = self._build_transaction()
        return self.working_ended(value)


    def _build_transaction(self):
        '''
        Resolve dependencies of current transaction
        '''
        self.TransactionEvent('start-build',NONE)
        rc, msgs = self.yumbase.buildTransaction()
        if rc == 2: # OK
            output = self._get_transaction_list()
        else:
            output = msgs
        self.TransactionEvent('end-build',NONE)
        return json.dumps((rc,output))

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='',
                                          out_signature='i',
                                          sender_keyword='sender')
    def RunTransaction(self, sender = None):
        '''
        Run the current yum transaction
        '''
        self.working_start(sender)
        self.check_permission(sender)
        self.check_lock(sender)
        try:
            self.TransactionEvent('start-run',NONE)
            self._can_quit = False
            callback = ProcessTransCallback(self)
            rpmDisplay = RPMCallback(self)
            result = self.yumbase.processTransaction(callback=callback, rpmDisplay=rpmDisplay)
            self._can_quit = True
            self._reset_yumbase()
            self.TransactionEvent('end-run',NONE)
            return self.working_ended(0)
        except Errors.YumGPGCheckError, errmsg: # GPG Key import needed
            return self.working_ended(1)       # return 1 to tell the client we need a ask the user for gpg import confirmation and run again           
        except Errors.YumBaseError, e:
            self._can_quit = True
            if str(e) == "Didn't install any keys": #FIXME: This is crap, find a better way
                return self.working_ended(1)       # return 1 to tell the client we need a ask the user for gpg import confirmation and run again
            self.TransactionEvent('fail',NONE)
            self._reset_yumbase()
            return self.working_ended(2)
            #raise YumTransactionError(str(e))

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
        result = self._search(fields, keys, match_all, newest_only, tags)
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

    @Logger
    @dbus.service.method(DAEMON_INTERFACE,
                                          in_signature='sb',
                                          out_signature='',
                                          sender_keyword='sender')
    def ConfirmGPGImport(self, hexkeyid, confirmed, sender=None ):
        '''
        Confirm import of at GPG Key by yum
        :param hexkeyid: hex keyid for GPG key
        :param confirmed: confirm import of key (True/False)
        :param sender:
        '''
        
        self.working_start(sender)
        self._gpg_confirm[hexkeyid] = confirmed # store confirmation of GPG import
        return self.working_ended()


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

    @dbus.service.signal(DAEMON_INTERFACE)
    def TransactionEvent(self,event,data):
        '''
        DBus signal with Transaction event information, telling the current step in the processing of
        the current transaction.
        
        Steps are : start-run, download, pkg-to-download, signature-check, run-test-transaction, run-transaction, fail, end-run
        
        :param event: current step 
        '''
        #print "event: %s" % event
        pass


    @dbus.service.signal(DAEMON_INTERFACE)
    def RPMProgress(self, package, action, te_current, te_total, ts_current, ts_total):
        """
        RPM Progress DBus signal
        :param package: A yum package object or simple string of a package name
        :param action: A yum.constant transaction set state or in the obscure
                       rpm repackage case it could be the string 'repackaging'
        :param te_current: Current number of bytes processed in the transaction
                           element being processed
        :param te_total: Total number of bytes in the transaction element being
                         processed
        :param ts_current: number of processes completed in whole transaction
        :param ts_total: total number of processes in the transaction.
        """
        pass


    @dbus.service.signal(DAEMON_INTERFACE)
    def GPGImport(self, pkg_id, userid, hexkeyid, keyurl, timestamp ):
        '''
        GPG Key Import DBus signal
        
        :param pkg_id: pkg_id for the package needing the GPG Key to be verified
        :param userid: GPG key name
        :param hexkeyid: GPG key hex id
        :param keyurl: Url to the GPG Key
        :param timestamp: 
        '''
        pass

#===============================================================================
# Helper methods
#===============================================================================
    def working_start(self,sender):
        self.check_permission(sender)
        self.check_lock(sender)
        self._is_working = True
        self._watchdog_count = 0

    def working_ended(self, value=None):
        self._is_working = False
        return value

    def handle_gpg_import(self, gpg_info):
        '''
        Callback for handling af user confirmation of gpg key import
        
        :param gpg_info: dict with info about gpg key {"po": ..,  "userid": .., "hexkeyid": .., "keyurl": ..,  "fingerprint": .., "timestamp": ..)
        
        '''
        print(gpg_info)
        pkg_id = self._get_id(gpg_info['po'])
        userid = gpg_info['userid']
        hexkeyid = gpg_info['hexkeyid']
        keyurl = gpg_info['keyurl']
        fingerprint = gpg_info['fingerprint']
        timestamp = gpg_info['timestamp']
        if not hexkeyid in self._gpg_confirm: # the gpg key has not been confirmed by the user
            self._gpg_confirm[hexkeyid] = False
            self.GPGImport( pkg_id, userid, hexkeyid, keyurl, timestamp )
        return self._gpg_confirm[hexkeyid]
    

    def _set_option(self, option, value):
        if hasattr(self.yumbase.conf, option):
            setattr(self.yumbase.conf, option, value)
            self.logger.debug(_("Setting Yum Option %s = %s") % (option, value))
            for repo in self.yumbase.repos.repos.values():
                if repo.isEnabled():
                    if hasattr(repo, option):
                        setattr(repo, option, value)
                        self.logger.debug("Setting Yum Option %s = %s (%s)" % (option, value, repo.id), __name__)
            return True
        else:
            return False


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

    def _get_transaction_list(self):
        '''
        Generate a list of the current transaction
        '''
        out_list = []
        sublist = []
        self.yumbase.tsInfo.makelists()
        for (action, pkglist) in [('install', self.yumbase.tsInfo.installed),
                            ('update', self.yumbase.tsInfo.updated),
                            ('remove', self.yumbase.tsInfo.removed),
                            ('install-deps', self.yumbase.tsInfo.depinstalled),
                            ('update-deps', self.yumbase.tsInfo.depupdated),
                            ('remove-deps', self.yumbase.tsInfo.depremoved)]:
            for txmbr in pkglist:
                (n, a, e, v, r) = txmbr.pkgtup
                evr = txmbr.po.printVer()
                repoid = txmbr.repoid
                pkgsize = float(txmbr.po.size)
                size = pkgsize
                alist = []
                for (obspo, relationship) in txmbr.relatedto:
                    if relationship == 'obsoletes':
                        alist.append(self._get_id(obspo))
                el = (self._get_id(txmbr.po), size, alist)
                sublist.append(el)
            if pkglist:
                out_list.append([action, sublist])
                sublist = []
        for (action, pkglist) in [('skipped',
                                   self.yumbase.skipped_packages), ]:
            lines = []
            for po in pkglist:
                (n, a, e, v, r) = po.pkgtup
                evr = po.printVer()
                repoid = po.repoid
                pkgsize = float(po.size)
                size = format_number(pkgsize)
                el = (self._get_id(po), size, alist)
                sublist.append(el)
            if pkglist:
                out_list.append([action, sublist])
                sublist = []

        return out_list

    def _to_transaction_id_list(self, txmbrs):
        '''
        return a sorted list of package ids from a list of packages
        if and po is installed, the installed po id will be returned
        :param pkgs:
        '''
        result = []
        for txmbr in txmbrs:
            po = txmbr.po
            result.append("%s,%s" % (self._get_id(po), txmbr.ts_state ))
        return result
    
    def check_lock(self, sender):
        '''
        Check that the current sender is owning the yum lock
        :param sender:
        '''
        if self._lock == sender:
            return True
        else:
            raise YumLockedError('Yum is locked by another application')
    

    def check_permission(self, sender):
        ''' Check for senders permission to run root stuff'''
        if sender in self.authorized_sender:
            return
        else:
            self._check_permission(sender)
            self.authorized_sender.add(sender)


    def _check_permission(self, sender):
        '''
        check senders permissions using PolicyKit1
        :param sender:
        '''
        if not sender: raise ValueError('sender == None')

        obj = dbus.SystemBus().get_object('org.freedesktop.PolicyKit1', '/org/freedesktop/PolicyKit1/Authority')
        obj = dbus.Interface(obj, 'org.freedesktop.PolicyKit1.Authority')
        (granted, _, details) = obj.CheckAuthorization(
                ('system-bus-name', {'name': sender}), DAEMON_ORG, {}, dbus.UInt32(1), '', timeout=600)
        if not granted:
            raise AccessDeniedError('Session is not authorized')

    def _get_yumbase(self, repos=[]):
        '''
        Get a YumBase object to work with
        '''
        self._yumbase = DaemonYumBase(self)
        # make yum silent
        self._yumbase.preconf.errorlevel=0
        self._yumbase.preconf.debuglevel=0
        #self._yumbase.doConfigSetup()
        # setup the download callback handler
        self._yumbase.repos.setProgressBar( DownloadCallback(self) )
        if repos:
            self._enable_repos_from_list(repos)            
        # Disable parallel down for this repo, we dont support it
        for repo in self._yumbase.repos.listEnabled():
            repo._async = False

        self._yumbase.doLock()
        self.logger.debug(' --> YUM LOCKED: Lockfile = %s' % self._yumbase._lockfile)
        ygh = self._yumbase.doPackageLists("updates") # make sure the basic stuff is up and running

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
    parser = argparse.ArgumentParser(description='Yum D-Bus Daemon')
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
