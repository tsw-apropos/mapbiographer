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
from PyQt4.QtGui import QWheelEvent
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
import os, datetime, time, json, inspect, re
from ui_mapbio_navigator import Ui_mapbioNavigator

class mapBiographerNavigator(QtGui.QDockWidget, Ui_mapbioNavigator):

    #
    # init method to define globals and make widget / method connections
    
    def __init__(self, iface, baseGroups, boundaryLayerName, enableReference, referenceLayerName):

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
        self.setWindowTitle('LMB - Layers')
        # project settings
        self.projectTree = []
        self.baseGroups = baseGroups
        self.baseGroupIdxs = range(len(baseGroups))
        self.boundaryLayerName = boundaryLayerName
        self.boundaryLayer = None
        self.enableReference = enableReference
        self.referenceLayerName = referenceLayerName
        self.referenceLayer = None
        self.points_layer = None
        self.lines_layer = None
        self.polygons_layer = None
        self.projectLoading = False
        self.defaultBase = ''
        # add panel
        self.iface.mainWindow().addDockWidget(QtCore.Qt.LeftDockWidgetArea, self)
        # panel functionality
        self.setFeatures(self.DockWidgetMovable | self.DockWidgetFloatable | self.DockWidgetClosable)
        #
        # signals and slots setup
        # map options
        QtCore.QObject.connect(self.cbBase, QtCore.SIGNAL("currentIndexChanged(int)"), self.selectBase)
        QtCore.QObject.connect(self.cbBoundary, QtCore.SIGNAL("stateChanged(int)"), self.viewBoundary)
        QtCore.QObject.connect(self.cbReference, QtCore.SIGNAL("stateChanged(int)"), self.viewReference)
        QtCore.QObject.connect(self.cbFeatures, QtCore.SIGNAL("stateChanged(int)"), self.viewFeatures)
        QtCore.QObject.connect(self.cbLabels, QtCore.SIGNAL("stateChanged(int)"), self.viewFeatureLabels)
        # track scale
        self.canvas.scale()
        # open project

        # set canvas view
        if self.boundaryLayer <> None:
            self.canvas.setExtent(self.boundaryLayer.extent())
        else:
            self.canvas.zoomToFullExtent()

    #
    #####################################################
    #           project and panel management            #
    #####################################################

    #
    # load legend tree
    #
    def loadLegendTree(self, root):
        tree = []
        for child in root.children():
            if isinstance(child, QgsLayerTreeGroup):
                tree.append(['group',child.name(),'layers',self.loadLegendTree(child)])
            elif isinstance(child, QgsLayerTreeLayer):
                tree.append(['layer',child.layerName(),child.layerId(),child.layer()])
        return(tree)

    #
    # add group contents to overview
    #
    def addGroupContentsToOverview(self,group):

        for item in group:
            if item[0] == 'group':
                self.addGroupContentsToOverview(item[3])
            elif not 'OPENLAYERS' in item[2].upper():
                # prevent non-cached layers to be used in overview
                self.iface.setActiveLayer(item[3])
                self.iface.actionAddToOverview().activate(0)

    #
    # load base layers
    #
    def loadBaseLayers(self):

        if self.debug == True:
            QgsMessageLog.logMessage('mapNavigator: '+self.myself())

        self.projectLoading = True
        # groups
        root = QgsProject.instance().layerTreeRoot()
        self.projectTree = self.loadLegendTree(root)
        projectGroups = self.iface.legendInterface().groups()
        # set index to identify difference between stored setting list and project index
        for group in self.baseGroups:
            self.baseGroupIdxs[self.baseGroups.index(group)] = projectGroups.index(group)
        self.cbBase.clear()
        self.cbBase.addItems(self.baseGroups)
        # clear overview
        self.iface.actionRemoveAllFromOverview().activate(0)
        # check against settings to determine if we can proceed
        visibleGroupSet = False
        for item in self.projectTree:
            if item[0] == 'group':
                idx = projectGroups.index(item[1])
                if not (group in projectGroups):
                    return(-1)
                elif visibleGroupSet == False:
                    if self.iface.legendInterface().isGroupVisible(idx):
                        self.defaultBase = self.baseGroups.index(item[1])
                        visibleGroupSet = True
                        #self.addGroupContentsToOverview(item[3])
                        self.cbBase.setCurrentIndex(self.defaultBase)
                else:
                    self.iface.legendInterface().setGroupVisible(idx,False)
        # layers
        validLayers = []
        layers = self.iface.legendInterface().layers()
        self.points_layer = None
        self.lines_layer = None
        self.polygons_layer = None
        for layer in layers:
            validLayers.append(layer.name())
            if layer.name() == self.boundaryLayerName:
                self.boundaryLayer = layer
                if self.iface.legendInterface().isLayerVisible(layer):
                    self.iface.setActiveLayer(layer)
                    self.iface.actionAddToOverview().activate(0)
                    self.cbBoundary.setChecked(True)
                else:
                    self.cbBoundary.setChecked(False)
            if layer.name() == self.referenceLayerName:
                self.referenceLayer = layer
                if self.iface.legendInterface().isLayerVisible(layer):
                    self.cbReference.setChecked(True)
                    self.iface.setActiveLayer(layer)
                    self.iface.actionAddToOverview().activate(0)
                else:
                    self.cbReference.setChecked(False)
        # boundary layer
        if not (self.boundaryLayerName in validLayers):
            return(-1)
        # reference layer
        if self.enableReference == True:
            self.cbReference.setEnabled(True)
            if not (self.referenceLayerName in validLayers):
                return(-1)
        else:
            self.cbReference.setDisabled(True)
        # reset show / hide button
        self.cbFeatures.setChecked(True)
        self.cbLabels.setChecked(True)
        self.projectLoading = False

    
    #
    # load interview layers
    #
    def loadInterviewLayers(self):
        
        if self.debug == True:
            QgsMessageLog.logMessage('mapNavigator: '+self.myself())
        validLayers = []
        layers = self.iface.legendInterface().layers()
        self.points_layer = None
        self.lines_layer = None
        self.polygons_layer = None
        for layer in layers:
            validLayers.append(layer.name())
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

    #
    #####################################################
    #              base and reference maps              #
    #####################################################
    #
    # select default base
    #
    def selectDefaultBase(self):

        if self.debug == True:
            QgsMessageLog.logMessage('mapNavigator: '+self.myself())
        if self.defaultBase <> '':
            self.cbBase.setCurrentIndex(self.defaultBase)

    #
    # select base map - this doesn't change overview
    #
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
    #
    def viewBoundary(self):

        if self.debug == True:
            QgsMessageLog.logMessage('mapNavigator: '+self.myself())

        if self.projectLoading == False:
            if self.cbBoundary.isChecked() == False:
                self.iface.legendInterface().setLayerVisible(self.boundaryLayer,False)
                self.iface.setActiveLayer(self.boundaryLayer)
                # remove from overview
                self.iface.actionAddToOverview().activate(0)
            else:
                self.iface.legendInterface().setLayerVisible(self.boundaryLayer,True)
                self.iface.setActiveLayer(self.boundaryLayer)
                # add to overview
                self.iface.actionAddToOverview().activate(0)

    #
    # view reference layer
    #
    def viewReference(self):

        if self.debug == True:
            QgsMessageLog.logMessage('mapNavigator: '+self.myself())

        if self.projectLoading == False:
            if self.cbReference.isChecked() == False:
                self.iface.legendInterface().setLayerVisible(self.referenceLayer,False)
                self.iface.setActiveLayer(self.referenceLayer)
                # remove from overview
                self.iface.actionAddToOverview().activate(0)
            else:
                self.iface.legendInterface().setLayerVisible(self.referenceLayer,True)
                self.iface.setActiveLayer(self.referenceLayer)
                # add to overview
                self.iface.actionAddToOverview().activate(0)
        
    #
    # view features
    #
    def viewFeatures(self):

        if self.debug == True:
            QgsMessageLog.logMessage('mapNavigator: '+self.myself())

        if self.points_layer <> None and self.lines_layer <> None and self.polygons_layer <> None:
            if self.cbFeatures.isChecked():
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
            
    #
    # view feature labels
    #
    def viewFeatureLabels(self):

        if self.debug == True:
            QgsMessageLog.logMessage('mapNavigator: '+self.myself())

        if self.points_layer <> None and self.lines_layer <> None and self.polygons_layer <> None:
            if self.cbLabels.isChecked():
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

