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
from datetime import date

DAEMON_ORG = 'org.baseurl.Yum'
DAEMON_INTERFACE = DAEMON_ORG+'.Interface'

# Exception classes 

class AccessDeniedError(Exception):
    'User press cancel button in policykit window'

class YumLockedError(Exception):
    'The Yum daemon is locked'

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
    def lock(self):
        self.daemon.lock(dbus_interface=DAEMON_INTERFACE)

    @catch_exception
    def unlock(self):
        self.daemon.unlock(dbus_interface=DAEMON_INTERFACE)
            
    @catch_exception
    def get_attribute(self, id, attr):
        '''
        get yum package attribute (summary, size etc)
        @param id:
        @param attr:
        '''
        result = self.daemon.get_attribute(id, attr, dbus_interface=DAEMON_INTERFACE)
        if result == ':none': # illegal attribute
            result = None
        elif result == ':not_found': # package not found
            result = None # FIXME: maybe raise an exception
        else:
            result = eval(result)
        return result

    @catch_exception
    def get_packages(self, narrow):
        '''
        Get a list of pkg ids for the current availabe updates
        '''
        return self.daemon.get_packages(narrow, dbus_interface=DAEMON_INTERFACE, timeout=600)

    @catch_exception
    def get_packages_by_name(self, name, newest_only=True):
        '''
        Get a list of pkg ids for the current availabe updates
        '''
        return self.daemon.get_packages_by_name(name, newest_only, dbus_interface=DAEMON_INTERFACE, timeout=600)
    
    def exit(self):
        ''' End the daemon'''
        self.daemon.exit(dbus_interface=DAEMON_INTERFACE)

    def get_version(self):
        ''' get the daemon version'''
        return self.daemon.get_version( dbus_interface=DAEMON_INTERFACE)
    
    def to_pkg_tuple(self, id):
        ''' find the real package from an package id'''
        (n, e, v, r, a, repo_id)  = str(id).split(',')
        return (n, e, v, r, a, repo_id)


def show_changelog(changelog, max_elem=3):
    i = 0
    for (c_date, c_ver, msg) in changelog:
        i += 1
        if i > max_elem:
            return
        print("* %s %s" % (date.fromtimestamp(c_date).isoformat(), c_ver))
        for line in msg.split('\n'):
            print("%s" % line)
    
    
if __name__ == '__main__':
    cli = YumDaemonClient()
    try:
        print('Getting deamon version')
        print "Daemon Version : %i" % cli.get_version()
        if len(sys.argv) > 1 and sys.argv[1] == 'quit':
            cli.exit()
        else:
            cli.lock()
            print('Testing get_packages')
            pkgs = cli.get_packages('installed')
            for po in sorted(pkgs):
                print str(po)
            id = str(po)
            (n, e, v, r, a, repo_id) = cli.to_pkg_tuple(id)
            print "Name : %s " % n
            print "Summary : %s" % cli.get_attribute(id, 'summary')                 
            pkgs = cli.get_packages('updates')
            for po in sorted(pkgs):
                print str(po)
            id = str(po)
            (n, e, v, r, a, repo_id) = cli.to_pkg_tuple(id)
            print "\nName : %s " % n
            print "Summary : %s" % cli.get_attribute(id, 'summary')    
            print "\nDescription:"             
            print cli.get_attribute(id, 'description')               
            print "\nChangelog:"             
            changelog = cli.get_attribute(id, 'changelog')
            show_changelog(changelog, max_elem=2)   
            pkgs = cli.get_packages_by_name('yum', newest_only=False)            
            for po in sorted(pkgs):
                print str(po)
            cli.unlock() # We should always 
    except AccessDeniedError, e: # Catch if user press Cancel in the PolicyKit dialog
        print str(e)
    except YumLockedError, e: # Catch if user press Cancel in the PolicyKit dialog
        print str(e)
