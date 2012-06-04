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

"""
This is a Python 2.x client API for the yumdaemon Dbus Service

This module gives a simple pythonic interface to doing Yum package action using the 
yum-daemon Dbus service.

It uses synchronous call to the DBus service

Example::

    from yumdaemon2 import YumDaemonClient
    
    try:
        cli = YumDaemonClient()
        cli.Lock()
        pkgs = cli.GetPackagesByName('yum', newest_only=False) # get packages where names starts with yum
        for pkg in pkgs:
            print(pkg)
        
    except AccessDeniedError, e: # Catch if user press Cancel in the PolicyKit dialog
        print('Access denied')
    except YumLockedError, e: # Catch if user press Cancel in the PolicyKit dialog
        print('Yum is locked by another application')



"""

import os
import dbus
import sys
import json
from datetime import date

DAEMON_ORG = 'org.baseurl.Yum'
DAEMON_INTERFACE = DAEMON_ORG+'.Interface'

# Exception classes 

class AccessDeniedError(Exception):
    'User press cancel button in policykit window'

class YumLockedError(Exception):
    'The Yum daemon is locked'

class YumTransactionError(Exception):
    'The yum transaction failed'

def catch_exception(func):
    """
    This decorator to and dbus exceptions and make them python ones instead 
    """
    def newFunc(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except dbus.exceptions.DBusException, e:
            if e.get_dbus_name() == 'org.baseurl.Yum.AccessDeniedError': 
                raise AccessDeniedError(*e.args)
            elif e.get_dbus_name() == 'org.baseurl.Yum.YumLockedError':
                raise YumLockedError(*e.args)
            elif e.get_dbus_name() == 'org.baseurl.Yum.YumTransactionError':
                raise YumTransactionError(*e.args)
            else: raise

    newFunc.__name__ = func.__name__
    newFunc.__doc__ = func.__doc__
    newFunc.__dict__.update(func.__dict__)
    return newFunc

    
class YumDaemonClient:  
    ''' A class to communicate with a Yum DBUS system service daemon '''  

    def __init__(self):
        self.daemon = self._get_daemon() 

    def _get_daemon(self):
        ''' Get the daemon dbus object'''
        obj = None
        try:
            bus = dbus.SystemBus()
            obj = bus.get_object(DAEMON_ORG, '/')
        except dbus.exceptions.DBusException, e:
            print "Initialize of dbus daemon failed"
            print str(e)
        return obj

    @catch_exception
    def Lock(self):
        self.daemon.Lock(dbus_interface=DAEMON_INTERFACE)

    @catch_exception
    def Unlock(self):
        self.daemon.Unlock(dbus_interface=DAEMON_INTERFACE)
        
    @catch_exception
    def SetWatchdogState(self,state):
        '''
        Set the Watchdog state 
        :param state: True = Watchdog active, False = Watchdog disabled
        :type state: boolean (b)
        '''
        self.daemon.SetWatchdogState(state, dbus_interface=DAEMON_INTERFACE)
        

    @catch_exception
    def GetRepositories(self, filter):
        '''        
        :param filer:
        '''
        result = self.daemon.GetRepositories(filter, dbus_interface=DAEMON_INTERFACE)
        return [str(r) for r in result]

    @catch_exception
    def GetRepo(self, repo_id):
        '''
        
        :param repo_id:
        '''
        result = json.loads(self.daemon.GetRepo(repo_id, dbus_interface=DAEMON_INTERFACE))
        return result

    
    @catch_exception
    def GetConfig(self, setting):
        '''
        get yum package attribute (summary, size etc)
        :param id:
        :param attr:
        '''
        result = json.loads(self.daemon.GetConfig(setting, dbus_interface=DAEMON_INTERFACE))
        return result
            
    @catch_exception
    def GetAttribute(self, id, attr):
        '''
        get yum package attribute (summary, size etc)
        :param id:
        :param attr:
        '''
        result = self.daemon.GetAttribute(id, attr, dbus_interface=DAEMON_INTERFACE)
        if result == ':none': # illegal attribute
            result = None
        elif result == ':not_found': # package not found
            result = None # FIXME: maybe raise an exception
        else:
            result = json.loads(result)
        return result

    @catch_exception
    def GetAction(self, id):
        '''
        Return the available action for a given pkg_id
        The action is what can be performed on the package
        an installed package will return as 'remove' as action
        an available update will return 'update'
        an available package will return 'install'
        :param id: yum package id
        :type id: string (s)
        :return: action (remove, install, update, downgrade, obsolete)
        :rtype: string (s)
        '''
        result = self.daemon.GetAction(id, dbus_interface=DAEMON_INTERFACE)
        return result

    @catch_exception
    def GetPackages(self, pkg_filter):
        '''
        Get a list of pkg ids for a given package filter
        '''
        return self.daemon.GetPackages(pkg_filter, dbus_interface=DAEMON_INTERFACE, timeout=600)

    @catch_exception
    def GetPackageObjects(self, pkg_filter,fields):
        '''
        Get a list of pkg list for a given package filter
        each pkg list contains [pkg_id, field,....] where field is a atrribute of the package object
        Ex. summary, size etc.
        '''
        result = self.daemon.GetPackageObjects(pkg_filter, dbus_interface=DAEMON_INTERFACE, timeout=600)
        return json.loads(result)

    @catch_exception
    def GetPackagesByName(self, name, newest_only=True):
        '''
        Get a list of pkg ids for the current availabe updates
        '''
        return self.daemon.GetPackagesByName(name, newest_only, dbus_interface=DAEMON_INTERFACE, timeout=600)

    @catch_exception
    def ClearTransaction(self):
        '''
        Clear the current transaction
        '''
        return self.daemon.ClearTransaction(dbus_interface=DAEMON_INTERFACE, timeout=600)


    @catch_exception
    def GetTransaction(self):
        '''
        Get the current transaction
        '''
        return self.daemon.GetTransaction(dbus_interface=DAEMON_INTERFACE, timeout=600)

    @catch_exception
    def AddTransaction(self, id, action):
        '''
        Get a list of pkg ids for the current availabe updates
        '''
        return self.daemon.AddTransaction(id, action, dbus_interface=DAEMON_INTERFACE, timeout=600)

    @catch_exception
    def Install(self, pattern):
        '''
        Do a install <pattern string>, same as yum install <pattern string>
        '''
        return self.daemon.Install(pattern, dbus_interface=DAEMON_INTERFACE, timeout=600)

    @catch_exception
    def Remove(self, pattern):
        '''
        Do a install <pattern string>, same as yum remove <pattern string>
        '''
        return self.daemon.Remove(pattern, dbus_interface=DAEMON_INTERFACE, timeout=600)

    @catch_exception
    def Update(self, pattern):
        '''
        Do a update <pattern string>, same as yum update <pattern string>
        '''
        return self.daemon.Update(pattern, dbus_interface=DAEMON_INTERFACE, timeout=600)

    @catch_exception
    def Search(self, fields, keys, match_all):
        '''
        
        :param fields:
        :param keys:
        :param match_all:
        '''
        return self.daemon.Search(fields, keys, match_all, dbus_interface=DAEMON_INTERFACE, timeout=600)

    @catch_exception
    def GetGroups(self):
        '''
        
        '''
        return json.loads(self.daemon.GetGroups( dbus_interface=DAEMON_INTERFACE, timeout=600))

    @catch_exception
    def Reinstall(self, pattern):
        '''
        Do a reinstall <pattern string>, same as yum reinstall <pattern string>
        '''
        return self.daemon.Reinstall(pattern, dbus_interface=DAEMON_INTERFACE, timeout=600)

    @catch_exception
    def Downgrade(self, pattern):
        '''
        Do a install <pattern string>, same as yum remove <pattern string>
        '''
        return self.daemon.Downgrade(pattern, dbus_interface=DAEMON_INTERFACE, timeout=600)


    @catch_exception
    def BuildTransaction(self):
        '''
        Get a list of pkg ids for the current availabe updates
        '''
        return self.daemon.BuildTransaction( dbus_interface=DAEMON_INTERFACE, timeout=600)

    @catch_exception
    def RunTransaction(self):
        '''
        Get a list of pkg ids for the current availabe updates
        '''
        self.daemon.RunTransaction( dbus_interface=DAEMON_INTERFACE, timeout=600)

    
    def Exit(self):
        ''' End the daemon'''
        self.daemon.Exit(dbus_interface=DAEMON_INTERFACE)

    def GetVersion(self):
        ''' get the daemon version'''
        return self.daemon.GetVersion( dbus_interface=DAEMON_INTERFACE)
    
    def to_pkg_tuple(self, id):
        ''' find the real package from an package id'''
        (n, e, v, r, a, repo_id)  = str(id).split(',')
        return (n, e, v, r, a, repo_id)

    def to_txmbr_tuple(self, id):
        ''' find the real package from an package id'''
        (n, e, v, r, a, repo_id, ts_state)  = str(id).split(',')
        return (n, e, v, r, a, repo_id, ts_state)

    
if __name__ == '__main__':
    cli = YumDaemonClient()
    try:
        print "Daemon Version : %i" % cli.GetVersion()
        if len(sys.argv) > 1 and sys.argv[1] == 'quit':
            cli.Exit()
    except AccessDeniedError, e: # Catch if user press Cancel in the PolicyKit dialog
        print str(e)
    except YumLockedError, e: # Catch if user press Cancel in the PolicyKit dialog
        print str(e)
