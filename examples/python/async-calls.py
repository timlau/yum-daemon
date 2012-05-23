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

'''
This is a test for making async calls to Yum DBus Daemon

You can do a 'yum clean all' as root before to see the UpdateProgress from the 
metadata being downloaded for the mirrors.
'''

import dbus
import dbus.service
import dbus.glib
import gobject
import os
import sys

DAEMON_ORG = 'org.baseurl.Yum'
DAEMON_INTERFACE = DAEMON_ORG+'.Interface'

#------------------------------------------------------------------------------ Main class
class YumAsync:

    def __init__(self, mainloop):
        self.mainloop = mainloop # use to terminate mainloop
        self.bus = dbus.SystemBus()
        self.bus.add_signal_receiver(self.on_UpdateProgress, dbus_interface=DAEMON_INTERFACE,
                                     signal_name="UpdateProgress")
        self.bus.add_signal_receiver(self.on_TransactionEvent, dbus_interface=DAEMON_INTERFACE,
                                     signal_name="TransactionEvent")
        self.bus.add_signal_receiver(self.on_RPMProgress, dbus_interface=DAEMON_INTERFACE,
                                     signal_name="RPMProgress")
        self.daemon = self._get_daemon() 
        # Make the method call after a short delay
        gobject.timeout_add(1000, self.make_calls)

    def _get_daemon(self):
        ''' Get the daemon dbus object'''
        obj = None
        try:
            obj = self.bus.get_object(DAEMON_ORG, '/')
        except dbus.exceptions.DBusException, e:
            print "Initialize of dbus daemon failed"
            print str(e)
            sys.exit(1)
        return obj


    def on_UpdateProgress(self,name,frac,fread,ftime):
        print("UpdateProgress : %s %s" % (name,frac))

    def on_TransactionEvent(self,event):
        print("TransactionEvent : %s" % event)

    def on_RPMProgress(self, package, action, te_current, te_total, ts_current, ts_total):
        print("RPMProgress : %s %s" % (action, package))
        
    def handle_reply(self, pkgs):
        '''
        reply handler for the GetPackagesByName call
        @param pkgs: the result from the call
        '''
        print "We got some results"
        print 70 * "="
        self.show_package_list(pkgs)
        self.quit()

    def handle_error(self, rc):
        '''
        error handler for the GetPackagesByName call
        @param rc:
        '''
        print "We got some errors"
        print 70 * "="
        self.quit()
        
    def quit(self):
        '''
        quit the application by unlocking yum and stop the mainloop
        '''
        self.daemon.Unlock(dbus_interface=DAEMON_INTERFACE)
        self.mainloop.quit()
        
    def show_package_list(self, pkgs):    
        '''
        show a list of packages
        @param pkgs:
        '''
        for id in pkgs:
            (n, e, v, r, a, repo_id) = self.to_pkg_tuple(id)
            print " --> %s-%s:%s-%s.%s (%s)" % (n, e, v, r, a, repo_id)

    def to_pkg_tuple(self, id):
        ''' find the real package nevre & repoid from an package id'''
        (n, e, v, r, a, repo_id)  = str(id).split(',')
        return (n, e, v, r, a, repo_id)
        
    def make_calls(self):
        '''
        Get the yum lock and make an async call to GetPackagesByName
        '''
        print "starting make_calls"
        # get the lock 
        self.daemon.Lock(dbus_interface=DAEMON_INTERFACE)
        # call GetPackagesByName as a async call by using reply_handler and error_handler kwargs
        # reply_handler will be called when the result is ready, if an error occours the error_handler
        # will be called
        self.daemon.GetPackagesByName("yum*", True, 
                                     dbus_interface=DAEMON_INTERFACE, 
                                     timeout=600,
                                     reply_handler=self.handle_reply,
                                     error_handler=self.handle_error)
                                            
        print "ending make_calls"
        return False
        
        

def main():
    # setup the DBus mainloop
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    mainloop = gobject.MainLoop()
    YumAsync(mainloop)
    mainloop.run()

if __name__ == '__main__':
    main()