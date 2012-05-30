#!/usr/bin/python3
'''
A simple example of how to use the yumdaemon client API for python 3 

This example show how to get available updates (incl. summary & size) and
how to search for packages where 'yum' is in the name.
'''
from yumdaemon3 import YumDaemonClient, AccessDeniedError, YumLockedError, YumDaemonError, YumTransactionError

class MyClient(YumDaemonClient):

    def __init(self):
        YumDaemonClient.__init__(self)
        
    def do_something(self):
        try:
            self.Lock()
            print("=" * 70)
            print("Getting Updates")
            print("=" * 70)
            result = self.GetPackageObjects('updates',['summary','size'])
            for (pkg_id,summary,size) in result:
                print("%s\n\tsummary : %s\n\tsize : %s" % (self._fullname(pkg_id),summary,size))
            print("=" * 70)
            print("Search : yum ")
            print("=" * 70)
            result = self.Search(["name"],["yum"], True)
            for id in result:
                print(" --> %s" % self._fullname(id))
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

                    
    def on_UpdateProgress(self,name,frac,fread,ftime):
        pass

    def on_TransactionEvent(self,event):
        pass

    def on_RPMProgress(self, package, action, te_current, te_total, ts_current, ts_total):
        pass

if __name__ == "__main__":
    
    cli = MyClient()
    cli.do_something()

