# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LocatePointsDialog
                                 A QGIS plugin
 Creating points along lines with given offset and interval
                             -------------------
        begin                : 2015-03-18
        copyright            : (C) 2018 by Łukasz Dębek
        email                : damnback333@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os
from qgis.PyQt import QtWidgets, uic
from qgis.core import QgsProject
from qgis.gui import QgsMessageBar
from qgis.PyQt.QtCore import QObject, QThread, pyqtSignal
from .locate_points_core import LocatePointsEngine

try:
    from qgis.core import QgsMapLayerRegistry
except ImportError:
    pass

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'locate_points_dialog_base.ui'))


class LocatePointsDialog(QtWidgets.QDialog, FORM_CLASS):
    """Plugin main dialog."""
    def __init__(self, parent=None):
        super(LocatePointsDialog, self).__init__(parent)
        self.setupUi(self)
        self.in_combo.currentIndexChanged.connect(self.combo_changed)
        self.out_lyr.textChanged.connect(self.line_edit_text_changed)
        self.check_vertices.stateChanged.connect(self.checkbox_changed)
        self.run_button.clicked.connect(self.on_start)

        # Extra attributes
        self.in_name = False
        self.out_name = False

        # Extra thread attributes
        self.worker = None
        self.thread = None

    def on_start(self):
        self.pbar.setRange(0, 0)
        self.run_button.setEnabled(False)
        self.close_button.setEnabled(False)
        self.in_combo.setEnabled(False)
        self.out_lyr.setEnabled(False)
        self.offset.setEnabled(False)
        self.interval.setEnabled(False)
        self.check_attrs.setEnabled(False)
        self.check_vertices.setEnabled(False)
        self.check_endpoints.setEnabled(False)

        inlyr = self.in_combo.itemData(self.in_combo.currentIndex())
        outlyr = self.out_lyr.text()
        offset = self.offset.value()
        interval = self.interval.value()
        keep_attrs = self.check_attrs.isChecked()
        add_ver = self.check_vertices.isChecked()
        add_end = self.check_endpoints.isChecked()

        self.worker = Worker(inlyr, outlyr, offset, interval, keep_attrs, add_ver, add_end)
        self.thread = QThread(self)
        self.worker.moveToThread(self.thread)
        self.worker.finished.connect(self.on_finished)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def on_finished(self, error):
        vl = self.worker.vl
        self.worker.deleteLater()
        self.thread.quit()
        self.thread.wait()
        self.thread.deleteLater()

        self.pbar.setRange(0, 10)
        self.pbar.setValue(10)
        self.run_button.setEnabled(True)
        self.close_button.setEnabled(True)
        self.in_combo.setEnabled(True)
        self.out_lyr.setEnabled(True)
        self.offset.setEnabled(True)
        self.interval.setEnabled(True)
        self.check_attrs.setEnabled(True)
        self.check_vertices.setEnabled(True)

        if self.check_vertices.isChecked() is False:
            self.check_endpoints.setEnabled(True)

        if error:
            self.iface.messageBar().pushMessage(
                'Failed to create points!', '{}'.format(error),
                level=QgsMessageBar.CRITICAL)
        else:
            try:
                QgsProject.instance().addMapLayer(vl)
            except AttributeError:
                QgsMapLayerRegistry.instance().addMapLayer(vl)

    def combo_changed(self, idx):
        if idx > 0:
            self.in_name = True
            if self.out_name is True:
                self.run_button.setEnabled(True)
            else:
                self.run_button.setEnabled(False)
        else:
            self.in_name = False
            self.run_button.setEnabled(False)

    def line_edit_text_changed(self, text):
        if text:
            self.out_name = True
            if self.in_name is True:
                self.run_button.setEnabled(True)
            else:
                self.run_button.setEnabled(False)
        else:
            self.out_name = False
            self.run_button.setEnabled(False)

    def checkbox_changed(self, state):
        if state == 2:
            self.check_endpoints.setChecked(0)
            self.check_endpoints.setEnabled(False)
        else:
            self.check_endpoints.setEnabled(True)


class Worker(QObject):
    """Worker object that will be moved to a separate thread."""
    finished = pyqtSignal(str)

    def __init__(self, inlyr, outlyr, offset, interval, keep_attrs, add_ver, add_end):
        super(QObject, self).__init__()
        self.inlyr = inlyr
        self.outlyr = outlyr
        self.offset = offset
        self.interval = interval
        self.keep_attrs = keep_attrs
        self.add_ver = add_ver
        self.add_end = add_end
        self.vl = None

    def run(self):
        error = ''
        try:
            if self.interval == 0 and self.add_ver == 0 and self.add_end == 0:
                raise RuntimeError('Invalid set of parameters! Creation of points aborted!')

            engine = LocatePointsEngine(self.inlyr,
                                        self.outlyr,
                                        self.offset,
                                        self.interval,
                                        self.keep_attrs,
                                        self.add_ver,
                                        self.add_end)
            engine.lines2dict()
            engine.update_distance()
            self.vl = engine.dict2lyr()
        except Exception as e:
            error = str(e)

        self.finished.emit(error)
