PKGNAME = yumdaemon
PKGDIR = /usr/share/$(PKGNAME)
ORG_NAME = org.baseurl.Yum
SUBDIRS = client/yumdaemon2 client/yumdaemon3
VERSION=$(shell awk '/Version:/ { print $$2 }' ${PKGNAME}.spec)
PYTHON=python
GITDATE=git$(shell date +%Y%m%d)
VER_REGEX=\(^Version:\s*[0-9]*\.[0-9]*\.\)\(.*\)
BUMPED_MINOR=${shell VN=`cat ${PKGNAME}.spec | grep Version| sed  's/${VER_REGEX}/\2/'`; echo $$(($$VN + 1))}
NEW_VER=${shell cat ${PKGNAME}.spec | grep Version| sed  's/\(^Version:\s*\)\([0-9]*\.[0-9]*\.\)\(.*\)/\2${BUMPED_MINOR}/'}
NEW_REL=0.1.${GITDATE}
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
	mkdir -p $(DESTDIR)/$(PKGDIR)
	install -m644 dbus/$(ORG_NAME).service $(DESTDIR)/usr/share/dbus-1/system-services/.				
	install -m644 dbus/$(ORG_NAME).conf $(DESTDIR)/etc/dbus-1/system.d/.				
	install -m644 policykit1/$(ORG_NAME).policy $(DESTDIR)/usr/share/polkit-1/actions/.				
	install -m755 yumdaemon/yumdaemon $(DESTDIR)/$(PKGDIR)/.
	for d in $(SUBDIRS); do make DESTDIR=$(DESTDIR) -C $$d install; [ $$? = 0 ] || exit 1; done

uninstall:
	rm -f $(DESTDIR)/usr/share/dbus-1/system-services/$(ORG_NAME).*
	rm -f $(DESTDIR)/etc/dbus-1/system.d/$(ORG_NAME).*				
	rm -r $(DESTDIR)/usr/share/polkit-1/actions/$(ORG_NAME).*		
	rm -rf $(DESTDIR)/$(PKGDIR)/

selinux:
	@$(MAKE) install
	semanage fcontext -a -t rpm_exec_t $(DESTDIR)/$(PKGDIR)/yumdaemon
	restorecon $(DESTDIR)/$(PKGDIR)/yumdaemon
	

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

archive:
	@rm -rf ${PKGNAME}-${VERSION}.tar.gz
	@git archive --format=tar --prefix=$(PKGNAME)-$(VERSION)/ HEAD | gzip -9v >${PKGNAME}-$(VERSION).tar.gz
	@cp ${PKGNAME}-$(VERSION).tar.gz $(shell rpm -E '%_sourcedir')
	@rm -rf ${PKGNAME}-${VERSION}.tar.gz
	@echo "The archive is in ${PKGNAME}-$(VERSION).tar.gz"
	
# needs perl-TimeDate for git2cl
changelog:
	@git log --pretty --numstat --summary --after=2008-10-22 | tools/git2cl > ChangeLog
	
upload: FORCE
	@scp ~/rpmbuild/SOURCES/${PKGNAME}-${VERSION}.tar.gz yum-extender.org:public_html/dnl/${PKGNAME}/source/.
	
release:
	@git commit -a -m "bumped version to $(VERSION)"
	@git push
	@git tag -f -m "Added ${PKGNAME}-${VERSION} release tag" ${PKGNAME}-${VERSION}
	@git push --tags origin
	@$(MAKE) archive
	@$(MAKE) upload

test-cleanup:	
	@rm -rf ${PKGNAME}-${VERSION}.test.tar.gz
	@echo "Cleanup the git release-test local branch"
	@git checkout -f
	@git checkout master
	@git branch -D release-test

show-vars:
	@echo ${GITDATE}
	@echo ${BUMPED_MINOR}
	@echo ${NEW_VER}-${NEW_REL}
	
test-release:
	@git checkout -b release-test
	# +1 Minor version and add 0.1-gitYYYYMMDD release
	@cat ${PKGNAME}.spec | sed  -e 's/${VER_REGEX}/\1${BUMPED_MINOR}/' -e 's/\(^Release:\s*\)\([0-9]*\)\(.*\)./\10.1.${GITDATE}%{?dist}/' > ${PKGNAME}-test.spec ; mv ${PKGNAME}-test.spec ${PKGNAME}.spec
	@git commit -a -m "bumped ${PKGNAME} version ${NEW_VER}-${NEW_REL}"
	# Make Changelog
	@git log --pretty --numstat --summary | ./tools/git2cl > ChangeLog
	@git commit -a -m "updated ChangeLog"
		# Make archive
	@rm -rf ${PKGNAME}-${NEW_VER}.tar.gz
	@git archive --format=tar --prefix=$(PKGNAME)-$(NEW_VER)/ HEAD | gzip -9v >${PKGNAME}-$(NEW_VER).tar.gz
	# Build RPMS
	@rpmdev-wipetree
	@rpmbuild -ta ${PKGNAME}-${NEW_VER}.tar.gz
	@$(MAKE) test-cleanup
	
rpm:
	@$(MAKE) archive
	@rpmbuild -ba ${PKGNAME}.spec
	
test-builds:
	@$(MAKE) test-release
	@ssh timlau.fedorapeople.org rm -f public_html/files/${PKGNAME}/*
	@scp ${PKGNAME}-${NEW_VER}.tar.gz timlau.fedorapeople.org:public_html/files/${PKGNAME}/${PKGNAME}-${NEW_VER}-${GITDATE}.tar.gz
	@scp ~/rpmbuild/RPMS/noarch/${PKGNAME}-${NEW_VER}*.rpm timlau.fedorapeople.org:public_html/files/${PKGNAME}/.
	@scp ~/rpmbuild/RPMS/noarch/python-${PKGNAME}-${NEW_VER}*.rpm timlau.fedorapeople.org:public_html/files/${PKGNAME}/.
	@scp ~/rpmbuild/RPMS/noarch/python3-${PKGNAME}-${NEW_VER}*.rpm timlau.fedorapeople.org:public_html/files/${PKGNAME}/.
	@scp ~/rpmbuild/SRPMS/${PKGNAME}-${NEW_VER}*.rpm timlau.fedorapeople.org:public_html/files/${PKGNAME}/.

get-builddeps:
	yum install perl-TimeDate gettext intltool rpmdevtools python-devel python3-devel

FORCE:
	
