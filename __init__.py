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
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):
    """Load LocatePoints class from file LocatePoints."""
    from .locate_points import LocatePoints
    return LocatePoints(iface)
