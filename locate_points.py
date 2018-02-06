# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LocatePoints
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
from __future__ import absolute_import
import os.path
from qgis.core import QgsProject, QgsMapLayer
from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QThread, pyqtSignal
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from .locate_points_dialog import LocatePointsDialog
from .locate_points_core import LocatePointsEngine

try:
    from qgis.core import QgsWkbTypes
    LINE_GEOM = QgsWkbTypes.LineGeometry
except ImportError:
    from qgis.core import QGis, QgsMapLayerRegistry
    LINE_GEOM = QGis.Line


class LocatePoints(object):
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor."""
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(self.plugin_dir, 'i18n', 'LocatePoints_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = LocatePointsDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Locate points along lines')
        self.toolbar = self.iface.addToolBar(u'LocatePoints')
        self.toolbar.setObjectName(u'LocatePoints')

        # Extra attributes
        self.in_name = False
        self.out_name = False
        self.heavy_task = TaskThread()

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """
        Get the translation for a string using Qt translation API.
        We implement this ourselves since we do not inherit QObject.
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('LocatePoints', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None
    ):
        """Add a toolbar icon to the toolbar."""
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        self.add_action(
            icon_path,
            text=self.tr(u'Locate points along lines'),
            callback=self.run,
            parent=self.iface.mainWindow())
        self.dlg.in_combo.currentIndexChanged.connect(self.combo_changed)
        self.dlg.out_lyr.textChanged.connect(self.line_edit_text_changed)
        self.dlg.check_vertices.stateChanged.connect(self.checkbox_changed)
        self.dlg.run_button.clicked.connect(self.on_start)
        self.heavy_task.task_finished.connect(self.on_finished)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&Locate points along lines'), action)
            self.iface.removeToolBarIcon(action)

    def on_start(self):
        self.dlg.pbar.setRange(0, 0)
        self.dlg.run_button.setEnabled(False)
        self.dlg.close_button.setEnabled(False)
        self.dlg.in_combo.setEnabled(False)
        self.dlg.out_lyr.setEnabled(False)
        self.dlg.offset.setEnabled(False)
        self.dlg.interval.setEnabled(False)
        self.dlg.check_attrs.setEnabled(False)
        self.dlg.check_vertices.setEnabled(False)
        self.dlg.check_endpoints.setEnabled(False)
        self.heavy_task.inlyr = self.dlg.in_combo.itemData(self.dlg.in_combo.currentIndex())
        self.heavy_task.outlyr = self.dlg.out_lyr.text()
        self.heavy_task.offset = self.dlg.offset.value()
        self.heavy_task.interval = self.dlg.interval.value()
        self.heavy_task.keep_attrs = self.dlg.check_attrs.isChecked()
        self.heavy_task.add_ver = self.dlg.check_vertices.isChecked()
        self.heavy_task.add_end = self.dlg.check_endpoints.isChecked()
        self.heavy_task.start()

    def on_finished(self, error):
        self.dlg.pbar.setRange(0, 10)
        self.dlg.pbar.setValue(10)
        self.dlg.run_button.setEnabled(True)
        self.dlg.close_button.setEnabled(True)
        self.dlg.in_combo.setEnabled(True)
        self.dlg.out_lyr.setEnabled(True)
        self.dlg.offset.setEnabled(True)
        self.dlg.interval.setEnabled(True)
        self.dlg.check_attrs.setEnabled(True)
        self.dlg.check_vertices.setEnabled(True)
        if self.dlg.check_vertices.isChecked() is False:
            self.dlg.check_endpoints.setEnabled(True)
        else:
            pass
        if error:
            self.iface.messageBar().pushMessage('Failed to create points!', '{}'.format(error), level=2)
        else:
            try:
                QgsProject.instance().addMapLayer(self.heavy_task.vl)
            except AttributeError:
                QgsMapLayerRegistry.instance().addMapLayer(self.heavy_task.vl)

    def combo_changed(self, idx):
        if idx > 0:
            self.in_name = True
            if self.out_name is True:
                self.dlg.run_button.setEnabled(True)
            else:
                self.dlg.run_button.setEnabled(False)
        else:
            self.in_name = False
            self.dlg.run_button.setEnabled(False)

    def line_edit_text_changed(self, text):
        if text:
            self.out_name = True
            if self.in_name is True:
                self.dlg.run_button.setEnabled(True)
            else:
                self.dlg.run_button.setEnabled(False)
        else:
            self.out_name = False
            self.dlg.run_button.setEnabled(False)

    def checkbox_changed(self, state):
        if state == 2:
            self.dlg.check_endpoints.setChecked(0)
            self.dlg.check_endpoints.setEnabled(False)
        else:
            self.dlg.check_endpoints.setEnabled(True)

    def run(self):
        """Run method that performs all the real work."""
        self.dlg.show()
        self.dlg.in_combo.clear()
        self.dlg.in_combo.addItem(None)
        try:
            layers = list(QgsProject.instance().mapLayers().values())
        except AttributeError:
            layers = QgsMapLayerRegistry.instance().mapLayers().values()
        for lyr in layers:
            if lyr.type() == QgsMapLayer.VectorLayer and lyr.geometryType() == LINE_GEOM:
                self.dlg.in_combo.addItem(lyr.name(), lyr)
            else:
                pass
        self.dlg.exec_()
        self.dlg.pbar.setValue(0)


class TaskThread(QThread):
    """Extra thread for handling calculations."""
    task_finished = pyqtSignal(str)

    def __init__(self):
        super(TaskThread, self).__init__()
        self.inlyr = None
        self.outlyr = None
        self.offset = None
        self.interval = None
        self.keep_attrs = None
        self.add_ver = None
        self.add_end = None
        self.vl = None

    def run(self):
        error = ''
        try:
            if self.interval == 0 and self.add_ver == 0 and self.add_end == 0:
                raise RuntimeError('Invalid set of parameters! Creation of points aborted!')
            else:
                pass
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

        self.task_finished.emit(error)
