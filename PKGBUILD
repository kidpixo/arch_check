# Maintainer: kidpixo <your@email.com>
pkgname=arch_check
gitname=arch-check
pkgver=1.0.0
pkgrel=1
pkgdesc="Arch Linux system health and disk origin checker CLI"
arch=(any)
url="https://github.com/kidpixo/arch-check"
license=('MIT')
depends=('python')
makedepends=('python-build' 'python-installer' 'python-wheel' 'python-setuptools')
source=("arch_check.py" "pyproject.toml")
md5sums=('5e7a064e0917ca23797efa577e4a8056' '7bdec62ca089d089b20c62cf01ffb98f')

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
