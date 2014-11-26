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

# The name of the package as it should be installed
PKGNAME = featherweight



.PHONY: default
default: info

.PHONY: all
all: doc


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



.PHONY: clean
clean:
	-rm -r bin obj
