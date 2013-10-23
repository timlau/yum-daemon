'''
A simple example of how to use the yumdaemon client API for python 2 or 3

The example show how to install & remove the '0xFFFF' package

'''
from yumdaemon import YumDaemonClient, AccessDeniedError, YumLockedError, YumDaemonError, YumTransactionError

class MyClient(YumDaemonClient):

    def __init(self):
        YumDaemonClient.__init__(self)

    def do_something(self):
        try:
            self.Lock()
            print("=" * 70)
            print("Install : 0xFFFF")
            print("=" * 70)
            rc, result = self.Install('0xFFFF')
            if rc==2: # OK
                print ("Dependency resolution completed ok")
                self._show_transaction_result(result)
                result = self.RunTransaction()
                print(result)
            elif rc == 0: # Nothing to do (package now found or already installed)
                print("Noting to do")
            else: # Error in Dependency resolution
                print ("Dependency resolution failed")
                print(result)
            print("=" * 70)
            print("Remove : 0xFFFF")
            print("=" * 70)
            rc, result = self.Remove('0xFFFF')
            if rc==2:
                print ("Dependency resolution completed ok")
                self._show_transaction_result(result)
                result = self.RunTransaction()
                print(result)
            elif rc == 0:
                print("Noting to do")
            else:
                print ("Dependency resolution failed")
                print(result)
        except AccessDeniedError as err:
            print("Access Denied : \n\t"+str(err))
        except YumLockedError as err:
            print("Yum Locked : \n\t"+str(err))
        except YumTransactionError as err:
            print("Yum Transaction Error : \n\t"+str(err))
        except YumDaemonError as err:
            print("Error in Yum Backend : \n\t"+str(err))
            print(err)
        finally:
            # always try to Unlock (ignore errors)
            try:
                self.Unlock()
            except:
                pass

    def _fullname(self,id):
        ''' Package fullname  '''
        (n, e, v, r, a, repo_id)  = str(id).split(',')
        if e and e != '0':
            return "%s-%s:%s-%s.%s (%s)" % (n, e, v, r, a, repo_id)
        else:
            return "%s-%s-%s.%s (%s)" % (n, v, r, a, repo_id)

    def _show_transaction_result(self, output):
        for action, pkgs in output:
            print( "  %s" % action)
            for pkg_list in pkgs:
                id, size, obs_list = pkg_list  # (pkg_id, size, list with id's obsoleted by this pkg)
                print ("    --> %-50s : %s" % (self._fullname(id),size))

if __name__ == "__main__":

    cli = MyClient()
    cli.do_something()

