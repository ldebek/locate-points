# -*- coding: utf-8 -*-
##########################################################################################
"""
/***************************************************************************
 LocatePoints
                                 A QGIS plugin
 Functions for geometry and attributes processing
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
import math
from qgis.core import *
from PyQt4.QtCore import QVariant

# Extracting polyline geometry and attributes to dictionary:
def lines2dict(layer, keep_attrs):
  ndict = {}
  if keep_attrs is True:
    flds = layer.dataProvider().fields().toList()
    row_attrs = lambda row: row.attributes()
  else:
    flds = []
    row_attrs = lambda row: []
  field_names = [f.name() for f in flds]
  flds.append(QgsField('org_fid', QVariant.Int))
  flds.append(QgsField('distance', QVariant.Double))
  fc = layer.selectedFeatures() if layer.selectedFeatureCount() > 0 else layer.getFeatures()
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
    ndict[k] = {'attrs':attrs, 'ver':vertices, 'multi':multi}
  return (ndict, flds)

# Updating dictionary with new points:
def update_distance(ndict, interval, offset, add_end):
  for k in ndict:
    totaldist = 0
    partdist = offset
    ver = ndict[k]['ver']
    multi = ndict[k]['multi']
    if multi is True:
      points = []
      for part in ver:
        part_points, partdist, totaldist = calc_coords(part, interval, partdist, totaldist)
        points.extend(part_points)
      ver = ver[-1]
    else:
      points, partdist, totaldist = calc_coords(ver, interval, partdist, totaldist)
    if add_end is True:
      endX, endY = ver[-1]
      dl = totaldist - partdist
      points.append({'distance':dl, 'X':endX, 'Y':endY})
    else:
      pass
    ndict[k]['points'] = points

# Calculating coordinates of points along lines:
def calc_coords(ver, interval, partdist, totaldist):
  points = []
  iver = iter(ver)
  xl, yl = next(iver)
  xr, yr = next(iver)
  while True:
    dx = xr - xl
    dy = yr - yl
    dl = math.sqrt(dx**2 + dy**2)
    leftdist = dl - partdist
    while leftdist >= 0:
      pnt = {'distance':totaldist}
      coef = partdist / dl
      pnt['X'] = (1 - coef) * xl + coef * xr
      pnt['Y'] = (1 - coef) * yl + coef * yr
      partdist += interval
      totaldist += interval
      leftdist -= interval
      points.append(pnt)
    partdist = abs(leftdist)
    try:
      xl, yl = xr, yr
      xr, yr = next(iver)
    except StopIteration:
      break
  return (points, partdist, totaldist)

# Converting dictionary to QgsVectorLayer:
def dict2lyr(ndict, flds, crs, outname):
  vl = QgsVectorLayer('Point?crs={0}'.format(crs), outname, 'memory')
  pr = vl.dataProvider()
  pr.addAttributes(flds)
  vl.startEditing()
  for k in ndict:
    cs = ndict[k]['attrs']
    for points in ndict[k]['points']:
      distance = points['distance']
      elem = QgsFeature()
      elem.setGeometry(QgsGeometry.fromPoint(QgsPoint(points['X'], points['Y'])))
      elem.setAttributes(cs + [distance])
      vl.addFeature(elem)
  vl.updateExtents()
  vl.commitChanges()
  return vl

##########################################################################################
