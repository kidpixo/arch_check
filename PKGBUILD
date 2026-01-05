# Maintainer: kidpixo <kidpixo@gmail.com>
pkgname=arch-check
gitname=arch-check
pkgver=0.1.0
pkgrel=1
pkgdesc="Arch Linux system health and disk origin checker CLI"
arch=(any)
url="https://github.com/kidpixo/arch-check"
license=('0BSD')
depends=('python')
makedepends=('python-build' 'python-installer' 'python-wheel' 'python-setuptools')
source=("arch_check.py" "pyproject.toml")
sha256sums=('e4946b71bf9c4007b7e6ed1ff6d307b007dcb37e6a4da973439f64280838920b'
            '918abc64006e948fe94048139e3755042d9b490579632f26f105fee000f5cfd1')

build() {
  cd "$srcdir"
  python -m build --wheel --no-isolation
}

package() {
  cd "$srcdir"
  # Find the built wheel file in dist/ (avoid hardcoded names and glob issues)
  wheel_file=$(ls dist/*.whl 2>/dev/null | head -n1)
  if [ -z "$wheel_file" ]; then
    echo "No wheel found in dist/, aborting"
    return 1
  fi
  python -m installer --destdir="$pkgdir" "$wheel_file"
  install -Dm644 pyproject.toml "$pkgdir/usr/share/$pkgname/pyproject.toml"
  install -Dm644 arch_check.py "$pkgdir/usr/share/$pkgname/arch_check.py"
}
