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

   :rtype: string with API version

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


