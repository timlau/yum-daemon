#include 	<glib.h>
#include	<glib-object.h>
#include	<dbus/dbus.h>
#include	<dbus/dbus-glib.h>

#define 	YUM_SERVICE_NAME   "org.baseurl.Yum"
#define 	YUM_INTERFACE	"org.baseurl.Yum.Interface"
#define 	YUM_OBJECT_PATH	"/"

gboolean yum_dbus_init();
gboolean yum_dbus_translate(const gchar*, gboolean, gchar*);

static DBusGConnection *conn = NULL;
static DBusGProxy *proxy = NULL;
static gboolean *version = NULL;
static gboolean *locked = NULL;
char **package_list;
char **package_list_ptr;


gboolean yum_dbus_init()
{
	GError *error = NULL;
	
	conn = dbus_g_bus_get(DBUS_BUS_SYSTEM, &error);
	
	if (conn == NULL) {
		g_warning("Error %s\n", error->message);
        g_error_free(error);
		return FALSE;
	}
	else
	{
		g_debug("conn object is %d\n", conn);
	}

	proxy = dbus_g_proxy_new_for_name_owner(conn,
						YUM_SERVICE_NAME,
						YUM_OBJECT_PATH,
						YUM_INTERFACE,
					        &error);
    dbus_g_proxy_set_default_timeout(proxy, 60000);		
	g_debug("proxy %d\n", proxy);
									
	if (proxy == NULL || error != NULL)
	{
		g_warning("Cannot connect to the yum service : %s\n", error->message);
		g_error_free(error);
		return FALSE;
	}
	else
	{
		return TRUE;
	}
	
}

gboolean yum_dbus_get_version()
{
		
	GError *error = NULL;
	dbus_g_proxy_call(proxy, "GetVersion", &error, 
					G_TYPE_INVALID,
					G_TYPE_INT,
					&version,
					G_TYPE_INVALID);
									
	
	if (error) 
        {
    		g_warning("Error : %s\n", error->message);
	        g_error_free(error);
            return FALSE;
        }
	else
        {
	        return TRUE;
        }
}

gboolean yum_dbus_lock()
{
		
	GError *error = NULL;
	dbus_g_proxy_call(proxy, "Lock", &error, 
					G_TYPE_INVALID,
					G_TYPE_BOOLEAN,
					&locked,
					G_TYPE_INVALID);
									
	
	if (error) 
        {
    		g_warning("Error : %s\n", error->message);
	        g_error_free(error);
            return FALSE;
        }
	else
        {
            if (locked) {
                g_print("Yum is now locked\n");
                return TRUE;
            } else {
                g_print("Yum is locked by another application\n");
                return FALSE;
            }
        }
}

gboolean yum_dbus_unlock()
{
		
	GError *error = NULL;
    gboolean *unlocked = NULL;    

	dbus_g_proxy_call(proxy, "Unlock", &error, 
					G_TYPE_INVALID,
					G_TYPE_BOOLEAN,
					&unlocked,
					G_TYPE_INVALID);
									
	
	if (error) 
        {
    		g_warning("Error : %s\n", error->message);
	        g_error_free(error);
            return FALSE;
        }
	else
        {
            if (unlocked) {
                g_print("Yum is unlocked\n");
                locked = FALSE;
                return TRUE;
            } else {
      	        return FALSE;
            }
        }
}

gboolean yum_dbus_get_packages_by_name(gchar* pattern, gboolean use_newest)
{
		
	GError *error = NULL;

    g_print("Getting packages matching : %s \n", pattern);
	dbus_g_proxy_call(proxy, "GetPackagesByName", &error, 
					G_TYPE_STRING, pattern,
					G_TYPE_BOOLEAN, use_newest, 
					G_TYPE_INVALID,
					G_TYPE_STRV, &package_list,
					G_TYPE_INVALID);
									
	
	if (error) 
        {
    		g_warning("Error : %s\n", error->message);
	        g_error_free(error);
            yum_dbus_unlock();
            return FALSE;
        }
	else
        {
            g_print("Got packages\n");
            return TRUE;
        }
}

int main(int argc, char** argv)
{
	g_type_init();	
	
	if (yum_dbus_init() == FALSE)
		g_error("yum_dbus_init, unable to connect yum DBUS service");
	else
	{
		yum_dbus_get_version();	
		g_print("version is : %i\n", version);
        if (yum_dbus_lock() == TRUE) {
    		g_print("Ready for some action\n");    
            if (yum_dbus_get_packages_by_name("yum*", TRUE)) {
                g_print("Packages:\n");
                g_print("==========================:\n");
                for (package_list_ptr = package_list; *package_list_ptr; package_list_ptr++)
                {
                  g_print ("  %s\n", *package_list_ptr);
                }
                g_strfreev (package_list);
            }
            yum_dbus_unlock();
        }
		g_object_unref(proxy);
	}	
	return 0;
}

