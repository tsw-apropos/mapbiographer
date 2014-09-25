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
from ui_mapbio_transcriber import Ui_mapbioTranscriber
from audio_player import audioPlayer
from point_tool import lmbMapToolPoint
from line_tool import lmbMapToolLine
from polygon_tool import lmbMapToolPolygon
import inspect, re

class mapBiographerTranscriber(QtGui.QDockWidget, Ui_mapbioTranscriber):

    #
    # init method to define globals and make widget / method connections
    
    def __init__(self, iface):

        # debug setup
        self.basicDebug = False
        self.editDebug = False
        self.audioDebug = False
        self.spatialDebug = False
        self.debugFile = True
        self.df = None
        self.debugFileName = './transcriber.log'
        if self.basicDebug or self.editDebug or self.audioDebug or self.spatialDebug:
            self.myself = lambda: inspect.stack()[1][3]
            self.df = open(self.debugFileName,'w')
        if self.basicDebug:
            if self.debugFile == True:
                self.df.write('\n--Initialization--\n')
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        #
        # begin setup process
        QtGui.QDockWidget.__init__(self)
        self.setupUi(self)
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        self.iface.newProject()
        # clear selected layers
        tv = iface.layerTreeView()
        tv.selectionModel().clear()
        # set default projection if none set
        if self.canvas.mapSettings().hasCrsTransformEnabled() == False:
            self.canvas.mapSettings().setCrsTransformEnabled(True)
            self.canvas.mapSettings().setDestinationCrs( QgsCoordinateReferenceSystem(3857) )
        # global variables
        self.conn = None
        self.cur = None
        self.intvList = []
        self.interview_id = 0
        self.featureState = 'None'
        self.interviewState = 'New'
        # audio 
        self.audioDeviceIndex = None
        self.audioStartPosition = 0
        self.audioEndPosition = 0
        self.audioCurrentPosition = 0
        self.mediaState = 'paused'
        self.afName = ''
        # vector editing
        self.vectorEditing = False
        self.geomSourceAction = 'no change'
        self.editLayer = None
        self.previousSectionId = None
        self.previousPointId = None
        self.previousLineId = None
        self.previousPolygonId = None
        self.sectionData = None
        self.shiftKey = False
        # settings variables
        self.projectDir = '.'
        self.projectDB = ''
        self.qgsProject = ''
        self.baseGroups = []
        self.baseGroupIdxs = []
        self.boundaryLayerName = ''
        self.boundaryLayer = None
        self.enableReference = ''
        self.referenceLayerName = ''
        self.referenceLayer = None
        self.qgsProjectLoading = True
        # add panel
        self.iface.mainWindow().addDockWidget(QtCore.Qt.RightDockWidgetArea, self)
        # panel functionality
        self.setFeatures(self.DockWidgetMovable | self.DockWidgetFloatable)
        #
        # signals and slots setup
        # connect map tools
        self.connectMapTools()
        # map options
        QtCore.QObject.connect(self.cbBase, QtCore.SIGNAL("currentIndexChanged(int)"), self.selectBase)
        QtCore.QObject.connect(self.cbBoundary, QtCore.SIGNAL("currentIndexChanged(int)"), self.viewBoundary)
        QtCore.QObject.connect(self.cbReference, QtCore.SIGNAL("currentIndexChanged(int)"), self.viewReference)
        # connect interview selection panel controls
        QtCore.QObject.connect(self, QtCore.SIGNAL("topLevelChanged(bool)"), self.adjustPanelSize)
        QtCore.QObject.connect(self.cbInterviewSelection, QtCore.SIGNAL("currentIndexChanged(int)"), self.updateInterviewInfo)
        QtCore.QObject.connect(self.pbClose, QtCore.SIGNAL("clicked()"), self.closeTranscriber)
        # audio
        self.tbMediaPlay.setIcon(QtGui.QIcon(":/plugins/mapbiographer/media_play.png"))
        QtCore.QObject.connect(self.tbMediaPlay, QtCore.SIGNAL("clicked()"), self.playPauseMedia)
        self.tbAudioSettings.setMenu(QtGui.QMenu(self.tbAudioSettings))
        # section edit widgets
        QtCore.QObject.connect(self.lwSectionList, QtCore.SIGNAL("itemSelectionChanged()"), self.selectFeature)
        QtCore.QObject.connect(self.spMediaStart, QtCore.SIGNAL("valueChanged(int)"), self.enableSectionSaveCancel)
        QtCore.QObject.connect(self.spMediaEnd, QtCore.SIGNAL("valueChanged(int)"), self.enableSectionSaveCancel)
        QtCore.QObject.connect(self.hsSectionMedia, QtCore.SIGNAL("valueChanged(int)"), self.updateAudioCurrentPosition)
        QtCore.QObject.connect(self.cbSectionSecurity, QtCore.SIGNAL("currentIndexChanged(int)"), self.enableSectionSaveCancel)
        QtCore.QObject.connect(self.cbFeatureStatus, QtCore.SIGNAL("currentIndexChanged(int)"), self.featureStatusChanged)
        QtCore.QObject.connect(self.cbTimePeriod, QtCore.SIGNAL("currentIndexChanged(int)"), self.enableSectionSaveCancel)
        QtCore.QObject.connect(self.cbAnnualVariation, QtCore.SIGNAL("currentIndexChanged(int)"), self.enableSectionSaveCancel)
        QtCore.QObject.connect(self.pteSectionNote, QtCore.SIGNAL("textChanged()"), self.enableSectionSaveCancel)
        QtCore.QObject.connect(self.pteSectionText, QtCore.SIGNAL("textChanged()"), self.enableSectionSaveCancel)
        QtCore.QObject.connect(self.lwProjectCodes, QtCore.SIGNAL("itemClicked(QListWidgetItem*)"), self.addRemoveSectionTags)
        # connect section editing buttons
        QtCore.QObject.connect(self.pbSaveSection, QtCore.SIGNAL("clicked()"), self.saveSectionEdits)
        QtCore.QObject.connect(self.pbCancelSection, QtCore.SIGNAL("clicked()"), self.cancelSectionEdits)
        QtCore.QObject.connect(self.pbDeleteSection, QtCore.SIGNAL("clicked()"), self.deleteSection)
        #
        # map projections
        canvasCRS = self.canvas.mapSettings().destinationCrs()
        layerCRS = QgsCoordinateReferenceSystem(3857)
        self.xform = QgsCoordinateTransform(canvasCRS, layerCRS)
        #
        # check for valid audio device
        self.populateAudioDeviceList()
        #
        # final prep for transcribing interviews
        # open project
        result = self.readSettings()
        if result == 0:
            result = self.openTranscriber()
            if result <> 0:
                QtGui.QMessageBox.information(self, 'message',
                'Missing Files. Please correct. Closing.', QtGui.QMessageBox.Ok)
                self.closeTranscriber()
        else:
            QtGui.QMessageBox.information(self, 'message',
            'Map Biographer Settings Error. Please correct. Closing.', QtGui.QMessageBox.Ok)
            self.closeTranscriber()
        # activate pan tool
        self.activatePanTool()
        # set canvas view
        if self.boundaryLayer <> None:
            self.canvas.setExtent(self.boundaryLayer.extent())
        else:
            self.canvas.zoomToFullExtent()

    #
    # redefine close event to make sure it closes properly because panel close
    # icon can not be prevented on Mac OS X when panel is floating

    def closeEvent(self, event):

        self.closeTranscriber()

    #
    # connect map tools

    def connectMapTools(self):
        
        # use debug track order of calls
        if self.basicDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
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
        QtCore.QObject.connect(self.tbPoint, QtCore.SIGNAL("clicked()"), self.activatePointCapture)
        self.pointTool.rbFinished.connect(self.placePoint)
        # lines
        QtCore.QObject.connect(self.tbLine, QtCore.SIGNAL("clicked()"), self.activateLineCapture)
        self.lineTool.rbFinished.connect(self.placeLine)
        # polygons
        QtCore.QObject.connect(self.tbPolygon, QtCore.SIGNAL("clicked()"), self.activatePolygonCapture)
        self.polygonTool.rbFinished.connect(self.placePolygon)
        # edit
        QtCore.QObject.connect(self.tbEdit, QtCore.SIGNAL("clicked()"), self.activateSpatialEdit)
        # move
        QtCore.QObject.connect(self.tbMove, QtCore.SIGNAL("clicked()"), self.activateSpatialMove)
        # pan
        QtCore.QObject.connect(self.tbPan, QtCore.SIGNAL("clicked()"), self.activatePanTool)
        # non-spatial / new section
        QtCore.QObject.connect(self.tbNonSpatial, QtCore.SIGNAL("clicked()"), self.createNonSpatialSection)
        # get button for Node Tool
        self.nodeButton = None
        dtb = self.iface.digitizeToolBar()
        for cld in dtb.children():
            if 'QToolButton' in str(cld.__class__) and len(cld.actions()) > 0:
                if 'NodeTool' in cld.actions()[0].objectName():
                    self.nodeButton = cld
                    break
        # get button for Move Tool
        self.moveButton = None
        for cld in dtb.children():
            if 'QToolButton' in str(cld.__class__) and len(cld.actions()) > 0:
                if 'MoveFeature' in cld.actions()[0].objectName():
                    self.moveButton = cld
                    break

    #
    # disconnect map tools

    def disconnectMapTools(self):

        # use debug track order of calls
        if self.basicDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # break connections to custom tools
        result = QtCore.QObject.disconnect(self.pointTool, QtCore.SIGNAL("rbFinished(QgsGeometry*)"), self.placePoint)
        result = QtCore.QObject.disconnect(self.lineTool, QtCore.SIGNAL("rbFinished(QgsGeometry*)"), self.placeLine)
        result = QtCore.QObject.disconnect(self.polygonTool, QtCore.SIGNAL("rbFinished(QgsGeometry*)"), self.placePolygon)
        result = QtCore.QObject.disconnect(self.tbPan, QtCore.SIGNAL("clicked()"), self.activatePanTool)


    #####################################################
    #           project and panel management            #
    #####################################################

    #
    # read QGIS settings

    def readSettings( self ):

        self.projectLoading = True
        # use debug track order of calls
        if self.basicDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        s = QtCore.QSettings()
        rv = s.value('mapBiographer/projectDir')
        if os.path.exists(rv):
            self.projectDir = rv
        else:
            self.projectDir = '.'
        rv = s.value('mapBiographer/projectDB')
        if os.path.exists(os.path.join(self.projectDir,rv)):
            self.projectDB = rv
        else:
            self.projectDB = ''
            return(-1)
        rv = s.value('mapBiographer/qgsProject')
        if os.path.exists(rv):
            self.qgsProject = rv
        else:
            self.qgsProject = ''
            return(-1)
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
        self.projectLoading = False

        return(0)
        
    #
    # open map biographer project and display interview list

    def openTranscriber(self):

        # use debug track order of calls
        if self.basicDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        self.projectLoading = True
        # connect to database
        self.conn = sqlite.connect(os.path.join(self.projectDir,self.projectDB))
        self.cur = self.conn.cursor()
        #
        # project info and defaults
        sql = 'SELECT id,code,default_codes,default_time_periods,default_annual_variation FROM project;'
        rs = self.cur.execute(sql)
        projData = rs.fetchall()
        # basic setup
        self.leProjectCode.setText(projData[0][1])
        # content codes
        self.default_codes = ['Non-spatial']
        self.lwProjectCodes.clear()
        self.lwProjectCodes.addItem('S')
        codeList = projData[0][2].split('\n')
        for item in codeList:
            if item <> '':
                code, defn = item.split('=')
                self.default_codes.append(defn.strip())
                self.lwProjectCodes.addItem(code.strip())
        # section references
        self.cbFeatureStatus.clear()
        self.cbFeatureStatus.addItems(['none','is unique'])
        self.cbFeatureStatus.setCurrentIndex(0)
        # time periods
        self.default_time_periods = ['R','U','N']
        self.cbTimePeriod.clear()
        self.cbTimePeriod.addItems(['Refused','Unknown','Not Recorded'])
        if projData[0][3] <> None:
            timeList = projData[0][3].split('\n')
            for item in timeList:
                if item <> '':
                    defn,desc = item.split('=')
                    self.default_time_periods.append(defn.strip())
                    self.cbTimePeriod.addItem(desc.strip())
        self.cbTimePeriod.setCurrentIndex(1)
        # annnual variation
        self.default_annual_variation = ['R','U','N','SP','SE','Y']
        self.cbAnnualVariation.clear()
        self.cbAnnualVariation.addItems(['Refused','Unknown','Not Recorded','Sporadic','Seasonal','All Year'])
        if projData[0][4] <> None:
            seasonList = projData[0][4].split('\n')
            for item in seasonList:
                if item <> '':
                    defn,desc = item.split('=')
                    self.default_annual_variation.append(defn.strip())
                    self.cbAnnualVariation.addItem(desc.strip())
        self.cbAnnualVariation.setCurrentIndex(1)
        # security
        self.default_security = ['PU','CO','RS','PR']
        self.cbSectionSecurity.clear()
        self.cbSectionSecurity.addItems(['Public','Community','Restricted','Private'])
        self.cbSectionSecurity.setCurrentIndex(0)
        #
        # map parameters
        # load QGIS project
        if QgsProject.instance().fileName() <> self.qgsProject:
            self.iface.newProject()
            QgsProject.instance().read(QtCore.QFileInfo(self.qgsProject))
        # gather information about what is available in the QGIS project
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
        for layer in layers:
            validLayers.append(layer.name())
            if layer.name() == self.boundaryLayerName:
                self.boundaryLayer = layer
                if self.iface.legendInterface().isLayerVisible(layer):
                    self.cbBoundary.setCurrentIndex(1)
                else:
                    self.cbBoundary.setCurrentIndex(0)
            if layer.name() == self.referenceLayerName:
                self.referenceLayer = layer
                if self.iface.legendInterface().isLayerVisible(layer):
                    self.cbReference.setCurrentIndex(1)
                else:
                    self.cbReference.setCurrentIndex(0)
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
        self.projectLoading = False
        #
        # populate lists
        self.populateInterviewList()
            
        return(0)

    #
    # populate interview list in combobox
    
    def populateInterviewList(self):

        # use debug track order of calls
        if self.basicDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        #
        sql = "SELECT a.id, a.code FROM interviews a "
        sql += "WHERE a.data_status = 'RC' AND a.id IN "
        sql += "(SELECT DISTINCT interview_id FROM interview_sections);"
        rs = self.cur.execute(sql)
        intvData = rs.fetchall()
        if len(intvData) == 0:
            QtGui.QMessageBox.warning(self.iface.mainWindow(), 'Warning',
            "No completed interviews exist.", QtGui.QMessageBox.Ok)
            self.closeInterview()
            self.closeTranscriber()
        else:
            self.cbInterviewSelection.clear()
            self.intvList = []
            for row in intvData:
                sql = "SELECT c.first_name || ' ' || c.last_name as participant FROM "
                sql += "participants c, interviewees b "
                sql += "WHERE c.id = b.participant_id AND "
                sql += "b.interview_id = %d;" % row[0]
                rs = self.cur.execute(sql)
                userData = rs.fetchall()
                nameList = ''
                for user in userData:
                    nameList = nameList + user[0] + ', '
                nameList = nameList[:-2]
                self.cbInterviewSelection.addItem(row[1])
                self.intvList.append([row[0],row[1],nameList])
            self.updateInterviewInfo(0)
            self.cbInterviewSelection.setCurrentIndex(0)
            self.pteParticipants.setPlainText(self.intvList[0][2])

    #
    # update interview info 

    def updateInterviewInfo(self, cIndex):

        # use debug track order of calls
        if self.basicDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        #
        # update interface when an interview is selected
        if len(self.intvList) > 0:
            self.pteParticipants.setPlainText(self.intvList[cIndex][2])
            self.interview_id = self.intvList[cIndex][0]
            self.interview_code = self.intvList[cIndex][1]
            self.loadInterview()
        else:
            self.interview_id = None
            self.interview_code = ''
            self.pteParticipants.setPlainText('')

    #
    # adjust panel size

    def adjustPanelSize(self):

        if self.isFloating() == True:
            self.setFixedHeight(715)
        else:
            self.setFixedHeight(705)

    #
    # load interview

    def loadInterview(self):

        # use debug track order of calls
        if self.basicDebug:
            if self.debugFile == True:
                self.df.write('\n--Loading Interview--\n')
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # get path for audio file and create prefix
        s = QtCore.QSettings()
        dirName = s.value('mapBiographer/projectDir')
        self.afName = os.path.join(dirName, self.interview_code + '.wav')
        if os.path.exists(self.afName):
            self.tbMediaPlay.setEnabled(True)
            self.hsSectionMedia.setEnabled(True)
            self.mediaState = 'paused'
        else:
            self.tbMediaPlay.setDisabled(True)
            self.hsSectionMedia.setDisabled(True)
            self.mediaState = 'disabled'
        # remove previous interview
        if self.interviewState <> 'New':
            self.interviewState = 'Unload'
            self.unloadInterview()
        self.interviewState == 'Load'
        #self.lwSectionList.clear()
        #
        # prepare for new interview
        # reset interview variables
        self.section_id = 0
        self.point_id = 0
        self.line_id = 0
        self.polygon_id = 0
        self.startTime = 0
        self.pauseDuration = 0
        self.startPause = 0
        self.currentSequence = 0
        self.maxCodeNumber = 0
        self.currentCodeNumber = 0
        self.audioPartNo = 1
        self.currentFeature = 'ns'
        self.selectedCodeCount = 0
        # load starting points
        # get previous section id
        sql = 'SELECT max(id) FROM interview_sections;'
        rs = self.cur.execute(sql)
        rsData = rs.fetchall()
        if rsData[0][0] == None:
            self.previousSectionId = 0
        else:
            self.previousSectionId = rsData[0][0]
        # get previous point id
        sql = 'SELECT max(id) FROM points;'
        rs = self.cur.execute(sql)
        rsData = rs.fetchall()
        if rsData[0][0] == None:
            self.previousPointId = 0
        else:
            self.previousPointId = rsData[0][0]
        # get previous line id
        sql = 'SELECT max(id) FROM lines;'
        rs = self.cur.execute(sql)
        rsData = rs.fetchall()
        if rsData[0][0] == None:
            self.previousLineId = 0
        else:
            self.previousLineId = rsData[0][0]
        # get previous polygon id
        sql = 'SELECT max(id) FROM polygons;'
        rs = self.cur.execute(sql)
        rsData = rs.fetchall()
        if rsData[0][0] == None:
            self.previousPolygonId = 0
        else:
            self.previousPolygonId = rsData[0][0]
        # get max code value
        sql = 'SELECT max(sequence_number) FROM interview_sections '
        sql += 'WHERE interview_id = %d ' % self.interview_id
        rs = self.cur.execute(sql)
        rsData = rs.fetchall()
        if rsData[0][0] == None:
            self.maxCodeNumber = 1
        else:
            self.maxCodeNumber = rsData[0][0]
        # enable navigation
        self.enableSectionControls()
        # load interview map layers
        self.addInterviewMapLayers()
        # load interview sections and update link list for cbFeatureStatus
        sql = "SELECT id, section_code, geom_source, sequence_number FROM interview_sections "
        sql += "WHERE interview_id = %d ORDER BY sequence_number;" % self.interview_id
        rs = self.cur.execute(sql)
        sectionList = rs.fetchall()
        self.cbFeatureStatus.clear()
        self.cbFeatureStatus.addItems(['none','unique'])
        for section in sectionList:
            self.lwSectionList.addItem(section[1])
            if section[2] in ('pt','ln','pl'):
                self.cbFeatureStatus.addItem('same as %s' % section[1])
        self.interviewState = 'View'
        if len(sectionList) > 0:
            self.lwSectionList.setCurrentItem(self.lwSectionList.item(0))
        
    #
    # unload interview

    def unloadInterview(self):

        # use debug track order of calls
        if self.basicDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        self.interviewState = 'Unload'
        # clear section list
        self.lwSectionList.clear()
        # remove layers if they exist
        self.removeInterviewMapLayers()

    #
    # close trancription interface
    
    def closeTranscriber (self):

        # use debug track order of calls
        if self.basicDebug:
            if self.debugFile == True:
                self.df.write('\n--Close Transcriber--\n')
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # unload interview
        self.unloadInterview()
        # disconnect map tools
        self.disconnectMapTools()
        # close database connection
        if self.conn <> None:
            self.conn.close()
        # hide panel
        self.hide()
        # restore window state
        s = QtCore.QSettings()
        geom = s.value('mapBiographer/geom')
        state = s.value('mapBiographer/state')
        self.iface.mainWindow().restoreGeometry(geom)
        self.iface.mainWindow().restoreState(state)
        # reset canvas view
        if self.boundaryLayer <> None:
            self.canvas.setExtent(self.boundaryLayer.extent())
        else:
            self.canvas.zoomToFullExtent()
        # deselect active layer and select active layer again
        tv = self.iface.layerTreeView()
        tv.selectionModel().clear()
        a = self.iface.legendInterface().layers()
        if len(a) > 0:
            self.iface.setActiveLayer(a[0])
        self.iface.newProject()
        if self.basicDebug or self.editDebug or self.audioDebug or self.spatialDebug:
            self.df.close()

    #
    # add interview map layers in order of polygon, line and point to ensure visibility

    def addInterviewMapLayers(self):

        if self.basicDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # load layers
        uri = QgsDataSourceURI()
        uri.setDatabase(os.path.join(self.projectDir,self.projectDB))
        schema = ''
        # set interview_id filter for all layers
        sql = 'interview_id = %d' % self.interview_id
        #
        # polygons layer
        table = 'polygons'
        geom_column = 'geom'
        uri.setDataSource(schema, table, geom_column, sql)
        display_name = 'polygons'
        self.polygons_layer = QgsVectorLayer(uri.uri(), display_name, 'spatialite')
        # set display characteristics
        self.polygons_layer.rendererV2().symbol().setAlpha(0.5)
        symbolLayer = self.polygons_layer.rendererV2().symbol().symbolLayer(0)
        symbolLayer.setFillColor(QtGui.QColor('#47b247'))
        symbolLayer.setBorderColor(QtGui.QColor('#245924'))
        symbolLayer.setBorderWidth(0.6)
        QgsMapLayerRegistry.instance().addMapLayer(self.polygons_layer)
        # set label
        palyrPolygons = QgsPalLayerSettings()
        palyrPolygons.readFromLayer(self.polygons_layer)
        palyrPolygons.enabled = True
        palyrPolygons.fieldName = 'section_code'
        palyrPolygons.setDataDefinedProperty(QgsPalLayerSettings.Size,True,True,'10','')
        palyrPolygons.writeToLayer(self.polygons_layer)
        #
        # lines layer
        table = 'lines'
        geom_column = 'geom'
        uri.setDataSource(schema, table, geom_column, sql)
        display_name = 'lines'
        self.lines_layer = QgsVectorLayer(uri.uri(), display_name, 'spatialite')
        # set display characteristics
        symbol = self.lines_layer.rendererV2().symbol()
        symbol.setColor(QtGui.QColor('#245924'))
        symbol.setWidth(0.6)
        QgsMapLayerRegistry.instance().addMapLayer(self.lines_layer)
        # set label
        palyrLines = QgsPalLayerSettings()
        palyrLines.readFromLayer(self.lines_layer)
        palyrLines.enabled = True
        palyrLines.fieldName = 'section_code'
        palyrLines.placement= QgsPalLayerSettings.Line
        palyrLines.placementFlags = QgsPalLayerSettings.AboveLine
        palyrLines.setDataDefinedProperty(QgsPalLayerSettings.Size,True,True,'10','')
        palyrLines.writeToLayer(self.lines_layer)
        #
        # points layer
        table = 'points'
        geom_column = 'geom'
        uri.setDataSource(schema, table, geom_column, sql)
        display_name = 'points'
        self.points_layer = QgsVectorLayer(uri.uri(), display_name, 'spatialite')
        # set display characteristics
        symbol = self.points_layer.rendererV2().symbols()[0]
        symbol.setSize(3)
        symbol.setColor(QtGui.QColor('#47b247'))
        symbol.setAlpha(0.5)
        QgsMapLayerRegistry.instance().addMapLayer(self.points_layer)
        # set label
        palyrPoints = QgsPalLayerSettings()
        palyrPoints.readFromLayer(self.points_layer)
        palyrPoints.enabled = True
        palyrPoints.fieldName = 'section_code'
        palyrPoints.placement= QgsPalLayerSettings.OverPoint
        palyrPoints.quadrantPosition = QgsPalLayerSettings.QuadrantBelowRight
        palyrPoints.setDataDefinedProperty(QgsPalLayerSettings.Size,True,True,'10','')
        palyrPoints.setDataDefinedProperty(QgsPalLayerSettings.OffsetQuad,True, True, '8','')
        palyrPoints.writeToLayer(self.points_layer)

    #
    # remove interview map layers

    def removeInterviewMapLayers(self):

        if self.basicDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        try:
            # remove layers
            QgsMapLayerRegistry.instance().removeMapLayer(self.points_layer.id())
            QgsMapLayerRegistry.instance().removeMapLayer(self.lines_layer.id())
            QgsMapLayerRegistry.instance().removeMapLayer(self.polygons_layer.id())
        except:
            pass 

    #
    # show interview map layers

    def showInterviewMapLayers(self):
        
        if self.basicDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        self.iface.legendInterface().setLayerVisible(self.points_layer, True)
        self.iface.legendInterface().setLayerVisible(self.lines_layer, True)
        self.iface.legendInterface().setLayerVisible(self.polygons_layer, True)

    #
    # hide interview map layers

    def hideInterviewMapLayers(self):

        if self.basicDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        self.iface.legendInterface().setLayerVisible(self.points_layer, False)
        self.iface.legendInterface().setLayerVisible(self.lines_layer, False)
        self.iface.legendInterface().setLayerVisible(self.polygons_layer, False)


    #####################################################
    #              base and reference maps              #
    #####################################################

    #
    # select base map

    def selectBase( self ):

        if self.projectLoading == False:
            listIdx = self.cbBase.currentIndex()
            for x in range(len(self.baseGroups)):
                if x == listIdx:
                    if self.iface.legendInterface().isGroupVisible(self.baseGroupIdxs[x]) == False:
                        self.iface.legendInterface().setGroupVisible(self.baseGroupIdxs[x],True)
                elif self.iface.legendInterface().isGroupVisible(self.baseGroupIdxs[x]) == True:
                    self.iface.legendInterface().setGroupVisible(self.baseGroupIdxs[x],False)
        
    #
    # view boundary layer

    def viewBoundary( self ):

        if self.projectLoading == False:
            if self.cbBoundary.currentIndex() == 0:
                self.iface.legendInterface().setLayerVisible(self.boundaryLayer,False)
            else:
                self.iface.legendInterface().setLayerVisible(self.boundaryLayer,True)

    #
    # view reference layer

    def viewReference( self ):

        if self.projectLoading == False:
            if self.cbReference.currentIndex() == 0:
                self.iface.legendInterface().setLayerVisible(self.referenceLayer,False)
            else:
                self.iface.legendInterface().setLayerVisible(self.referenceLayer,True)
        
    
    #####################################################
    #               audio operations                    #
    #####################################################

    #
    # populate audio device list

    def populateAudioDeviceList(self):

        # use debug track order of calls
        if self.audioDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # create array to store info
        self.deviceList = []
        p = pyaudio.PyAudio()
        # add devices with input channels
        bestChoice = 0
        # clear menu actions
        self.tbAudioSettings.menu().clear()
        #self.tbAudioSettings.menu().setTitle('Select Audio Device')
        x = 0
        for i in range(p.get_device_count()):
            devinfo = p.get_device_info_by_index(i)
            if devinfo['maxOutputChannels'] > 0:
                    # add to device list
                    self.deviceList.append([i,devinfo['name']])
                    # create a menu item action
                    menuItem_AudioDevice = self.tbAudioSettings.menu().addAction(devinfo['name'])
                    # create lambda function
                    receiver = lambda deviceIndex=i: self.selectDevice(deviceIndex)
                    # link lambda function to menu action
                    self.connect(menuItem_AudioDevice, QtCore.SIGNAL('triggered()'), receiver)
                    # add to menu
                    self.tbAudioSettings.menu().addAction(menuItem_AudioDevice)
                    if devinfo['name'] == 'default':
                        bestChoice = x
                    x += 1
        p.terminate()
        self.audioDeviceIndex = self.deviceList[bestChoice][0]
        if len(self.deviceList) > 0:
            self.setWindowTitle('LOUIS Map Biographer - Transcription Tool (Audio Device: %s)' % self.deviceList[bestChoice][1])
        else:
            self.setWindowTitle('LOUIS Map Biographer - Transcription Tool (No Audio Device Found)')

    #
    # select audio device

    def selectDevice(self,deviceIndex):

        # use debug track order of calls
        if self.audioDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        self.audioDeviceIndex = deviceIndex
        self.setWindowTitle('LOUIS Map Biographer - Transcription Tool (Audio Device: %s)' % self.deviceList[deviceIndex][1])

    #
    # play audio

    def playAudio(self):

        # use debug track order of calls
        if self.audioDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # create worker
        worker = audioPlayer(self.afName,self.audioDeviceIndex,self.audioCurrentPosition,self.audioEndPosition)
        # start worker in new thread
        thread = QtCore.QThread(self)
        worker.moveToThread(thread)
        # connect thread events to functions
        worker.status.connect(self.updateAudioStatus)
        worker.error.connect(self.notifyAudioError)
        worker.progress.connect(self.updateSliderPosition)
        thread.started.connect(worker.run)
        # run
        thread.start()
        # manage thread and worker
        self.thread = thread
        self.worker = worker

    #
    # play or pause audio

    def playPauseMedia(self):

        # use debug track order of calls
        if self.audioDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        if self.mediaState == 'paused':
            self.playAudio()
        elif self.mediaState == 'playing':
            self.stopAudio()

    #
    # stop audio

    def stopAudio(self):
        
        # use debug track order of calls
        if self.audioDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        self.worker.kill()           
        self.worker.deleteLater()
        self.thread.quit()
        self.thread.wait()
        self.thread.deleteLater()

    #
    # update audio status

    def updateAudioStatus(self, statusMessage):

        # use debug track order of calls
        if self.audioDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
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
    # update audio current position

    def updateAudioCurrentPosition(self):

        self.audioCurrentPosition = self.hsSectionMedia.value()

    #
    # notify of audio error - for debugging purposes

    def notifyAudioError(self, e, exception_string):

        # use debug track order of calls
        if self.audioDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        errorMessage = 'Audio thread raised an exception:\n' + format(exception_string)
        QtGui.QMessageBox.critical(self, 'message',
            errorMessage, QtGui.QMessageBox.Ok)
        self.stopAudio()
        self.finishInterview()

    #
    # update slider position

    def updateSliderPosition(self, position):

        self.hsSectionMedia.setValue(position)


    #####################################################
    #           section editing controls                #
    #####################################################
        
    #
    # disable section controls

    def disableSectionControls(self):

        # use debug track order of calls
        if self.editDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # make sure buttons are disabled
        # add features
        self.tbNonSpatial.setDisabled(True)
        self.tbNonSpatial.setChecked(False)
        self.tbPoint.setDisabled(True)
        self.tbPoint.setChecked(False)
        self.tbLine.setDisabled(True)
        self.tbLine.setChecked(False)
        self.tbPolygon.setDisabled(True)
        self.tbPolygon.setChecked(False)
        # navigation
        self.tbPan.setDisabled(True)
        self.tbPan.setChecked(False)
        # edit features
        self.tbEdit.setDisabled(True)
        self.tbEdit.setChecked(False)
        self.tbMove.setDisabled(True)
        self.tbMove.setChecked(False)
        # edit widgets
        self.lwSectionList.setDisabled(True)
        self.leCode.setDisabled(True)
        self.cbSectionSecurity.setDisabled(True)
        self.pteTags.setDisabled(True)
        self.cbFeatureStatus.setDisabled(True)
        self.cbTimePeriod.setDisabled(True)
        self.cbAnnualVariation.setDisabled(True)
        self.pteSectionNote.setDisabled(True)
        self.pteSectionText.setDisabled(True)
        # edit buttons
        self.pbSaveSection.setDisabled(True)
        self.pbCancelSection.setDisabled(True)
        self.pbDeleteSection.setDisabled(True)

    #
    # enable section controls

    def enableSectionControls(self):

        # use debug track order of calls
        if self.editDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # make sure buttons are disabled
        # add features
        self.tbNonSpatial.setEnabled(True)
        self.tbNonSpatial.setChecked(False)
        self.tbPoint.setDisabled(True)
        self.tbPoint.setChecked(False)
        self.tbLine.setDisabled(True)
        self.tbLine.setChecked(False)
        self.tbPolygon.setDisabled(True)
        self.tbPolygon.setChecked(False)
        # navigation
        self.tbPan.setEnabled(True)
        self.tbPan.setChecked(False)
        # edit features
        # Note: only enabled when spatial section is selected
        # edit widgets
        self.lwSectionList.setEnabled(True)
        self.leCode.setEnabled(True)
        self.cbSectionSecurity.setEnabled(True)
        self.pteTags.setEnabled(True)
        self.cbFeatureStatus.setEnabled(True)
        self.cbTimePeriod.setEnabled(True)
        self.cbAnnualVariation.setEnabled(True)
        self.pteSectionNote.setEnabled(True)
        self.pteSectionText.setEnabled(True)

    #
    # enable save, cancel and delete buttons

    def enableSectionSaveCancel(self):

        if self.interviewState == 'View' and self.featureState == 'View':
            # use debug track order of calls
            if self.editDebug:
                if self.debugFile == True:
                    self.df.write(self.myself()+ '\n')
                else:
                    QtGui.QMessageBox.warning(self, 'DEBUG',
                        self.myself(), QtGui.QMessageBox.Ok)
            # method body
            # prevent section from being changed
            self.lwSectionList.setDisabled(True)
            # enable save and cancel
            self.pbSaveSection.setEnabled(True)
            self.pbCancelSection.setEnabled(True)
            self.pbDeleteSection.setEnabled(True)
            # disable new section
            self.tbNonSpatial.setDisabled(True)
            self.featureState = 'Edit'

    #
    # disable save and cancel buttons, but leave delete enabled

    def disableSectionSaveCancel(self):

        if self.interviewState == 'View':
            # use debug track order of calls
            if self.editDebug:
                if self.debugFile == True:
                    self.df.write(self.myself()+ '\n')
                else:
                    QtGui.QMessageBox.warning(self, 'DEBUG',
                        self.myself() + self.featureState, QtGui.QMessageBox.Ok)
            # method body
            # allow section from being changed
            self.lwSectionList.setEnabled(True)
            # disable save and cancel
            self.pbSaveSection.setDisabled(True)
            self.pbCancelSection.setDisabled(True)
            self.pbDeleteSection.setEnabled(True)
            # enable new section tool
            self.tbNonSpatial.setEnabled(True)
            # adjust state
            if self.featureState == 'Edit':
                self.featureState = 'View'

    #
    # enable section cancel and save (optionally) buttons but disable delete

    def enableSectionCancel(self,enableSave=False):

        if self.interviewState == 'View':
            # use debug track order of calls
            if self.editDebug:
                if self.debugFile == True:
                    self.df.write(self.myself()+ '\n')
                else:
                    QtGui.QMessageBox.warning(self, 'DEBUG',
                        self.myself(), QtGui.QMessageBox.Ok)
            # method body
            # prevent section from being changed
            self.lwSectionList.setDisabled(True)
            self.pbCancelSection.setEnabled(True)
            if enableSave == True:
                self.pbSaveSection.setEnabled(True)
            else:
                self.pbSaveSection.setDisabled(True)
            self.pbDeleteSection.setDisabled(True)
            # enable move and edit
            self.tbMove.setEnabled(True)
            self.tbEdit.setEnabled(True)
            self.tbNonSpatial.setDisabled(True)


    #####################################################
    #           section creation and deletion           #
    #####################################################

    #
    # create non-spatial section

    def createNonSpatialSection(self):

        # use debug track order of calls
        if self.editDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        self.currentFeature = 'ns'
        self.activatePanTool()
        self.createSectionRecord()
        # commit section 
        self.conn.commit()
        # reset state
        self.featureState == 'View'
        # add entry to list
        self.addSectionEntry()

    #
    # create section record - creates record in database and sets global variables

    def createSectionRecord(self):

        # use debug track order of calls
        if self.editDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # set state
        self.featureState = 'Create'
        # set date information
        self.section_date_created = datetime.datetime.now().isoformat()[:10]
        self.section_date_modified = self.section_date_created 
        # set media times for new section and update media time for existing section
        media_start_time = self.seconds2timeString(self.audioEndPosition-1)
        media_end_time = self.seconds2timeString(self.audioEndPosition)
        sql = "UPDATE interview_sections "
        sql += 'SET media_end_time = "%s" ' % media_start_time
        sql += "WHERE interview_id = %d AND id = %d " % (self.interview_id, self.section_id)
        self.cur.execute(sql)
        # get next section id
        self.section_id = self.previousSectionId + 1
        self.previousSectionId = self.section_id
        # insert section record
        spatial_data_source = 'OS'
        # create new record
        contentCode = "S"
        data_security = 'PU'
        tags = 'S'
        use_period = 'U'
        annual_variation = 'U'
        note = ''
        # insert a new record after the current one
        newSequence = self.currentSequence + 1
        # update subsequence sections
        sql = "UPDATE interview_sections "
        sql += "SET sequence_number = sequence_number + 1 "
        sql += "WHERE interview_id = %d AND " % self.interview_id
        sql += "sequence_number > %d;" % self.currentSequence
        self.cur.execute(sql)
        self.conn.commit()
        self.maxCodeNumber += 1
        self.currentSectionCode = '%s%04d' % (contentCode,self.maxCodeNumber)
        sql = 'INSERT INTO interview_sections (id, interview_id, sequence_number, '
        sql += 'content_code, section_code, note, use_period, annual_variation, '
        sql += 'spatial_data_source, geom_source, tags, media_start_time, media_end_time, '
        sql += 'data_security, date_created, date_modified) VALUES '
        sql += '(%d,%d,' % (self.section_id, self.interview_id)
        sql += '%d,"%s","%s","%s",' % (newSequence, contentCode, self.currentSectionCode, note)
        sql += '"%s","%s","%s",' % (use_period, annual_variation, spatial_data_source)
        sql += '"%s","%s","%s","%s","%s",' % (self.currentFeature,tags,media_start_time,media_end_time,data_security)
        sql += '"%s","%s");' % (self.section_date_created, self.section_date_modified)
        self.cur.execute(sql)
        # set defaults
        self.previousContentCode = contentCode 
        self.previousSecurity = data_security
        self.previousTags = tags
        self.previousUsePeriod = use_period
        self.previousAnnualVariation = annual_variation
        self.previousNote = note
        self.currentSequence = newSequence
        self.currentCodeNumber = self.maxCodeNumber
    #
    # add section record to list widget - called after a section is fully created
    
    def addSectionEntry(self):

        # use debug track order of calls
        if self.editDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # clear selected tags
        selectedItems = self.lwProjectCodes.selectedItems()
        for item in selectedItems:
            self.lwProjectCodes.setItemSelected(item,False)
        # insert into section list
        self.lwSectionList.insertItem(self.lwSectionList.currentRow()+1,self.currentSectionCode)
        # set new row as current which will trigger select and load
        self.lwSectionList.setCurrentRow(self.lwSectionList.currentRow()+1)
        # set action buttons
        self.disableSectionSaveCancel()

    #
    # update map feature when a spatial feature is edited

    def updateMapFeature(self):

        # use debug track order of calls
        if self.editDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        self.editLayer.selectAll()
        feat2 = self.editLayer.selectedFeatures()[0]
        if self.currentFeature == 'pt':
            # update database
            sql = "UPDATE points "
            sql += "SET geom = GeomFromText('%s',3857) " % feat2.geometry().exportToWkt()
            sql += "WHERE id = %d " % self.point_id
            self.cur.execute(sql)
        elif self.currentFeature == 'ln':
            # update database
            sql = "UPDATE lines "
            sql += "SET geom = GeomFromText('%s',3857) " % feat2.geometry().exportToWkt()
            sql += "WHERE id = %d " % self.line_id
            self.cur.execute(sql)
        elif self.currentFeature == 'pl':
            # update database
            sql = "UPDATE polygons "
            sql += "SET geom = GeomFromText('%s',3857) " % feat2.geometry().exportToWkt()
            sql += "WHERE id = %d " % self.polygon_id
            self.cur.execute(sql)
        # update scale after editing
        sql = "UPDATE interview_sections "
        sql += "SET spatial_data_scale = '%s' " % str(int(self.canvas.scale()))
        sql += "WHERE interview_id = %d and id = %d " % (self.interview_id, self.section_id)
        self.cur.execute(sql)
        self.conn.commit()
        # reset flag
        self.vectorEditing = False
        # remove layer
        self.editLayer.commitChanges()
        QgsMapLayerRegistry.instance().removeMapLayer(self.editLayer.id())
        self.activatePanTool()
        
    #
    # delete map feature from a section

    def deleteMapFeature(self, oldGeomSource):

        # use debug track order of calls
        if self.editDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # delete spatial records
        if oldGeomSource == 'pt':
            sql = "DELETE FROM points WHERE interview_id = %d " % self.interview_id
            sql += "AND section_id = %d;" % self.section_id
        elif oldGeomSource == 'ln':
            sql = "DELETE FROM lines WHERE interview_id = %d " % self.interview_id
            sql += "AND section_id = %d;" % self.section_id
        elif oldGeomSource == 'pl':
            sql = "DELETE FROM polygons WHERE interview_id = %d " % self.interview_id
            sql += "AND section_id = %d;" % self.section_id
        self.cur.execute(sql)
        self.conn.commit()

    #
    # copy referenced map feature to a new section in response to user setting feature to be unique

    def copyReferencedFeature(self, referencedCode):

        # use debug track order of calls
        if self.editDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        sql = "SELECT geom_source FROM interview_sections "
        sql += "WHERE interview_id = %d and section_code = '%s' " % (self.interview_id, referencedCode)
        rs = self.cur.execute(sql)
        gs = rs.fetchall()[0][0]
        # copy feature
        if gs == 'pt':
            # get geometry from referenced section
            sql = "SELECT id FROM points WHERE "
            sql += "interview_id = %d AND section_code = '%s' " % (self.interview_id, referencedCode)
            rs = self.cur.execute(sql)
            selectedId = rs.fetchall()[0][0]
            self.points_layer.select(selectedId)
            oldFeat = self.points_layer.selectedFeatures()[0]
            # create new id
            self.point_id = self.previousPointId + 1
            self.previousPointId = self.point_id
            # insert into database
            sql = "INSERT INTO points "
            sql += "(id,interview_id,section_id,section_code,date_created,date_modified,geom) "
            sql += "VALUES (%d,%d,%d, " % (self.point_id, self.interview_id, self.section_id)
            sql += "'%s','%s','%s'," %  (self.currentSectionCode,self.section_date_created, self.section_date_modified)
            sql += "GeomFromText('%s',3857));" % oldFeat.geometry().exportToWkt()
            self.cur.execute(sql)
            currentGeomSource = 'pt'
        elif gs == 'ln':
            # get geometry from referenced section
            sql = "SELECT id FROM lines WHERE "
            sql += "interview_id = %d AND section_code = '%s' " % (self.interview_id, referencedCode)
            rs = self.cur.execute(sql)
            selectedId = rs.fetchall()[0][0]
            self.lines_layer.select(selectedId)
            oldFeat = self.lines_layer.selectedFeatures()[0]
            # create new id
            self.line_id = self.previousLineId + 1
            self.previousLineId = self.line_id
            # insert into database
            sql = "INSERT INTO lines "
            sql += "(id,interview_id,section_id,section_code,date_created,date_modified,geom) "
            sql += "VALUES (%d,%d,%d, " % (self.line_id, self.interview_id, self.section_id)
            sql += "'%s','%s','%s'," %  (self.currentSectionCode,self.section_date_created, self.section_date_modified)
            sql += "GeomFromText('%s',3857));" % oldFeat.geometry().exportToWkt()
            self.cur.execute(sql)
            currentGeomSource = 'ln'
        elif gs == 'pl':
            # get geometry from referenced section
            sql = "SELECT id FROM polygons WHERE "
            sql += "interview_id = %d AND section_code = '%s' " % (self.interview_id, referencedCode)
            rs = self.cur.execute(sql)
            selectedId = rs.fetchall()[0][0]
            self.polygons_layer.select(selectedId)
            oldFeat = self.polygons_layer.selectedFeatures()[0]
            # create new id
            self.polygon_id = self.previousPolygonId + 1
            self.previousPolygonId = self.polygon_id
            # insert into database
            sql = "INSERT INTO polygons "
            sql += "(id,interview_id,section_id,section_code,date_created,date_modified,geom) "
            sql += "VALUES (%d,%d,%d, " % (self.polygon_id, self.interview_id, self.section_id)
            sql += "'%s','%s','%s'," %  (self.currentSectionCode,self.section_date_created, self.section_date_modified)
            sql += "GeomFromText('%s',3857));" % oldFeat.geometry().exportToWkt()
            self.cur.execute(sql)
            currentGeomSource = 'pl'
        self.currentFeature = currentGeomSource
        self.conn.commit()
        return(currentGeomSource)

    #
    # save section - this is somewhat complex because of many options detailed in comments below
    
    def saveSectionEdits(self):

        # use debug track order of calls
        if self.editDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # change interface to reflect completion of editing
        self.disableSectionSaveCancel()
        # set codes for SQL
        contentCode = self.leCode.text()
        sectionCode = '%s%04d' % (contentCode,self.currentCodeNumber)
        currentGeomSource = self.currentFeature
        sql = "SELECT geom_source FROM interview_sections "
        sql += "WHERE interview_id = %d and section_code = '%s' " % (self.interview_id, self.currentSectionCode)
        rs = self.cur.execute(sql)
        oldGeomSource = rs.fetchall()[0][0]
        # set spatial flags
        editVector = False
        deselectOld = False
        selectNew = False
        # process spatial changes first
        #
        # case 1 - saving vector edits
        if self.vectorEditing == True:
            deselectOld = True
            selectNew = True
            self.updateMapFeature()
            if self.featureState == 'Add Spatial':
                self.cbFeatureStatus.addItem('same as %s' % self.currentSectionCode)
        #
        # case 2 - spatial to non-spatial
        elif oldGeomSource in ('pt','ln','pl') and self.cbFeatureStatus.currentIndex() == 0:
            # check if it is referenced
            sql = "SELECT count(*) FROM interview_sections "
            sql += "WHERE interview_id = %d AND geom_source = '%s' " % (self.interview_id, self.currentSectionCode)
            rs = self.cur.execute(sql)
            refCount = rs.fetchall()[0][0]
            if refCount > 0:
                mText = "The spatial details of this section are referenced by other sections. "
                mText += "You can not delete its geometry."
                QtGui.QMessageBox.warning(self, 'User Error',
                        mText, QtGui.QMessageBox.Ok)
                return
            questionText = "You have selected to remove the spatial feature associated with %s. " % self.currentSectionCode
            questionText += "Are you sure you want to do this?"
            response = QtGui.QMessageBox.information(self, 'Deleting spatial feature',
                        questionText, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if response == QtGui.QMessageBox.Yes:
                deselectOld = True
                selectNew = True
                self.deleteMapFeature(oldGeomSource)
                currentGeomSource = 'ns'
                self.currentFeature = 'ns'
                idx = self.cbFeatureStatus.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
                if idx > -1:
                    self.cbFeatureStatus.removeItem(idx)
            else:
                return
        #
        # case 3 - spatial to link
        elif oldGeomSource in ('pt','ln','pl') and self.cbFeatureStatus.currentIndex() > 1:
            # check if it is referenced
            sql = "SELECT count(*) FROM interview_sections "
            sql += "WHERE interview_id = %d AND geom_source = '%s' " % (self.interview_id, self.currentSectionCode)
            rs = self.cur.execute(sql)
            refCount = rs.fetchall()[0][0]
            if refCount > 0:
                mText = "The spatial details of this section are referenced by other sections. "
                mText += "You can not delete its geometry."
                QtGui.QMessageBox.warning(self, 'User Error',
                        mText, QtGui.QMessageBox.Ok)
                return
            referencedCode = self.cbFeatureStatus.currentText()[8:]
            questionText = "You have selected to remove the spatial feature associated with %s " % self.currentSectionCode
            questionText += "and reference %s instead. Are you sure you want to do this?" % referencedCode
            response = QtGui.QMessageBox.information(self, 'Deleting spatial feature',
                        questionText, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if response == QtGui.QMessageBox.Yes:
                deselectOld = True
                selectNew = True
                self.deleteMapFeature(oldGeomSource)
                currentGeomSource = referencedCode
                self.currentFeature = 'rf'
                idx = self.cbFeatureStatus.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
                if idx > -1:
                    self.cbFeatureStatus.removeItem(idx)
            else:
                return
        #
        # case 4 - non-spatial to link
        elif oldGeomSource == 'ns' and self.cbFeatureStatus.currentIndex() > 1:
            deselectOld = True
            selectNew = True
            referencedCode = self.cbFeatureStatus.currentText()[8:]
            currentGeomSource = referencedCode
        #
        # case 5 - linked to non-spatial
        elif not oldGeomSource in ('pt','ln','pl','ns') and self.cbFeatureStatus.currentIndex() == 0:
            deselectOld = True
            currentGeomSource = 'ns'
            self.currentFeature = 'ns'          
        #
        # case 6 - link to different link
        elif not oldGeomSource in ('pt','ln','pl','ns') and self.cbFeatureStatus.currentIndex() > 1:
            deselectOld = True
            selectNew = True
            referencedCode = self.cbFeatureStatus.currentText()[8:]
            currentGeomSource = referencedCode
        #
        # case 7 - link to spatial
        elif not oldGeomSource in ('pt','ln','pl','ns') and self.cbFeatureStatus.currentIndex() == 1:
            referencedCode = oldGeomSource
            questionText = 'You have set this feature as unique and separate from the previously referenced section %s.' % referencedCode
            questionText += 'The geometry from %s will be copied to this section for editing. ' % referencedCode
            questionText += 'Are you sure you want to do this?'
            response = QtGui.QMessageBox.information(self, 'Spatial Feature Changed',
                questionText, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if response == QtGui.QMessageBox.No:
                return
            else:
                # may not be good idea here
                self.featureState = 'Add Spatial'
                currentGeomSource = self.copyReferencedFeature(referencedCode)
                editVector = True
        # process core record changes second
        # 
        # check for changes to section code
        if sectionCode <>  self.currentSectionCode:
            # update section list
            self.previousContentCode = contentCode
            self.updateSectionCode(sectionCode)
            lstIdx = self.cbFeatureStatus.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
            if lstIdx <> -1:
                self.cbFeatureStatus.setItemText(lstIdx, 'same as %s' % sectionCode)
            self.lwSectionList.currentItem().setText(sectionCode)
        # now check for changes to media start and end times
        media_start_time = self.seconds2timeString(self.spMediaStart.value())
        media_end_time = self.seconds2timeString(self.spMediaEnd.value())
        # if start times have changed update preceding setion if it exists
        if self.audioStartPosition <> self.spMediaStart.value() and \
        self.lwSectionList.currentRow() <> 0:
            # determine precending section
            precendingSectionCode = self.lwSectionList.item(self.lwSectionList.currentRow()-1).text()
            sql = "UPDATE interview_sections "
            sql += 'SET media_end_time = "%s" ' % media_start_time
            sql += "WHERE interview_id = %d AND section_code = '%s' " % (self.interview_id, precendingSectionCode)
            self.cur.execute(sql)
            self.audioStartPosition = self.timeString2seconds(media_start_time)
            self.hsSectionMedia.setMinimum(self.audioStartPosition)
            self.hsSectionMedia.setValue(self.audioStartPosition)
        # if end times have changed changed the following section if it exists
        if self.audioEndPosition <> self.spMediaEnd.value() and \
        self.lwSectionList.currentRow() < self.lwSectionList.count()-1:
            followingSectionCode = self.lwSectionList.item(self.lwSectionList.currentRow()+1).text()
            sql = "UPDATE interview_sections "
            sql += 'SET media_start_time = "%s" ' % media_end_time
            sql += "WHERE interview_id = %d AND section_code = '%s' " % (self.interview_id, followingSectionCode)
            self.cur.execute(sql)
            self.audioEndPosition = self.timeString2seconds(media_end_time)
            self.hsSectionMedia.setMaximum(self.audioEndPosition)
            self.hsSectionMedia.setValue(self.audioStartPosition)
        # update section table
        self.previousSecurity = self.default_security[self.cbSectionSecurity.currentIndex()]
        self.previousTags = self.pteTags.document().toPlainText()
        self.previousUsePeriod = self.default_time_periods[self.cbTimePeriod.currentIndex()]
        self.previousAnnualVariation = self.default_annual_variation[self.cbAnnualVariation.currentIndex()]
        self.previousNote = self.pteSectionNote.document().toPlainText().replace("'","''")
        self.previousText = self.pteSectionText.document().toPlainText().replace("'","''")
        self.section_date_modified = datetime.datetime.now().isoformat()[:10]
        sql = 'UPDATE interview_sections SET '
        sql += "content_code = '%s', " % contentCode
        sql += "section_code = '%s', " % sectionCode
        sql += "data_security = '%s', " % self.previousSecurity
        sql += "geom_source = '%s', " % currentGeomSource
        sql += "tags = '%s', " % self.previousTags
        sql += "use_period = '%s', " % self.previousUsePeriod
        sql += "annual_variation = '%s', " % self.previousAnnualVariation
        sql += "note = '%s', " % self.previousNote
        sql += "section_text = '%s', " % self.previousText
        sql += "media_start_time = '%s', " % media_start_time
        sql += "media_end_time = '%s', " % media_end_time
        sql += "date_modified = '%s' " % self.section_date_modified
        sql += "WHERE id = %s " % self.section_id
        self.cur.execute(sql)
        self.conn.commit()
        # repaint if changes to section code
        if sectionCode <>  self.currentSectionCode:
            self.currentSectionCode = sectionCode
            if self.currentFeature == 'pt':
                self.points_layer.triggerRepaint()
            elif self.currentFeature == 'ln':
                self.lines_layer.triggerRepaint()
            else:
                self.polygons_layer.triggerRepaint()
        # activate spatial edit or refresh if needed
        if selectNew == True:
            self.selectFeature()
        elif deselectOld == True:
            # this is an else statement because the selectFeature method deselects old features
            self.points_layer.deselect(self.points_layer.selectedFeaturesIds())
            self.lines_layer.deselect(self.lines_layer.selectedFeaturesIds())
            self.polygons_layer.deselect(self.polygons_layer.selectedFeaturesIds())
        if editVector == True:
            self.activateSpatialEdit()
            
    #
    # cancel edits to section

    def cancelSectionEdits(self):

        # use debug track order of calls
        if self.editDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself() + self.featureState, QtGui.QMessageBox.Ok)
        # method body
        # cancel edits in a variety of spatial cases
        if self.featureState == 'Add Spatial':
            # if feature copied, delete it and reset to non-spatial
            sql = "DELETE FROM points WHERE "
            sql += "interview_id = %d AND section_code = '%s';" % (self.interview_id, self.currentSectionCode)
            self.cur.execute(sql)
            sql = "DELETE FROM lines WHERE "
            sql += "interview_id = %d AND section_code = '%s';" % (self.interview_id, self.currentSectionCode)
            self.cur.execute(sql)
            sql = "DELETE FROM polygons WHERE "
            sql += "interview_id = %d AND section_code = '%s';" % (self.interview_id, self.currentSectionCode)
            self.cur.execute(sql)
            sql = "UPDATE interview_sections "
            sql += "SET geom_source = 'ns' "
            sql += "WHERE interview_id = %d AND section_code = '%s'" % (self.interview_id, self.currentSectionCode)
            self.cur.execute(sql)
            self.conn.commit()
            if self.editLayer <> None:
                self.editLayer.commitChanges()
                QgsMapLayerRegistry.instance().removeMapLayer(self.editLayer.id())
            self.points_layer.deselect(self.points_layer.selectedFeaturesIds())
            self.lines_layer.deselect(self.lines_layer.selectedFeaturesIds())
            self.polygons_layer.deselect(self.polygons_layer.selectedFeaturesIds())
            self.cbFeatureStatus.setCurrentIndex(0)
            self.vectorEditing = False
            # no need to reload as other changes already saved
        elif self.vectorEditing == True:
            # if vector edting, abandon changes
            self.vectorEditing = False
            self.editLayer.commitChanges()
            QgsMapLayerRegistry.instance().removeMapLayer(self.editLayer.id())
            # reload as other changes not saved too
            self.loadSectionRecord()
        else:
            # no spatial changes so just reload the record
            self.loadSectionRecord()
        # reset state, tools and widgets
        self.featureState = 'View'
        self.activatePanTool()
        self.disableSectionSaveCancel()
        
    #
    # delete section

    def deleteSection(self):

        # use debug track order of calls
        if self.editDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # prevent deletion if this section is referenced by another section
        sql = "SELECT count(*) FROM interview_sections "
        sql += "WHERE interview_id = %d AND geom_source = '%s' " % (self.interview_id, self.currentSectionCode)
        rs = self.cur.execute(sql)
        refCount = rs.fetchall()[0][0]
        if refCount > 0:
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
            # check if spatial and remove for spatial feature reference combobox
            idx = self.cbFeatureStatus.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
            if idx > -1:
                self.cbFeatureStatus.removeItem(idx)
            # check if last section as adjust time index of precending section if needed
            if self.lwSectionList.currentRow()+1 == self.lwSectionList.count():
                pIdx = self.lwSectionList.currentRow()-1
                pSCode = self.lwSectionList.item(pIdx).text()
                sql = "UPDATE interview_sections "
                sql += "SET media_end_time = '%s' " % self.seconds2timeString(self.spMediaEnd.value())
                sql += "WHERE interview_id = %d and section_code = '%s'" % (self.interview_id, pSCode)
                self.cur.execute(sql)
            if self.currentFeature == 'pt':
                sql = "DELETE FROM points WHERE "
                sql += "interview_id = %d and section_id = %d" % (self.interview_id, self.section_id)
                self.cur.execute(sql)
                #self.conn.commit()
            elif self.currentFeature == 'ln':
                sql = "DELETE FROM lines WHERE "
                sql += "interview_id = %d and section_id = %d" % (self.interview_id, self.section_id)
                self.cur.execute(sql)
                #self.conn.commit()
            elif self.currentFeature == 'pl':
                sql = "DELETE FROM polygons WHERE "
                sql += "interview_id = %d and section_id = %d" % (self.interview_id, self.section_id)
                self.cur.execute(sql)
                #self.conn.commit()
            sql = "DELETE FROM interview_sections WHERE "
            sql += "id = %d" % self.section_id
            self.cur.execute(sql)
            self.conn.commit()
            # remove from section list
            self.lwSectionList.takeItem(self.lwSectionList.currentRow())
        # reset interface
        self.disableSectionSaveCancel()
        # refresh view
        if self.currentFeature == 'pt':
            self.points_layer.setCacheImage(None)
            self.points_layer.triggerRepaint()
        elif self.currentFeature == 'ln':
            self.lines_layer.setCacheImage(None)
            self.lines_layer.triggerRepaint()
        elif self.currentFeature == 'pl':
            self.polygons_layer.setCacheImage(None)
            self.polygons_layer.triggerRepaint()
        # cancel spatial edits if delete clicked during editing
        if self.vectorEditing == True:
            # reset flag
            self.vectorEditing = False
            # remove layer
            self.editLayer.commitChanges()
            QgsMapLayerRegistry.instance().removeMapLayer(self.editLayer.id())
            self.activatePanTool()
        

    #####################################################
    #           section selection and loading           #
    #####################################################

    #
    # select feature

    def selectFeature(self):

        # check for keyboard modifier
        modifiers = QtGui.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.ShiftModifier:
            self.shiftKey = True
        else:
            self.shiftKey = False
        # determine nature of current feature and select
        if self.lwSectionList.currentItem() <> None and self.interviewState == 'View':
            if self.mediaState == 'playing':
                self.playPauseMedia()
            # use debug track order of calls
            if self.editDebug:
                if self.debugFile == True:
                    self.df.write('\n--Select Feature--\n')
                    self.df.write(self.myself()+ '\n')
                else:
                    QtGui.QMessageBox.warning(self, 'DEBUG',
                        self.myself(), QtGui.QMessageBox.Ok)
            self.featureState = 'Select'
            # deselect other features
            self.points_layer.deselect(self.points_layer.selectedFeaturesIds())
            self.lines_layer.deselect(self.lines_layer.selectedFeaturesIds())
            self.polygons_layer.deselect(self.polygons_layer.selectedFeaturesIds())
            # proceed
            self.geomSourceAction = 'no change'
            self.currentSectionCode = self.lwSectionList.currentItem().text()
            self.currentCodeNumber = int(re.sub(r'[\D+]','',self.currentSectionCode))
            # get the section data
            sql = "SELECT id, sequence_number, content_code, data_security, "
            sql += "geom_source, tags, use_period, annual_variation, note, "
            sql += "media_start_time, media_end_time, section_text "
            sql += "FROM interview_sections WHERE "
            sql += "interview_id = %d AND section_code = '%s';" % (self.interview_id, self.currentSectionCode)
            rs = self.cur.execute(sql)
            self.sectionData = rs.fetchall()
            self.section_id = self.sectionData[0][0]
            self.section_date_created = datetime.datetime.now().isoformat()[:10]
            self.section_date_modified = self.section_date_created 
            featureType = self.sectionData[0][4]
            # allow for selecting another section
            selectedCode = self.currentSectionCode
            self.featureState = 'Load'
            self.loadSectionRecord()
            self.featureState = 'View'
            # check if non-spatial
            if featureType == 'ns':
                self.currentFeature = 'ns'
            else:
                # select spatial feaure
                if not featureType in ('pt','ln','pl'):
                    # grab id for referenced feature
                    self.currentFeature = 'rf'
                    # get attributes of referenced feature from a different section
                    selectedCode = featureType
                    sql = "SELECT id, geom_source FROM interview_sections WHERE "
                    sql += "interview_id = %d AND section_code = '%s';" % (self.interview_id, selectedCode)
                    rs = self.cur.execute(sql)
                    idData = rs.fetchall()
                    selectedId = idData[0][0]
                    featureType = idData[0][1]
                else:
                    # set current feature variable for sections with their own spatial features
                    self.currentFeature = featureType
                # select feature connected to this section
                if featureType == 'pt':
                    sql = "SELECT id FROM points WHERE "
                    sql += "interview_id = %d AND section_code = '%s';" % (self.interview_id, selectedCode)
                    rs = self.cur.execute(sql)
                    idData = rs.fetchall()
                    if len(idData) > 0:
                        self.point_id = idData[0][0]
                        self.points_layer.select(self.point_id)
                        if self.shiftKey == True:
                            bbox = self.points_layer.boundingBoxOfSelected()
                            self.canvas.setExtent(bbox)
                            self.canvas.refresh()
                    else:
                        self.currentFeature = 'ns'
                elif featureType == 'ln':
                    sql = "SELECT id FROM lines WHERE "
                    sql += "interview_id = %d AND section_code = '%s';" % (self.interview_id, selectedCode)
                    rs = self.cur.execute(sql)
                    idData = rs.fetchall()
                    if len(idData) > 0:
                        self.line_id = idData[0][0]
                        self.lines_layer.select(self.line_id)
                        if self.shiftKey == True:
                            bbox = self.lines_layer.boundingBoxOfSelected()
                            self.canvas.setExtent(bbox)
                            self.canvas.refresh()
                    else:
                        self.currentFeature = 'ns'
                elif featureType == 'pl':
                    sql = "SELECT id FROM polygons WHERE "
                    sql += "interview_id = %d AND section_code = '%s';" % (self.interview_id, selectedCode)
                    rs = self.cur.execute(sql)
                    idData = rs.fetchall()
                    if len(idData) > 0:
                        self.polygon_id = idData[0][0]
                        self.polygons_layer.select(self.polygon_id)
                        if self.shiftKey == True:
                            bbox = self.polygons_layer.boundingBoxOfSelected()
                            self.canvas.setExtent(bbox)
                            self.canvas.refresh()
                    else:
                        self.currentFeature = 'ns'
            if self.currentFeature == 'ns' and self.shiftKey:
                if self.boundaryLayer <> None:
                    self.canvas.setExtent(self.boundaryLayer.extent())
                else:
                    self.canvas.zoomToFullExtent()
            self.pbDeleteSection.setEnabled(True)
            self.featureState = 'View'
            # enable spatial editing if section has spatial feature
            if self.currentFeature in ('pt','ln','pl'):
                self.tbEdit.setEnabled(True)
                self.tbMove.setEnabled(True)
            else:
                # disable spatial editing if no feature or referenced feature
                self.tbEdit.setDisabled(True)
                self.tbMove.setDisabled(True)

    #
    # load section record

    def loadSectionRecord(self):

        # use debug track order of calls
        if self.editDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        if self.sectionData == None or self.sectionData[0][0] <> self.section_id:
            # grab section record
            sql = "SELECT id, sequence_number, content_code, data_security, "
            sql += "geom_source, tags, use_period, annual_variation, note, "
            sql += "media_start_time, media_end_time, section_text "
            sql += "FROM interview_sections WHERE "
            sql += "interview_id = %d AND section_code = '%s';" % (self.interview_id, self.currentSectionCode)
            rs = self.cur.execute(sql)
            self.sectionData = rs.fetchall()
        # update section edit controls
        # set time info
        self.audioStartPosition = self.timeString2seconds(self.sectionData[0][9])
        self.audioEndPosition = self.timeString2seconds(self.sectionData[0][10])
        self.audioCurrentPosition = self.audioStartPosition
        self.spMediaStart.setValue(self.audioStartPosition)
        self.spMediaEnd.setValue(self.audioEndPosition)
        self.hsSectionMedia.setMinimum(self.audioStartPosition)
        self.hsSectionMedia.setMaximum(self.audioEndPosition)
        self.hsSectionMedia.setValue(self.audioStartPosition)
        # sequence value
        self.currentSequence = self.sectionData[0][1]
        # other fields
        self.leCode.setText(self.sectionData[0][2])
        self.cbSectionSecurity.setCurrentIndex(self.default_security.index(self.sectionData[0][3]))
        geomSource = self.sectionData[0][4]
        if geomSource in ('pt','ln','pl'):
            self.cbFeatureStatus.setCurrentIndex(1)
        elif geomSource == 'ns':
            self.cbFeatureStatus.setCurrentIndex(0)
        else:
            # find matching section code
            idx = self.cbFeatureStatus.findText(geomSource, QtCore.Qt.MatchEndsWith)
            if idx <> 0 and idx < self.cbFeatureStatus.count():
                self.cbFeatureStatus.setCurrentIndex(idx)
            else:
                self.cbFeatureStatus.setCurrentIndex(0)
        self.pteTags.setPlainText(self.sectionData[0][5])
        self.cbTimePeriod.setCurrentIndex(self.default_time_periods.index(self.sectionData[0][6]))
        self.cbAnnualVariation.setCurrentIndex(self.default_annual_variation.index(self.sectionData[0][7]))
        self.pteSectionNote.setPlainText(self.sectionData[0][8])
        # deselect items
        for i in range(self.lwProjectCodes.count()):
            item = self.lwProjectCodes.item(i)
            self.lwProjectCodes.setItemSelected(item,False)
        # select items
        tagList = self.sectionData[0][5].split(',')
        for tag in tagList:
            self.lwProjectCodes.setItemSelected(self.lwProjectCodes.findItems(tag,QtCore.Qt.MatchExactly)[0], True)
        # set text
        self.pteSectionText.setPlainText(self.sectionData[0][11])
            
    #
    # time string to seconds

    def timeString2seconds(self, timeString):
        ftr = [3600,60,1]
        seconds = sum([a*b for a,b in zip(ftr, map(int,timeString.split(':')))])
        return(seconds)
        
    #
    # seconds to time string

    def seconds2timeString(self, seconds):
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
    # update section code in spatial layer when the section code changes

    def updateSectionCode(self, sectionCode):
        
        # use debug track order of calls
        if self.editDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # update spatial table if section is spatial
        if self.currentFeature == 'pt':
            sql = "UPDATE points SET "
            sql += "section_code = '%s' " % sectionCode
            sql += "WHERE section_id = %d;" % self.section_id
        elif self.currentFeature == 'ln':
            sql = "UPDATE lines SET "
            sql += "section_code = '%s' " % sectionCode
            sql += "WHERE section_id = %d;" % self.section_id
        elif self.currentFeature == 'pl':
            sql = "UPDATE polygons SET "
            sql += "section_code = '%s' " % sectionCode
            sql += "WHERE section_id = %d;" % self.section_id
        else:
            sql = ''
        if self.currentFeature in ('pt','ln','pl'):
            self.cur.execute(sql)
        # update references to section code
        sql = "UPDATE interview_sections "
        sql += "SET geom_source = '%s' " % sectionCode
        sql += "WHERE interview_id = %d AND geom_source = '%s';" % (self.interview_id, self.currentSectionCode)
        self.cur.execute(sql)

    #
    # feature status changed

    def featureStatusChanged(self):

        # need to make changes here
        if self.featureState in ('View','Edit'):
            if self.currentFeature == 'ns' and self.cbFeatureStatus.currentIndex() == 1:
                # was non-spatial and user choose to make it spatial switch to point tool
                # because use can change to line or polygon tool if needed
                self.featureState = 'Add Spatial'
                self.activatePointCapture()
            elif self.cbFeatureStatus.currentIndex() > 1:
                # check that a section is not self referencing
                referencedCode = self.cbFeatureStatus.currentText()[8:]
                if referencedCode == self.currentSectionCode:
                    QtGui.QMessageBox.warning(self, 'User Error',
                        'A section can not reference itself', QtGui.QMessageBox.Ok)
                    if self.sectionData[0][4] in ('pt','ln','pl'):
                        self.cbFeatureStatus.setCurrentIndex(1)
                    else:
                        self.cbFeatureStatus.setCurrentIndex(0)
                self.enableSectionSaveCancel()
            else:
                # enable saving or cancelling in response to editing
                self.enableSectionSaveCancel()

    #
    # add / remove tags to sections
        
    def addRemoveSectionTags(self):

        modifiers = QtGui.QApplication.keyboardModifiers()
        # use debug track order of calls
        if self.editDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself() + ': ' + self.featureState, QtGui.QMessageBox.Ok)
        # method body
        # only act if editing or viewing, not loading
        if self.featureState in ('View','Edit'):
            # grab modifier key
            ctrlKey = False
            if modifiers == QtCore.Qt.ControlModifier:
                ctrlKey = True
            # determine what items are selected
            selectedItems = self.lwProjectCodes.selectedItems()
            # if adding items
            if self.selectedCodeCount < len(selectedItems):
                # set content code if ctrl key is held down and adding the item
                if ctrlKey == True:
                    self.leCode.setText(self.lwProjectCodes.currentItem().text())
            # if removing items
            else:
                # check if content code has been deselected and if so reselect it
                deselected = True
                for item in selectedItems:
                    if item.text() == self.leCode.text():
                        deselected = False
                if deselected:
                    itemList = self.lwProjectCodes.findItems(self.leCode.text(),QtCore.Qt.MatchExactly)
                    self.lwProjectCodes.setItemSelected(itemList[0],True)
                    selectedItems = self.lwProjectCodes.selectedItems()
            self.selectedCodeCount = len(selectedItems)
            tagList = []
            sectionTags = ''
            for item in selectedItems:
                tagList.append(item.text())
            tagList.sort()
            for tag in tagList:
                sectionTags += tag + ','
            self.pteTags.setPlainText(sectionTags[:-1])
            # check if content code has been deselected and if so reselect it
            itemList = self.lwProjectCodes.findItems(self.leCode.text(),QtCore.Qt.MatchExactly)
            self.lwProjectCodes.setItemSelected(itemList[0],True)
            # enable save or cancel
            self.enableSectionSaveCancel()


    #####################################################
    #                   map tools                       #
    #####################################################

    #
    # activate pan tool

    def activatePanTool(self):

        # use debug track order of calls
        if self.spatialDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        self.canvas.setMapTool(self.panTool)
        self.tbPan.setChecked(True)

        self.tbPoint.setChecked(False)
        self.tbLine.setChecked(False)
        self.tbPolygon.setChecked(False)
        self.tbEdit.setChecked(False)
        self.tbMove.setChecked(False)

    #
    # activate point capture tool

    def activatePointCapture(self):

        # disable everything option but placing item or cancelling
        self.enableSectionCancel()
        # use debug track order of calls
        if self.spatialDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        self.currentFeature = 'pt'
        # select the layer and tool
        self.iface.legendInterface().setCurrentLayer(self.points_layer)
        self.canvas.setMapTool(self.pointTool)
        self.tbPoint.setChecked(True)
        self.tbPoint.setEnabled(True)
        self.tbLine.setEnabled(True)
        self.tbPolygon.setEnabled(True)
        # disable editing
        self.tbEdit.setDisabled(True)
        self.tbMove.setDisabled(True)
        # adjust visibility and state of other tools
        self.tbLine.setChecked(False)
        self.tbPolygon.setChecked(False)
        self.tbEdit.setChecked(False)
        self.tbMove.setChecked(False)
        self.tbPan.setChecked(False)

    #
    # activate line tool

    def activateLineCapture(self):

        # disable everything option but placing item or cancelling
        self.enableSectionCancel()
        # use debug track order of calls
        if self.spatialDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        self.currentFeature = 'ln'
        # select the layer and tool
        self.iface.legendInterface().setCurrentLayer(self.lines_layer)
        self.canvas.setMapTool(self.lineTool)
        self.tbLine.setChecked(True)
        # disable editing
        self.tbEdit.setDisabled(True)
        self.tbMove.setDisabled(True)
        # adjust visibility and state of other tools
        self.tbPolygon.setChecked(False)
        self.tbPoint.setChecked(False)
        self.tbEdit.setChecked(False)
        self.tbMove.setChecked(False)
        self.tbPan.setChecked(False)
        
    #
    # activate polygon tool

    def activatePolygonCapture(self):

        # disable everything option but placing item or cancelling
        self.enableSectionCancel()
        # use debug track order of calls
        if self.spatialDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        self.currentFeature = 'pl'
        # select the layer and tool
        self.iface.legendInterface().setCurrentLayer(self.polygons_layer)
        self.canvas.setMapTool(self.polygonTool)
        self.tbPolygon.setChecked(True)
        # disable editing
        self.tbEdit.setDisabled(True)
        self.tbMove.setDisabled(True)
        # adjust visibility and state of other tools
        self.tbLine.setChecked(False)
        self.tbPoint.setChecked(False)
        self.tbEdit.setChecked(False)
        self.tbMove.setChecked(False)
        self.tbPan.setChecked(False)

    #
    # activate spatial edit by creating copy of feature and activating the node tool

    def activateSpatialEdit( self ):

        # use debug track order of calls
        if self.spatialDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # set buttons
        self.tbEdit.setChecked(True)
        self.tbMove.setChecked(False)
        self.tbPolygon.setChecked(False)
        self.tbPoint.setChecked(False)
        self.tbLine.setChecked(False)
        self.tbPan.setChecked(False)
        # disable everything option but saving or cancelling
        self.enableSectionCancel(True)

        if self.nodeButton == None:
            QtGui.QMessageBox.warning(self, 'QGIS Error',
                'The Node Tool could not be found. Can not edit feature.', QtGui.QMessageBox.Ok)
            return(-1)
        if self.vectorEditing == False:
            # create memory layer
            if self.currentFeature == 'pt':
                uri = "MultiPoint?crs=epsg:3857"
                self.editLayer = QgsVectorLayer(uri, 'Edit Point', 'memory')
                feat = self.points_layer.selectedFeatures()[0]
                # set display parameters
                symbol = self.editLayer.rendererV2().symbols()[0]
                symbol.setSize(3)
                symbol.setColor(QtGui.QColor('#ff0000'))
                symbol.setAlpha(0.5)
            elif self.currentFeature == 'ln':
                uri = "MultiLineString?crs=epsg:3857"
                self.editLayer = QgsVectorLayer(uri, 'Edit Line', 'memory')
                feat = self.lines_layer.selectedFeatures()[0]
                # set display parameters
                symbol = self.editLayer.rendererV2().symbol()
                symbol.setColor(QtGui.QColor('#ff0000'))
                symbol.setWidth(1)
            elif self.currentFeature == 'pl':
                uri = "MultiPolygon?crs=epsg:3857"
                self.editLayer = QgsVectorLayer(uri, 'Edit Polygon', 'memory')
                feat = self.polygons_layer.selectedFeatures()[0]
                # set display parameters
                self.editLayer.rendererV2().symbol().setAlpha(0.5)
                symbolLayer = self.editLayer.rendererV2().symbol().symbolLayer(0)
                symbolLayer.setFillColor(QtGui.QColor('#ff8080'))
                symbolLayer.setBorderColor(QtGui.QColor('#ff0000'))
                symbolLayer.setBorderWidth(1)
            else:
                QtGui.QMessageBox.warning(self, 'User Error',
                    'The selected section has no spatial data', QtGui.QMessageBox.Ok)
                return(-1)
            # copy feature to memory layer
            dataProvider = self.editLayer.dataProvider()
            dataProvider.addFeatures([feat])
            # register and select current layer
            QgsMapLayerRegistry.instance().addMapLayer(self.editLayer)
            self.iface.legendInterface().setCurrentLayer(self.editLayer)
            # make memory layer editable
            self.editLayer.startEditing()
            # set flag
            self.vectorEditing = True
        # activate node tool
        self.nodeButton.click()

        return(0)
        
    #
    # activate spatial move by creating copy of feature and activating the move tool

    def activateSpatialMove( self ):

        # use debug track order of calls
        if self.spatialDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # set buttons
        self.tbEdit.setChecked(False)
        self.tbMove.setChecked(True)
        self.tbPolygon.setChecked(False)
        self.tbPoint.setChecked(False)
        self.tbLine.setChecked(False)
        self.tbPan.setChecked(False)
        # disable everything option but saving or cancelling
        self.enableSectionCancel(True)
        
        if self.moveButton == None:
            QtGui.QMessageBox.warning(self, 'QGIS Error',
                'The Move Tool could not be found. Can not edit feature.', QtGui.QMessageBox.Ok)
            return(-1)
        if self.vectorEditing == False:
            # create memory layer
            if self.currentFeature == 'pt':
                uri = "MultiPoint?crs=epsg:3857"
                self.editLayer = QgsVectorLayer(uri, 'Edit Point', 'memory')
                feat = self.points_layer.selectedFeatures()[0]
                # set display parameters
                symbol = self.editLayer.rendererV2().symbols()[0]
                symbol.setSize(3)
                symbol.setColor(QtGui.QColor('#ff0000'))
                symbol.setAlpha(0.5)
            elif self.currentFeature == 'ln':
                uri = "MultiLineString?crs=epsg:3857"
                self.editLayer = QgsVectorLayer(uri, 'Edit Line', 'memory')
                feat = self.lines_layer.selectedFeatures()[0]
                # set display parameters
                symbol = self.editLayer.rendererV2().symbol()
                symbol.setColor(QtGui.QColor('#ff0000'))
                symbol.setWidth(1)
            elif self.currentFeature == 'pl':
                uri = "MultiPolygon?crs=epsg:3857"
                self.editLayer = QgsVectorLayer(uri, 'Edit Polygon', 'memory')
                feat = self.polygons_layer.selectedFeatures()[0]
                # set display parameters
                self.editLayer.rendererV2().symbol().setAlpha(0.5)
                symbolLayer = self.editLayer.rendererV2().symbol().symbolLayer(0)
                symbolLayer.setFillColor(QtGui.QColor('#ff8080'))
                symbolLayer.setBorderColor(QtGui.QColor('#ff0000'))
                symbolLayer.setBorderWidth(1)
            else:
                QtGui.QMessageBox.warning(self, 'User Error',
                    'The selected section has no spatial data', QtGui.QMessageBox.Ok)
                return(-1)
            # copy feature to memory layer
            dataProvider = self.editLayer.dataProvider()
            dataProvider.addFeatures([feat])
            # register and select current layer
            QgsMapLayerRegistry.instance().addMapLayer(self.editLayer)
            self.iface.legendInterface().setCurrentLayer(self.editLayer)
            # make memory layer editable
            self.editLayer.startEditing()
            # disable other tools and buttons
            self.enableSectionSaveCancel()
            # set flag
            self.vectorEditing = True
        # activate node tool
        self.moveButton.click()

        return(0)

    # 
    # place new point using custom point tool

    def placePoint(self, point):

        # use debug track order of calls
        if self.spatialDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # get next point id
        self.point_id = self.previousPointId + 1
        self.previousPointId = self.point_id
        point.convertToMultiType()
        # insert into database
        sql = "INSERT INTO points "
        sql += "(id,interview_id,section_id,section_code,date_created,date_modified,geom) "
        sql += "VALUES (%d,%d,%d, " % (self.point_id, self.interview_id, self.section_id)
        sql += "'%s','%s','%s'," %  (self.currentSectionCode,self.section_date_created, self.section_date_modified)
        sql += "GeomFromText('%s',3857));" % point.exportToWkt()
        self.cur.execute(sql)
        sql = "SELECT count(*) FROM interview_sections "
        sql += "WHERE interview_id = %d AND " % self.interview_id
        sql += "id = %d AND " %  self.section_id
        sql += "geom_source = 'pt'"
        rs = self.cur.execute(sql)
        cData = rs.fetchall()
        if cData[0][0] == 0:
            self.currentFeature = 'pt'
            sql = "UPDATE interview_sections "
            sql += "SET geom_source = '%s', " % self.currentFeature
            sql += "spatial_data_scale = '%s' " % str(int(self.canvas.scale()))
            sql += "WHERE interview_id = %d and id = %d " % (self.interview_id, self.section_id)
            self.cur.execute(sql)
            if self.cbFeatureStatus.currentIndex() <> 1: 
                self.cbFeatureStatus.setCurrentIndex(1)
        else:
            sql = "UPDATE interview_sections "
            sql += "SET spatial_data_scale = '%s' " % str(int(self.canvas.scale()))
            sql += "WHERE interview_id = %d and id = %d " % (self.interview_id, self.section_id)
            self.cur.execute(sql)
        # commit record
        self.conn.commit()
        idx = self.cbFeatureStatus.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
        if idx == -1:
            self.cbFeatureStatus.addItem('same as %s' % self.currentSectionCode)
        # reset state
        self.featureState = 'View'
        self.activatePanTool()
        self.points_layer.select(self.point_id)
        self.disableSectionSaveCancel()

    #
    # place new line using custom line tool
    
    def placeLine(self, line):

        # use debug track order of calls
        if self.spatialDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # get next line id
        self.line_id = self.previousLineId + 1
        self.previousLineId = self.line_id
        line.convertToMultiType()
        # insert into database
        sql = "INSERT INTO lines "
        sql += "(id,interview_id,section_id,section_code,date_created,date_modified,geom) "
        sql += "VALUES (%d,%d,%d, " % (self.line_id, self.interview_id, self.section_id)
        sql += "'%s','%s','%s'," %  (self.currentSectionCode,self.section_date_created, self.section_date_modified)
        sql += "GeomFromText('%s',3857));" % line.exportToWkt()
        self.cur.execute(sql)
        # make sure the feature types line up
        # in case tools where changed before a feature was placed
        sql = "SELECT count(*) FROM interview_sections "
        sql += "WHERE interview_id = %d AND " % self.interview_id
        sql += "id = %d AND " %  self.section_id
        sql += "geom_source = 'ln'"
        rs = self.cur.execute(sql)
        cData = rs.fetchall()
        if cData[0][0] == 0:
            self.currentFeature = 'ln'
            sql = "UPDATE interview_sections "
            sql += "SET geom_source = '%s', " % self.currentFeature
            sql += "spatial_data_scale = '%s' " % str(int(self.canvas.scale()))
            sql += "WHERE interview_id = %d and id = %d " % (self.interview_id, self.section_id)
            self.cur.execute(sql)
            if self.cbFeatureStatus.currentIndex() <> 1: 
                self.cbFeatureStatus.setCurrentIndex(1)
        else:
            sql = "UPDATE interview_sections "
            sql += "SET spatial_data_scale = '%s' " % str(int(self.canvas.scale()))
            sql += "WHERE interview_id = %d and id = %d " % (self.interview_id, self.section_id)
            self.cur.execute(sql)
        # commit record
        self.conn.commit()
        idx = self.cbFeatureStatus.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
        if idx == -1:
            self.cbFeatureStatus.addItem('same as %s' % self.currentSectionCode)
        # reset state
        self.featureState = 'View'
        self.activatePanTool()
        self.lines_layer.select(self.line_id)
        self.disableSectionSaveCancel()

    #
    # place new line using custom polygon tool
    
    def placePolygon(self, polygon):

        # use debug track order of calls
        if self.spatialDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # get next polygon id
        self.polygon_id = self.previousPolygonId + 1
        self.previousPolygonId = self.polygon_id
        polygon.convertToMultiType()
        # insert into database
        sql = "INSERT INTO polygons "
        sql += "(id,interview_id,section_id,section_code,date_created,date_modified,geom) "
        sql += "VALUES (%d,%d,%d, " % (self.polygon_id, self.interview_id, self.section_id)
        sql += "'%s','%s','%s'," %  (self.currentSectionCode,self.section_date_created, self.section_date_modified)
        sql += "GeomFromText('%s',3857));" % polygon.exportToWkt()
        self.cur.execute(sql)
        # make sure the feature types line up
        # in case tools where changed before a feature was placed
        sql = "SELECT count(*) FROM interview_sections "
        sql += "WHERE interview_id = %d AND " % self.interview_id
        sql += "id = %d AND " %  self.section_id
        sql += "geom_source = 'pl'"
        rs = self.cur.execute(sql)
        cData = rs.fetchall()
        if cData[0][0] == 0:
            self.currentFeature = 'pl'
            sql = "UPDATE interview_sections "
            sql += "SET geom_source = '%s', " % self.currentFeature
            sql += "spatial_data_scale = '%s' " % str(int(self.canvas.scale()))
            sql += "WHERE interview_id = %d and id = %d " % (self.interview_id, self.section_id)
            self.cur.execute(sql)
            if self.cbFeatureStatus.currentIndex() <> 1: 
                self.cbFeatureStatus.setCurrentIndex(1)
        else:
            sql = "UPDATE interview_sections "
            sql += "SET spatial_data_scale = '%s' " % str(int(self.canvas.scale()))
            sql += "WHERE interview_id = %d and id = %d " % (self.interview_id, self.section_id)
            self.cur.execute(sql)
        # commit record
        self.conn.commit()
        idx = self.cbFeatureStatus.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
        if idx == -1:
            self.cbFeatureStatus.addItem('same as %s' % self.currentSectionCode)
        # reset state
        self.featureState = 'View'
        self.activatePanTool()
        self.polygons_layer.select(self.polygon_id)
        self.disableSectionSaveCancel()

