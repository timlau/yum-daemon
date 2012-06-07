yum-daemon
===========

Yum-daemon is a DBus system service there make part for Yum's API available for application via DBus calls.

This make it easy to do packaging action from your application no matter what language it is written in, as long as there
is DBus binding for it.

Yum-daemon uses PolicyKit for authentication, so when you call one of the commands (as normal users) you will get a  
PolicyKit dialog to ask for password of a priviledged user like root.

**yum-daemon is still under heavy development and the API is not stable or complete yet**

Source overview
----------------

    server/         Contains the daemon python source
    client/
      yumdaemon2/      Contains the client API bindings for python 2.x
      yumdaemon3/      Contains the client API bindings for python 3.x
    test/           Unit test for the daemon and python 2.x bindings
    dbus/           DBus system service setup files
    policykit1/     PolicyKit authentication setup files



How to install:
----------------

Run the following as root

`make install DESTDIR=/`

How to test:
-------------

just run:
   
    make test-verbose

to run the unit test with output to console

or this to just run the unit tests.

    make test
   
to make the daemon exit run:

    python examples/yumdaemon2/exit.py
   
if you want to monitor the yum progress signals send by the daemon
the start the following in another shell window.

    python examples/yumdaemon2/monitor.py
   
If you run it as normal user, you well get PolicyKit dialog asking for root password
If you run as root it will just execute

If you want to test the the daemon without installing it:

    su -c "./yumdaemon/daemon.py -v --notimeout"

**-v** gives extra verbose outout from the daemon  
**--notimeout** disable the daemon watchdog, there normally will quit the daemon after 20 second, if not in use 
 
in a separate shell window.

API Definitions: 
====================================

The yumdaemon api is documented [here](http://timlau.fedorapeople.org/yumdaemon)
