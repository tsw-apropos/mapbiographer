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
import pyaudio
from ui_mapbio_transcriber import Ui_mapbioTranscriber
from mapbio_navigator import mapBiographerNavigator
from audio_recorder import audioRecorder
from audio_player import audioPlayer
from point_tool import lmbMapToolPoint
from line_tool import lmbMapToolLine
from polygon_tool import lmbMapToolPolygon
import inspect, re

class mapBiographerTranscriber(QtGui.QDockWidget, Ui_mapbioTranscriber):

    #####################################################
    #                   basic setup                     #
    #####################################################

    #
    # init method to define globals and make widget / method connections
    
    def __init__(self, iface):

        # debug setup
        self.basicDebug = False
        self.editDebug = False
        self.audioDebug = False
        self.spatialDebug = False
        self.debugLog= True
        if self.basicDebug or self.editDebug or self.audioDebug or self.spatialDebug:
            self.myself = lambda: inspect.stack()[1][3]
        if self.basicDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
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
        self.ovPanel = None
        self.lmbMode = 'Conduct Interview'
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
        self.recordAudio = False
        self.interview_length = '00:00'
        self.intTimeSegment = 0
        # audio 
        self.pyAI = None
        self.audioDeviceIndex = None
        self.audioDeviceName = None
        self.audioStartPosition = 0
        self.audioEndPosition = 0
        self.audioCurrentPosition = 0
        self.mediaState = 'paused'
        self.afName = ''
        self.bitDepth = 16
        self.samplingFrequency = 44100
        # vector editing
        self.vectorEditing = False
        self.geomSourceAction = 'no change'
        self.currentContentCode = ''
        self.editLayer = None
        self.previousSectionId = None
        self.previousPointId = None
        self.previousLineId = None
        self.previousPolygonId = None
        self.sectionData = None
        # special actions based on key states
        self.copyPrevious = False
        self.rapidCapture = False
        self.zoomToFeature = False
        # settings variables
        self.projectDir = '.'
        self.projectDB = ''
        self.qgsProject = ''
        self.qgsProjectLoading = True
        # add panel
        self.iface.mainWindow().addDockWidget(QtCore.Qt.RightDockWidgetArea, self)
        # panel functionality
        self.setFeatures(self.DockWidgetMovable | self.DockWidgetFloatable)
        #
        # signals and slots setup
        # connect map tools
        self.mapToolsConnect()
        # basic interface operation
        QtCore.QObject.connect(self.cbMode, QtCore.SIGNAL("currentIndexChanged(int)"), self.setLMBMode)
        QtCore.QObject.connect(self.pbClose, QtCore.SIGNAL("clicked()"), self.transcriberClose)
        QtCore.QObject.connect(self.cbInterviewSelection, QtCore.SIGNAL("currentIndexChanged(int)"), self.interviewUpdateInfo)
        # audio
        self.tbMediaPlay.setIcon(QtGui.QIcon(":/plugins/mapbiographer/media_play.png"))
        QtCore.QObject.connect(self.tbMediaPlay, QtCore.SIGNAL("clicked()"), self.audioPlayPause)
        self.tbAudioSettings.setMenu(QtGui.QMenu(self.tbAudioSettings))
        QtCore.QObject.connect(self.cbRecordAudio, QtCore.SIGNAL("currentIndexChanged(int)"), self.audioTest)
        # interview controls
        QtCore.QObject.connect(self.pbStart, QtCore.SIGNAL("clicked()"), self.interviewStart)
        QtCore.QObject.connect(self.pbPause, QtCore.SIGNAL("clicked()"), self.interviewPause)
        QtCore.QObject.connect(self.pbFinish, QtCore.SIGNAL("clicked()"), self.interviewFinish)
        # section controls
        # widgets
        QtCore.QObject.connect(self.lwSectionList, QtCore.SIGNAL("itemSelectionChanged()"), self.sectionSelect)
        QtCore.QObject.connect(self.spMediaStart, QtCore.SIGNAL("valueChanged(int)"), self.sectionEnableSaveCancel)
        QtCore.QObject.connect(self.spMediaEnd, QtCore.SIGNAL("valueChanged(int)"), self.sectionEnableSaveCancel)
        QtCore.QObject.connect(self.hsSectionMedia, QtCore.SIGNAL("valueChanged(int)"), self.audioUpdateCurrentPosition)
        QtCore.QObject.connect(self.cbSectionSecurity, QtCore.SIGNAL("currentIndexChanged(int)"), self.sectionEnableSaveCancel)
        QtCore.QObject.connect(self.cbFeatureStatus, QtCore.SIGNAL("currentIndexChanged(int)"), self.sectionFeatureStatusChanged)
        QtCore.QObject.connect(self.cbTimePeriod, QtCore.SIGNAL("currentIndexChanged(int)"), self.sectionEnableSaveCancel)
        QtCore.QObject.connect(self.cbAnnualVariation, QtCore.SIGNAL("currentIndexChanged(int)"), self.sectionEnableSaveCancel)
        QtCore.QObject.connect(self.pteSectionNote, QtCore.SIGNAL("textChanged()"), self.sectionEnableSaveCancel)
        QtCore.QObject.connect(self.pteSectionText, QtCore.SIGNAL("textChanged()"), self.sectionEnableSaveCancel)
        QtCore.QObject.connect(self.lwProjectCodes, QtCore.SIGNAL("itemClicked(QListWidgetItem*)"), self.sectionAddRemoveTags)
        # buttons
        QtCore.QObject.connect(self.pbSaveSection, QtCore.SIGNAL("clicked()"), self.sectionSaveEdits)
        QtCore.QObject.connect(self.pbCancelSection, QtCore.SIGNAL("clicked()"), self.sectionCancelEdits)
        QtCore.QObject.connect(self.pbDeleteSection, QtCore.SIGNAL("clicked()"), self.sectionDelete)
        #
        # map projections
        canvasCRS = self.canvas.mapSettings().destinationCrs()
        layerCRS = QgsCoordinateReferenceSystem(3857)
        self.xform = QgsCoordinateTransform(canvasCRS, layerCRS)
        # final prep for transcribing interviews
        # open project
        result = self.settingsRead()
        if result == 0:
            result = self.transcriberOpen()
            if result <> 0:
                QtGui.QMessageBox.information(self, 'message',
                'Missing Files. Please correct. Closing.', QtGui.QMessageBox.Ok)
                self.transcriberClose()
        else:
            QtGui.QMessageBox.information(self, 'message',
            'Map Biographer Settings Error. Please correct. Closing.', QtGui.QMessageBox.Ok)
            self.transcriberClose()
        #
        # set mode
        self.setLMBMode()

    #
    # set LMB mode - set mode and and visibility and initial status of controls

    def setLMBMode(self):

        if self.basicDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        if self.cbMode.currentText() == 'Import':
            self.lmbMode = 'Import'
            self.tbImportFeatures.setVisible(True)
            self.tbImportAudio.setVisible(True)
            self.cbRecordAudio.setVisible(False)
            self.tbMoveUp.setVisible(True)
            self.tbMoveDown.setVisible(True)
            self.tbMediaPlay.setVisible(True)
            self.hsSectionMedia.setVisible(True)
            self.lblTimeOfDay.setVisible(False)
            self.vlLeftOfTimer.setVisible(False)
            self.lblTimer.setVisible(False)
            self.lblMediaStart.setVisible(True)
            self.spMediaStart.setVisible(True)
            self.lblMediaEnd.setVisible(True)
            self.spMediaEnd.setVisible(True)
            self.pbStart.setVisible(False)
            self.pbPause.setVisible(False)
            self.pbFinish.setVisible(False)
            self.twSectionContent.tabBar().setVisible(True)
            self.frSectionControls.setEnabled(True)
            self.tbNonSpatial.setEnabled(True)
        elif self.cbMode.currentText() == 'Conduct Interview':
            self.lmbMode = 'Interview'
            self.tbImportFeatures.setVisible(False)
            self.tbImportAudio.setVisible(False)
            self.cbRecordAudio.setVisible(True)
            self.tbMoveUp.setVisible(False)
            self.tbMoveDown.setVisible(False)
            self.tbMediaPlay.setVisible(False)
            self.hsSectionMedia.setVisible(False)
            self.lblTimeOfDay.setVisible(True)
            self.vlLeftOfTimer.setVisible(True)
            self.lblTimer.setVisible(True)
            self.lblMediaStart.setVisible(False)
            self.spMediaStart.setVisible(False)
            self.lblMediaEnd.setVisible(False)
            self.spMediaEnd.setVisible(False)
            self.pbStart.setVisible(True)
            self.pbPause.setVisible(True)
            self.pbFinish.setVisible(True)
            self.twSectionContent.tabBar().setVisible(False)
            self.frSectionControls.setDisabled(True)
            self.tbNonSpatial.setDisabled(True)
        else:
            self.lmbMode = 'Transcribe'
            self.tbImportFeatures.setVisible(False)
            self.tbImportAudio.setVisible(False)
            self.cbRecordAudio.setVisible(False)
            self.tbMoveUp.setVisible(False)
            self.tbMoveDown.setVisible(False)
            self.tbMediaPlay.setVisible(True)
            self.hsSectionMedia.setVisible(True)
            self.lblTimeOfDay.setVisible(False)
            self.vlLeftOfTimer.setVisible(False)
            self.lblTimer.setVisible(False)
            self.lblMediaStart.setVisible(True)
            self.spMediaStart.setVisible(True)
            self.lblMediaEnd.setVisible(True)
            self.spMediaEnd.setVisible(True)
            self.pbStart.setVisible(False)
            self.pbPause.setVisible(False)
            self.pbFinish.setVisible(False)
            self.twSectionContent.tabBar().setVisible(True)
            self.frSectionControls.setEnabled(True)
            self.tbNonSpatial.setEnabled(True)
        try:
            if self.points_layer <> None:
                self.unloadInterview()
        except:
            pass 
        self.audioPopulateDeviceList()
        self.interviewPopulateList()
        # activate pan tool
        self.mapToolsActivatePanTool()

    #
    # redefine close event to make sure it closes properly because panel close
    # icon can not be prevented on Mac OS X when panel is floating

    def closeEvent(self, event):

        if self.lmbMode == 'Interview' and self.interviewState in ('Running','Paused'):
            self.interviewFinish()
        self.transcriberClose()
        if self.pyAI <> None:
            self.pyAI.terminate()
        try:
            self.audioStopPlayback()
        except:
            pass 
        
    #
    # connect map tools

    def mapToolsConnect(self):
        
        # use debug track order of calls
        if self.basicDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
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

    #
    # disconnect map tools

    def mapToolsDisconnect(self):

        # use debug track order of calls
        if self.basicDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # break connections to custom tools
        result = QtCore.QObject.disconnect(self.pointTool, QtCore.SIGNAL("rbFinished(QgsGeometry*)"), self.mapToolsPlacePoint)
        result = QtCore.QObject.disconnect(self.lineTool, QtCore.SIGNAL("rbFinished(QgsGeometry*)"), self.mapToolsPlaceLine)
        result = QtCore.QObject.disconnect(self.polygonTool, QtCore.SIGNAL("rbFinished(QgsGeometry*)"), self.mapToolsPlacePolygon)
        result = QtCore.QObject.disconnect(self.tbPan, QtCore.SIGNAL("clicked()"), self.mapToolsActivatePanTool)


    #####################################################
    #       time operations and notification            #
    #####################################################

    #
    # display clock & write audio file to disk each minute if recording
    
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
                # commit file to disk each minute and start another
                if self.recordAudio == True and m > self.intTimeSegment:
                    self.intTimeSegment = m
                    self.audioStop()
                    self.audioStartRecording()

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


    #####################################################
    #           project and panel management            #
    #####################################################

    #
    # read QGIS settings

    def settingsRead( self ):

        self.projectLoading = True
        # use debug track order of calls
        if self.basicDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
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

    def transcriberOpen(self):

        # disable map tips
        mpta = self.iface.actionMapTips()
        if mpta.isChecked() == True:
            mpta.trigger()

        # use debug track order of calls
        if self.basicDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
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
        self.lwProjectCodes.setMouseTracking(True)
        self.lwProjectCodes.clear()
        tempItem = QtGui.QListWidgetItem('S')
        tempItem.setToolTip('Section')
        self.lwProjectCodes.addItem(tempItem)
        codeList = projData[0][2].split('\n')
        for item in codeList:
            if item <> '':
                code, defn = item.split('=')
                self.default_codes.append(defn.strip())
                tempItem = QtGui.QListWidgetItem(code.strip())
                tempItem.setToolTip(defn.strip())
                self.lwProjectCodes.addItem(tempItem)
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
        self.projectLoading = False
        # open navigator panel
        self.navigatorPanel = mapBiographerNavigator(self.iface)
        #
        # open overview panel
        iobjs = self.iface.mainWindow().children()
        for obj in iobjs:
            if 'Overview' == obj.objectName() and 'QDockWidget' in str(obj.__class__):
                self.ovPanel = obj
                break
        # show panel
        if self.ovPanel <> None:
            self.ovPanel.show()

        return(0)

    #
    # populate interview list in combobox
    
    def interviewPopulateList(self):

        if self.projectLoading == False:
            # use debug track order of calls
            if self.basicDebug:
                if self.debugLog == True:
                    QgsMessageLog.logMessage(self.myself())
                else:
                    QtGui.QMessageBox.warning(self, 'DEBUG',
                        self.myself(), QtGui.QMessageBox.Ok)
            failMessage = 'No interviews could be found'
            # method body
            if self.lmbMode in ('Interview','Import'):
                sql = "SELECT a.id, a.code FROM interviews a "
                sql += "WHERE a.data_status = 'N' AND a.id NOT IN "
                sql += "(SELECT DISTINCT interview_id FROM interview_sections);"
                rs = self.cur.execute(sql)
                intvData = rs.fetchall()
            else:
                sql = "SELECT a.id, a.code FROM interviews a "
                sql += "WHERE a.data_status = 'RC' AND a.id IN "
                sql += "(SELECT DISTINCT interview_id FROM interview_sections);"
                rs = self.cur.execute(sql)
                intvData = rs.fetchall()
            #QgsMessageLog.logMessage('intvData len: %d ' % len(intvData))
            self.intvList = []
            self.cbInterviewSelection.clear()
            if len(intvData) == 0:
