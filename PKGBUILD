# Maintainer: Bill Sideris <bill88t@feline.gr>
pkgname=('bakery' 'bakery-gui')
pkgbase="bredos"
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
        install -Dm644 "$srcdir/locale/" "$pkgdir/usr/share/locale/"
        install -Dm644 "$srcdir/Bakery" "$pkgdir/usr/bin/Bakery"
        # install bakery files
        install -Dm644 "$srcdir/bakery.py" "$pkgdir/usr/share/bakery/"
        install -Dm644 "$srcdir/bakery-cli.py" "$pkgdir/usr/share/bakery/"
        # install license
        install -Dm644 "$srcdir/LICENSE" "$pkgdir/usr/share/licenses/bakery/LICENSE"
}

package_bakery-gui() {
        
        install -Dm644 "$srcdir/assets/" "$pkgdir/usr/share/bakery/"
        install -Dm644 "$srcdir/gui.py" "$pkgdir/usr/share/bakery/"

}
