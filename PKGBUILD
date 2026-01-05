# Maintainer: kidpixo <kidpixo@gmail.com>
pkgname=arch-check
pkgver=0.1.0
# upstream repository name (GitHub) — note underscore vs package name
upstream_name=arch_check
pkgrel=1
pkgdesc="Arch Linux system health and disk origin checker CLI"
arch=('any')
url="https://github.com/kidpixo/arch_check"
license=('0BSD')
depends=('python')
makedepends=('python-build' 'python-installer' 'python-wheel' 'python-setuptools')
# Use the GitHub tag release (use upstream_name for the archive filename)
source=("$upstream_name-$pkgver.tar.gz::$url/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('c8fd58ee7fe43292ae153f946b6c1961e6f5ab5551af9955695f40d37424ba64')

build() {
  cd "$upstream_name-$pkgver"
  python -m build --wheel --no-isolation 
}

package() {
  cd "$upstream_name-$pkgver"
  # Find the built wheel file in dist/ and pass it to the installer
  wheel_file=$(ls dist/*.whl 2>/dev/null | head -n1)
  if [ -z "$wheel_file" ]; then
    echo "No wheel found in dist/, aborting"
    return 1
  fi
  python -m installer --destdir="$pkgdir" "$wheel_file"

  # Install the license file (required for 0BSD as it's not in common-licenses)
  install -Dm644 LICENSE -t "$pkgdir/usr/share/licenses/$pkgname/"
}
