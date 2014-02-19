# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# (C) 2013 - Tim Lauridsen <timlau@fedoraproject.org>

"""
Common stuff for the yumdaemon dbus services
"""
from __future__ import print_function
from __future__ import absolute_import
import os
import dbus
import dbus.service
import dbus.glib
import gobject
import json
import logging
from datetime import datetime

import sys
from time import time
from dnf.pycomp import long

import dnf
import dnf.yum
import dnf.const
import dnf.conf
import dnf.subject

FAKE_ATTR = ['downgrades','action','pkgtags']
NONE = json.dumps(None)


#------------------------------------------------------------------------------ Callback handlers
class DownloadCallback:
    '''
    Yum Download callback handler class
    the updateProgress will be called while something is being downloaded
    '''
    def __init__(self):
        pass
    
    def updateProgress(self,name,frac,fread,ftime):
        '''
        Update the progressbar
        :param name: filename
        :param frac: Progress fracment (0 -> 1)
        :param fread: formated string containing BytesRead
        :param ftime : formated string containing remaining or elapsed time
        '''
        # send a DBus signal with progress info
        self.base.UpdateProgress(name,frac,fread,ftime)


logger = logging.getLogger('yumdaemon.service')

def Logger(func):
    """
    This decorator catch yum exceptions and send fatal signal to frontend
    """
    def newFunc(*args, **kwargs):
        logger.debug("%s started args: %s " % (func.__name__, repr(args[1:])))
        rc = func(*args, **kwargs)
        logger.debug("%s ended" % func.__name__)
        return rc

    newFunc.__name__ = func.__name__
    newFunc.__doc__ = func.__doc__
    newFunc.__dict__.update(func.__dict__)
    return newFunc

class DnfDaemonBase(dbus.service.Object, DownloadCallback):

    def __init__(self, mainloop):
        DownloadCallback.__init__(self)
        self.logger = logging.getLogger('dnfdaemon.base')
        self.mainloop = mainloop # use to terminate mainloop
        self.authorized_sender = set()
        self._lock = None
        self._base = None
        self._can_quit = True
        self._is_working = False
        self._watchdog_count = 0
        self._watchdog_disabled = False
        self._timeout_idle = 20         # time to daemon is closed when unlocked
        self._timeout_locked = 600      # time to daemon is closed when locked and not working

    @property
    def base(self):
        '''
        yumbase property so we can auto initialize it if not defined
        '''
        if not self._base:
            self._get_base()
        return self._base

