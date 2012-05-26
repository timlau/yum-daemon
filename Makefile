PKGDIR = /usr/share/yum-daemon
ORG_NAME = org.baseurl.Yum
SUBDIRS = client/python2 client/python3
all: subdirs
	
subdirs:
	for d in $(SUBDIRS); do make -C $$d; [ $$? = 0 ] || exit 1 ; done

clean:
	@rm -fv *~ *.tar.gz *.list *.lang 
	for d in $(SUBDIRS); do make -C $$d clean ; done

install:
	mkdir -p $(DESTDIR)/usr/share/dbus-1/system-services
	mkdir -p $(DESTDIR)/etc/dbus-1/system.d
	mkdir -p $(DESTDIR)/usr/share/polkit-1/actions
	mkdir -p $(DESTDIR)$(DESTDIR)/$(PKGDIR)
	install -m644 dbus/$(ORG_NAME).service $(DESTDIR)/usr/share/dbus-1/system-services/.				
	install -m644 dbus/$(ORG_NAME).conf $(DESTDIR)/etc/dbus-1/system.d/.				
	install -m644 policykit1/$(ORG_NAME).policy $(DESTDIR)/usr/share/polkit-1/actions/.				
	install -m644 server/daemon.py $(DESTDIR)/$(PKGDIR)/.
	install -m755 server/yum-daemon $(DESTDIR)/$(PKGDIR)/.
	for d in $(SUBDIRS); do make DESTDIR=`cd $(DESTDIR); pwd` -C $$d install; [ $$? = 0 ] || exit 1; done

uninstall:
	rm -f $(DESTDIR)/usr/share/dbus-1/system-services/$(ORG_NAME).*
	rm -f $(DESTDIR)/etc/dbus-1/system.d/$(ORG_NAME).*				
	rm -r $(DESTDIR)/usr/share/polkit-1/actions/$(ORG_NAME).*		
	rm -rf $(DESTDIR)/$(PKGDIR)/
	
clean:
	@rm *.pyc *.pyo	
	
# Run as root or you will get a password prompt for each test method :)
test-verbose: FORCE
	@nosetests -v -s test/


# Run as root or you will get a password prompt for each test method :)
test: FORCE
	@nosetests -v test/

# Run as root or you will get a password prompt for each test method :)
test-devel: FORCE
	@nosetests -v -s test/unit-devel.py


instdeps:
	sudo yum install python-nose	

FORCE:
    
