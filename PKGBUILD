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

package_bakery() {
        # install locale files
        mkdir -pv "$pkgdir/usr/share/locale/"
        mkdir -pv "$pkgdir/usr/share/licenses/bakery/"
        mkdir -pv "$pkgdir/usr/share/bakery/"
        mkdir -pv "$pkgdir/usr/bin/"
        cp -rv "$srcdir/Bakery/locale/"* "$pkgdir/usr/share/locale/"
        install -Dm644 "$srcdir/Bakery/Bakery" "$pkgdir/usr/bin/Bakery"
        # install bakery filess
        install -Dm644 "$srcdir/Bakery/bakery.py" "$pkgdir/usr/share/bakery/"
        install -Dm644 "$srcdir/Bakery/bakery-cli.py" "$pkgdir/usr/share/bakery/"
        # install license
        install -Dm644 "$srcdir/Bakery/LICENSE" "$pkgdir/usr/share/licenses/bakery/LICENSE"
}

package_bakery-gui() {
        mkdir -pv "$pkgdir/usr/share/bakery/assets/"
        mkdir -pv "$pkgdir/usr/bin/"
        install -Dm644 "$srcdir/Bakery/assets/"* "$pkgdir/usr/share/bakery/assets/"
        install -Dm644 "$srcdir/Bakery/gui.py" "$pkgdir/usr/share/bakery/"

}
