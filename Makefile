# Copyright © 2013, 2014  Mattias Andrée (maandree@member.fsf.org)
# 
# Copying and distribution of this file, with or without modification,
# are permitted in any medium without royalty provided the copyright
# notice and this notice are preserved.  This file is offered as-is,
# without any warranty.
# 
# [GNU All Permissive License]


# The package path prefix, if you want to install to another root, set DESTDIR to that root
PREFIX = /usr
# The command path excluding prefix
BIN = /bin
# The resource path excluding prefix
DATA = /share
# The command path including prefix
BINDIR = $(PREFIX)$(BIN)
# The resource path including prefix
DATADIR = $(PREFIX)$(DATA)
# The generic documentation path including prefix
DOCDIR = $(DATADIR)/doc
# The man page documentation path including prefix
MANDIR = $(DATADIR)/man
# The info manual documentation path including prefix
INFODIR = $(DATADIR)/info
# The license base path including prefix
LICENSEDIR = $(DATADIR)/licenses

# Python 3 command to use in shebangs
SHEBANG = /usr/bin/env python3
# The name of the package as it should be installed
PKGNAME = featherweight
# The name of the command as it should be installed
COMMAND = featherweight

# Python source files
SRC = __main__ common feeds flocker parser trees updater



.PHONY: default
default: command info

.PHONY: all
all: command doc


.PHONY: command
command: bin/featherweight

bin/featherweight: obj/featherweight.zip
	@mkdir -p bin
	echo '#!$(SHEBANG)' > $@
	cat $< >> $@
	chmod a+x $@

obj/featherweight.zip: compiled optimised $(foreach F,$(SRC),src/$(F).py)
	@mkdir -p obj
	cd src && zip ../$@ $(foreach F,$(SRC),$(F).py)

.PHONY: compiled
compiled: $(foreach M,$(SRC),src/__pycache__/$(M).cpython-$(PY_VER).pyc)

.PHONY: optimised
optimised: $(foreach M,$(SRC),src/__pycache__/$(M).cpython-$(PY_VER).pyo)

src/__pycache__/%.cpython-$(PY_VER).pyc: src/%.py
	python -m compileall $<

src/__pycache__/%.cpython-$(PY_VER).pyo: src/%.py
	python -OO -m compileall $<



.PHONY: doc
doc: info pdf dvi ps

.PHONY: info
info: bin/featherweight.info
bin/%.info: info/%.texinfo info/fdl.texinfo
	@mkdir -p obj bin
	cd obj ; makeinfo ../$<
	mv obj/$*.info bin/$*.info

.PHONY: pdf
pdf: bin/featherweight.pdf
bin/%.pdf: info/%.texinfo info/fdl.texinfo
	@mkdir -p obj bin
	cd obj ; yes X | texi2pdf ../$<
	mv obj/$*.pdf bin/$*.pdf

.PHONY: dvi
dvi: bin/featherweight.dvi
bin/%.dvi: info/%.texinfo info/fdl.texinfo
	@mkdir -p obj bin
	cd obj ; yes X | $(TEXI2DVI) ../$<
	mv obj/$*.dvi bin/$*.dvi

.PHONY: ps
ps: bin/featherweight.ps
bin/%.ps: info/%.texinfo info/fdl.texinfo
	@mkdir -p obj bin
	cd obj ; yes X | texi2pdf --ps ../$<
	mv obj/$*.ps bin/$*.ps



.PHONY: install
install: install-base install-info

.PHONY: install
install-all: install-base install-doc

.PHONY: install-base
install-base: install-command install-copyright


.PHONY: install-command
install-command: bin/featherweight
	install -dm755 -- "$(DESTDIR)$(BINDIR)"
	install -m755 $< -- "$(DESTDIR)$(BINDIR)/$(COMMAND)"


.PHONY: install-copyright
install-copyright: install-copying install-license

.PHONY: install-copying
install-copying:
	install -dm755 -- "$(DESTDIR)$(LICENSEDIR)/$(PKGNAME)"
	install -m644 COPYING -- "$(DESTDIR)$(LICENSEDIR)/$(PKGNAME)"

.PHONY: install-license
install-license:
	install -dm755 -- "$(DESTDIR)$(LICENSEDIR)/$(PKGNAME)"
	install -m644 LICENSE -- "$(DESTDIR)$(LICENSEDIR)/$(PKGNAME)"


.PHONY: install-doc
install-doc: install-info install-pdf install-ps install-dvi

.PHONY: install-info
install-info: featherweight.info
	install -dm755 -- "$(DESTDIR)$(INFODIR)"
	install -m644 $< -- "$(DESTDIR)$(INFODIR)/$(PKGNAME).info"

.PHONY: install-pdf
install-pdf: featherweight.pdf
	install -dm755 -- "$(DESTDIR)$(DOCDIR)"
	install -m644 $< -- "$(DESTDIR)$(DOCDIR)/$(PKGNAME).pdf"

.PHONY: install-ps
install-ps: featherweight.ps
	install -dm755 -- "$(DESTDIR)$(DOCDIR)"
	install -m644 $< -- "$(DESTDIR)$(DOCDIR)/$(PKGNAME).ps"

.PHONY: install-dvi
install-dvi: featherweight.dvi
	install -dm755 -- "$(DESTDIR)$(DOCDIR)"
	install -m644 $< -- "$(DESTDIR)$(DOCDIR)/$(PKGNAME).dvi"



.PHONY: uninstall
uninstall:
	-rm -- "$(DESTDIR)$(BINDIR)/$(COMMAND)"
	-rm -- "$(DESTDIR)$(LICENSEDIR)/$(PKGNAME)/COPYING"
	-rm -- "$(DESTDIR)$(LICENSEDIR)/$(PKGNAME)/LICENSE"
	-rmdir -- "$(DESTDIR)$(DOCDIR)/$(PKGNAME)/examples"
	-rmdir -- "$(DESTDIR)$(DOCDIR)/$(PKGNAME)"
	-rm -- "$(DESTDIR)$(INFODIR)/$(PKGNAME).info"
	-rm -- "$(DESTDIR)$(DOCDIR)/$(PKGNAME).pdf"
	-rm -- "$(DESTDIR)$(DOCDIR)/$(PKGNAME).ps"
	-rm -- "$(DESTDIR)$(DOCDIR)/$(PKGNAME).dvi"



.PHONY: clean
clean:
	-rm -r bin obj

