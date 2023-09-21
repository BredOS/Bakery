project('bakery',
          version: '0.1.0',
    meson_version: '>= 0.62.0',
  default_options: [ 'warning_level=2', 'werror=false', ],
)

i18n = import('i18n')

install_data('bakery-cli.py', install_dir: join_paths(get_option('datadir'), 'bakery'))
install_data('bakery-gui.py', install_dir: join_paths(get_option('datadir'), 'bakery'))
install_data('bakery.py', install_dir: join_paths(get_option('datadir'), 'bakery'))
install_data('config.py', install_dir: join_paths(get_option('datadir'), 'bakery'))
# install license
install_data('LICENSE', install_dir: join_paths(get_option('datadir'), 'licenses/bakery'))
install_data('Bakery', install_dir: join_paths(get_option('bindir')))

subdir('po')
subdir('data')


