# -*- coding: utf-8 -*-
"""
/***************************************************************************
 lmbMapToolPolygon
                                 A QGIS plugin
 Effectively onduct direct to digital map biographies and traditional land
 use studies
                             -------------------
        begin                : 2014-05-13
        copyright            : (C) 2014 by Apropos Information Systems Inc.
        email                : info@aproposinfosystems.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   any later version.                                                    *
 *                                                                         *
 *   Derived from vertexTracerTool.py & freehandeditingtool.py             *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt4 import QtCore, QtGui
from qgis.core import *
from qgis.gui import *
import time 

class lmbMapToolPolygon(QgsMapTool):
    
    rbFinished = QtCore.pyqtSignal('QgsGeometry*')

    def __init__(self, canvas):
        # get canvas
        QgsMapTool.__init__(self,canvas)
        self.canvas = canvas
        # control variables
        self.started = False
        self.firstTimeOnSegment = True
        self.dragging = False
        self.dragStart = time.time()
        # related to temp output but function unclear
        self.prevPoint = None
    
        # custom cursor
        self.cursor = QtGui.QCursor(QtGui.QPixmap(["16 16 3 1",
                                      "      c None",
                                      ".     c #FF0000",
                                      "+     c #000000",
                                      "                ",
                                      "       +.+      ",
                                      "      ++.++     ",
                                      "     +.....+    ",
                                      "    +.     .+   ",
                                      "   +.   .   .+  ",
                                      "  +.    .    .+ ",
                                      " ++.    .    .++",
                                      " ... ...+... ...",
                                      " ++.    .    .++",
                                      "  +.    .    .+ ",
                                      "   +.   .   .+  ",
                                      "   ++.     .+   ",
                                      "    ++.....+    ",
                                      "      ++.++     ",
                                      "       +.+      "]))
                                  
 
    #
    # track when delete is released to permit deletion of last point
    
    def keyReleaseEvent(self,  event):
        # remove the last added point when the delete key is pressed
        if event.key() == QtCore.Qt.Key_Backspace:
            self.rb.removeLastPoint()

    #
    # canvas click events

    def canvasPressEvent(self,event):

        if event.button() == 1:
            self.dragging = True
            self.dragStart = time.time()

    #
    # canvas move events
     
    def canvasMoveEvent(self,event):

        if self.dragging == True:
            self.canvas.panAction(event)
        else:
            if self.started:
                #Get the click
                x = event.pos().x()
                y = event.pos().y()
                eventPoint = QtCore.QPoint(x,y)
                layer = self.canvas.currentLayer()
                if layer <> None:
                   point = QgsMapToPixel.toMapCoordinates(self.canvas.getCoordinateTransform(), x, y)
                   self.rb.movePoint(point)

    #
    # canvas release events
    
    def canvasReleaseEvent(self,event):

        diff = 0
        if self.dragging == True:
            self.dragging = False
            self.canvas.panActionEnd(event.pos())
            diff = time.time() - self.dragStart
        # if drag time is very short then assume that this was a click
        if diff < 0.5:
            # left click
            if event.button() == 1:
                # select the current layer
                layer = self.canvas.currentLayer()
                # if it is the start of a polygon set the rubberband up
                if self.started == False:
                    self.rb = QgsRubberBand(self.canvas, layer.geometryType())
                    self.rb.setColor(QtGui.QColor('#ff0000'))
                    self.rb.setWidth(1)
                    self.rb.setOpacity(0.5)
                    self.started = True
                # get coordinates if we are connecting to an editable layer
                if layer <> None:
                    x = event.pos().x()
                    y = event.pos().y()
                    selPoint = QtCore.QPoint(x,y)
                    # create point
                    point = QgsMapToPixel.toMapCoordinates(self.canvas.getCoordinateTransform(), x, y)
                    # put rubber band at cursor
                    self.rb.movePoint(point)
                    # set new point
                    self.appendPoint(point)
            # right click
            elif event.button() == 2:
                self.sendGeometry()
  
    #
    # append point

    def appendPoint(self, point):
        # only add point if different from previous
        if not (self.prevPoint == point) :      
            self.rb.addPoint(point)
            self.prevPoint = QgsPoint(point)

    #
    # send geometry
      
    def sendGeometry(self):
        layer = self.canvas.currentLayer() 
        coords = []

        #
        # NOTE: code from vertex tracer skipped first point by using range of
        # 1 to # of vertices. Changed to zero to include all points and have a
        # complete feature.
        # Also skip last point when right click was pressed to avoid extra points
        # being placed
        #
        [coords.append(self.rb.getPoint(0,i)) for i in range(0,self.rb.numberOfVertices()-1)]
    
        coords_tmp = coords[:]
        coords = []
        for point in coords_tmp:
            transformedPoint = self.canvas.mapRenderer().mapToLayerCoordinates( layer, point );
            coords.append(transformedPoint)
       
        coords_tmp = coords[:]
        coords = []
        lastPt = None
        for pt in coords_tmp:
            if (lastPt <> pt) :
                coords.append(pt)
            lastPt = pt
             
        g = QgsGeometry().fromPolygon([coords])
        if g <> None and g.isGeosValid():
            self.rbFinished.emit(g) 
            self.started = False

    #
    # activate tool
    
    def activate(self):
        self.canvas.setCursor(self.cursor)

    #
    # deactivate tool
    
    def deactivate(self):
        try:
            self.rb.reset()
        except AttributeError:
            pass

    #
    # send false if queried if zoom tool
    
    def isZoomTool(self):
        return False

    #
    # send false if queried if transient (performs zoom or pan operation)
    
    def isTransient(self):
        return False

    #
    # send true if queried if edit tool
    
    def isEditTool(self):
        return True
