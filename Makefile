#see Makefiles in python projects https://krzysztofzuraw.com/blog/2016/makefiles-in-python-projects.html
#TEST_PATH=extensions/
.DEFAULT_GOAL := help

update_hash_srcinfo: ## Update PKGBUILD md5sums for arch_check.py and pyproject.toml (PKGBUILD must exist)
	make update_release_checksum
	makepkg --printsrcinfo > .SRCINFO

# Download the GitHub release tarball (based on fields in `PKGBUILD`), compute
# its sha256, and replace the `sha256sums=` line in `PKGBUILD`.
update_release_checksum: ## Download release tarball and update `sha256sums` in PKGBUILD
	@pkgname=$$(grep '^pkgname=' PKGBUILD | cut -d= -f2 | tr -d '"'); \
	pkgver=$$(grep '^pkgver=' PKGBUILD | cut -d= -f2 | tr -d '"'); \
	url=$$(grep '^url=' PKGBUILD | cut -d= -f2 | tr -d '"'); \
	upstream=$$(grep '^upstream_name=' PKGBUILD | cut -d= -f2 | tr -d '"' || true); \
	if [ -n "$$upstream" ]; then \
		tarball="$$upstream-$$pkgver.tar.gz"; \
	else \
		tarball="$$pkgname-$$pkgver.tar.gz"; \
	fi; \
	echo "Downloading $$url/archive/refs/tags/v$$pkgver.tar.gz -> $$tarball"; \
	curl -fSL -o "$$tarball" "$$url/archive/refs/tags/v$$pkgver.tar.gz" || { echo "download failed"; exit 1; }; \
	# Diagnostics: show file type and size, then verify gzip integrity
	echo "Downloaded $$tarball:"; \
	file "$$tarball" || true; ls -l "$$tarball" || true; \
	# Let updpkgsums compute and write the sha256sums for the local tarball
	echo "Downloaded $$tarball; running updpkgsums to update PKGBUILD"; \
	updpkgsums || { echo "updpkgsums failed"; exit 1; }; \
	# Regenerate .SRCINFO with the updated checksums
	makepkg --printsrcinfo > .SRCINFO; \
	echo "PKGBUILD and .SRCINFO updated with new sha256sums";

pkgbuild: ## Build Arch package using PKGBUILD (PKGBUILD must exist)
	make update_hash_srcinfo
	makepkg -f

clean_build: ## Remove build, dist, *.egg-info, pkg, and src directories
	rm -rf build dist *.egg-info pkg src

makepkg_install: pkgbuild ## Build and install Arch package using PKGBUILD (PKGBUILD must exist)
	makepkg -si

#################################################################################
# Self Documenting Commands                                                     #

help: ## Show help. Only lines with ": ##" will show up!
	@awk -F':[[:space:]]*.*## ' '/^[a-zA-Z0-9_.-]+ *:.*## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
