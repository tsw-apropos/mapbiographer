# -*- coding: utf-8 -*-
"""
/***************************************************************************
 mapBiographerManager
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
from ui_mapbio_manager import Ui_mapbioManager
from mapbio_porter import mapBiographerPorter
from pyspatialite import dbapi2 as sqlite
import os, datetime, time
import inspect
from pydub import AudioSegment

class mapBiographerManager(QtGui.QDialog, Ui_mapbioManager):
    
    def __init__(self, iface):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)
        self.iface = iface

        # debug setup
        self.debug = False
        if self.debug:
            self.myself = lambda: inspect.stack()[1][3]
        if self.debug:
            QgsMessageLog.logMessage(self.myself())

        # settings variable
        self.setModal(False)
        self.dirName = '.'
        self.hasHeritage = False
        self.heritageCommunity = 'N/A'
        self.heritageUser = 'N/A'
        self.projectDB = ''
        self.qgsProject = ''
        self.baseGroups = []
        self.projectGroups = []
        self.projectLayers = []
        self.boundaryLayer = ''
        self.enableReference = ''
        self.referenceLayer = ''
        self.qgsProjectChanged = True
        self.projCodes = []
        self.projDefs = []
        
        # object variables
        self.conn = None
        self.cur = None
        self.projDate = None
        self.contDate = None
        self.addrDate = None
        self.teleDate = None
        self.intvDate = None
        self.intvPartDate = None
        self.projId = 1
        self.partId = 1
        self.addrId = 1
        self.teleId = 1
        self.intvId = 1
        self.intvPartId = 1
        self.participantList = []
        self.interviewerList = []
        self.interviewStatus = 'N'

        self.setWindowTitle('LMB Manager')

        # trigger control
        self.settingsState = 'load'
        self.projectState = 'load'
        #self.participantState = 'load'
        #self.interviewState = 'load'

        # make connections
        # main form
        QtCore.QObject.connect(self.pbDialogClose, QtCore.SIGNAL("clicked()"), self.closeDialog)
        # map biographer settings tab actions
        QtCore.QObject.connect(self.tbSelectProjectDir, QtCore.SIGNAL("clicked()"), self.settingsGetDir)
        QtCore.QObject.connect(self.cbProjectDatabase, QtCore.SIGNAL("currentIndexChanged(int)"), self.settingsSelectDB)
        QtCore.QObject.connect(self.cbMaxScale, QtCore.SIGNAL("currentIndexChanged(int)"), self.settingsEnableEdit)
        QtCore.QObject.connect(self.cbMinScale, QtCore.SIGNAL("currentIndexChanged(int)"), self.settingsEnableEdit)
        QtCore.QObject.connect(self.cbZoomRangeNotices, QtCore.SIGNAL("currentIndexChanged(int)"), self.settingsEnableEdit)
        QtCore.QObject.connect(self.tbSelectQgsProject, QtCore.SIGNAL("clicked()"), self.qgisReadProject)
        QtCore.QObject.connect(self.tblBaseGroups, QtCore.SIGNAL("itemSelectionChanged()"), self.baseGroupEnableRemoval)
        QtCore.QObject.connect(self.pbAddBaseGroup, QtCore.SIGNAL("clicked()"), self.baseGroupAdd)
        QtCore.QObject.connect(self.pbRemoveBaseGroup, QtCore.SIGNAL("clicked()"), self.baseGroupRemove)
        QtCore.QObject.connect(self.cbBoundaryLayer, QtCore.SIGNAL("currentIndexChanged(int)"), self.boundaryLayerUpdate)
        QtCore.QObject.connect(self.cbEnableReference, QtCore.SIGNAL("currentIndexChanged(int)"), self.referenceLayerSetStatus)
        QtCore.QObject.connect(self.cbReferenceLayer, QtCore.SIGNAL("currentIndexChanged(int)"), self.referenceLayerUpdate)
        # tab controls
        QtCore.QObject.connect(self.pbSaveSettings, QtCore.SIGNAL("clicked()"), self.settingsSave)
        QtCore.QObject.connect(self.pbCancelSettings, QtCore.SIGNAL("clicked()"), self.settingsCancel)
        QtCore.QObject.connect(self.pbTransfer, QtCore.SIGNAL("clicked()"), self.transferData)
        #
        # project details tab states
        QtCore.QObject.connect(self.leProjectCode, QtCore.SIGNAL("textChanged(QString)"), self.projectEnableEdit)
        QtCore.QObject.connect(self.pteProjectDescription, QtCore.SIGNAL("textChanged()"), self.projectEnableEdit)
        QtCore.QObject.connect(self.leProjectTags, QtCore.SIGNAL("textChanged(QString)"), self.projectEnableEdit)
        QtCore.QObject.connect(self.pteProjectNote, QtCore.SIGNAL("textChanged()"), self.projectEnableEdit)
        QtCore.QObject.connect(self.pteContentCodes, QtCore.SIGNAL("textChanged()"), self.projectRefreshCodes)
        QtCore.QObject.connect(self.pteDateAndTime, QtCore.SIGNAL("textChanged()"), self.projectEnableEdit)
        QtCore.QObject.connect(self.pteTimeOfYear, QtCore.SIGNAL("textChanged()"), self.projectEnableEdit)
        QtCore.QObject.connect(self.cbDefaultCode, QtCore.SIGNAL("currentIndexChanged(int)"), self.projectEnableEdit)
        QtCore.QObject.connect(self.cbPointCode, QtCore.SIGNAL("currentIndexChanged(int)"), self.projectEnableEdit)
        QtCore.QObject.connect(self.cbLineCode, QtCore.SIGNAL("currentIndexChanged(int)"), self.projectEnableEdit)
        QtCore.QObject.connect(self.cbPolygonCode, QtCore.SIGNAL("currentIndexChanged(int)"), self.projectEnableEdit)
        QtCore.QObject.connect(self.pbProjectSave, QtCore.SIGNAL("clicked()"), self.projectTableWrite)
        QtCore.QObject.connect(self.pbProjectCancel, QtCore.SIGNAL("clicked()"), self.projectTableCancel)
        #
        # people basic info actions
        QtCore.QObject.connect(self.pbParticipantNew, QtCore.SIGNAL("clicked()"), self.participantNew)
        QtCore.QObject.connect(self.pbParticipantCancel, QtCore.SIGNAL("clicked()"), self.participantCancelEdit)
        QtCore.QObject.connect(self.pbParticipantSave, QtCore.SIGNAL("clicked()"), self.participantWrite)
        QtCore.QObject.connect(self.pbParticipantDelete, QtCore.SIGNAL("clicked()"), self.participantDelete)
        # people basic info states
        QtCore.QObject.connect(self.tblParticipants, QtCore.SIGNAL("itemSelectionChanged()"), self.participantCheckSelection)
        # people address actions
        QtCore.QObject.connect(self.pbAddNew, QtCore.SIGNAL("clicked()"), self.addressNew)
        QtCore.QObject.connect(self.pbAddCancel, QtCore.SIGNAL("clicked()"), self.addressCancelEdit)
        QtCore.QObject.connect(self.pbAddSave, QtCore.SIGNAL("clicked()"), self.addressWrite)
        QtCore.QObject.connect(self.pbAddDelete, QtCore.SIGNAL("clicked()"), self.addressDelete)
        # people address states
        QtCore.QObject.connect(self.tblAddresses, QtCore.SIGNAL("itemSelectionChanged()"), self.addressCheckSelection)
        # people telecom actions
        QtCore.QObject.connect(self.pbTelNew, QtCore.SIGNAL("clicked()"), self.telecomNew)
        QtCore.QObject.connect(self.pbTelCancel, QtCore.SIGNAL("clicked()"), self.telecomCancelEdits)
        QtCore.QObject.connect(self.pbTelSave, QtCore.SIGNAL("clicked()"), self.telecomWrite)
        QtCore.QObject.connect(self.pbTelDelete, QtCore.SIGNAL("clicked()"), self.telecomDelete)
        # people telecom states
        QtCore.QObject.connect(self.tblTelecoms, QtCore.SIGNAL("itemSelectionChanged()"), self.telecomCheckSelection)
        #
        # interview basic info actions
        QtCore.QObject.connect(self.pbIntNew, QtCore.SIGNAL("clicked()"), self.interviewNew)
        QtCore.QObject.connect(self.pbIntCancel, QtCore.SIGNAL("clicked()"), self.interviewCancel)
        QtCore.QObject.connect(self.pbIntSave, QtCore.SIGNAL("clicked()"), self.interviewWrite)
        QtCore.QObject.connect(self.pbIntDelete, QtCore.SIGNAL("clicked()"), self.interviewDelete)
        # interview basic info states
        QtCore.QObject.connect(self.tblInterviews, QtCore.SIGNAL("itemSelectionChanged()"), self.interviewCheckSelection)
        # interview participant actions
        QtCore.QObject.connect(self.pbIntPartNew, QtCore.SIGNAL("clicked()"), self.interviewParticipantNew)
        QtCore.QObject.connect(self.pbIntPartCancel, QtCore.SIGNAL("clicked()"), self.interviewParticipantCancel)
        QtCore.QObject.connect(self.pbIntPartSave, QtCore.SIGNAL("clicked()"), self.interviewParticipantWrite)
        QtCore.QObject.connect(self.pbIntPartDelete, QtCore.SIGNAL("clicked()"), self.interviewParticipantDelete)
        # interview participant states
        QtCore.QObject.connect(self.tblInterviewParticipants, QtCore.SIGNAL("itemSelectionChanged()"), self.interviewParticipantCheckSelection)
        # participant edit selection
        QtCore.QObject.connect(self.cbIntPartName, QtCore.SIGNAL("currentIndexChanged(int)"), self.interviewParticipantSelection)
        
        try:
            self.settingsState = 'load'
            self.settingsRead()
            self.settingsDisableEdit()
            if os.path.exists(os.path.join(self.dirName,self.projectDB)):
                self.dbOpen()
                self.dbRead()
                self.projectDisableEdit()
                self.projectState = 'load'
                self.projectEnable()
        except:
            self.projectDisable()
            self.projectDisableEdit()

        self.settingsState = 'edit'
        self.projectState = 'edit'

    #
    # close dialog

    def closeDialog(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        if self.projectDB <> '' and self.conn <> None:
            self.dbClose()
        tv = self.iface.layerTreeView()
        tv.selectionModel().clear()
        self.iface.newProject()
        self.close()


    ########################################################
    #        map biographer settings tab functions         #
    ########################################################
    
    #
    # get project directory

    def settingsGetDir(self):
        
        lmbdir = QtGui.QFileDialog.getExistingDirectory(self, 'Select Directory')
        if lmbdir == '':
            lmbdir = '.'
        self.leProjectDir.setText(lmbdir)
        self.dirName = lmbdir
        self.refreshDatabaseList()
        self.settingsEnableEdit()

    #
    # select project database

    def settingsSelectDB(self):
        
        if self.projectState <> 'load':
            if self.debug:
                QgsMessageLog.logMessage(self.myself())
            #
            if self.cbProjectDatabase.currentIndex() == 1:
                newName, ok = QtGui.QInputDialog.getText(self, 'DB Name', 'Enter name for new database:')
                if ok:
                    if os.path.splitext(newName)[1] == '':
                        # add on .db extension (possibly for new db)
                        self.projectDB = newName + '.db'
                    else:
                        self.projectDB = newName
                else:
                    self.projectDB = ''
                    self.projectDisable()
                    self.cbProjectDatabase.setCurrentIndex(0)
                if self.projectDB <> '':
                    # read file if it exists
                    if not os.path.exists(os.path.join(self.dirName,self.projectDB)):
                        QtGui.QMessageBox.information(self, 'Information',
                           "System will create new database, please wait", QtGui.QMessageBox.Ok)
                        self.setDisabled(True)
                        self.createDB(os.path.join(self.dirName,self.projectDB))
                        self.setEnabled(True)
                        self.cbProjectDatabase.addItem(self.projectDB)
                        self.cbProjectDatabase.setCurrentIndex(self.cbProjectDatabase.count()-1)
                        self.dbOpen()
                        self.dbRead()
                        self.projectEnable()
                        self.settingsEnableEdit()
            elif self.cbProjectDatabase.currentIndex() == 0:
                self.projectDB = ''
                self.projectDisable()
                self.cbProjectDatabase.setCurrentIndex(0)
            elif self.cbProjectDatabase.count() > 2:
                self.projectDB = self.cbProjectDatabase.currentText()
                self.dbOpen()
                self.dbRead()
                self.projectEnable()
                self.settingsEnableEdit()

    #
    # enable settings buttons

    def settingsEnableEdit(self):

        if self.settingsState <> 'load' and self.pbDialogClose.isEnabled():
            if self.debug:
                QgsMessageLog.logMessage(self.myself())
            # enable save and cancel
            self.pbSaveSettings.setEnabled(True)
            self.pbCancelSettings.setEnabled(True)
            self.twMapBioSettings.tabBar().setDisabled(True)
            # other tabs
            self.tbProjectDetails.setDisabled(True)
            self.tbPeople.setDisabled(True)
            self.tbInterviews.setDisabled(True)
            # dialog close
            self.pbDialogClose.setDisabled(True)

    #
    # disable settings buttons

    def settingsDisableEdit(self):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # disable save and cancel
        self.pbSaveSettings.setDisabled(True)
        self.pbCancelSettings.setDisabled(True)
        self.twMapBioSettings.tabBar().setEnabled(True)
        # other tabs
        self.tbProjectDetails.setEnabled(True)
        self.tbPeople.setEnabled(True)
        self.tbInterviews.setEnabled(True)
        # dialog close
        self.pbDialogClose.setEnabled(True)
        
    #
    # save LMB settings

    def settingsSave(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        s = QtCore.QSettings()
        s.setValue('mapBiographer/projectDir', self.dirName)
        s.setValue('mapBiographer/projectDB', self.projectDB)
        s.setValue('mapBiographer/maxScale', self.cbMaxScale.currentText())
        s.setValue('mapBiographer/minScale', self.cbMinScale.currentText())
        s.setValue('mapBiographer/zoomNotices', self.cbZoomRangeNotices.currentText())
        s.setValue('mapBiographer/qgsProject', self.qgsProject)
        s.setValue('mapBiographer/baseGroups', self.baseGroups)
        s.setValue('mapBiographer/boundaryLayer', self.boundaryLayer)
        s.setValue('mapBiographer/enableReference', str(self.enableReference))
        s.setValue('mapBiographer/referenceLayer', self.referenceLayer)
        self.settingsDisableEdit()
        
    #
    # cancel LM settings

    def settingsCancel(self):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.settingsRead()
        self.settingsDisableEdit()
        
    #
    # refresh database list
    
    def refreshDatabaseList(self):

        # populate project database list
        self.cbProjectDatabase.clear()
        self.cbProjectDatabase.addItem('--None Selected--')
        self.cbProjectDatabase.addItem('Create New Database')
        listing = os.listdir(self.dirName)
        for item in listing:
            if '.db' in item:
                self.cbProjectDatabase.addItem(item)
        self.cbProjectDatabase.setCurrentIndex(0)
    
    #
    # read LMB settings

    def settingsRead(self):

        self.settingsState = 'load'
        self.projectState = 'load'
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # project dir
        s = QtCore.QSettings()
        rv = s.value('mapBiographer/projectDir')
        if rv == None:
            self.dirName = '.'
        else:
            self.dirName = rv
        self.leProjectDir.setText(self.dirName)
        self.refreshDatabaseList()
        # select project database
        rv = s.value('mapBiographer/projectDB')
        if rv == None:
            self.projectDB = ''
        else:
            self.projectDB = rv
        if os.path.exists(os.path.join(self.dirName,self.projectDB)):
            idx = self.cbProjectDatabase.findText(self.projectDB,QtCore.Qt.MatchExactly)
            self.cbProjectDatabase.setCurrentIndex(idx)
        # map settings
        rv = s.value('mapBiographer/qgsProject')
        if rv <> None and os.path.exists(rv) and self.qgsProjectChanged:
            self.qgisLoadProject(rv)
        else:
            # blank values if project invalid
            self.qgisSetNoProject()
        rv = s.value('mapBiographer/maxScale')
        if rv <> None:
            idx = self.cbMaxScale.findText(rv,QtCore.Qt.MatchExactly)
            self.cbMaxScale.setCurrentIndex(idx)
        else:
            self.cbMaxScale.setCurrentIndex(0)
        rv = s.value('mapBiographer/minScale')
        if rv <> None:
            idx = self.cbMinScale.findText(rv,QtCore.Qt.MatchExactly)
            self.cbMinScale.setCurrentIndex(idx)
        else:
            self.cbMinScale.setCurrentIndex(9)
        rv = s.value('mapBiographer/zoomNotices')
        if rv <> None:
            idx = self.cbZoomRangeNotices.findText(rv,QtCore.Qt.MatchExactly)
            self.cbZoomRangeNotices.setCurrentIndex(idx)
        else:
            self.cbZoomRangeNotices.setCurrentIndex(0)
        self.projectState = 'edit'
        self.settingsState = 'edit'

    #
    # set no QGIS project

    def qgisSetNoProject(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.leQgsProject.setText('')
        self.qgsProject = ''
        self.tblBaseGroups.clear()
        self.baseGroups = []
        self.cbBoundaryLayer.clear()
        self.boundaryLayer = ''
        self.cbEnableReference.setCurrentIndex(0)
        self.enableReference = False
        self.cbReferenceLayer.clear()
        self.cbReferenceLayer.setDisabled(True)
        self.referenceLayer = ''
        
    #
    # read QGIS proejct

    def qgisReadProject(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        projectName = QtGui.QFileDialog.getOpenFileName(self, 'Select QGIS project', self.dirName, '*.qgs')
        if os.path.exists(projectName):
            self.qgsProjectChanged = True
            self.leQgsProject.setText(projectName)
            self.qgsProject = projectName
            self.qgisLoadProject(projectName)
        else:
            self.qgisSetNoProject()
        self.settingsEnableEdit()

    #
    # load QgsProject

    def qgisLoadProject( self, projectName ):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        s = QtCore.QSettings()
        if QgsProject.instance().fileName() <> projectName:
            self.iface.newProject()
            result = QgsProject.instance().read(QtCore.QFileInfo(projectName))
        else:
            result = True
        self.projectGroups = self.iface.legendInterface().groups()
        self.cbProjectGroups.clear()
        self.cbProjectGroups.addItems(self.projectGroups)
        if result == True:
            self.qgsProject = projectName
            # add info if group is valid
            self.leQgsProject.setText(projectName)
            rv = s.value('mapBiographer/baseGroups')
            self.tblBaseGroups.clear()
            self.tblBaseGroups.setColumnCount(1)
            self.tblBaseGroups.setColumnWidth(0,250)
            header = []
            header.append('Base Map Group')
            self.tblBaseGroups.setHorizontalHeaderLabels(header)
            validGroups = []
            if rv <> None:
                for g in rv:
                    if g in self.projectGroups:
                        validGroups.append(g)
            if len(validGroups) > 0:
                self.tblBaseGroups.setRowCount(len(rv))
                # add content
                x = 0
                for rec in validGroups:
                    item = QtGui.QTableWidgetItem()
                    item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                    item.setText(str(rec))
                    item.setToolTip('Base Map Group')
                    self.tblBaseGroups.setItem(x,0,item)
                    x = x + 1
                self.baseGroups = validGroups
            # set boundary layer
            rv = s.value('mapBiographer/boundaryLayer')
            self.projectLayers = []
            self.cbBoundaryLayer.clear()
            self.cbReferenceLayer.clear()
            layers = self.iface.legendInterface().layers()
            for layer in layers:
                self.projectLayers.append(layer.name())
                self.cbBoundaryLayer.addItem(layer.name())
                self.cbReferenceLayer.addItem(layer.name())
            if rv in self.projectLayers:
                self.cbBoundaryLayer.setCurrentIndex(self.projectLayers.index(rv))
                self.boundaryLayer = rv
            else:
                self.cbBoundaryLayer.setCurrentIndex(0)
                self.boundaryLayer = self.projectLayers[0]
            # check if reference layer used and load if applicable
            rv = s.value('mapBiographer/enableReference')
            if rv == 'True':
                self.cbEnableReference.setCurrentIndex(1)
                self.cbReferenceLayer.setEnabled(True)
                self.enableReference = True
                rv = s.value('mapBiographer/referenceLayer')
                if rv in self.projectLayers:
                    self.cbReferenceLayer.setCurrentIndex(self.projectLayers.index(rv))
                    self.referenceLayer = rv
                else:
                    self.cbReferenceLayer.setCurrentIndex(0)
                    self.referenceLayer = self.projectLayers[0]
            else:
                self.cbEnableReference.setCurrentIndex(0)
                self.cbReferenceLayer.setDisabled(True)
                self.enableReference = False
                self.referenceLayer = ''
        self.qgsProjectChange = False

    #
    # enable base group removal

    def baseGroupEnableRemoval(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        if len(self.tblBaseGroups.selectedItems()) > 0:
            self.pbRemoveBaseGroup.setEnabled(True)
        else:
            self.pbRemoveBaseGroup.setDisabled(True)

    #
    # add base groups

    def baseGroupAdd(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        idx = self.cbProjectGroups.currentIndex()
        grp = self.projectGroups[idx]
        tblIdx = len(self.baseGroups)
        self.tblBaseGroups.setRowCount(tblIdx+1)
        if not (grp in self.baseGroups):
            # add to table
            item = QtGui.QTableWidgetItem()
            item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            item.setText(str(grp))
            item.setToolTip('Base Map Group')
            self.tblBaseGroups.setItem(tblIdx,0,item)
            # add to list
            self.baseGroups.append(grp)
        self.settingsEnableEdit()
        
    #
    # remove base groups

    def baseGroupRemove(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())

        txt = self.tblBaseGroups.currentItem().text()
        self.tblBaseGroups.removeRow(self.tblBaseGroups.currentRow())
        self.baseGroups.remove(txt)
        self.settingsEnableEdit()

    #
    # udpate boundary

    def boundaryLayerUpdate(self):

        if self.settingsState <> 'load':
            if self.debug:
                QgsMessageLog.logMessage(self.myself())
            #
            if self.cbBoundaryLayer.count() > 0:
                idx = self.cbBoundaryLayer.currentIndex()
                if idx < 0:
                    idx = 0
                self.boundaryLayer = self.projectLayers[idx]
                self.settingsEnableEdit()

    #
    # enable reference layer

    def referenceLayerSetStatus(self):

        if self.settingsState <> 'load':
            if self.debug:
                QgsMessageLog.logMessage(self.myself())
            #
            if self.cbEnableReference.currentIndex() == 0:
                self.cbReferenceLayer.setDisabled(True)
                self.enableReference = False
                self.referenceLayer = ''
            else:
                self.cbReferenceLayer.setEnabled(True)
                self.enableReference = True
                self.cbReferenceLayer.setCurrentIndex(0)
                self.referenceLayer = self.projectLayers[0]
            self.settingsEnableEdit()

    #
    # update reference

    def referenceLayerUpdate(self):

        if self.settingsState <> 'load':
            if self.debug:
                QgsMessageLog.logMessage(self.myself())
            #
            if self.enableReference == True and self.cbReferenceLayer.count() > 0:
                idx = self.cbReferenceLayer.currentIndex()
                if idx < 0:
                    idx = 0
                self.referenceLayer = self.projectLayers[idx]
                self.settingsEnableEdit()



    ########################################################
    #                   database functions                 #
    ########################################################

    #
    # create database

    def dbCreate(self, dbName):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # connect
        # note that this first act creates a blank file on the disk
        self.conn = sqlite.connect(dbName)
        self.cur = self.conn.cursor()
        # create actual database with information
        sql = "SELECT InitSpatialMetadata()"
        self.cur.execute(sql)
        # create necessary tables
        self.dbCreateTables()
        # close
        self.conn.close()

    #
    # open database

    def dbOpen(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # connect
        self.conn = sqlite.connect(os.path.join(self.dirName,self.projectDB))
        self.cur = self.conn.cursor()

    #
    # close database
    
    def dbClose(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # disconnect
        self.cur = None
        self.conn.close()

    #
    # read database

    def dbRead(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.projectTableRead()
        self.participantListRead()
        self.interviewListRead()

    #
    # create tables

    def dbCreateTables(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        # create project table
        sql = "CREATE TABLE project ("
        sql += "id INTEGER NOT NULL PRIMARY KEY, "
        sql += "code TEXT, "
        sql += "description TEXT, "
        sql += "note TEXT, "
        sql += "tags TEXT, "
        sql += "data_status TEXT, "
        sql += "content_codes TEXT, "
        sql += "default_codes TEXT, "
        sql += "dates_and_times TEXT,"
        sql += "times_of_year TEXT, "
        sql += "date_created TEXT, "
        sql += "date_modified TEXT)"
        self.cur.execute(sql)
        # insert a new record into the projects table
        modDate = datetime.datetime.now().isoformat()[:10]
        sql = "INSERT into project (id, code, description, note, tags, "
        sql += "data_status, content_codes, "
        sql += "dates_and_times, times_of_year, date_created, date_modified) "
        sql += "VALUES (%d, '%s', '%s', '%s', '%s', " % (1, 'NEW1', 'New Project', '', '')
        sql += "'%s', '%s', " % ('N', '')
        sql += "'%s', '%s', '%s', '%s');" % ('', '', modDate, modDate)
        self.cur.execute(sql)
        # create participants table
        sql = "CREATE TABLE participants ("
        sql += "id INTEGER NOT NULL PRIMARY KEY, "
        sql += "participant_code TEXT, "
        sql += "first_name TEXT, "
        sql += "last_name TEXT,"
        sql += "email_address TEXT, "
        sql += "community TEXT, "
        sql += "family TEXT, "
        sql += "maiden_name TEXT, "
        sql += "gender TEXT, "
        sql += "marital_status TEXT, "
        sql += "birth_date TEXT, "
        sql += "tags TEXT,"
        sql += "note TEXT,"
        sql += "date_created TEXT, "
        sql += "date_modified TEXT )"
        self.cur.execute(sql)
        # create participants address table
        sql = "CREATE TABLE addresses ("
        sql += "id INTEGER NOT NULL PRIMARY KEY, "
        sql += "participant_id INTEGER, "
        sql += "address_type TEXT, "
        sql += "line_one TEXT, "
        sql += "line_two TEXT, "
        sql += "city TEXT, "
        sql += "province TEXT, "
        sql += "country TEXT, "
        sql += "postal_code TEXT, "
        sql += "date_created TEXT, "
        sql += "date_modified TEXT, "
        sql += "FOREIGN KEY(participant_id) REFERENCES participants(id) )"
        self.cur.execute(sql)
        # create participants telecom table
        sql = "CREATE TABLE telecoms ("
        sql += "id INTEGER NOT NULL PRIMARY KEY, "
        sql += "participant_id INTEGER, "
        sql += "telecom_type TEXT, "
        sql += "telecom TEXT, "
        sql += "date_created TEXT, "
        sql += "date_modified TEXT, "
        sql += "FOREIGN KEY(participant_id) REFERENCES participants(id) )"
        self.cur.execute(sql)
        # create interviews table
        sql = "CREATE TABLE interviews ("
        sql += "id INTEGER NOT NULL PRIMARY KEY, "
        sql += "project_id INTEGER, "
        sql += "code TEXT, "
        sql += "start_datetime TEXT, "
        sql += "end_datetime TEXT, "
        sql += "description TEXT, "
        sql += "interview_location TEXT, "
        sql += "note TEXT, "
        sql += "tags TEXT, "
        sql += "data_status TEXT, "
        sql += "data_security TEXT, "
        sql += "interviewer TEXT, "
        sql += "date_created TEXT, "
        sql += "date_modified TEXT,"
        sql += "FOREIGN KEY(project_id) REFERENCES project(id) )"
        self.cur.execute(sql)
        # create interview participants table
        sql = "CREATE TABLE interviewees ("
        sql += "id INTEGER NOT NULL PRIMARY KEY, "
        sql += "interview_id INTEGER, "
        sql += "participant_id INTEGER, "
        sql += "community TEXT, "
        sql += "family TEXT, "
        sql += "date_created TEXT, "
        sql += "date_modified TEXT, "
        sql += "FOREIGN KEY(interview_id) REFERENCES interviews(id), "
        sql += "FOREIGN KEY(participant_id) REFERENCES participants(id) )"
        self.cur.execute(sql)
        # create sections table
        sql = "CREATE TABLE interview_sections ("
        sql += "id INTEGER NOT NULL PRIMARY KEY, "
        sql += "interview_id INTEGER, "
        sql += "sequence_number INTEGER, "
        sql += "primary_code TEXT, "
        sql += "section_code TEXT, "
        sql += "section_text TEXT, "
        sql += "note TEXT, "
        sql += "date_time TEXT, "
        sql += "date_time_start TEXT, "
        sql += "date_time_end TEXT, "
        sql += "time_of_year TEXT, "
        sql += "time_of_year_months TEXT, "
        sql += "spatial_data_source TEXT, "
        sql += "spatial_data_scale TEXT, "
        sql += "geom_source TEXT, "
        sql += "content_codes TEXT, "
        sql += "tags TEXT, "
        sql += "media_start_time TEXT, "
        sql += "media_end_time TEXT, "
        sql += "data_security TEXT, "
        sql += "date_created TEXT, "
        sql += "date_modified TEXT, "
        sql += "media_files TEXT, "
        sql += "FOREIGN KEY(interview_id) REFERENCES interviews(id) )"
        self.cur.execute(sql)
        # create points table
        sql = "CREATE TABLE points ("
        sql += "id INTEGER NOT NULL PRIMARY KEY, "
        sql += "interview_id INTEGER, "
        sql += "section_id INTEGER, "
        sql += "section_code TEXT, "
        sql += "content_code TEXT, "
        sql += "date_created TEXT, "
        sql += "date_modified TEXT, "
        sql += "FOREIGN KEY(interview_id) REFERENCES interviews(id), "
        sql += "FOREIGN KEY(section_id) REFERENCES interview_sections(id) )"
        self.cur.execute(sql)
        sql = "SELECT AddGeometryColumn('points', "
        sql += "'geom', 3857, 'MULTIPOINT', 'XY')"
        self.cur.execute(sql)
        # create lines table
        sql = "CREATE TABLE lines ("
        sql += "id INTEGER NOT NULL PRIMARY KEY, "
        sql += "interview_id INTEGER, "
        sql += "section_id INTEGER, "
        sql += "section_code TEXT, "
        sql += "content_code TEXT, "
        sql += "date_created TEXT, "
        sql += "date_modified TEXT, "
        sql += "FOREIGN KEY(interview_id) REFERENCES interviews(id), "
        sql += "FOREIGN KEY(section_id) REFERENCES interview_sections(id) )"
        self.cur.execute(sql)
        sql = "SELECT AddGeometryColumn('lines', "
        sql += "'geom', 3857, 'MULTILINESTRING', 'XY')"
        self.cur.execute(sql)
        # create polygon table
        sql = "CREATE TABLE polygons ("
        sql += "id INTEGER NOT NULL PRIMARY KEY, "
        sql += "interview_id INTEGER, "
        sql += "section_id INTEGER, "
        sql += "section_code TEXT, "
        sql += "content_code TEXT, "
        sql += "date_created TEXT, "
        sql += "date_modified TEXT, "
        sql += "FOREIGN KEY(interview_id) REFERENCES interviews(id), "
        sql += "FOREIGN KEY(section_id) REFERENCES interview_sections(id) )"
        self.cur.execute(sql)
        sql = "SELECT AddGeometryColumn('polygons', "
        sql += "'geom', 3857, 'MULTIPOLYGON', 'XY')"
        self.cur.execute(sql)
        self.conn.commit()


    ########################################################
    #               projects tab functions                 #
    ########################################################

    #
    # enable project

    def projectEnable(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # main tabs
        self.tbProjectDetails.setEnabled(True)
        self.tbPeople.setEnabled(True)
        self.tbInterviews.setEnabled(True)
        self.pbTransfer.setEnabled(True)
        
    #
    # disable project

    def projectDisable(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # main tabs
        self.tbProjectDetails.setDisabled(True)
        self.tbPeople.setDisabled(True)
        self.tbInterviews.setDisabled(True)
        self.pbTransfer.setDisabled(True)
        
    #
    # enable project edit

    def projectEnableEdit(self):

        if self.projectState <> 'load' and self.pbDialogClose.isEnabled():
            if self.debug:
                QgsMessageLog.logMessage(self.myself())
            # other tabs & main control
            self.pbDialogClose.setDisabled(True)
            self.twMapBioSettings.tabBar().setDisabled(True)
            # controls on this tab
            self.pbProjectSave.setEnabled(True)
            self.pbProjectCancel.setEnabled(True)
            # dialog close
            self.pbDialogClose.setDisabled(True)

    #
    # disable project edit

    def projectDisableEdit(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # other tabs & main control
        self.pbDialogClose.setEnabled(True)
        self.twMapBioSettings.tabBar().setEnabled(True)
        # controls on this tab
        self.pbProjectSave.setDisabled(True)
        self.pbProjectCancel.setDisabled(True)
        # dialog close
        self.pbDialogClose.setEnabled(True)

    #
    # process project content codes

    def projectParseProjectCodes(self,codes,defaults):

        self.projCodes = []
        self.projDefs = []
        codeList = codes.split('\n')
        codeList.sort()
        for item in codeList:
            if item <> '' and '=' in item:
                code, defn = item.split('=')
                if code <> '' and defn <> '':
                    self.projCodes.append(code.strip())
                    self.projDefs.append(defn.strip())
                    self.cbDefaultCode.addItem(defn.strip())
                    self.cbPointCode.addItem(defn.strip())
                    self.cbLineCode.addItem(defn.strip())
                    self.cbPolygonCode.addItem(defn.strip())
        if len(codeList) > 0 and not defaults is None and defaults <> '':
            dCodes = defaults.split('|||')
            for dc in dCodes:
                dDef,dCode = dc.split('||')
                if dDef == 'dfc':
                    if dCode in self.projCodes:
                        idx = self.projCodes.index(dCode)
                    else:
                        idx = 0
                    self.cbDefaultCode.setCurrentIndex(idx)
                if dDef == 'ptc':
                    if dCode in self.projCodes:
                        idx = self.projCodes.index(dCode)
                    else:
                        idx = 0
                    self.cbPointCode.setCurrentIndex(idx)
                if dDef == 'lnc':
                    if dCode in self.projCodes:
                        idx = self.projCodes.index(dCode)
                    else:
                        idx = 0
                    self.cbLineCode.setCurrentIndex(idx)
                if dDef == 'plc':
                    if dCode in self.projCodes:
                        idx = self.projCodes.index(dCode)
                    else:
                        idx = 0
                    self.cbPolygonCode.setCurrentIndex(idx)
        
    #
    # refresh project codes

    def projectRefreshCodes(self):

        codes = self.pteContentCodes.document().toPlainText()
        if self.projCodes <> []:
            dfc = self.projCodes[self.cbDefaultCode.currentIndex()]
            ptc = self.projCodes[self.cbPointCode.currentIndex()]
            lnc = self.projCodes[self.cbLineCode.currentIndex()]
            plc = self.projCodes[self.cbPolygonCode.currentIndex()]
            defaultCodes = 'dfc||%s|||ptc||%s|||lnc||%s|||plc||%s' % (dfc,ptc,lnc,plc)
        else:
            defaultCodes = ''
        self.cbDefaultCode.clear()
        self.cbPointCode.clear()
        self.cbLineCode.clear()
        self.cbPolygonCode.clear()
        self.projectParseProjectCodes(codes,defaultCodes)
        
    #
    # read project table
    
    def projectTableRead(self):

        self.projectState = 'load'

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        sql = "SELECT id, code, description, note, tags, "
        sql += "content_codes, dates_and_times, "
        sql += "times_of_year, date_created, default_codes FROM project;"
        rs = self.cur.execute(sql)
        projData = rs.fetchall()
        self.projId = int(projData[0][0])
        if len(projData) > 0:
            self.leProjectCode.setText(projData[0][1])
            self.pteProjectDescription.setPlainText(projData[0][2])
            self.pteProjectNote.setPlainText(projData[0][3])
            self.leProjectTags.setText(projData[0][4])
            self.pteContentCodes.setPlainText(projData[0][5])
            self.pteDateAndTime.setPlainText(projData[0][6])
            self.pteTimeOfYear.setPlainText(projData[0][7])
            self.cbDefaultCode.clear()
            self.cbPointCode.clear()
            self.cbLineCode.clear()
            self.cbPolygonCode.clear()
            if projData[0][5] <> '':
                self.projectParseProjectCodes(projData[0][5],projData[0][9])
            self.projDate = projData[0][8]

        self.projectState = 'edit'

    # 
    # update project table
    
    def projectTableWrite(self):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        sql = "SELECT max(id) FROM project;"
        rs = self.cur.execute(sql)
        projData = rs.fetchall()
        code = self.leProjectCode.text()
        description = self.pteProjectDescription.document().toPlainText()
        tags = self.leProjectTags.text()
        note = self.pteProjectNote.document().toPlainText()
        dataStatus = 'N'
        contentCodes = self.pteContentCodes.document().toPlainText()
        datesTimes = self.pteDateAndTime.document().toPlainText()
        timesOfYear = self.pteTimeOfYear.document().toPlainText()
        dfc = self.projCodes[self.cbDefaultCode.currentIndex()]
        ptc = self.projCodes[self.cbPointCode.currentIndex()]
        lnc = self.projCodes[self.cbLineCode.currentIndex()]
        plc = self.projCodes[self.cbPolygonCode.currentIndex()]
        defaultCodes = 'dfc||%s|||ptc||%s|||lnc||%s|||plc||%s' % (dfc,ptc,lnc,plc)
        if self.projDate == None or self.projDate == '':
            createDate = datetime.datetime.now().isoformat()[:10]
            modDate = createDate
        else:
            createDate = self.projDate
            modDate = datetime.datetime.now().isoformat()[:10] 
        if projData[0][0] == None:
            sql = "INSERT INTO project (id, code, description, note, tags, "
            sql += "data_status, content_codes, default_codes"
            sql += "dates_and_times, times_of_year, date_created, date_modified) "
            sql += "VALUES (%d, '%s', '%s', '%s', '%s', " % (1, code, description, note, tags)
            sql += "'%s', '%s', '%s', " % (dataStatus, contentCodes, defaultCodes)
            sql += "'%s', '%s', '%s', '%s');" % (datesTimes, timesOfYear, createDate, modDate)
        else:
            sql = "UPDATE project SET "
            sql += "code = '%s', " % code
            sql += "description = '%s', " % description
            sql += "note = '%s', " % note
            sql += "tags = '%s', " % tags
            sql += "data_status = '%s', " % dataStatus
            sql += "content_codes = '%s', " % contentCodes
            sql += "default_codes = '%s' , " % defaultCodes
            sql += "dates_and_times = '%s', " % datesTimes
            sql += "times_of_year = '%s', " % timesOfYear
            sql += "date_created = '%s', " % createDate
            sql += "date_modified = '%s' " % modDate
            sql += "WHERE id = %d;" % self.projId
        self.cur.execute(sql)
        self.conn.commit()
        self.projectDisableEdit()

    #
    # cancel project table updates

    def projectTableCancel(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.projectTableRead()
        self.projectDisableEdit()


    ########################################################
    #               manage participant tables              #
    ########################################################

    #
    # add / update participant record to participant table widget

    def participantSet(self,x,rec):

        # id
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[0]))
        item.setToolTip('Map Biographer Participant Id')
        self.tblParticipants.setItem(x,0,item)
        # user name
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[1]))
        item.setToolTip('Participant Code')
        self.tblParticipants.setItem(x,1,item)
        # first name
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[2]))
        item.setToolTip('First Name')
        self.tblParticipants.setItem(x,2,item)
        # last name
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[3]))
        item.setToolTip('Last Name')
        self.tblParticipants.setItem(x,3,item)

    #
    # read participant list

    def participantListRead(self):
            
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        sql = "SELECT id, participant_code, first_name, last_name FROM participants;"
        rs = self.cur.execute(sql)
        partData = rs.fetchall()
        # clear old data and setup row and column counts
        self.tblParticipants.clear()
        self.tblParticipants.setColumnCount(4)
        self.tblParticipants.setRowCount(len(partData))
        # set header
        header = []
        header.append('Id')
        header.append('Participant Code')
        header.append('First Name')
        header.append('Last Name')
        self.tblParticipants.setHorizontalHeaderLabels(header)
        # add content
        x = 0
        for rec in partData:
            self.participantSet(x,rec)
            x = x + 1
        self.tblParticipants.setColumnWidth(0,75)
        self.tblParticipants.setColumnWidth(1,150)
        self.tblParticipants.setColumnWidth(2,200)
        self.tblParticipants.setColumnWidth(3,200)

    #
    # check if participant is selected or unselected
    
    def participantCheckSelection(self):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        if len(self.tblParticipants.selectedItems()) == 0:
            # change widget states
            self.participantDisableEdit()
        else:
            # change widget states
            self.participantEnableEdit()
            # read information
            self.participantRead()

    #
    # set edit of participant

    def participantEnableEdit(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        # other tabs & main control
        self.pbDialogClose.setDisabled(True)
        self.twMapBioSettings.tabBar().setDisabled(True)
        # controls on this tab
        self.tblParticipants.setDisabled(True)
        self.pbParticipantNew.setDisabled(True)
        self.pbParticipantSave.setEnabled(True)
        self.pbParticipantCancel.setEnabled(True)
        self.pbParticipantDelete.setEnabled(True)
        self.tbxParticipants.setEnabled(True)
        self.tbxParticipants.setCurrentWidget(self.pgBasicInfo)

    #
    # disable edit of participant

    def participantDisableEdit(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        # other tabs
        self.pbDialogClose.setEnabled(True)
        self.twMapBioSettings.tabBar().setEnabled(True)
        # controls on this tab
        self.participantClearValues()
        self.tblParticipants.setEnabled(True)
        self.pbParticipantNew.setEnabled(True)
        self.pbParticipantSave.setDisabled(True)
        self.pbParticipantCancel.setDisabled(True)
        self.pbParticipantDelete.setDisabled(True)
        self.pgAddresses.setEnabled(True)
        self.pgTelecoms.setEnabled(True)
        self.tbxParticipants.setDisabled(True)
        self.tbxParticipants.setCurrentWidget(self.pgBasicInfo)

    #
    # clear participant values

    def participantClearValues(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.leParticipantCode.setText('')
        self.leFirstName.setText('')
        self.leLastName.setText('')
        self.leEmail.setText('')
        self.leCommunity.setText('')
        self.leFamily.setText('')
        self.leMaidenName.setText('')
        self.cbGender.setCurrentIndex(0)
        self.leBirthDate.setText('')
        self.cbMaritalStatus.setCurrentIndex(0)
        self.leParticipantTags.setText('')
        self.pteParticipantNote.setPlainText('')
        self.addressClear()
        self.telecomClear()
        
    #
    # new participant

    def participantNew(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.participantClearValues()
        self.participantEnableEdit()
        self.pgAddresses.setDisabled(True)
        self.pgTelecoms.setDisabled(True)
        sql = "SELECT max(id) FROM participants;"
        rs = self.cur.execute(sql)
        partData = rs.fetchall()
        if partData[0][0] == None:
            pass
        else:
            self.partId = int(partData[0][0]) + 1
        self.leParticipantCode.setFocus()

    #
    # cancel participant edits

    def participantCancelEdit(self):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.participantClearValues()
        self.participantDisableEdit()
        row = self.tblParticipants.currentRow()
        self.tblParticipants.setItemSelected(self.tblParticipants.item(row,0),False)
        self.tblParticipants.setItemSelected(self.tblParticipants.item(row,1),False)
        self.tblParticipants.setItemSelected(self.tblParticipants.item(row,2),False)
        self.tblParticipants.setItemSelected(self.tblParticipants.item(row,3),False)

    #
    # read participant

    def participantRead(self):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.tbxParticipants.setEnabled(True)
        row = int(self.tblParticipants.currentRow())
        self.partId = int(self.tblParticipants.item(row,0).text())
        sql = "SELECT id, participant_code, first_name, last_name, "
        sql += "email_address, community, family, maiden_name, "
        sql += "gender, marital_status, birth_date, tags, note, "
        sql += "date_created FROM participants WHERE id = %d" % self.partId
        rs = self.cur.execute(sql)
        partData = rs.fetchall()
        self.leParticipantCode.setText(partData[0][1])
        self.leFirstName.setText(partData[0][2])
        self.leLastName.setText(partData[0][3])
        self.leEmail.setText(partData[0][4])
        self.leCommunity.setText(partData[0][5])
        self.leFamily.setText(partData[0][6])
        self.leMaidenName.setText(partData[0][7])
        if partData[0][8] == 'M':
            self.cbGender.setCurrentIndex(1)
        elif partData[0][8] == 'F':
            self.cbGender.setCurrentIndex(2)
        elif partData[0][8] == 'R':
            self.cbGender.setCurrentIndex(3)
        elif partData[0][8] == 'O':
            self.cbGender.setCurrentIndex(4)
        else:
            self.cbGender.setCurrentIndex(0)
        if partData[0][9] == 'S':
            self.cbMaritalStatus.setCurrentIndex(1)
        elif partData[0][9] == 'M':
            self.cbMaritalStatus.setCurrentIndex(2)
        elif partData[0][9] == 'D':
            self.cbMaritalStatus.setCurrentIndex(3)
        elif partData[0][9] == 'R':
            self.cbMaritalStatus.setCurrentIndex(4)
        elif partData[0][9] == 'O':
            self.cbMaritalStatus.setCurrentIndex(5)
        else:
            self.cbMaritalStatus.setCurrentIndex(0)
        self.leBirthDate.setText(partData[0][10])
        self.leParticipantTags.setText(partData[0][11])
        self.pteParticipantNote.setPlainText(partData[0][12])
        self.addressListRead()
        self.telecomListRead()
        self.contDate = partData[0][13]

    #
    # update participant

    def participantWrite(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        sql = "SELECT max(id) FROM participants;"
        rs = self.cur.execute(sql)
        partData = rs.fetchall()
        partCode = self.leParticipantCode.text()
        firstName = self.leFirstName.text()
        lastName = self.leLastName.text()
        email = self.leEmail.text()
        community = self.leCommunity.text()
        family = self.leFamily.text()
        maidenName = self.leMaidenName.text()
        # gender
        if self.cbGender.currentIndex() == 1:
            gender = 'M'
        elif self.cbGender.currentIndex() == 2:
            gender = 'F'
        elif self.cbGender.currentIndex() == 3:
            gender = 'R'
        elif self.cbGender.currentIndex() == 4:
            gender = 'O'
        else:
            gender = 'U'
        # marital status
        if self.cbMaritalStatus.currentIndex() == 1:
            maritalStatus = 'S'
        elif self.cbMaritalStatus.currentIndex() == 2:
            maritalStatus = 'M'
        elif self.cbMaritalStatus.currentIndex() == 3:
            maritalStatus = 'D'
        elif self.cbMaritalStatus.currentIndex() == 4:
            maritalStatus = 'R'
        elif self.cbMaritalStatus.currentIndex() == 5:
            maritalStatus = 'O'
        else:
            maritalStatus = 'U'
        birthDate = self.leBirthDate.text()
        tags = self.leParticipantTags.text()
        note = self.pteParticipantNote.document().toPlainText()
        if self.contDate == None or self.contDate == '':
            createDate = datetime.datetime.now().isoformat()[:10]
            modDate = createDate
        else:
            createDate = self.contDate
            modDate = datetime.datetime.now().isoformat()[:10] 
        if partData[0][0] == None or partData[0][0] < self.partId:
            sql = "SELECT count(*) FROM participants WHERE participant_code = '%s';" % partCode
            rs = self.cur.execute(sql)
            cntData = rs.fetchall()
            if cntData[0][0] == 0:
                commitOk = True
                sql = "INSERT into participants (id, participant_code, first_name, "
                sql += "last_name, email_address, community, family, "
                sql += "maiden_name, gender, marital_status, birth_date, tags, "
                sql += "note, date_created, date_modified) "
                sql += "VALUES (%d, '%s', '%s', '%s', '%s', " % (self.partId, partCode, firstName, lastName, email)
                sql += "'%s', '%s', '%s', '%s', " % (community, family, maidenName, gender)
                sql += "'%s', '%s', '%s', " % (maritalStatus, birthDate, tags)
                sql += "'%s', '%s', '%s');" % (note, createDate, modDate)
                rCnt = self.tblParticipants.rowCount()
                self.tblParticipants.setRowCount(rCnt+1)
                self.participantSet(rCnt, [self.partId,partCode,firstName,lastName])
            else:
                commitOk = False
        else:
            sql = "SELECT id FROM participants WHERE participant_code = '%s';" % partCode
            rs = self.cur.execute(sql)
            cntData = rs.fetchall()
            if cntData == [] or cntData[0][0] == self.partId:
                commitOk = True
                sql = "UPDATE participants SET "
                sql += "participant_code = '%s', " % partCode
                sql += "first_name = '%s', " % firstName
                sql += "last_name = '%s', " % lastName
                sql += "email_address = '%s', " % email
                sql += "community = '%s', " % community
                sql += "family = '%s', " % family
                sql += "maiden_name = '%s', " % maidenName
                sql += "gender = '%s', " % gender
                sql += "marital_status = '%s', " % maritalStatus
                sql += "birth_date = '%s', " % birthDate
                sql += "tags = '%s', " % tags
                sql += "note = '%s', " % note
                sql += "date_created = '%s', " % createDate
                sql += "date_modified = '%s' " % modDate
                sql += "where id = %d;" % self.partId
                self.participantSet(self.tblParticipants.currentRow(), [self.partId,partCode,firstName,lastName])
            else:
                commitOk = False
        if commitOk == True:
            self.cur.execute(sql)
            self.conn.commit()
            self.participantDisableEdit()
            row = self.tblParticipants.currentRow()
            self.tblParticipants.setItemSelected(self.tblParticipants.item(row,0),False)
            self.tblParticipants.setItemSelected(self.tblParticipants.item(row,1),False)
            self.tblParticipants.setItemSelected(self.tblParticipants.item(row,2),False)
            self.tblParticipants.setItemSelected(self.tblParticipants.item(row,3),False)
        else:
            messageText = "The Participant Code '%s' is not unique. " % partCode
            messageText += "Modify the code and try again to save."
            response = QtGui.QMessageBox.warning(self, 'Warning',
               messageText, QtGui.QMessageBox.Ok)
        
    #
    # delete participant

    def participantDelete(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        # check if participant
        sql = "SELECT count(*) FROM interviewees WHERE participant_id = %d" % self.partId
        rs = self.cur.execute(sql)
        confData = rs.fetchall()
        isParticipant = False
        if confData[0][0] > 0:
            isParticipant = True
        if isParticipant == True:
            QtGui.QMessageBox.warning(self, 'Warning',
               "Can not delete this person. Currently referenced in an interview.", QtGui.QMessageBox.Ok)
        else:
            # if ok cascade delete address records
            sql = "DELETE FROM addresses WHERE participant_id = %d" % self.partId
            self.cur.execute(sql)
            self.conn.commit()
            # cascade delete telecom records
            sql = "DELETE FROM telecoms WHERE participant_id = %d" % self.partId
            self.cur.execute(sql)
            self.conn.commit()
            # everything OK, delete main record
            sql = "DELETE FROM participants WHERE id = %d" % self.partId
            self.cur.execute(sql)
            self.conn.commit()
            self.participantDisableEdit()
            # remove row
            row = self.tblParticipants.currentRow()
            self.tblParticipants.removeRow(row)
        row = self.tblParticipants.currentRow()
        self.tblParticipants.setItemSelected(self.tblParticipants.item(row,0),False)
        self.tblParticipants.setItemSelected(self.tblParticipants.item(row,1),False)
        self.tblParticipants.setItemSelected(self.tblParticipants.item(row,2),False)
        self.tblParticipants.setItemSelected(self.tblParticipants.item(row,3),False)


    ########################################################
    #               manage participant addresses           #
    ########################################################
    
    #
    # add / update address record to participant address table widget

    def addressSet(self,x,rec):

        # id
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[0]))
        item.setToolTip('Map Biographer Participant Id')
        self.tblAddresses.setItem(x,0,item)
        # address type
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[1]))
        item.setToolTip('Type')
        self.tblAddresses.setItem(x,1,item)
        # line one
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[2]))
        item.setToolTip('Line One')
        self.tblAddresses.setItem(x,2,item)

    #
    # read participant address list

    def addressListRead(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        sql = "SELECT id, address_type, line_one FROM addresses "
        sql += "WHERE participant_id = %d" % self.partId
        rs = self.cur.execute(sql)
        addrData = rs.fetchall()
        # clear old data and setup row and column counts
        self.tblAddresses.clear()
        self.tblAddresses.setColumnCount(3)
        self.tblAddresses.setRowCount(len(addrData))
        # set header
        header = []
        header.append('Id')
        header.append('Type')
        header.append('Line One')
        self.tblAddresses.setHorizontalHeaderLabels(header)
        # add content
        x = 0
        for rec in addrData:
            self.addressSet(x,rec)
            x = x + 1
        self.tblAddresses.setColumnWidth(0,75)
        self.tblAddresses.setColumnWidth(1,50)
        self.tblAddresses.setColumnWidth(2,200)
        self.addressDisableEdit()

    #
    # check if address is selected or unselected
    
    def addressCheckSelection(self):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        if len(self.tblAddresses.selectedItems()) == 0:
            # change widget states
            self.addressDisableEdit()
        else:
            # change widget states
            self.addressEnableEdit()
            # read information
            self.addressRead()

    #
    # enable edit of address

    def addressEnableEdit(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        # other tool boxes
        self.pgBasicInfo.setDisabled(True)
        self.pgTelecoms.setDisabled(True)
        self.frPeopleControls.setDisabled(True)
        # other controls
        self.tblAddresses.setDisabled(True)
        self.pbAddNew.setDisabled(True)
        self.pbAddSave.setEnabled(True)
        self.pbAddCancel.setEnabled(True)
        self.pbAddDelete.setEnabled(True)
        self.pgBasicInfo.setDisabled(True)
        self.pgTelecoms.setDisabled(True)
        # address specific widgets
        self.cbAddType.setEnabled(True)
        self.leLineOne.setEnabled(True)
        self.leLineTwo.setEnabled(True)
        self.leCity.setEnabled(True)
        self.leProvince.setEnabled(True)
        self.leCountry.setEnabled(True)
        self.lePostalCode.setEnabled(True)

    #
    # disable edit of address

    def addressDisableEdit(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        # other tool boxes
        self.pgBasicInfo.setEnabled(True)
        self.pgTelecoms.setEnabled(True)
        self.frPeopleControls.setEnabled(True)
        # other controls
        self.addressClearValues()
        self.tblAddresses.setEnabled(True)
        self.pbAddNew.setEnabled(True)
        self.pbAddSave.setDisabled(True)
        self.pbAddCancel.setDisabled(True)
        self.pbAddDelete.setDisabled(True)
        self.pgBasicInfo.setEnabled(True)
        self.pgTelecoms.setEnabled(True)
        # address specific widgets
        self.cbAddType.setDisabled(True)
        self.leLineOne.setDisabled(True)
        self.leLineTwo.setDisabled(True)
        self.leCity.setDisabled(True)
        self.leProvince.setDisabled(True)
        self.leCountry.setDisabled(True)
        self.lePostalCode.setDisabled(True)

    #
    # clear address values

    def addressClearValues(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.cbAddType.setCurrentIndex(0)
        self.leLineOne.setText('')
        self.leLineTwo.setText('')
        self.leCity.setText('')
        self.leCity.setText('')
        self.leProvince.setText('')
        self.leCountry.setText('')
        self.lePostalCode.setText('')
        
    #
    # new address

    def addressNew(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.addressClearValues()
        self.addressEnableEdit()
        sql = "SELECT max(id) FROM addresses;"
        rs = self.cur.execute(sql)
        addrData = rs.fetchall()
        if addrData[0][0] == None:
            pass
        else:
            self.addrId = int(addrData[0][0]) + 1
        self.cbAddType.setFocus()
            
    #
    # cancel address edits

    def addressCancelEdit(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.addressClearValues()
        self.addressDisableEdit()
        row = self.tblAddresses.currentRow()
        self.tblAddresses.setItemSelected(self.tblAddresses.item(row,0),False)
        self.tblAddresses.setItemSelected(self.tblAddresses.item(row,1),False)
        self.tblAddresses.setItemSelected(self.tblAddresses.item(row,2),False)

    #
    # read address

    def addressRead(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        row = int(self.tblAddresses.currentRow())
        self.addrId = int(self.tblAddresses.item(row,0).text())
        sql = "SELECT * FROM addresses WHERE id = %d" % self.addrId
        rs = self.cur.execute(sql)
        addrData = rs.fetchall()
        if addrData[0][2] == 'H':
            self.cbAddType.setCurrentIndex(0)
        elif addrData[0][2] == 'W':
            self.cbAddType.setCurrentIndex(1)
        elif addrData[0][2] == 'P':
            self.cbAddType.setCurrentIndex(2)
        else:
            self.cbAddType.setCurrentIndex(3)
        self.leLineOne.setText(addrData[0][3])
        self.leLineTwo.setText(addrData[0][4])
        self.leCity.setText(addrData[0][5])
        self.leProvince.setText(addrData[0][6])
        self.leCountry.setText(addrData[0][7])
        self.lePostalCode.setText(addrData[0][8])
        self.addrDate = addrData[0][9]

    #
    # update address

    def addressWrite(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        sql = "SELECT max(id) FROM addresses WHERE participant_id = %d;" % self.partId
        rs = self.cur.execute(sql)
        addrData = rs.fetchall()
        if self.cbAddType.currentIndex() == 0:
            addrType = 'H'
        elif self.cbAddType.currentIndex() == 1:
            addrType = 'W'
        elif self.cbAddType.currentIndex() == 2:
            addrType = 'P'
        else:
            addrType = 'O'
        lineOne = self.leLineOne.text()
        lineTwo = self.leLineTwo.text()
        city = self.leCity.text()
        province = self.leProvince.text()
        country = self.leCountry.text()
        postalCode = self.lePostalCode.text()
        if self.addrDate == None or self.addrDate == '':
            createDate = datetime.datetime.now().isoformat()[:10]
            modDate = createDate
        else:
            createDate = self.addrDate
            modDate = datetime.datetime.now().isoformat()[:10] 
        if addrData[0][0] == None or addrData[0][0] < self.addrId:
            sql = "INSERT into addresses (id, participant_id, address_type, "
            sql += "line_one, line_two, city, province, "
            sql += "country, postal_code, date_created, date_modified) "
            sql += "VALUES (%d, %d,  " % (self.addrId, self.partId)
            sql += "'%s', '%s', '%s', " % (addrType, lineOne, lineTwo)
            sql += "'%s', '%s', '%s', '%s', " % (city, province, country, postalCode)
            sql += "'%s', '%s');" % (createDate, modDate)
            rCnt = self.tblAddresses.rowCount()
            self.tblAddresses.setRowCount(rCnt+1)
            self.addressSet(rCnt, [self.addrId, addrType, lineOne])
        else:
            sql = "UPDATE addresses SET "
            sql += "address_type = '%s', " % addrType
            sql += "line_one = '%s', " % lineOne
            sql += "line_two = '%s', " % lineTwo
            sql += "city = '%s', " % city
            sql += "province = '%s', " % province
            sql += "country = '%s', " % country
            sql += "postal_code = '%s', " % postalCode
            sql += "date_created = '%s', " % createDate
            sql += "date_modified = '%s' " % modDate
            sql += "where id = %d;" % self.addrId
            self.addressSet(self.tblAddresses.currentRow(), [self.addrId, addrType, lineOne])
        self.cur.execute(sql)
        self.conn.commit()

        self.addressDisableEdit()
        row = self.tblAddresses.currentRow()
        self.tblAddresses.setItemSelected(self.tblAddresses.item(row,0),False)
        self.tblAddresses.setItemSelected(self.tblAddresses.item(row,1),False)
        self.tblAddresses.setItemSelected(self.tblAddresses.item(row,2),False)
        
    #
    # delete address
    
    def addressDelete(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        sql = "DELETE FROM addresses WHERE id = %d" % self.addrId
        self.cur.execute(sql)
        self.conn.commit()
        self.addressClearValues()
        self.addressDisableEdit()
        # remove row
        row = self.tblAddresses.currentRow()
        self.tblAddresses.removeRow(row)
        row = self.tblAddresses.currentRow()
        self.tblAddresses.setItemSelected(self.tblAddresses.item(row,0),False)
        self.tblAddresses.setItemSelected(self.tblAddresses.item(row,1),False)
        self.tblAddresses.setItemSelected(self.tblAddresses.item(row,2),False)

    #
    # clear address widgets

    def addressClear(self):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.tblAddresses.clear()
        

    ########################################################
    #           manage participant telecoms                #
    ########################################################
    
    #
    # add / update participant telecom record to telecom table widget

    def telecomSet(self,x,rec):

        # id
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[0]))
        item.setToolTip('Map Biographer Participant Id')
        self.tblTelecoms.setItem(x,0,item)
        # user name
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[1]))
        item.setToolTip('Type')
        self.tblTelecoms.setItem(x,1,item)
        # first name
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[2]))
        item.setToolTip('Telecom')
        self.tblTelecoms.setItem(x,2,item)

    #
    # read participant telecom list

    def telecomListRead(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        sql = "SELECT id, telecom_type, telecom FROM telecoms "
        sql += "WHERE participant_id = %d" % self.partId
        rs = self.cur.execute(sql)
        telData = rs.fetchall()
       # clear old data and setup row and column counts
        self.tblTelecoms.clear()
        self.tblTelecoms.setColumnCount(3)
        self.tblTelecoms.setRowCount(len(telData))
        # set header
        header = []
        header.append('Id')
        header.append('Type')
        header.append('Telecom')
        self.tblTelecoms.setHorizontalHeaderLabels(header)
        # add content
        x = 0
        for rec in telData:
            self.telecomSet(x,rec)
            x = x + 1
        self.tblTelecoms.setColumnWidth(0,75)
        self.tblTelecoms.setColumnWidth(1,50)
        self.tblTelecoms.setColumnWidth(2,200)
        self.telecomDisableEdit()

    #
    # check if telecom is selected or unselected
    
    def telecomCheckSelection(self):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        if len(self.tblTelecoms.selectedItems()) == 0:
            # change widget states
            self.telecomDisableEdit()
        else:
            # change widget states
            self.telecomEnableEdit()
            # read information
            self.telecomRead()

    #
    # set edit of telecom

    def telecomEnableEdit(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        # other tool boxes
        self.pgBasicInfo.setDisabled(True)
        self.pgAddresses.setDisabled(True)
        self.frPeopleControls.setDisabled(True)
        # other controls
        self.tblTelecoms.setDisabled(True)
        self.pbTelNew.setDisabled(True)
        self.pbTelSave.setEnabled(True)
        self.pbTelCancel.setEnabled(True)
        self.pbTelDelete.setEnabled(True)
        self.pgBasicInfo.setDisabled(True)
        self.pgAddresses.setDisabled(True)
        # telecom specific widgets
        self.cbTelType.setEnabled(True)
        self.leTelNumber.setEnabled(True)

    #
    # disable edit of telecom

    def telecomDisableEdit(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        # other tool boxes
        self.pgBasicInfo.setEnabled(True)
        self.pgAddresses.setEnabled(True)
        self.frPeopleControls.setEnabled(True)
        # other controls
        self.telecomClearValues()
        self.tblTelecoms.setEnabled(True)
        self.pbTelNew.setEnabled(True)
        self.pbTelSave.setDisabled(True)
        self.pbTelCancel.setDisabled(True)
        self.pbTelDelete.setDisabled(True)
        self.pgBasicInfo.setEnabled(True)
        self.pgAddresses.setEnabled(True)
        # telecom specific widgets
        self.cbTelType.setDisabled(True)
        self.leTelNumber.setDisabled(True)

    #
    # clear telecom values

    def telecomClearValues(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.cbTelType.setCurrentIndex(0)
        self.leTelNumber.setText('')
        
    #
    # new telecom

    def telecomNew(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.telecomClearValues()
        self.telecomEnableEdit()
        sql = "SELECT max(id) FROM telecoms;"
        rs = self.cur.execute(sql)
        telData = rs.fetchall()
        if telData[0][0] == None:
            pass
        else:
            self.teleId = int(telData[0][0]) + 1
        self.cbTelType.setFocus()
        
    #
    # cancel telecom edits

    def telecomCancelEdits(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.telecomClearValues()
        self.telecomDisableEdit()
        row = self.tblTelecoms.currentRow()
        self.tblTelecoms.setItemSelected(self.tblTelecoms.item(row,0),False)
        self.tblTelecoms.setItemSelected(self.tblTelecoms.item(row,1),False)
        self.tblTelecoms.setItemSelected(self.tblTelecoms.item(row,2),False)

    #
    # read telecom

    def telecomRead(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        row = int(self.tblTelecoms.currentRow())
        self.telelId = int(self.tblTelecoms.item(row,0).text())
        sql = "SELECT * FROM telecoms WHERE id = %d" % self.telelId
        rs = self.cur.execute(sql)
        telData = rs.fetchall()
        if telData[0][2] == 'H':
            self.cbTelType.setCurrentIndex(0)
        elif telData[0][2] == 'W':
            self.cbTelType.setCurrentIndex(1)
        elif telData[0][2] == 'M':
            self.cbTelType.setCurrentIndex(2)
        elif telData[0][2] == 'P':
            self.cbTelType.setCurrentIndex(3)
        elif telData[0][2] == 'F':
            self.cbTelType.setCurrentIndex(4)
        else:
            self.cbTelType.setCurrentIndex(3)
        self.leTelNumber.setText(telData[0][3])
        self.teleDate = telData[0][4]

    #
    # update telecom

    def telecomWrite(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        sql = "SELECT max(id) FROM telecoms WHERE participant_id = %d;" % self.partId
        rs = self.cur.execute(sql)
        telData = rs.fetchall()
        if self.cbTelType.currentIndex() == 0:
            telType = 'H'
        elif self.cbTelType.currentIndex() == 1:
            telType = 'W'
        elif self.cbTelType.currentIndex() == 2:
            telType = 'M'
        elif self.cbTelType.currentIndex() == 3:
            telType = 'P'
        elif self.cbTelType.currentIndex() == 4:
            telType = 'W'
        else:
            telType = 'O'
        telNumber = self.leTelNumber.text()
        if self.teleDate == None or self.teleDate == '':
            createDate = datetime.datetime.now().isoformat()[:10]
            modDate = createDate
        else:
            createDate = self.teleDate
            modDate = datetime.datetime.now().isoformat()[:10] 
        if telData[0][0] == None or telData[0][0] < self.teleId:
            sql = "INSERT into telecoms (id, participant_id, telecom_type, "
            sql += "telecom, date_created, date_modified) "
            sql += "VALUES (%d, %d,  " % (self.teleId, self.partId)
            sql += "'%s', '%s', " % (telType, telNumber)
            sql += "'%s', '%s');" % (createDate, modDate)
            rCnt = self.tblTelecoms.rowCount()
            self.tblTelecoms.setRowCount(rCnt+1)
            self.telecomSet(rCnt, [self.teleId, telType, telNumber])
        else:
            sql = "UPDATE telecoms SET "
            sql += "telecom_type = '%s', " % telType
            sql += "telecom = '%s', " % telNumber
            sql += "date_created = '%s', " % createDate
            sql += "date_modified = '%s' " % modDate
            sql += "where id = %d;" % self.teleId
            self.telecomSet(self.tblTelecoms.currentRow(), [self.teleId, telType, telNumber])
        self.cur.execute(sql)
        self.conn.commit()

        self.telecomDisableEdit()
        row = self.tblTelecoms.currentRow()
        self.tblTelecoms.setItemSelected(self.tblTelecoms.item(row,0),False)
        self.tblTelecoms.setItemSelected(self.tblTelecoms.item(row,1),False)
        self.tblTelecoms.setItemSelected(self.tblTelecoms.item(row,2),False)
        
    #
    # delete telecom
    
    def telecomDelete(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        sql = "DELETE FROM telecoms WHERE id = %d" % self.teleId
        self.cur.execute(sql)
        self.conn.commit()
        self.telecomClearValues()
        self.telecomDisableEdit()
        # remove row
        row = self.tblTelecoms.currentRow()
        self.tblTelecoms.removeRow(row)
        row = self.tblTelecoms.currentRow()
        self.tblTelecoms.setItemSelected(self.tblTelecoms.item(row,0),False)
        self.tblTelecoms.setItemSelected(self.tblTelecoms.item(row,1),False)
        self.tblTelecoms.setItemSelected(self.tblTelecoms.item(row,2),False)

    #
    # clear telecom widgets

    def telecomClear(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.tblTelecoms.clear()
        

    ########################################################
    #               manage interview tables                #
    ########################################################

    #
    # add / update interview record to interview table widget

    def interviewSet(self,x,rec):

        # id
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[0]))
        item.setToolTip('Map Biographer Interview Id')
        self.tblInterviews.setItem(x,0,item)
        # code
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[1]))
        item.setToolTip('Interview Code')
        self.tblInterviews.setItem(x,1,item)
        # description
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[2]))
        item.setToolTip('Description')
        self.tblInterviews.setItem(x,2,item)
        # status
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[3]))
        item.setToolTip('Status')
        self.tblInterviews.setItem(x,3,item)

    #
    # read interview list

    def interviewListRead(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        sql = "SELECT id, code, description, data_status FROM interviews;"
        rs = self.cur.execute(sql)
        intvData = rs.fetchall()
        # clear old data and setup row and column counts
        self.tblInterviews.clear()
        self.tblInterviews.setColumnCount(4)
        self.tblInterviews.setRowCount(len(intvData))
        # set header
        header = []
        header.append('Id')
        header.append('Interview Code')
        header.append('Description')
        header.append('Status')
        self.tblInterviews.setHorizontalHeaderLabels(header)
        # add content
        x = 0
        for rec in intvData:
            self.interviewSet(x,rec)
            x = x + 1
        self.interviewDisableEdit()
        self.tblInterviews.setColumnWidth(0,75)
        self.tblInterviews.setColumnWidth(1,125)
        self.tblInterviews.setColumnWidth(2,350)
        self.tblInterviews.setColumnWidth(3,75)

    #
    # check if interview is selected or unselected
    
    def interviewCheckSelection(self):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        if len(self.tblInterviews.selectedItems()) == 0:
            # change widget states
            self.interviewDisableEdit()
        else:
            # change widget states
            self.interviewEnableEdit()
            # read information
            self.interviewRead()

    #
    # set edit of interview

    def interviewEnableEdit(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        # other tabs & main control
        self.pbDialogClose.setDisabled(True)
        self.twMapBioSettings.tabBar().setDisabled(True)
        # controls on this tab
        self.tblInterviews.setDisabled(True)
        self.pbIntNew.setDisabled(True)
        self.pbIntSave.setEnabled(True)
        self.pbIntCancel.setEnabled(True)
        self.pbIntDelete.setEnabled(True)
        self.tbxInterview.setEnabled(True)
        self.tbxInterview.setCurrentWidget(self.pgIntBasic)

    #
    # disable edit of interview

    def interviewDisableEdit(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        # other tabs & main control
        self.pbDialogClose.setEnabled(True)
        self.twMapBioSettings.tabBar().setEnabled(True)
        # controls on this tab
        self.interviewClearValues()
        self.tblInterviews.setEnabled(True)
        self.pbIntNew.setEnabled(True)
        self.pbIntSave.setDisabled(True)
        self.pbIntCancel.setDisabled(True)
        self.pbIntDelete.setDisabled(True)
        self.pgIntParticipants.setEnabled(True)
        self.tbxInterview.setDisabled(True)
        self.tbxInterview.setCurrentWidget(self.pgIntBasic)

    #
    # clear interview values

    def interviewClearValues(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.leInterviewCode.setText('')
        self.pteInterviewDescription.setPlainText('')
        self.dteStart.setDateTime(datetime.datetime.strptime("2000-01-01 12:00","%Y-%m-%d %H:%M"))
        self.dteEnd.setDateTime(datetime.datetime.strptime("2000-01-01 12:00","%Y-%m-%d %H:%M"))
        self.leFirstName.setText('')
        self.leInterviewTags.setText('')
        self.leInterviewLocation.setText('')
        self.pteInterviewNote.setPlainText('')
        self.cbInterviewSecurity.setCurrentIndex(0)
        self.leInterviewer.setText('')
        
    #
    # new interview

    def interviewNew(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.interviewClearValues()
        self.interviewEnableEdit()
        self.cbInterviewStatus.setCurrentIndex(0)
        self.pgIntParticipants.setDisabled(True)
        sql = "SELECT max(id) FROM interviews;"
        rs = self.cur.execute(sql)
        intvData = rs.fetchall()
        if intvData[0][0] == None:
            pass
        else:
            self.intvId = int(intvData[0][0]) + 1
        self.leInterviewCode.setFocus()
        
    #
    # cancel interview edits

    def interviewCancel(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.interviewClearValues()
        self.interviewDisableEdit()
        row = self.tblInterviews.currentRow()
        self.tblInterviews.setItemSelected(self.tblInterviews.item(row,0),False)
        self.tblInterviews.setItemSelected(self.tblInterviews.item(row,1),False)
        self.tblInterviews.setItemSelected(self.tblInterviews.item(row,2),False)
        self.tblInterviews.setItemSelected(self.tblInterviews.item(row,3),False)

    #
    # read interview

    def interviewRead(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.tbxInterview.setEnabled(True)
        row = int(self.tblInterviews.currentRow())
        self.intvId = int(self.tblInterviews.item(row,0).text())
        sql = "SELECT id, project_id, code, start_datetime, end_datetime, "
        sql += "description, interview_location, note, tags, data_status, "
        sql += "data_security, interviewer, date_created, date_modified  "
        sql += "FROM interviews WHERE id = %d" % self.intvId
        rs = self.cur.execute(sql)
        intvData = rs.fetchall()
        self.leInterviewCode.setText(intvData[0][2])
        self.dteStart.setDateTime(datetime.datetime.strptime(intvData[0][3],"%Y-%m-%d %H:%M"))
        self.dteEnd.setDateTime(datetime.datetime.strptime(intvData[0][4],"%Y-%m-%d %H:%M"))
        self.pteInterviewDescription.setPlainText(intvData[0][5])
        self.leInterviewLocation.setText(intvData[0][6])
        self.pteInterviewNote.setPlainText(intvData[0][7])
        self.leInterviewTags.setText(intvData[0][8])
        self.interviewStatus = intvData[0][9]
        if self.interviewStatus == 'U':
            self.cbInterviewStatus.setCurrentIndex(3)
        elif self.interviewStatus == 'T':
            self.cbInterviewStatus.setCurrentIndex(2)
        elif self.interviewStatus == 'C':
            self.cbInterviewStatus.setCurrentIndex(1)
        else:
            self.cbInterviewStatus.setCurrentIndex(0)
        if intvData[0][10] == 'PU':
            self.cbInterviewSecurity.setCurrentIndex(0)
        elif intvData[0][10] == 'CO':
            self.cbInterviewSecurity.setCurrentIndex(1)
        elif intvData[0][10] == 'RS':
            self.cbInterviewSecurity.setCurrentIndex(2)
        else:
            self.cbInterviewSecurity.setCurrentIndex(3)
        self.leInterviewer.setText(intvData[0][11])
        self.intvDate = intvData[0][12]
        self.interviewParticipantRefresh()
        self.interviewParticipantListRead()

    #
    # update interview

    def interviewWrite(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        sql = "SELECT max(id) FROM interviews;"
        rs = self.cur.execute(sql)
        intvData = rs.fetchall()
        code = self.leInterviewCode.text()
        description = self.pteInterviewDescription.document().toPlainText()
        startDate = self.dteStart.dateTime().toPyDateTime().isoformat()[:16].replace('T',' ')
        endDate = self.dteEnd.dateTime().toPyDateTime().isoformat()[:16].replace('T',' ')
        tags = self.leInterviewTags.text()
        location = self.leInterviewLocation.text()
        note = self.pteInterviewNote.document().toPlainText()
        # security
        if self.cbInterviewSecurity.currentIndex() == 1:
            security = 'CO'
        elif self.cbInterviewSecurity.currentIndex() == 2:
            security = 'RS'
        elif self.cbInterviewSecurity.currentIndex() == 3:
            security = 'PR'
        else:
            security = 'PU'
        # data status
        if self.cbInterviewStatus.currentIndex() == 0:
            self.interviewStatus = 'N'
        elif self.cbInterviewStatus.currentIndex() == 1:
            self.interviewStatus = 'C'
        elif self.cbInterviewStatus.currentIndex() == 2:
            self.interviewStatus = 'T'
        elif self.cbInterviewStatus.currentIndex() == 3:
            self.interviewStatus = 'U'
        # interviewer
        interviewer = self.leInterviewer.text()
        if self.intvDate == None or self.intvDate == '':
            createDate = datetime.datetime.now().isoformat()[:10]
            modDate = createDate
        else:
            createDate = self.intvDate
            modDate = datetime.datetime.now().isoformat()[:10] 
        if intvData[0][0] == None or intvData[0][0] < self.intvId:
            sql = "SELECT count(*) FROM interviews WHERE code = '%s';" % code
            rs = self.cur.execute(sql)
            cntData = rs.fetchall()
            if cntData[0][0] == 0:
                commitOk = True
                sql = "INSERT into interviews (id, project_id, code, "
                sql += "start_datetime, end_datetime, description, "
                sql += "interview_location, note, tags, data_status, "
                sql += "data_security, interviewer, date_created, date_modified) "
                sql += "VALUES (%d, %d, " % (self.intvId, self.projId)
                sql += "'%s', '%s', '%s', "% (code, startDate, endDate)
                sql += "'%s', '%s', " % (description, location)
                sql += "'%s', '%s', '%s', " % (note, tags, self.interviewStatus)
                sql += "'%s', '%s', '%s', '%s');" % (security, interviewer, createDate, modDate)
                rCnt = self.tblInterviews.rowCount()
                self.tblInterviews.setRowCount(rCnt+1)
                self.interviewSet(rCnt, [self.intvId,code,description,'N'])
            else:
                commitOk = False
        else:
            sql = "SELECT id FROM interviews WHERE code = '%s';" % code
            rs = self.cur.execute(sql)
            cntData = rs.fetchall()
            if cntData == [] or cntData[0][0] == self.intvId:
                commitOk = True
                sql = "UPDATE interviews SET "
                sql += "code = '%s', " % code
                sql += "start_datetime = '%s', " % startDate
                sql += "end_datetime = '%s', " % endDate
                sql += "description = '%s', " % description
                sql += "interview_location = '%s', " % location
                sql += "note = '%s', " % note
                sql += "tags = '%s', " % tags
                sql += "data_security = '%s', " % security
                sql += "data_status = '%s', " % self.interviewStatus
                sql += "interviewer = '%s', " % interviewer
                sql += "date_created = '%s', " % createDate
                sql += "date_modified = '%s' " % modDate
                sql += "where id = %d;" % self.intvId
                self.interviewSet(self.tblInterviews.currentRow(), [self.intvId,code,description,self.interviewStatus])
            else:
                commitOk = False
        if commitOk == True:
            self.cur.execute(sql)
            self.conn.commit()
            self.interviewDisableEdit()
            row = self.tblInterviews.currentRow()
            self.tblInterviews.setItemSelected(self.tblInterviews.item(row,0),False)
            self.tblInterviews.setItemSelected(self.tblInterviews.item(row,1),False)
            self.tblInterviews.setItemSelected(self.tblInterviews.item(row,2),False)
            self.tblInterviews.setItemSelected(self.tblInterviews.item(row,3),False)
        else:
            messageText = "The Interview Code '%s' is not unique. " % code
            messageText += "Modify the code and try again to save."
            response = QtGui.QMessageBox.warning(self, 'Warning',
               messageText, QtGui.QMessageBox.Ok)
        
    #
    # delete interview

    def interviewDelete(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        dRec = False
        # check for referenced use in interview
        sql = "SELECT count(*) FROM interview_sections WHERE interview_id = %d" % self.intvId
        rs = self.cur.execute(sql)
        confData = rs.fetchall()
        if confData[0][0] > 0:
            messageText = 'Are you sure you want to delete this interview. '
            messageText += 'There are %d sections in this interview.' % confData[0][0]
            response = QtGui.QMessageBox.warning(self, 'Warning',
               messageText, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if response == QtGui.QMessageBox.Yes:
                dRec = True
        else:
            dRec = True
        if dRec == True:
            # delete sections point records first
            sql = "DELETE FROM points WHERE section_id in "
            sql += "(SELECT id FROM interview_sections WHERE interview_id = %d);" % self.intvId
            self.cur.execute(sql)
            self.conn.commit()
            # delete sections line records first
            sql = "DELETE FROM lines WHERE section_id in "
            sql += "(SELECT id FROM interview_sections WHERE interview_id = %d);" % self.intvId
            self.cur.execute(sql)
            self.conn.commit()
            # delete sections polygon records first
            sql = "DELETE FROM polygons WHERE section_id in "
            sql += "(SELECT id FROM interview_sections WHERE interview_id = %d);" % self.intvId
            self.cur.execute(sql)
            self.conn.commit()
            # delete sections records first
            sql = "DELETE FROM interview_sections WHERE interview_id = %d" % self.intvId
            self.cur.execute(sql)
            self.conn.commit()
            # delete participant records first
            sql = "DELETE FROM interviewees WHERE interview_id = %d" % self.intvId
            self.cur.execute(sql)
            self.conn.commit()
            # delete main record
            sql = "DELETE FROM interviews WHERE id = %d" % self.intvId
            self.cur.execute(sql)
            self.conn.commit()
            self.interviewDisableEdit()
            # remove row
            row = self.tblInterviews.currentRow()
            self.tblInterviews.removeRow(row)
        row = self.tblInterviews.currentRow()
        self.tblInterviews.setItemSelected(self.tblInterviews.item(row,0),False)
        self.tblInterviews.setItemSelected(self.tblInterviews.item(row,1),False)
        self.tblInterviews.setItemSelected(self.tblInterviews.item(row,2),False)
        self.tblInterviews.setItemSelected(self.tblInterviews.item(row,3),False)


    ########################################################
    #            manage interview participants             #
    ########################################################
    
    #
    # add / update interview participant record to participant table widget

    def interviewParticipantSet(self,x,rec):

        # id
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[0]))
        item.setToolTip('Map Biographer Interview Id')
        self.tblInterviewParticipants.setItem(x,0,item)
        # user name
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[1]))
        item.setToolTip('Map Biographer Participant Id')
        self.tblInterviewParticipants.setItem(x,1,item)
        # first name
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[2]))
        item.setToolTip('Name')
        self.tblInterviewParticipants.setItem(x,2,item)

    #
    # read interview participant list

    def interviewParticipantListRead(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        sql = "SELECT a.id, b.id, b.last_name || ', ' || b.first_name as name FROM interviewees a, "
        sql += "participants b "
        sql += "WHERE a.interview_id = %d and " % self.intvId
        sql += "a.participant_id = b.id ORDER BY name;"
        rs = self.cur.execute(sql)
        partData = rs.fetchall()
        # clear old data and setup row and column counts
        self.tblInterviewParticipants.clear()
        self.tblInterviewParticipants.setColumnCount(3)
        self.tblInterviewParticipants.setRowCount(len(partData))
        # set header
        header = []
        header.append('Id')
        header.append('Part. Id')
        header.append('Name')
        self.tblInterviewParticipants.setHorizontalHeaderLabels(header)
        # add content
        x = 0
        for rec in partData:
            self.interviewParticipantSet(x,rec)
            x = x + 1
        self.tblInterviewParticipants.setColumnWidth(0,75)
        self.tblInterviewParticipants.setColumnWidth(1,75)
        self.tblInterviewParticipants.setColumnWidth(2,200)
        self.interviewParticipantDisableEdit()

    #
    # check if participant is selected or unselected
    
    def interviewParticipantCheckSelection(self):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        if len(self.tblInterviewParticipants.selectedItems()) == 0:
            # change widget states
            self.interviewParticipantDisableEdit()
        else:
            # change widget states
            self.interviewParticipantEnableEdit()
            # read information
            self.interviewParticipantRead()

    #
    # set edit of participant

    def interviewParticipantEnableEdit(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        # other controls
        self.pgIntBasic.setDisabled(True)
        self.frInterviewControls.setDisabled(True)
        # other controls
        self.tblInterviewParticipants.setDisabled(True)
        self.pbIntPartNew.setDisabled(True)
        self.pbIntPartSave.setEnabled(True)
        self.pbIntPartCancel.setEnabled(True)
        self.pbIntPartDelete.setEnabled(True)
        self.pgIntBasic.setDisabled(True)
        # participant specific widgets
        self.cbIntPartName.setEnabled(True)
        self.leIntPartCommunity.setEnabled(True)
        self.leIntPartFamily.setEnabled(True)

    #
    # disable edit of participant

    def interviewParticipantDisableEdit(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        # other controls
        self.pgIntBasic.setEnabled(True)
        self.frInterviewControls.setEnabled(True)
        # other controls
        self.interviewParticipantClearValues()
        self.tblInterviewParticipants.setEnabled(True)
        self.pbIntPartNew.setEnabled(True)
        self.pbIntPartSave.setDisabled(True)
        self.pbIntPartCancel.setDisabled(True)
        self.pbIntPartDelete.setDisabled(True)
        self.pgIntBasic.setEnabled(True)
        # participant specific widgets
        self.cbIntPartName.setDisabled(True)
        self.leIntPartCommunity.setDisabled(True)
        self.leIntPartFamily.setDisabled(True)

    #
    # clear participant values

    def interviewParticipantClearValues(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.cbIntPartName.setCurrentIndex(0)
        self.leIntPartCommunity.setText('')
        self.leIntPartFamily.setText('')
        
    #
    # new participant

    def interviewParticipantNew(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.interviewParticipantClearValues()
        self.interviewParticipantEnableEdit()
        sql = "SELECT max(id) FROM interviewees;"
        rs = self.cur.execute(sql)
        partData = rs.fetchall()
        if partData[0][0] == None:
            pass
        else:
            self.intvPartId = int(partData[0][0]) + 1
        if len(self.participantList) > 0:
            self.cbIntPartName.setCurrentIndex(0)
            self.leIntPartCommunity.setText(self.participantList[0][3])
            self.leIntPartFamily.setText(self.participantList[0][4])
        self.cbIntPartName.setFocus()            

    #
    # update when participant selected

    def interviewParticipantSelection(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        x = self.cbIntPartName.currentIndex()
        if len(self.participantList) > 0:
            self.leIntPartCommunity.setText(self.participantList[x][3])
            self.leIntPartFamily.setText(self.participantList[x][4])
    
    #
    # cancel participant edits

    def interviewParticipantCancel(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.interviewParticipantClearValues()
        self.interviewParticipantDisableEdit()
        row = self.tblInterviewParticipants.currentRow()
        self.tblInterviewParticipants.setItemSelected(self.tblInterviewParticipants.item(row,0),False)
        self.tblInterviewParticipants.setItemSelected(self.tblInterviewParticipants.item(row,1),False)
        self.tblInterviewParticipants.setItemSelected(self.tblInterviewParticipants.item(row,2),False)

    #
    # populate participant combobox

    def interviewParticipantRefresh(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        sql = "SELECT id, first_name, last_name, community, family "
        sql += "FROM participants ORDER BY last_name, first_name;"
        rs = self.cur.execute(sql)
        partData = rs.fetchall()
        self.cbIntPartName.clear()
        self.participantList = []
        for part in partData:
            self.cbIntPartName.addItem("%s, %s" % (part[2],part[1]))
            self.participantList.append(part)

    #
    # read participant

    def interviewParticipantRead(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.interviewParticipantClearValues()
        row = self.tblInterviewParticipants.currentRow()
        self.intvPartId = int(self.tblInterviewParticipants.item(row,0).text())
        partId = int(self.tblInterviewParticipants.item(row,1).text())
        sql = "SELECT id, interview_id, participant_id, community, "
        sql += "family, date_created, date_modified "
        sql += "FROM interviewees WHERE id = %d" % self.intvPartId
        rs = self.cur.execute(sql)
        partData = rs.fetchall()
        for x in range(self.cbIntPartName.count()):
            if self.participantList[x][0] == partId:
                self.cbIntPartName.setCurrentIndex(x)
                break
        if self.cbIntPartName.count() > 0:
            self.leIntPartCommunity.setText(partData[0][3])
            self.leIntPartFamily.setText(partData[0][4])

    #
    # update participant

    def interviewParticipantWrite(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        sql = "SELECT max(id) FROM interviewees WHERE interview_id = %d;" % self.intvId
        rs = self.cur.execute(sql)
        partData = rs.fetchall()
        userName = self.cbIntPartName.currentText()
        x = self.cbIntPartName.currentIndex()
        participantId = self.participantList[x][0]
        community = self.leIntPartCommunity.text()
        family = self.leIntPartFamily.text()
        if self.intvPartDate == None or self.intvPartDate == '':
            createDate = datetime.datetime.now().isoformat()[:10]
            modDate = createDate
        else:
            createDate = self.intvPartDate
            modDate = datetime.datetime.now().isoformat()[:10]
        if partData[0][0] == None or partData[0][0] < self.intvPartId:
            sql = "INSERT into interviewees (id, interview_id, participant_id, "
            sql += "community, family, date_created, date_modified) "
            sql += "VALUES (%d, %d, %d, " % (self.intvPartId, self.intvId, participantId)
            sql += "'%s', '%s', '%s', '%s');" % (community, family, createDate, modDate)
            rCnt = self.tblInterviewParticipants.rowCount()
            self.tblInterviewParticipants.setRowCount(rCnt+1)
            self.interviewParticipantSet(rCnt, [self.intvPartId,participantId,userName])
        else:
            sql = "UPDATE interviewees SET "
            sql += "participant_id = '%s', " % participantId
            sql += "community = '%s', " % community
            sql += "family = '%s', " % family
            sql += "date_created = '%s', " % createDate
            sql += "date_modified = '%s' " % modDate
            sql += "where id = %d;" % self.intvPartId
            self.interviewParticipantSet(self.tblInterviewParticipants.currentRow(), [self.intvPartId,participantId,userName])
        self.cur.execute(sql)
        self.conn.commit()

        self.interviewParticipantDisableEdit()
        row = self.tblInterviewParticipants.currentRow()
        self.tblInterviewParticipants.setItemSelected(self.tblInterviewParticipants.item(row,0),False)
        self.tblInterviewParticipants.setItemSelected(self.tblInterviewParticipants.item(row,1),False)
        self.tblInterviewParticipants.setItemSelected(self.tblInterviewParticipants.item(row,2),False)
        
    #
    # delete participant
    
    def interviewParticipantDelete(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        sql = "DELETE FROM interviewees WHERE id = %d" % self.intvPartId
        self.cur.execute(sql)
        self.conn.commit()
        self.interviewParticipantClearValues()
        self.interviewParticipantDisableEdit()
        # remove row
        row = self.tblInterviewParticipants.currentRow()
        self.tblInterviewParticipants.removeRow(row)
        row = self.tblInterviewParticipants.currentRow()
        self.tblInterviewParticipants.setItemSelected(self.tblInterviewParticipants.item(row,0),False)
        self.tblInterviewParticipants.setItemSelected(self.tblInterviewParticipants.item(row,1),False)
        self.tblInterviewParticipants.setItemSelected(self.tblInterviewParticipants.item(row,2),False)

    #
    # clear participant widgets

    def interviewParticipantClear(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.tblInterviewParticipants.clear()
        

    ########################################################
    #                data transfer functions               #
    ########################################################

    #
    # open transfer dialog and selection actions
    
    def transferData(self):

        s = QtCore.QSettings()
        dirName = s.value('mapBiographer/projectDir')
        self.importDialog = mapBiographerPorter(self.iface, dirName, self.projectDB)
        # show the dialog
        self.importDialog.show()
        # Run the dialog event loop
        result = self.importDialog.exec_()
