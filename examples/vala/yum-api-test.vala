[DBus (name = "org.baseurl.YumSystem")]
interface YumSystem : Object {
    public abstract bool lock() throws IOError;
    public abstract bool unlock() throws IOError;
    public abstract int get_version () throws IOError;
    public abstract async string[] get_packages(string pkg_narrow) throws IOError;
    public abstract async string[] get_packages_by_name(string pattern, bool newest_only) throws IOError;
}
[DBus (name = "org.baseurl.YumSession")]
interface YumSession : Object {
    public abstract bool lock() throws IOError;
    public abstract bool unlock() throws IOError;
    public abstract int get_version () throws IOError;
    public abstract async string[] get_packages(string pkg_narrow) throws IOError;
    public abstract async string[] get_packages_by_name(string pattern, bool newest_only) throws IOError;
}

MainLoop main_loop;

async void run_system () {
    string [] packages;
    try {
        YumSystem yum = yield Bus.get_proxy (BusType.SYSTEM,
                                        "org.baseurl.YumSystem",
                                        "/");

        int version = yum.get_version();
        stdout.printf ("================================================================\n");
        stdout.printf ("Testing yumdaemon system service\n");
        stdout.printf ("================================================================\n");
        stdout.printf ("System YumDaemon version %i\n", version);
        bool lock = yum.lock();
        if (lock) {
            packages = yield yum.get_packages("updates");
            foreach (string pkg in packages) {            
                stdout.printf ("package:  %s\n", pkg);            
            }
            packages = yield yum.get_packages_by_name("yum*",true);
            foreach (string pkg in packages) {            
                stdout.printf ("package:  %s\n", pkg);            
            }
            yum.unlock();
        }        
    } catch (IOError e) {
        stderr.printf ("%s\n", e.message);
    }
    main_loop.quit ();
}

async void run_session () {
    string [] packages;
    try {
        YumSession yum = yield Bus.get_proxy (BusType.SESSION,
                                        "org.baseurl.YumSession",
                                        "/");

        int version = yum.get_version();
        stdout.printf ("================================================================\n");
        stdout.printf ("Testing yumdaemon system service\n");
        stdout.printf ("================================================================\n");
        stdout.printf ("Session YumDaemon version %i\n", version);
        bool lock = yum.lock();
        if (lock) {
            packages = yield yum.get_packages("updates");
            foreach (string pkg in packages) {            
                stdout.printf ("package:  %s\n", pkg);            
            }
            packages = yield yum.get_packages_by_name("yum*",true);
            foreach (string pkg in packages) {            
                stdout.printf ("package:  %s\n", pkg);            
            }
            yum.unlock();
        }        
    } catch (IOError e) {
        stderr.printf ("%s\n", e.message);
    }
    main_loop.quit ();
}

int main () {
    run_session();
    main_loop = new MainLoop (null, false);
    main_loop.run ();
    run_system();
    main_loop = new MainLoop (null, false);
    main_loop.run ();
    return 0;
}

