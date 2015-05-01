# -*- coding: utf-8 -*-
##########################################################################################
"""
/***************************************************************************
 LocatePoints
                                 A QGIS plugin
 Creating points along lines with given offset and interval
                              -------------------
        begin                : 2015-03-18
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Łukasz Dębek
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
##########################################################################################
# Import qgis.core functions
from qgis.core import *
# Import PyQt4 functions
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QThread, pyqtSignal, pyqtSlot
from PyQt4.QtGui import QAction, QIcon
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from locate_points_dialog import LocatePointsDialog
from locate_points_core import LocatePointsEngine
import os.path


class LocatePoints(object):
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
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
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'LocatePoints')
        self.toolbar.setObjectName(u'LocatePoints')

        # Extra attributes
        self.inName = False
        self.outName = False
        self.heavyTask = TaskThread()

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
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
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

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

        icon_path = ':/plugins/LocatePoints/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Locate points along lines'),
            callback=self.run,
            parent=self.iface.mainWindow())
        self.dlg.inCombo.currentIndexChanged.connect(self.combo_changed)
        self.dlg.outLyr.textChanged.connect(self.line_edit_text_changed)
        self.dlg.checkVertices.stateChanged.connect(self.checkbox_changed)
        self.dlg.runButton.clicked.connect(self.onStart)
        self.heavyTask.taskFinished.connect(self.onFinished)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&Locate points along lines'), action)
            self.iface.removeToolBarIcon(action)

    @pyqtSlot()
    def onStart(self):
        self.dlg.pbar.setRange(0,0)
        self.dlg.runButton.setEnabled(False)
        self.dlg.closeButton.setEnabled(False)
        self.dlg.inCombo.setEnabled(False)
        self.dlg.outLyr.setEnabled(False)
        self.dlg.offset.setEnabled(False)
        self.dlg.interval.setEnabled(False)
        self.dlg.checkAttrs.setEnabled(False)
        self.dlg.checkVertices.setEnabled(False)
        self.dlg.checkEndpoints.setEnabled(False)
        self.heavyTask.inlyr = self.dlg.inCombo.itemData(self.dlg.inCombo.currentIndex())
        self.heavyTask.outlyr = self.dlg.outLyr.text()
        self.heavyTask.offset = self.dlg.offset.value()
        self.heavyTask.interval = self.dlg.interval.value()
        self.heavyTask.keep_attrs = self.dlg.checkAttrs.isChecked()
        self.heavyTask.add_ver = self.dlg.checkVertices.isChecked()
        self.heavyTask.add_end = self.dlg.checkEndpoints.isChecked()
        self.heavyTask.start()

    @pyqtSlot()
    def onFinished(self):
        self.dlg.pbar.setRange(0,10)
        self.dlg.pbar.setValue(10)
        self.dlg.runButton.setEnabled(True)
        self.dlg.closeButton.setEnabled(True)
        self.dlg.inCombo.setEnabled(True)
        self.dlg.outLyr.setEnabled(True)
        self.dlg.offset.setEnabled(True)
        self.dlg.interval.setEnabled(True)
        self.dlg.checkAttrs.setEnabled(True)
        self.dlg.checkVertices.setEnabled(True)
        if self.dlg.checkVertices.isChecked() is False:
            self.dlg.checkEndpoints.setEnabled(True)
        else:
            pass
        if self.heavyTask.vl is None:
            self.iface.messageBar().pushMessage('Error', 'Failed to create points!', level=2)
        else:
            QgsMapLayerRegistry.instance().addMapLayer(self.heavyTask.vl)

    @pyqtSlot(str)
    def combo_changed(self, text):
        if text:
            self.inName = True
            if self.outName is True:
                self.dlg.runButton.setEnabled(True)
            else:
                self.dlg.runButton.setEnabled(False)
        else:
            self.inName = False
            self.dlg.runButton.setEnabled(False)

    @pyqtSlot(str)
    def line_edit_text_changed(self, text):
        if text:
            self.outName = True
            if self.inName is True:
                self.dlg.runButton.setEnabled(True)
            else:
                self.dlg.runButton.setEnabled(False)
        else:
            self.outName = False
            self.dlg.runButton.setEnabled(False)
    
    @pyqtSlot(int)
    def checkbox_changed(self, state):
        if state == 2:
            self.dlg.checkEndpoints.setChecked(0)
            self.dlg.checkEndpoints.setEnabled(False)
        else:
            self.dlg.checkEndpoints.setEnabled(True)

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        self.dlg.inCombo.clear()
        self.dlg.inCombo.addItem(None)
        layers = QgsMapLayerRegistry.instance().mapLayers().values()
        for lyr in layers:
            if lyr.type() == QgsMapLayer.VectorLayer and lyr.geometryType() == QGis.Line:
                self.dlg.inCombo.addItem(lyr.name(), lyr)
            else:
                pass
        # Run the dialog event loop
        self.dlg.exec_()
        self.dlg.pbar.setValue(0)


##########################################################################################
# Extra thread:
class TaskThread(QThread):
    taskFinished = pyqtSignal()

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
        try:
            engine = LocatePointsEngine(self.inlyr, self.outlyr, self.offset, self.interval, self.keep_attrs, self.add_ver, self.add_end)
            engine.lines2dict()
            engine.update_distance()
            self.vl = engine.dict2lyr()
        except:
            pass
        self.taskFinished.emit()

##########################################################################################