#                QtGui.QMessageBox.warning(self.iface.mainWindow(), 'Warning',
#                failMessage, QtGui.QMessageBox.Ok)
                if self.lmbMode == 'Interview':
                    self.pbStart.setDisabled(True)
            else:
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
                    self.intvList.append([row[0],row[1],nameList])
                    self.cbInterviewSelection.addItem(row[1])
                self.cbInterviewSelection.setCurrentIndex(0)
                self.pteParticipants.setPlainText(self.intvList[0][2])
                if self.lmbMode == 'Interview':
                    self.lwSectionList.clear()
                    self.pbStart.setEnabled(True)

    #
    # update interview info 

    def interviewUpdateInfo(self, cIndex):

        # use debug track order of calls
        if self.basicDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
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
            if self.lmbMode in ('Interview','Import'):
                self.mapRemoveInterviewLayers()
                self.mapAddInterviewLayers()
            else:
                self.interviewLoad()
        else:
            self.interview_id = None
            self.interview_code = ''
            self.pteParticipants.setPlainText('')

    #
    # load interview

    def interviewLoad(self):

        self.iface.actionRemoveAllFromOverview().activate(0)
        # use debug track order of calls
        if self.basicDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
#                QgsMessageLog.logMessage('\nLoading Interview')
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
            self.interviewUnload()
        self.interviewState == 'Load'
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
        self.frSectionControls.setEnabled(True)
        # load interview map layers
        self.mapAddInterviewLayers()
        # load interview sections and update link list for cbFeatureStatus
        sql = "SELECT id, section_code, geom_source, sequence_number FROM interview_sections "
        sql += "WHERE interview_id = %d ORDER BY sequence_number;" % self.interview_id
        rs = self.cur.execute(sql)
        sectionList = rs.fetchall()
        self.cbFeatureStatus.clear()
        self.cbFeatureStatus.addItems(['none','unique'])
        self.lwSectionList.clear()
        for section in sectionList:
            self.lwSectionList.addItem(section[1])
            if section[2] in ('pt','ln','pl'):
                self.cbFeatureStatus.addItem('same as %s' % section[1])
        self.interviewState = 'View'
        if len(sectionList) > 0:
            self.lwSectionList.setCurrentItem(self.lwSectionList.item(0))
        
    #
    # unload interview

    def interviewUnload(self):

        # use debug track order of calls
        if self.basicDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        self.interviewState = 'Unload'
        # clear section list
        self.lwSectionList.clear()
        # remove layers if they exist
        self.mapRemoveInterviewLayers()

    #
    # close trancription interface
    
    def transcriberClose(self):

        # use debug track order of calls
        if self.basicDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
