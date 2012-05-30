#!/usr/bin/python

'''
A little helper to exit the running yumdaemon
'''

from yumdaemon2 import YumDaemonClient

if __name__ == "__main__":
    cli = YumDaemonClient()
    cli.Exit()