#===============================================================================
# Helper methods for api methods both in system & session
# Search -> _search etc
#===============================================================================


    def _search(self, fields, keys, match_all, newest_only, tags):
        '''
        Search for for packages, where given fields contain given key words
        (Helper for Search)
        
        :param fields: list of fields to search in
        :param keys: list of keywords to search for
        :param match_all: match all flag, if True return only packages matching all keys
        :param newest_only: return only the newest version of a package
        :param tags: seach pkgtags
        '''
        result = []
        # TODO : Add dnf code
        return result



    def _get_packages_by_name(self, name, newest_only):
        '''
        Get a list of packages from a name pattern
        (Helper for GetPackagesByName)
        
        :param name: name pattern
        :param newest_only: True = get newest packages only
        '''
        subj = dnf.subject.Subject(name)
        qa = subj.get_best_query(self.base.sack, with_provides=False)
        if newest_only:
            qa = qa.latest()
        pkg_ids = self._to_package_id_list(qa)
        return pkg_ids

    def _get_groups(self):
        '''
        make a list with categoties and there groups
        This is the old way of yum groups, where a group is a collection of mandatory, default and optional pacakges
        and the group is installed when all mandatory & default packages is installed.
        '''
        all_groups = []
        # TODO : Add dnf code
        all_groups.sort()
        return json.dumps(all_groups)

    def _get_repositories(self, filter):
        '''
        Get the value a list of repo ids
        :param filter: filter to limit the listed repositories
        '''
        repos = []
        # TODO : Add dnf code
        return repos
    

    def _get_config(self, setting):
        '''
        Get the value of a yum config setting
        it will return a JSON string of the config
        :param setting: name of setting (debuglevel etc..)
        '''
        value = json.dumps(None)
        # TODO : Add dnf code
        return value
    
    def _get_repo(self, repo_id ):
        '''
        Get information about a give repo_id
        the repo setting will be returned as dictionary in JSON format
        :param repo_id:
        '''
        value = json.dumps(None)
        # TODO : Add dnf code
        return value
    
    def _get_packages(self, pkg_filter):
        '''
        Get a list of package ids, based on a package pkg_filterer
        :param pkg_filter: pkg pkg_filter string ('installed','updates' etc)
        '''
        if pkg_filter in ['installed','available','updates','obsoletes','recent','extras']:
            yh = self.base.doPackageLists(pkgnarrow=pkg_filter)
            pkgs = getattr(yh,pkg_filter)
            value = self._to_package_id_list(pkgs)
        else:
            value = []
        return value
    
    def _get_package_with_attributes(self, pkg_filter, fields):
        '''
        Get a list of package ids, based on a package pkg_filterer
        :param pkg_filter: pkg pkg_filter string ('installed','updates' etc)
        '''
        value = []
        if pkg_filter in ['installed','available','updates']:
            pkgs = self._get_packages(pkg_filter)
            value = [self._get_po_list(po,fields) for po in pkgs]
        return value

    def _get_attribute(self, id, attr):
        '''
        Get an attribute from a yum package id
        it will return a python repr string of the attribute
        :param id: yum package id
        :param attr: name of attribute (summary, size, description, changelog etc..)
        '''
        po = self._get_po(id)
        if po:
            if attr in FAKE_ATTR: # is this a fake attr:
                value = json.dumps(self._get_fake_attributes(po, attr))
            elif hasattr(po, attr):
                value = json.dumps(getattr(po,attr))
            else:
                value = json.dumps(None)
        else:
            value = json.dumps(None)
        return value

    def _get_updateInfo(self, id):
        '''
        Get an Update Infomation e from a yum package id
        it will return a python repr string of the attribute
        :param id: yum package id
        '''
        po = self._get_po(id)
        if po:
            # TODO : Add dnf code
            value = json.dumps(None)
        else:
            value = json.dumps(None)
        return value



    def _get_group_pkgs(self, grp_id, grp_flt):
        '''
        Get packages for a given grp_id and group filter
        '''
        pkgs = []
        # TODO : Add dnf code
        pkg_ids = self._to_package_id_list(pkgs)
        return pkg_ids

#===============================================================================
# Helper methods
#===============================================================================

    def _get_po_list(self, pkg, fields):

        id = self._get_id(pkg)
        po_list = [id]
        for field in fields:
            if hasattr(pkg,field):
                po_list.append(getattr(pkg,field))
        return po_list

    def _get_id_time_list(self, hist_trans):
        '''
        return a list of (tid, isodate) pairs from a list of yum history transactions
        '''
        result = []
        for ht in hist_trans:
            tm = datetime.fromtimestamp(ht.end_timestamp)
            result.append((ht.tid, tm.isoformat()))
        return result

    def _get_fake_attributes(self,po, attr):
        '''
        Get Fake Attributes, a whey to useful stuff for a package there is not real
        attritbutes to the yum package object.
        :param attr: Fake attribute
        :type attr: string
        '''
        if attr == "action":
            return self._get_action(po)
        elif attr == 'downgrades':
            return self._get_downgrades(po)
        elif attr == 'pkgtags':
            return self._get_pkgtags(po)

    def _get_downgrades(self,pkg):
        pkg_ids = []
        # TODO : Add dnf code
        return pkg_ids

    def _get_pkgtags(self, po):
        '''
        Get pkgtags from a given po
        '''
        # TODO : Add dnf code
        return []



    def _is_installed(self, po):
        '''
        Check if a package is installed
        :param po: package to check for
        '''
        # TODO : Add dnf code
        return False

    def _is_valid_downgrade(self, po, down_po):
        '''
        Check if down_po is a valid downgrade to po
        @param po:
        @param down_po:
        '''
        valid = False
        # TODO : Add dnf code
        return valid
    
    def _to_package_id_list(self, pkgs):
        '''
        return a sorted list of package ids from a list of packages
        if and po is installed, the installed po id will be returned
        :param pkgs:
        '''
        result = set()
        for po in sorted(pkgs):
            result.add(self._get_id(po))
        return result

    def _get_po(self,id):
        ''' find the real package from an package id'''
        n, e, v, r, a, repo_id = id.split(',')
        q = self.base.sack.query()
        if repo_id.startswith('@'): # installed package
            f = q.installed()
            f = f.filter(name=n, version=v, release=r, arch=a)
            if len(f) > 0:
                return f[0]
            else:
                return None
        else:
            f = q.available()
            f = f.filter(name=n, version=v, release=r, arch=a)
            if len(f) > 0:
                return f[0]
            else:
                return None

    def _get_id(self,pkg):
        '''
        convert a yum package obejct to an id string containing (n,e,v,r,a,repo)
        :param pkg:
        '''
        values = [pkg.name, str(pkg.epoch), pkg.version, pkg.release, pkg.arch, pkg.ui_from_repo]
        return ",".join(values)


    def _get_action(self, po):
        '''
        Return the available action for a given pkg_id
        The action is what can be performed on the package
        an installed package will return as 'remove' as action
        an available update will return 'update'
        an available package will return 'install'
        :param po: yum package
        :type po: yum package object
        :return: action (remove, install, update, downgrade, obsolete)
        :rtype: string
        '''
        action = ''
        # TODO : Add dnf code
        return action


    def _get_base(self):
        '''
        Get a Dnf Base object to work with
        '''
        # TODO : Add dnf code
        if not self._base:
            self._base = DnfBase()
        return self._base


    def _reset_base(self):
        '''
        destroy the current YumBase object
        '''
        # TODO : Add dnf code
        del self._base
        self._base = None


    def _setup_watchdog(self):
        '''
        Setup the watchdog to run every second when idle
        '''
        gobject.timeout_add(1000, self._watchdog)

    def _watchdog(self):
        terminate = False
        if self._watchdog_disabled or self._is_working: # is working
            return True
        if not self._lock: # is locked
            if self._watchdog_count > self._timeout_idle:
                terminate = True
        else:
            if self._watchdog_count > self._timeout_locked:
                terminate = True
        if terminate: # shall we quit
            if self._can_quit:
                self._reset_base()
                self.mainloop.quit()
        else:
            self._watchdog_count += 1
            self.logger.debug("Watchdog : %i" % self._watchdog_count )
            return True