#                QgsMessageLog.logMessage('\nClose Transcriber')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # close navigator
        self.navigatorPanel.close()
        # unload interview
        self.interviewUnload()
        # disconnect map tools
        self.mapToolsDisconnect()
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
        # deselect active layer and select active layer again
        tv = self.iface.layerTreeView()
        tv.selectionModel().clear()
        a = self.iface.legendInterface().layers()
        if len(a) > 0:
            self.iface.setActiveLayer(a[0])
        self.iface.newProject()

    #
    # add interview map layers in order of polygon, line and point to ensure visibility

    def mapAddInterviewLayers(self):

        if self.basicDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
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
        display_name = 'lmb_polygons'
        self.polygons_layer = QgsVectorLayer(uri.uri(), display_name, 'spatialite',False)
        self.polygons_layer.setDisplayField('section_code')
        # set display characteristics
        self.polygons_layer.rendererV2().symbol().setAlpha(0.5)
        symbolLayer = self.polygons_layer.rendererV2().symbol().symbolLayer(0)
        symbolLayer.setFillColor(QtGui.QColor('#47b247'))
        symbolLayer.setBorderColor(QtGui.QColor('#245924'))
        symbolLayer.setBorderWidth(0.6)
        QgsMapLayerRegistry.instance().addMapLayer(self.polygons_layer)
        # add to overview
        self.iface.actionAddToOverview().activate(0)
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
        display_name = 'lmb_lines'
        self.lines_layer = QgsVectorLayer(uri.uri(), display_name, 'spatialite',False)
        self.lines_layer.setDisplayField('section_code')
        # set display characteristics
        symbol = self.lines_layer.rendererV2().symbol()
        symbol.setColor(QtGui.QColor('#245924'))
        symbol.setWidth(0.6)
        QgsMapLayerRegistry.instance().addMapLayer(self.lines_layer)
        # add to overview
        self.iface.actionAddToOverview().activate(0)
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
        display_name = 'lmb_points'
        self.points_layer = QgsVectorLayer(uri.uri(), display_name, 'spatialite',False)
        self.points_layer.setDisplayField('section_code')
        # set display characteristics
        symbol = self.points_layer.rendererV2().symbols()[0]
        symbol.setSize(3)
        symbol.setColor(QtGui.QColor('#47b247'))
        symbol.setAlpha(0.5)
        QgsMapLayerRegistry.instance().addMapLayer(self.points_layer)
        # add to overview
        self.iface.actionAddToOverview().activate(0)
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
        # set display fields for map tips
        self.polygons_layer.setDisplayField('section_code')
        self.lines_layer.setDisplayField('section_code')
        self.points_layer.setDisplayField('section_code')
        # refresh navigator panel
        self.navigatorPanel.loadLayers()

    #
    # remove interview map layers

    def mapRemoveInterviewLayers(self):

        if self.basicDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        try:
            lyrs = self.iface.mapCanvas().layers()
            #QgsMessageLog.logMessage('lyr count %d' % len(lyrs))
            for lyr in lyrs:
                if lyr.name() in ('lmb_points','lmb_lines','lmb_polygons'):
                    #QgsMessageLog.logMessage('removing: %s ' % str(lyr.name()))
                    QgsMapLayerRegistry.instance().removeMapLayer(lyr.id())
        except:
            pass


    #####################################################
    #               audio operations                    #
    #####################################################

    #
    # populate audio device list

    def audioPopulateDeviceList(self):

        # use debug track order of calls
        if self.audioDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # create array to store info
        self.deviceList = []
        self.pyAI = None
        self.pyAI = pyaudio.PyAudio()
        # add devices with input channels
        bestChoice = 0
        # clear menu actions
        self.tbAudioSettings.menu().clear()
        #self.tbAudioSettings.menu().setTitle('Select Audio Device')
        x = 0
        for i in range(self.pyAI.get_device_count()):
            devinfo = self.pyAI.get_device_info_by_index(i)
            if self.lmbMode in ('Transcribe','Import'):
                # check if we can play audio
                if devinfo['maxOutputChannels'] > 0:
                        # add to device list
                        self.deviceList.append([i,devinfo['name']])
                        # create a menu item action
                        menuItem_AudioDevice = self.tbAudioSettings.menu().addAction(devinfo['name'])
                        # create lambda function
                        receiver = lambda deviceIndex=i: self.audioSelectDevice(deviceIndex)
                        # link lambda function to menu action
                        self.connect(menuItem_AudioDevice, QtCore.SIGNAL('triggered()'), receiver)
                        # add to menu
                        self.tbAudioSettings.menu().addAction(menuItem_AudioDevice)
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
                            menuItem_AudioDevice = self.tbAudioSettings.menu().addAction(devinfo['name'])
                            # create lambda function
                            receiver = lambda deviceIndex=i: self.audioSelectDevice(deviceIndex)
                            # link lambda function to menu action
                            self.connect(menuItem_AudioDevice, QtCore.SIGNAL('triggered()'), receiver)
                            # add to menu
                            self.tbAudioSettings.menu().addAction(menuItem_AudioDevice)
                            if devinfo['name'] == 'default':
                                bestChoice = x
                            x += 1
                    except:
                        pass 
        self.audioDeviceIndex = self.deviceList[bestChoice][0]
        self.audioDeviceName = self.deviceList[bestChoice][1]
        if len(self.deviceList) > 0:
            if self.lmbMode == 'Interview':
                self.setWindowTitle('LMB - (Audio Device: %s) - Recording Disabled' % self.audioDeviceName)
            else:
                self.setWindowTitle('LMB - (Audio Device: %s)'  % self.audioDeviceName)
        else:
            if self.lmbMode == 'Interview':
                self.setWindowTitle('LMB - (No Audio Device Found) - Recording Disabled')
            else:
                self.setWindowTitle('LMB - (No Audio Device Found)')

    #
    # select audio device for recording or playback

    def audioSelectDevice(self,deviceIndex):

        # use debug track order of calls
        if self.audioDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        self.audioDeviceIndex = deviceIndex
        for x in range(len(self.deviceList)):
            if self.deviceList[x][0] == self.audioDeviceIndex:
                self.audioDeviceName = self.deviceList[x][1]
                break
        # set title
        if self.lmbMode == 'Interview':
            self.setWindowTitle('LMB - (Audio Device: %s) - Recording Disabled' % self.audioDeviceName)
        else:
            self.setWindowTitle('LMB - (Audio Device: %s)'  % self.audioDeviceName)
        # reset recording state
        self.cbRecordAudio.setCurrentIndex(0)

    #
    # play audio during transcript and import mode

    def audioStartPlayback(self):

        # use debug track order of calls
        if self.audioDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
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

    def audioPlayPause(self):

        # use debug track order of calls
        if self.audioDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        if self.mediaState == 'paused':
            self.audioStartPlayback()
        elif self.mediaState == 'playing':
            self.audioStopPlayback()

    #
    # stop audio playback

    def audioStopPlayback(self):
        
        # use debug track order of calls
        if self.audioDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
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
    # update audio current position during playback

    def audioUpdateCurrentPosition(self):

        self.audioCurrentPosition = self.hsSectionMedia.value()

    #
    # update audio status during playback

    def audioUpdateStatus(self, statusMessage):

        # use debug track order of calls
        if self.audioDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
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
    # test microphone

    def audioTest(self):

        # use debug track order of calls
        if self.audioDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        if self.cbRecordAudio.currentText() == 'Record Audio':
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
                    self.cbRecordAudio.setCurrentIndex(0)
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
                self.recordAudio = False
                self.cbRecordAudio.setCurrentIndex(0)
            else:
                self.recordAudio = True
                #QgsMessageLog.logMessage(str(self.deviceList))
                #QgsMessageLog.logMessage(str(self.audioDeviceIndex))
                self.setWindowTitle('LMB - (Audio Device: %s) - Recording Enabled' % self.audioDeviceName)
        else:
            self.recordAudio = False
            # no audio recording
            self.pbStart.setEnabled(True)
            if len(self.deviceList) > 0:
                self.setWindowTitle('LMB - (Audio Device: %s) - Recording Disabled' % self.audioDeviceName)
            else:
                self.setWindowTitle('LMB - (No Audio Device Found) - Recording Disabled')

    #
    # notify of audio status during recording

    def audioNotifyStatus(self, statusMessage):
    
        self.setWindowTitle('LMB - (Audio Device: %s) - %s' % (self.audioDeviceName,statusMessage))
        
    #
    # notify of audio error - for debugging purposes

    def audioNotifyError(self, e, exception_string):

        # use debug track order of calls
        if self.audioDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        errorMessage = 'Audio thread raised an exception:\n' + format(exception_string)
        QtGui.QMessageBox.critical(self, 'message',
            errorMessage, QtGui.QMessageBox.Ok)
        self.audioStop()
        self.interviewFinish()

    #
    # update slider position

    def audioUpdateSliderPosition(self, position):

        self.hsSectionMedia.setValue(position)

    #
    # start audio

    def audioStartRecording(self):

        # use debug track order of calls
        if self.audioDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # get path for audio file and create prefix
        s = QtCore.QSettings()
        dirName = s.value('mapBiographer/projectDir')
        afPrefix = os.path.join(dirName, self.interview_code)
        # create worker
        worker = audioRecorder(afPrefix,self.audioDeviceIndex,self.pyAI,self.interview_code)
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

    def audioStop(self):
        
        # use debug track order of calls
        if self.audioDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        self.worker.stop()           
        self.audioSection += 1
        self.worker.deleteLater()
        self.thread.quit()
        self.thread.wait()
        self.thread.deleteLater()        

    #
    # stop audio and merge recordings

    def audioStopConsolidate(self):
        
        # use debug track order of calls
        if self.audioDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        self.worker.stopNMerge()           
        self.audioSection += 1
        self.worker.deleteLater()
        self.thread.quit()
        self.thread.wait()
        self.thread.deleteLater()        


    #####################################################
    #               interview operation                 #
    #####################################################

    #
    # start interview

    def interviewStart(self):

        # use debug track order of calls
        if self.basicDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
