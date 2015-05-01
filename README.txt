***************************************************************************
 Locate points along lines
                                 A QGIS plugin
 Creating points along lines with given offset and interval
                              -------------------
        copyright            : (C) 2015 by Łukasz Dębek
        email                : damnback333@gmail.com
***************************************************************************
"Locate points along lines" is simple tool for creating points along lines with given offset and interval.

With "Locate points along lines" plugin you can:

- create points only on selected polylines;
- define offset and interval parameters;
- choose whether points should inherit attributes from source polylines;
- force adding endpoints of polylines;
- force adding vertices of polylines.

The resulting layer is 'memory layer' which you can export to different vector format.
Setting interval to 0 will cause adding vertices only (startpoints, endpoints or all vertices - depends on the options checked).
