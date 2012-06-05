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
This is a test monitor for the DBus signals send by the Yum DBus Daemon
'''

import dbus
import dbus.service
import dbus.glib
import gobject
import os

DAEMON_ORG = 'org.baseurl.Yum'
DAEMON_INTERFACE = DAEMON_ORG+'.Interface'

#------------------------------------------------------------------------------ Main class
class YumSignalMonitor:

    def __init__(self, mainloop):
        self.mainloop = mainloop # use to terminate mainloop
        self.bus = dbus.SystemBus()
        self.bus.add_signal_receiver(self.on_UpdateProgress, dbus_interface=DAEMON_INTERFACE,
                                     signal_name="UpdateProgress")
        self.bus.add_signal_receiver(self.on_TransactionEvent, dbus_interface=DAEMON_INTERFACE,
                                     signal_name="TransactionEvent")
        self.bus.add_signal_receiver(self.on_RPMProgress, dbus_interface=DAEMON_INTERFACE,
                                     signal_name="RPMProgress")


    def on_UpdateProgress(self,name,frac,fread,ftime):
        print("UpdateProgress : %s %s" % (name,frac))

    def on_TransactionEvent(self,event, data):
        print("TransactionEvent : %s" % event)

    def on_RPMProgress(self, package, action, te_current, te_total, ts_current, ts_total):
        print("RPMProgress : %s %s" % (action, package))
        

def main():
    # setup the DBus mainloop
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    mainloop = gobject.MainLoop()
    YumSignalMonitor(mainloop)
    mainloop.run()

if __name__ == '__main__':
    main()