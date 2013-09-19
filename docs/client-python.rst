==========================================
Client API for Python 2.x &3.x
==========================================

.. automodule:: yumdaemon

Classes
========

.. autoclass:: yumdaemon.YumDaemonClient
    :members:
    

.. autoclass:: yumdaemon.YumDaemonReadOnlyClient
    :members:
    
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

