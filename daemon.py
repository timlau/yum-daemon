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

import dbus
import dbus.service
import dbus.glib
import gobject
import os
import subprocess
import json
import yum
import yum.Errors as Errors
from urlgrabber.progress import format_number
from yum.callbacks import *
from yum.rpmtrans import RPMBaseCallback
from yum.constants import *



version = 100 # must be integer
DAEMON_ORG = 'org.baseurl.Yum'
DAEMON_INTERFACE = DAEMON_ORG+'.Interface'

def _(msg):
    return msg

#------------------------------------------------------------------------------ DBus Exception
class AccessDeniedError(dbus.DBusException):
    _dbus_error_name = DAEMON_ORG+'.AccessDeniedError'

class YumLockedError(dbus.DBusException):
    _dbus_error_name = DAEMON_ORG+'.YumLockedError'

class YumTransactionError(dbus.DBusException):
    _dbus_error_name = DAEMON_ORG+'.YumTransactionError'

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
        @param name: filename
        @param frac: Progress fracment (0 -> 1)
        @param fread: formated string containing BytesRead
        @param ftime : formated string containing remaining or elapsed time
        '''
        # send a DBus signal with progress info
        self.base.UpdateProgress(name,frac,fread,ftime)

class ProcessTransCallback(ProcessTransBaseCallback):
    STATES = { PT_DOWNLOAD  : "download",
               PT_GPGCHECK    : "signature-check",
               PT_TEST_TRANS  : "run-test-transaction",
               PT_TRANSACTION : "run-transaction"}

    def __init__(self, base):
        ProcessTransBaseCallback.__init__(self)
        self.base = base
        
    def event(self,state,data=None):
        if state in ProcessTransCallback.STATES:
            ProcessTransBaseCallback.event(self,state,data)
            self.base.TransactionEvent(ProcessTransCallback.STATES[state])
            
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
        @param package: A yum package object or simple string of a package name
        @param action: A yum.constant transaction set state or in the obscure 
                       rpm repackage case it could be the string 'repackaging'
        @param te_current: Current number of bytes processed in the transaction
                           element being processed
        @param te_total: Total number of bytes in the transaction element being
                         processed
        @param ts_current: number of processes completed in whole transaction
        @param ts_total: total number of processes in the transaction.
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

            
            

#------------------------------------------------------------------------------ Main class
class YumDaemon(dbus.service.Object, DownloadBaseCallback):

    def __init__(self, mainloop):
        DownloadBaseCallback.__init__(self)
        self.mainloop = mainloop # use to terminate mainloop
        self.authorized_sender = set()
        self._lock = None
        bus_name = dbus.service.BusName(DAEMON_ORG, bus = dbus.SystemBus())
        dbus.service.Object.__init__(self, bus_name, '/')
        self._yumbase = None
        self._can_quit = True
        
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


    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='', 
                                          out_signature='i') 
    def GetVersion(self):
        '''
        Get the daemon version
        '''
        return version

    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='', 
                                          out_signature='b',
                                          sender_keyword='sender')
    def Exit(self, sender=None):
        '''
        Exit the daemon
        @param sender:
        '''
        self.check_permission(sender)
        if self._can_quit:
            self.mainloop.quit()
            return True
        else:
            return False

    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='', 
                                          out_signature='b',
                                          sender_keyword='sender')
    def Lock(self, sender=None):
        '''
        Get the yum lock
        @param sender:
        '''
        self.check_permission(sender)
        if not self._lock:
            try:
                self.yumbase.doLock()
                self._lock = sender
                print('Yum is locked by : %s' % sender)
                return True
            except Errors.LockError, e:
                raise YumLockedError(str(e))
        return False

    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='s', 
                                          out_signature='as',
                                          sender_keyword='sender')
    def GetRepositories(self, filter, sender=None):
        '''
        Get the value a list of repo ids
        @param filter: filter to limit the listed repositories
        @param sender:
        '''
        self.check_permission(sender)
        self.check_lock(sender)
        repos = []
        repos = self.yumbase.repos
        if filter == '' or filter == 'enabled':
            repos = [repo.id for repo in repos.listEnabled()]
        else:
            repos = [repo.id for repo in repos.findRepos(filter)]
        return repos    
            
        
    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='s', 
                                          out_signature='s',
                                          sender_keyword='sender')
    def GetConfig(self, setting ,sender=None):
        '''
        Get the value of a yum config setting
        it will return a JSON string of the config
        @param setting: name of setting (debuglevel etc..)
        @param sender:
        '''
        self.check_permission(sender)
        self.check_lock(sender)
        if setting == '*': # Return all config
            cfg = self.yumbase.conf
            all_conf = dict([(c,getattr(cfg,c)) for c in cfg.iterkeys()])
            return json.dumps(all_conf)            
        if hasattr(self.yumbase.conf, setting):
            value = json.dumps(getattr(self.yumbase.conf, setting))
            return value
        else:
            return json.dumps(None)

    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='s', 
                                          out_signature='s',
                                          sender_keyword='sender')
    def GetRepo(self, repo_id ,sender=None):
        '''
        Get information about a give repo_id
        the repo setting will be returned as dictionary in JSON format
        @param repo_id:
        @param sender:
        '''
        self.check_permission(sender)
        self.check_lock(sender)
        try:
            repo = self.yumbase.repos.getRepo(repo_id)
            repo_conf = dict([(c,getattr(repo,c)) for c in repo.iterkeys()])
            return json.dumps(repo_conf)            
        except Errors.RepoError:
            return json.dumps(None)

    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='s', 
                                          out_signature='as',
                                          sender_keyword='sender')
    def GetPackages(self, narrow, sender=None):
        '''
        Get a list of package ids, based on a package narrower
        @param narrow: pkg narrow string ('installed','updates' etc)
        @param sender:
        '''
        
        self.check_permission(sender)
        self.check_lock(sender)
        yh = self.yumbase.doPackageLists(pkgnarrow=narrow)
        pkgs = getattr(yh,narrow)
        return self._to_package_id_list(pkgs)
        
    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='sb', 
                                          out_signature='as',
                                          sender_keyword='sender')
    def GetPackagesByName(self, name, newest_only, sender=None):
        '''
        Get a list of packages from a name pattern
        @param name: name pattern
        @param newest_only: True = get newest packages only
        @param sender:
        '''
        self.check_permission(sender)
        self.check_lock(sender)
        if newest_only:
            pkgs = self.yumbase.pkgSack.returnNewestByName(patterns=[name], ignore_case=False)
        else:
            pkgs = self.yumbase.pkgSack.returnPackages(patterns=[name], ignore_case=False)
        return self._to_package_id_list(pkgs)
        
        
    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='ss', 
                                          out_signature='s',
                                          sender_keyword='sender')
    def GetAttribute(self, id, attr,sender=None):
        '''
        Get an attribute from a yum package id
        it will return a python repr string of the attribute
        @param id: yum package id
        @param attr: name of attribute (summary, size, description, changelog etc..)
        @param sender:
        '''
        self.check_permission(sender)
        self.check_lock(sender)
        po = self._get_po(id)
        if po:
            if hasattr(po, attr):
                value = json.dumps(getattr(po,attr))
                return value
            else:
                return ':none'
        else:
            return ':not_found'        
            
    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='', 
                                          out_signature='b',
                                          sender_keyword='sender')
    def Unlock(self, sender=None):
        ''' release the lock'''
        self.check_permission(sender)
        if self.check_lock(sender):
            self.yumbase.doUnlock()
            self._reset_yumbase()
            print('Yum lock by %s released' % self._lock)
            self._lock = None
            return True

    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='ss', 
                                          out_signature='as',
                                          sender_keyword='sender')

    def AddTransaction(self, id, action, sender=None):
        self.check_permission(sender)
        self.check_lock(sender)
        if action != 'localinstall': # Dont get a po if it is at local package
            po = self._get_po(id)
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
        return self._to_transaction_id_list(txmbrs)
    
    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='', 
                                          out_signature='s',
                                          sender_keyword='sender')
    def BuildTransaction(self, sender):
        '''
        Resolve dependencies of current transaction
        '''
        self.check_permission(sender)
        self.check_lock(sender)
        self.TransactionEvent('start-build')
        rc, msgs = self.yumbase.buildTransaction()
        if rc == 2: # OK
            output = self._get_transaction_list()
        else:
            output = msgs
        self.TransactionEvent('end-build')
        return json.dumps((rc,output))
    
    
    @dbus.service.method(DAEMON_INTERFACE, 
                                          in_signature='', 
                                          out_signature='',
                                          sender_keyword='sender')
    def RunTransaction(self, sender = None):
        '''
        Run the current yum transaction
        '''
        self.check_permission(sender)
        self.check_lock(sender)
        try:
            self.TransactionEvent('start-run')
            self._can_quit = False
            callback = ProcessTransCallback(self)
            rpmDisplay = RPMCallback(self)
            self.yumbase.processTransaction(callback=callback, rpmDisplay=rpmDisplay)
            self._can_quit = True
            self.TransactionEvent('end-run')
        except Errors.YumBaseError, e:
            self._can_quit = True            
            self.TransactionEvent('fail')
            raise YumTransactionError(str(e))
#===============================================================================
# DBus signals
#===============================================================================
    @dbus.service.signal(DAEMON_INTERFACE)
    def UpdateProgress(self,name,frac,fread,ftime):
        '''
        DBus signal with download progress information
        will send dbus signals with download progress information
        @param name: filename
        @param frac: Progress fracment (0 -> 1)
        @param fread: formated string containing BytesRead
        @param ftime : formated string containing remaining or elapsed time
        '''
        pass

    @dbus.service.signal(DAEMON_INTERFACE)
    def TransactionEvent(self,event):
        '''
        DBus signal with Transaction information        
        @param event:
        '''
        pass
    
    
    @dbus.service.signal(DAEMON_INTERFACE)
    def RPMProgress(self, package, action, te_current, te_total, ts_current, ts_total):
        """
        RPM Progress DBus signal
        @param package: A yum package object or simple string of a package name
        @param action: A yum.constant transaction set state or in the obscure 
                       rpm repackage case it could be the string 'repackaging'
        @param te_current: Current number of bytes processed in the transaction
                           element being processed
        @param te_total: Total number of bytes in the transaction element being
                         processed
        @param ts_current: number of processes completed in whole transaction
        @param ts_total: total number of processes in the transaction.
        """
        pass
    
#===============================================================================
# Helper methods
#===============================================================================
    def _get_transaction_list(self):
        ''' 
        Generate a list of the current transaction 
        '''
        out_list = []
        sublist = []
        self.yumbase.tsInfo.makelists()
        for (action, pkglist) in [(yum.i18n._('Installing'), self.yumbase.tsInfo.installed),
                            (_('Updating'), self.yumbase.tsInfo.updated),
                            (_('Removing'), self.yumbase.tsInfo.removed),
                            (_('Installing for dependencies'), self.yumbase.tsInfo.depinstalled),
                            (_('Updating for dependencies'), self.yumbase.tsInfo.depupdated),
                            (_('Removing for dependencies'), self.yumbase.tsInfo.depremoved)]:
            for txmbr in pkglist:
                (n, a, e, v, r) = txmbr.pkgtup
                evr = txmbr.po.printVer()
                repoid = txmbr.repoid
                pkgsize = float(txmbr.po.size)
                size = format_number(pkgsize)
                alist = []
                for (obspo, relationship) in txmbr.relatedto:
                    if relationship == 'obsoletes':
                        appended = _('     replacing  %s%s%s.%s %s\n\n')
                        appended %= ("", obspo.name, "",
                                     obspo.arch, obspo.printVer())
                        alist.append(appended)
                el = (n, a, evr, repoid, size, alist)
                sublist.append(el)
            if pkglist:
                out_list.append([action, sublist])
                sublist = []
        for (action, pkglist) in [(_('Skipped (dependency problems)'),
                                   self.yumbase.skipped_packages), ]:
            lines = []
            for po in pkglist:
                (n, a, e, v, r) = po.pkgtup
                evr = po.printVer()
                repoid = po.repoid
                pkgsize = float(po.size)
                size = format_number(pkgsize)
                el = (n, a, evr, repoid, size, alist)
                sublist.append(el)
            if pkglist:
                out_list.append([action, sublist])
                sublist = []

        return out_list

    def _to_transaction_id_list(self, txmbrs):
        '''
        return a sorted list of package ids from a list of packages
        if and po is installed, the installed po id will be returned
        @param pkgs:
        '''
        result = []
        for txmbr in txmbrs:
            po = txmbr.po
            result.append("%s,%s" % (self._get_id(po), txmbr.ts_state ))
        return result

    def _to_package_id_list(self, pkgs):
        '''
        return a sorted list of package ids from a list of packages
        if and po is installed, the installed po id will be returned
        @param pkgs:
        '''
        result = []
        for po in sorted(pkgs):
            if self.yumbase.rpmdb.contains(po=po): # if the po is installed, then return the installed po 
                (n, a, e, v, r) = po.pkgtup
                po = self.yumbase.rpmdb.searchNevra(name=n, arch=a, ver=v, rel=r, epoch=e)[0]
            result.append(self._get_id(po))
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
        @param pkg:
        '''
        values = [pkg.name, pkg.epoch, pkg.ver, pkg.rel, pkg.arch, pkg.ui_from_repo]
        return ",".join(values)

    def check_lock(self, sender):
        '''
        Check that the current sender is owning the yum lock
        @param sender:
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
        @param sender:
        '''
        if not sender: raise ValueError('sender == None')
        
        obj = dbus.SystemBus().get_object('org.freedesktop.PolicyKit1', '/org/freedesktop/PolicyKit1/Authority')
        obj = dbus.Interface(obj, 'org.freedesktop.PolicyKit1.Authority')
        (granted, _, details) = obj.CheckAuthorization(
                ('system-bus-name', {'name': sender}), DAEMON_ORG, {}, dbus.UInt32(1), '', timeout=600)
        if not granted:
            raise AccessDeniedError('Session is not authorized')

    
    def _get_yumbase(self):
        '''
        Get a YumBase object to work with
        '''
        self._yumbase = yum.YumBase()
        #self._yumbase.doConfigSetup()
        # setup the download callback handler
        self._yumbase.repos.setProgressBar( DownloadCallback(self) )
        
    def _reset_yumbase(self):
        '''
        destroy the current YumBase object
        '''
        del self._yumbase
        self._yumbase = None

def main():
    # setup the DBus mainloop
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    mainloop = gobject.MainLoop()
    YumDaemon(mainloop)
    mainloop.run()

if __name__ == '__main__':
    main()