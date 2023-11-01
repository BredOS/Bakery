SHELL = bash

all: help

translations:
	@meson setup build
	@cd build && (ninja bakery-pot || (ninja reconfigure && ninja bakery-pot))

package: translations
	echo "Package make not done"

help:
	@cat makefile_help.txt
