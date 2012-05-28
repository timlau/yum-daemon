==========================================
yum-daemon DBus service API documentation
==========================================

The yum-daemon is an easy way to utililize the power of the yum package manager from your own programs

API Methods
=============

Misc methods
-------------

.. py:function:: GetVersion()

   Get the API version

   :return: string with API version

.. py:function:: Lock()

   Get the daemon Lock, if posible

.. py:function:: Unlock()

   Get the daemon Lock, if posible

Repository and config methods
------------------------------

.. py:function:: GetRepositories(filter)

   Get the value a list of repo ids

   :param filter: filter to limit the listed repositories
   :type filter: String
   :return: list of strings with repo id's

.. py:function:: GetRepo(repo_id)

   Get information about a give repo_id

   :param repo_id: repo id 
   :return: a dictionary with repo information
   :rtype: JSON string


.. py:function:: GetConfig(setting)

   Get the value of a yum config setting

   :param setting: name of setting (debuglevel etc..)
   :return:  the config value of the requested setting
   :rtype: JSON string

Package methods
----------------

These methods is for getting packages and information about packages

.. py:function:: GetPackages(pkg_filter)
.. py:function:: GetPackageObjects(pkg_filter, fields)
.. py:function:: GetPackagesByName(name, newest_only)
.. py:function:: GetAttribute(id, attr,)
.. py:function:: GetUpdateInfo(id,)
.. py:function:: Search(fields, keys, match_all )

High level methods
-------------------
The high level methods simulate the yum command line main functions.

.. py:function:: Install(cmds)
Works just like the 'yum install **cmds**' command line

   :param cmds: package arguments separated by spaces
   :type cmds: String
   :return: return code, result of resolved transaction
   :rtype: (return code, transaction) encoded as JSON

.. py:function:: Remove(cmds)
Works just like the 'yum remove **cmds**' command line

   :param cmds: package arguments separated by spaces
   :type cmds: String
   :return: return code, result of resolved transaction
   :rtype: (return code, transaction) encoded as JSON


.. py:function:: Update(cmds)
Works just like the 'yum update **cmds**' command line

   :param cmds: package arguments separated by spaces
   :type cmds: String
   :return: return code, result of resolved transaction
   :rtype: (return code, transaction) encoded as JSON


.. py:function:: Reinstall(cmds)
Works just like the 'yum reinstall **cmds**' command line

   :param cmds: package arguments separated by spaces
   :type cmds: String
   :return: return code, result of resolved transaction
   :rtype: (return code, transaction) encoded as JSON


.. py:function:: Downgrade(cmds)
Works just like the 'yum downgrade **cmds**' command line

   :param cmds: package arguments separated by spaces
   :type cmds: String
   :return: return code, result of resolved transaction
   :rtype: (return code, transaction) encoded as JSON



Transaction methods
--------------------
These methods is for handling the current yum transaction

.. py:function:: AddTransaction(id, action)
.. py:function:: ClearTransaction()
.. py:function:: GetTransaction()
.. py:function:: BuildTransaction()
.. py:function:: RunTransaction()

.. py:function:: GetGroups( )

