# Maintainer: Bill Sideris <bill88t@feline.gr>
pkgname=('bakery' 'bakery-gui' 'bakery-tui')
pkgbase="bakery"
pkgver=1.3.2
pkgrel=5
pkgdesc="BredOS Installer"
arch=('any')
url="https://github.com/BredOS/Bakery"
license=('GPL3')
options=('!strip')
source=()
makedepends=('meson' 'glib2')
md5sums=()

prepare() {
        cd "$srcdir"
        mkdir -p "$srcdir/$pkgbase"
        cp -r "$srcdir/../"* "$srcdir/$pkgbase" || true
}

build() {
        cd "$srcdir/$pkgbase/data"
        echo "Compiling gresources.."
        glib-compile-resources org.bredos.bakery.gresource.xml
        cd ..
        meson setup build --prefix=/usr
}

package_bakery() {
        cd "$srcdir/$pkgbase/build"
        depends=('python-pyrunning' 'python-toml' 'python-requests' 'python-pyparted' 'arch-install-scripts' 'bakery-device-tweaks' 'python-yaml' 'appstream-glib' 'archlinux-appstream-data' 'python-bredos-common>=1.8.1')
        DESTDIR="$pkgdir" meson install -q
        rm -r "$pkgdir/usr/share/bakery/bakery-"{gui,tui}".py" \
              "$pkgdir/usr/lib/python3.13/site-packages/bakery/"{gui/,tui/,__pycache__/} \
              "$pkgdir/usr/share/"{icons/,appdata/,applications/,glib-2.0/}
}

package_bakery-gui() {
        cd "$srcdir/$pkgbase/build"
        depends=('bakery' 'python-babel' 'python-pyrunning' 'libadwaita' 'python-psutil')
        DESTDIR="$pkgdir" meson install -q
        rm -r "$pkgdir/usr/share/locale" \
              "$pkgdir/usr/share/bakery/bakery-tui.py" \
              "$pkgdir/usr/share/bakery/data/" \
              "$pkgdir/usr/share/licenses/" \
              "$pkgdir/usr/bin" \
              "$pkgdir/usr/lib/python3.13/site-packages/bakery/"{appstream.py,__init__.py,keyboard.py,network.py,__pycache__,tweaks.py,config.py,install.py,locale.py,packages.py,timezone.py,validate.py,tui/,gui/__pycache__/,iso.py,misc.py,partitioning.py}
}

package_bakery-tui() {
        cd "$srcdir/$pkgbase/build"
        depends=('bakery' 'python-babel' 'python-pyrunning' 'python-psutil')
        DESTDIR="$pkgdir" meson install -q
        rm -r "$pkgdir/usr/share/bakery/bakery-gui.py" \
              "$pkgdir/usr/share/"{appdata/,applications/,bakery/data/,glib-2.0/,icons/,licenses/,locale/} \
              "$pkgdir/usr/bin" \
              "$pkgdir/usr/lib/python3.13/site-packages/bakery/"{appstream.py,__init__.py,keyboard.py,network.py,__pycache__,tweaks.py,config.py,install.py,locale.py,packages.py,timezone.py,validate.py,tui/__pycache__/,gui/,iso.py,misc.py,partitioning.py}

}
