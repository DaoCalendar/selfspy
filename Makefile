build:
	@echo "Nothing to build. Only install. Destination is: " $(DESTDIR)

install:
	mkdir -p $(DESTDIR)/var/lib/selfspy
	install selfspy/*.py $(DESTDIR)/var/lib/selfspy
#mkdir -p ~/.selfspy
	ln -s $(DESTDIR)/var/lib/selfspy/__init__.py $(DESTDIR)/usr/local/bin/selfspy
	ln -s $(DESTDIR)/var/lib/selfspy/stats.py $(DESTDIR)/usr/local/bin/selfstats
