[DBus (name = "org.baseurl.Yum.Interface")]
interface Yum : Object {
    public abstract bool lock() throws IOError;
    public abstract bool unlock() throws IOError;
    public abstract int get_version () throws IOError;
    public abstract string[] get_packages(string pkg_narrow) throws IOError;
    public abstract string[] get_packages_by_name(string pattern, bool newest_only) throws IOError;
}

int main () {
    string [] packages;
    try {
        Yum yum = Bus.get_proxy_sync (BusType.SYSTEM,
                                        "org.baseurl.Yum",
                                        "/");

        int  version = yum.get_version();
        stdout.printf ("Yum Daemon version %i\n", version);
        if (yum.lock()) {
            packages = yum.get_packages("updates");
            foreach (string pkg in packages) {            
                stdout.printf ("package:  %s\n", pkg);            
            }
            packages = yum.get_packages_by_name("yum*",true);
            foreach (string pkg in packages) {            
                stdout.printf ("package:  %s\n", pkg);            
            }
            yum.unlock();
        }        
//        var loop = new MainLoop ();
//        loop.run ();

    } catch (IOError e) {
        stderr.printf ("%s\n", e.message);
        return 1;
    }

    return 0;
}

