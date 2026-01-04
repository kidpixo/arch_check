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
sha256sums=('a53bb2565438544b0a61052c8e1abfec0de1a3c32702cf2683a6d8c33ef98d9e'
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
