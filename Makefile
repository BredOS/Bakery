SHELL = bash

all: help

translations:
	@meson setup build
	@cd build && (ninja bakery-update-po || (ninja reconfigure && ninja bakery-update-po))

package: translations
	echo "Package make not done"

help:
	@cat makefile_help.txt