class DnfBase(dnf.Base):

    def __init__(self):
        dnf.Base.__init__(self)
        self.setup_cache()
        self.read_all_repos()
        self.progress = MultiFileProgressMeter(fo=sys.stdout)
        self.bar = RepoCallback(fo=sys.stdout)
        self.repos.all.set_progress_bar(self.bar)
        self.fill_sack()

    def setup_cache(self):
        # perform the CLI-specific cachedir tricks
        conf = self.conf
        #conf.read() # Read the conf file from disk
        conf.releasever = '20'
        # conf.cachedir = CACHE_DIR # hardcoded cache dir
        # This is not public API, but we want the same cache as dnf cli
        suffix = dnf.yum.parser.varReplace(dnf.const.CACHEDIR_SUFFIX, conf.yumvar)
        cli_cache = dnf.conf.CliCache(conf.cachedir, suffix)
        conf.cachedir = cli_cache.cachedir
        self._system_cachedir = cli_cache.system_cachedir
        print("cachedir: %s" % conf.cachedir)

    def do_filter(self):
        print("=============== filter name = yumex (available) =====================")
        q = self.sack.query()
        a = q.available()
        a = a.filter(name='yumex')
        for pkg in a: # a only gets evaluated here
            print(pkg)

    def do_query(self):
        print("=============== packages matching yum* =====================")
        subj = dnf.subject.Subject("yum*")
        qa = subj.get_best_query(self.sack, with_provides=False)
        for po in qa:
            print(po)

    def do_install(self):
        print("=============== install btanks =====================")
        if os.getuid() != 0:
            print("You need to run test.py install as root")
            return
        rc = self.install('btanks')
        print("# of packages added : %d" % rc)
        print(self._goal)
        rc = self.resolve()
        to_dnl = []
        for tsi in self.transaction:
            print("   "+tsi.active_history_state+" - "+ str(tsi.active) )
            if tsi.installed:
                to_dnl.append(tsi.installed)
        print(to_dnl)
        print("Downloading Packages")
        print(self.download_packages(to_dnl, self.progress))
        print("Running Transaction")
        disp = TransactionDisplay()
        print(self.do_transaction(display=disp))
        



def _term_width(fd=1):
    return 80


