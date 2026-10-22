PREFIX ?= /usr
SYSCONFDIR ?= /etc
DESTDIR ?=

.PHONY: all deb install uninstall clean help

all: help

help:
	@echo "Chionecast Makefile"
	@echo "Targets:"
	@echo "  deb         - Build Debian (.deb) package for Ubuntu / Debian"
	@echo "  install     - Install directly onto the system"
	@echo "  uninstall   - Remove installed files from system"
	@echo "  clean       - Clean build artifacts"

deb:
	./package_deb.sh

install:
	install -d $(DESTDIR)$(PREFIX)/lib/chionecast
	install -m 755 chione_cli.py $(DESTDIR)$(PREFIX)/lib/chionecast/chione_cli.py
	install -m 644 chione_device.py $(DESTDIR)$(PREFIX)/lib/chionecast/chione_device.py
	install -m 644 display_renderer.py $(DESTDIR)$(PREFIX)/lib/chionecast/display_renderer.py
	install -m 644 system_stats.py $(DESTDIR)$(PREFIX)/lib/chionecast/system_stats.py
	install -m 644 config_manager.py $(DESTDIR)$(PREFIX)/lib/chionecast/config_manager.py
	install -d $(DESTDIR)$(PREFIX)/share/chionecast
	cp -r assets $(DESTDIR)$(PREFIX)/share/chionecast/
	install -d $(DESTDIR)$(PREFIX)/bin
	printf '#!/bin/sh\nexec /usr/bin/python3 $(PREFIX)/lib/chionecast/chione_cli.py "$$@"\n' > $(DESTDIR)$(PREFIX)/bin/chionecast
	chmod 755 $(DESTDIR)$(PREFIX)/bin/chionecast
	install -d $(DESTDIR)/lib/udev/rules.d
	install -m 644 99-gamdias-chione.rules $(DESTDIR)/lib/udev/rules.d/99-gamdias-chione.rules
	install -d $(DESTDIR)$(PREFIX)/lib/systemd/user
	install -m 644 chionecast.service $(DESTDIR)$(PREFIX)/lib/systemd/user/chionecast.service

uninstall:
	rm -f $(DESTDIR)$(PREFIX)/bin/chionecast
	rm -rf $(DESTDIR)$(PREFIX)/lib/chionecast
	rm -f $(DESTDIR)/lib/udev/rules.d/99-gamdias-chione.rules
	rm -f $(DESTDIR)$(PREFIX)/lib/systemd/user/chionecast.service

clean:
	rm -rf build *.deb
