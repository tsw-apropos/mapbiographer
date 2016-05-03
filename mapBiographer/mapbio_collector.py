# -*- coding: utf-8 -*-
"""
/***************************************************************************
 mapBiographerCollector
                                 A QGIS plugin
 Effectively conduct direct to digital map biographies and traditional land
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
import os, datetime, time, shutil, json, inspect, re, processing, glob
import urlparse
from email.utils import parseaddr
from copy import deepcopy
from ui_mapbio_collector import Ui_mapbioCollector
from mapbio_importer import mapBiographerImporter
from mapbio_transcript_importer import mapBiographerTranscriptImporter
from point_tool import lmbMapToolPoint
from line_tool import lmbMapToolLine
from polygon_tool import lmbMapToolPolygon
from qgis.utils import plugins
try:
    import pyaudio, wave
    from audio_recorder import audioRecorder
    from audio_player import audioPlayer
    lmb_audioEnabled = True
except:
    lmb_audioEnabled = False

#
# main class for collector
#
class mapBiographerCollector(QtGui.QDockWidget, Ui_mapbioCollector):

    #
    #####################################################
    #                   basic setup                     #
    #####################################################
    
    #
    # init method to define globals and make widget / method connections
    #
    def __init__(self, iface):

        # attach event hook
        #self.hook = EventHook()
        # debug setup
        self.debug = False
        self.reportTiming = False
        self.debugDepth = 2
        self.initTime = datetime.datetime.now()
        if self.debug and self.debugDepth >= 1:
            self.myself = lambda: inspect.stack()[1][3]
            QgsMessageLog.logMessage(self.myself())
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        # permitted map scale
        self.maxDenom = 2500000
        self.minDenom = 5000
        self.scaleConnection = False
        self.zoomMessage = 'None'
        self.canDigitize = False
        self.showZoomNotices = False
        # begin setup process
        QtGui.QDockWidget.__init__(self)
        self.setupUi(self)
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        self.iface.newProject()
        self.ovPanel = None
        self.dteRecordingDate.clearMaximumDate()
        self.dteRecordingDate.clearMinimumDate()
        # clear selected layers
        tv = iface.layerTreeView()
        tv.selectionModel().clear()
        self.optionalFields = {}
        self.customFields = {}
        # set default projection if none set
        if self.canvas.mapSettings().hasCrsTransformEnabled() == False:
            self.canvas.mapSettings().setCrsTransformEnabled(True)
            self.canvas.mapSettings().setDestinationCrs( QgsCoordinateReferenceSystem(3857) )
        # global variables
        self.projId = None
        self.projDict = {}
        self.intvDict = {}
        self.intvList = []
        self.intvId = 0
        self.recordAudio = False
        self.intTimeSegment = 0
        self.projCode = ''
        self.defaultCode = ''
        self.pointCode = ''
        self.lineCode = ''
        self.polygonCode = ''
        self.defaultSecurity = 'PR'
        # state variables
        self.lmbMode = 'Interview'
        self.featureState = "Empty"
        self.sectionGeometryState = "Unchanged"
        self.interviewState = "Empty"
        self.mediaState = 'paused'
        self.audioPreSlide = 'paused'
        self.geomSourceAction = 'no change'
        self.qgsProjectLoading = True
        # state variables for special actions based on key states
        self.copyPrevious = False
        self.rapidCapture = False
        self.zoomToFeature = False
        # layers
        self.points_layer = None
        self.lines_layer = None
        self.polygons_layer = None
        # vector editing
        self.currentPrimaryCode = ''
        self.currentMediaFiles =  []
        self.editLayer = None
        self.sectionData = None
        # settings variables
        self.dirName = '.'
        self.lastDir = self.dirName
        self.qgsProject = ''
        # add panel
        self.iface.mainWindow().addDockWidget(QtCore.Qt.RightDockWidgetArea, self)
        # panel functionality
        self.setFeatures(self.DockWidgetMovable | self.DockWidgetFloatable)
        #
        # signals and slots setup
        # connect map tools and enable navigation functions
        self.sketchMode = False
        self.connectMapTools()
        # basic interface operation
        # enable audio if libraries are available
        if lmb_audioEnabled:
            # variables
            self.pyAI = None
            self.audioDeviceIndex = None
            self.audioDeviceName = None
            self.audioStartPosition = 0
            self.audioEndPosition = 0
            self.audioCurrentPosition = 0
            self.afName = ''
            self.bitDepth = 16
            self.samplingFrequency = 44100
            # connections
            self.tbMediaPlay.setIcon(QtGui.QIcon(":/plugins/mapbiographer/media_play.png"))
            QtCore.QObject.connect(self.tbMediaPlay, QtCore.SIGNAL("clicked()"), self.audioPlayPause)
            QtCore.QObject.connect(self.pbImportAudio, QtCore.SIGNAL("clicked()"), self.importAudio)
        else:
            self.pbImportAudio.setVisible(False)
            self.tbMediaPlay.setVisible(False)
        # set shortcut at application level so that not over-ridden by QGIS settings
        self.short = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Space"), self)
        self.short.setContext(QtCore.Qt.ApplicationShortcut)
        self.short.activated.connect(self.audioPlayPause)
        # import functions
        QtCore.QObject.connect(self.pbImportFeatures, QtCore.SIGNAL("clicked()"), self.importFeatures)
        QtCore.QObject.connect(self.pbImportTranscript, QtCore.SIGNAL("clicked()"), self.importTranscript)
        QtCore.QObject.connect(self.pbRenumberSections, QtCore.SIGNAL("clicked()"), self.sectionRenumber)
        # interview controls
        QtCore.QObject.connect(self.pbStart, QtCore.SIGNAL("clicked()"), self.interviewStart)
        QtCore.QObject.connect(self.pbPause, QtCore.SIGNAL("clicked()"), self.interviewPause)
        QtCore.QObject.connect(self.pbFinish, QtCore.SIGNAL("clicked()"), self.interviewFinish)
        # section controls
        # section reordering
        QtCore.QObject.connect(self.tbMoveUp, QtCore.SIGNAL("clicked()"), self.sectionMoveUp)
        QtCore.QObject.connect(self.tbMoveDown, QtCore.SIGNAL("clicked()"), self.sectionMoveDown)
        QtCore.QObject.connect(self.tbSort, QtCore.SIGNAL("clicked()"), self.sectionSort)
        # buttons
        QtCore.QObject.connect(self.pbSaveSection, QtCore.SIGNAL("clicked()"), self.sectionSaveEdits)
        # disable CTRL+S for saving project
        self.iface.actionSaveProject().setShortcut("")
        # set shortcut at application level so that not over-ridden by QGIS settings
        self.shortSave = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        self.shortSave.setContext(QtCore.Qt.ApplicationShortcut)
        self.shortSave.activated.connect(self.sectionSaveEdits)
        QtCore.QObject.connect(self.pbCancelSection, QtCore.SIGNAL("clicked()"), self.sectionCancelEdits)
        QtCore.QObject.connect(self.pbDeleteSection, QtCore.SIGNAL("clicked()"), self.sectionDelete)
        # photo controls
        QtCore.QObject.connect(self.pbAddPhoto, QtCore.SIGNAL("clicked()"), self.photoAdd)
        QtCore.QObject.connect(self.pbEditPhoto, QtCore.SIGNAL("clicked()"), self.photoEdit)
        QtCore.QObject.connect(self.pbRemovePhoto, QtCore.SIGNAL("clicked()"), self.photoRemove)
        QtCore.QObject.connect(self.twPhotos, QtCore.SIGNAL("itemSelectionChanged()"), self.photoSelect)
        #
        # photo list widget settings
        self.photoSpacing = 10
        self.thumbnailSize = 112
        self.twPhotos.setIconSize(QtCore.QSize(self.thumbnailSize,self.thumbnailSize))
        self.twPhotos.setColumnCount(2)
        self.twPhotos.setGridStyle(QtCore.Qt.NoPen)
        # Set the default column width and hide the header
        self.twPhotos.verticalHeader().setDefaultSectionSize(self.thumbnailSize+self.photoSpacing)
        self.twPhotos.verticalHeader().hide()
         # Set the default row height and hide the header
        self.twPhotos.horizontalHeader().setDefaultSectionSize(self.thumbnailSize+self.photoSpacing)
        self.twPhotos.horizontalHeader().hide()
        # Set the table width to show all images without horizontal scrolling
        self.twPhotos.setMinimumWidth((self.thumbnailSize+self.photoSpacing)*1+(self.photoSpacing*2))
        #
        # map projections
        canvasCRS = self.canvas.mapSettings().destinationCrs()
        layerCRS = QgsCoordinateReferenceSystem(3857)
        self.xform = QgsCoordinateTransform(canvasCRS, layerCRS)
        #
        # basic map visibility
        QtCore.QObject.connect(self.cbBoundary, QtCore.SIGNAL("stateChanged(int)"), self.baseViewBoundary)
        QtCore.QObject.connect(self.cbReference, QtCore.SIGNAL("stateChanged(int)"), self.baseViewReference)
        QtCore.QObject.connect(self.cbFeatures, QtCore.SIGNAL("stateChanged(int)"), self.baseViewFeatures)
        QtCore.QObject.connect(self.cbLabels, QtCore.SIGNAL("stateChanged(int)"), self.baseViewFeatureLabels)
        #
        self.toolBarCreate()
        #
        # open project
        result = self.settingsRead()
        if result == 0:
            self.customFieldsConfigure()
            result, message = self.collectorOpen()
            if result <> 0:
                QtGui.QMessageBox.information(self, 'LMB Notice',
                    message, QtGui.QMessageBox.Ok)
                self.collectorClose()
            else:
                # set mode
                self.setLMBMode()
        else:
            QtGui.QMessageBox.information(self, 'LMB Notice',
            'Closing because of settings error. Please correct and try again.', QtGui.QMessageBox.Ok)
            self.collectorClose()
    
    #
    # create tool bar
    #

    def toolBarCreate(self):

        self.toolBar = self.iface.addToolBar("LMB Collector Toolbar")
        self.toolBar.setObjectName("lmbCollector")
        
        #
        # LMB Mode
        #
        # add dropdown button
        self.modeButton = QtGui.QToolButton()
        self.modeButton.setText("LMB Mode: Interview")
        self.toolBar.addWidget(self.modeButton)
        # add items to dropdown menu
        self.modeButton.setMenu(QtGui.QMenu(self.modeButton))
        self.setInterviewMode = QtGui.QAction(QtGui.QIcon(''),'Conduct Interview', self.iface.mainWindow())
        self.setInterviewMode.triggered.connect(self.lmbModeMenuInterview)
        self.modeButton.menu().addAction(self.setInterviewMode)
        self.setImportMode = QtGui.QAction(QtGui.QIcon(''),'Import Interview', self.iface.mainWindow())
        self.setImportMode.triggered.connect(self.lmbModeMenuImport)
        self.modeButton.menu().addAction(self.setImportMode)
        self.setTranscriptionMode = QtGui.QAction(QtGui.QIcon(''),'Transcribe Interview', self.iface.mainWindow())
        self.setTranscriptionMode.triggered.connect(self.lmbModeMenuTranscribe)
        self.modeButton.menu().addAction(self.setTranscriptionMode)
        self.toolBar.addSeparator()
        #
        # Audio Device 
        #
        # add dropdown button
        self.deviceButton = QtGui.QToolButton()
        self.deviceButton.setText("Audio Device: Default")
        self.toolBar.addWidget(self.deviceButton)
        # add items to dropdown menu
        self.deviceButton.setMenu(QtGui.QMenu(self.deviceButton))
        self.toolBar.addSeparator()
        #
        # Audio Mode
        #
        # add dropdown button
        self.audioButton = QtGui.QToolButton()
        self.audioButton.setText("Record Audio: False")
        self.toolBar.addWidget(self.audioButton)
        # add items to dropdown menu
        self.audioButton.setMenu(QtGui.QMenu(self.audioButton))
        self.setAudioOn = QtGui.QAction(QtGui.QIcon(''),'Record Audio', self.iface.mainWindow())
        self.setAudioOn.triggered.connect(self.lmbAudioSelected)
        self.audioButton.menu().addAction(self.setAudioOn)
        self.setAudioOff = QtGui.QAction(QtGui.QIcon(''),"Don't Record Audio", self.iface.mainWindow())
        self.setAudioOff.triggered.connect(self.lmbAudioNotSelected)
        self.audioButton.menu().addAction(self.setAudioOff)
        self.toolBar.addSeparator()
        #
        # Select Interview
        #
        # add dropdown button
        self.interviewButton = QtGui.QToolButton()
        self.interviewButton.setText("Interview: None")
        self.toolBar.addWidget(self.interviewButton)
        # add items to dropdown menu
        self.interviewButton.setMenu(QtGui.QMenu(self.interviewButton))
        self.toolBar.addSeparator()
        #
        # Base Map
        #
        # add dropdown button
        self.baseMapButton = QtGui.QToolButton()
        self.baseMapButton.setText("Base Map: ")
        self.toolBar.addWidget(self.baseMapButton)
        # add items to dropdown menu
        self.baseMapButton.setMenu(QtGui.QMenu(self.baseMapButton))
        self.toolBar.addSeparator()
        #
        # Close Button
        #
        self.closeButton = QtGui.QToolButton()
        self.closeButton.setText('Close LMB Collector')
        QtCore.QObject.connect(self.closeButton, QtCore.SIGNAL("clicked()"), self.collectorClose)
        self.toolBar.addWidget(self.closeButton)
        self.toolBar.addSeparator()
        #
        self.toolBarEnableDisableAudio()

    #
    # tool bar set visibility
    #
    def toolBarEnableDisableAudio(self):
        
        # use debug track order of calls
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself() + ' - lmbMode: ' + self.lmbMode)
        # reset to false
        self.recordAudio = False
        self.audioButton.setText("Record Audio: False")
        if self.lmbMode == 'Interview':
            self.audioButton.setEnabled(True)
        else:
            self.audioButton.setDisabled(True)

    #
    # connect map tools
    #
    def connectMapTools(self):
        
        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        # icons
        # replace features
        self.tbPoint.setIcon(QtGui.QIcon(":/plugins/mapbiographer/point.png"))
        self.tbLine.setIcon(QtGui.QIcon(":/plugins/mapbiographer/line.png"))
        self.tbPolygon.setIcon(QtGui.QIcon(":/plugins/mapbiographer/polygon.png"))
        # navigation
        self.tbPan.setIcon(QtGui.QIcon(":/plugins/mapbiographer/pan.png"))
        # edit features
        self.tbEdit.setIcon(QtGui.QIcon(":/plugins/mapbiographer/edit_node.png"))
        self.tbMove.setIcon(QtGui.QIcon(":/plugins/mapbiographer/edit_move.png"))
        # Qgs map tools
        self.panTool = QgsMapToolPan(self.canvas)
        self.pointTool = lmbMapToolPoint(self.canvas)
        self.lineTool = lmbMapToolLine(self.canvas)
        self.polygonTool = lmbMapToolPolygon(self.canvas)
        # connect tool buttons
        # points
        QtCore.QObject.connect(self.tbPoint, QtCore.SIGNAL("clicked()"), self.mapToolsActivatePointCapture)
        self.pointTool.rbFinished.connect(self.mapToolsPlacePoint)
        # lines
        QtCore.QObject.connect(self.tbLine, QtCore.SIGNAL("clicked()"), self.mapToolsActivateLineCapture)
        self.lineTool.rbFinished.connect(self.mapToolsPlaceLine)
        # polygons
        QtCore.QObject.connect(self.tbPolygon, QtCore.SIGNAL("clicked()"), self.mapToolsActivatePolygonCapture)
        self.polygonTool.rbFinished.connect(self.mapToolsPlacePolygon)
        # edit
        QtCore.QObject.connect(self.tbEdit, QtCore.SIGNAL("clicked()"), self.mapToolsActivateSpatialEdit)
        # move
        QtCore.QObject.connect(self.tbMove, QtCore.SIGNAL("clicked()"), self.mapToolsActivateSpatialMove)
        # pan
        QtCore.QObject.connect(self.tbPan, QtCore.SIGNAL("clicked()"), self.mapToolsActivatePanTool)
        # non-spatial / new section
        QtCore.QObject.connect(self.tbNonSpatial, QtCore.SIGNAL("clicked()"), self.sectionCreateNonSpatial)
        # basic navigation
        QtCore.QObject.connect(self.tbZoomData, QtCore.SIGNAL("clicked()"), self.mapZoomToData)
        QtCore.QObject.connect(self.tbZoomArea, QtCore.SIGNAL("clicked()"), self.mapZoomArea)
        QtCore.QObject.connect(self.tbZoomIn, QtCore.SIGNAL("clicked()"), self.mapZoomIn)
        QtCore.QObject.connect(self.tbZoomOut, QtCore.SIGNAL("clicked()"), self.mapZoomOut)
        # add icons
        self.tbZoomIn.setIcon(QtGui.QIcon(":/plugins/mapbiographer/zoom_in.png"))
        self.tbZoomOut.setIcon(QtGui.QIcon(":/plugins/mapbiographer/zoom_out.png"))
        self.tbZoomData.setIcon(QtGui.QIcon(":/plugins/mapbiographer/zoom_data.png"))
        self.tbZoomArea.setIcon(QtGui.QIcon(":/plugins/mapbiographer/zoom_area.png"))
        if 'redLayer' in plugins and 'joinmultiplelines' in plugins:
            QtCore.QObject.connect(self.tbSketchMode, QtCore.SIGNAL("clicked()"), self.mapSetSketchMode)
            self.tbSketchMode.setVisible(True)
            rl = plugins['redLayer']
            #
            self.sketchButton = QtGui.QToolButton(self)
            self.sketchButton.setText("Sketch Line")
            self.sketchButton.setIcon(rl.sketchButton.icon())
            self.sketchButton.setCheckable(True)
            QtCore.QObject.connect(self.sketchButton, QtCore.SIGNAL("clicked()"), self.sketchDrawButton)
            self.hlButtons.addWidget(self.sketchButton)
            self.sketchButton.setVisible(False)
            #
            self.lineButton = QtGui.QToolButton(self)
            self.lineButton.setText("Draw Line Segments")
            self.lineButton.setIcon(rl.penButton.icon())
            self.lineButton.setCheckable(True)
            QtCore.QObject.connect(self.lineButton, QtCore.SIGNAL("clicked()"), self.sketchLineButton)
            self.hlButtons.addWidget(self.lineButton)
            self.lineButton.setVisible(False)
            #
            self.styleButton = QtGui.QToolButton(self)
            self.styleButton.setText("Set color and thickness of sketch")
            self.styleButton.setIcon(rl.canvasButton.icon())
            self.hlButtons.addWidget(self.styleButton)
            self.styleButton.setMenu(rl.canvasMenu())
            self.styleButton.setVisible(False)
            #
            self.eraseButton = QtGui.QToolButton(self)
            self.eraseButton.setText("Erase")
            self.eraseButton.setIcon(rl.eraseButton.icon())
            self.eraseButton.setCheckable(True)
            QtCore.QObject.connect(self.eraseButton, QtCore.SIGNAL("clicked()"), self.sketchEraseButton)
            self.hlButtons.addWidget(self.eraseButton)
            self.eraseButton.setVisible(False)
            #
            self.clearButton = QtGui.QToolButton(self)
            self.clearButton.setText("Clear")
            self.clearButton.setIcon(rl.removeButton.icon())
            QtCore.QObject.connect(self.clearButton, QtCore.SIGNAL("clicked()"), rl.removeSketchesAction.__call__)
            self.hlButtons.addWidget(self.clearButton)
            self.clearButton.setVisible(False)
            #
            self.makeLineButton = QtGui.QToolButton(self)
            self.makeLineButton.setText("Convert sketch to line")
            self.makeLineButton.setIcon(QtGui.QIcon(":/plugins/mapbiographer/red_line.png"))
            QtCore.QObject.connect(self.makeLineButton, QtCore.SIGNAL("clicked()"), self.sketchToLine)
            self.hlButtons.addWidget(self.makeLineButton)
            self.makeLineButton.setVisible(False)
            #
            self.makePolygonButton = QtGui.QToolButton(self)
            self.makePolygonButton.setText("Convert sketch to polygon")
            self.makePolygonButton.setIcon(QtGui.QIcon(":/plugins/mapbiographer/red_polygon.png"))
            QtCore.QObject.connect(self.makePolygonButton, QtCore.SIGNAL("clicked()"), self.sketchToPolygon)
            self.hlButtons.addWidget(self.makePolygonButton)
            self.makePolygonButton.setVisible(False)
        else:
            self.tbSketchMode.setVisible(False)
            messageText = 'Sketch mode needs the Red Layer and Multiline Join plugins installed. Please install them before proceeding.'
            QtGui.QMessageBox.warning(self, 'Action Needed',
                messageText, QtGui.QMessageBox.Ok)

    #
    # disconnect map tools
    #
    def disconnectMapTools(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        # break connections to custom tools
        result = QtCore.QObject.disconnect(self.pointTool, QtCore.SIGNAL("rbFinished(QgsGeometry*)"), self.mapToolsPlacePoint)
        result = QtCore.QObject.disconnect(self.lineTool, QtCore.SIGNAL("rbFinished(QgsGeometry*)"), self.mapToolsPlaceLine)
        result = QtCore.QObject.disconnect(self.polygonTool, QtCore.SIGNAL("rbFinished(QgsGeometry*)"), self.mapToolsPlacePolygon)
        result = QtCore.QObject.disconnect(self.tbPan, QtCore.SIGNAL("clicked()"), self.mapToolsActivatePanTool)
        result = QtCore.QObject.disconnect(self.tbEdit, QtCore.SIGNAL("clicked()"), self.mapToolsActivateSpatialEdit)
        result = QtCore.QObject.disconnect(self.tbMove, QtCore.SIGNAL("clicked()"), self.mapToolsActivateSpatialMove)
        result = QtCore.QObject.disconnect(self.tbZoomData, QtCore.SIGNAL("clicked()"), self.mapZoomToData)
        result = QtCore.QObject.disconnect(self.tbZoomArea, QtCore.SIGNAL("clicked()"), self.mapZoomArea)
        result = QtCore.QObject.disconnect(self.tbZoomIn, QtCore.SIGNAL("clicked()"), self.mapZoomIn)
        result = QtCore.QObject.disconnect(self.tbZoomOut, QtCore.SIGNAL("clicked()"), self.mapZoomOut)
        if 'redLayer' in plugins and 'joinmultiplelines' in plugins:
            result = QtCore.QObject.disconnect(self.tbSketchMode, QtCore.SIGNAL("clicked()"), self.mapSetSketchMode)
            result = QtCore.QObject.disconnect(self.sketchButton, QtCore.SIGNAL("clicked()"), self.sketchDrawButton)
            result = QtCore.QObject.disconnect(self.lineButton, QtCore.SIGNAL("clicked()"), self.sketchLineButton)
            result = QtCore.QObject.disconnect(self.eraseButton, QtCore.SIGNAL("clicked()"), self.sketchEraseButton)
            result = QtCore.QObject.disconnect(self.clearButton, QtCore.SIGNAL("clicked()"), rl.removeSketchesAction.__call__)
            result = QtCore.QObject.disconnect(self.makeLineButton, QtCore.SIGNAL("clicked()"), self.sketchToLine)
            result = QtCore.QObject.disconnect(self.makePolygonButton, QtCore.SIGNAL("clicked()"), self.sketchToLine)

    #
    # connect section controls
    #
    def connectSectionControls(self):
        
        # use debug track order of calls
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        # connect
        QtCore.QObject.connect(self.lwSectionList, QtCore.SIGNAL("itemSelectionChanged()"), self.sectionSelect)
        QtCore.QObject.connect(self.spMediaStart, QtCore.SIGNAL("valueChanged(int)"), self.audioSetStartValue)
        QtCore.QObject.connect(self.spMediaEnd, QtCore.SIGNAL("valueChanged(int)"), self.audioSetEndValue)
        QtCore.QObject.connect(self.dteRecordingDate, QtCore.SIGNAL("dateTimeChanged(const QDateTime&)"), self.sectionEnableSaveCancel)
        QtCore.QObject.connect(self.hsSectionMedia, QtCore.SIGNAL("valueChanged(int)"), self.audioUpdateCurrentPosition)
        QtCore.QObject.connect(self.hsSectionMedia, QtCore.SIGNAL("sliderReleased()"), self.audioSlideAndStart)
        QtCore.QObject.connect(self.hsSectionMedia, QtCore.SIGNAL("sliderPressed()"), self.audioStopAndSlide)
        QtCore.QObject.connect(self.tbSetStart, QtCore.SIGNAL("clicked()"), self.audioSetStart)
        QtCore.QObject.connect(self.tbSetEnd, QtCore.SIGNAL("clicked()"), self.audioSetEnd)
        QtCore.QObject.connect(self.leSearch, QtCore.SIGNAL("textEdited (const QString&)"), self.textSearchSetState)
        QtCore.QObject.connect(self.tbSearchNext, QtCore.SIGNAL("clicked()"), self.textSearchNext)
        QtCore.QObject.connect(self.tbSearchPrevious, QtCore.SIGNAL("clicked()"), self.textSearchPrevious)
        QtCore.QObject.connect(self.cbSectionSecurity, QtCore.SIGNAL("currentIndexChanged(int)"), self.sectionEnableSaveCancel)
        QtCore.QObject.connect(self.cbFeatureSource, QtCore.SIGNAL("currentIndexChanged(int)"), self.sectionMapFeatureSourceChanged)
        QtCore.QObject.connect(self.cbUsePeriod, QtCore.SIGNAL("currentIndexChanged(int)"), self.sectionEnableSaveCancel)
        QtCore.QObject.connect(self.cbTimeOfYear, QtCore.SIGNAL("currentIndexChanged(int)"), self.sectionEnableSaveCancel)
        QtCore.QObject.connect(self.pteSectionTags, QtCore.SIGNAL("textChanged()"), self.sectionEnableSaveCancel)
        QtCore.QObject.connect(self.pteSectionNote, QtCore.SIGNAL("textChanged()"), self.sectionEnableSaveCancel)
        QtCore.QObject.connect(self.pteSectionText, QtCore.SIGNAL("textChanged()"), self.sectionEnableSaveCancel)
        QtCore.QObject.connect(self.lwProjectCodes, QtCore.SIGNAL("itemClicked(QListWidgetItem*)"), self.sectionAddRemoveCodes)
        QtCore.QObject.connect(self.twSectionContent, QtCore.SIGNAL("currentChanged(int)"), self.sectionCheckTabs)
        # connection custom fields
        for rec in self.customWidgets:
            QtCore.QObject.connect(rec['widget'], QtCore.SIGNAL(rec['signal']), self.sectionEnableSaveCancel)
    
    #
    # disconnect section controls
    #
    def disconnectSectionControls(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        # disconnect
        result = QtCore.QObject.disconnect(self.lwSectionList, QtCore.SIGNAL("itemSelectionChanged()"), self.sectionSelect)
        result = QtCore.QObject.disconnect(self.spMediaStart, QtCore.SIGNAL("valueChanged(int)"), self.audioSetStartValue)
        result = QtCore.QObject.disconnect(self.spMediaEnd, QtCore.SIGNAL("valueChanged(int)"), self.audioSetEndValue)
        result = QtCore.QObject.disconnect(self.dteRecordingDate, QtCore.SIGNAL("dateTimeChanged(const QDateTime&)"), self.sectionEnableSaveCancel)
        result = QtCore.QObject.disconnect(self.hsSectionMedia, QtCore.SIGNAL("valueChanged(int)"), self.audioUpdateCurrentPosition)
        result = QtCore.QObject.disconnect(self.hsSectionMedia, QtCore.SIGNAL("sliderReleased()"), self.audioSlideAndStart)
        result = QtCore.QObject.disconnect(self.hsSectionMedia, QtCore.SIGNAL("sliderPressed()"), self.audioStopAndSlide)
        result = QtCore.QObject.disconnect(self.tbSetStart, QtCore.SIGNAL("clicked()"), self.audioSetStart)
        result = QtCore.QObject.disconnect(self.tbSetEnd, QtCore.SIGNAL("clicked()"), self.audioSetEnd)
        result = QtCore.QObject.disconnect(self.leSearch, QtCore.SIGNAL("textEdited (const QString&)"), self.textSearchSetState)
        result = QtCore.QObject.disconnect(self.tbSearchNext, QtCore.SIGNAL("clicked()"), self.textSearchNext)
        result = QtCore.QObject.disconnect(self.tbSearchPrevious, QtCore.SIGNAL("clicked()"), self.textSearchPrevious)
        result = QtCore.QObject.disconnect(self.cbSectionSecurity, QtCore.SIGNAL("currentIndexChanged(int)"), self.sectionEnableSaveCancel)
        result = QtCore.QObject.disconnect(self.cbFeatureSource, QtCore.SIGNAL("currentIndexChanged(int)"), self.sectionMapFeatureSourceChanged)
        result = QtCore.QObject.disconnect(self.cbUsePeriod, QtCore.SIGNAL("currentIndexChanged(int)"), self.sectionEnableSaveCancel)
        result = QtCore.QObject.disconnect(self.cbTimeOfYear, QtCore.SIGNAL("currentIndexChanged(int)"), self.sectionEnableSaveCancel)
        result = QtCore.QObject.disconnect(self.pteSectionTags, QtCore.SIGNAL("textChanged()"), self.sectionEnableSaveCancel)
        result = QtCore.QObject.disconnect(self.pteSectionNote, QtCore.SIGNAL("textChanged()"), self.sectionEnableSaveCancel)
        result = QtCore.QObject.disconnect(self.pteSectionText, QtCore.SIGNAL("textChanged()"), self.sectionEnableSaveCancel)
        result = QtCore.QObject.disconnect(self.lwProjectCodes, QtCore.SIGNAL("itemClicked(QListWidgetItem*)"), self.sectionAddRemoveCodes)
        result = QtCore.QObject.disconnect(self.twSectionContent, QtCore.SIGNAL("currentChanged(int)"), self.sectionCheckTabs)
        # connection custom fields
        for rec in self.customWidgets:
            QtCore.QObject.disconnect(rec['widget'], QtCore.SIGNAL(rec['signal']), self.sectionEnableSaveCancel)
        
    #
    # read QGIS settings
    #
    def settingsRead( self ):

        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        # project dir
        s = QtCore.QSettings()
        rv = s.value('mapBiographer/projectDir')
        if not rv is None and os.path.exists(rv):
            self.dirName = rv
        else:
            self.dirName = '.'
        self.lastDir = self.dirName
        # project id
        rv = s.value('mapBiographer/projectId')
        if rv == None:
            self.projId = None
        else:
            self.projId = int(rv)
        if os.path.exists(os.path.join(self.dirName,'lmb-project-info.json')):
            result = self.projectFileRead()
            return(result)
        else:
            return(-1)

    #
    # read lmb project file
    #
    def projectFileRead(self):

        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        # confirm file present before reading
        nf = os.path.join(self.dirName,'lmb-project-info.json')
        if os.path.exists(nf):
            f = open(nf,'r')
            self.projDict = json.loads(f.read())
            f.close()
            mapData = self.projDict["projects"][str(self.projId)]["lmb_map_settings"]
            if 'qgis_project' not in mapData:
                messageText = 'A QGIS project needs to be defined before conducting, importing or transcribing data'
                response = QtGui.QMessageBox.warning(self, 'Warning',
                    messageText, QtGui.QMessageBox.Ok)
                return(-1)
            else:
                self.qgsProject = mapData["qgis_project"]
                self.baseGroups = mapData["base_groups"]
                self.baseGroupIdxs = range(len(self.baseGroups))
                self.boundaryLayerName = mapData["boundary_layer"]
                if mapData["enable_reference"] == "Yes":
                    self.enableReference = True
                else: 
                    self.enableReference = False
                self.referenceLayerName = mapData["reference_layer"]
                self.minDenom = int(mapData["max_scale"].split(':')[1].replace(',',''))
                self.maxDenom = int(mapData["min_scale"].split(':')[1].replace(',',''))
                if mapData["zoom_notices"] == "Yes":
                    self.showZoomNotices = True
                else:
                    self.showZoomNotices = False
                if 'custom_fields' in self.projDict["projects"][str(self.projId)]:
                    self.customFields = self.projDict["projects"][str(self.projId)]['custom_fields']
                else:
                    self.customFields = []
                # test options fileds by adding definitions here and later replace
                # with proper read statement from project-info.json
#                self.customFields = [{"code": "AnimalCount", "type": "in", "name": "Animal Count"}, 
#                 {"code": "IdConfidence", "type": "sl", "name": "Identification Confidence", "args": "3=High\n2=Medium\n1=Low"},
#                 {"code": "Pipeline", "type": "sl", "name": "Pipepline", "args": "E=Existing\nP=Planned\nN=Newly Built"}, 
#                 {"code": "TextBox", "type": "tb", "name": "Text Box Field"}, 
#                 {"code": "TextArea", "type": "ta", "name": "Text Area Field"}, 
#                 {"code": "Decimal", "type": "dm", "name": "Decimal Field"}, 
#                 {"code": "DateField", "type": "dt", "name": "Date Field"}, 
#                 {"code": "TimeField", "type": "tm", "name": "Time Field"}, 
#                 {"code": "DateTimeField", "type": "d&t", "name": "Date Time Field"}, 
#                 {"code": "WebAddress", "type": "url", "name": "Web Address"}]
                if len(self.projDict["projects"][str(self.projId)]['default_time_periods']) == 0:
                    usePeriod = False
                else:
                    usePeriod = True
                if len(self.projDict["projects"][str(self.projId)]['default_time_of_year']) == 0:
                    timeOfYear = False
                else:
                    timeOfYear = True
                self.optionalFields = {'usePeriod':usePeriod,'timeOfYear':timeOfYear}
                return(0)
            
    #
    # write lmb file
    #
    def projectFileSave(self):

        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        # confirm file present before writing
        nf = os.path.join(self.dirName,'lmb-project-info.json')
        if os.path.exists(nf):
            f = open(nf,'w')
            f.write(json.dumps(self.projDict,indent=4))
            f.close()

    #
    # open collector
    #
    def collectorOpen(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself() + " (starting)")
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        #
        # disable map tips
        mpta = self.iface.actionMapTips()
        if mpta.isChecked() == True:
            mpta.trigger()
        # open overview panel
        iobjs = self.iface.mainWindow().children()
        for obj in iobjs:
            if 'Overview' == obj.objectName() and 'QDockWidget' in str(obj.__class__):
                self.ovPanel = obj
                break
        # show panel
        if self.ovPanel <> None:
            self.ovPanel.show()
        # load project information
        projData = self.projDict["projects"][str(self.projId)]
        self.projCode = projData["code"]
        self.project_codes = []
        self.lwProjectCodes.setMouseTracking(True)
        self.lwProjectCodes.clear()
        codeList = projData["default_codes"]
        #codeList.sort()
        for item in codeList:
            self.project_codes.append(item[0])
            tempItem = QtGui.QListWidgetItem(item[0])
            tempItem.setToolTip(item[1])
            self.lwProjectCodes.addItem(tempItem)
        # close the interface if there are no codes
        if len(codeList) == 0:
            message = 'Can not work without at least one default code'
            return(1, message)
        # set default codes
        self.defaultCode = projData["ns_code"]
        self.pointCode = projData["pt_code"]
        self.lineCode = projData["ln_code"]
        self.polygonCode = projData["pl_code"]
        # section references
        self.cbFeatureSource.clear()
        self.cbFeatureSource.addItems(['none','is unique'])
        self.cbFeatureSource.setCurrentIndex(0)
        # time periods
        self.project_use_period = ['R','U','N']
        self.cbUsePeriod.clear()
        self.cbUsePeriod.addItems(['Refused','Unknown','Not Recorded'])
        for item in projData["default_time_periods"]:
            self.project_use_period.append(item[0])
            self.cbUsePeriod.addItem(item[1])
        self.cbUsePeriod.setCurrentIndex(1)
        # annnual variation
        self.project_time_of_year = ['R','U','N','SP']
        self.cbTimeOfYear.clear()
        self.cbTimeOfYear.addItems(['Refused','Unknown','Not Recorded','Sporadic'])
        for item in projData["default_time_of_year"]:
            self.project_time_of_year.append(item[0])
            self.cbTimeOfYear.addItem(item[1])
        self.cbTimeOfYear.setCurrentIndex(1)
        # security
        self.project_security = ['PU','CO','PR']
        self.cbSectionSecurity.clear()
        self.cbSectionSecurity.addItems(['Public','Community','Private'])
        self.cbSectionSecurity.setCurrentIndex(0)
        # debugging
        if self.debug and self.reportTiming:
            QgsMessageLog.logMessage("about to open qgis project")
            QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        # load QGIS project
        if QgsProject.instance().fileName() <> self.qgsProject:
            self.iface.newProject()
            QgsProject.instance().read(QtCore.QFileInfo(self.qgsProject))
        # debugging
        if self.debug and self.reportTiming:
            QgsMessageLog.logMessage("qgis project opened")
            QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        # use debug track order of calls
        if self.debug and self.debugDepth >= 4:
            QgsMessageLog.logMessage(self.myself() + " (finishing)")
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))

        return(0, "Be Happy")

    #
    # close collector interface
    #
    def collectorClose(self):

        # re-enable saving project shortcut
        self.iface.actionSaveProject().setShortcut("Ctrl+S")
        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        if lmb_audioEnabled:
            # check if audio is playing and stop it
            if self.mediaState == 'playing':
                self.audioPlayPause()
        # disconnect scale notice
        if self.scaleConnection == True:
            QtCore.QObject.disconnect(self.canvas, QtCore.SIGNAL("scaleChanged(double)"), self.mapToolsScaleNotification)
        # unload interview
        try:
            self.interviewUnload()
        except:
            pass
        # disconnect map tools
        try:
            self.disconnectMapTools()
        except:
            pass
        # hide panel
        self.hide()
        # restore window state
        s = QtCore.QSettings()
        geom = s.value('mapBiographer/geom')
        state = s.value('mapBiographer/state')
        self.iface.mainWindow().restoreGeometry(geom)
        self.iface.mainWindow().restoreState(state)
        # deselect active layer and select active layer again
        tv = self.iface.layerTreeView()
        tv.selectionModel().clear()
        a = self.iface.legendInterface().layers()
        if len(a) > 0:
            self.iface.setActiveLayer(a[0])
        self.iface.newProject()
        self.toolBar = None
        self.close()

    #
    # lmb mode menu options
    #
    def lmbModeMenuInterview(self):
        
        self.modeButton.setText('Mode: Interview')
        self.lmbMode = 'Interview'
        self.setLMBMode()

    #
    # lmb mode menue import
    #
    def lmbModeMenuImport(self):
        
        self.modeButton.setText('LMB Mode: Import')
        self.lmbMode = 'Import'
        self.setLMBMode()

    #
    # lmb mode menu transcribe
    #
    def lmbModeMenuTranscribe(self):
        
        self.modeButton.setText('LMB Mode: Transcribe')
        self.lmbMode = 'Transcribe'
        self.setLMBMode()
    
    #
    # set LMB mode - set mode and and visibility and initial status of controls
    #
    def setLMBMode(self):

        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage('****************')
            QgsMessageLog.logMessage(self.myself() + " (starting)")
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        # reload QGIS project
        self.loading = True
        self.baseLoadLayers()
        self.twSectionContent.setCurrentIndex(0)
        # start loading
        self.lblTimer.setText("00:00:00")
        self.lblTimer.setToolTip('0 seconds elapsed in interview')
        # populate lists accordingly
        if lmb_audioEnabled:
            self.audioLoadDeviceList()
        self.interviewLoadList()
        # disable adding features by default
        self.mapToolsDisableDrawing()
        if self.lmbMode == "Import":
            self.frInterviewActions.setVisible(True)
            if self.scaleConnection == True:
                QtCore.QObject.disconnect(self.canvas, QtCore.SIGNAL("scaleChanged(double)"), self.mapToolsScaleNotification)
            if lmb_audioEnabled:
                # hide audio recording
                self.pbImportAudio.setVisible(True)
                self.tbMediaPlay.setVisible(True)
                self.hsSectionMedia.setVisible(True)
            else:
                self.hsSectionMedia.setVisible(False)
                self.tbMediaPlay.setVisible(False)
            # display section reordering
            self.tbMoveUp.setVisible(True)
            self.tbMoveDown.setVisible(True)
            self.tbSort.setVisible(True)
            # show timer
            self.lblTimeOfDay.setVisible(False)
            self.vlLeftOfTimer.setVisible(False)
            self.lblTimer.setVisible(True)
            # show start and end media times
            self.lblMediaStart.setVisible(True)
            self.spMediaStart.setVisible(True)
            self.lblMediaEnd.setVisible(True)
            self.spMediaEnd.setVisible(True)
            # hide start and pause
            self.pbStart.setVisible(False)
            self.pbPause.setVisible(False)
            # show and enable finish
            self.pbFinish.setVisible(True)
            # show import
            self.pbImportFeatures.setVisible(True)
            self.pbImportTranscript.setVisible(True)
            self.pbRenumberSections.setVisible(True)
            # show tabs
            self.twSectionContent.tabBar().setVisible(True)
            # check if valid option exist and if so enable interface
            if len(self.intvList) > 0:
                self.pbImportFeatures.setEnabled(True)
                self.pbImportTranscript.setEnabled(True)
                if lmb_audioEnabled:
                    self.pbImportAudio.setEnabled(True)
                self.pbRenumberSections.setEnabled(True)
                self.tpPhotos.setEnabled(True)
                self.pbFinish.setEnabled(True)
                self.frSectionControls.setEnabled(True)
                self.tbNonSpatial.setEnabled(True)
            else:
                self.pbImportFeatures.setDisabled(True)
                self.pbImportTranscript.setDisabled(True)
                self.pbImportAudio.setDisabled(True)
                self.pbRenumberSections.setDisabled(True)
                self.tpPhotos.setDisabled(True)
                self.pbFinish.setDisabled(True)
                self.frSectionControls.setDisabled(True)
                self.tbNonSpatial.setDisabled(True)
        elif self.lmbMode == 'Transcribe':
            self.frInterviewActions.setVisible(False)
            if self.scaleConnection == True:
                QtCore.QObject.disconnect(self.canvas, QtCore.SIGNAL("scaleChanged(double)"), self.mapToolsScaleNotification)
            # hide section reordering
            self.tbMoveUp.setVisible(False)
            self.tbMoveDown.setVisible(False)
            self.tbSort.setVisible(False)
            if lmb_audioEnabled:
                # display media player
                self.tbMediaPlay.setVisible(True)
                self.hsSectionMedia.setVisible(True)
                self.pbImportAudio.setVisible(False)
            else:
                self.hsSectionMedia.setVisible(False)
                self.tbMediaPlay.setVisible(False)
            # show timer
            self.lblTimeOfDay.setVisible(False)
            self.vlLeftOfTimer.setVisible(False)
            self.lblTimer.setVisible(True)
            # show start and end media times
            self.lblMediaStart.setVisible(True)
            self.spMediaStart.setVisible(True)
            self.lblMediaEnd.setVisible(True)
            self.spMediaEnd.setVisible(True)
            # hide start, pause and finish
            self.pbStart.setVisible(False)
            self.pbPause.setVisible(False)
            self.pbFinish.setVisible(False)
            # hide import
            self.pbImportFeatures.setVisible(False)
            self.pbImportTranscript.setVisible(False)
            self.pbRenumberSections.setVisible(False)
            # show tabs
            self.twSectionContent.tabBar().setVisible(True)
            # check if valid option exist and if so enable interface
            if len(self.intvList) > 0:
                self.tpPhotos.setEnabled(True)
                self.frSectionControls.setEnabled(True)
                self.tbNonSpatial.setEnabled(True)
            else:
                self.tpPhotos.setDisabled(True)
                self.frSectionControls.setDisabled(True)
                self.tbNonSpatial.setDisabled(True)
        elif self.lmbMode == 'Interview':
            self.frInterviewActions.setVisible(True)
            # control digitizing scale
            QtCore.QObject.connect(self.canvas, QtCore.SIGNAL("scaleChanged(double)"), self.mapToolsScaleNotification)
            self.scaleConnection = True
            # hide section reordering
            self.tbMoveUp.setVisible(False)
            self.tbMoveDown.setVisible(False)
            self.tbSort.setVisible(False)
            # hide media player
            self.tbMediaPlay.setVisible(False)
            self.vlLeftOfTimer.setVisible(True)
            self.hsSectionMedia.setVisible(False)
            # show timer
            self.lblTimeOfDay.setVisible(True)
            self.lblTimer.setVisible(True)
            # hide start and end media times
            self.lblMediaStart.setVisible(False)
            self.spMediaStart.setVisible(False)
            self.lblMediaEnd.setVisible(False)
            self.spMediaEnd.setVisible(False)
            # show start, pause and finish
            self.pbStart.setVisible(True)
            self.pbPause.setVisible(True)
            self.pbFinish.setVisible(True)
            self.pbFinish.setDisabled(True)
            # hide import
            self.pbImportFeatures.setVisible(False)
            self.pbImportTranscript.setVisible(False)
            self.pbImportAudio.setVisible(False)
            self.pbRenumberSections.setVisible(False)
            # hide tabs
            self.twSectionContent.tabBar().setVisible(False)
            self.frSectionControls.setDisabled(True)
            # disable section controls
            self.tbNonSpatial.setDisabled(True)
        # adjust interface according to mode
        self.toolBarEnableDisableAudio()
        # activate pan tool
        self.interviewSelect(0)
        if self.debug and self.debugDepth >= 4:
            QgsMessageLog.logMessage(self.myself() + " (finishing)")
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        self.loading = False

    #
    # redefine close event to make sure it closes properly because panel close
    # icon can not be prevented on Mac OS X when panel is floating
    #
    def closeEvent(self, event):

        #if self.traceMode:
        #    self.canvas.viewport().removeEventFilter(self.hook)
        #    self.traceMode = False
        #    self.tbTraceMode.setChecked(False)
        if self.lmbMode == 'Interview' and self.interviewState in ('Running','Paused'):
            self.interviewFinish()
            self.collectorClose()
        if lmb_audioEnabled:
            if self.pyAI <> None:
                self.pyAI.terminate()
            try:
                self.audioStopPlayback()
            except:
                pass
        self.setParent(None)

    #
    # check if string is a valid email
    #
    def emailIsValid(self, email):

        match = re.search(r'[\w.-]+@[\w.-]+.\w+', email)
        if match:
            return True
        else:
            return False
    
    #
    # check if string is a valid url
    #
    def urlIsValid(self, url):
        
        parsed = urlparse.urlparse(url)
        if parsed.netloc == '':
            return False
        else:
            return True

    #
    #####################################################
    #       time operations and notification            #
    #####################################################
    
    #
    # display clock & write audio file to disk each minute if recording
    #
    def timeShow(self):

        # set 24 hr format
        text = time.strftime('%H:%M:%S')
        self.lblTimeOfDay.setText(text)
        if self.startTime <> 0:
            if self.interviewState == 'Running':
                # if running keep track of time difference and set timer display
                timeDiff = time.time() - self.pauseDuration - self.startTime
                m, s = divmod(timeDiff, 60)
                h, m = divmod(m, 60)
                timerText =  "%02d:%02d:%02d" % (h, m, s)
                self.lblTimer.setText(timerText)
                self.lblTimer.setToolTip('%d seconds elapsed in interview' % timeDiff)
                if lmb_audioEnabled:
                    # commit file to disk each minute and start another
                    if self.recordAudio == True and m > self.intTimeSegment:
                        self.intTimeSegment = m
                        self.audioStop()
                        self.audioStartRecording()

    #
    # time string to seconds
    #
    def timeString2Seconds(self, timeString):
        
        ftr = [3600,60,1]
        seconds = sum([a*b for a,b in zip(ftr, map(int,timeString.split(':')))])
        return(seconds)
        
    #
    # seconds to time string
    #
    def seconds2TimeString(self, seconds):
        
        secs = int(seconds)
        if secs / 3600.0 > 1.0:
            hrs = secs / 3600
            remainder = secs % 3600
        else:
            hrs = 0
            remainder = secs
        if remainder / 60.0 > 1.0:
            mins = remainder / 60
            remSecs = remainder % 60
        else:
            mins = 0
            remSecs = secs
        timeString = '%02d:%02d:%02d' % (hrs,mins,remSecs)
        return(timeString)

    #
    #####################################################
    #      open, close and manage interviews            #
    #####################################################
    
    #
    # load interview list into combobox
    #
    def interviewLoadList(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        failMessage = 'No interviews could be found'
        intvData = self.projDict["projects"][str(self.projId)]["documents"]
        self.intvList = []
        for key, value in intvData.iteritems():
            intvFileName = "lmb-p%d-i%d-data.json" % (self.projId,value["id"])
            if os.path.exists(os.path.join(self.dirName, 'interviews', intvFileName)):
                dataExists = True
            else:
                dataExists = False
            nameList = ''
            for uKey,uValue in value["participants"].iteritems():
                partDict = self.projDict["participants"][str(uValue["participant_id"])]
                uName = partDict["first_name"] + ' ' + partDict["last_name"]
                nameList += uName + ', '
            nameList = nameList[:-2]
            if self.lmbMode == "Interview":
                if value["status"] == "N" and not dataExists:
                    self.intvList.append([value["code"],value["id"],nameList,value['start_datetime']])
            elif self.lmbMode == "Import":
                if value["status"] == "N":
                    self.intvList.append([value["code"],value["id"],nameList,value['start_datetime']])
            else:
                if value["status"] == "C":
                    self.intvList.append([value["code"],value["id"],nameList,value['start_datetime']])
        self.intvList.sort()
        # clear list and re-populate
        self.interviewButton.menu().clear()
        i = 0
        for item in self.intvList:
            menuItem_Interview = self.interviewButton.menu().addAction(self.projCode + ":" + item[0])
            # create lambda function
            receiver = lambda interviewIndex=i: self.interviewSelect(interviewIndex)
            # link lambda function to menu action
            self.connect(menuItem_Interview, QtCore.SIGNAL('triggered()'), receiver)
            # add to menu
            self.interviewButton.menu().addAction(menuItem_Interview)
            i += 1
        # enable interface based on mode
        if self.lmbMode == 'Interview':
            if len(self.intvList) > 0:
                self.pbStart.setEnabled(True)
            else:
                self.pbStart.setDisabled(True)
        if self.debug and self.debugDepth >= 4:
            QgsMessageLog.logMessage("Interview Count: %d" % len(self.intvList))

    #
    # select interview 
    #
    def interviewSelect(self, cIndex):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        # remove old interview or blank layers
        self.interviewUnload()
        if len(self.intvList) == 0:
            self.interviewButton.setText("Interview: None")
            # no valid interviews for the selected mode
            self.intvId = None
            self.interview_code = ''
            #self.lblParticipants.setText('No Participants Listed')
            self.tbMediaPlay.setDisabled(True)
            self.hsSectionMedia.setDisabled(True)
            self.mediaState = 'disabled'
        else:
            # there are some valid interviews for the selected mode
            self.interviewButton.setText("Interview: %s" % self.intvList[cIndex][0] )
            self.intvId = self.intvList[cIndex][1]
            self.interview_code = self.intvList[cIndex][0]
            self.interviewStart = self.intvList[cIndex][3]
            self.interviewLoad()
            self.connectSectionControls()
            self.defaultSecurity = self.projDict["projects"][str(self.projId)]["documents"][str(self.intvId)]["default_data_security"]

    #
    # load interview
    #
    def interviewLoad(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself() + " (starting)")
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        # method body
        if lmb_audioEnabled:
            # get path for audio file and create prefix
            fname = "lmb-p%d-i%d-media.wav" % (self.projId,self.intvId)
            self.afName = os.path.join(self.dirName,"media",fname)
            if os.path.exists(self.afName):
                self.tbMediaPlay.setEnabled(True)
                self.hsSectionMedia.setEnabled(True)
                self.mediaState = 'paused'
            else:
                self.tbMediaPlay.setDisabled(True)
                self.hsSectionMedia.setDisabled(True)
                self.mediaState = 'disabled'
        #
        # prepare for new interview
        # reset interview variables
        self.startTime = 0
        self.pauseDuration = 0
        self.startPause = 0
        self.currentSequence = 0
        self.maxCodeNumber = 0
        self.currentCodeNumber = 0
        self.audioPartNo = 1
        self.currentFeature = 'ns'
        self.oldFeature = 'ns'
        self.currentSectionCode = ''
        # load file and layers
        self.interviewFileRead()
        self.interviewAddMapLayers()
        # get keys and add features
        sectionList = []
        self.points_layer.startEditing()
        self.lines_layer.startEditing()
        self.polygons_layer.startEditing()
        #loadTime = datetime.datetime.now()
        for key,value in self.intvDict.iteritems():
            #QgsMessageLog.logMessage(str(key))
            sectionList.append([value["sequence"],key,value["geom_source"]])
            if value["geom_source"] in ("pt","ln","pl"):
                geom = QgsGeometry.fromWkt(value["the_geom"])
                geom.convertToMultiType()
                self.sectionMapFeatureLoad(geom,value["geom_source"],value["section_code"])
            if value["code_integer"] > self.maxCodeNumber:
                self.maxCodeNumber = value["code_integer"]
        self.points_layer.commitChanges()
        self.points_layer.updateExtents()
        self.lines_layer.commitChanges()
        self.lines_layer.updateExtents()
        self.polygons_layer.commitChanges()
        self.polygons_layer.updateExtents()
        #QgsMessageLog.logMessage('Layers Load %s' % str((datetime.datetime.now()-loadTime).total_seconds()))
        sectionList.sort()
        self.cbFeatureSource.clear()
        self.cbFeatureSource.addItems(['none','unique'])
        self.lwSectionList.clear()
        for section in sectionList:
            self.lwSectionList.addItem(section[1])
            if section[2] in ('pt','ln','pl'):
                self.cbFeatureSource.addItem('Same as %s' % section[1])
        # enable navigation
        if len(sectionList) > 0:
            self.twSectionContent.setEnabled(True)
            self.lwProjectCodes.setEnabled(True)
            self.lwSectionList.setCurrentItem(self.lwSectionList.item(0))
        else:
            self.twSectionContent.setDisabled(True)
            self.lwProjectCodes.setDisabled(True)
        # load overview
        self.baseLoadInterviewLayers()
        if self.lwSectionList.count() > 0:
            self.lwSectionList.setItemSelected(self.lwSectionList.item(0),True)
            self.sectionSelect()
        self.mapToolsActivatePanTool()
        self.mapZoomArea()
        # use debug track order of calls
        if self.debug and self.debugDepth >= 4:
            QgsMessageLog.logMessage(self.myself() + " (finishing)")
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        
    #
    # unload interview
    #
    def interviewUnload(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        # method body
        self.interviewState = 'Unload'
        # clear interface 
        self.disconnectSectionControls()
        self.lwSectionList.clear()
        self.cbFeatureSource.clear()
        self.cbFeatureSource.addItems(['none','unique'])
        # remove layers if they exist
        self.interviewRemoveMapLayers()

    #
    # interview file load
    #
    def interviewFileRead(self):

        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        # confirm file present before reading
        fname = "lmb-p%d-i%d-data.json" % (self.projId,self.intvId)
        nf = os.path.join(self.dirName,"interviews",fname)
        if os.path.exists(nf):
            f = open(nf,'r')
            self.intvDict = json.loads(f.read())
            f.close()
        else:
            self.intvDict = {}
        
    #
    # interview file save
    #
    def interviewFileSave(self):
        
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        # confirm file present before writing
        fname = "lmb-p%d-i%d-data.json" % (self.projId,self.intvId)
        rootPath = os.path.join(self.dirName,"interviews")
        nf = os.path.join(rootPath,fname)
        if os.path.exists(nf) or os.path.exists(rootPath):
            f = open(nf,'w')
            f.write(json.dumps(self.intvDict,indent=4))
            f.close()
        else:
            QgsMessageLog.logMessage('%s does not exist.' % nf)
            
    #
    # interview file create
    #
    def interviewFileCreate(self):

        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        # notify user that they can not overwrite an existing interview
        fname = "lmb-p%d-i%d-data.json" % (self.projId,self.intvId)
        nf = os.path.join(self.dirName,"interviews",fname)
        if os.path.exists(nf):
            questionText = "An interview file exists and can not be over-written or added to in interview mode. "
            questionText += "This interview will be reset to completed."
            response = QtGui.QMessageBox.warning(self, 'ERROR',
                        questionText, QtGui.QMessageBox.Ok)
            self.projDict["projects"][str(self.projId)]["documents"][str(self.intvId)]["status"] = "C"
            self.projectFileSave()
            return(-1)
        else:
            f = open(nf,'w')
            self.intvDict = {}
            f.write(json.dumps(self.intvDict))
            f.close()
            return(0)
        
    #
    # add interview map layers in order of polygon, line and point to ensure visibility
    #
    def interviewAddMapLayers(self):

        if self.debug and self.debugDepth >= 3:
            QgsMessageLog.logMessage(self.myself())
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        # load layers
        # polygon layer
        self.polygons_layer = QgsVectorLayer('MultiPolygon?crs=epsg:4326&field=section_code:string(20)&index=yes',"lmb_polygons","memory")
        symbol = QgsFillSymbolV2.createSimple({'color':'#ff7800','outline_color':'#717272','outline_width':'0.6'})
        symbol.setAlpha(0.5)
        self.polygons_layer.rendererV2().setSymbol(symbol)
        QgsMapLayerRegistry.instance().addMapLayer(self.polygons_layer)
        palyrPolygons = QgsPalLayerSettings()
        palyrPolygons.readFromLayer(self.polygons_layer)
        palyrPolygons.enabled = True
        palyrPolygons.fieldName = 'section_code'
        palyrPolygons.setDataDefinedProperty(QgsPalLayerSettings.Size,True,True,'11','')
        palyrPolygons.writeToLayer(self.polygons_layer)
        # lines layer
        self.lines_layer = QgsVectorLayer('MultiLineString?crs=epsg:4326&field=section_code:string(20)&index=yes',"lmb_lines","memory")
        symbol = QgsLineSymbolV2.createSimple({'color':'#ff7800','line_width':'0.6'})
        symbol.setAlpha(0.75)
        self.lines_layer.rendererV2().setSymbol(symbol)
        QgsMapLayerRegistry.instance().addMapLayer(self.lines_layer)
        palyrLines = QgsPalLayerSettings()
        palyrLines.readFromLayer(self.lines_layer)
        palyrLines.enabled = True
        palyrLines.fieldName = 'section_code'
        palyrLines.placement= QgsPalLayerSettings.Line
        palyrLines.placementFlags = QgsPalLayerSettings.AboveLine
        palyrLines.setDataDefinedProperty(QgsPalLayerSettings.Size,True,True,'11','')
        palyrLines.writeToLayer(self.lines_layer)
        # points layer
        self.points_layer = QgsVectorLayer('MultiPoint?crs=epsg:4326&field=section_code:string(20)&index=yes',"lmb_points","memory")
        symbol = QgsMarkerSymbolV2.createSimple({'name':'circle','color':'#ff7800','size':'2.2'})
        symbol.setAlpha(0.5)
        self.points_layer.rendererV2().setSymbol(symbol)
        QgsMapLayerRegistry.instance().addMapLayer(self.points_layer)
        palyrPoints = QgsPalLayerSettings()
        palyrPoints.readFromLayer(self.points_layer)
        palyrPoints.enabled = True
        palyrPoints.fieldName = 'section_code'
        palyrPoints.placement= QgsPalLayerSettings.OverPoint
        palyrPoints.quadrantPosition = QgsPalLayerSettings.QuadrantBelowRight
        palyrPoints.setDataDefinedProperty(QgsPalLayerSettings.Size,True,True,'11','')
        palyrPoints.setDataDefinedProperty(QgsPalLayerSettings.OffsetQuad,True, True, '8','')
        palyrPoints.writeToLayer(self.points_layer)
        # set display fields for map tips
        self.polygons_layer.setDisplayField('section_code')
        self.lines_layer.setDisplayField('section_code')
        self.points_layer.setDisplayField('section_code')

    #
    # remove interview map layers
    #
    def interviewRemoveMapLayers(self):

        if self.debug and self.debugDepth >= 3:
            QgsMessageLog.logMessage(self.myself())
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        try:
            lyrs = self.iface.mapCanvas().layers()
            for lyr in lyrs:
                if lyr.name() in ('lmb_points','lmb_lines','lmb_polygons'):
                    # NOTE: Set active so that another layer does not get accidently removed from overview
                    self.iface.setActiveLayer(lyr)
                    self.iface.actionAddToOverview().activate(0)
                    QgsMapLayerRegistry.instance().removeMapLayer(lyr.id())
            # set variable to none to ensure consitent treatment of these variables
            self.points_layer = None
            self.lines_layer = None
            self.polygons_layer = None
        except:
            pass

    #
    # set interview defaults
    #
    def interviewSetDefaults(self):

        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        # set defaults
        # interview info
        self.startTime = 0
        self.pauseDuration = 0
        self.startPause = 0
        self.audioPartNo = 1
        self.interviewState = 'New'
        # section info
        self.sequence = 0
        self.currentSequence = 0
        self.currentPrimaryCode = ''
        self.previousPrimaryCode = ''
        self.previousSecurity = self.defaultSecurity
        self.previousContentCodes = ''
        self.previousTags = []
        self.previousUsePeriod = 'U'
        self.previousTimeOfYear = 'U'
        self.previousNote = ''
        self.currentFeature = 'ns'
        self.maxCodeNumber = 0
        self.audioSection = 1

    #
    # start interview
    #
    def interviewStart(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage('-----------------')
            QgsMessageLog.logMessage(self.myself())
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        self.interviewSetDefaults()
        # enable section edit controls
        self.frSectionControls.setEnabled(True)
        if self.lmbMode == 'Interview':
            self.modeButton.setDisabled(True)
            self.deviceButton.setDisabled(True)
            self.audioButton.setDisabled(True)
            self.interviewButton.setDisabled(True)
            self.closeButton.setDisabled(True)
            result = self.interviewFileCreate()
            if result == -1:
                self.canvas.unsetMapTool(self.canvas.mapTool())
                self.frSectionControls.setDisabled(True)
                self.modeButton.setEnabled(True)
                self.deviceButton.setEnabled(True)
                self.audioButton.setEnabled(True)
                self.interviewButton.setEnabled(True)
                self.closeButton.setEnabled(True)
                self.interviewUnload()
                self.interviewLoadList()
                return
            # start timer thread
            self.startTime = time.time()
            self.lblTimer.setText('00:00:00')
            self.lblTimer.setToolTip('0 seconds elapsed in interview')
            # setup clock and timer
            self.timer = QtCore.QTimer(self)
            self.timer.timeout.connect(self.timeShow)
            # call time with update event triggered once per second
            self.timer.start(1000)
            self.timeShow()
            if lmb_audioEnabled:
                if self.recordAudio == True:
                    # start audio recording
                    self.audioStartRecording()
            # set main buttons status
            self.pbStart.setDisabled(True)
            self.pbPause.setEnabled(True)
            self.pbFinish.setEnabled(True)
            # set interview state
            self.interviewState = 'Running'
            # create a new section at the start of interview 
            # to capture introductory remarks
            self.sectionCreateNonSpatial()
            self.mapToolsScaleNotification()

    #
    # pause and start interview
    #
    def interviewPause(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        # change label and action if running or paused
        if self.interviewState == 'Running':
            # measure time at start of pause
            self.pauseStart = time.time()
            if lmb_audioEnabled:
                # pause recording if appropriate
                if self.recordAudio == True:
                    # stop audio recording
                    self.audioStop()
            # adjust interface
            self.interviewState = 'Paused'
            self.pbPause.setText('Continue')
            # disable section edit controls
            self.frSectionControls.setDisabled(True)
        else:
            self.pauseEnd = time.time()
            # update pause duration
            self.pauseDuration = self.pauseDuration + self.pauseEnd - self.pauseStart
            if lmb_audioEnabled:
                # continue recording if appropriate
                if self.recordAudio == True:
                    # start audio recording
                    self.audioStartRecording()
            # adjust interface
            self.interviewState = 'Running'
            self.pbPause.setText('Pause')
            # enable section edit controls
            self.frSectionControls.setEnabled(True)
            # switch to pan tool
            self.mapToolsActivatePanTool()
        self.mapToolsScaleNotification()
        
    #
    # finish interview - stop recording, consolidate audio and close of section and interview records
    #
    def interviewFinish(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
            QgsMessageLog.logMessage('-----------------')
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        # set state
        self.copyPrevious = False
        self.rapidCapture = False
        self.zoomToFeature = False
        self.mapToolsDisableDrawing()
        if self.sketchMode:
            self.tbSketchMode.click()
        self.interviewState = 'Finished'
        # reset map tool
        self.canvas.unsetMapTool(self.canvas.mapTool())
        # clean up
        if self.lmbMode == 'Interview':
            self.modeButton.setEnabled(True)
            self.deviceButton.setEnabled(True)
            self.audioButton.setEnabled(True)
            self.interviewButton.setEnabled(True)
            self.closeButton.setEnabled(True)
            # disable pause and finish
            self.pbFinish.setDisabled(True)
            self.pbPause.setDisabled(True)
            # stop timer
            try:
                self.timer.stop()
            except:
                pass 
            self.endTime = time.time()
            self.interviewLength = self.timeString2Seconds(self.lblTimer.text())
            if lmb_audioEnabled:
                if self.recordAudio == True:
                    # stop audio recording and consolidate recordings
                    self.audioStopConsolidate()
                # reset audio setting
                self.lmbAudioNotSelected()
            # update last inteview section
            self.intvDict[self.currentSectionCode]["media_end_time"] = self.interviewLength
            self.interviewFileSave()
            # update interview record
            startString = time.strftime("%Y-%m-%d %H:%M", time.localtime(self.startTime))
            endString = time.strftime("%Y-%m-%d %H:%M", time.localtime(self.endTime))
            self.projDict["projects"][str(self.projId)]["documents"][str(self.intvId)]["start_datetime"] = startString
            self.projDict["projects"][str(self.projId)]["documents"][str(self.intvId)]["end_datetime"] = endString
            self.projDict["projects"][str(self.projId)]["documents"][str(self.intvId)]["status"] = "C"
            self.projectFileSave()
        elif self.lmbMode == 'Import':
            # update interview record
            self.projDict["projects"][str(self.projId)]["documents"][str(self.intvId)]["status"] = "C"
            self.projectFileSave()
            self.tbEdit.setDisabled(True)
            self.tbMove.setDisabled(True)
        # disable interview
        self.frSectionControls.setDisabled(True)
        # clear interview
        self.disconnectSectionControls()
        self.interviewUnload()
        # update interview list
        self.interviewLoadList()
        self.interviewSelect(0)

    #
    #####################################################
    #                 custom fields                     #
    #####################################################
    
    #
    # configure optional and custom fields
    #
    def customFieldsConfigure(self):
            
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        # show or hide optional fields
        if self.optionalFields['usePeriod'] == True:
            self.lblUsePeriod.setVisible(True)
            self.cbUsePeriod.setVisible(True)
        else:
            self.lblUsePeriod.setVisible(False)
            self.cbUsePeriod.setVisible(False)
        if self.optionalFields['timeOfYear'] == True:
            self.lblTimeOfYear.setVisible(True)
            self.cbTimeOfYear.setVisible(True)
        else:
            self.lblTimeOfYear.setVisible(False)
            self.cbTimeOfYear.setVisible(False)
        # add custom fields if needed
        # look for a 'required' data element with value sof True/False field for optional or required fields
        self.customWidgets = []
        for cf in self.customFields:
            rCnt = self.grSectionEdit.rowCount()
            if cf['type'] == 'tb':
                # text box
                # create and place label
                label = QtGui.QLabel()
                label.setText(cf['name'])
                self.grSectionEdit.addWidget(label,rCnt,0)
                label.setVisible(True)
                # create widget
                widget = QtGui.QLineEdit()
                if cf['required'] == True:
                    widget.setStyleSheet("border: 1px solid red;")
                self.grSectionEdit.addWidget(widget,rCnt,1)
                widget.setVisible(True)
                # create dictionary to enable / disable interface based on editing
                self.customWidgets.append({'code':cf['code'],'label':label,'type':cf['type'],'widget':widget,'signal':"textChanged(QString)",'required':cf['required']})
            elif cf['type'] == 'ta':
                # text area
                # create and place label
                label = QtGui.QLabel()
                label.setText(cf['name'])
                self.grSectionEdit.addWidget(label,rCnt,0)
                label.setVisible(True)
                # create widget
                widget = QtGui.QPlainTextEdit()
                if cf['required'] == True:
                    widget.setStyleSheet("border: 1px solid red;")
                self.grSectionEdit.addWidget(widget,rCnt,1)
                widget.setVisible(True)
                # create dictionary to enable / disable interface based on editing
                self.customWidgets.append({'code':cf['code'],'label':label,'type':cf['type'],'widget':widget,'signal':"textChanged()",'required':cf['required']})
            elif cf['type'] == 'sl':
                # select list
                # create and place label
                label = QtGui.QLabel()
                label.setText(cf['name'])
                self.grSectionEdit.addWidget(label,rCnt,0)
                label.setVisible(True)
                # create widget
                widget = QtGui.QComboBox()
                if cf['required'] == False:
                    codes = ['']
                    labels = ['--None--']
                else:
                    widget.setStyleSheet("border: 1px solid red;")
                    codes = []
                    labels = []
                argList = cf['args'].split('\n')
                for arg in argList:
                    a,b = arg.split('=')
                    codes.append(a)
                    labels.append(b)
                widget.addItems(labels)
                self.grSectionEdit.addWidget(widget,rCnt,1)
                widget.setVisible(True)
                # create dictionary to enable / disable interface based on editing
                self.customWidgets.append({'code':cf['code'],'label':label,'type':cf['type'],'widget':widget,'signal':"currentIndexChanged(int)",'codes':codes,'required':cf['required']})
            elif cf['type'] == 'in':
                # integer
                # create and place label
                label = QtGui.QLabel()
                label.setText(cf['name'])
                self.grSectionEdit.addWidget(label,rCnt,0)
                label.setVisible(True)
                # create widget
                widget = QtGui.QLineEdit()
                if cf['required'] == True:
                    widget.setStyleSheet("border: 1px solid red;")
                validator = QtGui.QIntValidator()
                widget.setValidator(validator)
                widget.clear()
                self.grSectionEdit.addWidget(widget,rCnt,1)
                widget.setVisible(True)
                # create dictionary to enable / disable interface based on editing
                self.customWidgets.append({'code':cf['code'],'label':label,'type':cf['type'],'widget':widget,'signal':"textChanged(QString)",'required':cf['required']})
            elif cf['type'] == 'dm':
                # decimal
                # create and place label
                label = QtGui.QLabel()
                label.setText(cf['name'])
                self.grSectionEdit.addWidget(label,rCnt,0)
                label.setVisible(True)
                # create widget
                widget = QtGui.QLineEdit()
                if cf['required'] == True:
                    widget.setStyleSheet("border: 1px solid red;")
                validator = QtGui.QDoubleValidator()
                widget.setValidator(validator)
                widget.clear()
                self.grSectionEdit.addWidget(widget,rCnt,1)
                widget.setVisible(True)
                # create dictionary to enable / disable interface based on editing
                self.customWidgets.append({'code':cf['code'],'label':label,'type':cf['type'],'widget':widget,'signal':"textChanged(QString)",'required':cf['required']})
            elif cf['type'] == 'dt':
                # date
                # create and place label
                label = QtGui.QLabel()
                label.setText(cf['name'])
                self.grSectionEdit.addWidget(label,rCnt,0)
                label.setVisible(True)
                # create widget
                widget = QtGui.QLineEdit()
                if cf['required'] == True:
                    widget.setStyleSheet("border: 1px solid red;")
                widget.setInputMask('9999-99-99')
                widget.clear()
                self.grSectionEdit.addWidget(widget,rCnt,1)
                widget.setVisible(True)
                # create dictionary to enable / disable interface based on editing
                self.customWidgets.append({'code':cf['code'],'label':label,'type':cf['type'],'widget':widget,'signal':'textChanged(QString)','required':cf['required']})
            elif cf['type'] == 'tm':
                # time
                # create and place label
                label = QtGui.QLabel()
                label.setText(cf['name'])
                self.grSectionEdit.addWidget(label,rCnt,0)
                label.setVisible(True)
                # create widget
                widget = QtGui.QLineEdit()
                if cf['required'] == True:
                    widget.setStyleSheet("border: 1px solid red;")
                widget.setInputMask('99:99')
                widget.clear()
                self.grSectionEdit.addWidget(widget,rCnt,1)
                widget.setVisible(True)
                # create dictionary to enable / disable interface based on editing
                self.customWidgets.append({'code':cf['code'],'label':label,'type':cf['type'],'widget':widget,'signal':"textChanged(QString)",'required':cf['required']})
            elif cf['type'] == 'd&t':
                # date and time
                # create and place label
                label = QtGui.QLabel()
                label.setText(cf['name'])
                self.grSectionEdit.addWidget(label,rCnt,0)
                label.setVisible(True)
                # create widget
                widget = QtGui.QLineEdit()
                if cf['required'] == True:
                    widget.setStyleSheet("border: 1px solid red;")
                widget.setInputMask('9999-99-99 99:99')
                widget.clear()
                self.grSectionEdit.addWidget(widget,rCnt,1)
                widget.setVisible(True)
                # create dictionary to enable / disable interface based on editing
                self.customWidgets.append({'code':cf['code'],'label':label,'type':cf['type'],'widget':widget,'signal':"textChanged(QString)",'required':cf['required']})
            elif cf['type'] == 'url':
                # url
                # create and place label
                label = QtGui.QLabel()
                label.setText(cf['name'])
                self.grSectionEdit.addWidget(label,rCnt,0)
                label.setVisible(True)
                # create widget
                widget = QtGui.QLineEdit()
                if cf['required'] == True:
                    widget.setStyleSheet("border: 1px solid red;")
                regex = QtCore.QRegExp('^(https?:\/\/)?([\da-zA-Z\.-]+)\.([a-zA-Z\.]{2,6})([\/\w\.-]*)*\/?$')
                validator = QtGui.QRegExpValidator(regex)
                widget.setValidator(validator)
                widget.clear()
                self.grSectionEdit.addWidget(widget,rCnt,1)
                widget.setVisible(True)
                # create dictionary to enable / disable interface based on editing
                self.customWidgets.append({'code':cf['code'],'label':label,'type':cf['type'],'widget':widget,'signal':"textChanged(QString)",'required':cf['required']})

    #
    # load section custom field values
    #
    def customFieldsLoad(self):
        
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        for cf in self.customWidgets:
            if cf['type'] == 'tb':
                # text box
                if cf['code'] in self.sectionData:
                    cf['widget'].setText(self.sectionData[cf['code']])
                else:
                    cf['widget'].setText('')
            elif cf['type'] == 'ta':
                # text area
                if cf['code'] in self.sectionData:
                    cf['widget'].setPlainText(self.sectionData[cf['code']])
                else:
                    cf['widget'].setPlainText('')
            elif cf['type'] == 'sl':
                # select list
                if cf['code'] in self.sectionData and self.sectionData[cf['code']] <> '':
                    cf['widget'].setCurrentIndex(cf['codes'].index(self.sectionData[cf['code']]))
                else:
                     cf['widget'].setCurrentIndex(0)
            elif cf['type'] == 'in':
                # integer
                if cf['code'] in self.sectionData and self.sectionData[cf['code']] <> '':
                    cf['widget'].setText(str(self.sectionData[cf['code']]))
                else:
                    cf['widget'].setText('')
            elif cf['type'] == 'dm':
                # decimal
                if cf['code'] in self.sectionData and self.sectionData[cf['code']] <> '':
                    cf['widget'].setText(str(self.sectionData[cf['code']]))
                else:
                    cf['widget'].setText('')
            elif cf['type'] == 'dt':
                # date
                if cf['code'] in self.sectionData and self.sectionData[cf['code']] <> '':
                    cf['widget'].setText(self.sectionData[cf['code']])
                else:
                    cf['widget'].setText('')
            elif cf['type'] == 'tm':
                # time
                if cf['code'] in self.sectionData and self.sectionData[cf['code']] <> '':
                    cf['widget'].setText(self.sectionData[cf['code']])
                else:
                    cf['widget'].setText('')
            elif cf['type'] == 'd&t':
                # date and time
                if cf['code'] in self.sectionData and self.sectionData[cf['code']] <> '':
                    cf['widget'].setText(self.sectionData[cf['code']])
                else:
                    cf['widget'].clear()
            elif cf['type'] == 'url':
                # url
                if cf['code'] in self.sectionData:
                    cf['widget'].setText(self.sectionData[cf['code']])
                else:
                    cf['widget'].setText('')
        
    #
    # save section custom field values
    #
    def customFieldsSave(self):
        
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        fieldsValid = True
        messageText = ''
        for cf in self.customWidgets:
            if cf['type'] == 'tb':
                # text box
                if cf['required'] and cf['widget'].text() == '':
                    fieldsValid = False
                    messageText += '"%s" is required and it does not have a valid value\n' % cf['label'].text()
                else:
                    self.sectionData[cf['code']] = cf['widget'].text()
            elif cf['type'] == 'ta':
                # text area
                if cf['required'] and cf['widget'].document().toPlainText() == '':
                    fieldsValid = False
                    messageText += '"%s" is required and it does not have a valid value\n' % cf['label'].text()
                else:
                    self.sectionData[cf['code']] = cf['widget'].document().toPlainText()
            elif cf['type'] == 'sl':
                # select list
                self.sectionData[cf['code']] = cf['codes'][cf['widget'].currentIndex()]
            elif cf['type'] == 'in':
                # integer
                if cf['required'] == True:
                    try:
                        val = int(cf['widget'].text())
                        self.sectionData[cf['code']] = val
                    except:
                        fieldsValid = False
                        messageText += '"%s" is required and it does not have a valid value\n' % cf['label'].text()
                else:
                    if cf['widget'].text() == '':
                        self.sectionData[cf['code']] = ''
                    else:
                        try:
                            val = int(cf['widget'].text())
                            self.sectionData[cf['code']] = val
                        except:
                            fieldsValid = False
                            messageText += '"%s" is optional and it does not have a valid or blank value\n' % cf['label'].text()
            elif cf['type'] == 'dm':
                # decimal
                if cf['required'] == True:
                    try:
                        val = float(cf['widget'].text())
                        self.sectionData[cf['code']] = val
                    except:
                        fieldsValid = False
                        messageText += '"%s" is required and it does not have a valid value\n' % cf['label'].text()
                else:
                    if cf['widget'].text() == '':
                        self.sectionData[cf['code']] = ''
                    else:
                        try:
                            val = float(cf['widget'].text())
                            self.sectionData[cf['code']] = val
                        except:
                            fieldsValid = False
                            messageText += '"%s" is optional and it does not have a valid or blank value\n' % cf['label'].text()
            elif cf['type'] == 'dt':
                # date
                if cf['required'] == True:
                    try:
                        a = datetime.datetime.strptime(cf['widget'].text(),"%Y-%m-%d")
                        self.sectionData[cf['code']] = cf['widget'].text()
                    except:
                        fieldsValid = False
                        messageText += '"%s" is required and it does not have a valid value\n' % cf['label'].text()
                else:
                    if cf['widget'].text().strip(' -:') == '':
                        self.sectionData[cf['code']] = ''
                    else:
                        try:
                            a = datetime.datetime.strptime(cf['widget'].text(),"%Y-%m-%d")
                            self.sectionData[cf['code']] = cf['widget'].text()
                        except:
                            fieldsValid = False
                            messageText += '"%s" is optional and it does not have a valid or blank value\n' % cf['label'].text()
            elif cf['type'] == 'tm':
                # time
                if cf['required'] == True:
                    try:
                        a = datetime.datetime.strptime(cf['widget'].text(),"%H:%M")
                        self.sectionData[cf['code']] = cf['widget'].text()
                    except:
                        fieldsValid = False
                        messageText += '"%s" is required and it does not have a valid value\n' % cf['label'].text()
                else:
                    if cf['widget'].text().strip(' -:') == '':
                        self.sectionData[cf['code']] = ''
                    else:
                        try:
                            a = datetime.datetime.strptime(cf['widget'].text(),"%H:%M")
                            self.sectionData[cf['code']] = cf['widget'].text()
                        except:
                            fieldsValid = False
                            messageText += '"%s" is optional and it does not have a valid or blank value\n' % cf['label'].text()
            elif cf['type'] == 'd&t':
                # date and time
                if cf['required'] == True:
                    try:
                        a = datetime.datetime.strptime(cf['widget'].text(),"%Y-%m-%d %H:%M")
                        self.sectionData[cf['code']] = cf['widget'].text()
                    except:
                        fieldsValid = False
                        messageText += '"%s" is required and it does not have a valid value\n' % cf['label'].text()
                else:
                    if cf['widget'].text().strip(' -:') == '':
                        self.sectionData[cf['code']] = ''   
                    else:
                        try:
                            a = datetime.datetime.strptime(cf['widget'].text(),"%Y-%m-%d %H:%M")
                            self.sectionData[cf['code']] = cf['widget'].text()
                        except:
                            fieldsValid = False
                            messageText += '"%s" is optional and it does not have a valid or blank value\n' % cf['label'].text()
            elif cf['type'] == 'url':
                # url
                if cf['required'] and cf['widget'].text() == '':
                    fieldsValid = False
                    messageText += '"%s" is required and does not have a valid value\n' % cf['label'].text()
                else:
                    self.sectionData[cf['code']] = cf['widget'].text()
        return (fieldsValid, messageText)

    #
    # add custom fields with defaults to new section
    # since heritage provides no default option for required fields
    # this code will generate one and will require staff to be trained
    # to check this value
    #
    def customFieldsAdd(self,tempDict):
        
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        for cf in self.customWidgets:
            if cf['type'] == 'tb':
                # text box
                if cf['required'] == True:
                    tempDict[cf['code']] = 'Value needed!'
                else:
                    tempDict[cf['code']] = ''
            elif cf['type'] == 'sl':
                # select list
                tempDict[cf['code']] = cf['codes'][cf['widget'].currentIndex()]
            elif cf['type'] == 'in':
                # integer
                if cf['required'] == True:
                    tempDict[cf['code']] = 0
                else:
                    tempDict[cf['code']] = ''
            elif cf['type'] == 'dm':
                # decimal
                if cf['required'] == True:
                    tempDict[cf['code']] = 0.0
                else:
                    tempDict[cf['code']] = ''
            elif cf['type'] == 'dt':
                # date
                if cf['required'] == True:
                    tempDict[cf['code']] = datetime.datetime.now().isoformat()[:10]
                else:
                    tempDict[cf['code']] = ''
            elif cf['type'] == 'tm':
                # time
                if cf['required'] == True:
                    tempDict[cf['code']] = datetime.datetime.now().isoformat()[11:16]
                else:
                    tempDict[cf['code']] = ''
            elif cf['type'] == 'd&t':
                # date and time
                if cf['required'] == True:
                    tempDict[cf['code']] = datetime.datetime.now().isoformat()[:16].replace('T',' ')
                else:
                    tempDict[cf['code']] = ''
            elif cf['type'] == 'url':
                # url
                if cf['required'] == True:
                    tempDict[cf['code']] = 'https://louistoolkit.ca'
                else:
                    tempDict[cf['code']] = ''
        
        return(tempDict)

    #
    #####################################################
    #              section edit controls                #
    #####################################################
    
    #
    # enable save, cancel and delete buttons
    #
    def sectionEnableSaveCancel(self):

        if not self.pbSaveSection.isEnabled() and self.featureState <> "Load":
            # use debug track order of calls
            if self.debug:
                QgsMessageLog.logMessage(self.myself())
                if self.debugDepth >= 3:
                    QgsMessageLog.logMessage(' - feature state: ' + self.featureState)
                    QgsMessageLog.logMessage(' - geometry type: ' + self.currentFeature)
                    QgsMessageLog.logMessage(' - geometry state: ' + self.sectionGeometryState)
                if self.reportTiming:
                    QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
            # prevent selected section from being changed
            self.lwSectionList.setDisabled(True)
            if self.interviewState <> 'Running':
                self.modeButton.setDisabled(True)
                self.interviewButton.setDisabled(True)
                self.closeButton.setDisabled(True)
            # enable save and cancel
            self.pbSaveSection.setEnabled(True)
            self.pbCancelSection.setEnabled(True)
            self.pbDeleteSection.setEnabled(True)
            if self.lmbMode == 'Interview':
#                if self.sectionGeometryState == "Added":
#                    self.mapToolsEnableDrawing()
#                else:
#                    self.mapToolsDisableDrawing()
                # disable finish and pause
                self.pbPause.setDisabled(True)
                self.pbFinish.setDisabled(True)
            # disable new section
            self.tbNonSpatial.setDisabled(True)
            self.featureState = 'Edit'

    #
    # enable section cancel and save (optionally) buttons but disable delete
    # this is useful during digitizing of new feaures
    #
    def sectionEnableCancel(self,enableSave=False):

        if not self.pbSaveSection.isEnabled():
            # use debug to track order of calls
            if self.debug and self.debugDepth >= 1:
                QgsMessageLog.logMessage(self.myself())
                QgsMessageLog.logMessage(' - feature state: ' + self.featureState)
                QgsMessageLog.logMessage(' - geometry type: ' + self.currentFeature)
                QgsMessageLog.logMessage(' - geometry state: ' + self.sectionGeometryState)
                if self.reportTiming:
                    QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
            # prevent section from being changed
            self.lwSectionList.setDisabled(True)
            if self.interviewState <> 'Running':
                self.modeButton.setDisabled(True)
                self.interviewButton.setDisabled(True)
                self.closeButton.setDisabled(True)
            self.pbCancelSection.setEnabled(True)
            if self.lmbMode == 'Interview':
                if enableSave == True:
                    self.pbSaveSection.setEnabled(True)
                    # disable drawing map tools
#                    self.mapToolsDisableDrawing()
                else:
                    self.pbSaveSection.setDisabled(True)
                    # enable drawing map tools
#                    if self.mapToolsScaleOK():
#                        self.mapToolsEnableDrawing()
#                        self.mapToolsEnableEditing()
                # disable finish and pause
                self.pbPause.setDisabled(True)
                self.pbFinish.setDisabled(True)
            else:
#                self.mapToolsEnableDrawing()                
#                self.mapToolsEnableEditing()                
                if enableSave == True:
                    self.pbSaveSection.setEnabled(True)
                else:
                    self.pbSaveSection.setDisabled(True)
            self.pbDeleteSection.setDisabled(True)
            self.tbNonSpatial.setDisabled(True)

    #
    # disable save and cancel buttons, but leave delete enabled
    #
    def sectionDisableSaveCancel(self):

        # use debug track order of calls
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
            if self.debugDepth >= 3:
                QgsMessageLog.logMessage(' - feature state: ' + self.featureState)
                QgsMessageLog.logMessage(' - geometry type: ' + self.currentFeature)
                QgsMessageLog.logMessage(' - geometry state: ' + self.sectionGeometryState)
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        # method body
        # allow section from being changed
        self.lwSectionList.setEnabled(True)
        if self.interviewState <> 'Running':
            self.modeButton.setEnabled(True)
            self.interviewButton.setEnabled(True)
            self.closeButton.setEnabled(True)
        # disable save and cancel
        self.pbSaveSection.setDisabled(True)
        self.pbCancelSection.setDisabled(True)
        self.pbDeleteSection.setEnabled(True)
        if self.lmbMode == 'Interview':
            if self.mapToolsScaleOK():
                self.mapToolsEnableDrawing()
            else:
                self.mapToolsDisableDrawing()
            self.tbNonSpatial.setEnabled(True)
            self.pbPause.setEnabled(True)
            self.pbFinish.setEnabled(True)
        else:
            # enable new section tool
            self.tbNonSpatial.setEnabled(True)
            # disable spatial tools because not in interview mode
            self.mapToolsDisableDrawing()
        # adjust state
        if self.featureState == 'Edit':
            self.featureState = 'View'

    #
    # enable / disable section sort buttons
    #
    def sectionSetSortButtons(self):
        
        if self.lmbMode == 'Import':
            if self.debug and self.debugDepth >= 2:
                QgsMessageLog.logMessage(self.myself())
            minRow = 0
            maxRow = self.lwSectionList.count() - 1
            if maxRow > 0:
                row = self.lwSectionList.currentRow()
                if row == maxRow:
                    self.tbMoveUp.setEnabled(True)
                    self.tbMoveDown.setDisabled(True)
                elif row == minRow:
                    self.tbMoveUp.setDisabled(True)
                    self.tbMoveDown.setEnabled(True)
                else:
                    self.tbMoveUp.setEnabled(True)
                    self.tbMoveDown.setEnabled(True)
                self.tbSort.setEnabled(True)
            else:
                self.tbMoveUp.setDisabled(True)
                self.tbMoveDown.setDisabled(True)
                self.tbSort.setDisabled(True)
            
    #
    # add / remove tags to sections
    #
    def sectionAddRemoveCodes(self, item):

        modifiers = QtGui.QApplication.keyboardModifiers()
        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        # only act if editing or viewing, not loading
        if self.featureState in ('View','Edit'):
            # check modifier key
            if modifiers == QtCore.Qt.ControlModifier:
                # assign text making it the primary code
                self.leCode.setText(item.text())
            # determine what items are selected
            selectedItems = self.lwProjectCodes.selectedItems()
            # if removing items check if primary code has been deselected and if so reselect it
            deselected = True
            for item in selectedItems:
                if item.text() == self.leCode.text():
                    deselected = False
            if deselected:
                itemList = self.lwProjectCodes.findItems(self.leCode.text(),QtCore.Qt.MatchExactly)
                self.lwProjectCodes.setItemSelected(itemList[0],True)
                selectedItems = self.lwProjectCodes.selectedItems()
            codeList = []
            sectionCodes = ''
            for item in selectedItems:
                codeList.append(item.text())
            codeList.sort()
            for code in codeList:
                sectionCodes += code + ','
            self.pteContentCodes.setPlainText(sectionCodes[:-1])
            # check if content code has been deselected and if so reselect it
            itemList = self.lwProjectCodes.findItems(self.leCode.text(),QtCore.Qt.MatchExactly)
            self.lwProjectCodes.setItemSelected(itemList[0],True)
            # enable save or cancel
            self.sectionEnableSaveCancel()

    #
    #####################################################
    #   section selection, creation and deletion        #
    #####################################################
    
    #
    # load section record
    #
    def sectionLoadRecord(self):

        # use debug track order of calls
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
            if self.debugDepth >= 3:
                QgsMessageLog.logMessage(' - feature state: ' + self.featureState)
                QgsMessageLog.logMessage(' - geometry type: ' + self.currentFeature)
                QgsMessageLog.logMessage(' - geometry state: ' + self.sectionGeometryState)
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        # set to load state so no change in enabling controls happens
        oldState = self.featureState
        self.featureState = 'Load'
        self.sectionGeometryState = "Unchanged"
        # update section edit controls
        self.dteRecordingDate.setDateTime(datetime.datetime.strptime(self.sectionData["recording_datetime"], "%Y-%m-%d %H:%M"))
        # set time and audio controls
        self.audioStartPosition = int(self.sectionData["media_start_time"])
        self.audioEndPosition = int(self.sectionData["media_end_time"])
        self.audioCurrentPosition = int(self.audioStartPosition)
        self.spMediaStart.setValue(self.audioStartPosition)
        self.spMediaEnd.setValue(self.audioEndPosition)
        self.hsSectionMedia.setMinimum(self.audioStartPosition)
        self.hsSectionMedia.setMaximum(self.audioEndPosition)
        self.hsSectionMedia.setValue(self.audioStartPosition)
        # sequence value
        self.currentSequence = self.sectionData["sequence"]
        # set interface fields
        self.leCode.setText(self.sectionData["code_type"])
        self.cbSectionSecurity.setCurrentIndex(self.project_security.index(self.sectionData["data_security"]))
        geomSource = self.sectionData["geom_source"]
        if geomSource in ('pt','ln','pl'):
            self.cbFeatureSource.setCurrentIndex(1)
        elif geomSource == 'ns':
            self.cbFeatureSource.setCurrentIndex(0)
        else:
            # find matching section code
            idx = self.cbFeatureSource.findText(geomSource, QtCore.Qt.MatchEndsWith)
            if idx <> 0 and idx < self.cbFeatureSource.count():
                self.cbFeatureSource.setCurrentIndex(idx)
            else:
                self.cbFeatureSource.setCurrentIndex(0)
        self.pteContentCodes.setPlainText(",".join(self.sectionData["content_codes"]))
        self.pteSectionTags.setPlainText(",".join(self.sectionData["tags"]))
        self.cbUsePeriod.setCurrentIndex(self.project_use_period.index(self.sectionData["use_period"]))
        self.cbTimeOfYear.setCurrentIndex(self.project_time_of_year.index(self.sectionData["time_of_year"]))
        self.pteSectionNote.setPlainText(self.sectionData["note"])
        # deselect items
        for i in range(self.lwProjectCodes.count()):
            item = self.lwProjectCodes.item(i)
            self.lwProjectCodes.setItemSelected(item,False)
        # select items
        codeList = self.sectionData["content_codes"]
        #QgsMessageLog.logMessage(str(codeList))
        for code in codeList:
            self.lwProjectCodes.setItemSelected(self.lwProjectCodes.findItems(code,QtCore.Qt.MatchExactly)[0], True)
        # set text
        self.pteSectionText.setPlainText(self.sectionData["section_text"])
        if self.sectionData["legacy_code"] <> "":
            self.lblLegacyCode.setText('LC: %s' % self.sectionData["legacy_code"])
        else:
            self.lblLegacyCode.setText('LC: None')
        # load custom fields
        self.customFieldsLoad()
        # add photos to tab if visible
        self.twPhotos.clear()
        self.twPhotos.setRowCount(0)
        self.currentMediaFiles = self.sectionData["media_files"]
        self.photosLoaded = False
        self.sectionCheckTabs()
        # return to view state
        self.featureState = oldState
        
    #
    # section load photos
    #
    def sectionLoadPhotos(self):

        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
        for item in self.sectionData["media_files"]:
            fName = os.path.join(self.dirName,'images',item[0]) 
            if os.path.exists(fName):
                self.photoLoad(fName,item[1])

    #
    # section check tabs
    #
    def sectionCheckTabs(self):

        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
        if self.twSectionContent.currentIndex() == 2 and self.photosLoaded == False:
            self.sectionLoadPhotos()
            self.photosLoaded = True
        
    #
    # section clear selected features
    #
    def sectionClearSelectedFeatures(self):

        if self.debug and self.debugDepth >= 3:
            QgsMessageLog.logMessage(self.myself())
        #self.points_layer.deselect(self.points_layer.selectedFeaturesIds())
        #self.lines_layer.deselect(self.lines_layer.selectedFeaturesIds())
        #self.polygons_layer.deselect(self.polygons_layer.selectedFeaturesIds())
        self.points_layer.setSelectedFeatures([])
        self.lines_layer.setSelectedFeatures([])
        self.polygons_layer.setSelectedFeatures([])
        
    #
    # select section
    #
    def sectionSelect(self):

        # check for keyboard modifier to zoom to feature if shift is held down
        modifiers = QtGui.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.ShiftModifier:
            self.zoomToFeature = True
        else:
            self.zoomToFeature = False
        # select a section
        if self.lwSectionList.currentItem() <> None:
            if self.lmbMode in ('Import','Transcribe') and self.mediaState == 'playing':
                if lmb_audioEnabled:
                    self.audioPlayPause()
            # use debug track order of calls
            if self.debug and self.debugDepth >= 1:
                QgsMessageLog.logMessage(self.myself())
                if self.reportTiming:
                    QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
            self.featureState = 'Select'
            # proceed
            self.geomSourceAction = 'no change'
            self.currentSectionCode = self.lwSectionList.currentItem().text()
            self.sectionData = deepcopy(self.intvDict[self.currentSectionCode])
            self.currentCodeNumber = self.sectionData["code_integer"]
            geomSource = self.sectionData["geom_source"]
            self.currentFeature = geomSource
            # allow for selecting another section
            selectedCode = self.currentSectionCode
            # check if non-spatial
            if self.sectionData["geom_source"] == 'ns':
                self.currentFeature = 'ns'
                # deselect all map features
                self.sectionClearSelectedFeatures()
            else:
                # select spatial feaure
                if not self.sectionData["geom_source"] in ('pt','ln','pl'):
                    # grab id for referenced feature
                    self.currentFeature = 'rf'
                    # get attributes of referenced feature from a different section
                    selectedCode = self.sectionData["geom_source"]
                    geomSource = self.intvDict[selectedCode]["geom_source"]
                    self.sectionSelectMapFeature(geomSource, selectedCode)
                else:
                    self.sectionSelectMapFeature(self.sectionData["geom_source"], self.currentSectionCode)
            if self.currentFeature == 'ns' and self.zoomToFeature:
                self.canvas.zoomToFullExtent()
            # load record
            self.sectionLoadRecord()
            self.pbDeleteSection.setEnabled(True)
            self.featureState = 'View'
            # enable spatial editing if section has spatial feature
            if self.currentFeature in ('pt','ln','pl'):
                self.mapToolsEnableEditing()
            else:
                # disable spatial editing if no feature or referenced feature
                self.mapToolsDisableEditing()
            # for import mode allow reordering of sections
            self.sectionSetSortButtons()
            
    #
    # select map feature
    #
    def sectionSelectMapFeature(self, geomSource, selectedCode):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 3:
            QgsMessageLog.logMessage(self.myself())
        # clear other selections
        self.sectionClearSelectedFeatures()
        # select feature connected to this section
        if geomSource == 'pt':
            featId = self.sectionGetFeatureId(self.points_layer, selectedCode) 
            self.points_layer.select(featId)
            if self.zoomToFeature == True:
                self.canvas.zoomToSelected(self.points_layer)
        elif geomSource == 'ln':
            featId = self.sectionGetFeatureId(self.lines_layer, selectedCode) 
            self.lines_layer.select(featId)
            if self.zoomToFeature == True:
                self.canvas.zoomToSelected(self.lines_layer)
        elif geomSource == 'pl':
            featId = self.sectionGetFeatureId(self.polygons_layer, selectedCode) 
            self.polygons_layer.select(featId)
            if self.zoomToFeature == True:
                self.canvas.zoomToSelected(self.polygons_layer)

    #
    # section select primary code
    #
    def sectionSelectPrimaryCode(self, geomType):

        # if not pre-assigned then assign code by geometry type
        if geomType == 'pt':
            pCode = self.pointCode
        elif geomType == 'ln':
            pCode = self.lineCode
        elif geomType == 'pl':
            pCode = self.polygonCode
        else:
            pCode = self.defaultCode
        return(pCode)
        
    #
    # section calculate section code
    #
    def sectionCalculateSectionCode(self, pCode = '', pNum = -1):
        
        if pCode == '' or pNum == -1:
            sCode = '%s%04d' % (self.currentPrimaryCode,self.currentCodeNumber)
        else:
            sCode = '%s%04d' % (pCode, pNum)
        return(sCode)
        
    #
    # section create record
    #
    def sectionCreateRecord(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage("%s (max: %s)" % (self.myself(), self.maxCodeNumber))
            QgsMessageLog.logMessage(self.featureState)
        # check if feauture tab widget and project codes are disabled and if so
        # enabled them
        if self.lwProjectCodes.isEnabled() == False:
            self.lwProjectCodes.setEnabled(True)
            self.twSectionContent.setEnabled(True)
        # set common values
        self.featureState = 'Create'
        createdText = datetime.datetime.now().isoformat()[:16].replace('T',' ')
        self.section_date_created = createdText
        self.section_date_modified = createdText
        self.section_date_recorded = createdText
        spatial_data_source = 'OS'
        # add or insert records
        if self.lmbMode == 'Interview':
            # adding section 
            # adjust time index of previous record
            media_start_time = self.timeString2Seconds(self.lblTimer.text())
            media_end_time = media_start_time
            # make sure there is a previous section
            if self.lwSectionList.count() >= 1:
                self.intvDict[self.currentSectionCode]["media_end_time"] = media_start_time
            # copying previous values
            if self.copyPrevious == True:
                # need to make sure previous primary code is not blank
                if self.previousPrimaryCode == '':
                    if self.currentPrimaryCode == '':
                        self.currentPrimaryCode = self.sectionSelectPrimaryCode(self.currentFeature)
                        self.previousPrimaryCode = self.currentPrimaryCode
                    else:
                        # if past blank and current not, assign past to current
                        self.previousPrimaryCode = self.currentPrimaryCode
                else:
                    self.currentPrimaryCode = self.previousPrimaryCode
                # copy previous record content
                data_security = self.previousSecurity
                content_codes = self.previousContentCodes
                tags = self.previousTags
                use_period = self.previousUsePeriod
                time_of_year = self.previousTimeOfYear
                note = self.previousNote
            # create new record from scratch
            else:
                self.currentPrimaryCode = self.sectionSelectPrimaryCode(self.currentFeature)
                data_security = self.defaultSecurity
                content_codes = [self.currentPrimaryCode]
                tags = []
                use_period = 'U'
                time_of_year = 'U'
                note = ''
                self.previousPrimaryCode = self.currentPrimaryCode
            # add new record
            self.sequence += 1
            self.maxCodeNumber = self.sequence
            self.currentSequence = self.sequence
            self.currentCodeNumber = self.currentSequence
            self.currentSectionCode = self.sectionCalculateSectionCode()
        elif self.lmbMode in ("Transcribe","Import"):
            # inserting after the selected section
            # adjust time index of previous section
            media_start_time = self.audioEndPosition
            media_end_time = self.audioEndPosition
            if self.currentSectionCode in self.intvDict:
                self.intvDict[self.currentSectionCode]["media_end_time"] = media_start_time
            # create new record
            self.currentPrimaryCode = self.sectionSelectPrimaryCode(self.currentFeature)
            data_security = self.defaultSecurity
            content_codes = [self.currentPrimaryCode]
            tags = []
            use_period = 'U'
            time_of_year = 'U'
            note = ''
            # increase the sequence values of records after the current one
            newSequence = self.currentSequence + 1
            for key, value in self.intvDict.iteritems():
                if value["sequence"] >= newSequence:
                    value["sequence"] += 1
            self.maxCodeNumber += 1
            self.currentCodeNumber = self.maxCodeNumber
            self.currentSequence = newSequence
            self.currentSectionCode = self.sectionCalculateSectionCode()
        # now write the record to the file
        temp = {
            "code_type": self.currentPrimaryCode,
            "code_integer": self.maxCodeNumber,
            "sequence": self.currentSequence,
            "section_code": self.currentSectionCode,
            "legacy_code": "",
            "data_security": data_security,
            "section_text": "",
            "note": note,
            "use_period": use_period,
            "time_of_year": time_of_year,
            "spatial_data_source": spatial_data_source,
            "spatial_data_scale": "",
            "tags": tags,
            "content_codes": content_codes,
            "media_files": [],
            "media_start_time": media_start_time,
            "media_end_time": media_end_time,
            "the_geom": "",
            "geom_source": "ns",
            "date_created": self.section_date_created,
            "date_modified": self.section_date_modified,
            "recording_datetime": self.section_date_recorded
        }
        temp = self.customFieldsAdd(temp)
        self.intvDict[self.currentSectionCode] = temp
        self.sectionData = deepcopy(temp)
        self.interviewFileSave()
        # set defaults
        self.previousPrimaryCode = self.currentPrimaryCode 
        self.previousSecurity = data_security
        self.previousContentCodes = content_codes
        self.previousTags = tags
        self.previousUsePeriod = use_period
        self.previousTimeOfYear = time_of_year
        self.previousNote = note
        self.currentMediaFiles = []
        
    #
    # add section record to list widget - called after a section is fully created
    #
    def sectionAddEntry(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
        # method body
        # clear selected codes
        selectedItems = self.lwProjectCodes.selectedItems()
        for item in selectedItems:
            self.lwProjectCodes.setItemSelected(item,False)
        if self.lmbMode in ('Interview','Import'):
            # add  to end of list and select it in section list
            self.lwSectionList.addItem(self.currentSectionCode)
            self.lwSectionList.setCurrentRow(self.lwSectionList.count()-1)
            # add new section to feature status control
            if self.currentFeature in ('pt','ln','pl'):
                idx = self.cbFeatureSource.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
                if idx == -1:
                    self.cbFeatureSource.addItem('Same as %s' % self.currentSectionCode)
        else:
            # insert into section list after current item and select it
            self.lwSectionList.insertItem(self.lwSectionList.currentRow()+1,self.currentSectionCode)
            # set new row as current which will trigger select and load
            self.lwSectionList.setCurrentRow(self.lwSectionList.currentRow()+1)

    #
    # save section - this is simplified from previous versions
    #
    def sectionSaveEdits(self):
        
        # capture current record information
        self.currentPrimaryCode = self.leCode.text()
        newSectionCode = self.sectionCalculateSectionCode()
        currentGeomSource = self.sectionData["geom_source"]
        # use debug track order of calls
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
            QgsMessageLog.logMessage(newSectionCode)
            if self.debugDepth > 3:
                QgsMessageLog.logMessage('%s (geometry: %s)' % (self.myself(),self.sectionGeometryState))
        # adjust record if section code has changed
        if newSectionCode <>  self.currentSectionCode:
            if self.debug and self.debugDepth >= 3:
                QgsMessageLog.logMessage('Old code: %s, New code: %s ' % (self.currentSectionCode, newSectionCode))
            self.sectionData["section_code"] = newSectionCode
            self.sectionData["code_type"] = self.currentPrimaryCode
            del self.intvDict[self.currentSectionCode]
            self.intvDict[newSectionCode] = self.sectionData
            # update references to this section
            for key, value in self.intvDict.iteritems():
                if value["geom_source"] == self.currentSectionCode:
                    value["geom_source"] = newSectionCode
            # update section list
            self.previousPrimaryCode = self.currentPrimaryCode
            if self.sectionGeometryState == "Unchanged":
                if self.sectionData["geom_source"] in ("pt","ln","pl"):
                    self.sectionMapFeatureUpdateLabel(self.sectionData["geom_source"],self.currentSectionCode,newSectionCode)
                elif self.cbFeatureSource.currentIndex() > 1:
                    selectedCode = self.cbFeatureSource.currentText()[8:]
                    if self.intvDict[newSectionCode]["geom_source"] <> selectedCode:
                        geomSource = self.intvDict[selectedCode]["geom_source"]
                        self.sectionSelectMapFeature(geomSource, selectedCode)
                        self.sectionData["geom_source"] = selectedCode
                        self.sectionSelectMapFeature(geomSource, selectedCode)
                elif self.cbFeatureSource.currentIndex() == 0:
                    self.sectionClearSelectedFeatures()
            elif self.sectionGeometryState == "Deleted":
                # remove from map
                self.sectionMapFeatureDelete(self.currentFeature,self.currentSectionCode)
                # remove from reference list
                idx = self.cbFeatureSource.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
                if idx > -1:
                    self.cbFeatureSource.removeItem(idx)
            elif self.sectionGeometryState in ("Copied","Added"):
                # add to map
                geom = self.sectionData["the_geom"]
                geom.convertToMultiType()
                featureType = self.sectionData["geom_source"]
                if featureType == "pt":
                    self.points_layer.startEditing()
                    self.sectionMapFeatureLoad(geom, featureType, newSectionCode)
                    self.points_layer.commitChanges()
                    self.points_layer.updateExtents()
                elif featureType == "ln":
                    self.lines_layer.startEditing()
                    self.sectionMapFeatureLoad(geom, featureType, newSectionCode)
                    self.lines_layer.commitChanges()
                    self.lines_layer.updateExtents()
                elif featureType == "pl":
                    self.polygons_layer.startEditing()
                    self.sectionMapFeatureLoad(geom, featureType, newSectionCode)
                    self.polygons_layer.commitChanges()
                    self.polygons_layer.updateExtents()
                # add to reference list
                self.cbFeatureSource.addItem('Same as %s' % newSectionCode)
            elif self.sectionGeometryState == "Edited":
                # update map
                self.editLayer.selectAll()
                feat2 = self.editLayer.selectedFeatures()[0]
                self.sectionMapFeatureUpdateGeometry(feat2.geometry(), self.sectionData["geom_source"], self.currentSectionCode)
            # update reference list
            lstIdx = self.cbFeatureSource.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
            if lstIdx <> -1:
                self.cbFeatureSource.setItemText(lstIdx, 'Same as %s' % newSectionCode)
            # set user interface and storage variables to newSectionCode
            self.lwSectionList.currentItem().setText(newSectionCode)
            self.currentSectionCode = newSectionCode
        else:
            if self.sectionGeometryState == "Deleted":
                # remove from map
                self.sectionMapFeatureDelete(self.oldFeature,self.currentSectionCode)
                # remove from reference list
                idx = self.cbFeatureSource.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
                if idx > -1:
                    self.cbFeatureSource.removeItem(idx)
            elif self.sectionGeometryState in ("Copied","Added"):
                # add to map
                geom = QgsGeometry.fromWkt(self.sectionData["the_geom"])
                geom.convertToMultiType()
                featureType = self.sectionData["geom_source"]
                if featureType == "pt":
                    self.points_layer.startEditing()
                    self.sectionMapFeatureLoad(geom, featureType, self.currentSectionCode)
                    self.points_layer.commitChanges()
                    self.points_layer.updateExtents()
                elif featureType == "ln":
                    self.lines_layer.startEditing()
                    self.sectionMapFeatureLoad(geom, featureType, self.currentSectionCode)
                    self.lines_layer.commitChanges()
                    self.lines_layer.updateExtents()
                elif featureType == "pl":
                    self.polygons_layer.startEditing()
                    self.sectionMapFeatureLoad(geom, featureType, self.currentSectionCode)
                    self.polygons_layer.commitChanges()
                    self.polygons_layer.updateExtents()
                # add to reference list
                self.cbFeatureSource.addItem('Same as %s' % self.currentSectionCode)
            elif self.sectionGeometryState == "Edited":
                # update map
                self.editLayer.selectAll()
                feat2 = self.editLayer.selectedFeatures()[0]
                self.sectionMapFeatureUpdateGeometry(feat2.geometry(), self.sectionData["geom_source"], self.currentSectionCode)
            elif self.sectionGeometryState == 'Unchanged':
                if self.cbFeatureSource.currentIndex() > 1:
                    selectedCode = self.cbFeatureSource.currentText()[8:]
                    if self.intvDict[self.currentSectionCode]["geom_source"] <> selectedCode:
                        geomSource = self.intvDict[selectedCode]["geom_source"]
                        self.sectionSelectMapFeature(geomSource, selectedCode)
                        self.sectionData["geom_source"] = selectedCode
                        self.sectionSelectMapFeature(geomSource, selectedCode)
                elif self.cbFeatureSource.currentIndex() == 0:
                    self.sectionClearSelectedFeatures()
        # save other values
        self.previousSecurity = self.project_security[self.cbSectionSecurity.currentIndex()]
        self.previousContentCodes = self.pteContentCodes.document().toPlainText().split(",")
        tagText = self.pteSectionTags.document().toPlainText()
        if tagText == "":
            self.previousTags = []
        else:
            tagList = tagText.split(",")
            self.previousTags = [tag.strip() for tag in tagList]
        self.previousUsePeriod = self.project_use_period[self.cbUsePeriod.currentIndex()]
        self.previousTimeOfYear = self.project_time_of_year[self.cbTimeOfYear.currentIndex()]
        self.previousNote = self.pteSectionNote.document().toPlainText()
        self.previousText = self.pteSectionText.document().toPlainText()
        self.sectionData["code_type"] = self.currentPrimaryCode
        self.sectionData["data_security"] = self.previousSecurity
        self.sectionData["content_codes"] = self.previousContentCodes
        self.sectionData["tags"] = self.previousTags
        self.sectionData["use_period"] = self.previousUsePeriod
        self.sectionData["time_of_year"] = self.previousTimeOfYear
        self.sectionData["note"] = self.previousNote
        self.sectionData["section_text"] = self.previousText
        self.sectionData["media_files"] = self.currentMediaFiles
        self.sectionData["date_modified"] = datetime.datetime.now().isoformat()[:16].replace('T',' ')
        self.sectionData["recording_datetime"] = self.dteRecordingDate.dateTime().toPyDateTime().isoformat()[:16].replace('T',' ')
        if self.lmbMode <> "Interview":
            # correct and adjust media start and end times if needed
            newStart = self.spMediaStart.value()
            newEnd = self.spMediaEnd.value()
            #self.disconnectSectionControls()
            cRow = self.lwSectionList.currentRow()
            #if self.debug and self.debugDepth >= 4:
            #    QgsMessageLog.logMessage('row: %d, start: %d, end %d' % (cRow, newStart, newEnd))
            if newStart <> self.sectionData["media_start_time"]:
                self.sectionCascadeTimeBack(cRow,newStart)
                self.sectionData["media_start_time"] = newStart
                self.audioStartPosition = newStart            
                self.hsSectionMedia.setMinimum(self.audioStartPosition)
                self.hsSectionMedia.setValue(self.audioStartPosition)
            if newEnd <> self.sectionData["media_end_time"]:
                self.sectionCascadeTimeForward(cRow, newEnd)
                self.sectionData["media_end_time"] = newEnd
                self.audioEndPosition = newEnd
                self.hsSectionMedia.setMaximum(self.audioEndPosition)
        valid,message = self.customFieldsSave()
        if not valid:
            QtGui.QMessageBox.warning(self, 'Data Error',
                    message, QtGui.QMessageBox.Ok)
        else:
            self.intvDict[self.currentSectionCode] = deepcopy(self.sectionData)
            self.interviewFileSave()
            self.previousPrimaryCode = self.currentPrimaryCode
            self.sectionDisableSaveCancel()
            self.sectionGeometryState = "Unchanged"
            self.featureState = 'View'

    #
    # cascade media indexes backward in time
    #
    def sectionCascadeTimeBack(self, cRow, nextStart):
        
        if cRow > 0:
            item = self.lwSectionList.item(cRow-1)
            nCode = item.text()
            # use debug track order of calls
            if self.debug and self.debugDepth >= 3:
                QgsMessageLog.logMessage(self.myself() + ' (%s)' % nCode)
            oldStart = self.intvDict[nCode]["media_start_time"]
            oldEnd = self.intvDict[nCode]["media_end_time"]
            if nextStart > 0:
                self.intvDict[nCode]["media_end_time"] = nextStart
            else:
                self.intvDict[nCode]["media_end_time"] = 0
            if nextStart - 2 < oldStart:
                if nextStart > 1:
                    self.intvDict[nCode]["media_start_time"] = nextStart - 1
                    self.sectionCascadeTimeBack(cRow-1, nextStart - 1)
                else:
                    self.intvDict[nCode]["media_start_time"] = 0
                    self.sectionCascadeTimeBack(cRow-1, 0)

    #
    # cascade media indexes foward in time 
    #
    def sectionCascadeTimeForward(self, cRow, prevEnd):
        
        if cRow < self.lwSectionList.count()-1:
            item = self.lwSectionList.item(cRow+1)
            nCode = item.text()
            # use debug track order of calls
            if self.debug and self.debugDepth >= 3:
                QgsMessageLog.logMessage(self.myself() + ' (%s)' % nCode)
            oldStart = self.intvDict[nCode]["media_start_time"]
            oldEnd = self.intvDict[nCode]["media_end_time"]
            self.intvDict[nCode]["media_start_time"] = prevEnd
            if prevEnd+1 > oldEnd:
                self.intvDict[nCode]["media_end_time"] = prevEnd+1
                self.sectionCascadeTimeForward(cRow+1, prevEnd+1)
        
    #
    # cancel edits to section
    #
    def sectionCancelEdits(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
            QgsMessageLog.logMessage(' - feature state: ' + self.featureState)
            QgsMessageLog.logMessage(' - geometry state: ' + self.sectionGeometryState)
            QgsMessageLog.logMessage(' - geometry type: ' + self.currentFeature)
            QgsMessageLog.logMessage('sectionData: ' + self.sectionData["geom_source"])
            QgsMessageLog.logMessage('intvDict: ' + self.intvDict[self.currentSectionCode]["geom_source"])
        # method body
        if self.lmbMode == "Interview":
            if self.featureState == "Create":
                # if creating a new section, abandon edits by resetting tool and deleting new section
                if self.tbPoint.isChecked() == True:
                    self.pointTool.deactivate()
                elif self.tbLine.isChecked() == True:
                    self.lineTool.deactivate()
                elif self.tbPolygon.isChecked == True:
                    self.polygonTool.deactivate()
                del self.intvDict[self.currentSectionCode]
                self.interviewFileSave()
                self.sequence = self.sequence - 1
                # reset
                self.currentSectionCode = self.lwSectionList.currentItem().text()
            elif self.featureState == "Edit":
                if self.sectionGeometryState == "Edited":
                    self.editLayer.commitChanges()
                    QgsMapLayerRegistry.instance().removeMapLayer(self.editLayer.id())
                elif self.sectionGeometryState == "Added":
                    self.sectionMapFeatureDelete(self.currentFeature,self.currentSectionCode)
                    self.sectionClearSelectedFeatures()
            self.sectionData = deepcopy(self.intvDict[self.currentSectionCode])
            self.currentFeature = self.sectionData["geom_source"]
            self.disconnectSectionControls()
            self.sectionLoadRecord()
            self.connectSectionControls()
        else:
            if self.sectionGeometryState == 'Added':
                # if new feature added, delete and reset to non-spatial
                self.sectionMapFeatureDelete(self.currentFeature,self.currentSectionCode)
                self.sectionClearSelectedFeatures()
            elif self.sectionGeometryState == "Edited":
                # if vector edting, abandon changes
                self.editLayer.commitChanges()
                QgsMapLayerRegistry.instance().removeMapLayer(self.editLayer.id())
            # reload
            self.sectionData = deepcopy(self.intvDict[self.currentSectionCode])
            self.currentFeature = self.sectionData["geom_source"]
            self.disconnectSectionControls()
            self.sectionLoadRecord()
            self.connectSectionControls()
        # reset state, tools and widgets
        if self.tbSketchMode.isChecked() == True:
            self.clearButton.click()
            self.tbSketchMode.click()
        self.featureState = 'View'
        self.mapToolsActivatePanTool()
        self.sectionDisableSaveCancel()
        
    #
    # delete section
    #
    def sectionDelete(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        self.disconnectSectionControls()
        # check if referenced by another section
        # Note: that dictionary iteration is rather slow but given the size of the problem
        # this is not anticipated to be a performance causing design and is simpler than trying
        # to maintain a two way link
        isReferenced = False
        for key,value in self.intvDict.iteritems():
            if value["geom_source"] == self.currentSectionCode:
                isReferenced = True
                break
        if isReferenced:
            mText = "The this section are referenced by other sections. "
            mText += "You can not delete it."
            QtGui.QMessageBox.warning(self, 'User Error',
                    mText, QtGui.QMessageBox.Ok)
            return
        # confirm deletion
        messageText = 'Are you sure you want to delete section %s?' % self.currentSectionCode
        response = QtGui.QMessageBox.warning(self, 'Warning',
           messageText, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        if response == QtGui.QMessageBox.Yes:
            # store code locally to avoid any event driven alterations to value
            code = self.currentSectionCode
            # identify previous section
            cRow = self.lwSectionList.currentRow()
            if self.lwSectionList.count() > 1:
                if cRow > 0:
                    prevCode = self.lwSectionList.item(cRow-1).text()
                    if self.intvDict[code]["media_end_time"] > 0:
                        self.intvDict[prevCode]["media_end_time"] = self.intvDict[code]["media_end_time"]
                else:
                    nextCode = self.lwSectionList.item(cRow+1).text()
                    if self.intvDict[code]["media_end_time"] > 0:
                        self.intvDict[nextCode]["media_start_time"] = self.intvDict[code]["media_start_time"]                    
            # adjust media value of previous section
            # debug
            if self.debug and self.debugDepth >= 3:
                QgsMessageLog.logMessage('deleting %s' % code)
            # delete from the file
            del self.intvDict[code]
            self.interviewFileSave()
            # delete from interface
            self.lwSectionList.takeItem(self.lwSectionList.currentRow())
            if self.currentFeature in ('pt','ln','pl'):
                self.sectionMapFeatureDelete(self.currentFeature, code)
            # from from reference list
            idx = self.cbFeatureSource.findText(code, QtCore.Qt.MatchEndsWith)
            if idx > -1:
                self.cbFeatureSource.removeItem(idx)
            # select the adjacent row
            if cRow > 0:
                cRow = cRow - 1
            elif self.lwSectionList.count() > 0:
                cRow = 0
            else:
                cRow = -1
        else:
            cRow = self.lwSectionList.currentRow()
        # reset interface
        self.sectionDisableSaveCancel()
        # cancel spatial edits if delete clicked during editing
        if self.featureState == "Edit Spatial":
            # remove layer
            self.editLayer.commitChanges()
            QgsMapLayerRegistry.instance().removeMapLayer(self.editLayer.id())
            self.mapToolsActivatePanTool()
        # check if there are valid sections
        if self.lwSectionList.count() == 0:
            self.lwProjectCodes.setDisabled(True)
            self.twSectionContent.setDisabled(True)
        # reset sort buttons
        if self.lmbMode == 'Import':
            self.sectionSetSortButtons()
        # deselect anything and disable spatial edit buttons
        if cRow >= 0:
            self.lwSectionList.setCurrentRow(cRow)
            item = self.lwSectionList.item(cRow)
            self.lwSectionList.setItemSelected(item,True)
            self.lwSectionList.setCurrentItem(item)
            self.sectionSelect()
            self.connectSectionControls()
        else:
            self.lwSectionList.setItemSelected(self.lwSectionList.currentItem(),False)
            #self.disconnectSectionControls()
            #self.lwSectionList.clear()
            self.cbFeatureSource.clear()
            self.cbFeatureSource.addItems(['none','unique'])
            self.pbDeleteSection.setDisabled(True)
        self.mapToolsDisableEditing()

    #
    # create non-spatial section
    #
    def sectionCreateNonSpatial(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage("++++")
            QgsMessageLog.logMessage(self.myself())
        # create new section and set it to non-spatial
        self.currentFeature = 'ns'
        self.sectionCreateRecord()
        # reset state
        self.featureState == 'View'
        # add entry to list
        self.sectionAddEntry()
        # set action buttons
        self.sectionDisableSaveCancel()

    #
    # section move up
    #
    def sectionMoveUp(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        self.interviewState = 'Import'
        cSeqVal = self.currentSequence
        nSeqVal = cSeqVal - 1
        cc = self.currentSectionCode
        cseq = self.intvDict[cc]["sequence"]
        # disable section controls to prevent pointless event driven method calls
        self.disconnectSectionControls()
        # get previous section code
        currentRow = self.lwSectionList.currentRow()
        self.lwSectionList.setCurrentRow(currentRow-1)
        pc = self.lwSectionList.currentItem().text()
        pseq = self.intvDict[pc]["sequence"]
        # change sequenc ordering in table
        self.intvDict[cc]["sequence"] = pseq
        self.intvDict[pc]["sequence"] = cseq
        self.interviewFileSave()
        # move previous item down in list in interface
        currentItem = self.lwSectionList.takeItem(currentRow-1)
        self.lwSectionList.insertItem(currentRow, currentItem)
        self.currentSequence = nSeqVal
        self.interviewState = 'View'
        self.sectionSetSortButtons()
        # reconnection section controls
        self.connectSectionControls()

    #
    # section move down
    #
    def sectionMoveDown(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        self.interviewState = 'Import'
        cSeqVal = self.currentSequence
        nSeqVal = cSeqVal + 1
        cc = self.currentSectionCode
        cseq = self.intvDict[cc]["sequence"]
        # disable section controls to prevent pointless event driven method calls
        self.disconnectSectionControls()
        # get next section code
        currentRow = self.lwSectionList.currentRow()
        self.lwSectionList.setCurrentRow(currentRow+1)
        nc = self.lwSectionList.currentItem().text()
        nseq = self.intvDict[nc]["sequence"]
        # change sequenc ordering in table
        self.intvDict[cc]["sequence"] = nseq
        self.intvDict[nc]["sequence"] = cseq
        self.interviewFileSave()
        # move previous item down in list in interface
        currentItem = self.lwSectionList.takeItem(currentRow)
        self.lwSectionList.insertItem(currentRow+1, currentItem)
        self.lwSectionList.setCurrentRow(currentRow+1)
        self.currentSequence = nSeqVal
        self.interviewState = 'View'
        self.sectionSetSortButtons()
        # reconnection section controls
        self.connectSectionControls()

    #
    # section sort
    #
    def sectionSort(self):

        questionText = "This will re-order all sections. This can not be reversed. "
        questionText += "Are you sure you want to do this?"
        response = QtGui.QMessageBox.information(self, 'Re-order features',
                    questionText, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        if response == QtGui.QMessageBox.Yes:
            # use debug track order of calls
            if self.debug and self.debugDepth >= 1:
                QgsMessageLog.logMessage(self.myself())
                if self.reportTiming:
                    QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
            # loop through and set sequence to match the code number 
            for key, value in self.intvDict.iteritems():
                value["sequence"] = value["code_integer"]
            # save changes
            self.interviewFileSave()
            # reload
            self.disconnectSectionControls()
            self.interviewUnload()
            self.interviewLoad()
            self.connectSectionControls()

    #
    # section renumber
    #
    def sectionRenumber(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        questionText = "This will renumber all sections. This can not be reversed. "
        questionText += "Are you sure you want to do this?"
        response = QtGui.QMessageBox.information(self, 'Renumber features',
                    questionText, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        if response == QtGui.QMessageBox.Yes:
            x = 0
            # step 1 - create new codes and remember the names of the old ones
            key_lookup = {}
            newItemList = []
            newSectionList = []
            itemCount = self.lwSectionList.count()
            for i in range(0,itemCount):
                item = self.lwSectionList.item(i)
                currentCode = item.text()
                x += 1
                self.intvDict[currentCode]["code_integer"] = x
                self.intvDict[currentCode]['sequence'] = x
                oldCode = currentCode
                newCode = self.sectionCalculateSectionCode(self.intvDict[currentCode]["code_type"],x)
                key_lookup[oldCode] = newCode
                newItemList.append("Same as %s" % newCode)
                newSectionList.append(newCode)
                self.intvDict[currentCode]["section_code"] = newCode
                src = self.intvDict[currentCode]["geom_source"]
                #if src in ("pt","ln","pl"):
                #    self.sectionMapFeatureUpdateLabel(src,oldCode,newCode)
            # step 2 - change references of old codes to new codes
            for key, value in self.intvDict.iteritems():
                if not value["geom_source"] in ("ns","pt","ln","pl"):
                    value["geom_source"] = key_lookup[value["geom_source"]]
            # step 3 - create new dictionary to replace old so that keys are correct
            newDict = {}
            for key, value in self.intvDict.iteritems():
                newDict[value['section_code']] = value
            self.intvDict = newDict
            # save changes
            self.interviewFileSave()
            # reload
            self.disconnectSectionControls()
            self.interviewUnload()
            self.interviewLoad()
            self.connectSectionControls()
        
    #
    # get feature id
    #
    def sectionGetFeatureId(self, layer, sectionCode):
        
        featId = -1
        featIter = layer.getFeatures(QgsFeatureRequest().setFilterExpression('"section_code" = \'%s\'' % sectionCode))
        for feat in featIter:
            featId = feat.id()
        return(featId)
        
    #
    # map feature source changed
    # note all geometry changes only happen to the dictionary record and 
    # are not reflected in the display until saved
    #
    def sectionMapFeatureSourceChanged(self):

        if not self.pbSaveSection.isEnabled() and self.featureState <> "Load":
            if self.debug: 
                QgsMessageLog.logMessage(self.myself())
                if self.debugDepth >= 3:
                    QgsMessageLog.logMessage(' - feature state: ' + self.featureState)
                    QgsMessageLog.logMessage(' - geometry type: ' + self.currentFeature)
                    QgsMessageLog.logMessage(' - geometry state: ' + self.sectionGeometryState)
                    QgsMessageLog.logMessage(' - sectionData: ' + self.sectionData["geom_source"])
                    QgsMessageLog.logMessage(' - intvDict: ' + self.intvDict[self.currentSectionCode]["geom_source"])
                if self.reportTiming:
                    QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
            # adjust feature state if conducting an interview
            if self.lmbMode == "Interview":
                self.featureState = 'Edit'
            # check feature state
            if self.featureState in ('View','Edit'):
                self.featureState = 'Edit'
                # determine nature of change to geometry
                # non-spatial to spatial
                if self.currentFeature == 'ns' and self.cbFeatureSource.currentIndex() == 1:
                    # enable drawing tools and select point
                    self.mapToolsEnableDrawing()
                    self.mapToolsActivatePointCapture()
                    self.sectionGeometryState = "Added"
                    self.currentFeature = 'pt'
                # non-spatial to link
                elif self.currentFeature == 'ns' and self.cbFeatureSource.currentIndex() > 1:
                    # change currentFeature value and no other action needed
                    referencedCode = self.cbFeatureSource.currentText()[8:]
                    self.sectionData["geom_source"] = referencedCode
                    #self.sectionGeometryState = "Referenced"
                    self.currentFeature = 'rf'
                # spatial to non-spatial
                elif self.currentFeature in ('pt','ln','pl') and self.cbFeatureSource.currentIndex() == 0:
                    # check if feature is referenced by other section
                    isReferenced = False
                    for key,value in self.intvDict.iteritems():
                        if value["geom_source"] == self.currentSectionCode:
                            isReferenced = True
                            break
                    if isReferenced:
                        mText = "The this section and its location is referenced by other sections. "
                        mText += "You can not delete it."
                        QtGui.QMessageBox.warning(self, 'User Error',
                                mText, QtGui.QMessageBox.Ok)
                        self.disconnectSectionControls()
                        self.cbFeatureSource.setCurrentIndex(1)
                        self.connectSectionControls()
                        return
                    # prompt for deletion of current feature
                    questionText = "You have selected to remove the spatial feature for %s. " % self.currentSectionCode
                    questionText += "Are you sure you want to do this?"
                    response = QtGui.QMessageBox.information(self, 'Deleting spatial feature',
                                questionText, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
                    if response == QtGui.QMessageBox.Yes:
                        self.sectionData["the_geom"] = ""
                        self.sectionData["geom_source"] = "ns"
                        self.oldFeature = self.currentFeature
                        self.currentFeature = 'ns'
                        self.sectionGeometryState = "Deleted"
                    else:
                        self.cbFeatureSource.setCurrentIndex(1)
                # spatial to link 
                elif self.currentFeature in ('pt','ln','pl') and self.cbFeatureSource.currentIndex() > 1:
                    # check if referenced by other section
                    isReferenced = False
                    for key,value in self.intvDict.iteritems():
                        if value["geom_source"] == self.currentSectionCode:
                            isReferenced = True
                            break
                    if isReferenced:
                        mText = "The this section and its location is referenced by other sections. "
                        mText += "You can not delete it."
                        QtGui.QMessageBox.warning(self, 'User Error',
                                mText, QtGui.QMessageBox.Ok)
                        self.disconnectSectionControls()
                        self.cbFeatureSource.setCurrentIndex(1)
                        self.connectSectionControls()
                        return
                    # check if self referencing
                    referencedCode = self.cbFeatureSource.currentText()[8:]
                    if referencedCode == self.currentSectionCode:
                        QtGui.QMessageBox.warning(self, 'User Error',
                            'A section can not reference itself', QtGui.QMessageBox.Ok)
                    self.cbFeatureSource.setCurrentIndex(1)
                    # prompt for deletion of feature
                    questionText = "You have selected to remove the spatial feature for %s. " % self.currentSectionCode
                    questionText += "Are you sure you want to do this?"
                    response = QtGui.QMessageBox.information(self, 'Deleting spatial feature',
                                questionText, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
                    if response == QtGui.QMessageBox.Yes:
                        self.sectionData["the_geom"] = ""
                        self.sectionData["geom_source"] = referencedCode
                        self.oldFeature = self.currentFeature
                        self.currentFeature = 'rf'
                        self.sectionGeometryState = "Deleted"
                    else:
                        self.cbFeatureSource.setCurrentIndex(1)
                # link to non-spatial
                elif not self.currentFeature in ('pt','ln','pl','ns') and self.cbFeatureSource.currentIndex() == 0:
                    # change currentFeature value and no other action needed
                    self.sectionData["geom_source"] = "ns"
                    self.currentFeature = 'ns'
                # link to spatial
                elif not self.currentFeature in ('pt','ln','pl','ns') and self.cbFeatureSource.currentIndex() == 1:
                    # prompt to copy linked feature to current feature
                    referencedCode = self.sectionData["geom_source"]
                    questionText = 'You have set this feature as unique and separate from the previously referenced section %s.' % referencedCode
                    questionText += 'The geometry from %s will be copied to this section for editing. ' % referencedCode
                    questionText += 'Are you sure you want to do this?'
                    response = QtGui.QMessageBox.information(self, 'Spatial Feature Changed',
                        questionText, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
                    if response == QtGui.QMessageBox.No:
                        self.cbFeatureSource.setCurrentIndex(1)
                    else:
                        self.sectionData["the_geom"] = self.intvDict[referencedCode]["the_geom"]
                        self.sectionData["geom_source"] = self.intvDict[referencedCode]["geom_source"]
                        self.sectionData["spatial_data_scale"] = self.intvDict[referencedCode]["spatial_data_scale"]
                        self.sectionGeometryState = "Copied"
                # link to other link 
                elif not self.currentFeature in ('pt','ln','pl','ns') and self.cbFeatureSource.currentIndex() > 1:
                    # currentFeature value remains unchanged and no other action needed
                    pass 
                self.sectionEnableSaveCancel()
        if self.debug and self.debugDepth >= 3: 
            QgsMessageLog.logMessage(self.myself() + ' (exit)')
            QgsMessageLog.logMessage(' - sectionData: ' + self.sectionData["geom_source"])
            QgsMessageLog.logMessage(' - intvDict: ' + self.intvDict[self.currentSectionCode]["geom_source"])

    #
    # insert a map feature into a map layer for display
    #
    def sectionMapFeatureLoad(self, geom, featureType, sectionCode):
        
        # use debug track order of calls
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage('%s (%s)' % (self.myself(), sectionCode))
        feat = QgsFeature()
        feat.setGeometry(geom)
        feat.setAttributes([sectionCode])
        if featureType == "pt":
            #self.points_layer.dataProvider().addFeatures([feat])
            self.points_layer.addFeature(feat)
        elif featureType == "ln":
            #self.lines_layer.dataProvider().addFeatures([feat])
            self.lines_layer.addFeature(feat)
        elif featureType == "pl":
            #self.polygons_layer.dataProvider().addFeatures([feat])
            self.polygons_layer.addFeature(feat)
    
    #
    # add map feature to section and display it
    #
    def sectionMapFeatureAdd(self, geom, featureType, sectionCode):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
        if featureType == "pt":
            self.points_layer.startEditing()
            self.sectionMapFeatureLoad(geom, featureType, sectionCode)
            self.points_layer.commitChanges()
            self.points_layer.updateExtents()
        elif featureType == "ln":
            self.lines_layer.startEditing()
            self.sectionMapFeatureLoad(geom, featureType, sectionCode)
            self.lines_layer.commitChanges()
            self.lines_layer.updateExtents()
        elif featureType == "pl":
            self.polygons_layer.startEditing()
            self.sectionMapFeatureLoad(geom, featureType, sectionCode)
            self.polygons_layer.commitChanges()
            self.polygons_layer.updateExtents()
        self.sectionData["geom_source"] = featureType
        self.sectionData["the_geom"] = geom.exportToWkt()
        self.sectionData["spatial_data_scale"] = str(int(self.canvas.scale()))
        self.intvDict[self.currentSectionCode] = deepcopy(self.sectionData)
        self.interviewFileSave()
        # remove layer
        try:
            self.editLayer.commitChanges()
            QgsMapLayerRegistry.instance().removeMapLayer(self.editLayer.id())
        except:
            pass

    #
    # update map feature when a spatial feature is edited
    #
    def sectionMapFeatureUpdateGeometry(self, geom, featureType, sectionCode):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        self.sectionData["geom_source"] = featureType
        self.sectionData["the_geom"] = geom.exportToWkt()
        if featureType == 'pt':
            featId = self.sectionGetFeatureId(self.points_layer, sectionCode)
            self.points_layer.dataProvider().changeGeometryValues({ featId : geom })
            self.points_layer.updateExtents()
        elif featureType == 'ln':
            featId = self.sectionGetFeatureId(self.lines_layer, sectionCode)
            self.lines_layer.dataProvider().changeGeometryValues({ featId : geom })
            self.lines_layer.updateExtents()
        elif featureType == 'pl':
            featId = self.sectionGetFeatureId(self.polygons_layer, sectionCode)
            self.polygons_layer.dataProvider().changeGeometryValues({ featId : geom })
            self.polygons_layer.updateExtents()
        if self.lmbMode == 'Interview':
            # update scale after editing
            self.sectionData["spatial_data_scale"] = str(int(self.canvas.scale()))
        # remove layer
        try:
            self.editLayer.commitChanges()
            QgsMapLayerRegistry.instance().removeMapLayer(self.editLayer.id())
        except:
            pass 
        self.mapToolsActivatePanTool()

    #
    # update section code in spatial layer when the section code changes
    #
    def sectionMapFeatureUpdateLabel(self, featureType, oldCode, newCode):
        
        # use debug track order of calls
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
            QgsMessageLog.logMessage('feature type: %s' % featureType)
            QgsMessageLog.logMessage('old code: %s' % oldCode)
            QgsMessageLog.logMessage('new code: %s' % newCode)
        # update codes
        attrs = { 0 : newCode }
        if featureType == "pt":
            featId = self.sectionGetFeatureId(self.points_layer,oldCode)
            self.points_layer.dataProvider().changeAttributeValues({ featId : attrs })
        elif featureType == "ln":
            featId = self.sectionGetFeatureId(self.lines_layer,oldCode)
            self.lines_layer.dataProvider().changeAttributeValues({ featId : attrs })
        elif featureType == "pl":
            featId = self.sectionGetFeatureId(self.polygons_layer,oldCode)
            self.polygons_layer.dataProvider().changeAttributeValues({ featId : attrs })
        self.canvas.refresh()
        
    #
    # delete map feature from a section
    #
    def sectionMapFeatureDelete(self, featureType, sectionCode):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        # delete spatial records
        if featureType == 'pt':
            featId = self.sectionGetFeatureId(self.points_layer, sectionCode)
            self.points_layer.dataProvider().deleteFeatures([featId])
            self.points_layer.triggerRepaint()
        elif featureType == 'ln':
            featId = self.sectionGetFeatureId(self.lines_layer, sectionCode)
            self.lines_layer.dataProvider().deleteFeatures([featId])
            self.lines_layer.triggerRepaint()
        elif featureType == 'pl':
            featId = self.sectionGetFeatureId(self.polygons_layer, sectionCode)
            self.polygons_layer.dataProvider().deleteFeatures([featId])
            self.polygons_layer.triggerRepaint()
        self.canvas.refresh()

    #
    # copy referenced map feature to a new section in response to user setting feature to be unique
    #
    def sectionMapFeatureCopyReferenced(self, referencedCode):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        # method body
        gs = self.intvDict[referencedCode]["geom_source"]
        # copy feature
        if gs == 'pt':
            # get referenced feature
            featId = self.sectionGetFeatureId(self.points_layer, referencedCode)
            self.points_layer.select(featId)
            oldFeat = self.points_layer.selectedFeatures()[0]
            # duplicate feature
            feat = QgsFeature()
            feat.setGeometry(oldFeat.geometry())
            feat.setAttributes([self.currentSectionCode])
            self.points_layer.dataProvider().addFeatures([feat])
            self.points_layer.updateExtents()
            # store in dictionary
            self.sectionData["the_geom"] = oldFeat.geometry().exportToWkt()
            self.sectionData["geom_source"] = gs
        elif gs == 'ln':
            # get referenced feature
            featId = self.sectionGetFeatureId(self.lines_layer, referencedCode)
            self.lines_layer.select(featId)
            oldFeat = self.lines_layer.selectedFeatures()[0]
            # duplicate feature
            feat = QgsFeature()
            feat.setGeometry(oldFeat.geometry())
            feat.setAttributes([self.currentSectionCode])
            self.lines_layer.dataProvider().addFeatures([feat])
            self.lines_layer.updateExtents()
            # store in dictionary
            self.sectionData["the_geom"] = oldFeat.geometry().exportToWkt()
            self.sectionData["geom_source"] = gs
        elif gs == 'pl':
            # get referenced feature
            featId = self.sectionGetFeatureId(self.polygons_layer, referencedCode)
            self.polygons_layer.select(featId)
            oldFeat = self.polygons_layer.selectedFeatures()[0]
            # duplicate feature
            feat = QgsFeature()
            feat.setGeometry(oldFeat.geometry())
            feat.setAttributes([self.currentSectionCode])
            self.polygons_layer.dataProvider().addFeatures([feat])
            self.polygons_layer.updateExtents()
            # store in dictionary
            self.sectionData["the_geom"] = oldFeat.geometry().exportToWkt()
            self.sectionData["geom_source"] = gs
        self.currentFeature = gs
        return

    #
    #####################################################
    #               section text search                 #
    #####################################################

    #
    # set state of text search
    
    def textSearchSetState(self):
        
        if self.leSearch.text() == "":
            self.tbSearchNext.setDisabled(True)
            self.tbSearchPrevious.setDisabled(True)
        else:
            self.tbSearchNext.setEnabled(True)
            self.tbSearchPrevious.setEnabled(True)
        cursor = self.pteSectionText.textCursor()
        cursor.clearSelection()
        self.pteSectionText.setTextCursor(cursor)
            
    #
    # search from current position or start for string
    
    def textSearchNext(self):
        
        textBody = self.pteSectionText.document().toPlainText().lower()
        searchText = self.leSearch.text()
        searchPhrase = searchText.lower()
        cursor = self.pteSectionText.textCursor()
        cPos = cursor.position() 
        pos = textBody.find(searchPhrase,cPos,len(textBody))
        if pos >= 0:
            cursor.clearSelection()
            cursor.setPosition(pos)
            cursor.setPosition(pos+len(searchPhrase),QtGui.QTextCursor.KeepAnchor) 
            self.pteSectionText.setTextCursor(cursor)
        else:
            message = 'The text "%s" was not found after the current position' % searchText
            QtGui.QMessageBox.information(self, 'Search',
                message, QtGui.QMessageBox.Ok)

    #
    # search from current position or end for string
    
    def textSearchPrevious(self):

        textBody = self.pteSectionText.document().toPlainText().lower()
        searchText = self.leSearch.text()
        searchPhrase = searchText.lower()
        cursor = self.pteSectionText.textCursor()
        cPos = cursor.position() 
        pos = textBody.rfind(searchPhrase,0,cPos-len(searchPhrase))
        if pos >= 0:
            cursor.clearSelection()
            cursor.setPosition(pos)
            cursor.setPosition(pos+len(searchPhrase),QtGui.QTextCursor.KeepAnchor) 
            self.pteSectionText.setTextCursor(cursor)
        else:
            message = 'The text "%s" was not found before the current position' % searchText
            QtGui.QMessageBox.information(self, 'Search',
                message, QtGui.QMessageBox.Ok)

    #
    #####################################################
    #               audio operations                    #
    #####################################################
    
    #
    # audio set start value
    #
    def audioSetStartValue(self):

        if self.featureState <> 'Load':
            # use debug track order of calls
            if self.debug and self.debugDepth >= 1:
                QgsMessageLog.logMessage(self.myself())
            if self.spMediaStart.value() > self.spMediaEnd.value():
                self.spMediaStart.setValue(self.spMediaEnd.value())
            if self.pbSaveSection.isEnabled() == False:
                self.sectionEnableSaveCancel()

    #
    # audio set end value
    #
    def audioSetEndValue(self):

        if self.featureState <> 'Load':
            # use debug track order of calls
            if self.debug and self.debugDepth >= 1:
                QgsMessageLog.logMessage(self.myself())
            if self.spMediaEnd.value() < self.spMediaStart.value():
                self.spMediaEnd.setValue(self.spMediaStart.value())
            if self.pbSaveSection.isEnabled() == False:
                self.sectionEnableSaveCancel()

    #
    # audio set start from current slider position
    #
    def audioSetStart(self):
        
        self.spMediaStart.setValue(self.hsSectionMedia.value())
        
    #
    # audio set end from current slider position
    #
    def audioSetEnd(self):
        
        self.spMediaEnd.setValue(self.hsSectionMedia.value())
        
    #
    # load audio device list
    #
    def audioLoadDeviceList(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
            if self.reportTiming:
                QgsMessageLog.logMessage(str((datetime.datetime.now()-self.initTime).total_seconds()))
        # method body
        # create array to store info
        self.deviceList = []
        self.pyAI = None
        self.pyAI = pyaudio.PyAudio()
        # add devices with input channels
        bestChoice = 0
        # clear menu actions
        self.deviceButton.menu().clear()
        x = 0
        for i in range(self.pyAI.get_device_count()):
            devinfo = self.pyAI.get_device_info_by_index(i)
            if self.lmbMode in ('Transcribe','Import'):
                # check if we can play audio
                if devinfo['maxOutputChannels'] > 0:
                        # add to device list
                        self.deviceList.append([i,devinfo['name']])
                        # create a menu item action
                        menuItem_AudioDevice = self.deviceButton.menu().addAction(devinfo['name'])
                        # create lambda function
                        receiver = lambda deviceIndex=i: self.audioSelectDevice(deviceIndex)
                        # link lambda function to menu action
                        self.connect(menuItem_AudioDevice, QtCore.SIGNAL('triggered()'), receiver)
                        # add to menu
                        self.deviceButton.menu().addAction(menuItem_AudioDevice)
                        if devinfo['name'] == 'default':
                            bestChoice = x
                        x += 1
            else:
                # check if we can record audio
                if devinfo['maxInputChannels'] > 0:
                    try:
                        if self.pyAI.is_format_supported(44100.0,
                        input_device=devinfo['index'],
                        input_channels=devinfo['maxInputChannels'],
                        input_format=pyaudio.paInt16):
                            # add to device list
                            self.deviceList.append([i,devinfo['name']])
                            # create a menu item action
                            menuItem_AudioDevice = self.deviceButton.menu().addAction(devinfo['name'])
                            # create lambda function
                            receiver = lambda deviceIndex=i: self.audioSelectDevice(deviceIndex)
                            # link lambda function to menu action
                            self.connect(menuItem_AudioDevice, QtCore.SIGNAL('triggered()'), receiver)
                            # add to menu
                            self.deviceButton.menu().addAction(menuItem_AudioDevice)
                            if devinfo['name'] == 'default':
                                bestChoice = x
                            x += 1
                    except:
                        pass 
        self.audioDeviceIndex = self.deviceList[bestChoice][0]
        self.audioDeviceName = self.deviceList[bestChoice][1]
        if len(self.deviceList) > 0:
            self.deviceButton.setText('Audio Device: %s' % self.audioDeviceName)
        else:
            self.deviceButton.setText('Audio Device: None')

    #
    # select audio device for recording or playback
    #
    def audioSelectDevice(self,deviceIndex):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        # method body
        self.audioDeviceIndex = deviceIndex
        for x in range(len(self.deviceList)):
            if self.deviceList[x][0] == self.audioDeviceIndex:
                self.audioDeviceName = self.deviceList[x][1]
                break
        # set title
        self.deviceButton.setText('Audio Device: %s' % self.audioDeviceName)
        self.lmbAudioNotSelected()

    #
    # play audio during transcript and import mode
    #
    def audioStartPlayback(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        # method body
        # create worker
        worker = audioPlayer(self.afName,self.audioDeviceIndex,self.audioCurrentPosition,self.audioEndPosition)
        # start worker in new thread
        thread = QtCore.QThread(self)
        worker.moveToThread(thread)
        # connect thread events to functions
        worker.status.connect(self.audioUpdateStatus)
        worker.error.connect(self.audioNotifyError)
        worker.progress.connect(self.audioUpdateSliderPosition)
        thread.started.connect(worker.run)
        # run
        thread.start()
        # manage thread and worker
        self.thread = thread
        self.worker = worker

    #
    # play or pause audio playback
    #
    def audioPlayPause(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        # method body
        if self.tbMediaPlay.isEnabled():
            if self.mediaState == 'paused':
                self.audioStartPlayback()
            elif self.mediaState == 'playing':
                self.audioStopPlayback()

    #
    # stop audio playback
    #
    def audioStopPlayback(self):
        
        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        # method body
        self.worker.kill()           
        self.worker.deleteLater()
        self.thread.quit()
        self.thread.wait()
        self.thread.deleteLater()

    #
    # jump to position if slider moved
    #

    def audioSlideAndStart(self):
        
        if self.audioPreSlide == 'playing':
            self.audioCurrentPosition = self.hsSectionMedia.value()
            self.audioStartPlayback()
            
    #
    # stop playback if someone clicks the slider
    #
    
    def audioStopAndSlide(self):
        
        if self.mediaState == 'playing':
            self.audioPreSlide = 'playing'
            self.audioStopPlayback()
        else:
            self.audioPreSlide = 'paused'

    #
    # update audio current position during playback
    #
    def audioUpdateCurrentPosition(self):

        self.audioCurrentPosition = self.hsSectionMedia.value()
        if self.lmbMode in ('Import','Transcribe'):
            m, s = divmod(self.audioCurrentPosition, 60)
            h, m = divmod(m, 60)
            timerText =  "%02d:%02d:%02d" % (h, m, s)
            self.lblTimer.setText(timerText)
            self.lblTimer.setToolTip('%d seconds elapsed in interview' % self.audioCurrentPosition)

    #
    # update audio status during playback
    #
    def audioUpdateStatus(self, statusMessage):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        # method body
        if statusMessage == 'stopped':
            self.tbMediaPlay.setIcon(QtGui.QIcon(":/plugins/mapbiographer/media_play.png"))
            self.mediaState = 'paused'
            if self.hsSectionMedia.value() == self.audioEndPosition:
                self.hsSectionMedia.setValue(self.audioStartPosition)
        elif statusMessage == 'playing':
            self.tbMediaPlay.setIcon(QtGui.QIcon(":/plugins/mapbiographer/media_pause.png"))
            self.mediaState = 'playing'

    #
    # lmb audio menu test
    #
    def lmbAudioSelected(self):
        
        self.lmbAudioRecord = True
        self.audioTest()
    
    #
    # lmb audio menu to not test
    #
    def lmbAudioNotSelected(self):
        
        self.lmbAudioRecord = False
        self.audioButton.setText("Record Audio: False")
        
    #
    # test microphone
    #
    def audioTest(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        # method body
        if self.lmbAudioRecord:
            # try to enable audio recording
            # notify user
            QtGui.QMessageBox.information(self, 'Sound Test Recording',
                'Click OK to begin test recording', QtGui.QMessageBox.Ok)
            # begin recording
            # settings
            CHUNK = 1024
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 44100
            RECORD_SECONDS = 2
            # create instance
            try:
                stream = self.pyAI.open(format=FORMAT,
                                channels=CHANNELS,
                                rate=RATE,
                                input=True,
                                input_device_index=self.audioDeviceIndex,
                                frames_per_buffer=CHUNK)
                # create storage array
                frames = []
                # do recording
                for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                    data = stream.read(CHUNK)
                    frames.append(data)
                doPlayBack = True
            except:
                QtGui.QMessageBox.critical(self, 'Device Error',
                    'Try a different device', QtGui.QMessageBox.Ok)
                doPlayBack = False
            try:
                # done recording, close stream
                stream.stop_stream()
                stream.close()
            except:
                pass
            if doPlayBack:
                # notify user to listen to recording
                QtGui.QMessageBox.information(self, 'Sound Test Playback',
                    'Click OK to play back test recording', QtGui.QMessageBox.Ok)
                # play recording
                try:
                    # setup instance
                    p = pyaudio.PyAudio()
                    stream = p.open(format=FORMAT,
                            channels=CHANNELS,
                            rate=RATE,
                            output=True)
                    # play audio
                    for data in frames:
                        stream.write(data)
                except:
                    QtGui.QMessageBox.critical(self, 'Playback Error',
                        'Can not confirm success', QtGui.QMessageBox.Ok)
                    self.lmbAudioNotSelected()
                try:
                    # stop playing
                    stream.stop_stream()
                    stream.close()
                    p.terminate()
                except:
                    pass 
            ret = QtGui.QMessageBox.question(self, 'Test Results',
                'Could you hear your recording?', QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if ret == QtGui.QMessageBox.No:
                self.lmbAudioRecord = False
                self.recordAudio = False
                self.audioButton.setText("Record Audio: False")
            else:
                self.recordAudio = True
                self.audioButton.setText("Record Audio: True")
        else:
            self.recordAudio = False
            # no audio recording
            self.pbStart.setEnabled(True)

    #
    # notify of audio status during recording
    #
    def audioNotifyStatus(self, statusMessage):
    
        if lmb_audioEnabled:
            self.setWindowTitle('LMB Collector - (Audio Device: %s) - %s' % (self.audioDeviceName,statusMessage))
        else:
            self.setWindowTitle('LMB Collector - (Audio Disabled)')
        
    #
    # notify of audio error - for debugging purposes
    #
    def audioNotifyError(self, e, exception_string):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        # method body
        errorMessage = 'Audio thread raised an exception:\n' + format(exception_string)
        QtGui.QMessageBox.critical(self, 'message',
            errorMessage, QtGui.QMessageBox.Ok)
        self.audioStop()
        self.interviewFinish()

    #
    # update slider position
    #
    def audioUpdateSliderPosition(self, position):

        self.hsSectionMedia.setValue(position)

    #
    # start audio
    #
    def audioStartRecording(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        # method body
        # get path for audio file and create prefix
        s = QtCore.QSettings()
        fname = "lmb-p%d-i%d-media" % (self.projId,self.intvId)
        afPrefix = os.path.join(self.dirName,"media",fname)
        # create worker
        worker = audioRecorder(self.dirName,afPrefix,self.audioDeviceIndex,self.pyAI,fname)
        # start worker in new thread
        thread = QtCore.QThread(self)
        worker.moveToThread(thread)
        # connect thread events to methods
        worker.status.connect(self.audioNotifyStatus)
        worker.error.connect(self.audioNotifyError)
        thread.started.connect(worker.run)
        worker.setRecordingPart(self.audioSection)
        # run
        thread.start()
        # manage thread and worker
        self.thread = thread
        self.worker = worker

    #
    # stop audio 
    #
    def audioStop(self):
        
        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        # method body
        self.worker.stop()           
        self.audioSection += 1
        self.worker.deleteLater()
        self.thread.quit()
        self.thread.wait()
        self.thread.deleteLater()        

    #
    # stop audio and merge recordings
    #
    def audioStopConsolidate(self):
        
        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        # method body
        self.worker.stopNMerge()           
        self.audioSection += 1
        self.worker.deleteLater()
        self.thread.quit()
        self.thread.wait()
        self.thread.deleteLater()        

    #
    #####################################################
    #               map navigation                      #
    #####################################################
    
    #
    # zoom in
    #
    def mapZoomIn(self):

        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
        self.canvas.zoomIn()

    #
    # zoom out
    #
    def mapZoomOut(self):

        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
        self.canvas.zoomOut()

    #
    # zoom to features
    #
    def mapZoomToData(self):

        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
        extent = QgsRectangle()
        extent.setMinimal()
        zoom = False
        if self.points_layer.featureCount() > 0: 
            extent.combineExtentWith(self.points_layer.extent())
            zoom = True
        if self.lines_layer.featureCount() > 0:
            extent.combineExtentWith(self.lines_layer.extent())
            zoom = True
        if self.polygons_layer.featureCount() > 0:
            extent.combineExtentWith(self.polygons_layer.extent())
            zoom = True
        if zoom:
            extent.scale( 1.1 ) 
            crsSrc = QgsCoordinateReferenceSystem(4326)  
            crsDest = QgsCoordinateReferenceSystem(3857)  
            coordTransform = QgsCoordinateTransform(crsSrc, crsDest)
            geom = QgsGeometry.fromWkt(extent.asWktPolygon())
            geom.transform(coordTransform)
            self.canvas.setExtent( geom.boundingBox() )
            self.canvas.refresh()

    #
    # zoom to study area
    #
    def mapZoomArea(self):

        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
        self.iface.setActiveLayer(self.boundaryLayer)
        self.iface.zoomToActiveLayer()

    #
    # set sketch mode
    #
    def mapSetSketchMode(self):

        modifiers = QtGui.QApplication.keyboardModifiers()
        if self.lmbMode == 'Interview':
            if modifiers == QtCore.Qt.ControlModifier or self.rapidCapture == True:
                self.copyPrevious = True
            else:
                self.copyPrevious = False
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
            QgsMessageLog.logMessage(' - copyPrevious: %s' % str(self.copyPrevious))
            QgsMessageLog.logMessage(' - previousPrimaryCode: %s' % self.previousPrimaryCode)
            QgsMessageLog.logMessage(' - currentFeature: %s' % str(self.currentFeature))
        #if self.traceMode:
        #    self.canvas.viewport().removeEventFilter(self.hook)
        #    self.traceMode = False
        #    self.tbTraceMode.setChecked(False)
        #else:
        #    self.canvas.viewport().installEventFilter(self.hook)
        #    self.traceMode = True
        #    self.tbTraceMode.setChecked(True)
        if self.sketchMode:
            self.sketchMode = False
            self.clearButton.click()
            self.sketchButton.setVisible(False)
            self.sketchButton.setChecked(False)
            self.lineButton.setVisible(False)
            self.lineButton.setChecked(False)
            self.eraseButton.setVisible(False)
            self.eraseButton.setChecked(False)
            self.styleButton.setVisible(False)
            self.clearButton.setVisible(False)
            self.makeLineButton.setVisible(False)
            self.makePolygonButton.setVisible(False)
            self.tbPoint.setVisible(True)
            self.tbLine.setVisible(True)
            self.tbPolygon.setVisible(True)
            self.tbEdit.setVisible(True)
            self.tbMove.setVisible(True)
            self.tbNonSpatial.setVisible(True)
        else:
            self.sketchMode = True
            self.sectionDefaultCode = self.lineCode
            self.tbPoint.setVisible(False)
            self.tbLine.setVisible(False)
            self.tbPolygon.setVisible(False)
            self.tbEdit.setVisible(False)
            self.tbMove.setVisible(False)
            self.tbNonSpatial.setVisible(False)
            self.sketchButton.setVisible(True)
            self.lineButton.setVisible(True)
            self.eraseButton.setVisible(True)
            self.styleButton.setVisible(True)
            self.clearButton.setVisible(True)
            self.makeLineButton.setVisible(True)
            self.makePolygonButton.setVisible(True)
            self.sketchButton.click()
        
    #
    #####################################################
    #                   map tools                       #
    #####################################################
    
    #
    # map tools scale enable
    #
    def mapToolsScaleNotification(self):

        if self.lmbMode in 'Interview' and self.featureState == 'View' and \
        self.interviewState == 'Running':
            # use debug track order of calls
            if self.debug and self.debugDepth >= 1:
                QgsMessageLog.logMessage(self.myself())
            if self.mapToolsScaleOK():
                self.tbPoint.setBackgroundRole(QtGui.QPalette.ToolTipBase)
                self.mapToolsEnableDrawing()
                self.mapToolsEnableEditing()
                if self.showZoomNotices and self.zoomMessage <> '':
                    self.iface.messageBar().clearWidgets()
                    self.iface.messageBar().pushMessage("Proceed", self.zoomMessage, level=QgsMessageBar.INFO, duration=1)            
            else:
                self.tbPoint.setBackgroundRole(QtGui.QPalette.BrightText)
                self.mapToolsDisableDrawing()
                self.mapToolsDisableEditing()
                if self.showZoomNotices:
                    self.iface.messageBar().clearWidgets()
                    self.iface.messageBar().pushMessage("Error", self.zoomMessage, level=QgsMessageBar.CRITICAL, duration=2)            

    #
    # map tools scale OK
    #
    def mapToolsScaleOK(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 3:
            QgsMessageLog.logMessage(self.myself())
        cDenom = self.canvas.scale()
        if cDenom > self.maxDenom :
            self.zoomMessage = "Outside project map scale range. Zoom in to add features."
            self.canDigitize = False
        elif cDenom < self.minDenom:
            self.zoomMessage = "Outside project map scale range. Zoom out to add features."
            self.canDigitize = False
        else:
            if self.canDigitize == True:
                self.zoomMessage = ''
            else:
                self.zoomMessage = "Within project map scale range. You can add features."
                self.canDigitize = True
        return(self.canDigitize)

    #
    # map tools enable drawing
    #
    def mapToolsEnableDrawing(self):
        
        # use debug track order of calls
        if self.debug and self.debugDepth >= 3:
            QgsMessageLog.logMessage(self.myself())
        self.tbPoint.setEnabled(True)
        self.tbLine.setEnabled(True)
        self.tbPolygon.setEnabled(True)
        self.tbSketchMode.setEnabled(True)

    #
    # map tools disable drawing
    #
    def mapToolsDisableDrawing(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 3:
            QgsMessageLog.logMessage(self.myself())
        self.tbPoint.setDisabled(True)
        self.tbLine.setDisabled(True)
        self.tbPolygon.setDisabled(True)
        self.tbSketchMode.setDisabled(True)

    #
    # map tools enable editing
    #
    def mapToolsEnableEditing(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
        self.tbEdit.setEnabled(True)
        self.tbMove.setEnabled(True)

    #
    # map tools disable editing
    #
    def mapToolsDisableEditing(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
        self.tbEdit.setDisabled(True)
        self.tbMove.setDisabled(True)

    #
    # activate pan tool
    #
    def mapToolsActivatePanTool(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
        # method body
        self.canvas.setMapTool(self.panTool)
        self.tbPan.setChecked(True)
        # set other tools
        self.tbPoint.setChecked(False)
        self.tbLine.setChecked(False)
        self.tbPolygon.setChecked(False)
        self.tbEdit.setChecked(False)
        self.tbMove.setChecked(False)

    #
    # activate point capture tool
    #
    def mapToolsActivatePointCapture(self):

        if self.lmbMode == 'Interview':
            # check for keyboard modifier
            modifiers = QtGui.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ControlModifier or self.rapidCapture == True:
                self.copyPrevious = True
            else:
                self.copyPrevious = False
        # use debug track order of calls
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage("++++")
            QgsMessageLog.logMessage(self.myself())
            QgsMessageLog.logMessage(' - feature state: ' + self.featureState)
            QgsMessageLog.logMessage(' - feature type: ' + self.currentFeature)
            QgsMessageLog.logMessage(' - geometry state: ' + self.sectionGeometryState)
        # method body
        self.sectionEnableCancel()
        self.currentFeature = 'pt'
        # create an edit layer to hold new feature
        # first delete an existing temporary layer if it exists
        try:
            self.editLayer.commitChanges()
            QgsMapLayerRegistry.instance().removeMapLayer(self.editLayer.id())
        except:
            pass
        if self.lmbMode == 'Interview':
            if self.featureState <> 'Create':
                # create section record so that the audio index starts when tool is selected
                self.sectionCreateRecord()
                self.sectionDefaultCode = self.currentPrimaryCode
            else:
                # if not copying from previous section, use new default code because we have
                # changed tools after creating a new section
                if self.copyPrevious == False:
                    self.sectionDefaultCode = self.sectionSelectPrimaryCode(self.currentFeature)
        uri = "MultiPoint?crs=epsg:4326"
        self.editLayer = QgsVectorLayer(uri, 'New Point', 'memory')
        symbol = QgsMarkerSymbolV2.createSimple({'name':'circle','color':'#ff8000','size':'2.2'})
        symbol.setAlpha(0.5)
        self.editLayer.rendererV2().setSymbol(symbol)
        dataProvider = self.editLayer.dataProvider()
        QgsMapLayerRegistry.instance().addMapLayer(self.editLayer)
        self.iface.legendInterface().setCurrentLayer(self.editLayer)
        self.editLayer.startEditing()
        # select the layer and tool
        self.iface.legendInterface().setCurrentLayer(self.points_layer)
        self.canvas.setMapTool(self.pointTool)
        self.tbPoint.setChecked(True)
        self.mapToolsEnableDrawing()
        # disable editing
        self.mapToolsDisableEditing()
        # adjust visibility and state of other tools
        self.tbLine.setChecked(False)
        self.tbPolygon.setChecked(False)
        self.tbEdit.setChecked(False)
        self.tbMove.setChecked(False)
        self.tbPan.setChecked(False)

    #
    # activate line tool
    #
    def mapToolsActivateLineCapture(self, isSketch=False):

        if self.lmbMode == 'Interview' and isSketch == False:
            # check for keyboard modifier
            modifiers = QtGui.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ControlModifier or self.rapidCapture == True:
                self.copyPrevious = True
            else:
                self.copyPrevious = False
        # use debug track order of calls
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage("++++")
            QgsMessageLog.logMessage(self.myself())
            QgsMessageLog.logMessage(' - feature state: ' + self.featureState)
            QgsMessageLog.logMessage(' - feature type: ' + self.currentFeature)
            QgsMessageLog.logMessage(' - geometry state: ' + self.sectionGeometryState)
        # method body
        self.sectionEnableCancel()
        self.currentFeature = 'ln'
        # create an edit layer to add it to
        # first delete an existing temporary layer if it exists
        try:
            self.editLayer.commitChanges()
            QgsMapLayerRegistry.instance().removeMapLayer(self.editLayer.id())
        except:
            pass
        if not isSketch:
            if self.lmbMode == 'Interview':
                if self.featureState <> 'Create':
                    # create section record so that the audio index starts when tool is selected
                    self.sectionCreateRecord()
                    self.sectionDefaultCode = self.currentPrimaryCode
                else:
                    # if not copying from previous section, use new default code because we have
                    # changed tools after creating a new section
                    if self.copyPrevious == False:
                        self.sectionDefaultCode = self.sectionSelectPrimaryCode(self.currentFeature)
            uri = "MultiLineString?crs=epsg:4326"
            self.editLayer = QgsVectorLayer(uri, 'New Line', 'memory')
            symbol = QgsLineSymbolV2.createSimple({'color':'#ff7800','line_width':'0.6'})
            symbol.setAlpha(0.75)
            self.editLayer.rendererV2().setSymbol(symbol)
            dataProvider = self.editLayer.dataProvider()
            QgsMapLayerRegistry.instance().addMapLayer(self.editLayer)
            self.iface.legendInterface().setCurrentLayer(self.editLayer)
            self.editLayer.startEditing()
            # select the layer and tool
            self.iface.legendInterface().setCurrentLayer(self.lines_layer)
            self.canvas.setMapTool(self.lineTool)
            self.tbLine.setChecked(True)
            # adjust visibility and state of other tools
            self.tbPolygon.setChecked(False)
            self.tbPoint.setChecked(False)
            self.tbEdit.setChecked(False)
            self.tbMove.setChecked(False)
            self.tbPan.setChecked(False)
            self.mapToolsEnableDrawing()
            # disable editing
            self.mapToolsDisableEditing()
        
    #
    # activate polygon tool
    #
    def mapToolsActivatePolygonCapture(self, isSketch=False):

        if self.lmbMode == 'Interview' and isSketch == False:
            # check for keyboard modifier
            modifiers = QtGui.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ControlModifier or self.rapidCapture == True:
                self.copyPrevious = True
            else:
                self.copyPrevious = False
        # use debug track order of calls
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage("++++")
            QgsMessageLog.logMessage(self.myself())
            QgsMessageLog.logMessage(self.featureState)
        # method body
        self.sectionEnableCancel()
        self.currentFeature = 'pl'
        # create an edit layer to add it to
        # first delete an existing temporary layer if it exists
        try:
            self.editLayer.commitChanges()
            QgsMapLayerRegistry.instance().removeMapLayer(self.editLayer.id())
        except:
            pass
        if not isSketch:
            if self.lmbMode == 'Interview':
                if self.featureState <> 'Create':
                    # create section record so that the audio index starts when tool is selected
                    self.sectionCreateRecord()
                    self.sectionDefaultCode = self.currentPrimaryCode
                else:
                    # if not copying from previous section, use new default code because we have
                    # changed tools after creating a new section
                    if self.copyPrevious == False:
                        self.sectionDefaultCode = self.sectionSelectPrimaryCode(self.currentFeature)
            uri = "MultiPolygon?crs=epsg:4326"
            self.editLayer = QgsVectorLayer(uri, 'New Polygon', 'memory')
            symbol = QgsFillSymbolV2.createSimple({'color':'#ff7800','outline_color':'#717272','outline_width':'0.6'})
            symbol.setAlpha(0.5)
            self.editLayer.rendererV2().setSymbol(symbol)
            dataProvider = self.editLayer.dataProvider()
            QgsMapLayerRegistry.instance().addMapLayer(self.editLayer)
            self.iface.legendInterface().setCurrentLayer(self.editLayer)
            self.editLayer.startEditing()
            # select the layer and tool
            self.iface.legendInterface().setCurrentLayer(self.polygons_layer)
            self.canvas.setMapTool(self.polygonTool)
            self.tbPolygon.setChecked(True)
            self.mapToolsEnableDrawing()
            # disable editing
            self.mapToolsDisableEditing()
            # adjust visibility and state of other tools
            self.tbLine.setChecked(False)
            self.tbPoint.setChecked(False)
            self.tbEdit.setChecked(False)
            self.tbMove.setChecked(False)
            self.tbPan.setChecked(False)

    #
    # activate spatial edit by creating copy of feature and activating the node tool
    #
    def mapToolsActivateSpatialEdit( self ):

        isReferenced = False
        refList = ''
        for key,value in self.intvDict.iteritems():
            if value["geom_source"] == self.currentSectionCode:
                isReferenced = True
                refList += value['section_code'] + ', '
        if isReferenced:
            mText = "This section's map feature is referenced by: %s. " % refList[:-2]
            mText += "Are you sure you want to edit it?"
            response = QtGui.QMessageBox.warning(self, 'Warning',
                    mText, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if response == QtGui.QMessageBox.No:
                self.mapToolsActivatePanTool()
                return
        # use debug track order of calls
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
        # method body
        # set buttons
        self.tbEdit.setChecked(True)
        self.tbMove.setChecked(False)
        self.tbPolygon.setChecked(False)
        self.tbPoint.setChecked(False)
        self.tbLine.setChecked(False)
        self.tbPan.setChecked(False)
        # disable everything option but saving or cancelling
        self.sectionEnableCancel(True)
        # check if vector editing
        if self.featureState <> "Edit Spatial":
            # create memory layer
            if self.currentFeature == 'pt':
                uri = "MultiPoint?crs=epsg:4326"
                self.editLayer = QgsVectorLayer(uri, 'Edit Point', 'memory')
                feat = self.points_layer.selectedFeatures()[0]
                # set display parameters
                symbol = QgsMarkerSymbolV2.createSimple({'name':'circle','color':'#ff0000','size':'2.2'})
                symbol.setAlpha(0.5)
                self.editLayer.rendererV2().setSymbol(symbol)
            elif self.currentFeature == 'ln':
                uri = "MultiLineString?crs=epsg:4326"
                self.editLayer = QgsVectorLayer(uri, 'Edit Line', 'memory')
                feat = self.lines_layer.selectedFeatures()[0]
                # set display parameters
                symbol = QgsLineSymbolV2.createSimple({'color':'#ff0000','line_width':'0.6'})
                symbol.setAlpha(0.75)
                self.editLayer.rendererV2().setSymbol(symbol)
            elif self.currentFeature == 'pl':
                uri = "MultiPolygon?crs=epsg:4326"
                self.editLayer = QgsVectorLayer(uri, 'Edit Polygon', 'memory')
                feat = self.polygons_layer.selectedFeatures()[0]
                # set display parameters
                symbol = QgsFillSymbolV2.createSimple({'color':'#ff8080','outline_color':'#ff0000','outline_width':'0.6'})
                symbol.setAlpha(0.5)
                self.editLayer.rendererV2().setSymbol(symbol)
            else:
                QtGui.QMessageBox.warning(self, 'User Error',
                    'The selected section has no spatial data', QtGui.QMessageBox.Ok)
                return(-1)
            # copy feature to memory layer
            dataProvider = self.editLayer.dataProvider()
            dataProvider.addFeatures([feat])
            # register and select current layer
            # activate the points layer first as this is top layer
            # this means that the new edit layer will be added in front of this one
            self.iface.legendInterface().setCurrentLayer(self.points_layer)
            QgsMapLayerRegistry.instance().addMapLayer(self.editLayer)
            self.iface.legendInterface().setCurrentLayer(self.editLayer)
            # make memory layer editable
            self.editLayer.startEditing()
            # adjust feature state
            self.featureState = "Edit"
            self.sectionGeometryState = "Edited"
        # activate node tool
        ndta = self.iface.actionNodeTool()
        if ndta.isChecked() == False:
            ndta.trigger()
            
        return(0)
        
    #
    # activate spatial move by creating copy of feature and activating the move tool
    #
    def mapToolsActivateSpatialMove( self ):

        isReferenced = False
        refList = ''
        for key,value in self.intvDict.iteritems():
            if value["geom_source"] == self.currentSectionCode:
                isReferenced = True
                refList += value['section_code'] + ', '
        if isReferenced:
            mText = "This section's map feature is referenced by: %s. " % refList[:-2]
            mText += "Are you sure you want to move it?"
            response = QtGui.QMessageBox.warning(self, 'Warning',
                    mText, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if response == QtGui.QMessageBox.No:
                self.mapToolsActivatePanTool()
                return
        # set buttons
        self.tbEdit.setChecked(False)
        self.tbMove.setChecked(True)
        self.tbPolygon.setChecked(False)
        self.tbPoint.setChecked(False)
        self.tbLine.setChecked(False)
        self.tbPan.setChecked(False)
        # disable everything option but saving or cancelling
        self.sectionEnableCancel(True)
        # check if vector editing
        # use debug track order of calls
        if self.debug:
            if self.debugDepth == 2:
                QgsMessageLog.logMessage(self.myself())
            elif self.debugDepth >= 3:
                QgsMessageLog.logMessage('%s (%s)' % (self.myself(), self.featureState))
        if self.featureState <> "Edit Spatial":
            # create memory layer
            if self.currentFeature == 'pt':
                uri = "MultiPoint?crs=epsg:4326"
                self.editLayer = QgsVectorLayer(uri, 'Edit Point', 'memory')
                feat = self.points_layer.selectedFeatures()[0]
                # set display parameters
                symbol = QgsMarkerSymbolV2.createSimple({'name':'circle','color':'#ff0000','size':'2.2'})
                symbol.setAlpha(0.5)
                self.editLayer.rendererV2().setSymbol(symbol)
            elif self.currentFeature == 'ln':
                uri = "MultiLineString?crs=epsg:4326"
                self.editLayer = QgsVectorLayer(uri, 'Edit Line', 'memory')
                feat = self.lines_layer.selectedFeatures()[0]
                # set display parameters
                symbol = QgsLineSymbolV2.createSimple({'color':'#ff0000','line_width':'0.6'})
                symbol.setAlpha(0.75)
                self.editLayer.rendererV2().setSymbol(symbol)
            elif self.currentFeature == 'pl':
                uri = "MultiPolygon?crs=epsg:4326"
                self.editLayer = QgsVectorLayer(uri, 'Edit Polygon', 'memory')
                feat = self.polygons_layer.selectedFeatures()[0]
                # set display parameters
                symbol = QgsFillSymbolV2.createSimple({'color':'#ff8080','outline_color':'#ff0000','outline_width':'0.6'})
                symbol.setAlpha(0.5)
                self.editLayer.rendererV2().setSymbol(symbol)
            else:
                QtGui.QMessageBox.warning(self, 'User Error',
                    'The selected section has no spatial data', QtGui.QMessageBox.Ok)
                return(-1)
            # copy feature to memory layer
            dataProvider = self.editLayer.dataProvider()
            dataProvider.addFeatures([feat])
            # register and select current layer
            # activate the points layer first as this is top layer
            # this means that the new edit layer will be added in front of this one
            self.iface.legendInterface().setCurrentLayer(self.points_layer)            
            QgsMapLayerRegistry.instance().addMapLayer(self.editLayer)
            self.iface.legendInterface().setCurrentLayer(self.editLayer)
            # make memory layer editable
            self.editLayer.startEditing()
            # disable other tools and buttons
            self.sectionEnableSaveCancel()
            # adjust feature state
            self.featureState = "Edit"
            self.sectionGeometryState = "Edited"
        # activate move tool
        mvta = self.iface.actionMoveFeature()
        if mvta.isChecked() == False:
            mvta.trigger()

        return(0)

    # 
    # place point using custom point tool
    #
    def mapToolsPlacePoint(self, point):

        if self.lmbMode == 'Interview':
            modifiers = QtGui.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ControlModifier:
                self.rapidCapture = True
            else:
                self.rapidCapture = False
        # use debug track order of calls
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage("++")
            QgsMessageLog.logMessage(self.myself())
            QgsMessageLog.logMessage(self.currentSectionCode)
        #
        # 2016-02-20 - for reasons that are not understood, if the memory layer selections
        # are cleared bfore adding the new feature the past geometries get cleared.
        #
        # update spatial layer
        point.convertToMultiType()
        if self.sectionData["geom_source"] == "pt":
            self.sectionMapFeatureUpdateGeometry(point, "pt", self.currentSectionCode)
        else:
            self.sectionMapFeatureAdd(point, "pt", self.currentSectionCode)
        # adjust interface
        if self.lmbMode == 'Interview':
            # reset state
            if self.featureState == 'Create':
                newSectionCode = self.sectionCalculateSectionCode(self.sectionDefaultCode,self.currentCodeNumber)
                if newSectionCode <> self.currentSectionCode:
                    self.currentPrimaryCode = self.sectionDefaultCode
                    self.sectionData["code_type"] = self.currentPrimaryCode
                    self.sectionData['content_codes'] = [self.currentPrimaryCode]
                    del self.intvDict[self.currentSectionCode]
                    self.intvDict[newSectionCode] = self.sectionData
                    self.sectionMapFeatureUpdateLabel('pt',self.currentSectionCode,newSectionCode)
                    self.currentSectionCode = newSectionCode
                    self.interviewFileSave()
                self.featureState = 'View'
                self.sectionAddEntry()
            else:
                self.featureState = 'View'
            # keep point tool active
            if self.rapidCapture == True:
                self.mapToolsActivatePointCapture()
            else:
                self.mapToolsActivatePanTool()
                self.sectionDisableSaveCancel()
        else:
            # reset state
            self.featureState = 'View'
            self.mapToolsActivatePanTool()
            self.sectionDisableSaveCancel()
        # add to feature status list if needed
        idx = self.cbFeatureSource.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
        if idx == -1:
            self.cbFeatureSource.addItem('Same as %s' % self.currentSectionCode)
        # highlight feature
        featId = self.sectionGetFeatureId(self.points_layer, self.currentSectionCode) 
        self.points_layer.select(featId)        

    #
    # place line using custom line tool
    #
    def mapToolsPlaceLine(self, line):

        if self.lmbMode == 'Interview':
            modifiers = QtGui.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ControlModifier:
                self.rapidCapture = True
            else:
                self.rapidCapture = False
        # use debug track order of calls
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage("++")
            QgsMessageLog.logMessage(self.myself())
        # update spatial layer
        line.convertToMultiType()
        if self.sectionData["geom_source"] == "ln":
            self.sectionMapFeatureUpdateGeometry(line, "ln", self.currentSectionCode)
        else:
            self.sectionMapFeatureAdd(line, "ln", self.currentSectionCode)
        # adjust interface
        if self.lmbMode == 'Interview':
            # reset state
            if self.featureState == 'Create':
                newSectionCode = self.sectionCalculateSectionCode(self.sectionDefaultCode,self.currentCodeNumber)
                if newSectionCode <> self.currentSectionCode:
                    self.sectionData["section_code"] = newSectionCode
                    self.currentPrimaryCode = self.sectionDefaultCode
                    self.sectionData["code_type"] = self.currentPrimaryCode
                    self.sectionData['content_codes'] = [self.currentPrimaryCode]
                    del self.intvDict[self.currentSectionCode]
                    self.intvDict[newSectionCode] = self.sectionData
                    self.sectionMapFeatureUpdateLabel('ln',self.currentSectionCode,newSectionCode)
                    self.currentSectionCode = newSectionCode
                    self.interviewFileSave()
                self.featureState = 'View'
                self.sectionAddEntry()
            else:
                self.featureState = 'View'
            # keep line tool active
            if self.rapidCapture == True:
                self.mapToolsActivateLineCapture()
            else:
                self.mapToolsActivatePanTool()
                self.sectionDisableSaveCancel()
        else:
            # reset state
            self.featureState = 'View'
            self.mapToolsActivatePanTool()
            self.sectionDisableSaveCancel()
        # add to feature status list if needed
        idx = self.cbFeatureSource.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
        if idx == -1:
            self.cbFeatureSource.addItem('Same as %s' % self.currentSectionCode)
        featId = self.sectionGetFeatureId(self.lines_layer, self.currentSectionCode) 
        self.lines_layer.select(featId)        

    #
    # place polygon using custom polygon tool
    #
    def mapToolsPlacePolygon(self, polygon):

        if self.lmbMode == 'Interview':
            modifiers = QtGui.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ControlModifier:
                self.rapidCapture = True
            else:
                self.rapidCapture = False
        # use debug track order of calls
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage("++")
            QgsMessageLog.logMessage(self.myself())
        # update spatial layer
        polygon.convertToMultiType()
        if self.sectionData["geom_source"] == "pl":
            self.sectionMapFeatureUpdateGeometry(polygon, "pl", self.currentSectionCode)
        else:
            self.sectionMapFeatureAdd(polygon, "pl", self.currentSectionCode)
        # adjust interface
        if self.lmbMode == 'Interview':
            # reset state
            if self.featureState == 'Create':
                newSectionCode = self.sectionCalculateSectionCode(self.sectionDefaultCode,self.currentCodeNumber)
                if newSectionCode <> self.currentSectionCode:
                    self.sectionData["section_code"] = newSectionCode
                    self.currentPrimaryCode = self.sectionDefaultCode
                    self.sectionData["code_type"] = self.currentPrimaryCode
                    self.sectionData['content_codes'] = [self.currentPrimaryCode]
                    del self.intvDict[self.currentSectionCode]
                    self.intvDict[newSectionCode] = self.sectionData
                    self.sectionMapFeatureUpdateLabel('pl',self.currentSectionCode,newSectionCode)
                    self.currentSectionCode = newSectionCode
                    self.interviewFileSave()
                self.featureState = 'View'
                self.sectionAddEntry()
            else:
                self.featureState = 'View'
            # keep polygonTool active
            if self.rapidCapture == True:
                self.mapToolsActivatePolygonCapture()
            else:
                self.mapToolsActivatePanTool()
                self.sectionDisableSaveCancel()
        else:
            # reset state
            self.featureState = 'View'
            self.mapToolsActivatePanTool()
            self.sectionDisableSaveCancel()
        # add to feature status list if needed
        idx = self.cbFeatureSource.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
        if idx == -1:
            self.cbFeatureSource.addItem('Same as %s' % self.currentSectionCode)
        featId = self.sectionGetFeatureId(self.polygons_layer, self.currentSectionCode) 
        self.polygons_layer.select(featId)        

    #
    #####################################################
    #              sketch functions                     #
    #####################################################
    
    #
    # action on clicking sketch draw button
    #
    def sketchDrawButton(self):
        
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
            QgsMessageLog.logMessage(' - copyPrevious: %s' % str(self.copyPrevious))
            QgsMessageLog.logMessage(' - currentFeature: %s' % str(self.currentFeature))
        rl = plugins['redLayer']
        if not self.sketchButton.isChecked():
            self.mapToolsActivatePanTool()
        else:
            self.sectionEnableCancel()
            self.mapToolsEnableDrawing()
            # disable editing
            self.mapToolsDisableEditing()
            if self.lmbMode == 'Interview' and self.featureState <> 'Create':
                # create section record so that the audio index starts here
                self.currentFeature = 'ln'
                self.sectionCreateRecord()
            rl.sketchAction.__call__()
            self.lineButton.setChecked(False)
            self.eraseButton.setChecked(False)

    #
    # action on clicking sketch line button
    #
    def sketchLineButton(self):

        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
            QgsMessageLog.logMessage(' - copyPrevious: %s' % str(self.copyPrevious))
            QgsMessageLog.logMessage(' - currentFeature: %s' % str(self.currentFeature))
        rl = plugins['redLayer']
        if not self.lineButton.isChecked():
            self.mapToolsActivatePanTool()
        else:
            self.sectionEnableCancel()
            self.mapToolsEnableDrawing()
            # disable editing
            self.mapToolsDisableEditing()
            if self.lmbMode == 'Interview' and self.featureState <> 'Create':
                # create section record so that the audio index starts here
                self.currentFeature = 'ln'
                self.sectionCreateRecord()
            rl.penAction.__call__()
            self.sketchButton.setChecked(False)
            self.eraseButton.setChecked(False)

    #
    # action on clicking sketch erase button
    #
    def sketchEraseButton(self):

        rl = plugins['redLayer']
        rl.eraseAction.__call__()
        self.lineButton.setChecked(False)
        self.sketchButton.setChecked(False)

    #
    # convert sketch to line
    #
    def sketchToLine(self):
        
        # use debug track order of calls
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
            QgsMessageLog.logMessage(' - copyPrevious: %s' % str(self.copyPrevious))
            QgsMessageLog.logMessage(' - previousPrimaryCode: %s' % self.previousPrimaryCode)
            QgsMessageLog.logMessage(' - currentFeature: %s' % str(self.currentFeature))
        # confirm we have something to work with
        rl = plugins['redLayer']
        if len(rl.geoSketches) == 0:
            messageText = 'There are no sketches to convert to a line.'
            response = QtGui.QMessageBox.warning(self, 'Warning',
               messageText, QtGui.QMessageBox.Ok)
            return
        # set system to capture feature
        self.mapToolsActivateLineCapture(True)
        # copy to layer
        sketchLayer = self.sketchToLayer()
        # merge to a single line
        self.sketchMerge(sketchLayer)
        # copy feature
        featIter = sketchLayer.getFeatures()
        sFeat = featIter.next()
        newGeom = sFeat.geometry()
        # remove layer
        QgsMapLayerRegistry.instance().removeMapLayer( sketchLayer.id() )
        # clear interface
        self.clearButton.click()
        # set to default line code
        if self.copyPrevious == False:
            self.sectionDefaultCode = self.lineCode
        # insert into section
        self.mapToolsPlaceLine(newGeom)
        # change out of sketchMode
        self.tbSketchMode.click()
        
    #
    # convert sketch to area
    #
    def sketchToPolygon(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 2:
            QgsMessageLog.logMessage(self.myself())
            QgsMessageLog.logMessage(' - copyPrevious: %s' % str(self.copyPrevious))
            QgsMessageLog.logMessage(' - previousPrimaryCode: %s' % self.previousPrimaryCode)
            QgsMessageLog.logMessage(' - currentFeature: %s' % str(self.currentFeature))
        # confirm we have something to work with
        rl = plugins['redLayer']
        if len(rl.geoSketches) == 0:
            messageText = 'There are no sketches to convert to a polygon.'
            response = QtGui.QMessageBox.warning(self, 'Warning',
               messageText, QtGui.QMessageBox.Ok)
            return
        # set system to capture feature
        self.mapToolsActivatePolygonCapture(True)
        # copy to layer
        sketchLayer = self.sketchToLayer()
        # merge to a single line
        self.sketchMerge(sketchLayer)
        # convert to polygon
        fNameBase = './' + datetime.datetime.now().isoformat()[:10] + '_sketchPoly'
        processing.runalg('qgis:linestopolygons', sketchLayer, fNameBase)
        # open polygon layer
        fName = fNameBase + '.shp'
        polyLayer = self.iface.addVectorLayer(fName, "Polygon Layer", "ogr")
        # copy feature
        featIter = polyLayer.getFeatures()
        sFeat = featIter.next()
        newGeom = sFeat.geometry()
        # remove layers
        QgsMapLayerRegistry.instance().removeMapLayer( polyLayer.id() )
        QgsMapLayerRegistry.instance().removeMapLayer( sketchLayer.id() )
        # remove shapefile
        fList = glob.glob(fNameBase+'.*')
        for f in fList:
            os.remove(f)
        # clear interface
        self.clearButton.click()
        # set to default line code
        if self.copyPrevious == False:
            self.sectionDefaultCode = self.polygonCode
        # insert into section
        self.mapToolsPlacePolygon(newGeom)
        # change out of sketchMode
        self.tbSketchMode.click()

    #
    # convert sketch to layer
    #
    def sketchToLayer(self):
        
        # use debug track order of calls
        if self.debug and self.debugDepth >= 3:
            QgsMessageLog.logMessage(self.myself())
        rl = plugins['redLayer']
        segments = {}
        lastPoint = None
        segmentId = 0
        #cycle to classify elementary sketches in gestures
        for sketch in rl.geoSketches:
            if sketch[2].asGeometry():
                if not lastPoint or sketch[2].asGeometry().vertexAt(0) == lastPoint:
                    try:
                        segments[segmentId].append(sketch[:-1])
                    except:
                        segments[segmentId] =[sketch[:-1]]
                    lastPoint = sketch[2].asGeometry().vertexAt(1)
                else:
                    lastPoint = None
                    segmentId +=1
        sketchLayer = QgsVectorLayer("MultiLineString?crs=epsg:4326&field=id:integer&index=yes", "Sketch Layer", "memory")
        sketchLayer.startEditing()
        for segmentId,redLines in segments.iteritems():
            geometryList = []
            note = ""
            secLines = []
            for segment in redLines:
                vertex = segment[2].asGeometry().vertexAt(0)
                secLines.append(QgsPoint(vertex.x(),vertex.y()))
                if segment[4] != "":
                    note = segment[4]
            secLines.append(segment[2].asGeometry().vertexAt(1))
            polyline = QgsGeometry.fromPolyline(secLines)
            crsSrc = QgsCoordinateReferenceSystem(3857)  
            crsDest = QgsCoordinateReferenceSystem(4326)  
            coordTransform = QgsCoordinateTransform(crsSrc, crsDest)
            polyline.transform(coordTransform)
            newFeat = QgsFeature()
            newFeat.setGeometry(polyline)
            newFeat.setAttributes([segmentId])
            sketchLayer.addFeatures([newFeat])
        sketchLayer.commitChanges()
        # add to layer list
        QgsMapLayerRegistry.instance().addMapLayer(sketchLayer)
        
        return(sketchLayer)

    #
    # merge sketch layer to line
    #
    def sketchMerge(self, sketchLayer):
                
        # use debug track order of calls
        if self.debug and self.debugDepth >= 3:
            QgsMessageLog.logMessage(self.myself())
        self.iface.setActiveLayer(sketchLayer)
        sketchLayer.setSelectedFeatures([feat.id() for feat in sketchLayer.getFeatures()])
        selection = sketchLayer.selectedFeatures()
        if len(selection) > 1:
            jml = plugins['joinmultiplelines']
            jml.run()
            sketchLayer.commitChanges()

    #
    #####################################################
    #                   photos                          #
    #####################################################
    
    #
    # load photo to list
    #
    def photoLoad(self, fName, caption):
        
        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        p=QtGui.QPixmap(fName)
        #if p.height()>p.width():
        #    p=p.scaledToWidth(self.thumbnailSize)
        #else:
        #    p=p.scaledToHeight(self.thumbnailSize)
        #p2=p.scaledToWidth(self.thumbnailSize)
        #p=p.copy(0,0,self.thumbnailSize,self.thumbnailSize)
        item = QtGui.QTableWidgetItem()
        item.setStatusTip(caption)
        item.setIcon(QtGui.QIcon(p.scaledToWidth(self.thumbnailSize)))
        rCnt = self.twPhotos.rowCount()+1
        self.twPhotos.setRowCount(rCnt)
        self.twPhotos.setItem(rCnt-1,0,item)
        item = QtGui.QTableWidgetItem(caption)
        self.twPhotos.setItem(rCnt-1,1,item)

    #
    # add photo
    #
    def photoAdd(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        fName = QtGui.QFileDialog.getOpenFileName(self, 'Select Image',self.lastDir,"Image Files (*.png *.PNG *.jpg *.JPG *.bmp *.BMP *.tif *.tiff *.TIF *.TIFF *.gif *.GIF)")
        self.lastDir, temp = os.path.split(fName)
        if os.path.exists(fName):
            caption, ok = QtGui.QInputDialog.getText(self, 'Caption', 
                'Enter the caption for this image')
            if ok:
                localFile, fileName = self.photoCopy(fName)
                self.photoLoad(localFile,caption)
                self.twPhotos.clearSelection()
                self.currentMediaFiles.append([fileName,caption])
                self.sectionEnableSaveCancel()
    #
    # copy photo
    #
    def photoCopy(self, sourceFile):
        
        filePath, fileName = os.path.split(sourceFile)
        destFile = os.path.join(self.dirName,'images',fileName)
        if sourceFile <> destFile:
            shutil.copy(sourceFile,destFile)
        return(destFile,fileName)
        
    #
    # edit photo
    #
    def photoEdit(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        cRow = self.twPhotos.currentRow()
        oldCaption = self.twPhotos.item(cRow,1).text()
        caption, ok = QtGui.QInputDialog.getText(self, 'Caption', 
            'Edit the caption for this image', text = oldCaption)
        if ok:
            if self.debug and self.debugDepth >= 1:
                QgsMessageLog.logMessage(self.myself() + ' (%s)' % str(self.currentMediaFiles))
            self.twPhotos.item(cRow,1).setText(caption)
            self.currentMediaFiles[cRow][1] = caption
            self.sectionEnableSaveCancel()
        self.twPhotos.clearSelection()
        
    #
    # remove photo
    #
    def photoRemove(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        cRow = self.twPhotos.currentRow()
        self.twPhotos.removeRow(cRow)
        self.twPhotos.clearSelection()
        # do not delete the file
        # force manual removal of files
        # update the media list
        if cRow == len(self.currentMediaFiles)-1:
            # remove last item from list
            self.currentMediaFiles = self.currentMediaFiles[:cRow]
        elif cRow == 0:
            # remove first item from list
            self.currentMediaFiles = self.currentMediaFiles[1:]
        else:
            # keep items before and items after
            self.currentMediaFiles = self.currentMediaFiles[:cRow] + self.currentMediaFiles[cRow+1:]
        self.sectionEnableSaveCancel()

    #
    # select or deselect a photo
    #
    def photoSelect(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself() + ' (%s)' % self.featureState)
        if self.featureState <> 'Load':
            if len(self.twPhotos.selectedItems()) > 0:
                self.pbRemovePhoto.setEnabled(True)
                self.pbEditPhoto.setEnabled(True)
            else:
                self.pbRemovePhoto.setDisabled(True)
                self.pbEditPhoto.setDisabled(True)

    #
    #####################################################
    #                     data import                   #
    #####################################################
    
    #
    # import features
    #
    def importFeatures(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        # disable interface
        self.modeButton.setDisabled(True)
        self.interviewButton.setDisabled(True)
        self.closeButton.setDisabled(True)
        self.frInterviewActions.setDisabled(True)
        self.frSectionControls.setDisabled(True)
        # Create the dialog (after translation) and keep reference
        s = QtCore.QSettings()
        dirName = s.value('mapBiographer/projectDir')
        self.importDialog = mapBiographerImporter(self.iface, self.projDict["projects"][str(self.projId)], self.intvDict, self.dirName)
        # show the dialog
        self.importDialog.show()
        # Run the dialog event loop
        result = self.importDialog.exec_()
        dataDict = self.importDialog.returnData()
        # use debug track order of calls
        if self.debug and self.debugDepth >= 4:
            QgsMessageLog.logMessage(str(dataDict))
        # check if dictionary was created to guide import
        if dataDict <> {}:
            # check if interview file exists and if not create it
            fname = "lmb-p%d-i%d-data.json" % (self.projId,self.intvId)
            nf = os.path.join(self.dirName,"interviews",fname)
            if not os.path.exists(nf):
                self.interviewFileCreate()
                self.intvDict = {}
            # open source layer if it exists
            if os.path.exists(dataDict['source']):
                self.interviewState = 'Import'
                # open layer
                inputLayer = QgsVectorLayer(dataDict['source'], 'input', 'ogr')
                # get field names
                fields = inputLayer.dataProvider().fields().toList()
                x = 0
                fieldDict = {}
                for field in fields:
                    fieldDict[field.name()] = [x,field.typeName()]
                    x += 1
                if self.debug and self.debugDepth >= 2:
                    QgsMessageLog.logMessage(str(dataDict))
                    QgsMessageLog.logMessage(str(fieldDict))
                # setup projection transformation
                crsSrc = inputLayer.crs()    
                crsDest = QgsCoordinateReferenceSystem(4326)  
                coordTransform = QgsCoordinateTransform(crsSrc, crsDest)
                # begin importing
                if inputLayer.geometryType() == QGis.Point:
                    self.currentFeature = 'pt'
                elif inputLayer.geometryType() == QGis.Line:
                    self.currentFeature = 'ln'
                elif inputLayer.geometryType() == QGis.Polygon:
                    self.currentFeature = 'pl'
                # get features
                features = inputLayer.getFeatures()
                cnt = inputLayer.featureCount()
                # provide user with progress dialog
                x = 0
                lastPercent = 0.0
                progress = QtGui.QProgressDialog('Importing Features','Cancel',0,100,self)
                progress.setWindowTitle('Import progress')
                progress.setWindowModality(QtCore.Qt.WindowModal)
                # add features one by one to dictionary
                sequenceList = []
                for feature in features:
                    # increment and notify
                    x += 1
                    attrs = feature.attributes()
                    # set current sequence to x + the maxCodeNumber in case
                    # more than one import into an interview
                    if dataDict['sequence'] <> '--None--':
                        idx = fieldDict[dataDict['sequence']][0]
                        docSeq = str(attrs[idx])
                        if docSeq not in sequenceList:
                            self.currentSequence = int(docSeq)
                            sequenceList.append(int(docSeq))
                        else:
                            self.currentSequence = int(docSeq) + 5000
                            sequenceList.append(int(docSeq) + 5000)
                    else:
                        self.currentSequence = x + self.maxCodeNumber
                        sequenceList.append(self.currentSequence)
                    if (float(x)/cnt*100)+5 > lastPercent:
                        lastPercent = float(x)/cnt*100
                        progress.setValue(lastPercent)
                        if progress.wasCanceled():
                            break
                    # get geometry and attributes
                    geom = feature.geometry()
                    geom.transform(coordTransform)
                    # process attributes
                    if dataDict['sectionCode'] <> '--Create On Import--':
                        idx = fieldDict[dataDict['sectionCode']][0]
                        self.currentSectionCode = str(attrs[idx])
                        if dataDict['primaryCode'] <> '--None--':
                            # get primary code from field
                            idx = fieldDict[dataDict['primaryCode']][0]
                            self.currentPrimaryCode = str(attrs[idx])
                        else:
                            # extract primary code from section code
                            pc = re.findall(r'\D+', str(attrs[idx]))
                            if len(pc) > 0:
                                pc = pc[0]
                            else:
                                pc = self.defaultCode
                            self.currentPrimaryCode = pc
                    else:
                        # creating section code  on import
                        if dataDict['primaryCode'] <> '--None--':
                            idx = fieldDict[dataDict['primaryCode']][0]
                            self.currentPrimaryCode = str(attrs[idx])
                            self.currentSectionCode = self.sectionCalculateSectionCode(self.currentPrimaryCode,self.currentSequence)
                        else:
                            self.currentPrimaryCode = self.defaultCode
                            self.currentSectionCode = self.sectionCalculateSectionCode(self.currentPrimaryCode,self.currentSequence)
                    if dataDict['legacyCode'] <> '--None--':
                        idx = fieldDict[dataDict['legacyCode']][0]
                        legacyCode = str(attrs[idx])
                    else:
                        legacyCode = ""
                    if dataDict['security'] <> '--None--':
                        idx = fieldDict[dataDict['security']][0]
                        dataSecurity = str(attrs[idx])
                    else:
                        dataSecurity = "PR"
                    if dataDict['contentCodes'] <> '--None--':
                        idx = fieldDict[dataDict['contentCodes']][0]
                        contentCodes = str(attrs[idx]).split(',')
                    else:
                        contentCodes = [self.currentPrimaryCode]
                    if dataDict['tags'] <> '--None--':
                        idx = fieldDict[dataDict['tags']][0]
                        tags = str(attrs[idx]).split(',')
                    else:
                        tags = []
                    if dataDict['usePeriod'] <> '--None--':
                        idx = fieldDict[dataDict['usePeriod']][0]
                        usePeriod = str(attrs[idx])
                    else:
                        usePeriod = "N"
                    if dataDict['timeOfYear'] <> '--None--':
                        idx = fieldDict[dataDict['timeOfYear']][0]
                        timeOfYear = str(attrs[idx])
                    else:
                        timeOfYear = "N"
                    if dataDict['recordingDate'] <> '--None--':
                        try:
                            idx = fieldDict[dataDict['recordingDate']][0]
                            temp = str(attrs[idx])
                            tDate = datetime.datetime.strptime(temp, "%Y-%m-%d %H:%M")
                            recording_datetime = tDate.isoformat()[:16].replace('T',' ')
                        except:
                            try:
                                tDate = datetime.datetime.strptime(temp, "%Y-%m-%d")
                                recording_datetime = tDate.isoformat()[:16].replace('T',' ')
                            except:
                                try:
                                    tDate = datetime.datetime.strptime(temp, "%Y%m%d")
                                    recording_datetime = tDate.isoformat()[:16].replace('T',' ')
                                except:
                                    try:
                                        temp = attrs[idx]
                                        if isinstance(temp, QtCore.QDate):
                                            temp2 = temp.toPyDate()
                                            recording_datetime = temp2.isoformat() + " 12:00"
                                        elif isinstance(temp, QtCore.QDateTime):
                                            temp2 = temp.toPyDateTime()
                                            recording_datetime = temp2.isoformat()[:16].replace('T',' ')
                                        else:
                                            recording_datetime = self.interviewStart
                                    except:
                                        recording_datetime = self.interviewStart
                    else:
                        recording_datetime = self.interviewStart
                    if dataDict['notes'] <> '':
                        lst = dataDict['notes'].split(',')
                        outText = ''
                        for fld in lst:
                            idx = fieldDict[fld.strip()][0]
                            outText = outText + str(attrs[idx]) + '\n'
                        notes = outText
                    else:
                        notes = ""
                    if dataDict['sections'] <> '':
                        lst = dataDict['sections'].split(',')
                        outText = ''
                        for fld in lst:
                            idx = fieldDict[fld.strip()][0]
                            outText = outText + str(attrs[idx]) + '\n'
                        sectionText = outText
                    else:
                        sectionText = ""
                    # create temporary entry
                    temp = {
                        "code_type": self.currentPrimaryCode,
                        "code_integer": self.currentSequence,
                        "sequence": self.currentSequence,
                        "section_code": self.currentSectionCode,
                        "legacy_code": legacyCode,
                        "data_security": dataSecurity,
                        "section_text": sectionText,
                        "note": notes,
                        "use_period": usePeriod,
                        "time_of_year": timeOfYear,
                        "spatial_data_source": dataDict['spatialDataSource'],
                        "spatial_data_scale": dataDict["spatialDataScale"],
                        "tags": tags,
                        "content_codes": contentCodes,
                        "media_files": [],
                        "media_start_time": 0,
                        "media_end_time": 0,
                        "the_geom": "",
                        "geom_source": "ns",
                        "date_created": datetime.datetime.now().isoformat()[:16].replace('T',' '),
                        "date_modified": datetime.datetime.now().isoformat()[:16].replace('T',' '),
                        "recording_datetime": recording_datetime
                    }
                    # process and add geometry
                    if self.currentFeature == "pt":
                        temp["the_geom"] = geom.exportToWkt()
                        temp["geom_source"] = "pt"
                    elif self.currentFeature == "ln":
                        temp["the_geom"] = geom.exportToWkt()
                        temp["geom_source"] = "ln"
                    elif self.currentFeature == "pl":
                        temp["the_geom"] = geom.exportToWkt()
                        temp["geom_source"] = "pl"
                    # add section to dictionary
                    self.intvDict[self.currentSectionCode] = temp
                # write entire interview to file
                self.interviewFileSave()
                self.iface.messageBar().clearWidgets()
                # update maxCodeNumber
                self.maxCodeNumber = self.currentSequence
                # reset to view state and reload
                self.disconnectSectionControls()
                self.interviewUnload()
                self.interviewLoad()
                self.connectSectionControls()
                self.interviewState = 'View'
        # enable interface
        self.modeButton.setEnabled(True)
        self.interviewButton.setEnabled(True)
        self.closeButton.setEnabled(True)
        self.frInterviewActions.setEnabled(True)
        self.frSectionControls.setEnabled(True)
                
    #
    # import transcript
    #
    def importTranscript(self):
        
        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        # disable interface
        self.modeButton.setDisabled(True)
        self.interviewButton.setDisabled(True)
        self.closeButton.setDisabled(True)
        self.frInterviewActions.setDisabled(True)
        self.frSectionControls.setDisabled(True)
        # Create the dialog (after translation) and keep reference
        s = QtCore.QSettings()
        dirName = s.value('mapBiographer/projectDir')
        self.importTranscriptDialog = mapBiographerTranscriptImporter(self.iface, self.projDict["projects"][str(self.projId)], self.intvDict, self.dirName)
        # show the dialog
        self.importTranscriptDialog.show()
        # Run the dialog event loop
        result = self.importTranscriptDialog.exec_()
        sectionList,updateSections = self.importTranscriptDialog.returnData()
        # update or append
        recording_datetime = self.interviewStart
        if len(sectionList) > 0:
            self.interviewState = 'Import'
            # update sections
            if updateSections == True:
                for key, value in self.intvDict.iteritems():
                    for section in sectionList:
                        if key == section[1]:
                            self.intvDict[key]['section_text'] = section[2].encode('utf-8')
            else:
                # check if interview file exists and if not create it
                fname = "lmb-p%d-i%d-data.json" % (self.projId,self.intvId)
                nf = os.path.join(self.dirName,"interviews",fname)
                if not os.path.exists(nf):
                    self.interviewFileCreate()
                    self.intvDict = {}
                # now begin adding sections
                for section in sectionList:
                    self.currentPrimaryCode = self.defaultCode
                    self.currentSequence += 1
                    self.currentSectionCode = self.sectionCalculateSectionCode(self.currentPrimaryCode,self.currentSequence)
                    temp = {
                        "code_type": self.currentPrimaryCode,
                        "code_integer": self.currentSequence,
                        "sequence": self.currentSequence,
                        "section_code": self.currentSectionCode,
                        "legacy_code": section[1].encode('utf-8'),
                        "data_security": "PR",
                        "section_text": section[2].encode('utf-8'),
                        "note": "",
                        "use_period": "N",
                        "time_of_year": "N",
                        "spatial_data_source": "OS",
                        "spatial_data_scale": "",
                        "tags": "",
                        "content_codes": [self.currentPrimaryCode],
                        "media_files": [],
                        "media_start_time": 0,
                        "media_end_time": 0,
                        "the_geom": "",
                        "geom_source": "ns",
                        "date_created": datetime.datetime.now().isoformat()[:16].replace('T',' '),
                        "date_modified": datetime.datetime.now().isoformat()[:16].replace('T',' '),
                        "recording_datetime": recording_datetime
                    }
                    # add section to dictionary
                    self.intvDict[self.currentSectionCode] = temp
            # write entire interview to file
            self.interviewFileSave()
            self.iface.messageBar().clearWidgets()
            # update maxCodeNumber
            self.maxCodeNumber = self.currentSequence
            # reset to view state and reload
            self.disconnectSectionControls()
            self.interviewUnload()
            self.interviewLoad()
            self.connectSectionControls()
            self.interviewState = 'View'
        # enable interface
        self.modeButton.setEnabled(True)
        self.interviewButton.setEnabled(True)
        self.closeButton.setEnabled(True)
        self.frInterviewActions.setEnabled(True)
        self.frSectionControls.setEnabled(True)

    #
    # import audio
    #
    def importAudio(self):

        # use debug track order of calls
        if self.debug and self.debugDepth >= 1:
            QgsMessageLog.logMessage(self.myself())
        s = QtCore.QSettings()
        fname = QtGui.QFileDialog.getOpenFileName(self, 'Select Audio File', '.', '*.wav')
        if os.path.exists(fname):
            destFile = "lmb-p%d-i%d-media.wav" % (self.projId,self.intvId)
            destPath = os.path.join(self.dirName,'media',destFile)
            # check if audio file already exists
            if os.path.exists(destPath):
                audioAction = QtGui.QInputDialog.getItem(self, "Audio file already exists!!", 
                        "An audio file is already attached to this interview. How would you like to proceed?",
                        ['Cancel import', "Replace old audio with new audio", "Add new audio to the end", "Insert new audio at beginning"],
                        0, False, QtCore.Qt.Dialog)
                #QgsMessageLog.logMessage(str(audioAction))
            else:
                audioAction = ('new',True)
            # act based on user decision
            if audioAction[0] == "Cancel import":
                return()
            elif audioAction[0] == 'Replace old audio with new audio':
                # calculate section length
                audioLen = self.importAudioCalculateRecordingLength(fname)
                segLength,audioMax = self.importAudioCalculateSectionLength(audioLen)
                if segLength > 0:
                    progress = QtGui.QProgressDialog("Please wait, importing audio", "", 0, 100);
                    progress.show()
                    progress.setValue(5)
                    #time.sleep(2)
                    # copy the old file
                    copyFile = "lmb-p%d-i%d-media-old.wav" % (self.projId,self.intvId)
                    copyPath = os.path.join(self.dirName, 'media', copyFile)
                    shutil.move(destPath,copyPath)
                    progress.setValue(50)
                    # import new file
                    self.importAudioFile(fname,destPath,segLength,audioMax)
                    progress.close()
                    progress = None
            elif audioAction[0] == 'Add new audio to the end':
                # determine audio length
                aL1 = self.importAudioCalculateRecordingLength(destPath)                
                aL2 = self.importAudioCalculateRecordingLength(fname) 
                audioLen = aL1 + aL2
                segLength,audioMax = self.importAudioCalculateSectionLength(audioLen)
                if segLength > 0:
                    progress = QtGui.QProgressDialog("Please wait, importing audio", "", 0, 100);
                    progress.show()
                    progress.setValue(5)
                    # copy the old file
                    copyFile = "lmb-p%d-i%d-media-old.wav" % (self.projId,self.intvId)
                    copyPath = os.path.join(self.dirName, 'media', copyFile)
                    shutil.move(destPath,copyPath)
                    progress.setValue(50)
                    # merge files
                    inFiles = [copyPath,fname]
                    self.importAudioMerge(destPath,inFiles)
                    # update sections
                    self.importAudioUpdateSections(segLength,audioMax)
                    progress.close()
                    progress = None
            elif audioAction[0] == 'Insert new audio at beginning':
                # determine audio length
                aL1 = self.importAudioCalculateRecordingLength(destPath)                
                aL2 = self.importAudioCalculateRecordingLength(fname) 
                audioLen = aL1 + aL2
                segLength,audioMax = self.importAudioCalculateSectionLength(audioLen)
                if segLength > 0:
                    progress = QtGui.QProgressDialog("Please wait, importing audio", "", 0, 100);
                    progress.show()
                    progress.setValue(5)
                    # copy the old file
                    copyFile = "lmb-p%d-i%d-media-old.wav" % (self.projId,self.intvId)
                    copyPath = os.path.join(self.dirName, 'media', copyFile)
                    shutil.move(destPath,copyPath)
                    progress.setValue(50)
                    # merge files
                    inFiles = [fname,copyPath]
                    self.importAudioMerge(destPath,inFiles)
                    # update sections
                    self.importAudioUpdateSections(segLength,audioMax)
                    progress.close()
                    progress = None
            elif audioAction[0] == 'new':
                # calculate section length
                audioLen = self.importAudioCalculateRecordingLength(fname)
                segLength,audioMax = self.importAudioCalculateSectionLength(audioLen)
                if segLength > 0:
                    progress = QtGui.QProgressDialog("Please wait, importing audio", "", 0, 100);
                    progress.show()
                    progress.setValue(35)
                    # import new file
                    self.importAudioFile(fname,destPath,segLength,audioMax)
                    progress.close()
                    progress = None
        return()

    #
    # import audio file
    #
    def importAudioFile(self,src,dest,segLength,audioMax):

        # copy the file
        shutil.copyfile(src,dest)
        # update sections
        self.importAudioUpdateSections(segLength,audioMax)
        
    #
    # import audio update sections
    #
    def importAudioUpdateSections(self,segLength,audioMax):
        # iterate over sections and update media start and end
        itemCount = self.lwSectionList.count()
        audioIdx = 0
        audioAtEnd = False
        for i in range(0,itemCount):
            secCode = self.lwSectionList.item(i).text()
            if not audioAtEnd:
                if audioIdx + segLength >= audioMax:
                    segLength = audioMax - audioIdx
                    audioAtEnd = True
                if i+1 == itemCount:
                    segLength = audioMax - audioIdx
                self.intvDict[secCode]["media_start_time"] = audioIdx
                audioIdx += segLength
                self.intvDict[secCode]["media_end_time"] = audioIdx
            else:
                self.intvDict[secCode]["media_start_time"] = 0
                self.intvDict[secCode]["media_end_time"] = 0
        self.interviewFileSave()
        self.disconnectSectionControls()
        self.interviewUnload()
        self.interviewLoad()
        self.connectSectionControls()
        
    #
    # import audio calculate recording length
    #
    def importAudioCalculateRecordingLength(self,src):
        # open file
        f = wave.open(src,'r')
        frames = f.getnframes()
        rate = f.getframerate() 
        f.close()
        audioLen = frames / float(rate)
        return(audioLen)
        
    #
    # import audio calculate section length
    #
    def importAudioCalculateSectionLength(self,audioLen):
        # get audio file duration
        audioMax = round(audioLen + 0.5)
        # split into equal parts
        secCnt = self.lwSectionList.count()
        segLength = int(round(float(audioMax) / secCnt))
        if segLength <= 3:
            messageText = 'The audio file is too short for the number of sections. '
            messageText += 'Are you confident this is the correct file? '
            messageText += 'Do you wish to proceed with the import?'
            response = QtGui.QMessageBox.warning(self, 'Warning',
               messageText, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if response == QtGui.QMessageBox.Yes:
                if segLength <= 2:
                    segLength = 1
                else:
                    segLength = 2
            else:
                segLength = 0
        return(segLength, audioMax)
        
    #
    # import audio merge files
    #
    def importAudioMerge(self,outFName,inFiles):
        
        output = wave.open(outFName, 'wb')
        x = 1
        for infile in inFiles:
            fileName = os.path.join(self.dirName,"media",infile)
            w = wave.open(fileName, 'rb')
            # write output file
            if x == 1:
                output.setparams(w.getparams())
                x += 1
            output.writeframes(w.readframes(w.getnframes()))
            w.close()
        output.close()

    #
    #####################################################
    #                     base layers                   #
    #####################################################

    #
    # load base layers
    #
    def baseLoadLayers(self):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
            if self.cbBoundary.isChecked():
                QgsMessageLog.logMessage(' - boundary checked')
            else:
                QgsMessageLog.logMessage(' - boundary not checked')
        # groups
        root = QgsProject.instance().layerTreeRoot()
        self.projectTree = self.baseLoadLegendTree(root)
        projectGroups = self.iface.legendInterface().groups()
        # clear menu
        self.baseMapButton.menu().clear()
        # clear overview
        self.iface.actionRemoveAllFromOverview().activate(0)
        # load layer groups to menu
        visibleGroupSet = False
        self.defaultBase = 0
        i = 0
        for group in self.baseGroups:
            self.baseGroupIdxs[self.baseGroups.index(group)] = projectGroups.index(group)
            # add to menu with lambda function
            menuItem_Base = self.baseMapButton.menu().addAction(group)
            receiver = lambda baseIndex=i: self.baseSelect(baseIndex)
            self.connect(menuItem_Base, QtCore.SIGNAL('triggered()'), receiver)
            self.baseMapButton.menu().addAction(menuItem_Base)
            # check visibility
            if visibleGroupSet == False:
                if self.iface.legendInterface().isGroupVisible(i):
                    self.defaultBase = i
                    visibleGroupSet = True
            i += 1
        self.baseSelectDefault()
        # set layer visbility
        validLayers = []
        layers = self.iface.legendInterface().layers()
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
        # set canvas view
        if self.boundaryLayer <> None:
            self.canvas.setExtent(self.boundaryLayer.extent())
        else:
            self.canvas.zoomToFullExtent()
        

    #
    # select base map - this doesn't change overview
    #
    def baseSelect(self, currentIndex):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself() + ':%d' % currentIndex)
        for x in range(len(self.baseGroups)):
            if x == currentIndex:
                self.baseMapButton.setText('Base Map: %s' % self.baseGroups[x])
                if self.iface.legendInterface().isGroupVisible(self.baseGroupIdxs[x]) == False:
                    self.iface.legendInterface().setGroupVisible(self.baseGroupIdxs[x],True)
            elif self.iface.legendInterface().isGroupVisible(self.baseGroupIdxs[x]) == True:
                self.iface.legendInterface().setGroupVisible(self.baseGroupIdxs[x],False)

    #
    # load legend tree
    #
    def baseLoadLegendTree(self, root):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        tree = []
        for child in root.children():
            if isinstance(child, QgsLayerTreeGroup):
                tree.append(['group',child.name(),'layers',self.baseLoadLegendTree(child)])
            elif isinstance(child, QgsLayerTreeLayer):
                tree.append(['layer',child.layerName(),child.layerId(),child.layer()])
        return(tree)

    #
    # select default
    #
    def baseSelectDefault(self):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        self.baseSelect(self.defaultBase)

    #
    # view boundary layer
    #
    def baseViewBoundary(self):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())

        if not self.loading:
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
    def baseViewReference(self):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())

        if not self.loading:
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
    def baseViewFeatures(self):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())

        if self.points_layer <> None and self.lines_layer <> None and self.polygons_layer <> None:
            try:
                if self.cbFeatures.isChecked():
                    # points
                    self.iface.legendInterface().setLayerVisible(self.points_layer, True)
                    self.iface.setActiveLayer(self.points_layer)
                    self.iface.actionAddToOverview().activate(0)
                    # lines
                    self.iface.legendInterface().setLayerVisible(self.lines_layer, True)
                    self.iface.setActiveLayer(self.lines_layer)
                    self.iface.actionAddToOverview().activate(0)
                    # polygons
                    self.iface.legendInterface().setLayerVisible(self.polygons_layer, True)
                    self.iface.setActiveLayer(self.polygons_layer)
                    self.iface.actionAddToOverview().activate(0)
                else:
                    # points
                    self.iface.legendInterface().setLayerVisible(self.points_layer, False)
                    self.iface.setActiveLayer(self.points_layer)
                    self.iface.actionAddToOverview().activate(0)
                    # lines
                    self.iface.legendInterface().setLayerVisible(self.lines_layer, False)
                    self.iface.setActiveLayer(self.lines_layer)
                    self.iface.actionAddToOverview().activate(0)
                    # polygons
                    self.iface.legendInterface().setLayerVisible(self.polygons_layer, False)
                    self.iface.setActiveLayer(self.polygons_layer)
                    self.iface.actionAddToOverview().activate(0)
            except:
                QgsMessageLog.logMessage('mapNavigator.viewFeatures generated an exception')
            
    #
    # view feature labels
    #
    def baseViewFeatureLabels(self):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())

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

    #
    # load interview layers
    #
    def baseLoadInterviewLayers(self):
        
        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
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
