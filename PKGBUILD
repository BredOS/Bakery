# Maintainer: Bill Sideris <bill88t@feline.gr>
pkgname=('bakery' 'bakery-gui')
pkgbase="bakery"
pkgver=1.1.0
pkgrel=8
pkgdesc="BredOS Installer"
arch=('any')
url="https://github.com/BredOS/Bakery"
license=('GPL3')
options=('!strip')
source=()
makedepends=('meson')
md5sums=()

prepare() {
        cd "$srcdir"
        mkdir -pv "$srcdir/$pkgbase"
        cp -rv "$srcdir/../"* "$srcdir/$pkgbase" || true
}

build() {
        cd "$srcdir/$pkgbase"
        meson setup build --prefix=/usr
}

package_bakery() {
        cd "$srcdir/$pkgbase/build"
        depends=('python-pyrunning' 'python-toml' 'python-requests' 'python-pyparted' 'arch-install-scripts')
        DESTDIR="$pkgdir" meson install
        rm -rf "$pkgdir/usr/share/bakery/data/"*.ui
        rm -rf "$pkgdir/usr/share/bakery/data/"*.css
        rm -rf "$pkgdir/usr/share/bakery/bakery-gui.py"
        rm -rf "$pkgdir/usr/share/"{icons/,appdata/,applications/,glib-2.0/}
}

package_bakery-gui() {
        cd "$srcdir/$pkgbase/build"
        depends=('bakery' 'python-babel' 'python-pyrunning' 'libadwaita')
        DESTDIR="$pkgdir" meson install
        rm -rf "$pkgdir/usr/share/locale"
        rm -rf "$pkgdir/usr/share/bakery/"{bakery-tui.py,bakery.py,config.py}
        rm -rf "$pkgdir/usr/share/licenses/"
        rm -rf "$pkgdir/usr/bin"
}
