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
from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from .locate_points_dialog import LocatePointsDialog

try:
    from qgis.core import QgsWkbTypes
    LINE_GEOM = QgsWkbTypes.LineGeometry
except ImportError:
    from qgis.core import QGis, QgsMapLayerRegistry
    LINE_GEOM = QGis.Line


class LocatePoints(object):
    """QGIS Plugin Implementation."""
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(self.plugin_dir, 'i18n', 'LocatePoints_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
                QCoreApplication.installTranslator(self.translator)

        self.dlg = LocatePointsDialog(self.iface)

        self.actions = []
        self.menu = self.tr(u'&Locate points along lines')
        self.toolbar = self.iface.addToolBar(u'LocatePoints')
        self.toolbar.setObjectName(u'LocatePoints')

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

    # noinspection PyPep8Naming
    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        self.add_action(
            icon_path,
            text=self.tr(u'Locate points along lines'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&Locate points along lines'), action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        """Run method that performs all the real work."""
        self.dlg.pbar.setValue(0)
        self.dlg.in_combo.clear()
        self.dlg.in_combo.addItem(None)

        try:
            layers = list(QgsProject.instance().mapLayers().values())
        except AttributeError:
            layers = QgsMapLayerRegistry.instance().mapLayers().values()

        for lyr in layers:
            if lyr.type() == QgsMapLayer.VectorLayer and lyr.geometryType() == LINE_GEOM:
                self.dlg.in_combo.addItem(lyr.name(), lyr)

        self.dlg.show()
        self.dlg.exec_()