def format_number(number, SI=0, space=' '):
    """Return a human-readable metric-like string representation
    of a number.

    :param number: the number to be converted to a human-readable form
    :param SI: If is 0, this function will use the convention
       that 1 kilobyte = 1024 bytes, otherwise, the convention
       that 1 kilobyte = 1000 bytes will be used
    :param space: string that will be placed between the number
       and the SI prefix
    :return: a human-readable metric-like string representation of
       *number*
    """

    # copied from from urlgrabber.progress
    symbols = [ ' ', # (none)
                'k', # kilo
                'M', # mega
                'G', # giga
                'T', # tera
                'P', # peta
                'E', # exa
                'Z', # zetta
                'Y'] # yotta

    if SI: step = 1000.0
    else: step = 1024.0

    thresh = 999
    depth = 0
    max_depth = len(symbols) - 1

    if number is None:
        number = 0.0

    # we want numbers between 0 and thresh, but don't exceed the length
    # of our list.  In that event, the formatting will be screwed up,
    # but it'll still show the right number.
    while number > thresh and depth < max_depth:
        depth  = depth + 1
        number = number / step

    if isinstance(number, int) or isinstance(number, long):
        fmt = '%i%s%s'
    elif number < 9.95:
        # must use 9.95 for proper sizing.  For example, 9.99 will be
        # rounded to 10.0 with the .1f format string (which is too long)
        fmt = '%.1f%s%s'
    else:
        fmt = '%.0f%s%s'

    return(fmt % (float(number or 0), space, symbols[depth]))

def format_time(seconds, use_hours=0):
    """Return a human-readable string representation of a number
    of seconds.  The string will show seconds, minutes, and
    optionally hours.

    :param seconds: the number of seconds to convert to a
       human-readable form
    :param use_hours: If use_hours is 0, the representation will
       be in minutes and seconds. Otherwise, it will be in hours,
       minutes, and seconds
    :return: a human-readable string representation of *seconds*
    """

    # copied from from urlgrabber.progress
    if seconds is None or seconds < 0:
        if use_hours: return '--:--:--'
        else:         return '--:--'
    elif seconds == float('inf'):
        return 'Infinite'
    else:
        seconds = int(seconds)
        minutes = seconds // 60
        seconds = seconds % 60
        if use_hours:
            hours = minutes // 60
            minutes = minutes % 60
            return '%02i:%02i:%02i' % (hours, minutes, seconds)
        else:
            return '%02i:%02i' % (minutes, seconds)


