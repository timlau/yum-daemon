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
    def GetRepositories(self, filter):
        '''        
        @param filer:
        '''
        result = self.daemon.GetRepositories(filter, dbus_interface=DAEMON_INTERFACE)
        return [str(r) for r in result]

    @catch_exception
    def GetRepo(self, repo_id):
        '''
        
        @param repo_id:
        '''
        result = json.loads(self.daemon.GetRepo(repo_id, dbus_interface=DAEMON_INTERFACE))
        return result

    
    @catch_exception
    def GetConfig(self, setting):
        '''
        get yum package attribute (summary, size etc)
        @param id:
        @param attr:
        '''
        result = json.loads(self.daemon.GetConfig(setting, dbus_interface=DAEMON_INTERFACE))
        return result
            
    @catch_exception
    def GetAttribute(self, id, attr):
        '''
        get yum package attribute (summary, size etc)
        @param id:
        @param attr:
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
    def GetPackages(self, narrow):
        '''
        Get a list of pkg ids for the current availabe updates
        '''
        return self.daemon.GetPackages(narrow, dbus_interface=DAEMON_INTERFACE, timeout=600)

    @catch_exception
    def GetPackagesByName(self, name, newest_only=True):
        '''
        Get a list of pkg ids for the current availabe updates
        '''
        return self.daemon.GetPackagesByName(name, newest_only, dbus_interface=DAEMON_INTERFACE, timeout=600)

    @catch_exception
    def AddTransaction(self, id, action):
        '''
        Get a list of pkg ids for the current availabe updates
        '''
        return self.daemon.AddTransaction(id, action, dbus_interface=DAEMON_INTERFACE, timeout=600)

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


def show_changelog(changelog, max_elem=3):
    i = 0
    for (c_date, c_ver, msg) in changelog:
        i += 1
        if i > max_elem:
            return
        print("* %s %s" % (date.fromtimestamp(c_date).isoformat(), c_ver))
        for line in msg.split('\n'):
            print("%s" % line)

def show_package_list(pkgs):    
    for id in pkgs:
        (n, e, v, r, a, repo_id) = cli.to_pkg_tuple(id)
        print " --> %s-%s:%s-%s.%s (%s)" % (n, e, v, r, a, repo_id)

def show_transaction_list(pkgs):    
    for id in pkgs:
        id = str(id)
        (n, e, v, r, a, repo_id, ts_state) = cli.to_txmbr_tuple(id)
        print " --> %s-%s:%s-%s.%s (%s) - %s" % (n, e, v, r, a, repo_id, ts_state)

def show_transaction_result(output):
    for action, pkgs in output:
        print "  %s" % action
        for pkg in pkgs:
            print "  --> %s" % str(pkg)
    
if __name__ == '__main__':
    cli = YumDaemonClient()
    try:
        print "Daemon Version : %i" % cli.GetVersion()
        if len(sys.argv) > 1 and sys.argv[1] == 'quit':
            cli.Exit()
        else:
            cli.Lock()
            all_conf = cli.GetConfig('*')
            for key in all_conf:
                print "   %s = %s" % (key,all_conf[key])
            repos = cli.GetRepositories('*-source')
            print repos
            print cli.GetRepo('fedoraXXX')
            print "errorlevel = %s" % cli.GetConfig('errorlevel')
#            print "\nInstalled packages"             
#            pkgs = cli.GetPackages('installed')
#            show_package_list(pkgs)
            print "\nAvailable Updates"             
            pkgs = cli.GetPackages('updates')
            show_package_list(pkgs)
            id = str(pkgs[-1])
            (n, e, v, r, a, repo_id) = cli.to_pkg_tuple(id)
            print "\nPackage attributes"             
            print "Name : %s " % n
            print "Summary : %s" % cli.GetAttribute(id, 'summary')    
            print "\nDescription:"             
            print cli.GetAttribute(id, 'description')               
            print "\nChangelog:"             
            changelog = cli.GetAttribute(id, 'changelog')
            show_changelog(changelog, max_elem=2)   
            print "\nGet all yum packages:"                         
            pkgs = cli.GetPackagesByName('yum', newest_only=False)            
            show_package_list(pkgs)
            print "\nGet all packages starting with yum (newest only)"                         
            pkgs = cli.GetPackagesByName('yum*', newest_only=True)            
            show_package_list(pkgs)
            print "\ninstall/remove a package (yum-plugin-aliases)"                                     
            pkgs = cli.GetPackagesByName('yum-plugin-aliases', newest_only=True)
            if pkgs:
                id = str(pkgs[0])
                (n, e, v, r, a, repo_id) = cli.to_pkg_tuple(id)
                if repo_id.startswith('@'):
                    action = 'remove'
                else:
                    action = 'install'                    
                print "Adding %s to transaction for %s" % (n,action)    
                res = cli.AddTransaction(id, action)
                show_transaction_list(res)
                print "Resolving dependencies"
                rc, output = json.loads(cli.BuildTransaction())
                #print rc,output
                if rc == 2:
                    show_transaction_result(output)
                    try:
                        print "Running the transaction"
                        cli.RunTransaction()
                        print "Transaction Completed"
                    except YumTransactionError,e:
                        print "Transaction Failed : %s " % str(e)
            cli.Unlock() # We should always 
    except AccessDeniedError, e: # Catch if user press Cancel in the PolicyKit dialog
        print str(e)
    except YumLockedError, e: # Catch if user press Cancel in the PolicyKit dialog
        print str(e)
