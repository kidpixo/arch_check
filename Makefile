#see Makefiles in python projects https://krzysztofzuraw.com/blog/2016/makefiles-in-python-projects.html
#TEST_PATH=extensions/
.DEFAULT_GOAL := help

makepkg_install: pkgbuild ## Build and install Arch package using PKGBUILD (PKGBUILD must exist)
	makepkg -si

#################################################################################
# Self Documenting Commands                                                     #

help: ## Show help. Only lines with ": ##" will show up!
	@awk -F':[[:space:]]*.*## ' '/^[a-zA-Z0-9_.-]+ *:.*## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
