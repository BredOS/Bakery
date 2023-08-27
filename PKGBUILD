# Maintainer: Bill Sideris <bill88t@feline.gr>
pkgname=('bakery' 'bakery-gui')
pkgbase="bredos"
pkgver=0.0.1
pkgrel=1
pkgdesc=""
arch=('any')
_desc="BredOS Installer"
url="https://github.com/BredOS/BredOS-Bakery"
license=('GPL3')
options=('!strip')
source=()
md5sums=()

prepare() {
        cd "$pkgname-$pkgver"
        patch -p1 -i "$srcdir/$pkgname-$pkgver.patch"
}

build() {
        cd "$pkgbase-$pkgver"
        ./configure --prefix=/usr
        make
}

package_pkg1() {
        cd "$pkgbase-$pkgver"
        make DESTDIR="$pkgdir/" install-pkg1
}

package_pkg2() {
        cd "$pkgbase-$pkgver"
        make DESTDIR="$pkgdir/" install-pkg2
}
