#see Makefiles in python projects https://krzysztofzuraw.com/blog/2016/makefiles-in-python-projects.html
#TEST_PATH=extensions/
.DEFAULT_GOAL := help

update_md5hash_srcinfo: ## Update PKGBUILD md5sums for arch_check.py and pyproject.toml (PKGBUILD must exist)
	bash update_md5hash.sh
	makepkg --printsrcinfo > .SRCINFO

pkgbuild: ## Build Arch package using PKGBUILD (PKGBUILD must exist)
	make update_md5hash
	makepkg -f

clean_build: ## Remove build, dist, *.egg-info, pkg, and src directories
	rm -rf build dist *.egg-info pkg src

#################################################################################
# Self Documenting Commands                                                     #

help: ## Show help. Only lines with ": ##" will show up!
	@awk -F':[[:space:]]*.*## ' '/^[a-zA-Z0-9_.-]+ *:.*## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
