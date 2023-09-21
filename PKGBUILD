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
source=(git+https://github.com/BredOS/Bakery.git#branch=gui)
md5sums=('SKIP')

build() {
        cd "$srcdir/$pkgbase"
        meson build --prefix=/usr
}

package_bakery() {
        cd "$srcdir/$pkgbase/build"
        DESTDIR="$pkgdir" meson install
}

package_bakery-gui() {
        mkdir -pv "$pkgdir/usr/share/bakery/assets/"
        mkdir -pv "$pkgdir/usr/bin/"
        install -Dm644 "$srcdir/Bakery/assets/"* "$pkgdir/usr/share/bakery/assets/"
        install -Dm644 "$srcdir/Bakery/gui.py" "$pkgdir/usr/share/bakery/"

}
