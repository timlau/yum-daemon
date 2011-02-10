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

DAEMON_ORG = 'org.baseurl.Yum'
DAEMON_INTERFACE = DAEMON_ORG+'.Interface'

# Exception classes 
class CommandFailError(Exception):
    'Fail to execute a command'

class AccessDeniedError(Exception):
    'User press cancel button in policykit window'

class YumLockedError(Exception):
    'The Yum daemon is locked'
    
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

    def lock(self):
        try:
            self.daemon.lock(dbus_interface=DAEMON_INTERFACE)
        except dbus.exceptions.DBusException, e:
            if e.get_dbus_name() == 'org.baseurl.Yum.AccessDeniedError': raise AccessDeniedError(*e.args)
            elif e.get_dbus_name() == 'org.baseurl.Yum.YumLockedError':
                if not ignore_error: raise YumLockedErrors(*e.args)
            else: raise

    def unlock(self):
        try:
            self.daemon.unlock(dbus_interface=DAEMON_INTERFACE)
        except dbus.exceptions.DBusException, e:
            if e.get_dbus_name() == 'org.baseurl.Yum.AccessDeniedError': raise AccessDeniedError(*e.args)
            elif e.get_dbus_name() == 'org.baseurl.Yum.YumLockedError':
                if not ignore_error: raise YumLockedErrors(*e.args)
            else: raise

    def get_packages(self, narrow):
        '''
        Get a list of pkg ids for the current availabe updates
        '''
        try:
            return self.daemon.get_packages(narrow, dbus_interface=DAEMON_INTERFACE, timeout=600)
        except dbus.exceptions.DBusException, e:
            if e.get_dbus_name() == 'org.baseurl.Yum.AccessDeniedError': raise AccessDeniedError(*e.args)
            elif e.get_dbus_name() == 'org.baseurl.Yum.YumLockedError':
                if not ignore_error: raise YumLockedErrors(*e.args)
            else: raise
    
    def exit(self):
        ''' End the daemon'''
        self.daemon.exit(dbus_interface=DAEMON_INTERFACE)

    def get_version(self):
        ''' get the daemon version'''
        return self.daemon.get_version( dbus_interface=DAEMON_INTERFACE)

if __name__ == '__main__':
    cli = YumDaemonClient()
    try:
        print('Getting deamon version')
        print "Daemon Version : %i" % cli.get_version()
        cli.lock()
        print('Testing get_packages')
        pkgs = cli.get_packages('installed')
        for po in sorted(pkgs):
            print str(po)
        pkgs = cli.get_packages('updates')
        for po in sorted(pkgs):
            print str(po)
        cli.unlock()
    except AccessDeniedError, e: # Catch if user press Cancel in the PolicyKit dialog
        print str(e)
    except YumLockedError, e: # Catch if user press Cancel in the PolicyKit dialog
        print str(e)