#                QgsMessageLog.logMessage('\nStarting Interview')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        #
        # set defaults
        # interview info
        self.startTime = 0
        self.pauseDuration = 0
        self.startPause = 0
        self.audioPartNo = 1
        self.point_id = 0
        self.line_id = 0
        self.polygon_id = 0
        self.interviewState = 'New'
        # section info
        self.section_id = 0
        self.sequence = 0
        self.currentSequence = 0
        self.currentContentCode = ''
        self.previousContentCode = ''
        self.previousSecurity = 'PU'
        self.previousTags = ''
        self.previousUsePeriod = 'U'
        self.previousAnnualVariation = 'U'
        self.previousNote = ''
        self.currentFeature = 'ns'
        self.selectedCodeCount = 0
        # set audio section
        self.audioSection = 1
        # start timer thread
        self.startTime = time.time()
        self.lblTimer.setText('00:00:00')
        # setup clock and timer
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.timeShow)
        self.timer.start(1000)
        self.timeShow()
        if self.recordAudio == True:
            # start audio recording
            self.audioStartRecording()
        # set main buttons status
        self.pbStart.setDisabled(True)
        self.pbPause.setEnabled(True)
        self.pbFinish.setEnabled(True)
        # enable section edit controls
        self.frSectionControls.setEnabled(True)
        self.frInterviewSelection.setDisabled(True)
        # set interview state
        self.interviewState = 'Running'
        # get previous section id
        sql = 'SELECT max(id) FROM interview_sections;'
        rs = self.cur.execute(sql)
        rsData = rs.fetchall()
        if rsData[0][0] == None:
            self.previousSectionId = 0
        else:
            self.previousSectionId = int(rsData[0][0])
        # get previous point id
        sql = 'SELECT max(id) FROM points;'
        rs = self.cur.execute(sql)
        rsData = rs.fetchall()
        if rsData[0][0] == None:
            self.previousPointId = 0
        else:
            self.previousPointId = int(rsData[0][0])
        # get previous line id
        sql = 'SELECT max(id) FROM lines;'
        rs = self.cur.execute(sql)
        rsData = rs.fetchall()
        if rsData[0][0] == None:
            self.previousLineId = 0
        else:
            self.previousLineId = int(rsData[0][0])
        # get previous polygon id
        sql = 'SELECT max(id) FROM polygons;'
        rs = self.cur.execute(sql)
        rsData = rs.fetchall()
        if rsData[0][0] == None:
            self.previousPolygonId = 0
        else:
            self.previousPolygonId = int(rsData[0][0])
        # create a new section at the start of interview 
        # to capture introductory remarks
        self.sectionCreateNonSpatial()
        
    #
    # pause and start interview

    def interviewPause(self):

        # use debug track order of calls
        if self.basicDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # change label and action if running or paused
        if self.interviewState == 'Running':
            # measure time at start of pause
            self.pauseStart = time.time()
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

    #
    # finish interview - stop recording, consolidate audio and close of section and interview records

    def interviewFinish(self):

        # use debug track order of calls
        if self.basicDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
