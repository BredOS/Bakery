# Maintainer: Bill Sideris <bill88t@feline.gr>
pkgname=('bakery' 'bakery-gui' 'bakery-tui')
pkgbase="bakery"
pkgver=1.2.0
pkgrel=1
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
        depends=('python-pyrunning' 'python-toml' 'python-requests' 'python-pyparted' 'arch-install-scripts' 'bakery-device-tweaks' 'python-yaml')
        DESTDIR="$pkgdir" meson install
        rm -rf "$pkgdir/usr/share/bakery/data/"*.ui
        rm -rf "$pkgdir/usr/share/bakery/data/"*.css
        rm -rf "$pkgdir/usr/share/bakery/bakery-gui.py"
        rm -rf "$pkgdir/usr/share/"{icons/,appdata/,applications/,glib-2.0/}
}

package_bakery-gui() {
        cd "$srcdir/$pkgbase/build"
        depends=('bakery' 'python-babel' 'python-pyrunning' 'libadwaita' 'python-psutil')
        DESTDIR="$pkgdir" meson install
        rm -rf "$pkgdir/usr/share/locale"
        rm -rf "$pkgdir/usr/share/bakery/"{bakery-tui.py,bakery.py,config.py}
        rm -rf "$pkgdir/usr/share/licenses/"
        rm -rf "$pkgdir/usr/bin"
}

package_bakery-tui() {
        cd "$srcdir/$pkgbase/build"
        depends=('bakery' 'python-babel' 'python-pyrunning' 'python-psutil')
        DESTDIR="$pkgdir" meson install
        rm -rf "$pkgdir/usr/share/locale"
        rm -rf "$pkgdir/usr/share/bakery/"{bakery-gui.py,bakery.py,config.py}
        rm -rf "$pkgdir/usr/share/licenses/"
        rm -rf "$pkgdir/usr/bin"
}