class MultiFileProgressMeter(object):
    """Multi-file download progress meter"""

    def __init__(self, fo=sys.stderr, update_period=1.0, tick_period=2.0, rate_average=5.0):
        """Creates a new progress meter instance

        update_period -- how often to update the progress bar
        tick_period -- how fast to cycle through concurrent downloads
        rate_average -- time constant for average speed calculation
        """
        self.fo = fo
        self.update_period = update_period
        self.tick_period = tick_period
        self.rate_average = rate_average

    def start(self, total_files, total_size):
        """Initialize the progress meter

        This must be called first to initialize the progress object.
        We should know the number of files and total size in advance.

        total_files -- the number of files to download
        total_size -- the total size of all files
        """
        self.total_files = total_files
        self.total_size = total_size

        # download state
        self.done_files = 0
        self.done_size = 0
        self.state = {}
        self.active = []

        # rate averaging
        self.last_time = 0
        self.last_size = 0
        self.rate = None

    def progress(self, text, total, done):
        """Update the progress display

        text -- the file id
        total -- file total size (mostly ignored)
        done -- how much of this file is already downloaded
        """
        now = time()
        total = int(total)
        done = int(done)

        # update done_size
        if text not in self.state:
            self.state[text] = now, 0
            self.active.append(text)
            print("Starting to download : %s " % text)
        start, old = self.state[text]
        self.state[text] = start, done
        self.done_size += done - old

        # update screen if enough time has elapsed
        if now - self.last_time > self.update_period:
            if total > self.total_size:
                self.total_size = total
            #print("dnl :",text, total, done)
            #self._update(now)

    def _update(self, now):
        if self.last_time:
            delta_time = now - self.last_time
            delta_size = self.done_size - self.last_size
            if delta_time > 0 and delta_size > 0:
                # update the average rate
                rate = delta_size / delta_time
                if self.rate is not None:
                    weight = min(delta_time/self.rate_average, 1)
                    rate = rate*weight + self.rate*(1 - weight)
                self.rate = rate
        self.last_time = now
        self.last_size = self.done_size

        # pick one of the active downloads
        text = self.active[int(now/self.tick_period) % len(self.active)]
        if self.total_files > 1:
            n = '%d' % (self.done_files + 1)
            if len(self.active) > 1:
                n += '-%d' % (self.done_files + len(self.active))
            text = '(%s/%d): %s' % (n, self.total_files, text)

        # average rate, total done size, estimated remaining time
        msg = ' %5sB/s | %5sB %9s ETA\r' % (
            format_number(self.rate) if self.rate else '---  ',
            format_number(self.done_size),
            format_time((self.total_size - self.done_size) / self.rate) if self.rate else '--:--')
        left = _term_width() - len(msg)
        bl = (left - 7)//2
        if bl > 8:
            # use part of the remaining space for progress bar
            pct = self.done_size*100 // self.total_size
            n, p = divmod(self.done_size*bl*2 // self.total_size, 2)
            bar = '='*n + '-'*p
            msg = '%3d%% [%-*s]%s' % (pct, bl, bar, msg)
            left -= bl + 7
        self.fo.write('%-*.*s%s' % (left, left, text, msg))
        self.fo.flush()

    def end(self, text, size, err, status='FAILED'):
        """Display a message that file has finished downloading

        text -- the file id
        size -- the file size
        err -- None if ok, error message otherwise
        status -- Download status (relevant when err != None)
        """
        # update state
        start = now = time()
        if text in self.state:
            start, done = self.state.pop(text)
            self.active.remove(text)
            size -= done
        self.done_files += 1
        self.done_size += size

        if err:
            # the error message, no trimming
            msg = '[%s] %s: ' % (status, text)
            left = _term_width() - len(msg) - 1
            msg = '%s%-*s\n' % (msg, left, err)
        else:
            if self.total_files > 1:
                text = '(%d/%d): %s' % (self.done_files, self.total_files, text)

            # average rate, file size, download time
            tm = max(now - start, 0.001)
            msg = ' %5sB/s | %5sB %9s    \n' % (
                format_number(float(done) / tm),
                format_number(done),
                format_time(tm))
            left = _term_width() - len(msg)
            msg = '%-*.*s%s' % (left, left, text, msg)
        self.fo.write(msg)
        self.fo.flush()

        # now there's a blank line. fill it if possible.
        if self.active:
            self._update(now)

class RepoCallback(MultiFileProgressMeter):
    """Use it as single-file progress, too
    """
    def begin(self, text):
        self.text = text
        MultiFileProgressMeter.start(self, 1, 1)

    def librepo_cb(self, data, total, done):
        MultiFileProgressMeter.progress(self, self.text, total, done)

    def end(self):
        MultiFileProgressMeter.end(self, self.text, 0, None)

class TransactionDisplay(object):

    def __init__(self):
        self.last = -1

    def event(self, package, action, te_current, te_total, ts_current, ts_total):
        """
        @param package: A yum package object or simple string of a package name
        @param action: A constant transaction set state
        @param te_current: current number of bytes processed in the transaction
                           element being processed
        @param te_total: total number of bytes in the transaction element being
                         processed
        @param ts_current: number of processes completed in whole transaction
        @param ts_total: total number of processes in the transaction.
        """
        # this is where a progress bar would be called

        if te_total and te_total > 0:
            percent = int((float(te_current)/te_total)*100.0)
            if percent == 100:
                self.last=-1
                print(action, package, percent, ts_current, ts_total )
            elif percent > self.last and percent % 10 == 0:
                self.last = percent
                print(action, package, percent, ts_current, ts_total )

        else:
            print(action, package)

    def scriptout(self, msgs):
        """msgs is the messages that were output (if any)."""
        if msgs:
            print("ScriptOut: ",msgs)

    def errorlog(self, msg):
        """takes a simple error msg string"""
        print(msg, file=sys.stderr)

    def filelog(self, package, action):
        # check package object type - if it is a string - just output it
        """package is the same as in event() - a package object or simple string
           action is also the same as in event()"""
        pass

    def verify_tsi_package(self, pkg, count, total):
        print("Verifing : %s "% pkg)


      

def doTextLoggerSetup(logroot='dnfdaemon', logfmt='%(asctime)s: %(message)s', loglvl=logging.INFO):
    ''' Setup Python logging  '''
    logger = logging.getLogger(logroot)
    logger.setLevel(loglvl)
    formatter = logging.Formatter(logfmt, "%H:%M:%S")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.propagate = False
    logger.addHandler(handler)


