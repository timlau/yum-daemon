==========================================
Client API for Python 2.x and 3.x
==========================================

.. automodule:: yumdaemon

Classes
========

System API
-------------

.. autoclass:: yumdaemon.YumDaemonClient
    :members: Exit, Lock, Unlock, SetWatchdogState,GetPackageWithAttributes, GetRepositoriesGetRepo, GetConfig, SetConfig,
    		  GetAttribute, GetUpdateInfo, GetPackages, GetPackagesByName, GetHistoryByDays, HistorySearch, GetHistoryPackages,
    		  GetGroups, Search, ClearTransaction, GetTransaction, AddTransaction, Install, Remove, Update, Reinstal, Downgrade,
    		  BuildTransaction, RunTransaction
    
Session API
------------

.. autoclass:: yumdaemon.YumDaemonReadOnlyClient
    :members: Exit, Lock, Unlock, SetWatchdogState,GetPackageWithAttributes, GetRepositoriesGetRepo, GetConfig, 
    		  GetAttribute, GetUpdateInfo, GetPackages, GetPackagesByName, GetGroups, Search
    		  BuildTransaction, RunTransaction
    
Exceptions
============

.. class:: YumDaemonError(Exception)

Base Exception from the backend

.. class:: AccessDeniedError(YumDaemonError)

PolicyKit access was denied.

Ex.
User press cancel button in policykit window

.. class:: YumLockedError(YumDaemonError)

Yum is locked by another application

Ex.
yum is running in a another session
You have not called the Lock method to grep the Lock


.. class:: YumTransactionError(YumDaemonError)

Error in the yum transaction.

