# Maintainer: Bill Sideris <bill88t@feline.gr>
pkgname=('bakery' 'bakery-gui')
pkgbase="bakery"
pkgver=0.0.1
pkgrel=1
pkgdesc="BredOS Installer"
arch=('any')
url="https://github.com/BredOS/Bakery"
license=('GPL3')
options=('!strip')
# branch=gui
source=()
md5sums=()

prepare() {
        cd "$srcdir"
        mkdir -pv "$srcdir/$pkgbase"
        cp -rv "$srcdir/../"* "$srcdir/$pkgbase" || true
}

build() {
        cd "$srcdir/$pkgbase"
        meson build --prefix=/usr
}

package_bakery() {
        cd "$srcdir/$pkgbase/build"
        DESTDIR="$pkgdir" meson install
        rm -rf "$pkgdir/usr/share/bakery/data/"*.ui
        rm -rf "$pkgdir/usr/share/bakery/bakery-gui.py"
        rm -rf "$pkgdir/usr/share/"{icons/,appdata/,applications/}
}

package_bakery-gui() {
        cd "$srcdir/$pkgbase/build"
        DESTDIR="$pkgdir" meson install
        rm -rf "$pkgdir/usr/share/bakery/"{bakery-cli.py,bakery.py,config.py}
        rm -rf "$pkgdir/usr/share/licenses/"
        rm -rf "$pkgdir/usr/bin"
}
