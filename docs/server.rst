==========================================
DBus service API documentation
==========================================

The yumdaemon is an easy way to utililize the power of the yum package manager from your own programs

Data structures
----------------

.. table:: **Data structures**

   =================================  =================================
   Name                               Content
   =================================  =================================
   Package Id (pkg_id)                "name,epoch,ver,rel,arch,repo_id"
   Transaction List (tx_list)	      "pkg_id,ts_state"		 
   =================================  =================================
   
|
   
.. table:: **Attribute Descriptions**

   ================  =========================================================
   Attribute         Description
   ================  =========================================================
   name              Package Name
   epoch             Package Epoch
   ver               Package Version
   rel               Package Release
   arch				 Package Architecture
   repo_id			 Repository Id
   ts_state			 Transaction Member state
   ================  =========================================================
   
Transaction result::

	<transaction_result> ::= <result>, <result>, ...., <result>
	<result>             ::= <action>, <pkg_list>
	<action>             ::= install | update | remove | install-deps | update-deps | remove-deps | skipped
	<plg_list>           ::= <pkg_info>, <pkg_info>, ......, <pkg_info>
	<pkg_info>           ::= <pkg_id>, size, <obs_list>
	<pkg_id>             ::= name, epoch, version, release, arch, repo_id
	<obs_list>           ::= <obs_id>, <obs_id>, ...., <obs_id>
	<obs_id>             ::= name, epoch, version, release, arch, repo_id for packages obsoletes by <pkg_id>
   
 
Misc methods
-------------

.. function:: GetVersion()

   Get the API version

   :return: string with API version

.. function:: Lock()

   Get the daemon Lock, if posible

.. function:: Unlock()

   Get the daemon Lock, if posible

Repository and config methods
------------------------------

.. py:function:: GetRepositories(filter)

   Get the value a list of repo ids

   :param filter: filter to limit the listed repositories
   :type filter: string
   :return: list of repo id's
   :rtype: array for stings (as)

.. py:function:: GetRepo(repo_id)

   Get information about a give repo_id

   :param repo_id: repo id 
   :type repo_id: string
   :return: a dictionary with repo information **(JSON)**
   :rtype: string (s)


.. py:function:: GetConfig(setting)

   Get the value of a yum config setting

   :param setting: name of setting (debuglevel etc..)
   :type setting: string
   :return: the config value of the requested setting **(JSON)**
   :rtype: string (s)

Package methods
----------------

These methods is for getting packages and information about packages

.. function:: GetPackages(pkg_filter)

   get a list of packages matching the filter type
   
   :param pkg_filter: package filter ('installed','available','updates','obsoletes','recent','extras')
   :type pkg_filter: string
   :return: list of pkg_id's
   :rtype: array of strings (as)
   


.. function:: GetPackageObjects(pkg_filter, fields)

   | Get a list of pkg list for a given package filter  
   | each pkg list contains [pkg_id, field,....] where field is a atrribute of the package object  
   | Ex. summary, size etc.  
	
   :param pkg_filter: package filter ('installed','available','updates','obsoletes','recent','extras')
   :type pkg_filter: string
   :param fields: yum package objects attributes to get.
   :type fields: array of strings (as)
   :return: list of (id, field1, field2...) **(JSON)**, each JSON Sting contains (id, field1, field2...)
   :rtype: array of strings (as) 

.. py:function:: GetPackagesByName(name, newest_only)

   Get a list of pkg ids for starts with name
        
   :param name: name prefix to match
   :type name: string
   :param newest_only: show only the newest match or every match.
   :type newest_only: boolean
   :return: list of pkg_id's
   :rtype: array of strings (as)


.. py:function:: GetAttribute(id, attr,)

   get yum package attribute (description, filelist, changelog etc)

   :param pkg_id: pkg_id to get attribute from
   :type pkg_id: string
   :param attr: name of attribute to get
   :type attr: string
   :return: the value of the attribute **(JSON)**, the content depend on attribute being read
   :rtype:  string (s)
   
.. py:function:: GetUpdateInfo(id)
 
   Get Updateinfo for a package
        
   :param pkg_id: pkg_id to get update info from
   :type pkg_id: string
   :return: update info for the package **(JSON)**
   :rtype: string (s)

.. py:function:: Search(fields, keys, match_all )

   Search for packages where keys is matched in fields
        
   :param fields: yum po attributes to search in
   :type fields: array of strings
   :param keys: keys to search for
   :type keys: array of strings
   :param match_all: match all keys or only one
   :type match_all: boolean
   :return: list of pkg_id's for matches
   :rtype: array of stings (as)


High level methods
-------------------
The high level methods simulate the yum command line main functions.

.. py:function:: Install(cmds)

Works just like the ``yum install <cmds>`` command line

   :param cmds: package arguments separated by spaces
   :type cmds: string
   :return: return code, result of resolved transaction (rc = 2 is ok, else failure) **(JSON)**
   :rtype: string (s)

.. py:function:: Remove(cmds)

   Works just like the ``yum install <cmds>`` command line

   :param cmds: package arguments separated by spaces
   :type cmds: string
   :return: return code, result of resolved transaction (rc = 2 is ok, else failure) **(JSON)**
   :rtype: string (s)


.. py:function:: Update(cmds)

   Works just like the ``yum install <cmds>`` command line

   :param cmds: package arguments separated by spaces
   :type cmds: string
   :return: return code, result of resolved transaction (rc = 2 is ok, else failure) **(JSON)**
   :rtype: string (s)


.. py:function:: Reinstall(cmds)

   Works just like the ``yum install <cmds>`` command line

   :param cmds: package arguments separated by spaces
   :type cmds: string
   :return: return code, result of resolved transaction (rc = 2 is ok, else failure) **(JSON)**
   :rtype: string (s)


.. py:function:: Downgrade(cmds)

   Works just like the ``yum install <cmds>`` command line

   :param cmds: package arguments separated by spaces
   :type cmds: string
   :return: return code, result of resolved transaction (rc = 2 is ok, else failure) **(JSON)**
   :rtype: string (s)



Transaction methods
--------------------
These methods is for handling the current yum transaction

.. py:function:: AddTransaction(id, action)

   Add an package to the current transaction 
        
   :param id: package id for the package to add
   :type id: string
   :param action: the action to perform ( install, update, remove, obsolete, reinstall, downgrade, localinstall )
   :type action: string
   :return: list of (pkg_id, transaction state) pairs for the added members (comma separated)
   :rtype: array of strings (as)

.. py:function:: ClearTransaction()

   Clear the current transaction
   
.. py:function:: GetTransaction()

   Get the currrent transaction

   :return: list of (pkg_id, transaction state) pairs in the current transaction (comma separated)
   :rtype: array of strings (as)
   
.. py:function:: BuildTransaction()

   Depsolve the current transaction
   
   :return: (return code, result of resolved transaction) pair (rc = 2 is ok, else failure) **(JSON)**
   :rtype: string (s)
   
	
.. py:function:: RunTransaction()

   Execute the current transaction

Groups
-------

Methods to work with yum groups and categories

.. py:function:: GetGroups( )

   Get available group id's

.. note:: Under Development
   
   More to come in the future, methods to install groups etc. has to be defined and implemented

History
--------

Methods to work with the yum history

.. note:: Under Development
   
   Has not been defined and implemented yet