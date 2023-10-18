desktop_file = i18n.merge_file(
        input: 'org.bredos.bakery.desktop.in',
       output: 'org.bredos.bakery.desktop',
         type: 'desktop',
       po_dir: '../po',
      install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils, args: [desktop_file])
endif

appstream_file = i18n.merge_file(
        input: 'org.bredos.bakery.appdata.xml.in',
       output: 'org.bredos.bakery.appdata.xml',
       po_dir: '../po',
      install: true,
  install_dir: join_paths(get_option('datadir'), 'appdata')
)

appstream_util = find_program('appstream-util', required: false)
if appstream_util.found()
  test('Validate appstream file', appstream_util, args: ['validate', appstream_file])
endif

install_data('org.bredos.bakery.gschema.xml',
  install_dir: join_paths(get_option('datadir'), 'glib-2.0/schemas')
)

compile_schemas = find_program('glib-compile-schemas', required: false)
if compile_schemas.found()
  test('Validate schema file',
       compile_schemas,
       args: ['--strict', '--dry-run', meson.current_source_dir()])
endif

install_data('window.ui',
  install_dir: join_paths(get_option('datadir'), 'bakery/data')
)
install_data('kb_dialog.ui',
  install_dir: join_paths(get_option('datadir'), 'bakery/data')
)
install_data('kb_screen.ui',
  install_dir: join_paths(get_option('datadir'), 'bakery/data')
)
install_data('locale_screen.ui',
  install_dir: join_paths(get_option('datadir'), 'bakery/data')
)
install_data('timezone_screen.ui',
  install_dir: join_paths(get_option('datadir'), 'bakery/data')
)
install_data('user_screen.ui',
  install_dir: join_paths(get_option('datadir'), 'bakery/data')
)
# de_screen.ui summary_screen.ui


subdir('icons')