#                QgsMessageLog.logMessage('\nFinishing Interview')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # set state
        self.copyPrevious = False
        self.rapidCapture = False
        self.zoomToFeature = False
        self.interviewState = 'Finished'
        # reset tools
        self.canvas.unsetMapTool(self.canvas.mapTool())
        # clean up
        # stop timer
        self.timer.stop()
        self.endTime = time.time()
        self.interviewLength = self.lblTimer.text()
        if self.recordAudio == True:
            # stop audio recording and consolidate recordings
            self.audioStopConsolidate()
        # adjust interface
        # disable
        self.cbRecordAudio.setCurrentIndex(0)
        # disable pause and finish
        self.pbFinish.setDisabled(True)
        self.pbPause.setDisabled(True)
        # get last media_end_time value
        sql = "SELECT max(id) FROM interview_sections "
        sql += "WHERE interview_id = %d;" % self.interview_id
        rs = self.cur.execute(sql)
        secId = rs.fetchall()[0]
        # udate last media_end_time value
        sql = "UPDATE interview_sections "
        sql += "SET media_end_time = '%s' " % self.interviewLength
        sql += "WHERE id = %d and " % secId
        sql += "interview_id = %d; " % self.interview_id
        self.cur.execute(sql)
        # update interview record
        startString = time.strftime("%Y-%m-%d %H:%M", time.localtime(self.startTime))
        endString = time.strftime("%Y-%m-%d %H:%M", time.localtime(self.endTime))
        sql = "UPDATE interviews SET "
        sql += "start_datetime = '%s', " % startString
        sql += "end_datetime = '%s', " % endString
        sql += "date_modified = '%s', " % endString[:-6]
        sql += "data_status = 'RC' "
        sql += "WHERE id = %d; " % self.interview_id
        self.cur.execute(sql)
        self.conn.commit()
        # disable interview
        self.frSectionControls.setDisabled(True)
        # enable close button
        self.frInterviewSelection.setEnabled(True)
        # clear interview
        self.interviewUnload()
        # update interview list
        self.interviewPopulateList()
        
        

    #####################################################
    #           section editing controls                #
    #####################################################
        
    #
    # enable save, cancel and delete buttons

    def sectionEnableSaveCancel(self):

        if self.pbSaveSection.isEnabled() == False and \
        ( (self.interviewState == 'View' and self.featureState == 'View') or \
        (self.interviewState == 'Running' and self.featureState <> 'Load') ):
            # use debug track order of calls
            if self.editDebug:
                if self.debugLog == True:
                    QgsMessageLog.logMessage(self.myself())
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
            if self.lmbMode == 'Interview':
                # disable map tools
                self.tbPoint.setDisabled(True)
                self.tbLine.setDisabled(True)
                self.tbPolygon.setDisabled(True)
                # disable finish and pause
                self.pbPause.setDisabled(True)
                self.pbFinish.setDisabled(True)
            # disable new section
            self.tbNonSpatial.setDisabled(True)
            self.featureState = 'Edit'

    #
    # enable section cancel and save (optionally) buttons but disable delete
    # this is useful during digitizing of new feaures

    def sectionEnableCancel(self,enableSave=False):

        if self.interviewState in ('View','Running'):
            # use debug track order of calls
            if self.editDebug:
                if self.debugLog == True:
                    QgsMessageLog.logMessage(self.myself())
                else:
                    QtGui.QMessageBox.warning(self, 'DEBUG',
                        self.myself(), QtGui.QMessageBox.Ok)
            # method body
            # prevent section from being changed
            self.lwSectionList.setDisabled(True)
            self.pbCancelSection.setEnabled(True)
            if self.lmbMode == 'Interview':
                if enableSave == True:
                    self.pbSaveSection.setEnabled(True)
                    # disable map tools
                    self.tbPoint.setDisabled(True)
                    self.tbLine.setDisabled(True)
                    self.tbPolygon.setDisabled(True)
                else:
                    self.pbSaveSection.setDisabled(True)
                    # enable map tools
                    self.tbPoint.setEnabled(True)
                    self.tbLine.setEnabled(True)
                    self.tbPolygon.setEnabled(True)
                # disable finish and pause
                self.pbPause.setDisabled(True)
                self.pbFinish.setDisabled(True)
            else:
                if enableSave == True:
                    self.pbSaveSection.setEnabled(True)
                else:
                    self.pbSaveSection.setDisabled(True)
            self.pbDeleteSection.setDisabled(True)
            # enable move and edit
            self.tbMove.setEnabled(True)
            self.tbEdit.setEnabled(True)
            self.tbNonSpatial.setDisabled(True)

    #
    # disable save and cancel buttons, but leave delete enabled

    def sectionDisableSaveCancel(self):

        if self.interviewState in ('View','Running'):
            # use debug track order of calls
            if self.editDebug:
                if self.debugLog == True:
                    QgsMessageLog.logMessage(self.myself())
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
            if self.lmbMode == 'Interview':
                # enable map tools
                self.tbPoint.setEnabled(True)
                self.tbLine.setEnabled(True)
                self.tbPolygon.setEnabled(True)
                self.tbNonSpatial.setEnabled(True)
                # enable finish and pause
                self.pbPause.setEnabled(True)
                self.pbFinish.setEnabled(True)
            else:
                # enable new section tool
                self.tbNonSpatial.setEnabled(True)
            # adjust state
            if self.featureState == 'Edit':
                self.featureState = 'View'


    #####################################################
    #           section creation and deletion           #
    #####################################################

    #
    # create non-spatial section

    def sectionCreateNonSpatial(self):

        # use debug track order of calls
        if self.editDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        self.currentFeature = 'ns'
        #self.activatePanTool()
        self.sectionCreateRecord()
        # commit section 
        self.conn.commit()
        # reset state
        self.featureState == 'View'
        # add entry to list
        self.sectionAddEntry()
        # set action buttons
        self.sectionDisableSaveCancel()

    #
    # create section record - creates record in database and sets global variables

    def sectionCreateRecord(self):

        # use debug track order of calls
        if self.editDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # set state
        self.featureState = 'Create'
        # set date information
        self.section_date_created = datetime.datetime.now().isoformat()[:10]
        self.section_date_modified = self.section_date_created
        if self.lmbMode <> 'Interview':
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
        if self.lmbMode == 'Interview':
            if self.copyPrevious == True:
                # copy previous record
                self.currentContentCode = self.previousContentCode
                data_security = self.previousSecurity
                tags = self.previousTags
                use_period = self.previousUsePeriod
                annual_variation = self.previousAnnualVariation
                note = self.previousNote
            else:
                # create new record
                self.currentContentCode = "S"
                data_security = 'PU'
                tags = 'S'
                use_period = 'U'
                annual_variation = 'U'
                note = ''
            # update previous records media_end_time value
            media_start_time = self.lblTimer.text()
            media_end_time = media_start_time
            if self.section_id > 1:
                sql = "UPDATE interview_sections "
                sql += "SET media_end_time = '%s' " % media_start_time
                sql += "WHERE id = %d and interview_id = %d;" % (self.section_id - 1, self.interview_id)
                self.cur.execute(sql)
                #self.conn.commit()
            # add new record
            self.sequence += 1
            self.currentSequence = self.sequence
            self.currentSectionCode = '%s%04d' % (self.currentContentCode,self.currentSequence)
        else:
            # create new record
            self.currentContentCode = "S"
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
            #self.conn.commit()
            self.maxCodeNumber += 1
            self.currentSectionCode = '%s%04d' % (self.currentContentCode,self.maxCodeNumber)
            self.currentCodeNumber = self.maxCodeNumber
            self.currentSequence = newSequence
        sql = 'INSERT INTO interview_sections (id, interview_id, sequence_number, '
        sql += 'content_code, section_code, note, use_period, annual_variation, '
        sql += 'spatial_data_source, geom_source, tags, media_start_time, media_end_time, '
        sql += 'data_security, date_created, date_modified) VALUES '
        sql += '(%d,%d,' % (self.section_id, self.interview_id)
        sql += '%d,"%s","%s","%s",' % (self.currentSequence, self.currentContentCode, self.currentSectionCode, note)
        sql += '"%s","%s","%s",' % (use_period, annual_variation, spatial_data_source)
        sql += '"%s","%s","%s","%s","%s",' % (self.currentFeature,tags,media_start_time,media_end_time,data_security)
        sql += '"%s","%s");' % (self.section_date_created, self.section_date_modified)
        self.cur.execute(sql)
        #self.conn.commit()
        # set defaults
        self.previousContentCode = self.currentContentCode 
        self.previousSecurity = data_security
        self.previousTags = tags
        self.previousUsePeriod = use_period
        self.previousAnnualVariation = annual_variation
        self.previousNote = note
        
    #
    # add section record to list widget - called after a section is fully created
    
    def sectionAddEntry(self):

        # use debug track order of calls
        if self.editDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # clear selected tags
        selectedItems = self.lwProjectCodes.selectedItems()
        for item in selectedItems:
            self.lwProjectCodes.setItemSelected(item,False)
        if self.lmbMode == 'Interview':
            # add  to end of list and select it in section list
            self.lwSectionList.addItem(self.currentSectionCode)
            self.lwSectionList.setCurrentRow(self.lwSectionList.count()-1)
            # add new section to feature status control
            if self.currentFeature in ('pt','ln','pl'):
                idx = self.cbFeatureStatus.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
                if idx == -1:
                    self.cbFeatureStatus.addItem('same as %s' % self.currentSectionCode)
        else:
            # insert into section list after current item and select it
            self.lwSectionList.insertItem(self.lwSectionList.currentRow()+1,self.currentSectionCode)
            # set new row as current which will trigger select and load
            self.lwSectionList.setCurrentRow(self.lwSectionList.currentRow()+1)

    #
    # update map feature when a spatial feature is edited

    def sectionUpdateMapFeature(self):

        # use debug track order of calls
        if self.editDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
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
            self.points_layer.updateExtents()
        elif self.currentFeature == 'ln':
            # update database
            sql = "UPDATE lines "
            sql += "SET geom = GeomFromText('%s',3857) " % feat2.geometry().exportToWkt()
            sql += "WHERE id = %d " % self.line_id
            self.cur.execute(sql)
            self.lines_layer.updateExtents()
        elif self.currentFeature == 'pl':
            # update database
            sql = "UPDATE polygons "
            sql += "SET geom = GeomFromText('%s',3857) " % feat2.geometry().exportToWkt()
            sql += "WHERE id = %d " % self.polygon_id
            self.cur.execute(sql)
            self.polygons_layer.updateExtents()
        if self.lmbMode == 'Interview':
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
        self.mapToolsActivatePanTool()

    #
    # delete map feature from a section

    def sectionDeleteMapFeature(self, oldGeomSource):

        # use debug track order of calls
        if self.editDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
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

    def sectionCopyReferencedFeature(self, referencedCode):

        # use debug track order of calls
        if self.editDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
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
            sql += "(id,interview_id,section_id,section_code,content_code,date_created,date_modified,geom) "
            sql += "VALUES (%d,%d,%d, " % (self.point_id, self.interview_id, self.section_id)
            sql += "'%s','%s','%s','%s'," %  (self.currentSectionCode,self.currentContentCode,self.section_date_created, self.section_date_modified)
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
            sql += "(id,interview_id,section_id,section_code,content_code,date_created,date_modified,geom) "
            sql += "VALUES (%d,%d,%d, " % (self.line_id, self.interview_id, self.section_id)
            sql += "'%s','%s','%s','%s'," %  (self.currentSectionCode,self.currentContentCode,self.section_date_created, self.section_date_modified)
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
            sql += "(id,interview_id,section_id,section_code,content_code,date_created,date_modified,geom) "
            sql += "VALUES (%d,%d,%d, " % (self.polygon_id, self.interview_id, self.section_id)
            sql += "'%s','%s','%s','%s'," %  (self.currentSectionCode,self.currentContentCode,self.section_date_created, self.section_date_modified)
            sql += "GeomFromText('%s',3857));" % oldFeat.geometry().exportToWkt()
            self.cur.execute(sql)
            currentGeomSource = 'pl'
        self.currentFeature = currentGeomSource
        self.conn.commit()
        return(currentGeomSource)

    #
    # save section - this is somewhat complex because of many options detailed in comments below
    
    def sectionSaveEdits(self):

        # use debug track order of calls
        if self.editDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # change interface to reflect completion of editing
        self.sectionDisableSaveCancel()
        # set codes for SQL
        self.currentContentCode = self.leCode.text()
        sectionCode = '%s%04d' % (self.currentContentCode,self.currentCodeNumber)
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
            self.sectionUpdateMapFeature()
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
                self.sectionDeleteMapFeature(oldGeomSource)
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
                self.sectionDeleteMapFeature(oldGeomSource)
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
                currentGeomSource = self.sectionCopyReferencedFeature(referencedCode)
                editVector = True
        # process core record changes second
        # 
        # check for changes to section code
        if sectionCode <>  self.currentSectionCode:
            # update section list
            self.previousContentCode = self.currentContentCode
            self.sectionUpdateCode(sectionCode, self.currentContentCode)
            lstIdx = self.cbFeatureStatus.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
            if lstIdx <> -1:
                self.cbFeatureStatus.setItemText(lstIdx, 'same as %s' % sectionCode)
            self.lwSectionList.currentItem().setText(sectionCode)
        if self.lmbMode <> 'Interview':
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
        sql += "content_code = '%s', " % self.currentContentCode
        sql += "section_code = '%s', " % sectionCode
        sql += "data_security = '%s', " % self.previousSecurity
        sql += "geom_source = '%s', " % currentGeomSource
        sql += "tags = '%s', " % self.previousTags
        sql += "use_period = '%s', " % self.previousUsePeriod
        sql += "annual_variation = '%s', " % self.previousAnnualVariation
        sql += "note = '%s', " % self.previousNote
        sql += "section_text = '%s', " % self.previousText
        if self.lmbMode == 'Transcribe':
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
            self.sectionSelect()
        elif deselectOld == True:
            # this is an else statement because the selectFeature method deselects old features
            self.points_layer.deselect(self.points_layer.selectedFeaturesIds())
            self.lines_layer.deselect(self.lines_layer.selectedFeaturesIds())
            self.polygons_layer.deselect(self.polygons_layer.selectedFeaturesIds())
        if editVector == True:
            self.mapToolsActivateSpatialEdit()
        else:
            self.mapToolsActivatePanTool()
            
    #
    # cancel edits to section

    def sectionCancelEdits(self):

        # use debug track order of calls
        if self.editDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
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
                self.editLayer.rollback()
                QgsMapLayerRegistry.instance().removeMapLayer(self.editLayer.id())
            self.points_layer.deselect(self.points_layer.selectedFeaturesIds())
            self.lines_layer.deselect(self.lines_layer.selectedFeaturesIds())
            self.polygons_layer.deselect(self.polygons_layer.selectedFeaturesIds())
            self.cbFeatureStatus.setCurrentIndex(0)
            self.vectorEditing = False
            # no need to reload as other changes already saved
        elif self.lmbMode == 'Interview' and self.featureState == 'Create':
            # if creating a new section, abandon edits by resetting tool and deleting new section
            if self.tbPoint.isChecked() == True:
                self.pointTool.deactivate()
            elif self.tbLine.isChecked() == True:
                self.lineTool.deactivate()
            elif self.tbPolygon.isChecked == True:
                self.polygonTool.deactivate()
            sql = "DELETE FROM interview_sections WHERE "
            sql += "id = %d" % self.section_id
            self.cur.execute(sql)
            self.conn.commit()
            self.vectorEditing = False
            # don't reload as record deleted and old record still highlighted
        elif self.vectorEditing == True:
            # if vector edting, abandon changes
            self.vectorEditing = False
            self.editLayer.commitChanges()
            QgsMapLayerRegistry.instance().removeMapLayer(self.editLayer.id())
            # reload as other changes not saved too
            self.sectionLoadRecord()
        else:
            # no spatial changes so just reload the record
            self.sectionLoadRecord()
        # reset state, tools and widgets
        self.featureState = 'View'
        self.mapToolsActivatePanTool()
        self.sectionDisableSaveCancel()
        
    #
    # delete section

    def sectionDelete(self):

        # use debug track order of calls
        if self.editDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
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
            elif self.currentFeature == 'ln':
                sql = "DELETE FROM lines WHERE "
                sql += "interview_id = %d and section_id = %d" % (self.interview_id, self.section_id)
                self.cur.execute(sql)
            elif self.currentFeature == 'pl':
                sql = "DELETE FROM polygons WHERE "
                sql += "interview_id = %d and section_id = %d" % (self.interview_id, self.section_id)
                self.cur.execute(sql)
            sql = "DELETE FROM interview_sections WHERE "
            sql += "id = %d" % self.section_id
            self.cur.execute(sql)
            self.conn.commit()
            # remove from section list
            self.lwSectionList.takeItem(self.lwSectionList.currentRow())
        # reset interface
        self.sectionDisableSaveCancel()
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
            self.mapToolsActivatePanTool()
        

    #####################################################
    #           section selection and loading           #
    #####################################################

    #
    # select section

    def sectionSelect(self):

        # check for keyboard modifier to zoom to feature if shift is held down
        modifiers = QtGui.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.ShiftModifier:
            self.zoomToFeature = True
        else:
            self.zoomToFeature = False
            
        # determine nature of current feature and select
        if self.lwSectionList.currentItem() <> None and \
        ( (self.lmbMode in ('Import','Transcribe') and \
        self.interviewState == 'View') or \
        (self.lmbMode == 'Interview' and self.interviewState == 'Running') ):
            if self.lmbMode in ('Import','Transcribe') and \
            self.mediaState == 'playing':
                self.playPauseMedia()
            # use debug track order of calls
            if self.editDebug:
                if self.debugLog == True:
                    QgsMessageLog.logMessage(self.myself())
