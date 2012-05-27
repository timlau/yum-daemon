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
      python2/      Contains the client API bindings for python 2.x
      python3/      Contains the client API bindings for python 3.x
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
  
    make test-verbos

to run the unit test with output to console

or this to just run the unit tests.

    make test
  
to make the daemon exit run:

    python client/python2/client.py quit
  
if you want to monitor the yum progress signals send by the daemon
the start the following in another shell window.

    python examples/python2/monitor.py
  
If you run it as normal user, you well get PolicyKit dialog asking for root password
If you run as root it will just execute

If you want to test the the daemon without installing it:

    su -c "./daemon.py"

in a separate shell window.

API Definitions: (Work in Progress)
====================================


## Data


**Package Id** = "name,epoch,version,release,arch,repoid" (Comma separated string)
**Transaction Id** = "name,epoch,version,release,arch,repoid,ts_state" (Comma separated string)
                
## Locking

#### Lock() (DONE)

start a new yum instance and set the yum lock

#### Unlock() (DONE)

release the yum lock and delete the current yum instance

## Config

#### GetConfig(option)

return value from config

#### SetConfig(option, value, persistant)
set config option=value (for current session or persistant)

    
## Repository

#### EnableRepo(repo_id, persistant)

Enable repo

#### DisableRepo(repo_id, persistant)

Disable repo

#### GetRepositories(filer) (DONE) 

get list with repos 
filter = "" return enabled repositories
filter = **some pattern** will return repo matching **some pattern**
Ex. filter = **\*** will return all repos., filter = **\*-source** will return source repos

#### GetRepo(repo_id) (DONE)

return information about a repo
the information is returned as a dictinary in JSON format

#### SetRepo(repo_id, repo_info)

change repo info or create new one is not exists
**repo_info** = {'name' : values,.......}

## Packages

#### GetPackages(pkg_narrow) (DONE)

Return list of package ids
**pkg_narrow** = installed|available|updates|obsoletes|.....
        
#### GetPackagesByName(pattern, newest_only) (DONE)

get a list of package ids where name matches pattern
**pattern** ::= \\<pattern string\\> (ex. 'yum', 'yum*')


#### GetAttribute(pkg_id, attribute) (DONE)

return an attribute value from at give pkg_id.
attribute = \<Yum Package attribute Name\> (Ex. 'summanry', 'description')
it return a string there contains a python repr of the attribute
':none' will be returned if attribute dont exist.
':not-found' will be returned if no package matching pkg_id is found

#### GetUpdateInfo(pkg_id)

Get updateinfo about a given pkg_id


## Groups
Methods to handle yum groups/categories

** Do be definded **

## Search:

#### Search(fields, keys, match_all) (DONE)

return a list of package ids for matching packages
fields = a list of package attributes to search in (Name, summary, description etc)
keys = a list of key words to search for.
match_all = define if all keys should match or partial match is allowed (boolean)

## History

#### GetHistory(elements)

return a list with a number of history ids (integers)

elements = the number of elements to return

#### GetHistoryInfo(id)

return a dict with details about a give history id


#### RedoHistory(id)

redo a given history id


#### UndoHistory(id)

undo given history id

## Transaction

#### AddTransaction(pkg_id, action) (DONE)

Add a package to the current transaction for an given action
action = install|update|remove|reinstall|downgrade|localinstall
localinstall takes a path to a .rpm file as pkg_id
return a list of transaction ids for the packages added to the transaction

#### BuildTransaction() (DONE)

resolve the dependencies of the current transaction.
return a (return code, output) pair
return code = 2 is transaction was resolved without problems
if no problems output will contains a repr of a list containing tuples of (action, package info list)
if problmes output will contain a list of desolve problem messages.


#### RunTransaction() (DONE)

will run the current transaction (Download, signature check, test transaction, transaction)

#### ClearTransaction() (DONE)

will clear the current transaction

#### GetTransaction() (DONE)

will return the member of the current transaction 

## high-level Methods

Simple method to emulate yum cli actions
there methods will find packages matching the argument and add them to the transaction
and return the transaction result for confirmation.
The transaction can then be executed by calling !RunTransaction()

#### Install(args) (DONE)

Do the same as "yum install args"

#### Remove(args) (DONE)

Do the same as "yum remove args"

#### Update(args) (DONE) 

Do the same as "yum update args"

#### Reinstall(args)  (DONE)

Do the same as "yum reinstall args"

#### Downgrade(args)  (DONE)

Do the same as "yum downgrade args"

## Signals: (D-Bus signals sendt by yum's callback handlers)

#### UpdateProgress(self,name,frac,fread,ftime) (DONE)

This signal will be sent a evey progress callback when something is being downloaded (metadata, packages etc)

    name : filename
    frac : Progress fracment (0 -\> 1)
    fread : formated string containing !BytesRead
    ftime : formated string containing remaining or elapsed time

#### TransactionEvent(self,event) (DONE)

This signal will be in differnet part of the transaction flow

event: an action keyword of where we are in the transaction process.

    start-build : when starting to depsolve
    end-build : when depsolve is completed
    start-run : when starting to execute the current transaction
    end-run : when current transaction is ended without error
    fail : when current transaction is ended with errors
    download : when package downloading is started
    signature-check : when package signature check is started
    run-test-transaction : when rpm test transaction starts
    run-transaction : when rpm transaction starts


#### RPMProgress(pkg_id, action, te_current, te_total, ts_current, ts_total) (DONE)

    package : A package id or simple string of a package name
    action : the action being performed ( install,cleanup .....)
    te_current : Current number of bytes processed in the transaction element being processed
    te_total : Total number of bytes in the transaction element being processed
    ts_current : number of processes completed in whole transaction
    ts_total : total number of processes in the transaction.

#### Progress(action, percent)

    action : action being performed
    percent : the progress of the whole transaction in percent

