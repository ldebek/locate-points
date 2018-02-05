# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LocatePoints
                                 A QGIS plugin
 Class with methods for geometry and attributes processing
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
import math
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsField, QgsVectorLayer, QgsFeature, QgsGeometry

try:
    from qgis.core import QgsPointXY

    def point_geometry(x, y):
        return QgsGeometry.fromPointXY(QgsPointXY(x, y))

except ImportError:
    from qgis.core import QgsPoint

    def point_geometry(x, y):
        return QgsGeometry.fromPoint(QgsPoint(x, y))


class LocatePointsEngine(object):
    """Class for polylines processing."""
    def __init__(self, layer, outname, offset, interval, keep_attrs, add_ver, add_end):
        self.layer = layer
        self.outname = outname
        self.offset = offset
        self.interval = interval if interval > 0 else 10**24
        self.keep_attrs = keep_attrs
        self.add_ver = add_ver
        self.add_end = add_end
        self.ndict = {}
        self.totaldist = None
        self.partdist = None
        self.multi = None
        if self.keep_attrs is True:
            self.flds = self.layer.dataProvider().fields().toList()
        else:
            self.flds = []
        self.flds.append(QgsField('org_fid', QVariant.Int))
        self.flds.append(QgsField('distance', QVariant.Double))

    # Extracting polylines geometry and attributes to dictionary:
    def lines2dict(self):
        if self.keep_attrs is True:
            def row_attrs(row): return row.attributes()
        else:
            def row_attrs(row): return []
        fc = self.layer.selectedFeatures() if self.layer.selectedFeatureCount() > 0 else self.layer.getFeatures()
        for row in fc:
            k = row.id()
            attrs = row_attrs(row)
            attrs.append(k)
            geom = row.geometry()
            if geom.isMultipart():
                multi = True
                vertices = geom.asMultiPolyline()
            else:
                multi = False
                vertices = geom.asPolyline()
            self.ndict[k] = {'attrs': attrs, 'ver': vertices, 'multi': multi}

    # Updating dictionary with new points:
    def update_distance(self):
        for k in self.ndict:
            self.totaldist = self.offset
            self.partdist = self.offset
            ver = self.ndict[k]['ver']
            self.multi = self.ndict[k]['multi']
            if self.multi is True:
                points = []
                self.multi = False
                for part in ver:
                    part_points = self.calc_coords(part)
                    points.extend(part_points)
                    self.multi = True
                ver = ver[-1]
            else:
                points = self.calc_coords(ver)
            if self.add_end is True:
                end_x, end_y = ver[-1]
                dl = self.totaldist - self.partdist if self.totaldist >= self.partdist else self.offset - self.partdist
                points.append({'distance': dl, 'X': end_x, 'Y': end_y})
            else:
                pass
            self.ndict[k]['points'] = points

    # Calculating coordinates of points along lines:
    def calc_coords(self, ver):
        points = []
        iver = iter(ver)
        xl, yl = next(iver)
        xr, yr = next(iver)
        if self.add_ver is True and (self.offset > 0 or self.multi is True):
            points.append({'distance': self.totaldist - self.partdist, 'X': xl, 'Y': yl})
        else:
            pass
        while True:
            dx = xr - xl
            dy = yr - yl
            dl = math.sqrt(dx**2 + dy**2)
            leftdist = dl - self.partdist
            while leftdist >= 0:
                pnt = {'distance': self.totaldist}
                coef = self.partdist / dl
                pnt['X'] = (1 - coef) * xl + coef * xr
                pnt['Y'] = (1 - coef) * yl + coef * yr
                self.partdist += self.interval
                self.totaldist += self.interval
                leftdist -= self.interval
                points.append(pnt)
            self.partdist = abs(leftdist)
            if self.add_ver is True:
                points.append({'distance': self.totaldist - self.partdist, 'X': xr, 'Y': yr})
            else:
                pass
            try:
                xl, yl = xr, yr
                xr, yr = next(iver)
            except StopIteration:
                break
        return points

    # Converting dictionary to QgsVectorLayer:
    def dict2lyr(self):
        crs = self.layer.crs().authid()
        vl = QgsVectorLayer('Point?crs={0}'.format(crs), self.outname, 'memory')
        pr = vl.dataProvider()
        pr.addAttributes(self.flds)
        vl.startEditing()
        for k in self.ndict:
            cs = self.ndict[k]['attrs']
            for points in self.ndict[k]['points']:
                distance = points['distance']
                elem = QgsFeature()
                elem.setGeometry(point_geometry(points['X'], points['Y']))
                elem.setAttributes(cs + [distance])
                vl.addFeature(elem)
        vl.updateExtents()
        vl.commitChanges()
        return vl