#                    QgsMessageLog.logMessage('\nSelect Feature')
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
            geomSource = self.sectionData[0][4]
            # allow for selecting another section
            selectedCode = self.currentSectionCode
            self.sectionLoadRecord()
            # check if non-spatial
            if geomSource == 'ns':
                self.currentFeature = 'ns'
            else:
                # select spatial feaure
                if not geomSource in ('pt','ln','pl'):
                    # grab id for referenced feature
                    self.currentFeature = 'rf'
                    # get attributes of referenced feature from a different section
                    selectedCode = geomSource
                    sql = "SELECT id, geom_source FROM interview_sections WHERE "
                    sql += "interview_id = %d AND section_code = '%s';" % (self.interview_id, selectedCode)
                    rs = self.cur.execute(sql)
                    idData = rs.fetchall()
                    selectedId = idData[0][0]
                    geomSource = idData[0][1]
                else:
                    # set current feature variable for sections with their own spatial features
                    self.currentFeature = geomSource
                # select feature connected to this section
                if geomSource == 'pt':
                    sql = "SELECT id FROM points WHERE "
                    sql += "interview_id = %d AND section_code = '%s';" % (self.interview_id, selectedCode)
                    rs = self.cur.execute(sql)
                    idData = rs.fetchall()
                    if len(idData) > 0:
                        self.point_id = idData[0][0]
                        self.points_layer.select(self.point_id)
                        if self.zoomToFeature == True:
                            bbox = self.points_layer.boundingBoxOfSelected()
                            self.canvas.setExtent(bbox)
                            self.canvas.refresh()
                    else:
                        self.currentFeature = 'ns'
                elif geomSource == 'ln':
                    sql = "SELECT id FROM lines WHERE "
                    sql += "interview_id = %d AND section_code = '%s';" % (self.interview_id, selectedCode)
                    rs = self.cur.execute(sql)
                    idData = rs.fetchall()
                    if len(idData) > 0:
                        self.line_id = idData[0][0]
                        self.lines_layer.select(self.line_id)
                        if self.zoomToFeature == True:
                            bbox = self.lines_layer.boundingBoxOfSelected()
                            self.canvas.setExtent(bbox)
                            self.canvas.refresh()
                    else:
                        self.currentFeature = 'ns'
                elif geomSource == 'pl':
                    sql = "SELECT id FROM polygons WHERE "
                    sql += "interview_id = %d AND section_code = '%s';" % (self.interview_id, selectedCode)
                    rs = self.cur.execute(sql)
                    idData = rs.fetchall()
                    if len(idData) > 0:
                        self.polygon_id = idData[0][0]
                        self.polygons_layer.select(self.polygon_id)
                        if self.zoomToFeature == True:
                            bbox = self.polygons_layer.boundingBoxOfSelected()
                            self.canvas.setExtent(bbox)
                            self.canvas.refresh()
                    else:
                        self.currentFeature = 'ns'
            if self.currentFeature == 'ns' and self.zoomToFeature:
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

    def sectionLoadRecord(self):

        # use debug track order of calls
        if self.editDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
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
        # set to load state so no change in enabling controls happens
        oldState = self.featureState
        self.featureState = 'Load'
        # update section edit controls
        # set time and audio controls
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
        # set interface fields
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
        # return to view state
        self.featureState = oldState
            
    #
    # update section code in spatial layer when the section code changes

    def sectionUpdateCode(self, sectionCode, contentCode):
        
        # use debug track order of calls
        if self.editDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        # update spatial table if section is spatial
        if self.currentFeature == 'pt':
            sql = "UPDATE points SET "
            sql += "section_code = '%s', content_code = '%s' " % (sectionCode, contentCode)
            sql += "WHERE section_id = %d;" % self.section_id
        elif self.currentFeature == 'ln':
            sql = "UPDATE lines SET "
            sql += "section_code = '%s', content_code = '%s' " % (sectionCode, contentCode)
            sql += "WHERE section_id = %d;" % self.section_id
        elif self.currentFeature == 'pl':
            sql = "UPDATE polygons SET "
            sql += "section_code = '%s', content_code = '%s' " % (sectionCode, contentCode)
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

    def sectionFeatureStatusChanged(self):

        # need to make changes here
        if self.featureState in ('View','Edit'):
            if self.currentFeature == 'ns' and self.cbFeatureStatus.currentIndex() == 1:
                # was non-spatial and user choose to make it spatial switch to point tool
                # because user can change to line or polygon tool if needed
                self.featureState = 'Add Spatial'
                self.mapToolsActivatePointCapture()
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
                self.sectionEnableSaveCancel()
            else:
                # enable saving or cancelling in response to editing
                self.sectionEnableSaveCancel()

    #
    # add / remove tags to sections
        
    def sectionAddRemoveTags(self):

        modifiers = QtGui.QApplication.keyboardModifiers()
        # use debug track order of calls
        if self.editDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself() + ': ' + self.featureState, QtGui.QMessageBox.Ok)
        # method body
        # only act if editing or viewing, not loading
        if self.featureState in ('View','Edit'):
            # grab modifier key
            if modifiers == QtCore.Qt.ControlModifier:
                replaceContentCode = True
            else:
                replaceContentCode = False
            # determine what items are selected
            selectedItems = self.lwProjectCodes.selectedItems()
            # if adding items
            if self.selectedCodeCount < len(selectedItems):
                if replaceContentCode == True:
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
            self.sectionEnableSaveCancel()


    #####################################################
    #                   map tools                       #
    #####################################################

    #
    # activate pan tool

    def mapToolsActivatePanTool(self):

        # use debug track order of calls
        if self.spatialDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
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

    def mapToolsActivatePointCapture(self):

        if self.lmbMode == 'Interview':
            # check for keyboard modifier
            modifiers = QtGui.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ControlModifier or self.rapidCapture == True:
                self.copyPrevious = True
            else:
                self.copyPrevious = False
        # use debug track order of calls
        if self.spatialDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        self.sectionEnableCancel()
        self.currentFeature = 'pt'
        if self.lmbMode == 'Interview' and not self.featureState in ('Create','Add Spatial'):
            # create section record so that the audio index starts here
            self.sectionCreateRecord()
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

    def mapToolsActivateLineCapture(self):

        if self.lmbMode == 'Interview':
            # check for keyboard modifier
            modifiers = QtGui.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ControlModifier or self.rapidCapture == True:
                self.copyPrevious = True
            else:
                self.copyPrevious = False
        # use debug track order of calls
        if self.spatialDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        self.sectionEnableCancel()
        self.currentFeature = 'ln'
        if self.lmbMode == 'Interview' and not self.featureState in ('Create','Add Spatial'):
            # create section record so that the audio index starts here
            self.sectionCreateRecord()
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

    def mapToolsActivatePolygonCapture(self):

        if self.lmbMode == 'Interview':
            # check for keyboard modifier
            modifiers = QtGui.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ControlModifier or self.rapidCapture == True:
                self.copyPrevious = True
            else:
                self.copyPrevious = False
        # use debug track order of calls
        if self.spatialDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # method body
        self.sectionEnableCancel()
        self.currentFeature = 'pl'
        if self.lmbMode == 'Interview' and not self.featureState in ('Create','Add Spatial'):
            # create section record so that the audio index starts here
            self.sectionCreateRecord()
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

    def mapToolsActivateSpatialEdit( self ):

        # use debug track order of calls
        if self.spatialDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
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
        self.sectionEnableCancel(True)
        # check if vector editing
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
        ndta = self.iface.actionNodeTool()
        if ndta.isChecked() == False:
            ndta.trigger()
            
        return(0)
        
    #
    # activate spatial move by creating copy of feature and activating the move tool

    def mapToolsActivateSpatialMove( self ):

        # use debug track order of calls
        if self.spatialDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
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
        self.sectionEnableCancel(True)
        # check if vector editing
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
            self.sectionEnableSaveCancel()
            # set flag
            self.vectorEditing = True
        # activate move tool
        mvta = self.iface.actionMoveFeature()
        if mvta.isChecked() == False:
            mvta.trigger()

        return(0)

    # 
    # place point using custom point tool

    def mapToolsPlacePoint(self, point):

        if self.lmbMode == 'Interview':
            modifiers = QtGui.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ControlModifier:
                self.rapidCapture = True
            else:
                self.rapidCapture = False
        # use debug track order of calls
        if self.spatialDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
                #QgsMessageLog.logMessage(self.featureState)
                #QgsMessageLog.logMessage(str(self.rapidCapture))
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
        sql += "(id,interview_id,section_id,section_code,content_code,date_created,date_modified,geom) "
        sql += "VALUES (%d,%d,%d, " % (self.point_id, self.interview_id, self.section_id)
        sql += "'%s','%s','%s','%s'," %  (self.currentSectionCode,self.currentContentCode,self.section_date_created, self.section_date_modified)
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
        if self.lmbMode == 'Interview':
            # reset state
            if self.featureState == 'Create':
                self.featureState = 'View'
                self.sectionAddEntry()
            else:
                self.featureState = 'View'
            # keep point tool active
            if self.rapidCapture == True:
                #QgsMessageLog.logMessage('rapid capture')
                self.mapToolsActivatePointCapture()
            else:
                self.mapToolsActivatePanTool()
                # select and disable save / cancel
                self.points_layer.select(self.point_id)
                self.sectionDisableSaveCancel()
        else:
            # reset state
            self.featureState = 'View'
            self.mapToolsActivatePanTool()
            # select and disable save / cancel
            self.points_layer.select(self.point_id)
            self.sectionDisableSaveCancel()
        # add to feature status list if needed
        idx = self.cbFeatureStatus.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
        if idx == -1:
            self.cbFeatureStatus.addItem('same as %s' % self.currentSectionCode)

    #
    # place line using custom line tool
    
    def mapToolsPlaceLine(self, line):

        if self.lmbMode == 'Interview':
            modifiers = QtGui.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ControlModifier:
                self.rapidCapture = True
            else:
                self.rapidCapture = False
        # use debug track order of calls
        if self.spatialDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
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
        sql += "(id,interview_id,section_id,section_code,content_code,date_created,date_modified,geom) "
        sql += "VALUES (%d,%d,%d, " % (self.line_id, self.interview_id, self.section_id)
        sql += "'%s','%s','%s','%s'," %  (self.currentSectionCode,self.currentContentCode,self.section_date_created, self.section_date_modified)
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
        if self.lmbMode == 'Interview':
            # reset state
            if self.featureState == 'Create':
                self.featureState = 'View'
                self.sectionAddEntry()
            else:
                self.featureState = 'View'
            # keep point tool active
            if self.rapidCapture == True:
                self.mapToolsActivateLineCapture()
            else:
                self.mapToolsActivatePanTool()
                # select and disable save / cancel
                self.lines_layer.select(self.line_id)
                self.sectionDisableSaveCancel()
        else:
            # reset state
            self.featureState = 'View'
            self.mapToolsActivatePanTool()
            # select and disable save / cancel
            self.lines_layer.select(self.line_id)
            self.sectionDisableSaveCancel()
        # add to feature status list if needed
        idx = self.cbFeatureStatus.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
        if idx == -1:
            self.cbFeatureStatus.addItem('same as %s' % self.currentSectionCode)

    #
    # place polygon using custom polygon tool
    
    def mapToolsPlacePolygon(self, polygon):

        if self.lmbMode == 'Interview':
            modifiers = QtGui.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ControlModifier:
                self.rapidCapture = True
            else:
                self.rapidCapture = False
        # use debug track order of calls
        if self.spatialDebug:
            if self.debugLog == True:
                QgsMessageLog.logMessage(self.myself())
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
        sql += "(id,interview_id,section_id,section_code,content_code,date_created,date_modified,geom) "
        sql += "VALUES (%d,%d,%d, " % (self.polygon_id, self.interview_id, self.section_id)
        sql += "'%s','%s','%s','%s'," %  (self.currentSectionCode,self.currentContentCode,self.section_date_created, self.section_date_modified)
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
        if self.lmbMode == 'Interview':
            # reset state
            if self.featureState == 'Create':
                self.featureState = 'View'
                self.sectionAddEntry()
            else:
                self.featureState = 'View'
            # keep polygonTool active
            if self.rapidCapture == True:
                self.mapToolsActivatePolygonCapture()
            else:
                self.mapToolsActivatePanTool()
                # select and disable save / cancel
                self.polygons_layer.select(self.polygon_id)
                self.sectionDisableSaveCancel()
        else:
            # reset state
            self.featureState = 'View'
            self.mapToolsActivatePanTool()
            # select and disable save / cancel
            self.polygons_layer.select(self.polygon_id)
            self.sectionDisableSaveCancel()
        # add to feature status list if needed
        idx = self.cbFeatureStatus.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
        if idx == -1:
            self.cbFeatureStatus.addItem('same as %s' % self.currentSectionCode)

