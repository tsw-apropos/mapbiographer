# -*- coding: utf-8 -*-
"""
/***************************************************************************
 mapBiographerTranscriber
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
 ***************************************************************************/
"""

from PyQt4 import QtCore, QtGui
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from pyspatialite import dbapi2 as sqlite
import os, datetime, time
import pyaudio, wave, pydub
from ui_mapbio_navigator import Ui_mapbioNavigator
import inspect, re

class mapBiographerNavigator(QtGui.QDockWidget, Ui_mapbioNavigator):

    #
    # init method to define globals and make widget / method connections
    
    def __init__(self, iface):

        self.debug = False
        if self.debug:
            self.myself = lambda: inspect.stack()[1][3]
        if self.debug == True:
            QgsMessageLog.logMessage('mapNavigator: '+self.myself())

        #
        # begin setup process
        QtGui.QDockWidget.__init__(self)
        self.setupUi(self)
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        self.setWindowTitle('LMB - Navigator')
        # project settings
        self.baseGroups = []
        self.baseGroupIdxs = []
        self.boundaryLayerName = ''
        self.boundaryLayer = None
        self.enableReference = ''
        self.referenceLayerName = ''
        self.referenceLayer = None
        self.points_layer = None
        self.lines_layer = None
        self.polygons_layer = None
        self.projectLoading = False
        # add panel
        self.iface.mainWindow().addDockWidget(QtCore.Qt.LeftDockWidgetArea, self)
        # panel functionality
        self.setFeatures(self.DockWidgetMovable | self.DockWidgetFloatable | self.DockWidgetClosable)
        #
        # signals and slots setup
        # map options
        QtCore.QObject.connect(self.cbBase, QtCore.SIGNAL("currentIndexChanged(int)"), self.selectBase)
        QtCore.QObject.connect(self.pbBoundary, QtCore.SIGNAL("clicked()"), self.viewBoundary)
        QtCore.QObject.connect(self.pbReference, QtCore.SIGNAL("clicked()"), self.viewReference)
        QtCore.QObject.connect(self.pbViewFeatures, QtCore.SIGNAL("clicked()"), self.viewFeatures)
        QtCore.QObject.connect(self.pbFeatureLabels, QtCore.SIGNAL("clicked()"), self.viewFeatureLabels)
        QtCore.QObject.connect(self.pbZoomFull, QtCore.SIGNAL("clicked()"), self.zoomFull)
        QtCore.QObject.connect(self.pbZoomToStudyArea, QtCore.SIGNAL("clicked()"), self.zoomToStudyArea)
        QtCore.QObject.connect(self.pbZoomIn, QtCore.SIGNAL("clicked()"), self.canvas.zoomIn)
        QtCore.QObject.connect(self.pbZoomOut, QtCore.SIGNAL("clicked()"), self.canvas.zoomOut)
        # track scale
        self.canvas.scale()
        # open project
        result = self.readSettings()
        #self.loadLayers()
        # set canvas view
        if self.boundaryLayer <> None:
            self.canvas.setExtent(self.boundaryLayer.extent())
        else:
            self.canvas.zoomToFullExtent()


    #####################################################
    #           project and panel management            #
    #####################################################

    #
    # read QGIS settings

    def readSettings(self):

        if self.debug == True:
            QgsMessageLog.logMessage('mapNavigator: '+self.myself())

        # method body
        s = QtCore.QSettings()
        rv = s.value('mapBiographer/baseGroups')
        if len(rv) > 0:
            self.baseGroups = rv
            self.baseGroupIdxs = range(len(rv))
        else:
            self.baseGroups = []
            self.baseGroupIdxs = []
            return(-1)
        rv = s.value('mapBiographer/boundaryLayer')
        if rv <> '':
            self.boundaryLayerName = rv
        else:
            self.boundaryLayerName = ''
            return(-1)
        rv = s.value('mapBiographer/enableReference')
        if rv == 'True':
            self.enableReference = True
        else:
            self.enableReference = False
        rv = s.value('mapBiographer/referenceLayer')
        if rv <> '':
            self.referenceLayerName = rv
        else:
            self.enableReference = False
            self.referenceLayerName = ''

        return(0)

    #
    # load layers
    
    def loadLayers(self):

        if self.debug == True:
            QgsMessageLog.logMessage('mapNavigator: '+self.myself())

        self.projectLoading = True
        # groups
        projectGroups = self.iface.legendInterface().groups()
        # set index to identify difference between stored setting list and project index
        for group in self.baseGroups:
            self.baseGroupIdxs[self.baseGroups.index(group)] = projectGroups.index(group)
        self.cbBase.clear()
        self.cbBase.addItems(self.baseGroups)
        # check against settings to determine if we can proceed
        visibleGroupSet = False
        for group in self.baseGroups:
            idx = projectGroups.index(group)
            if not (group in projectGroups):
                return(-1)
            elif visibleGroupSet == False:
                if self.iface.legendInterface().isGroupVisible(idx):
                    self.cbBase.setCurrentIndex(self.baseGroups.index(group))
                    visibleGroupSet = True
            else:
                self.iface.legendInterface().setGroupVisible(idx,False)
        # layers
        validLayers = []
        layers = self.iface.legendInterface().layers()
        self.points_layer = None
        self.lines_layer = None
        self.polygons_layer = None
        self.iface.actionRemoveAllFromOverview().activate(0)
        for layer in layers:
            validLayers.append(layer.name())
            if layer.name() == self.boundaryLayerName:
                self.boundaryLayer = layer
                if self.iface.legendInterface().isLayerVisible(layer):
                    self.iface.setActiveLayer(layer)
                    self.iface.actionAddToOverview().activate(0)
                    self.pbBoundary.setText('Hide Boundary')
                else:
                    self.pbBoundary.setText('Show Boundary')
            if layer.name() == self.referenceLayerName:
                self.referenceLayer = layer
                if self.iface.legendInterface().isLayerVisible(layer):
                    self.pbReference.setText('Hide Reference')
                    self.iface.setActiveLayer(layer)
                    self.iface.actionAddToOverview().activate(0)
                else:
                    self.pbReference.setText('Show Reference')
            if layer.name() == 'lmb_points':
                self.points_layer = layer
                self.iface.setActiveLayer(layer)
                self.iface.actionAddToOverview().activate(0)
            if layer.name() == 'lmb_lines':
                self.lines_layer = layer
                self.iface.setActiveLayer(layer)
                self.iface.actionAddToOverview().activate(0)
            if layer.name() == 'lmb_polygons':
                self.polygons_layer = layer
                self.iface.setActiveLayer(layer)
                self.iface.actionAddToOverview().activate(0)
        # boundary layer
        if not (self.boundaryLayerName in validLayers):
            return(-1)
        # reference layer
        if self.enableReference == True:
            self.pbReference.setEnabled(True)
            if not (self.referenceLayerName in validLayers):
                return(-1)
        else:
            self.pbReference.setDisabled(True)
        # reset show / hide button
        self.pbViewFeatures.setText('Hide Features')
        self.pbFeatureLabels.setText('Hide Labels')
        self.projectLoading = False

    
    #####################################################
    #              base and reference maps              #
    #####################################################

    #
    # select base map

    def selectBase(self):

        if self.projectLoading == False:
            if self.debug == True:
                QgsMessageLog.logMessage('mapNavigator: '+self.myself())
            #
            listIdx = self.cbBase.currentIndex()
            for x in range(len(self.baseGroups)):
                if x == listIdx:
                    if self.iface.legendInterface().isGroupVisible(self.baseGroupIdxs[x]) == False:
                        self.iface.legendInterface().setGroupVisible(self.baseGroupIdxs[x],True)
                elif self.iface.legendInterface().isGroupVisible(self.baseGroupIdxs[x]) == True:
                    self.iface.legendInterface().setGroupVisible(self.baseGroupIdxs[x],False)
        
    #
    # view boundary layer

    def viewBoundary(self):

        if self.debug == True:
            QgsMessageLog.logMessage('mapNavigator: '+self.myself())

        if self.projectLoading == False:
            if self.pbBoundary.text() == 'Hide Boundary':
                self.iface.legendInterface().setLayerVisible(self.boundaryLayer,False)
                self.iface.setActiveLayer(self.boundaryLayer)
                # remove from overview
                self.iface.actionAddToOverview().activate(0)
                self.pbBoundary.setText('Show Boundary')
            else:
                self.iface.legendInterface().setLayerVisible(self.boundaryLayer,True)
                self.iface.setActiveLayer(self.boundaryLayer)
                # add to overview
                self.iface.actionAddToOverview().activate(0)
                self.pbBoundary.setText('Hide Boundary')

    #
    # view reference layer

    def viewReference(self):

        if self.debug == True:
            QgsMessageLog.logMessage('mapNavigator: '+self.myself())

        if self.projectLoading == False:
            if self.pbReference.text() == 'Hide Reference':
                self.iface.legendInterface().setLayerVisible(self.referenceLayer,False)
                self.iface.setActiveLayer(self.referenceLayer)
                # remove from overview
                self.iface.actionAddToOverview().activate(0)
                self.pbReference.setText('Show Reference')
            else:
                self.iface.legendInterface().setLayerVisible(self.referenceLayer,True)
                self.iface.setActiveLayer(self.referenceLayer)
                # add to overview
                self.iface.actionAddToOverview().activate(0)
                self.pbReference.setText('Hide Reference')
        
    #
    # view features

    def viewFeatures(self):

        if self.debug == True:
            QgsMessageLog.logMessage('mapNavigator: '+self.myself())

        if self.points_layer <> None and self.lines_layer <> None and self.polygons_layer <> None:
            if self.pbViewFeatures.text() == 'Show Features':
                self.iface.legendInterface().setLayerVisible(self.points_layer, True)
                self.iface.setActiveLayer(self.points_layer)
                # add to overview
                self.iface.actionAddToOverview().activate(0)
                self.iface.legendInterface().setLayerVisible(self.lines_layer, True)
                self.iface.setActiveLayer(self.lines_layer)
                # add to overview
                self.iface.actionAddToOverview().activate(0)
                self.iface.legendInterface().setLayerVisible(self.polygons_layer, True)
                self.iface.setActiveLayer(self.polygons_layer)
                # add to overview
                self.iface.actionAddToOverview().activate(0)
                self.pbViewFeatures.setText('Hide Features')
            else:
                self.iface.legendInterface().setLayerVisible(self.points_layer, False)
                self.iface.setActiveLayer(self.points_layer)
                # remove from overview
                self.iface.actionAddToOverview().activate(0)
                self.iface.legendInterface().setLayerVisible(self.lines_layer, False)
                self.iface.setActiveLayer(self.lines_layer)
                # remove from overview
                self.iface.actionAddToOverview().activate(0)
                self.iface.legendInterface().setLayerVisible(self.polygons_layer, False)
                self.iface.setActiveLayer(self.polygons_layer)
                # remove from overview
                self.iface.actionAddToOverview().activate(0)
                self.pbViewFeatures.setText('Show Features')
            
    #
    # view feature labels

    def viewFeatureLabels(self):

        if self.debug == True:
            QgsMessageLog.logMessage('mapNavigator: '+self.myself())

        if self.points_layer <> None and self.lines_layer <> None and self.polygons_layer <> None:
            if self.pbFeatureLabels.text() == 'Show Labels':
                # polygons
                palyrPolygons = QgsPalLayerSettings()
                palyrPolygons.readFromLayer(self.polygons_layer)
                palyrPolygons.enabled = True
                palyrPolygons.fieldName = 'section_code'
                palyrPolygons.setDataDefinedProperty(QgsPalLayerSettings.Size,True,True,'11','')
                palyrPolygons.writeToLayer(self.polygons_layer)
                # lines
                palyrLines = QgsPalLayerSettings()
                palyrLines.readFromLayer(self.lines_layer)
                palyrLines.enabled = True
                palyrLines.fieldName = 'section_code'
                palyrLines.placement= QgsPalLayerSettings.Line
                palyrLines.placementFlags = QgsPalLayerSettings.AboveLine
                palyrLines.setDataDefinedProperty(QgsPalLayerSettings.Size,True,True,'11','')
                palyrLines.writeToLayer(self.lines_layer)
                # points
                palyrPoints = QgsPalLayerSettings()
                palyrPoints.readFromLayer(self.points_layer)
                palyrPoints.enabled = True
                palyrPoints.fieldName = 'section_code'
                palyrPoints.placement= QgsPalLayerSettings.OverPoint
                palyrPoints.quadrantPosition = QgsPalLayerSettings.QuadrantBelowRight
                palyrPoints.setDataDefinedProperty(QgsPalLayerSettings.Size,True,True,'11','')
                palyrPoints.setDataDefinedProperty(QgsPalLayerSettings.OffsetQuad,True, True, '8','')
                palyrPoints.writeToLayer(self.points_layer)
                # refresh
                self.canvas.refresh()
                self.pbFeatureLabels.setText('Hide Labels')
            else:
                # polygons
                palyrPolygons = QgsPalLayerSettings()
                palyrPolygons.readFromLayer(self.polygons_layer)
                palyrPolygons.enabled = False
                palyrPolygons.writeToLayer(self.polygons_layer)
                # lines
                palyrLines = QgsPalLayerSettings()
                palyrLines.readFromLayer(self.lines_layer)
                palyrLines.enabled = False
                palyrLines.writeToLayer(self.lines_layer)
                # points
                palyrPoints = QgsPalLayerSettings()
                palyrPoints.readFromLayer(self.points_layer)
                palyrPoints.enabled = False
                palyrPoints.writeToLayer(self.points_layer)
                # refresh
                self.canvas.refresh()
                self.pbFeatureLabels.setText('Show Labels')

    #
    # zoom to features

    def zoomFull(self):

        if self.debug == True:
            QgsMessageLog.logMessage('mapNavigator: '+self.myself())

        self.canvas.zoomToFullExtent()

    #
    # zoom to study area

    def zoomToStudyArea(self):

        if self.debug == True:
            QgsMessageLog.logMessage('mapNavigator: '+self.myself())

        self.iface.setActiveLayer(self.boundaryLayer)
        self.iface.zoomToActiveLayer()
        
