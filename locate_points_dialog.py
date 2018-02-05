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

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'locate_points_dialog_base.ui'))


class LocatePointsDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(LocatePointsDialog, self).__init__(parent)
        self.setupUi(self)
