project('bakery',
          version: '1.1.0',
    meson_version: '>= 0.62.0',
  default_options: [ 'warning_level=2', 'werror=false', ],
)
py = import('python').find_installation()
i18n = import('i18n')

install_data('bakery-tui.py', install_dir: join_paths(get_option('datadir'), 'bakery'))
install_data('bakery-gui.py', install_dir: join_paths(get_option('datadir'), 'bakery'))
# install license
install_data('LICENSE', install_dir: join_paths(get_option('datadir'), 'licenses/bakery'))
install_data('Bakery', install_dir: join_paths(get_option('bindir')))

install_subdir('bakery', install_dir: py.get_install_dir())

subdir('po')
subdir('data')



