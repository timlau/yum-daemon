yum-daemon
===========

Yum-daemon is a 2 DBus services there make part for Yum's API available for application via DBus calls.

There is a DBus session bus service runnning as current user for performing readonly actions.

There is a DBus system bus service runnning as root for performing actions there is making changes to the system

This make it easy to do packaging action from your application no matter what language it is written in, as long as there
is DBus binding for it.

Yum-daemon uses PolicyKit for authentication for the system service, so when you call one of the commands (as normal users) you will get a  
PolicyKit dialog to ask for password of a priviledged user like root.

**yum-daemon is still under heavy development and the API is not stable or complete yet**

Source overview
----------------

    yumdaemon/      Contains the daemon python source
    client/         Contains the client API bindings for python 2.x & 3.x
    test/           Unit test for the daemon and python bindings
    dbus/           DBus system service setup files
    policykit1/     PolicyKit authentication setup files



How to install services and python bindings:
-----------------------------------------------

Run the following as root

	git clone ...
	cd yum-daemon
	make test-release
	sudo yum install ~/rpmbuild/RPMS/noarch/*yumdaemon*.rpm

How to test:
-------------

just run:
   
    make test-verbose

to run the unit test with output to console

or this to just run the unit tests.

    make test
   
To make the daemons shutdown
-------------------------------

Session:
	
	make kill-session
	
System
	
	make kill-system
	
Both

    make kill-both
   

to run the daemons in debug mode from checkout:
------------------------------------------------

session (readonly as current user)

	make run-session

system (as root)
	
	make run-system


API Definitions: 
====================================

The yumdaemon api is documented [here](http://timlau.fedorapeople.org/yumdaemon)


