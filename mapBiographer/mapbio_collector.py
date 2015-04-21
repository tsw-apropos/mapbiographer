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
from pyspatialite import dbapi2 as sqlite
import os, datetime, time, shutil
import pyaudio, pydub
from ui_mapbio_collector import Ui_mapbioCollector
from mapbio_importer import mapBiographerImporter
from mapbio_navigator import mapBiographerNavigator
from audio_recorder import audioRecorder
from audio_player import audioPlayer
from point_tool import lmbMapToolPoint
from line_tool import lmbMapToolLine
from polygon_tool import lmbMapToolPolygon
import inspect, re

class mapBiographerCollector(QtGui.QDockWidget, Ui_mapbioCollector):

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
        if self.basicDebug or self.editDebug or self.audioDebug or self.spatialDebug:
            self.myself = lambda: inspect.stack()[1][3]
        if self.basicDebug:
            QgsMessageLog.logMessage(self.myself())
        # permitted map scale
        self.maxDenom = 2500000
        self.minDenom = 5000
        self.scaleConnection = False
        self.zoomMessage = 'None'
        self.canDigitize = False
        self.showZoomNotices = False
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
        self.defaultCode = ''
        self.pointCode = ''
        self.lineCode = ''
        self.polygonCode = ''
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
        self.currentPrimaryCode = ''
        self.currentMediaFiles = ''
        self.editLayer = None
        self.previousSectionId = 0
        self.previousPointId = 0
        self.previousLineId = 0
        self.previousPolygonId = 0
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
        QtCore.QObject.connect(self.cbInterviewSelection, QtCore.SIGNAL("currentIndexChanged(int)"), self.interviewSelect)
        # audio
        self.tbMediaPlay.setIcon(QtGui.QIcon(":/plugins/mapbiographer/media_play.png"))
        QtCore.QObject.connect(self.tbMediaPlay, QtCore.SIGNAL("clicked()"), self.audioPlayPause)
        self.tbAudioSettings.setMenu(QtGui.QMenu(self.tbAudioSettings))
        # set shortcut at application level so that not over-ridden by QGIS settings
        self.short = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Space"), self)
        self.short.setContext(QtCore.Qt.ApplicationShortcut)
        self.short.activated.connect(self.audioPlayPause)
        #
        QtCore.QObject.connect(self.cbRecordAudio, QtCore.SIGNAL("currentIndexChanged(int)"), self.audioTest)
        # import functions
        QtCore.QObject.connect(self.pbImportFeatures, QtCore.SIGNAL("clicked()"), self.importFeatures)
        QtCore.QObject.connect(self.pbImportAudio, QtCore.SIGNAL("clicked()"), self.importAudio)
        QtCore.QObject.connect(self.pbRenumberSections, QtCore.SIGNAL("clicked()"), self.sectionRenumber)
        # interview controls
        QtCore.QObject.connect(self.pbStart, QtCore.SIGNAL("clicked()"), self.interviewStart)
        QtCore.QObject.connect(self.pbPause, QtCore.SIGNAL("clicked()"), self.interviewPause)
        QtCore.QObject.connect(self.pbFinish, QtCore.SIGNAL("clicked()"), self.interviewFinish)
        # section controls
        # widgets
        QtCore.QObject.connect(self.lwSectionList, QtCore.SIGNAL("itemSelectionChanged()"), self.sectionSelect)
        QtCore.QObject.connect(self.spMediaStart, QtCore.SIGNAL("valueChanged(int)"), self.audioSetStartValue)
        QtCore.QObject.connect(self.spMediaEnd, QtCore.SIGNAL("valueChanged(int)"), self.audioSetEndValue)
        QtCore.QObject.connect(self.hsSectionMedia, QtCore.SIGNAL("valueChanged(int)"), self.audioUpdateCurrentPosition)
        QtCore.QObject.connect(self.cbSectionSecurity, QtCore.SIGNAL("currentIndexChanged(int)"), self.sectionEnableSaveCancel)
        QtCore.QObject.connect(self.cbFeatureSource, QtCore.SIGNAL("currentIndexChanged(int)"), self.sectionFeatureSourceChanged)
        QtCore.QObject.connect(self.cbDateTime, QtCore.SIGNAL("currentIndexChanged(int)"), self.sectionEnableSaveCancel)
        QtCore.QObject.connect(self.cbTimeOfYear, QtCore.SIGNAL("currentIndexChanged(int)"), self.sectionEnableSaveCancel)
        QtCore.QObject.connect(self.pteSectionTags, QtCore.SIGNAL("textChanged()"), self.sectionEnableSaveCancel)
        QtCore.QObject.connect(self.pteSectionNote, QtCore.SIGNAL("textChanged()"), self.sectionEnableSaveCancel)
        QtCore.QObject.connect(self.pteSectionText, QtCore.SIGNAL("textChanged()"), self.sectionEnableSaveCancel)
        QtCore.QObject.connect(self.lwProjectCodes, QtCore.SIGNAL("itemClicked(QListWidgetItem*)"), self.sectionAddRemoveCodes)
        # section reordering
        QtCore.QObject.connect(self.tbMoveUp, QtCore.SIGNAL("clicked()"), self.sectionMoveUp)
        QtCore.QObject.connect(self.tbMoveDown, QtCore.SIGNAL("clicked()"), self.sectionMoveDown)
        QtCore.QObject.connect(self.tbSort, QtCore.SIGNAL("clicked()"), self.sectionSort)
        # buttons
        QtCore.QObject.connect(self.pbSaveSection, QtCore.SIGNAL("clicked()"), self.sectionSaveEdits)
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

        # final prep for transcribing interviews
        # open project
        result = self.settingsRead()
        if result == 0:
            result, message = self.transcriberOpen()
            if result <> 0:
                QtGui.QMessageBox.information(self, 'LMB Notice',
                    message, QtGui.QMessageBox.Ok)
                self.transcriberClose()
            else:
                # set mode
                self.setLMBMode()
        else:
            QtGui.QMessageBox.information(self, 'LMB Notice',
            'Map Biographer Settings Error. Please correct. Closing.', QtGui.QMessageBox.Ok)
            self.transcriberClose()

    #
    # set LMB mode - set mode and and visibility and initial status of controls

    def setLMBMode(self):

        if self.basicDebug:
            QgsMessageLog.logMessage(self.myself())
        self.interviewState = "Load"
        self.lblTimer.setText("00:00:00")
        if self.cbMode.currentText() == 'Import Interview':
            self.lmbMode = 'Import'
            if self.scaleConnection == True:
                QtCore.QObject.disconnect(self.canvas, QtCore.SIGNAL("scaleChanged(double)"), self.mapToolsScaleNotification)
            # hide audio recording
            self.cbRecordAudio.setVisible(False)
            # display section reordering
            self.tbMoveUp.setVisible(True)
            self.tbMoveDown.setVisible(True)
            self.tbSort.setVisible(True)
            # display media player
            self.tbMediaPlay.setVisible(True)
            self.hsSectionMedia.setVisible(True)
            # hide timer
            self.lblTimeOfDay.setVisible(False)
            self.vlLeftOfTimer.setVisible(True)
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
            self.pbFinish.setEnabled(True)
            # show and enable import
            self.pbImportFeatures.setVisible(True)
            self.pbImportFeatures.setEnabled(True)
            self.pbImportAudio.setVisible(True)
            self.pbImportAudio.setEnabled(True)
            self.pbRenumberSections.setVisible(True)
            self.pbRenumberSections.setEnabled(True)
            # enable photos
            self.tpPhotos.setEnabled(True)
            # show tabs
            self.twSectionContent.tabBar().setVisible(True)
            # enable section controls and non-spatial insert
            self.frSectionControls.setEnabled(True)
            self.tbNonSpatial.setEnabled(True)
        elif self.cbMode.currentText() == 'Transcribe':
            self.lmbMode = 'Transcribe'
            if self.scaleConnection == True:
                QtCore.QObject.disconnect(self.canvas, QtCore.SIGNAL("scaleChanged(double)"), self.mapToolsScaleNotification)
            # hide audio recording
            self.cbRecordAudio.setVisible(False)
            # hide section reordering
            self.tbMoveUp.setVisible(False)
            self.tbMoveDown.setVisible(False)
            self.tbSort.setVisible(False)
            # display media player
            self.tbMediaPlay.setVisible(True)
            self.hsSectionMedia.setVisible(True)
            # hide timer
            self.lblTimeOfDay.setVisible(False)
            self.vlLeftOfTimer.setVisible(True)
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
            self.pbImportAudio.setVisible(False)
            self.pbRenumberSections.setVisible(False)
            # show tabs
            self.twSectionContent.tabBar().setVisible(True)
            # enable photos
            self.tpPhotos.setEnabled(True)
            # enable section controls and non-spatial insert
            self.frSectionControls.setEnabled(True)
            self.tbNonSpatial.setEnabled(True)
        elif self.cbMode.currentText() == 'Conduct Interview':
            self.lmbMode = 'Interview'
            # control digitizing scale
            QtCore.QObject.connect(self.canvas, QtCore.SIGNAL("scaleChanged(double)"), self.mapToolsScaleNotification)
            self.scaleConnection = True
            # show audio recording
            self.cbRecordAudio.setVisible(True)
            # hide section reordering
            self.tbMoveUp.setVisible(False)
            self.tbMoveDown.setVisible(False)
            self.tbSort.setVisible(False)
            # hide media player
            self.tbMediaPlay.setVisible(False)
            self.hsSectionMedia.setVisible(False)
            # show timer
            self.lblTimeOfDay.setVisible(True)
            self.vlLeftOfTimer.setVisible(True)
            self.lblTimer.setVisible(True)
            # hide start and end media times
            self.lblMediaStart.setVisible(False)
            self.spMediaStart.setVisible(False)
            self.lblMediaEnd.setVisible(False)
            self.spMediaEnd.setVisible(False)
            # show start, pause and finish
            self.pbStart.setVisible(True)
            self.pbStart.setEnabled(True)
            self.pbPause.setVisible(True)
            self.pbFinish.setVisible(True)
            self.pbFinish.setDisabled(True)
            # hide import
            self.pbImportFeatures.setVisible(False)
            self.pbImportAudio.setVisible(False)
            self.pbRenumberSections.setVisible(False)
            # hide tabs
            self.twSectionContent.tabBar().setVisible(False)
            self.frSectionControls.setDisabled(True)
            # disable section controls
            self.tbNonSpatial.setDisabled(True)
        try:
            if self.points_layer <> None or self.lines_layer <> None:
                self.interviewUnload()
        except:
            pass 
        self.audioLoadDeviceList()
        self.interviewLoadList()
        # activate pan tool
        self.interviewState = "View"

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
            QgsMessageLog.logMessage(self.myself())
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
            QgsMessageLog.logMessage(self.myself())
        # method body
        # break connections to custom tools
        result = QtCore.QObject.disconnect(self.pointTool, QtCore.SIGNAL("rbFinished(QgsGeometry*)"), self.mapToolsPlacePoint)
        result = QtCore.QObject.disconnect(self.lineTool, QtCore.SIGNAL("rbFinished(QgsGeometry*)"), self.mapToolsPlaceLine)
        result = QtCore.QObject.disconnect(self.polygonTool, QtCore.SIGNAL("rbFinished(QgsGeometry*)"), self.mapToolsPlacePolygon)
        result = QtCore.QObject.disconnect(self.tbPan, QtCore.SIGNAL("clicked()"), self.mapToolsActivatePanTool)


    #####################################################
    #                     data import                   #
    #####################################################

    #
    # import features

    def importFeatures(self):

        # use debug track order of calls
        if self.basicDebug:
            QgsMessageLog.logMessage(self.myself())
        # disable interface
        self.frInterviewSelection.setDisabled(True)
        self.frInterviewActions.setDisabled(True)
        self.frSectionControls.setDisabled(True)
        # Create the dialog (after translation) and keep reference
        s = QtCore.QSettings()
        dirName = s.value('mapBiographer/projectDir')
        self.importDialog = mapBiographerImporter(self.iface, self.conn, self.cur, dirName)
        # show the dialog
        self.importDialog.show()
        # Run the dialog event loop
        result = self.importDialog.exec_()
        dataDict = self.importDialog.returnData()
        if dataDict <> {}:
            # do import
            # open layer
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
                # check projection
                crsSrc = inputLayer.crs()    
                crsDest = QgsCoordinateReferenceSystem(3857)  
                coordTransform = QgsCoordinateTransform(crsSrc, crsDest)
                # begin importing
                if inputLayer.geometryType() == QGis.Point:
                    self.currentFeature = 'pt'
                elif inputLayer.geometryType() == QGis.Line:
                    self.currentFeature = 'ln'
                elif inputLayer.geometryType() == QGis.Polygon:
                    self.currentFeature = 'pl'
                features = inputLayer.getFeatures()
                cnt = inputLayer.featureCount()
                x = 0
                lastPercent = 0.0
                progress = QtGui.QProgressDialog('Importing Features','Cancel',0,100,self)
                progress.setWindowTitle('Import progress')
                progress.setWindowModality(QtCore.Qt.WindowModal)
                for feature in features:
                    x += 1
                    if (float(x)/cnt*100)+5 > lastPercent:
                        lastPercent = float(x)/cnt*100
                        progress.setValue(lastPercent)
                        if progress.wasCanceled():
                            break
                    geom = feature.geometry()
                    geom.transform(coordTransform)
                    attrs = feature.attributes()
                    self.sectionCreateRecord()
                    #self.conn.commit()
                    sql = "UPDATE interview_sections SET "
                    if dataDict['sectionCode'] <> '--Create On Import--':
                        idx = fieldDict[dataDict['sectionCode']][0]
                        sql += 'section_code = "%s", ' % str(attrs[idx])
                        self.currentSectionCode = str(attrs[idx])
                        if dataDict['primaryCode'] <> '--None--':
                            idx = fieldDict[dataDict['primaryCode']][0]
                            sql += 'primary_code = "%s", ' % str(attrs[idx])
                            self.currentPrimaryCode = str(attrs[idx])
                        else:
                            # since primary code was not specified
                            # extract from section code
                            pc = re.findall(r'\D+', str(attrs[idx]))
                            if len(pc) > 0:
                                pc = pc[0]
                            else:
                                pc = self.defaultCode
                            sql += 'primary_code = "%s", ' % pc
                            self.currentPrimaryCode = pc
                    else:
                        # creating section code  on import
                        if dataDict['primaryCode'] <> '--None--':
                            # use specified primary code
                            idx = fieldDict[dataDict['primaryCode']][0]
                            sql += 'primary_code = "%s", ' % str(attrs[idx])
                            self.currentPrimaryCode = str(attrs[idx])
                            self.currentSectionCode = "%s%04d" % (self.currentPrimaryCode,self.currentSequence)
                            sql += 'section_code = "%s", ' % self.currentSectionCode
                        # note that if no section or primary code field then
                        # defaults applied
                    if dataDict['security'] <> '--None--':
                        idx = fieldDict[dataDict['security']][0]
                        sql += 'data_security = "%s", ' % str(attrs[idx])
                    if dataDict['contentCodes'] <> '--None--':
                        idx = fieldDict[dataDict['contentCodes']][0]
                        sql += 'content_codes = "%s", ' % str(attrs[idx])
                    if dataDict['tags'] <> '--None--':
                        idx = fieldDict[dataDict['tags']][0]
                        sql += 'tags = "%s", ' % str(attrs[idx])
                    if dataDict['datesTimes'] <> '--None--':
                        idx = fieldDict[dataDict['datesTimes']][0]
                        sql += 'date_time = "%s", ' % str(attrs[idx])
                    if dataDict['timeOfYear'] <> '--None--':
                        idx = fieldDict[dataDict['timeOfYear']][0]
                        sql += 'time_of_year = "%s", ' % str(attrs[idx])
                    if dataDict['notes'] <> '':
                        lst = dataDict['notes'].split(',')
                        outText = ''
                        for fld in lst:
                            idx = fieldDict[fld][0]
                            outText = outText + str(attrs[idx]) + '\n'
                        sql += 'note = "%s", ' % outText
                    if dataDict['sections'] <> '':
                        lst = dataDict['sections'].split(',')
                        outText = ''
                        for fld in lst:
                            idx = fieldDict[fld][0]
                            outText = outText + str(attrs[idx]) + '\n'
                        sql += 'section_text = "%s", ' % outText
                    sql += 'spatial_data_source = "%s", ' % dataDict['spatialDataSource']
                    sql += 'spatial_data_scale = "%s" ' % dataDict['spatialDataScale']
                    sql += "WHERE interview_id = %d AND id = '%s' " % (self.interview_id, self.section_id)
                    self.cur.execute(sql)
                    if self.currentFeature == 'pt':
                        self.point_id = self.previousPointId + 1
                        self.previousPointId = self.point_id
                        geom.convertToMultiType()
                        sql = "INSERT INTO points "
                        sql += "(id,interview_id,section_id,section_code,content_code,date_created,date_modified,geom) "
                        sql += "VALUES (%d,%d,%d, " % (self.point_id, self.interview_id, self.section_id)
                        sql += "'%s','%s','%s','%s'," %  (self.currentSectionCode,self.currentPrimaryCode,self.section_date_created, self.section_date_modified)
                        sql += "GeomFromText('%s',3857));" % geom.exportToWkt()
                        self.cur.execute(sql)
                    elif self.currentFeature == 'ln':
                        self.line_id = self.previousLineId + 1
                        self.previousLineId = self.line_id
                        geom.convertToMultiType()
                        # insert into database
                        sql = "INSERT INTO lines "
                        sql += "(id,interview_id,section_id,section_code,content_code,date_created,date_modified,geom) "
                        sql += "VALUES (%d,%d,%d, " % (self.line_id, self.interview_id, self.section_id)
                        sql += "'%s','%s','%s','%s'," %  (self.currentSectionCode,self.currentPrimaryCode,self.section_date_created, self.section_date_modified)
                        sql += "GeomFromText('%s',3857));" % geom.exportToWkt()
                        QgsMessageLog.logMessage(sql)
                        self.cur.execute(sql)
                    elif self.currentFeature == 'pl':
                        self.polygon_id = self.previousPolygonId + 1
                        self.previousPolygonId = self.polygon_id
                        geom.convertToMultiType()
                        # insert into database
                        sql = "INSERT INTO polygons "
                        sql += "(id,interview_id,section_id,section_code,content_code,date_created,date_modified,geom) "
                        sql += "VALUES (%d,%d,%d, " % (self.polygon_id, self.interview_id, self.section_id)
                        sql += "'%s','%s','%s','%s'," %  (self.currentSectionCode,self.currentPrimaryCode,self.section_date_created, self.section_date_modified)
                        sql += "GeomFromText('%s',3857));" % geom.exportToWkt()
                        self.cur.execute(sql)
                self.conn.commit()
                self.iface.messageBar().clearWidgets()
                # reset to view state and reload
                self.interviewUnload()
                self.interviewLoad()
                self.interviewState = 'View'
        # enable interface
        self.frInterviewSelection.setEnabled(True)
        self.frInterviewActions.setEnabled(True)
        self.frSectionControls.setEnabled(True)
                
    #
    # import audio

    def importAudio(self):

        # use debug track order of calls
        if self.basicDebug:
            QgsMessageLog.logMessage(self.myself())
        s = QtCore.QSettings()
        dirName = s.value('mapBiographer/projectDir')
        fname = QtGui.QFileDialog.getOpenFileName(self, 'Select Audio File', '.', '*.wav')
        if os.path.exists(fname):
            # get audio file duration
            audioLen = pydub.AudioSegment.from_file(fname).duration_seconds
            audioMax = round(audioLen + 0.5)
            # split into equal parts
            secCnt = self.lwSectionList.count()
            segLength = int(round(float(audioMax) / secCnt))
            if segLength == 0:
                messageText = 'The audio file is too short for the number of sections. '
                messageText += 'Are you confident this is the correct file? '
                messageText += 'Do you wish to proceed with the import?'
                response = QtGui.QMessageBox.warning(self, 'Warning',
                   messageText, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
                if response == QtGui.QMessageBox.Yes:
                    segLength = 1
            if segLength >= 1:
                # copy the file
                destFile = self.cbInterviewSelection.currentText() + '.wav'
                destPath = os.path.join(dirName,destFile)
                shutil.copyfile(fname, destPath)
                # get section ids
                sql = "SELECT id, sequence_number FROM interview_sections "
                sql += "WHERE interview_id = %d ORDER BY sequence_number;" % self.interview_id
                rs = self.cur.execute(sql)
                secIdList = rs.fetchall()
                audioIdx = 0
                audioAtEnd = False
                x = 0
                for secId in secIdList:
                    x += 1
                    if not audioAtEnd:
                        QgsMessageLog.logMessage('x: %d of %d' % (x,secCnt))
                        QgsMessageLog.logMessage('start: %d end: %d of %d' % (audioIdx, audioIdx+segLength, audioMax))
                        if audioIdx + segLength >= audioMax:
                            segLength = audioMax - audioIdx
                            audioAtEnd = True
                        if x == secCnt:
                            segLength = audioMax - audioIdx
                            QgsMessageLog.logMessage('match found')
                        QgsMessageLog.logMessage(str(segLength))
                        sql = "UPDATE interview_sections SET "
                        sql += "media_start_time = '%s', " % self.seconds2timeString(audioIdx)
                        sql += "media_end_time = '%s' " % self.seconds2timeString(audioIdx + segLength)
                        sql += "WHERE interview_id = %d and id = %d " % (self.interview_id, secId[0])
                        self.cur.execute(sql)
                        audioIdx = audioIdx + segLength
                    else:
                        sql = "UPDATE interview_sections SET "
                        sql += "media_start_time = '00:00:00', "
                        sql += "media_end_time = '00:00:00' " 
                        sql += "WHERE interview_id = %d and id = %d " % (self.interview_id, secId[0])
                        self.cur.execute(sql)
                self.conn.commit()
                self.interviewUnload()
                self.interviewLoad()
            

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
            QgsMessageLog.logMessage(self.myself())
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
        rv = s.value('mapBiographer/maxScale')
        if rv <>  '':
            temp = int(rv.strip('"').strip("'").split(':')[1].replace(',',''))
            self.minDenom = temp
        rv = s.value('mapBiographer/minScale')
        if rv <>  '':
            temp = int(rv.strip('"').strip("'").split(':')[1].replace(',',''))
            self.maxDenom = temp
        rv = s.value('mapBiographer/zoomNotices')
        if rv <>  '' and rv == 'Yes':
            self.showZoomNotices = True
        else:
            self.showZoomNotices = False
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
            QgsMessageLog.logMessage(self.myself())
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
            
        # method body
        self.projectLoading = True
        # connect to database
        self.conn = sqlite.connect(os.path.join(self.projectDir,self.projectDB))
        self.cur = self.conn.cursor()
        #
        # project info and defaults
        sql = 'SELECT id,code,content_codes,dates_and_times,times_of_year,default_codes FROM project;'
        rs = self.cur.execute(sql)
        projData = rs.fetchall()
        # basic setup
        self.leProjectCode.setText(projData[0][1])
        # content codes
        self.project_codes = []
        self.lwProjectCodes.setMouseTracking(True)
        self.lwProjectCodes.clear()
        codeList = projData[0][2].split('\n')
        codeList.sort()
        for item in codeList:
            if item <> '':
                code, defn = item.split('=')
                self.project_codes.append(code.strip())
                tempItem = QtGui.QListWidgetItem(code.strip())
                tempItem.setToolTip(defn.strip())
                self.lwProjectCodes.addItem(tempItem)
        # set default codes
        codeDefaults = projData[0][5]
        if codeDefaults is None or codeDefaults == '':
            self.projectLoading = False
            return(1, 'Default codes not set. Closing.')
        else:
            codeDefaults = projData[0][5]
            dCodes = projData[0][5].split('|||')
            for dc in dCodes:
                dDef,dCode = dc.split('||')
                if dDef.strip() == 'dfc' and dCode in self.project_codes:
                    self.defaultCode = dCode
                if dDef.strip() == 'ptc' and dCode in self.project_codes:
                    self.pointCode = dCode
                if dDef.strip() == 'lnc' and dCode in self.project_codes:
                    self.lineCode = dCode
                if dDef.strip() == 'plc' and dCode in self.project_codes:
                    self.polygonCode = dCode
            if self.defaultCode == '':
                self.projectLoading = False
                return(1, 'Default codes are not set. Closing.')
            if self.pointCode == '':
                self.pointCode = self.defaultCode
            if self.lineCode == '':
                self.lineCode = self.defaultCode
            if self.polygonCode == '':
                self.polygonCode = self.defaultCode
        # section references
        self.cbFeatureSource.clear()
        self.cbFeatureSource.addItems(['none','is unique'])
        self.cbFeatureSource.setCurrentIndex(0)
        # time periods
        self.project_date_time = ['R','U','N']
        self.cbDateTime.clear()
        self.cbDateTime.addItems(['Refused','Unknown','Not Recorded'])
        if projData[0][3] <> None:
            timeList = projData[0][3].split('\n')
            for item in timeList:
                if item <> '':
                    defn,desc = item.split('=')
                    self.project_date_time.append(defn.strip())
                    self.cbDateTime.addItem(desc.strip())
        self.cbDateTime.setCurrentIndex(1)
        # annnual variation
        self.project_time_of_year = ['R','U','N','SP']
        self.cbTimeOfYear.clear()
        self.cbTimeOfYear.addItems(['Refused','Unknown','Not Recorded','Sporadic'])
        if projData[0][4] <> None:
            seasonList = projData[0][4].split('\n')
            for item in seasonList:
                if item <> '':
                    defn,desc = item.split('=')
                    self.project_time_of_year.append(defn.strip())
                    self.cbTimeOfYear.addItem(desc.strip())
        self.cbTimeOfYear.setCurrentIndex(1)
        # security
        self.project_security = ['PU','CO','PR']
        self.cbSectionSecurity.clear()
        self.cbSectionSecurity.addItems(['Public','Community','Private'])
        self.cbSectionSecurity.setCurrentIndex(0)
        #
        # map parameters
        # load QGIS project
        if QgsProject.instance().fileName() <> self.qgsProject:
            self.iface.newProject()
            QgsProject.instance().read(QtCore.QFileInfo(self.qgsProject))
        # gather information about what is available in the QGIS project
        self.projectLoading = False

        return(0, "Be Happy")

    #
    # load interview list into combobox
    
    def interviewLoadList(self):

        if self.projectLoading == False:
            # use debug track order of calls
            if self.basicDebug:
                QgsMessageLog.logMessage(self.myself())
            failMessage = 'No interviews could be found'
            # method body
            if self.lmbMode == 'Interview':
                sql = "SELECT a.id, a.code FROM interviews a "
                sql += "WHERE a.data_status = 'N' AND a.id NOT IN "
                sql += "(SELECT DISTINCT interview_id FROM interview_sections);"
                rs = self.cur.execute(sql)
                intvData = rs.fetchall()
            elif self.lmbMode == 'Import':
                sql = "SELECT a.id, a.code FROM interviews a "
                sql += "WHERE a.data_status = 'N';"
                rs = self.cur.execute(sql)
                intvData = rs.fetchall()
            else:
                sql = "SELECT a.id, a.code FROM interviews a "
                sql += "WHERE a.data_status = 'C';"
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
                    self.frSectionControls.setDisabled(True)
                    self.frInterviewActions.setDisabled(True)
            else:
                self.frInterviewActions.setEnabled(True)
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
                    self.pbStart.setEnabled(True)

    #
    # select interview 

    def interviewSelect(self, cIndex):

        # use debug track order of calls
        if self.basicDebug:
            QgsMessageLog.logMessage(self.myself())
        # method body
        #
        # remove old interview if loaded
        if self.lwSectionList.count() > 0:
            self.interviewUnload()
        if len(self.intvList) == 0:
            self.interview_id = None
            self.interview_code = ''
            self.pteParticipants.setPlainText('')
            self.tbMediaPlay.setDisabled(True)
            self.hsSectionMedia.setDisabled(True)
            self.mediaState = 'disabled'
        else:
            self.pteParticipants.setPlainText(self.intvList[cIndex][2])
            self.interview_id = self.intvList[cIndex][0]
            self.interview_code = self.intvList[cIndex][1]
            self.interviewLoad()
            
    #
    # load interview

    def interviewLoad(self):

        # use debug track order of calls
        if self.basicDebug:
            QgsMessageLog.logMessage(self.myself())
        # method body
        # get path for audio file and create prefix
        self.interviewState == 'Load'
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
            self.maxCodeNumber = 0
        else:
            self.maxCodeNumber = rsData[0][0]
        # load interview map layers
        self.interviewAddMapLayers()
        # load interview sections and update link list for cbFeatureSource
        sql = "SELECT id, section_code, geom_source, sequence_number FROM interview_sections "
        sql += "WHERE interview_id = %d ORDER BY sequence_number;" % self.interview_id
        rs = self.cur.execute(sql)
        sectionList = rs.fetchall()
        self.cbFeatureSource.clear()
        self.cbFeatureSource.addItems(['none','unique'])
        self.lwSectionList.clear()
        for section in sectionList:
            self.lwSectionList.addItem(section[1])
            if section[2] in ('pt','ln','pl'):
                self.cbFeatureSource.addItem('same as %s' % section[1])
        # enable navigation
        if len(sectionList) > 0:
            self.twSectionContent.setEnabled(True)
            self.lwProjectCodes.setEnabled(True)
            self.lwSectionList.setCurrentItem(self.lwSectionList.item(0))
        else:
            self.twSectionContent.setDisabled(True)
            self.lwProjectCodes.setDisabled(True)
        # refresh navigator panel
        self.navigatorPanel.loadLayers()
        self.interviewState = 'View'
        if self.lwSectionList.count() > 0:
            self.lwSectionList.setItemSelected(self.lwSectionList.item(0),True)
            self.sectionSelect()
        self.mapToolsActivatePanTool()
        self.navigatorPanel.zoomToStudyArea()
        
    #
    # unload interview

    def interviewUnload(self):

        # use debug track order of calls
        if self.basicDebug:
            QgsMessageLog.logMessage(self.myself())
        # method body
        self.interviewState = 'Unload'
        # clear interface when an interview is selected
        self.cbFeatureSource.clear()
        self.cbFeatureSource.addItems(['none','unique'])
        # clear section list
        self.lwSectionList.clear()
        # remove layers if they exist
        self.interviewRemoveMapLayers()

    #
    # close trancription interface
    
    def transcriberClose(self):

        # use debug track order of calls
        if self.basicDebug:
            QgsMessageLog.logMessage(self.myself())
        # check if audio is playing and stop it
        if self.mediaState == 'playing':
            self.audioPlayPause()
        # method body
        if self.scaleConnection == True:
            QtCore.QObject.disconnect(self.canvas, QtCore.SIGNAL("scaleChanged(double)"), self.mapToolsScaleNotification)
        # close navigator
        try:
            self.navigatorPanel.close()
        except:
            pass
        # unload interview
        try:
            self.interviewUnload()
        except:
            pass
        # disconnect map tools
        try:
            self.mapToolsDisconnect()
        except:
            pass
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

    def interviewAddMapLayers(self):

        if self.basicDebug:
            QgsMessageLog.logMessage(self.myself())
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
        symbolLayer.setFillColor(QtGui.QColor('#ff7800'))
        symbolLayer.setBorderColor(QtGui.QColor('#717272'))
        symbolLayer.setBorderWidth(0.6)
        QgsMapLayerRegistry.instance().addMapLayer(self.polygons_layer)
        # add to overview
        #self.iface.setActiveLayer(self.polygons_layer)
        #self.iface.actionAddToOverview().activate(0)
        # set label
        palyrPolygons = QgsPalLayerSettings()
        palyrPolygons.readFromLayer(self.polygons_layer)
        palyrPolygons.enabled = True
        palyrPolygons.fieldName = 'section_code'
        palyrPolygons.setDataDefinedProperty(QgsPalLayerSettings.Size,True,True,'11','')
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
        symbol.setColor(QtGui.QColor('#ff7800'))
        symbol.setWidth(0.6)
        QgsMapLayerRegistry.instance().addMapLayer(self.lines_layer)
        # add to overview
        #self.iface.setActiveLayer(self.lines_layer)
        #self.iface.actionAddToOverview().activate(0)
        # set label
        palyrLines = QgsPalLayerSettings()
        palyrLines.readFromLayer(self.lines_layer)
        palyrLines.enabled = True
        palyrLines.fieldName = 'section_code'
        palyrLines.placement= QgsPalLayerSettings.Line
        palyrLines.placementFlags = QgsPalLayerSettings.AboveLine
        palyrLines.setDataDefinedProperty(QgsPalLayerSettings.Size,True,True,'11','')
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
        symbol.setColor(QtGui.QColor('#ff7800'))
        symbol.setAlpha(0.5)
        QgsMapLayerRegistry.instance().addMapLayer(self.points_layer)
        # add to overview
        #self.iface.setActiveLayer(self.points_layer)
        #self.iface.actionAddToOverview().activate(0)
        # set label
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

    def interviewRemoveMapLayers(self):

        if self.basicDebug:
            QgsMessageLog.logMessage(self.myself())
        try:
            lyrs = self.iface.mapCanvas().layers()
            #QgsMessageLog.logMessage('lyr count %d' % len(lyrs))
            for lyr in lyrs:
                if lyr.name() in ('lmb_points','lmb_lines','lmb_polygons'):
                    # NOTE: Set active so that another layer does not get removed
                    #       from overview window when this layer is removed
                    self.iface.setActiveLayer(lyr)
                    self.iface.actionAddToOverview().activate(0)
                    QgsMapLayerRegistry.instance().removeMapLayer(lyr.id())
        except:
            pass


    #####################################################
    #               audio operations                    #
    #####################################################

    #
    # audio set start value

    def audioSetStartValue(self):

        if self.featureState <> 'Load':
            # use debug track order of calls
            if self.editDebug:
                QgsMessageLog.logMessage(self.myself())
            if self.spMediaStart.value() > self.spMediaEnd.value():
                self.spMediaStart.setValue(self.spMediaEnd.value())
            if self.pbSaveSection.isEnabled() == False:
                self.sectionEnableSaveCancel()

    #
    # audio set end value

    def audioSetEndValue(self):

        if self.featureState <> 'Load':
            # use debug track order of calls
            if self.editDebug:
                QgsMessageLog.logMessage(self.myself())
            if self.spMediaEnd.value() < self.spMediaStart.value():
                self.spMediaEnd.setValue(self.spMediaStart.value())
            if self.pbSaveSection.isEnabled() == False:
                self.sectionEnableSaveCancel()

    #
    # load audio device list

    def audioLoadDeviceList(self):

        # use debug track order of calls
        if self.audioDebug:
            QgsMessageLog.logMessage(self.myself())
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
                self.setWindowTitle('LMB Collector - (Audio: %s) - Recording Disabled' % self.audioDeviceName)
            else:
                self.setWindowTitle('LMB Collector - (Audio: %s)'  % self.audioDeviceName)
        else:
            if self.lmbMode == 'Interview':
                self.setWindowTitle('LMB Collector - (No Audio Found) - Recording Disabled')
            else:
                self.setWindowTitle('LMB Collector - (No Audio Found)')

    #
    # select audio device for recording or playback

    def audioSelectDevice(self,deviceIndex):

        # use debug track order of calls
        if self.audioDebug:
            QgsMessageLog.logMessage(self.myself())
        # method body
        self.audioDeviceIndex = deviceIndex
        for x in range(len(self.deviceList)):
            if self.deviceList[x][0] == self.audioDeviceIndex:
                self.audioDeviceName = self.deviceList[x][1]
                break
        # set title
        if self.lmbMode == 'Interview':
            self.setWindowTitle('LMB Collector - (Audio Device: %s) - Recording Disabled' % self.audioDeviceName)
        else:
            self.setWindowTitle('LMB Collector - (Audio Device: %s)'  % self.audioDeviceName)
        # reset recording state
        self.cbRecordAudio.setCurrentIndex(0)

    #
    # play audio during transcript and import mode

    def audioStartPlayback(self):

        # use debug track order of calls
        if self.audioDebug:
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

    def audioPlayPause(self):

        # use debug track order of calls
        if self.audioDebug:
            QgsMessageLog.logMessage(self.myself())
        # method body
        if self.tbMediaPlay.isEnabled():
            if self.mediaState == 'paused':
                self.audioStartPlayback()
            elif self.mediaState == 'playing':
                self.audioStopPlayback()

    #
    # stop audio playback

    def audioStopPlayback(self):
        
        # use debug track order of calls
        if self.audioDebug:
            QgsMessageLog.logMessage(self.myself())
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
        if self.lmbMode in ('Import','Transcribe'):
            m, s = divmod(self.audioCurrentPosition, 60)
            h, m = divmod(m, 60)
            timerText =  "%02d:%02d:%02d" % (h, m, s)
            self.lblTimer.setText(timerText)

    #
    # update audio status during playback

    def audioUpdateStatus(self, statusMessage):

        # use debug track order of calls
        if self.audioDebug:
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
    # test microphone

    def audioTest(self):

        # use debug track order of calls
        if self.audioDebug:
            QgsMessageLog.logMessage(self.myself())
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
                self.setWindowTitle('LMB Collector - (Audio Device: %s) - Recording Enabled' % self.audioDeviceName)
        else:
            self.recordAudio = False
            # no audio recording
            self.pbStart.setEnabled(True)
            if len(self.deviceList) > 0:
                self.setWindowTitle('LMB Collector - (Audio Device: %s) - Recording Disabled' % self.audioDeviceName)
            else:
                self.setWindowTitle('LMB Collector - (No Audio Device Found) - Recording Disabled')

    #
    # notify of audio status during recording

    def audioNotifyStatus(self, statusMessage):
    
        self.setWindowTitle('LMB Collector - (Audio Device: %s) - %s' % (self.audioDeviceName,statusMessage))
        
    #
    # notify of audio error - for debugging purposes

    def audioNotifyError(self, e, exception_string):

        # use debug track order of calls
        if self.audioDebug:
            QgsMessageLog.logMessage(self.myself())
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
            QgsMessageLog.logMessage(self.myself())
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

    def audioStopConsolidate(self):
        
        # use debug track order of calls
        if self.audioDebug:
            QgsMessageLog.logMessage(self.myself())
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
    # set interview defaults

    def interviewSetDefaults(self):

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
        self.currentPrimaryCode = ''
        self.previousPrimaryCode = ''
        self.previousSecurity = 'PU'
        self.previousContentCodes = ''
        self.previousTags = ''
        self.previousDateTime = 'U'
        self.previousTimeOfYear = 'U'
        self.previousNote = ''
        self.currentFeature = 'ns'
        self.selectedCodeCount = 0
        self.maxCodeNumber = 0
        # set audio section
        self.audioSection = 1
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

    #
    # start interview

    def interviewStart(self):

        # use debug track order of calls
        if self.basicDebug:
            QgsMessageLog.logMessage(self.myself())
        # method body
        self.interviewSetDefaults()
        #
        # enable section edit controls
        self.frSectionControls.setEnabled(True)
        self.frInterviewSelection.setDisabled(True)
        if self.cbMode.currentText() == 'Conduct Interview':
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
            # set interview state
            self.interviewState = 'Running'
            # create a new section at the start of interview 
            # to capture introductory remarks
            self.sectionCreateNonSpatial()
            self.mapToolsScaleNotification()

    #
    # pause and start interview

    def interviewPause(self):

        # use debug track order of calls
        if self.basicDebug:
            QgsMessageLog.logMessage(self.myself())
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
            QgsMessageLog.logMessage(self.myself())
        # method body
        # set state
        self.copyPrevious = False
        self.rapidCapture = False
        self.zoomToFeature = False
        self.interviewState = 'Finished'
        # reset tools
        self.canvas.unsetMapTool(self.canvas.mapTool())
        # clean up
        if self.cbMode.currentText() == 'Conduct Interview':
            # disable pause and finish
            self.pbFinish.setDisabled(True)
            self.pbPause.setDisabled(True)
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
            sql += "data_status = 'C' "
            sql += "WHERE id = %d; " % self.interview_id
            self.cur.execute(sql)
            self.conn.commit()
        elif self.cbMode.currentText() == 'Import Interview':
            sql = "UPDATE interviews SET "
            sql += "data_status = 'C' "
            sql += "WHERE id = %d; " % self.interview_id
            self.cur.execute(sql)
            self.conn.commit()
            self.tbEdit.setDisabled(True)
            self.tbMove.setDisabled(True)
        # disable interview
        self.frSectionControls.setDisabled(True)
        # enable close button
        self.frInterviewSelection.setEnabled(True)
        # clear interview
        self.interviewUnload()
        # update interview list
        self.interviewLoadList()
        
        

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
                QgsMessageLog.logMessage(self.myself())
            # method body
            # prevent section from being changed
            self.lwSectionList.setDisabled(True)
            if self.interviewState <> 'Running':
                self.frInterviewSelection.setDisabled(True)
            # enable save and cancel
            self.pbSaveSection.setEnabled(True)
            self.pbCancelSection.setEnabled(True)
            self.pbDeleteSection.setEnabled(True)
            if self.lmbMode == 'Interview':
                # disable map tools
                self.mapToolsDisableDrawing()
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
                QgsMessageLog.logMessage(self.myself())
            # method body
            # prevent section from being changed
            self.lwSectionList.setDisabled(True)
            if self.interviewState <> 'Running':
                self.frInterviewSelection.setDisabled(True)
            self.pbCancelSection.setEnabled(True)
            if self.lmbMode == 'Interview':
                if enableSave == True:
                    self.pbSaveSection.setEnabled(True)
                    # disable drawing map tools
                    self.mapToolsDisableDrawing()
                else:
                    self.pbSaveSection.setDisabled(True)
                    # enable drawing map tools
                    if self.lmbMode == 'Interview':
                        if self.mapToolsScaleOK():
                            self.mapToolsEnableDrawing()
                    else:
                        self.mapToolsEnableDrawing()                
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
            if self.lmbMode == 'Interview':
                if self.mapToolsScaleOK():
                    self.mapToolsEnableEditing()
            else:
                self.mapToolsEnableEditing()                
            self.tbNonSpatial.setDisabled(True)

    #
    # disable save and cancel buttons, but leave delete enabled

    def sectionDisableSaveCancel(self):

        if self.interviewState in ('View','Running'):
            # use debug track order of calls
            if self.editDebug:
                QgsMessageLog.logMessage(self.myself())
            # method body
            # allow section from being changed
            self.lwSectionList.setEnabled(True)
            if self.interviewState <> 'Running':
                self.frInterviewSelection.setEnabled(True)
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
                # enable finish and pause
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


    #####################################################
    #           section creation and deletion           #
    #####################################################

    #
    # section move up

    def sectionMoveUp(self):

        # use debug track order of calls
        if self.editDebug:
            QgsMessageLog.logMessage(self.myself())
        self.interviewState = 'Import'
        # get current record sequence value
        cSeqVal = self.currentSequence
        nSeqVal = cSeqVal - 1
        # set current item to sequence value minus 1
        sql = "UPDATE interview_sections "
        sql += "SET sequence_number = %d " % nSeqVal
        sql += "WHERE interview_id = %d AND id = '%s' " % (self.interview_id, self.section_id)
        self.cur.execute(sql)
        # select previous item to get section code
        self.lwSectionList.setCurrentRow(self.lwSectionList.currentRow()-1)
        prevSecCode = self.lwSectionList.currentItem().text()        
        # increment new records sequence value
        sql = "UPDATE interview_sections "
        sql += "SET sequence_number = %d " % cSeqVal
        sql += "WHERE interview_id = %d AND section_code = '%s' " % (self.interview_id, prevSecCode)
        self.cur.execute(sql)
        self.conn.commit()
        # move previous item down in list in interface
        currentRow = self.lwSectionList.currentRow()
        currentItem = self.lwSectionList.takeItem(currentRow)
        self.lwSectionList.insertItem(currentRow + 1, currentItem)
        self.currentSequence = nSeqVal
        self.interviewState = 'View'
        self.setSectionSortButtons()

    #
    # section move down

    def sectionMoveDown(self):

        # use debug track order of calls
        if self.editDebug:
            QgsMessageLog.logMessage(self.myself())
        self.interviewState = 'Import'
        startRow = self.lwSectionList.currentRow()
        # get current record sequence value
        cSeqVal = self.currentSequence
        nSeqVal = cSeqVal + 1
        # set current item to sequence value plus 1
        sql = "UPDATE interview_sections "
        sql += "SET sequence_number = %d " % nSeqVal
        sql += "WHERE interview_id = %d AND id = '%s' " % (self.interview_id, self.section_id)
        self.cur.execute(sql)
        # select next item to get section code
        self.lwSectionList.setCurrentRow(self.lwSectionList.currentRow()+1)
        nextSecCode = self.lwSectionList.currentItem().text()        
        # increment new records sequence value
        sql = "UPDATE interview_sections "
        sql += "SET sequence_number = %d " % cSeqVal
        sql += "WHERE interview_id = %d AND section_code = '%s' " % (self.interview_id, nextSecCode)
        self.cur.execute(sql)
        self.conn.commit()
        # move previous item down in list in interface
        currentRow = self.lwSectionList.currentRow()
        currentItem = self.lwSectionList.takeItem(currentRow)
        self.lwSectionList.insertItem(currentRow - 1, currentItem)
        self.currentSequence = nSeqVal
        # reset selection
        endRow = self.lwSectionList.currentRow()
        # if the difference is two spots, then in the middle of list and need to
        # to move back one. if at end of list difference will be one and no shift
        # needed
        if endRow - startRow == 2:
            self.lwSectionList.setCurrentRow(self.lwSectionList.currentRow()-1)
        self.interviewState = 'View'
        self.setSectionSortButtons()

    #
    # section sort

    def sectionSort(self):

        # use debug track order of calls
        if self.editDebug:
            QgsMessageLog.logMessage(self.myself())
        questionText = "This will re-order all sections. This can not be reversed. "
        questionText += "Are you sure you want to do this?"
        response = QtGui.QMessageBox.information(self, 'Re-order features',
                    questionText, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        if response == QtGui.QMessageBox.Yes:
            # get current id, and content codes ordered by sequence
            sql = "SELECT id, primary_code, sequence_number, geom_source, section_code "
            sql += "FROM interview_sections "
            sql += "WHERE interview_id = %d ORDER by sequence_number " % self.interview_id
            rs = self.cur.execute(sql)
            secInfo = rs.fetchall()
            newInfo = []
            # collect information
            for sec in secInfo:
                #QgsMessageLog.logMessage(sec[4])
                sortVal = re.findall(r'\d+', sec[4])
                if len(sortVal) > 0:
                    sortVal = int(sortVal[0])
                else:
                    sortVal = 0
                #QgsMessageLog.logMessage(str(sortVal))
                newInfo.append([int(sortVal),sec[0]])
            # sort information
            newInfo.sort()
            # write changes
            x = 1
            for newSec in newInfo:
                # write new section codes and sequences numbers
                sql = "UPDATE interview_sections SET "
                sql += "sequence_number = %d " % x
                sql += "WHERE interview_id = %d and id = %d" % (self.interview_id, newSec[1])
                self.cur.execute(sql)
                x += 1
            self.conn.commit()
            self.interviewUnload()
            self.interviewLoad()
    #
    # section renumber

    def sectionRenumber(self):

        # use debug track order of calls
        if self.editDebug:
            QgsMessageLog.logMessage(self.myself())
        questionText = "This will renumber all sections. This can not be reversed. "
        questionText += "Are you sure you want to do this?"
        response = QtGui.QMessageBox.information(self, 'Renumber features',
                    questionText, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        if response == QtGui.QMessageBox.Yes:
            # renumber interview_sections
            # get current id, and content codes ordered by sequence
            sql = "SELECT id, primary_code, sequence_number, geom_source, section_code "
            sql += "FROM interview_sections "
            sql += "WHERE interview_id = %d ORDER by sequence_number " % self.interview_id
            rs = self.cur.execute(sql)
            intvInfo = rs.fetchall()
            x = 1
            progNotice = QtGui.QProgressDialog()
            progNotice.setWindowTitle("Renumbering sections")
            progNotice.setCancelButton(None)
            progNotice.show()
            for rec in intvInfo:
                progNotice.setValue(float(x)/float(len(intvInfo)))
                newSecCode = "%s%04d" % (rec[1],x)
                sql = "UPDATE interview_sections SET "
                sql += "sequence_number = %d, " % x
                sql += "section_code = '%s' " % newSecCode
                sql += "WHERE interview_id = %d and id = %d" % (self.interview_id, rec[0])
                self.cur.execute(sql)
                # update references to this section in interview_sections
                sql = "UPDATE interview_sections "
                sql += "SET geom_source = '%s' " % newSecCode
                sql += "WHERE interview_id = %d AND geom_source = '%s';" % (self.interview_id, rec[4])
                self.cur.execute(sql)
                # update references to this section in geographic tables
                if rec[3] == 'pt':
                    sql = "UPDATE points SET "
                    sql += "section_code = '%s', content_code = '%s' " % (newSecCode, rec[1])
                    sql += "WHERE section_id = %d;" % rec[0]
                elif rec[3] == 'ln':
                    sql = "UPDATE lines SET "
                    sql += "section_code = '%s', content_code = '%s' " % (newSecCode, rec[1])
                    sql += "WHERE section_id = %d;" % rec[0]
                elif rec[3] == 'pl':
                    sql = "UPDATE polygons SET "
                    sql += "section_code = '%s', content_code = '%s' " % (newSecCode, rec[1])
                    sql += "WHERE section_id = %d;" % rec[0]
                if rec[3] in ('pt','ln','pl'):
                    self.cur.execute(sql)
                self.conn.commit()
                x += 1
            progNotice.setValue(100.0)
            self.interviewUnload()
            self.interviewLoad()
            progNotice.hide()
        
    #
    # create non-spatial section

    def sectionCreateNonSpatial(self):

        # use debug track order of calls
        if self.editDebug:
            QgsMessageLog.logMessage(self.myself())
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
            QgsMessageLog.logMessage(self.myself())
        # method body
        # check if feauture tab widget and project codes are disabled and if so
        # enabled them
        if self.lwProjectCodes.isEnabled() == False:
            self.lwProjectCodes.setEnabled(True)
            self.twSectionContent.setEnabled(True)
        # set state
        self.featureState = 'Create'
        # set date information
        self.section_date_created = datetime.datetime.now().isoformat()[:10]
        self.section_date_modified = self.section_date_created
        if self.lmbMode <> 'Interview':
            # set media times for new section and update media time for existing section
            if self.audioEndPosition > 1:
                media_start_time = self.seconds2timeString(self.audioEndPosition-1)
            else:
                media_start_time = self.seconds2timeString(self.audioEndPosition)
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
            if self.previousPrimaryCode == '':
                if self.currentPrimaryCode == '':
                    if self.currentFeature == 'pt':
                        self.currentPrimaryCode = self.pointCode
                    elif self.currentFeature == 'ln':
                        self.currentPrimaryCode = self.lineCode
                    elif self.currentFeature == 'pl':
                        self.currentPrimaryCode = self.polygonCode
                    else:
                        self.currentPrimaryCode = self.defaultCode
                    self.previousPrimaryCode = self.currentPrimaryCode
                else:
                    self.previousPrimaryCode = self.currentPrimaryCode
            if self.copyPrevious == True:
                # copy previous record
                self.currentPrimaryCode = self.previousPrimaryCode
                data_security = self.previousSecurity
                content_codes = self.previousContentCodes
                tags = self.previousTags
                date_time = self.previousDateTime
                time_of_year = self.previousTimeOfYear
                note = self.previousNote
            else:
                # create new record
                if self.currentFeature == 'pt':
                    self.currentPrimaryCode = self.pointCode
                elif self.currentFeature == 'ln':
                    self.currentPrimaryCode = self.lineCode
                elif self.currentFeature == 'pl':
                    self.currentPrimaryCode = self.polygonCode
                else:
                    self.currentPrimaryCode = self.defaultCode
                data_security = 'PU'
                content_codes = self.currentPrimaryCode
                tags = ''
                date_time = 'U'
                time_of_year = 'U'
                note = ''
                self.previousPrimaryCode = self.currentPrimaryCode
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
            self.currentSectionCode = '%s%04d' % (self.currentPrimaryCode,self.currentSequence)
        else:
            # create new record
            if self.currentFeature == 'pt':
                self.currentPrimaryCode = self.pointCode
            elif self.currentFeature == 'ln':
                self.currentPrimaryCode = self.lineCode
            elif self.currentFeature == 'pl':
                self.currentPrimaryCode = self.polygonCode
            else:
                self.currentPrimaryCode = self.defaultCode
            data_security = 'PU'
            content_codes = self.currentPrimaryCode
            tags = ''
            date_time = 'U'
            time_of_year = 'U'
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
            self.currentSectionCode = '%s%04d' % (self.currentPrimaryCode,self.maxCodeNumber)
            self.currentCodeNumber = self.maxCodeNumber
            self.currentSequence = newSequence
        sql = 'INSERT INTO interview_sections (id, interview_id, sequence_number, '
        sql += 'primary_code, section_code, note, date_time, time_of_year, '
        sql += 'spatial_data_source, geom_source, content_codes, tags, media_start_time, media_end_time, '
        sql += 'data_security, date_created, date_modified) VALUES '
        sql += '(%d,%d,' % (self.section_id, self.interview_id)
        sql += '%d,"%s","%s","%s",' % (self.currentSequence, self.currentPrimaryCode, self.currentSectionCode, note)
        sql += '"%s","%s","%s",' % (date_time, time_of_year, spatial_data_source)
        sql += '"%s","%s","%s","%s","%s","%s",' % (self.currentFeature,content_codes,tags,media_start_time,media_end_time,data_security)
        sql += '"%s","%s");' % (self.section_date_created, self.section_date_modified)
        self.cur.execute(sql)
        #self.conn.commit()
        # set defaults
        self.previousPrimarytCode = self.currentPrimaryCode 
        self.previousSecurity = data_security
        self.previousContentCodes = content_codes
        self.previousTags = tags
        self.previousDateTime = date_time
        self.previousTimeOfYear = time_of_year
        self.previousNote = note
        self.currentMediaFiles = ''
        
    #
    # add section record to list widget - called after a section is fully created
    
    def sectionAddEntry(self):

        # use debug track order of calls
        if self.editDebug:
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
                    self.cbFeatureSource.addItem('same as %s' % self.currentSectionCode)
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
            QgsMessageLog.logMessage(self.myself())
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
            QgsMessageLog.logMessage(self.myself())
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
            QgsMessageLog.logMessage(self.myself())
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
            sql += "'%s','%s','%s','%s'," %  (self.currentSectionCode,self.currentPrimaryCode,self.section_date_created, self.section_date_modified)
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
            sql += "'%s','%s','%s','%s'," %  (self.currentSectionCode,self.currentPrimaryCode,self.section_date_created, self.section_date_modified)
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
            sql += "'%s','%s','%s','%s'," %  (self.currentSectionCode,self.currentPrimaryCode,self.section_date_created, self.section_date_modified)
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
            QgsMessageLog.logMessage(self.myself())
        # method body
        # change interface to reflect completion of editing
        self.sectionDisableSaveCancel()
        # set codes for SQL
        self.currentPrimaryCode = self.leCode.text()
        sectionCode = '%s%04d' % (self.currentPrimaryCode,self.currentCodeNumber)
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
                idx = self.cbFeatureSource.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
                if idx == -1:
                    self.cbFeatureSource.addItem('same as %s' % self.currentSectionCode)
        #
        # case 2 - spatial to non-spatial
        elif oldGeomSource in ('pt','ln','pl') and self.cbFeatureSource.currentIndex() == 0:
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
                idx = self.cbFeatureSource.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
                if idx > -1:
                    self.cbFeatureSource.removeItem(idx)
            else:
                self.sectionLoadRecord()
                return
        #
        # case 3 - spatial to link
        elif oldGeomSource in ('pt','ln','pl') and self.cbFeatureSource.currentIndex() > 1:
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
            referencedCode = self.cbFeatureSource.currentText()[8:]
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
                idx = self.cbFeatureSource.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
                if idx > -1:
                    self.cbFeatureSource.removeItem(idx)
            else:
                self.sectionLoadRecord()
                return
        #
        # case 4 - non-spatial to link
        elif oldGeomSource == 'ns' and self.cbFeatureSource.currentIndex() > 1:
            deselectOld = True
            selectNew = True
            referencedCode = self.cbFeatureSource.currentText()[8:]
            currentGeomSource = referencedCode
        #
        # case 5 - linked to non-spatial
        elif not oldGeomSource in ('pt','ln','pl','ns') and self.cbFeatureSource.currentIndex() == 0:
            deselectOld = True
            currentGeomSource = 'ns'
            self.currentFeature = 'ns'          
        #
        # case 6 - link to different link
        elif not oldGeomSource in ('pt','ln','pl','ns') and self.cbFeatureSource.currentIndex() > 1:
            deselectOld = True
            selectNew = True
            referencedCode = self.cbFeatureSource.currentText()[8:]
            currentGeomSource = referencedCode
        #
        # case 7 - link to spatial
        elif not oldGeomSource in ('pt','ln','pl','ns') and self.cbFeatureSource.currentIndex() == 1:
            referencedCode = oldGeomSource
            questionText = 'You have set this feature as unique and separate from the previously referenced section %s.' % referencedCode
            questionText += 'The geometry from %s will be copied to this section for editing. ' % referencedCode
            questionText += 'Are you sure you want to do this?'
            response = QtGui.QMessageBox.information(self, 'Spatial Feature Changed',
                questionText, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if response == QtGui.QMessageBox.No:
                self.sectionLoadRecord()
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
            self.previousPrimaryCode = self.currentPrimaryCode
            self.sectionUpdateCode(sectionCode, self.currentPrimaryCode)
            lstIdx = self.cbFeatureSource.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
            if lstIdx <> -1:
                self.cbFeatureSource.setItemText(lstIdx, 'same as %s' % sectionCode)
            self.lwSectionList.currentItem().setText(sectionCode)
        if self.lmbMode <> 'Interview':
            # now check for changes to media start and end times
            media_start_time = self.seconds2timeString(self.spMediaStart.value())
            media_end_time = self.seconds2timeString(self.spMediaEnd.value())
            # if start times have changed update preceding setion if it exists
            if self.audioStartPosition <> self.spMediaStart.value() and \
            self.lwSectionList.currentRow() <> 0:
                # determine precending section
                precedingSectionCode = self.lwSectionList.item(self.lwSectionList.currentRow()-1).text()
                sql = "UPDATE interview_sections "
                sql += 'SET media_end_time = "%s" ' % media_start_time
                sql += "WHERE interview_id = %d AND section_code = '%s' " % (self.interview_id, precedingSectionCode)
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
        self.previousSecurity = self.project_security[self.cbSectionSecurity.currentIndex()]
        self.previousContentCodes = self.pteContentCodes.document().toPlainText()
        self.previousTags = self.pteSectionTags.document().toPlainText()
        self.previousDateTime = self.project_date_time[self.cbDateTime.currentIndex()]
        self.previousTimeOfYear = self.project_time_of_year[self.cbTimeOfYear.currentIndex()]
        self.previousNote = self.pteSectionNote.document().toPlainText().replace("'","''")
        self.previousText = self.pteSectionText.document().toPlainText().replace("'","''")
        self.section_date_modified = datetime.datetime.now().isoformat()[:10]
        sql = 'UPDATE interview_sections SET '
        sql += "primary_code = '%s', " % self.currentPrimaryCode
        sql += "section_code = '%s', " % sectionCode
        sql += "data_security = '%s', " % self.previousSecurity
        sql += "geom_source = '%s', " % currentGeomSource
        sql += "content_codes = '%s', " % self.previousContentCodes
        sql += "tags = '%s', " % self.previousTags
        sql += "date_time = '%s', " % self.previousDateTime
        sql += "time_of_year = '%s', " % self.previousTimeOfYear
        sql += "note = '%s', " % self.previousNote
        sql += "section_text = '%s', " % self.previousText
        sql += "media_files = '%s', " % self.currentMediaFiles
        if self.lmbMode in ('Transcribe','Import'):
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
        self.previousPrimaryCode = self.currentPrimaryCode
            
    #
    # cancel edits to section

    def sectionCancelEdits(self):

        # use debug track order of calls
        if self.editDebug:
            QgsMessageLog.logMessage(self.myself())
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
            self.cbFeatureSource.setCurrentIndex(0)
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
            self.section_id = self.section_id - 1
            self.previousSectionId = self.previousSectionId - 1
            self.sequence = self.sequence - 1
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
            QgsMessageLog.logMessage(self.myself())
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
            idx = self.cbFeatureSource.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
            if idx > -1:
                self.cbFeatureSource.removeItem(idx)
            # check if last section as adjust time index of precending section if needed
            if self.lwSectionList.currentRow()+1 == self.lwSectionList.count():
                pIdx = self.lwSectionList.currentRow()
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
            #
            # adjust count variables so that sequence ordering is not lost
            # if the last item on the list is deleted. This will not affect deletions
            # in the middle of a sequence
            #
            sql = 'SELECT max(sequence_number) FROM interview_sections '
            sql += 'WHERE interview_id = %d ' % self.interview_id
            rs = self.cur.execute(sql)
            rsData = rs.fetchall()
            if rsData[0][0] == None:
                self.maxCodeNumber = 0
            else:
                self.maxCodeNumber = rsData[0][0]
            if self.lmbMode == 'Interview':
                self.sequence = self.maxCodeNumber
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
        # check if there are valid sections
        if self.lwSectionList.count() == 0:
            self.lwProjectCodes.setDisabled(True)
            self.twSectionContent.setDisabled(True)
        # reset sort buttons
        if self.lmbMode == 'Import':
            self.setSectionSortButtons()

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
        ( (self.lmbMode in ('Import','Transcribe') and self.interviewState == 'View') or \
          (self.lmbMode == 'Interview' and self.interviewState == 'Running') ):
            if self.lmbMode in ('Import','Transcribe') and \
            self.mediaState == 'playing':
                self.audioPlayPause()
            # use debug track order of calls
            if self.editDebug:
                QgsMessageLog.logMessage(self.myself())
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
            sql = "SELECT id, sequence_number, primary_code, data_security, "
            sql += "geom_source, content_codes, tags, date_time, time_of_year, note, "
            sql += "media_start_time, media_end_time, section_text, media_files "
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
            # for import mode allow reordering of sections
            self.setSectionSortButtons()

    #
    # enable / disable section sort buttons

    def setSectionSortButtons(self):
        
        if self.lmbMode == 'Import':
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
    # load section record

    def sectionLoadRecord(self):

        # use debug track order of calls
        if self.editDebug:
            QgsMessageLog.logMessage(self.myself())
        # method body
        if self.sectionData == None or self.sectionData[0][0] <> self.section_id:
            # grab section record
            sql = "SELECT id, sequence_number, primary_code, data_security, "
            sql += "geom_source, content_codes, tags, date_time, time_of_year, note, "
            sql += "media_start_time, media_end_time, section_text, media_files "
            sql += "FROM interview_sections WHERE "
            sql += "interview_id = %d AND section_code = '%s';" % (self.interview_id, self.currentSectionCode)
            rs = self.cur.execute(sql)
            self.sectionData = rs.fetchall()
        # set to load state so no change in enabling controls happens
        oldState = self.featureState
        self.featureState = 'Load'
        # update section edit controls
        # set time and audio controls
        self.audioStartPosition = self.timeString2seconds(self.sectionData[0][10])
        self.audioEndPosition = self.timeString2seconds(self.sectionData[0][11])
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
        self.cbSectionSecurity.setCurrentIndex(self.project_security.index(self.sectionData[0][3]))
        geomSource = self.sectionData[0][4]
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
        self.pteContentCodes.setPlainText(self.sectionData[0][5])
        self.pteSectionTags.setPlainText(self.sectionData[0][6])
        self.cbDateTime.setCurrentIndex(self.project_date_time.index(self.sectionData[0][7]))
        self.cbTimeOfYear.setCurrentIndex(self.project_time_of_year.index(self.sectionData[0][8]))
        self.pteSectionNote.setPlainText(self.sectionData[0][9])
        # deselect items
        for i in range(self.lwProjectCodes.count()):
            item = self.lwProjectCodes.item(i)
            self.lwProjectCodes.setItemSelected(item,False)
        # select items
        codeList = self.sectionData[0][5].split(',')
        for code in codeList:
            self.lwProjectCodes.setItemSelected(self.lwProjectCodes.findItems(code,QtCore.Qt.MatchExactly)[0], True)
        # set text
        self.pteSectionText.setPlainText(self.sectionData[0][12])
        if self.sectionData[0][13] <> None:
            self.currentMediaFiles = self.sectionData[0][13]
        else:
            self.currentMediaFiles = ''
        # return to view state
        self.featureState = oldState
        # add photos to tab
        self.twPhotos.clear()
        self.twPhotos.setRowCount(0)
        if self.currentMediaFiles <> None:
            cmFiles = self.currentMediaFiles.split('|||')
            if len(cmFiles) > 0:
                if cmFiles[0] == '':
                    cmFiles = cmFiles[1:]
                for item in cmFiles:
                    if '||' in item:
                        fName,caption = item.split('||')
                        if os.path.exists(fName):
                            self.photoLoad(fName,caption)
            
    #
    # update section code in spatial layer when the section code changes

    def sectionUpdateCode(self, sectionCode, contentCode):
        
        # use debug track order of calls
        if self.editDebug:
            QgsMessageLog.logMessage(self.myself())
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

    def sectionFeatureSourceChanged(self):

        # need to make changes here
        if self.featureState in ('View','Edit'):
            if self.currentFeature == 'ns' and self.cbFeatureSource.currentIndex() == 1:
                # was non-spatial and user choose to make it spatial switch to point tool
                # because user can change to line or polygon tool if needed
                self.featureState = 'Add Spatial'
                self.mapToolsActivatePointCapture()
            elif self.cbFeatureSource.currentIndex() > 1:
                # check that a section is not self referencing
                referencedCode = self.cbFeatureSource.currentText()[8:]
                if referencedCode == self.currentSectionCode:
                    QtGui.QMessageBox.warning(self, 'User Error',
                        'A section can not reference itself', QtGui.QMessageBox.Ok)
                    if self.sectionData[0][4] in ('pt','ln','pl'):
                        self.cbFeatureSource.setCurrentIndex(1)
                    else:
                        self.cbFeatureSource.setCurrentIndex(0)
                self.sectionEnableSaveCancel()
            else:
                # enable saving or cancelling in response to editing
                self.sectionEnableSaveCancel()

    #
    # add / remove tags to sections
        
    def sectionAddRemoveCodes(self):

        modifiers = QtGui.QApplication.keyboardModifiers()
        # use debug track order of calls
        if self.editDebug:
            QgsMessageLog.logMessage(self.myself())
        # method body
        # only act if editing or viewing, not loading
        if self.featureState in ('View','Edit'):
            # grab modifier key
            if modifiers == QtCore.Qt.ControlModifier:
                replacePrimaryCode = True
            else:
                replacePrimaryCode = False
            # determine what items are selected
            selectedItems = self.lwProjectCodes.selectedItems()
            # if adding items
            if self.selectedCodeCount < len(selectedItems):
                if replacePrimaryCode == True:
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


    #####################################################
    #                   map tools                       #
    #####################################################

    #
    # map tools scale enable

    def mapToolsScaleNotification(self):

        if self.lmbMode in 'Interview' and self.featureState == 'View' and \
        self.interviewState == 'Running':
            # use debug track order of calls
            if self.editDebug:
                QgsMessageLog.logMessage(self.myself())
            if self.mapToolsScaleOK():
                self.mapToolsEnableDrawing()
                self.mapToolsEnableEditing()
                if self.showZoomNotices and self.zoomMessage <> '':
                    self.iface.messageBar().clearWidgets()
                    self.iface.messageBar().pushMessage("Proceed", self.zoomMessage, level=QgsMessageBar.INFO, duration=1)            
            else:
                self.mapToolsDisableDrawing()
                self.mapToolsDisableEditing()
                if self.showZoomNotices:
                    self.iface.messageBar().clearWidgets()
                    self.iface.messageBar().pushMessage("Error", self.zoomMessage, level=QgsMessageBar.CRITICAL, duration=2)            

    #
    # map tools scale OK

    def mapToolsScaleOK(self):

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

    def mapToolsEnableDrawing(self):
        
        self.tbPoint.setEnabled(True)
        self.tbLine.setEnabled(True)
        self.tbPolygon.setEnabled(True)

    #
    # map tools disable drawing

    def mapToolsDisableDrawing(self):

        self.tbPoint.setDisabled(True)
        self.tbLine.setDisabled(True)
        self.tbPolygon.setDisabled(True)

    #
    # map tools enable editing

    def mapToolsEnableEditing(self):

        self.tbEdit.setEnabled(True)
        self.tbMove.setEnabled(True)

    #
    # map tools disable editing

    def mapToolsDisableEditing(self):

        self.tbEdit.setDisabled(True)
        self.tbMove.setDisabled(True)

    #
    # activate pan tool

    def mapToolsActivatePanTool(self):

        # use debug track order of calls
        if self.spatialDebug:
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
            QgsMessageLog.logMessage(self.myself())
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
            QgsMessageLog.logMessage(self.myself())
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
        self.mapToolsEnableDrawing()
        # disable editing
        self.mapToolsDisableEditing()
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
            QgsMessageLog.logMessage(self.myself())
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

    def mapToolsActivateSpatialEdit( self ):

        # use debug track order of calls
        if self.spatialDebug:
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
            QgsMessageLog.logMessage(self.myself())
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
            QgsMessageLog.logMessage(self.myself())
        # method body
        # get next point id
        self.point_id = self.previousPointId + 1
        self.previousPointId = self.point_id
        point.convertToMultiType()
        # insert into database
        sql = "INSERT INTO points "
        sql += "(id,interview_id,section_id,section_code,content_code,date_created,date_modified,geom) "
        sql += "VALUES (%d,%d,%d, " % (self.point_id, self.interview_id, self.section_id)
        sql += "'%s','%s','%s','%s'," %  (self.currentSectionCode,self.currentPrimaryCode,self.section_date_created, self.section_date_modified)
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
            if self.cbFeatureSource.currentIndex() <> 1: 
                self.cbFeatureSource.setCurrentIndex(1)
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
        idx = self.cbFeatureSource.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
        if idx == -1:
            self.cbFeatureSource.addItem('same as %s' % self.currentSectionCode)

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
            QgsMessageLog.logMessage(self.myself())
        # method body
        # get next line id
        self.line_id = self.previousLineId + 1
        self.previousLineId = self.line_id
        line.convertToMultiType()
        # insert into database
        sql = "INSERT INTO lines "
        sql += "(id,interview_id,section_id,section_code,content_code,date_created,date_modified,geom) "
        sql += "VALUES (%d,%d,%d, " % (self.line_id, self.interview_id, self.section_id)
        sql += "'%s','%s','%s','%s'," %  (self.currentSectionCode,self.currentPrimaryCode,self.section_date_created, self.section_date_modified)
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
            if self.cbFeatureSource.currentIndex() <> 1: 
                self.cbFeatureSource.setCurrentIndex(1)
        else:
            sql = "UPDATE interview_sections "
            sql += "SET spatial_data_scale = '%s' " % str(int(self.canvas.scale()))
            sql += "WHERE interview_id = %d and id = %d " % (self.interview_id, self.section_id)
            self.cur.execute(sql)
        # commit record
        self.conn.commit()
        idx = self.cbFeatureSource.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
        if idx == -1:
            self.cbFeatureSource.addItem('same as %s' % self.currentSectionCode)
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
        idx = self.cbFeatureSource.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
        if idx == -1:
            self.cbFeatureSource.addItem('same as %s' % self.currentSectionCode)

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
            QgsMessageLog.logMessage(self.myself())
        # method body
        # get next polygon id
        self.polygon_id = self.previousPolygonId + 1
        self.previousPolygonId = self.polygon_id
        polygon.convertToMultiType()
        # insert into database
        sql = "INSERT INTO polygons "
        sql += "(id,interview_id,section_id,section_code,content_code,date_created,date_modified,geom) "
        sql += "VALUES (%d,%d,%d, " % (self.polygon_id, self.interview_id, self.section_id)
        sql += "'%s','%s','%s','%s'," %  (self.currentSectionCode,self.currentPrimaryCode,self.section_date_created, self.section_date_modified)
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
            if self.cbFeatureSource.currentIndex() <> 1: 
                self.cbFeatureSource.setCurrentIndex(1)
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
        idx = self.cbFeatureSource.findText(self.currentSectionCode, QtCore.Qt.MatchEndsWith)
        if idx == -1:
            self.cbFeatureSource.addItem('same as %s' % self.currentSectionCode)




    #####################################################
    #                   photos                          #
    #####################################################

    #
    # load photo to list

    def photoLoad(self, fName, caption):
        
        # use debug track order of calls
        if self.basicDebug:
            QgsMessageLog.logMessage(self.myself())
        p=QtGui.QPixmap(fName)
        if p.height()>p.width():
            p=p.scaledToWidth(self.thumbnailSize)
        else:
            p=p.scaledToHeight(self.thumbnailSize)
        p=p.copy(0,0,self.thumbnailSize,self.thumbnailSize)
        item = QtGui.QTableWidgetItem()
        item.setStatusTip(caption)
        item.setIcon(QtGui.QIcon(p))
        rCnt = self.twPhotos.rowCount()+1
        self.twPhotos.setRowCount(rCnt)
        self.twPhotos.setItem(rCnt-1,0,item)
        item = QtGui.QTableWidgetItem(caption)
        self.twPhotos.setItem(rCnt-1,1,item)

    #
    # add photo

    def photoAdd(self):

        # use debug track order of calls
        if self.basicDebug:
            QgsMessageLog.logMessage(self.myself())
        fName = QtGui.QFileDialog.getOpenFileName(self, 'Select Project Directory',self.projectDir,"Image Files (*.png *.PNG *.jpg *.JPG *.bmp *.BMP *.tif *.tiff *.TIF *.TIFF *.gif *.GIF)")
        if os.path.exists(fName):
            caption, ok = QtGui.QInputDialog.getText(self, 'Caption', 
                'Enter the caption for this image')
            if ok:
                self.photoLoad(fName,caption)
                self.twPhotos.clearSelection()
                self.currentMediaFiles += '|||%s||%s' % (fName,caption)
                self.sectionEnableSaveCancel()
        
    #
    # edit photo

    def photoEdit(self):

        # use debug track order of calls
        if self.basicDebug:
            QgsMessageLog.logMessage(self.myself())
        cRow = self.twPhotos.currentRow()
        oldCaption = self.twPhotos.item(cRow,1).text()
        caption, ok = QtGui.QInputDialog.getText(self, 'Caption', 
            'Edit the caption for this image', text = oldCaption)
        if ok:
            self.twPhotos.item(cRow,1).setText(caption)
            cmList = self.currentMediaFiles.split('|||')
            if len(cmList) > 0:
                if cmList[0] == '':
                    cmList = cmList[1:]
                cmList[cRow] = '%s||%s' % (cmList[cRow].split('||')[0],caption)
            self.currentMediaFiles = ''
            for item in cmList:
                self.currentMediaFiles += '|||%s' % item
            self.sectionEnableSaveCancel()
        self.twPhotos.clearSelection()
        
            
    #
    # remove photo

    def photoRemove(self):

        # use debug track order of calls
        if self.basicDebug:
            QgsMessageLog.logMessage(self.myself())
        cRow = self.twPhotos.currentRow()
        self.twPhotos.removeRow(cRow)
        self.twPhotos.clearSelection()
        cmList = self.currentMediaFiles.split('|||')
        if len(cmList) > 0:
            if cmList[0] == '':
                cmList = cmList[1:]
            cmList.remove(cmList[cRow])
        self.currentMediaFiles = ''
        for item in cmList:
            self.currentMediaFiles += '|||%s' % item
        self.sectionEnableSaveCancel()

    #
    # select or deselect a photo

    def photoSelect(self):

        # use debug track order of calls
        if self.basicDebug:
            QgsMessageLog.logMessage(self.myself() + ':' + self.featureState)
        if self.featureState <> 'Load':
            if len(self.twPhotos.selectedItems()) > 0:
                self.pbRemovePhoto.setEnabled(True)
                self.pbEditPhoto.setEnabled(True)
            else:
                self.pbRemovePhoto.setDisabled(True)
                self.pbEditPhoto.setDisabled(True)

            
