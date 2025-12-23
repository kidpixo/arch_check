# Maintainer: kidpixo <kidpixo@gmail.com>
pkgname=arch-check
gitname=arch-check
pkgver=1.0.0
pkgrel=1
pkgdesc="Arch Linux system health and disk origin checker CLI"
arch=(any)
url="https://github.com/kidpixo/arch-check"
license=('0BSD')
depends=('python')
makedepends=('python-build' 'python-installer' 'python-wheel' 'python-setuptools')
source=("arch_check.py" "pyproject.toml")
sha256sums=('65a694cbc1264cee693802d85d5fdf2b20cf05bfb1895e48bb30e8310ed46b6c'
            'c7b09c9af408036d3aa2ee7e19fbf009f90fd14e05073434bd21d5922d2930d4')

build() {
  cd "$srcdir"
  python -m build --wheel --no-isolation
}

package() {
  cd "$srcdir"
  python -m installer --destdir="$pkgdir" dist/*.whl
  install -Dm644 pyproject.toml "$pkgdir/usr/share/$pkgname/pyproject.toml"
  install -Dm644 arch_check.py "$pkgdir/usr/share/$pkgname/arch_check.py"
}
