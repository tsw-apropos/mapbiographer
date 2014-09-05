# -*- coding: utf-8 -*-
"""
/***************************************************************************
 lmbMapToolPoint
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

class lmbMapToolPoint(QgsMapTool):
    
    rbFinished = QtCore.pyqtSignal('QgsGeometry*')

    def __init__(self, canvas):
        # get canvas
        QgsMapTool.__init__(self,canvas)
        self.canvas = canvas
        # control variables
        self.started = False
        self.dragging = False
        self.dragStart = time.time()
    
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
                # if it is the start of a point set the rubberband up
                if self.started == False:
                    # define rubber band
                    self.rb = QgsRubberBand(self.canvas, QGis.Point)
                    self.rb.setIconSize(8)
                    self.rb.setOpacity(0.5)
                    self.rb.setIcon(self.rb.ICON_CIRCLE)
                    self.rb.setColor(QtGui.QColor('#ff0000'))
                    self.started = True
                # get coordinates if we are connecting to an editable layer
                if layer <> None:
                    x = event.pos().x()
                    y = event.pos().y()
                    #selPoint = QtCore.QPoint(x,y)
                    # create point
                    point = QgsMapToPixel.toMapCoordinates(self.canvas.getCoordinateTransform(), x, y)
                    # add point
                    if self.rb.size() > 0:
                        self.rb.removeLastPoint()
                    # put rubber band at cursor
                    self.rb.movePoint(point)
                    g = QgsGeometry().fromPoint(point)
                    if g <> None and g.isGeosValid():
                        self.started = False
                        self.rbFinished.emit(g) 
  
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
