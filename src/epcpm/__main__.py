import argparse
import logging
import os.path
import sys

from PyQt5 import QtCore, QtGui, QtWidgets

import epyqlib.utils.qt
import epcpm.mainwindow

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='count', default=0)
    parser.add_argument('--file', '-f', type=argparse.FileType('r'))

    return parser.parse_args(args)


def main(*args, logger):
    app = QtWidgets.QApplication(sys.argv)

    epyqlib.utils.qt.exception_message_box_register_versions(
        version_tag=epcpm.__version_tag__,
        build_tag=epcpm.__build_tag__,
    )

    sys.excepthook = epyqlib.utils.qt.exception_message_box

    os_signal_timer = epyqlib.utils.qt.setup_sigint()

    QtCore.qInstallMessageHandler(epyqlib.utils.qt.message_handler)

    app.setStyleSheet('QMessageBox {{ messagebox-text-interaction-flags: {}; }}'
                      .format(QtCore.Qt.TextBrowserInteraction))

    app.setOrganizationName('EPC Power Corp.')
    app.setApplicationName('EPC Parameter Management')

    args = parse_args(args=args)

    if args.verbose >= 1:
        logger.setLevel(logging.DEBUG)

        if args.verbose >= 2:
            # twisted.internet.defer.setDebugging(True)
            pass

            if args.verbose >= 3:
                logging.getLogger().setLevel(logging.DEBUG)

    window = epcpm.mainwindow.Window(ui_file='__main__.ui')
    epyqlib.utils.qt.exception_message_box_register_parent(parent=window.ui)

    if args.file is not None:
        args.file.close()
        filename = os.path.abspath(args.file.name)
        window.open(filename=filename)
        args.file.close()

    window.ui.show()

    return app.exec()


def _entry_point():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    stream_handler = logging.StreamHandler()
    file_handler = logging.FileHandler('epcpm.log')

    for handler in (stream_handler, file_handler):
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')

    sys.excepthook = epyqlib.utils.general.exception_logger

    return main(*sys.argv[1:], logger=logger)
