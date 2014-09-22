# -*- coding: utf-8 -*-
"""
/***************************************************************************
 mapBiographerSettings
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
from ui_mapbio_settings import Ui_mapBiographerSettings
from pyspatialite import dbapi2 as sqlite
import os, datetime
import inspect, shutil
from pydub import AudioSegment

class mapBiographerSettings(QtGui.QDialog, Ui_mapBiographerSettings):
    
    def __init__(self, iface):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)
        self.iface = iface

        # debug setup
        self.settingsDebug = False
        self.projectDebug = False
        self.participantDebug = False
        self.interviewsDebug = False
        self.debugFile = True
        self.df = None
        self.debugFileName = './lmb_settings.log'
        if self.settingsDebug or self.projectDebug or self.participantDebug or self.interviewsDebug:
            self.myself = lambda: inspect.stack()[1][3]
            self.df = open(self.debugFileName,'w')
        if self.settingsDebug:
            if self.debugFile == True:
                self.df.write('\n--Initialization--\n')
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)

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

        # trigger control
        self.settingsState = 'load'
        self.projectState = 'load'
        #self.participantState = 'load'
        #self.interviewState = 'load'

        # make connections
        # main form
        QtCore.QObject.connect(self.pbDialogClose, QtCore.SIGNAL("clicked()"), self.closeDialog)
        # map biographer settings tab actions
        QtCore.QObject.connect(self.tbSelectProjectDir, QtCore.SIGNAL("clicked()"), self.getProjectDir)
        QtCore.QObject.connect(self.cbProjectDatabase, QtCore.SIGNAL("currentIndexChanged(int)"), self.selectProjectDB)
        QtCore.QObject.connect(self.tbSelectQgsProject, QtCore.SIGNAL("clicked()"), self.readQgsProject)
        QtCore.QObject.connect(self.tblBaseGroups, QtCore.SIGNAL("itemSelectionChanged()"), self.enableBaseGroupRemoval)
        QtCore.QObject.connect(self.pbAddBaseGroup, QtCore.SIGNAL("clicked()"), self.addBaseGroup)
        QtCore.QObject.connect(self.pbRemoveBaseGroup, QtCore.SIGNAL("clicked()"), self.removeBaseGroup)
        QtCore.QObject.connect(self.cbBoundaryLayer, QtCore.SIGNAL("currentIndexChanged(int)"), self.updateBoundary)
        QtCore.QObject.connect(self.cbEnableReference, QtCore.SIGNAL("currentIndexChanged(int)"), self.setReferenceStatus)
        QtCore.QObject.connect(self.cbReferenceLayer, QtCore.SIGNAL("currentIndexChanged(int)"), self.updateReference)
        # tab controls
        QtCore.QObject.connect(self.pbSaveSettings, QtCore.SIGNAL("clicked()"), self.saveSettings)
        QtCore.QObject.connect(self.pbCancelSettings, QtCore.SIGNAL("clicked()"), self.cancelSettings)
        QtCore.QObject.connect(self.pbExport, QtCore.SIGNAL("clicked()"), self.exportInterviews)
        # heritage account
        QtCore.QObject.connect(self.rdoHasHeritage, QtCore.SIGNAL("clicked(bool)"), self.userChangedHeritageStatus)
        QtCore.QObject.connect(self.rdoNoHeritage, QtCore.SIGNAL("clicked(bool)"), self.userChangedHeritageStatus)
        QtCore.QObject.connect(self.leHeritageCommunity, QtCore.SIGNAL("textChanged(QString)"), self.enableSettingsEdit)
        QtCore.QObject.connect(self.leHeritageUser, QtCore.SIGNAL("textChanged(QString)"), self.enableSettingsEdit)
        QtCore.QObject.connect(self.pbPullData, QtCore.SIGNAL("clicked()"), self.pullData)
        QtCore.QObject.connect(self.pbPushData, QtCore.SIGNAL("clicked()"), self.pushData)
        #
        # project details tab states
        QtCore.QObject.connect(self.leProjectCode, QtCore.SIGNAL("textChanged(QString)"), self.enableProjectEdit)
        QtCore.QObject.connect(self.pteProjectDescription, QtCore.SIGNAL("textChanged()"), self.enableProjectEdit)
        QtCore.QObject.connect(self.leProjectTags, QtCore.SIGNAL("textChanged(QString)"), self.enableProjectEdit)
        QtCore.QObject.connect(self.pteProjectNote, QtCore.SIGNAL("textChanged()"), self.enableProjectEdit)
        QtCore.QObject.connect(self.pteProjectCitations, QtCore.SIGNAL("textChanged()"), self.enableProjectEdit)
        QtCore.QObject.connect(self.pteContentCodes, QtCore.SIGNAL("textChanged()"), self.enableProjectEdit)
        QtCore.QObject.connect(self.pteTimePeriods, QtCore.SIGNAL("textChanged()"), self.enableProjectEdit)
        QtCore.QObject.connect(self.pteAnnualVariation, QtCore.SIGNAL("textChanged()"), self.enableProjectEdit)
        QtCore.QObject.connect(self.pbProjectSave, QtCore.SIGNAL("clicked()"), self.saveProjectTable)
        QtCore.QObject.connect(self.pbProjectCancel, QtCore.SIGNAL("clicked()"), self.cancelProjectTable)
        #
        # people basic info actions
        QtCore.QObject.connect(self.pbParticipantNew, QtCore.SIGNAL("clicked()"), self.newParticipantEdit)
        QtCore.QObject.connect(self.pbParticipantCancel, QtCore.SIGNAL("clicked()"), self.cancelParticipantEdit)
        QtCore.QObject.connect(self.pbParticipantSave, QtCore.SIGNAL("clicked()"), self.updateParticipantRecord)
        QtCore.QObject.connect(self.pbParticipantDelete, QtCore.SIGNAL("clicked()"), self.deleteParticipantRecord)
        # people basic info states
        QtCore.QObject.connect(self.tblParticipants, QtCore.SIGNAL("itemSelectionChanged()"), self.checkParticipantSelection)
        # people address actions
        QtCore.QObject.connect(self.pbAddNew, QtCore.SIGNAL("clicked()"), self.newAddressEdit)
        QtCore.QObject.connect(self.pbAddCancel, QtCore.SIGNAL("clicked()"), self.cancelAddressEdit)
        QtCore.QObject.connect(self.pbAddSave, QtCore.SIGNAL("clicked()"), self.updateAddressRecord)
        QtCore.QObject.connect(self.pbAddDelete, QtCore.SIGNAL("clicked()"), self.deleteAddressRecord)
        # people address states
        QtCore.QObject.connect(self.tblAddresses, QtCore.SIGNAL("itemSelectionChanged()"), self.checkAddressSelection)
        # people telecom actions
        QtCore.QObject.connect(self.pbTelNew, QtCore.SIGNAL("clicked()"), self.newTelecomEdit)
        QtCore.QObject.connect(self.pbTelCancel, QtCore.SIGNAL("clicked()"), self.cancelTelecomEdit)
        QtCore.QObject.connect(self.pbTelSave, QtCore.SIGNAL("clicked()"), self.updateTelecomRecord)
        QtCore.QObject.connect(self.pbTelDelete, QtCore.SIGNAL("clicked()"), self.deleteTelecomRecord)
        # people telecom states
        QtCore.QObject.connect(self.tblTelecoms, QtCore.SIGNAL("itemSelectionChanged()"), self.checkTelecomSelection)
        #
        # interview basic info actions
        QtCore.QObject.connect(self.pbIntNew, QtCore.SIGNAL("clicked()"), self.newInterviewEdit)
        QtCore.QObject.connect(self.pbIntCancel, QtCore.SIGNAL("clicked()"), self.cancelInterviewEdit)
        QtCore.QObject.connect(self.pbIntSave, QtCore.SIGNAL("clicked()"), self.updateInterviewRecord)
        QtCore.QObject.connect(self.pbIntDelete, QtCore.SIGNAL("clicked()"), self.deleteInterviewRecord)
        # interview basic info states
        QtCore.QObject.connect(self.tblInterviews, QtCore.SIGNAL("itemSelectionChanged()"), self.checkInterviewSelection)
        # interview participant actions
        QtCore.QObject.connect(self.pbIntPartNew, QtCore.SIGNAL("clicked()"), self.newInterviewParticipantEdit)
        QtCore.QObject.connect(self.pbIntPartCancel, QtCore.SIGNAL("clicked()"), self.cancelInterviewParticipantEdit)
        QtCore.QObject.connect(self.pbIntPartSave, QtCore.SIGNAL("clicked()"), self.updateInterviewParticipantRecord)
        QtCore.QObject.connect(self.pbIntPartDelete, QtCore.SIGNAL("clicked()"), self.deleteInterviewParticipantRecord)
        # interview participant states
        QtCore.QObject.connect(self.tblInterviewParticipants, QtCore.SIGNAL("itemSelectionChanged()"), self.checkInterviewParticipantSelection)
        # participant edit selection
        QtCore.QObject.connect(self.cbIntPartName, QtCore.SIGNAL("currentIndexChanged(int)"), self.interviewParticipantSelection)
        
        try:
            self.settingsState = 'load'
            self.readSettings()
            self.disableSettingsEdit()
            if os.path.exists(os.path.join(self.dirName,self.projectDB)):
                self.openDB()
                self.readDB()
                self.disableProjectEdit()
                self.projectState = 'load'
                self.enableProject()
        except:
            self.disableProject()
            self.disableProjectEdit()

        self.settingsState = 'edit'
        self.projectState = 'edit'

    #
    # close dialog

    def closeDialog(self):

        if self.settingsDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)

        if self.projectDB <> '' and self.conn <> None:
            self.closeDB()
        tv = self.iface.layerTreeView()
        tv.selectionModel().clear()
        self.iface.newProject()
        if self.settingsDebug or self.projectDebug or self.participantDebug or self.interviewsDebug:
            self.df.close()
        self.close()


    ########################################################
    #        map biographer settings tab functions         #
    ########################################################
    
    #
    # get project directory

    def getProjectDir(self):
        
        dirName = QtGui.QFileDialog.getExistingDirectory(self, 'Select Project Directory')
        if dirName <> '':
            self.leProjectDir.setText(dirName)
            self.dirName = dirName
        self.enableSettingsEdit()

    #
    # heritage status manually changed

    def userChangedHeritageStatus(self):

        if self.settingsStatus <> 'load':
            self.setHeritageAccess()
            self.enableSettingsEdit()

    #
    # get heritage access status

    def setHeritageAccess(self):
        
        if self.rdoHasHeritage.isChecked():
            self.hasHeritage = True
            self.leHeritageCommunity.setEnabled(True)
            self.leHeritageUser.setEnabled(True)
            self.pbPullData.setEnabled(True)
            self.pbPushData.setEnabled(True)
        else:
            self.hasHeritage = False
            self.leHeritageCommunity.setDisabled(True)
            self.leHeritageUser.setDisabled(True)
            self.pbPullData.setDisabled(True)
            self.pbPushData.setDisabled(True)

    #
    # select project database

    def selectProjectDB(self):
        
        if self.projectState <> 'load':
            if self.projectDebug:
                if self.debugFile == True:
                    self.df.write(self.myself()+ '\n')
                else:
                    QtGui.QMessageBox.warning(self, 'DEBUG',
                        self.myself(), QtGui.QMessageBox.Ok)

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
                    self.disableProject()
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
                        self.openDB()
                        self.readDB()
                        self.enableProject()
                        self.enableSettingsEdit()
            elif self.cbProjectDatabase.currentIndex() == 0:
                self.projectDB = ''
                self.disableProject()
                self.cbProjectDatabase.setCurrentIndex(0)
            elif self.cbProjectDatabase.count() > 2:
                self.projectDB = self.cbProjectDatabase.currentText()
                self.openDB()
                self.readDB()
                self.enableProject()
                self.enableSettingsEdit()

    #
    # enable settings buttons

    def enableSettingsEdit(self):

        if self.settingsState <> 'load' and self.pbDialogClose.isEnabled():
            if self.settingsDebug:
                if self.debugFile == True:
                    self.df.write(self.myself()+ '\n')
                else:
                    QtGui.QMessageBox.warning(self, 'DEBUG',
                        self.myself(), QtGui.QMessageBox.Ok)

            # enable save and cancel
            self.pbSaveSettings.setEnabled(True)
            self.pbCancelSettings.setEnabled(True)
            # disable download
            self.pbPullData.setDisabled(True)
            self.pbPushData.setDisabled(True)
            # other tabs
            self.twProject.setDisabled(True)
            self.twParticipants.setDisabled(True)
            self.twInterviews.setDisabled(True)
            # dialog close
            self.pbDialogClose.setDisabled(True)

    #
    # disable settings buttons

    def disableSettingsEdit(self):
        
        if self.settingsDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)

        # disable save and cancel
        self.pbSaveSettings.setDisabled(True)
        self.pbCancelSettings.setDisabled(True)
        # enable download
        if self.hasHeritage:
            self.pbPullData.setEnabled(True)
            self.pbPushData.setEnabled(True)
        # other tabs
        self.twProject.setEnabled(True)
        self.twParticipants.setEnabled(True)
        self.twInterviews.setEnabled(True)
        # dialog close
        self.pbDialogClose.setEnabled(True)
        
    #
    # save LMB settings

    def saveSettings(self):

        if self.settingsDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)

        s = QtCore.QSettings()
        self.heritageCommunity = self.leHeritageCommunity.text()
        self.heritageUser = self.leHeritageUser.text()
        s.setValue('mapBiographer/projectDir', self.dirName)
        s.setValue('mapBiographer/hasHeritage', str(self.hasHeritage))
        if self.hasHeritage == False:
            self.heritageCommunity = 'N/A'
            self.heritageUser = 'N/A'
            self.leHeritageCommunity.setText(self.heritageCommunity)
            self.leHeritageUser.setText(self.heritageUser)
        s.setValue('mapBiographer/heritageCommunity', self.heritageCommunity)
        s.setValue('mapBiographer/heritageUser', self.heritageUser)
        s.setValue('mapBiographer/projectDB', self.projectDB)
        s.setValue('mapBiographer/qgsProject', self.qgsProject)
        s.setValue('mapBiographer/baseGroups', self.baseGroups)
        s.setValue('mapBiographer/boundaryLayer', self.boundaryLayer)
        s.setValue('mapBiographer/enableReference', str(self.enableReference))
        s.setValue('mapBiographer/referenceLayer', self.referenceLayer)
        self.disableSettingsEdit()
        
    #
    # cancel LM settings

    def cancelSettings(self):
        
        if self.settingsDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)

        self.readSettings()
        self.disableSettingsEdit()
        
    #
    # read LMB settings

    def readSettings(self):

        self.settingsState = 'load'
        self.projectState = 'load'
        
        if self.settingsDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        # project dir
        s = QtCore.QSettings()
        rv = s.value('mapBiographer/projectDir')
        if rv == None:
            self.dirName = '.'
        else:
            self.dirName = rv
        # connection settings
        self.leProjectDir.setText(self.dirName)
        rv = s.value('mapBiographer/hasHeritage')
        if rv == None:
            self.hasHeritage = False
        else:
            if rv == 'False':
                self.hasHeritage = False
            else:
                self.hasHeritage = True
        if self.hasHeritage == True:
            self.heritageCommunity = s.value('mapBiographer/heritageCommunity')
            self.leHeritageCommunity.setText(self.heritageCommunity)
            self.heritageUser = s.value('mapBiographer/heritageUser')
            self.leHeritageUser.setText(self.heritageUser)
            self.rdoHasHeritage.setChecked(True)
            self.leHeritageCommunity.setEnabled(True)
            self.leHeritageUser.setEnabled(True)
        else:
            self.heritageCommunity = 'N/A'
            self.leHeritageCommunity.setText('N/A')
            self.heritageUser = 'N/A'
            self.leHeritageUser.setText('N/A')
            self.rdoNoHeritage.setChecked(True)
            self.leHeritageCommunity.setDisabled(True)
            self.leHeritageUser.setDisabled(True)
        # populate project database list
        self.cbProjectDatabase.clear()
        self.cbProjectDatabase.addItem('--None Selected--')
        self.cbProjectDatabase.addItem('Create New Database')
        listing = os.listdir(self.dirName)
        for item in listing:
            if '.db' in item:
                self.cbProjectDatabase.addItem(item)
        self.cbProjectDatabase.setCurrentIndex(0)
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
            self.loadQgsProject(rv)
        else:
            # blank values if project invalid
            self.setNoQgsProject()

        self.projectState = 'edit'
        self.settingsState = 'edit'

    #
    # set no QGIS project

    def setNoQgsProject(self):

        if self.settingsDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)

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

    def readQgsProject(self):

        if self.settingsDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)

        projectName = QtGui.QFileDialog.getOpenFileName(self, 'Select QGIS project', self.dirName, '*.qgs')
        if os.path.exists(projectName):
            self.qgsProjectChanged = True
            self.leQgsProject.setText(projectName)
            self.qgsProject = projectName
            self.loadQgsProject(projectName)
        else:
            self.setNoQgsProject()
        self.enableSettingsEdit()

    #
    # load QgsProject

    def loadQgsProject( self, projectName ):

        if self.settingsDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)

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

    def enableBaseGroupRemoval(self):

        if self.settingsDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)

        if len(self.tblBaseGroups.selectedItems()) > 0:
            self.pbRemoveBaseGroup.setEnabled(True)
        else:
            self.pbRemoveBaseGroup.setDisabled(True)

    #
    # add base groups

    def addBaseGroup(self):

        if self.settingsDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)

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
        self.enableSettingsEdit()
        
    #
    # remove base groups

    def removeBaseGroup(self):

        if self.settingsDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)

        txt = self.tblBaseGroups.currentItem().text()
        self.tblBaseGroups.removeRow(self.tblBaseGroups.currentRow())
        self.baseGroups.remove(txt)
        self.enableSettingsEdit()

    #
    # udpate boundary

    def updateBoundary(self):

        if self.settingsState <> 'load':
            if self.settingsDebug:
                if self.debugFile == True:
                    self.df.write(self.myself()+ '\n')
                else:
                    QtGui.QMessageBox.warning(self, 'DEBUG',
                        self.myself(), QtGui.QMessageBox.Ok)

            if self.cbBoundaryLayer.count() > 0:
                idx = self.cbBoundaryLayer.currentIndex()
                if idx < 0:
                    idx = 0
                self.boundaryLayer = self.projectLayers[idx]
                self.enableSettingsEdit()

    #
    # enable reference layer

    def setReferenceStatus(self):

        if self.settingsState <> 'load':
            if self.settingsDebug:
                if self.debugFile == True:
                    self.df.write(self.myself()+ '\n')
                else:
                    QtGui.QMessageBox.warning(self, 'DEBUG',
                        self.myself(), QtGui.QMessageBox.Ok)

            if self.cbEnableReference.currentIndex() == 0:
                self.cbReferenceLayer.setDisabled(True)
                self.enableReference = False
                self.referenceLayer = ''
            else:
                self.cbReferenceLayer.setEnabled(True)
                self.enableReference = True
                self.cbReferenceLayer.setCurrentIndex(0)
                self.referenceLayer = self.projectLayers[0]
            self.enableSettingsEdit()

    #
    # update reference

    def updateReference(self):

        if self.settingsState <> 'load':
            if self.settingsDebug:
                if self.debugFile == True:
                    self.df.write(self.myself()+ '\n')
                else:
                    QtGui.QMessageBox.warning(self, 'DEBUG',
                        self.myself(), QtGui.QMessageBox.Ok)

            if self.enableReference == True and self.cbReferenceLayer.count() > 0:
                idx = self.cbReferenceLayer.currentIndex()
                if idx < 0:
                    idx = 0
                self.referenceLayer = self.projectLayers[idx]
                self.enableSettingsEdit()

    #
    # export project descriptive files in all formats

    def exportProjectFiles(self,pData,hDir,jDir,kDir):

        # heritage first
        # heritage users file
        pofH = os.path.join(hDir,pData[0][0]+'_users.ini')
        f = open(pofH,'w')
        f.write('[user]\n')
        f.write('username=%s\n' % self.heritageUser)
        f.write('password=passwordhidden\n')
        f.close()
        # heritage project file
        pfH = os.path.join(hDir,pData[0][0]+'.ini')
        f = open(pfH,'w')
        f.write('owner=%s\n' % self.heritageUser)
        f.write('code=%s\n' % pData[0][0])
        f.write('description=%s\n' % pData[0][1])
        f.write('note=%s\n' % pData[0][2])
        f.write('tags=%s\n' % pData[0][3])
        f.write('citations=%s\n' % pData[0][4])
        f.write('default_codes=%s\n' % str(pData[0][5].split('\n')).replace("u'","'"))
        f.write('default_time_periods=%s\n' % str(pData[0][6].split('\n')).replace("u'","'"))
        f.write('default_annual_variation=%s\n' % str(pData[0][7].split('\n')).replace("u'","'"))
        f.write('date_modified=%s\n' % pData[0][8])
        f.close()
        # json second
        # json users file
        pofJ= os.path.join(jDir,pData[0][0]+'_users.json')
        f = open(pofJ,'w')
        f.write('{"users":[{\n')
        f.write('    "%s":[{\n' % self.heritageUser)
        f.write('        "password":"passwordhidden"\n')
        f.write('    }]\n}]}\n')
        f.close()
        # json project file
        pfJ = os.path.join(jDir,pData[0][0]+'.json')
        f = open(pfJ,'w')
        f.write('{"attributes":[{\n')
        f.write('    "owner":"%s",\n' % self.heritageUser)
        f.write('    "code":"%s",\n' % pData[0][0])
        f.write('    "description":"%s",\n' % pData[0][1])
        f.write('    "note":"%s",\n' % pData[0][2])
        f.write('    "tags":"%s",\n' % pData[0][3])
        f.write('    "citations":"%s",\n' % pData[0][4])
        f.write('    "default_codes":"%s",\n' % str(pData[0][5].split('\n')).replace('[','{').replace(']','}').replace("u'","'"))
        f.write('    "default_time_periods":"%s",\n' % str(pData[0][6].split('\n')).replace('[','{').replace(']','}').replace("u'","'"))
        f.write('    "default_annual_variation":"%s",\n' % str(pData[0][7].split('\n')).replace('[','{').replace(']','}').replace("u'","'"))
        f.write('    "date_modified":"%s"\n' % pData[0][8])
        f.write('}]}\n')
        f.close()
        # kml third
        # kml users file
        pofK= os.path.join(kDir,pData[0][0]+'_users.xml')
        f = open(pofK,'w')
        f.write('<?xml version="1.0"?>\n')
        f.write('<users>\n')
        f.write('    <user>\n')
        f.write('        <name>%s</name>\n' % self.heritageUser)
        f.write('        <password>passwordhidden</password>\n')
        f.write('    </user>\n')
        f.write('</users>\n')
        f.close()
        # kml project file
        pfK = os.path.join(kDir,pData[0][0]+'.xml')
        f = open(pfK,'w')
        f.write('<?xml version="1.0"?>\n')
        f.write('<attributes>\n')
        f.write('    <owner>%s</owner>\n' % self.heritageUser)
        f.write('    <code>%s</code>\n' % pData[0][0])
        f.write('    <description>%s</description>\n' % pData[0][1])
        f.write('    <note>%s</note>\n' % pData[0][2])
        f.write('    <tags>%s</tags>\n' % pData[0][3])
        f.write('    <citations>%s</citations>\n' % pData[0][4])
        f.write('    <default_codes>%s</default_codes>\n' % str(pData[0][5].split('\n')).replace("u'","'"))
        f.write('    <default_time_periods>%s</default_time_periods>\n' % str(pData[0][6].split('\n')).replace("u'","'"))
        f.write('    <default_annual_variation>%s</default_annual_variation>\n' % str(pData[0][7].split('\n')).replace("u'","'"))
        f.write('    <date_modified>%s</date_modified>\n' % pData[0][8])
        f.write('</attributes>\n')
        f.close()

    #
    # export interview in heritage format

    def exportHeritageInterview(self,intvData,docOData,partData,outDir):
        
        # users first
        contribList = docOData[0][1]
        ofName = os.path.join(outDir,intvData[2]+'_users.ini')
        f = open(ofName,'w')
        f.write('[user]\n')
        f.write('username=%s\n' % docOData[0][1])
        f.write('account_security=INACTIVE\n')
        f.write('active=false\n')
        f.write('password=passwordhidden\n')
        f.write('first_name=%s\n' % docOData[0][2])
        f.write('last_name=%s\n' % docOData[0][3])
        f.write('email=%s\n' % docOData[0][4])
        f.write('community_affiliation=%s\n' % docOData[0][5])
        f.write('family_group=%s\n' % docOData[0][6])
        f.write('maiden_name=%s\n' % docOData[0][7])
        f.write('gender=%s\n' % docOData[0][8])
        f.write('marital_status=%s\n' % docOData[0][9])
        f.write('birth_date=%s\n' % docOData[0][10])
        f.write('tags=%s\n' % docOData[0][11])
        f.write('note=%s\n' % docOData[0][12])
        f.write('\n')
        for participant in partData:
            contribList += ','+participant[1]
            f.write('[user]\n')
            f.write('username=%s\n' % participant[1])
            f.write('account_security=INACTIVE\n')
            f.write('active=false\n')
            f.write('password=passwordhidden\n')
            f.write('first_name=%s\n' % participant[2])
            f.write('last_name=%s\n' % participant[3])
            f.write('email=%s\n' % participant[4])
            f.write('community_affiliation=%s\n' % participant[5])
            f.write('family_group=%s\n' % participant[6])
            f.write('maiden_name=%s\n' % participant[7])
            f.write('gender=%s\n' % participant[8])
            f.write('marital_status=%s\n' % participant[9])
            f.write('birth_date=%s\n' % participant[10])
            f.write('tags=%s\n' % participant[11])
            f.write('note=%s\n' % participant[12])
            f.write('\n')
        f.close()
        # interview file header
        ofName = os.path.join(outDir,intvData[2]+'.ini')
        f = open(ofName,'w')
        f.write('owner=%s\n' % docOData[0][1])
        f.write('code=%s\n' % intvData[2])
        f.write('description=%s\n' % intvData[5])
        f.write('start_date=%s\n' % intvData[3])
        f.write('end_date=%s\n' % intvData[4])
        f.write('location=%s\n' % intvData[6])
        f.write('note=%s\n' % intvData[7])
        f.write('tags=%s\n' % intvData[8])
        f.write('security_code=%s\n' % intvData[10])
        f.write('date_modified=%s\n' % intvData[12])
        f.write('contributors=%s\n' % contribList)
        f.write('\n')
        # get sections
        sql = "SELECT sequence_number, section_code, section_text, note, "
        sql += "use_period, use_period_start, use_period_end, annual_variation, "
        sql += "annual_variation_months, spatial_data_source, spatial_data_scale, "
        sql += "geom_source, tags, media_start_time, media_end_time, "
        sql += "data_security, date_created, date_modified, media_files, id "
        sql += "FROM interview_sections WHERE interview_id = %d " % intvData[0]
        sql += "ORDER by sequence_number;"
        rs = self.cur.execute(sql)
        secData = rs.fetchall()
        firstPoint = True
        firstLine = True
        firstPolygon = True
        for section in secData:
            f.write('[section=%s]\n' % section[1])
            f.write('sequence_number=%s\n' % section[0])
            f.write('section_text=%s\n' % section[2])
            f.write('note=%s\n' % section[3])
            f.write('use_period=%s\n' % section[4])
            f.write('use_period_start=%s\n' % section[5])
            f.write('use_period_end=%s\n' % section[6])
            f.write('annual_variation=%s\n' % section[7])
            f.write('annual_variation_months=%s\n' % section[8])
            f.write('spatial_data_source=%s\n' % section[9])
            f.write('spatial_data_scale=%s\n' % section[10])
            f.write('geom_source=%s\n' % section[11])
            f.write('tags=%s\n' % section[12])
            f.write('media_start_time=%s\n' % section[13])
            f.write('media_end_time=%s\n' % section[14])
            f.write('data_security=%s\n' % section[15])
            f.write('date_created=%s\n' % section[16])
            f.write('date_modified=%s\n' % section[17])
            f.write('\n')
            if section[11] == 'pt':
                sql = "SELECT section_code, AsKml(geom) "
                sql += "FROM points WHERE interview_id = %d AND " % intvData[0]
                sql += "section_id = %d " % section[19]
                rs = self.cur.execute(sql)
                featData = rs.fetchall()[0]
                ofn = os.path.join(outDir,intvData[2]+'_points.kml')
                if firstPoint:
                    self.writeKMLFile(ofn,featData,intvData[2])
                    firstPoint = False
                else:
                    self.writeKMLFile(ofn,featData,intvData[2],True)
            elif section[11] == 'ln':
                sql = "SELECT section_code, AsKml(geom) "
                sql += "FROM lines WHERE interview_id = %d AND " % intvData[0]
                sql += "section_id = %d " % section[19]
                rs = self.cur.execute(sql)
                featData = rs.fetchall()[0]
                ofn = os.path.join(outDir,intvData[2]+'_lines.kml')
                if firstLine:
                    self.writeKMLFile(ofn,featData,intvData[2])
                    firstLine = False
                else:
                    self.writeKMLFile(ofn,featData,intvData[2],True)
            elif section[11] == 'pl':
                sql = "SELECT section_code, AsKml(geom) "
                sql += "FROM polygons WHERE interview_id = %d AND " % intvData[0]
                sql += "section_id = %d " % section[19]
                rs = self.cur.execute(sql)
                featData = rs.fetchall()[0]
                ofn = os.path.join(outDir,intvData[2]+'_polygons.kml')
                if firstPolygon:
                    self.writeKMLFile(ofn,featData,intvData[2])
                    firstPolygon = False
                else:
                    self.writeKMLFile(ofn,featData,intvData[2],True)
        f.close()

    #
    # export interview in json format

    def exportJSONInterview(self,intvData,docOData,partData,outDir):

        # users first
        contribList = docOData[0][1]
        ofName = os.path.join(outDir,intvData[2]+'_users.json')
        f = open(ofName,'w')
        f.write('{"users":[{\n')
        f.write('    "%s":[{\n' % docOData[0][1])
        f.write('        "account_security":"INACTIVE",\n')
        f.write('        "active":"false",\n')
        f.write('        "password":"passwordhidden",\n')
        f.write('        "first_name":"%s",\n' % docOData[0][2])
        f.write('        "last_name":"%s",\n' % docOData[0][3])
        f.write('        "email":"%s",\n' % docOData[0][4])
        f.write('        "community_affiliation":"%s",\n' % docOData[0][5])
        f.write('        "family_group":"%s",\n' % docOData[0][6])
        f.write('        "maiden_name":"%s",\n' % docOData[0][7])
        f.write('        "gender":"%s",\n' % docOData[0][8])
        f.write('        "marital_status":"%s",\n' % docOData[0][9])
        f.write('        "birth_date":"%s",\n' % docOData[0][10])
        f.write('        "tags":"%s",\n' % docOData[0][11])
        f.write('        "note":"%s"\n' % docOData[0][12])
        f.write('    }]\n')
        for participant in partData:
            f.write(',')
            contribList += ','+participant[1]
            f.write('    "%s":[{\n' % participant[1])
            f.write('        "account_security":"INACTIVE",\n')
            f.write('        "active":"false",\n')
            f.write('        "password":"passwordhidden",\n')
            f.write('        "first_name":"%s",\n' % participant[2])
            f.write('        "last_name":"%s",\n' % participant[3])
            f.write('        "email":"%s",\n' % participant[4])
            f.write('        "community_affiliation":"%s",\n' % participant[5])
            f.write('        "family_group":"%s",\n' % participant[6])
            f.write('        "maiden_name":"%s",\n' % participant[7])
            f.write('        "gender":"%s",\n' % participant[8])
            f.write('        "marital_status":"%s",\n' % participant[9])
            f.write('        "birth_date":"%s",\n' % participant[10])
            f.write('        "tags":"%s",\n' % participant[11])
            f.write('        "note":"%s"\n' % participant[12])
            f.write('    }]\n')
        f.write('}]}\n')
        f.close()
        # interview file header
        ofName = os.path.join(outDir,intvData[2]+'.json')
        f = open(ofName,'w')
        f.write('{"attributes":[{\n')
        f.write('    "owner":"%s",\n' % docOData[0][1])
        f.write('    "code":"%s",\n' % intvData[2])
        f.write('    "description":"%s",\n' % intvData[5])
        f.write('    "start_date":"%s",\n' % intvData[3])
        f.write('    "end_date":"%s",\n' % intvData[4])
        f.write('    "location":"%s",\n' % intvData[6])
        f.write('    "note":"%s",\n' % intvData[7])
        f.write('    "tags":"%s",\n' % intvData[8])
        f.write('    "security_code":"%s",\n' % intvData[10])
        f.write('    "date_modified":"%s",\n' % intvData[12])
        f.write('    "contributors":"%s",\n' % contribList)
        f.write('    "sections":[{\n')
        # get sections
        sql = "SELECT sequence_number, section_code, section_text, note, "
        sql += "use_period, use_period_start, use_period_end, annual_variation, "
        sql += "annual_variation_months, spatial_data_source, spatial_data_scale, "
        sql += "geom_source, tags, media_start_time, media_end_time, "
        sql += "data_security, date_created, date_modified, media_files, id "
        sql += "FROM interview_sections WHERE interview_id = %d " % intvData[0]
        sql += "ORDER by sequence_number;"
        rs = self.cur.execute(sql)
        secData = rs.fetchall()
        firstPoint = True
        firstLine = True
        firstPolygon = True
        firstSection = True
        for section in secData:
            if firstSection:
                firstSection = False
            else:
                f.write(',')
            f.write('        "%s":[{\n' % section[1])
            f.write('        "sequence_number":"%s",\n' % section[0])
            f.write('        "section_text":"%s",\n' % section[2])
            f.write('        "note":"%s",\n' % section[3])
            f.write('        "use_period":"%s",\n' % section[4])
            f.write('        "use_period_start":"%s",\n' % section[5])
            f.write('        "use_period_end":"%s",\n' % section[6])
            f.write('        "annual_variation":"%s",\n' % section[7])
            f.write('        "annual_variation_months":"%s",\n' % section[8])
            f.write('        "spatial_data_source":"%s",\n' % section[9])
            f.write('        "spatial_data_scale":"%s",\n' % section[10])
            f.write('        "geom_source":"%s",\n' % section[11])
            f.write('        "tags":"%s",\n' % section[12])
            f.write('        "media_start_time":"%s",\n' % section[13])
            f.write('        "media_end_time":"%s",\n' % section[14])
            f.write('        "data_security":"%s",\n' % section[15])
            f.write('        "date_created":"%s",\n' % section[16])
            f.write('        "date_modified":"%s"\n' % section[17])
            f.write('    }]\n')
            if section[11] == 'pt':
                sql = "SELECT section_code, AsGeoJSON(geom) "
                sql += "FROM points WHERE interview_id = %d AND " % intvData[0]
                sql += "section_id = %d " % section[19]
                rs = self.cur.execute(sql)
                featData = rs.fetchall()[0]
                ofn = os.path.join(outDir,intvData[2]+'_points.geojson')
                if firstPoint:
                    self.writeGeoJSONFile(ofn,featData,intvData[2])
                    firstPoint = False
                else:
                    self.writeGeoJSONFile(ofn,featData,intvData[2],True)
            elif section[11] == 'ln':
                sql = "SELECT section_code, AsGeoJSON(geom) "
                sql += "FROM lines WHERE interview_id = %d AND " % intvData[0]
                sql += "section_id = %d " % section[19]
                rs = self.cur.execute(sql)
                featData = rs.fetchall()[0]
                ofn = os.path.join(outDir,intvData[2]+'_lines.geojson')
                if firstLine:
                    self.writeGeoJSONFile(ofn,featData,intvData[2])
                    firstLine = False
                else:
                    self.writeGeoJSONFile(ofn,featData,intvData[2],True)
            elif section[11] == 'pl':
                sql = "SELECT section_code, AsGeoJSON(geom) "
                sql += "FROM polygons WHERE interview_id = %d AND " % intvData[0]
                sql += "section_id = %d " % section[19]
                rs = self.cur.execute(sql)
                featData = rs.fetchall()[0]
                ofn = os.path.join(outDir,intvData[2]+'_polygons.geojson')
                if firstPolygon:
                    self.writeGeoJSONFile(ofn,featData,intvData[2])
                    firstPolygon = False
                else:
                    self.writeGeoJSONFile(ofn,featData,intvData[2],True)
        f.write('    }]\n}]}\n')
        f.close()

    #
    # export interview in kml/xml format

    def exportKMLInterview(self,intvData,docOData,partData,outDir):

        # users first
        contribList = docOData[0][1]
        ofName = os.path.join(outDir,intvData[2]+'_users.xml')
        f = open(ofName,'w')
        f.write('<?xml version="1.0"?>\n')
        f.write('<users>\n')
        f.write('    <user>\n')
        f.write('        <name>%s</name>\n' % docOData[0][1])
        f.write('        <account_security>INACTIVE</account_security>\n')
        f.write('        <active>false</active>\n')
        f.write('        <password>passwordhidden</password>\n')
        f.write('        <first_name>%s</first_name>\n' % docOData[0][2])
        f.write('        <last_name>%s</last_name>\n' % docOData[0][3])
        f.write('        <email>%s</email>\n' % docOData[0][4])
        f.write('        <community_affiliation>%s</community_affiliation>\n' % docOData[0][5])
        f.write('        <family_group>%s</family_group>\n' % docOData[0][6])
        f.write('        <maiden_name>%s</maiden_name>\n' % docOData[0][7])
        f.write('        <gender>%s</gender>\n' % docOData[0][8])
        f.write('        <marital_status>%s</marital_status>\n' % docOData[0][9])
        f.write('        <birth_date>%s</birth_date>\n' % docOData[0][10])
        f.write('        <tags>%s</tags>\n' % docOData[0][11])
        f.write('        <note>%s</note>\n' % docOData[0][12])
        f.write('   </user>\n')
        for participant in partData:
            contribList += ','+participant[1]
            f.write('    <user>\n')
            f.write('        <name>%s</name>\n' % participant[1])
            f.write('        <account_security>INACTIVE</account_security>\n')
            f.write('        <active>false</active>\n')
            f.write('        <password>passwordhidden</password>\n')
            f.write('        <first_name>%s</first_name>\n' % participant[2])
            f.write('        <last_name>%s</last_name>\n' % participant[3])
            f.write('        <email>%s</email>\n' % participant[4])
            f.write('        <community_affiliation>%s</community_affiliation>\n' % participant[5])
            f.write('        <family_group>%s</family_group>\n' % participant[6])
            f.write('        <maiden_name>%s</maiden_name>\n' % participant[7])
            f.write('        <gender>%s</gender>\n' % participant[8])
            f.write('        <marital_status>%s</marital_status>\n' % participant[9])
            f.write('        <birth_date>%s</birth_date>\n' % participant[10])
            f.write('        <tags>%s</tags>\n' % participant[11])
            f.write('        <note>%s</note>\n' % participant[12])
            f.write('   </user>\n')
        f.write('</users>\n')
        f.close()
        # interview file header
        ofName = os.path.join(outDir,intvData[2]+'.xml')
        f = open(ofName,'w')
        f.write('<?xml version="1.0"?>\n')
        f.write('<attributes>\n')
        f.write('    <owner>%s</owner>\n' % docOData[0][1])
        f.write('    <code>%s</code>\n' % intvData[2])
        f.write('    <description>%s</description>\n' % intvData[5])
        f.write('    <start_date>%s</start_date>\n' % intvData[3])
        f.write('    <end_date>%s</end_date>\n' % intvData[4])
        f.write('    <location>%s</location>\n' % intvData[6])
        f.write('    <note>%s</note>\n' % intvData[7])
        f.write('    <tags>%s</tags>\n' % intvData[8])
        f.write('    <security_code>%s</security_code>\n' % intvData[10])
        f.write('    <date_modified>%s</date_modified>\n' % intvData[12])
        f.write('    <contributors>%s</contributors>\n' % contribList)
        f.write('    <sections>\n')
        # get sections
        sql = "SELECT sequence_number, section_code, section_text, note, "
        sql += "use_period, use_period_start, use_period_end, annual_variation, "
        sql += "annual_variation_months, spatial_data_source, spatial_data_scale, "
        sql += "geom_source, tags, media_start_time, media_end_time, "
        sql += "data_security, date_created, date_modified, media_files, id "
        sql += "FROM interview_sections WHERE interview_id = %d " % intvData[0]
        sql += "ORDER by sequence_number;"
        rs = self.cur.execute(sql)
        secData = rs.fetchall()
        firstPoint = True
        firstLine = True
        firstPolygon = True
        for section in secData:
            f.write('        <section>\n')
            f.write('            <section_code>%s</section_code>\n' % section[1])
            f.write('            <sequence_number>%s</sequence_number>\n' % section[0])
            f.write('            <section_text>%s</section_text>\n' % section[2])
            f.write('            <note>%s</note>\n' % section[3])
            f.write('            <use_period>%s</use_period>\n' % section[4])
            f.write('            <use_period_start>%s</use_period_start>\n' % section[5])
            f.write('            <use_period_end>%s</use_period_end>\n' % section[6])
            f.write('            <annual_variation>%s</annual_variation>\n' % section[7])
            f.write('            <annual_variation_months>%s</annual_variation_months>\n' % section[8])
            f.write('            <spatial_data_source>%s</spatial_data_source>\n' % section[9])
            f.write('            <spatial_data_scale>%s</spatial_data_scale>\n' % section[10])
            f.write('            <geom_source>%s</geom_source>\n' % section[11])
            f.write('            <tags>%s</tags>\n' % section[12])
            f.write('            <media_start_time>%s</media_start_time>\n' % section[13])
            f.write('            <media_end_time>%s</media_end_time>\n' % section[14])
            f.write('            <data_security>%s</data_security>\n' % section[15])
            f.write('            <date_created>%s</date_created>\n' % section[16])
            f.write('            <date_modified>%s</date_modified>\n' % section[17])
            f.write('        </section>\n')
            if section[11] == 'pt':
                sql = "SELECT section_code, AsKml(geom) "
                sql += "FROM points WHERE interview_id = %d AND " % intvData[0]
                sql += "section_id = %d " % section[19]
                rs = self.cur.execute(sql)
                featData = rs.fetchall()[0]
                ofn = os.path.join(outDir,intvData[2]+'_points.geojson')
                if firstPoint:
                    self.writeKMLFile(ofn,featData,intvData[2])
                    firstPoint = False
                else:
                    self.writeKMLFile(ofn,featData,intvData[2],True)
            elif section[11] == 'ln':
                sql = "SELECT section_code, AsKml(geom) "
                sql += "FROM lines WHERE interview_id = %d AND " % intvData[0]
                sql += "section_id = %d " % section[19]
                rs = self.cur.execute(sql)
                featData = rs.fetchall()[0]
                ofn = os.path.join(outDir,intvData[2]+'_lines.geojson')
                if firstLine:
                    self.writeKMLFile(ofn,featData,intvData[2])
                    firstLine = False
                else:
                    self.writeKMLFile(ofn,featData,intvData[2],True)
            elif section[11] == 'pl':
                sql = "SELECT section_code, AsKml(geom) "
                sql += "FROM polygons WHERE interview_id = %d AND " % intvData[0]
                sql += "section_id = %d " % section[19]
                rs = self.cur.execute(sql)
                featData = rs.fetchall()[0]
                ofn = os.path.join(outDir,intvData[2]+'_polygons.geojson')
                if firstPolygon:
                    self.writeKMLFile(ofn,featData,intvData[2])
                    firstPolygon = False
                else:
                    self.writeKMLFile(ofn,featData,intvData[2],True)
        f.write('    </sections>\n')
        f.write('</attributes>\n')
        f.close()
        
    #
    # write kml file

    def writeKMLFile(self,outFName,recordInfo,intvCode,append=False):

        if append:
            rf = open(outFName,'r')
            lns = rf.readlines()
            rf.close()
            f = open(outFName,'w')
            for ln in lns:
                if '</Document>' in ln:
                    break
                else:
                    f.write(ln)
        else:
            f = open(outFName,'w')
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<kml xmlns="http://www.opengis.net/kml/2.2">\n')
            f.write("    <Document>\n")
            f.write("        <name>Heritage Features</name>\n")
        f.write("        <Placemark>\n")
        f.write("            <name>%s</name>\n" % recordInfo[0])
        f.write("            <description>Feature from %s</description>\n" % intvCode)
        f.write("            %s\n" % recordInfo[1])
        f.write("        </Placemark>\n")
        f.write("    </Document>\n")
        f.write("</kml>\n")
        f.close()

    #
    # write geojson file

    def writeGeoJSONFile(self,outFName,recordInfo,intvCode,append=False):

        if append:
            rf = open(outFName,'r')
            lns = rf.readlines()
            rf.close()
            f = open(outFName,'w')
            for ln in lns:
                if ln == '    ]\n':
                    f.write(',')
                    break
                else:
                    f.write(ln)
        else:
            f = open(outFName,'w')
            f.write('{"type":"FeatureCollection",\n')
            f.write('    "features":[\n')
        f.write('        {"type":"Feature",\n')
        f.write('            "properties":{\n')
        f.write('                "section_code":"%s",\n' % recordInfo[0])
        f.write('                "source":"Feature from %s"},\n' % intvCode)
        f.write('            "geometry":%s\n' % recordInfo[1])
        f.write('        }\n')
        f.write('    ]\n')
        f.write('}\n')
        f.close()

    #
    # export interviews to LOUIS Archive format

    def exportInterviews(self):

        # get project information
        sql = "SELECT code,description,note,tags, "
        sql += "citations,default_codes,default_time_periods, "
        sql += "default_annual_variation,date_modified FROM project"
        rs = self.cur.execute(sql)
        pData = rs.fetchall()
        pCode = pData[0][0]
        # get list of interviews
        sql = "SELECT id, project_id, code, start_datetime, end_datetime, "
        sql += "description, interview_location, note, tags, data_status, "
        sql += "data_security, owner_id, date_modified FROM interviews"
        rs = self.cur.execute(sql)
        intvList = rs.fetchall()
        intCnt = len(intvList)
        progress = QtGui.QProgressDialog('Exporting Interviews for %s' % pCode,'Cancel',0,intCnt, self)
        progress.setWindowTitle('Export progress')
        progress.setWindowModality(QtCore.Qt.WindowModal)
        # create directory structure
        self.exDir = os.path.join(self.dirName,'exports')
        if not os.path.exists(self.exDir):
            os.makedirs(self.exDir,0755)
        self.exProjDir = os.path.join(self.exDir,pCode)
        if not os.path.exists(self.exProjDir):
            os.makedirs(self.exProjDir,0755)
        # create internal structure for different archive types
        hDir = os.path.join(self.exProjDir,'heritage')
        if not os.path.exists(hDir):
            os.makedirs(hDir,0755)
        jDir = os.path.join(self.exProjDir,'json')
        if not os.path.exists(jDir):
            os.makedirs(jDir,0755)
        kDir = os.path.join(self.exProjDir,'kml')
        if not os.path.exists(kDir):
            os.makedirs(kDir,0755)
        # write project files
        self.exportProjectFiles(pData,hDir,jDir,kDir)
        x = 0
        for intvData in intvList:
            x += 1
            progress.setValue(x)
            if progress.wasCanceled():
                break
            # export data
            # heritage first
            # identify or create heritage output directory for this interview
            intvHDir = os.path.join(hDir,'doc_'+intvData[2],'images')
            if not os.path.exists(intvHDir):
                os.makedirs(intvHDir, 0755)
            intvHDir = os.path.join(hDir,'doc_'+intvData[2])
            # identify or create json output directory for this interview
            intvJDir = os.path.join(jDir,'doc_'+intvData[2],'images')
            if not os.path.exists(intvJDir):
                os.makedirs(intvJDir, 0755)
            intvJDir = os.path.join(jDir,'doc_'+intvData[2])
            # identify or create kml output directory for this interview
            intvKDir = os.path.join(kDir,'doc_'+intvData[2],'images')
            if not os.path.exists(intvKDir):
                os.makedirs(intvKDir, 0755)
            intvKDir = os.path.join(kDir,'doc_'+intvData[2])
            # get document owner
            sql = "SELECT id, user_name, first_name, last_name, email_address, "
            sql += "community, family, maiden_name, gender, marital_status, "
            sql += "birth_date, tags, note, date_modified "
            sql += "FROM participants WHERE id = %d " % intvData[11]
            rs = self.cur.execute(sql)
            docOData = rs.fetchall()
            sql = "SELECT a.id, a.user_name, a.first_name, a.last_name, a.email_address, "
            sql += "b.community, b.family, a.maiden_name, a.gender, a.marital_status, "
            sql += "a.birth_date, a.tags, a.note, b.date_modified "
            sql += "FROM participants a, interviewees b "
            sql += "WHERE a.id = b.participant_id AND "
            sql += "b.interview_id = %d " % intvData[0]
            rs = self.cur.execute(sql)
            partData = rs.fetchall()
            # export interview
            self.exportHeritageInterview(intvData,docOData,partData,intvHDir)
            self.exportJSONInterview(intvData,docOData,partData,intvJDir)
            self.exportKMLInterview(intvData,docOData,partData,intvKDir)
            # process multimedia
            # check if audio file exists
            wfName = os.path.join(self.dirName,intvData[2]+'.wav')
            mp3Name = os.path.join(self.dirName,intvData[2]+'.mp3')
            if os.path.exists(wfName):
                self.createMp3(wfName,mp3Name)
                hcopy = os.path.join(intvHDir,intvData[2]+'.mp3')
                jcopy = os.path.join(intvJDir,intvData[2]+'.mp3')
                kcopy = os.path.join(intvKDir,intvData[2]+'.mp3')
                shutil.copy(mp3Name,hcopy)
                shutil.copy(mp3Name,jcopy)
                shutil.move(mp3Name,kcopy)

    #
    # create mp3 audio file

    def createMp3(self, srcFile, destFile):

        src = AudioSegment.from_wav(srcFile)
        src.export(destFile, format='mp3', bitrate='44.1k')
    
    #
    # pull data from Heritage
    
    def pullData(self):
        pass

    #
    # push data to Heritage

    def pushData(self):
        pass 


    ########################################################
    #               projects tab functions                 #
    ########################################################

    #
    # enable project

    def enableProject(self):

        if self.projectDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)

        # main tabs
        self.twProject.setEnabled(True)
        self.twParticipants.setEnabled(True)
        self.twInterviews.setEnabled(True)
        self.pbExport.setEnabled(True)
        
    #
    # disable project

    def disableProject(self):

        if self.projectDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)

        # main tabs
        self.twProject.setDisabled(True)
        self.twParticipants.setDisabled(True)
        self.twInterviews.setDisabled(True)
        self.pbExport.setDisabled(True)
        
    #
    # enable project edit

    def enableProjectEdit(self):

        if self.projectState <> 'load' and self.pbDialogClose.isEnabled():
            if self.projectDebug:
                if self.debugFile == True:
                    self.df.write(self.myself()+ '\n')
                else:
                    QtGui.QMessageBox.warning(self, 'DEBUG',
                        self.myself(), QtGui.QMessageBox.Ok)

            # other tabs & main control
            self.twSettings.setDisabled(True)
            self.twParticipants.setDisabled(True)
            self.twInterviews.setDisabled(True)
            self.pbDialogClose.setDisabled(True)
            # controls on this tab
            self.pbProjectSave.setEnabled(True)
            self.pbProjectCancel.setEnabled(True)
            # dialog close
            self.pbDialogClose.setDisabled(True)

    #
    # disable project edit

    def disableProjectEdit(self):

        if self.projectDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)

        # other tabs & main control
        self.twSettings.setEnabled(True)
        self.twParticipants.setEnabled(True)
        self.twInterviews.setEnabled(True)
        self.pbDialogClose.setEnabled(True)
        # controls on this tab
        self.pbProjectSave.setDisabled(True)
        self.pbProjectCancel.setDisabled(True)
        # dialog close
        self.pbDialogClose.setEnabled(True)

        
    ########################################################
    #                   database functions                 #
    ########################################################

    #
    # create database

    def createDB(self, dbName):

        if self.projectDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)

        # connect
        # note that this first act creates a blank file on the disk
        self.conn = sqlite.connect(dbName)
        self.cur = self.conn.cursor()
        # create actual database with information
        sql = "SELECT InitSpatialMetadata()"
        self.cur.execute(sql)
        # create necessary tables
        self.createLOUISHeritageTables()
        # close
        self.conn.close()

    #
    # open database

    def openDB(self):

        if self.projectDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)

        # connect
        self.conn = sqlite.connect(os.path.join(self.dirName,self.projectDB))
        self.cur = self.conn.cursor()

    #
    # close database
    
    def closeDB(self):
        # disconnect
        self.cur = None
        self.conn.close()

    #
    # read database

    def readDB(self):

        if self.projectDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)

        self.readProjectTable()
        self.readParticipantList()
        self.readInterviewList()

    #
    # create tables

    def createLOUISHeritageTables(self):

        if self.projectDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)

        # create project table
        sql = "CREATE TABLE project ("
        sql += "id INTEGER NOT NULL PRIMARY KEY, "
        sql += "code TEXT, "
        sql += "description TEXT, "
        sql += "note TEXT, "
        sql += "tags TEXT, "
        sql += "data_status TEXT, "
        sql += "citations TEXT, "
        sql += "default_codes TEXT, "
        sql += "default_time_periods TEXT,"
        sql += "default_annual_variation TEXT, "
        sql += "date_created TEXT, "
        sql += "date_modified TEXT)"
        self.cur.execute(sql)
        # insert a new record into the projects table
        modDate = datetime.datetime.now().isoformat()[:10]
        sql = "INSERT into project (id, code, description, note, tags, "
        sql += "data_status, citations, default_codes, "
        sql += "default_time_periods, date_created, date_modified) "
        sql += "VALUES (%d, '%s', '%s', '%s', '%s', " % (1, 'NEW1', 'New Project', '', '')
        sql += "'%s', '%s', '%s', " % ('N', '', '')
        sql += "'%s', '%s', '%s');" % ('', modDate, modDate)
        self.cur.execute(sql)
        # create participants table
        sql = "CREATE TABLE participants ("
        sql += "id INTEGER NOT NULL PRIMARY KEY, "
        sql += "user_name TEXT, "
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
        sql += "owner_id INTEGER, "
        sql += "date_created TEXT, "
        sql += "date_modified TEXT,"
        sql += "FOREIGN KEY(project_id) REFERENCES project(id), "
        sql += "FOREIGN KEY(owner_id) REFERENCES participants(id) )"
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
        sql += "content_code TEXT, "
        sql += "section_code TEXT, "
        sql += "section_text TEXT, "
        sql += "note TEXT, "
        sql += "use_period TEXT, "
        sql += "use_period_start TEXT, "
        sql += "use_period_end TEXT, "
        sql += "annual_variation TEXT, "
        sql += "annual_variation_months TEXT, "
        sql += "spatial_data_source TEXT, "
        sql += "spatial_data_scale TEXT, "
        sql += "geom_source TEXT, "
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
    #               manage project tables                  #
    ########################################################

    #
    # read project table
    
    def readProjectTable(self):

        self.projectState = 'load'

        if self.projectDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)
        sql = "SELECT id, code, description, note, tags, "
        sql += "citations, default_codes, default_time_periods, "
        sql += "default_annual_variation, date_created FROM project;"
        rs = self.cur.execute(sql)
        projData = rs.fetchall()
        self.projId = int(projData[0][0])
        if len(projData) > 0:
            self.leProjectCode.setText(projData[0][1])
            self.pteProjectDescription.setPlainText(projData[0][2])
            self.pteProjectNote.setPlainText(projData[0][3])
            self.leProjectTags.setText(projData[0][4])
            self.pteProjectCitations.setPlainText(projData[0][5])
            self.pteContentCodes.setPlainText(projData[0][6])
            self.pteTimePeriods.setPlainText(projData[0][7])
            self.pteAnnualVariation.setPlainText(projData[0][8])
        self.projDate = projData[0][9]

        self.projectState = 'edit'

    # 
    # update project table
    
    def saveProjectTable(self):
        
        if self.projectDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)

        sql = "SELECT max(id) FROM project;"
        rs = self.cur.execute(sql)
        projData = rs.fetchall()
        code = self.leProjectCode.text()
        description = self.pteProjectDescription.document().toPlainText()
        tags = self.leProjectTags.text()
        note = self.pteProjectNote.document().toPlainText()
        citations = self.pteProjectCitations.document().toPlainText()
        dataStatus = 'N'
        defaultCodes = self.pteContentCodes.document().toPlainText()
        timePeriods = self.pteTimePeriods.document().toPlainText()
        annualVariation = self.pteAnnualVariation.document().toPlainText()
        if self.projDate == None or self.projDate == '':
            createDate = datetime.datetime.now().isoformat()[:10]
            modDate = createDate
        else:
            createDate = self.projDate
            modDate = datetime.datetime.now().isoformat()[:10] 
        if projData[0][0] == None:
            sql = "INSERT INTO project (id, code, description, note, tags, "
            sql += "data_status, citations, default_codes, "
            sql += "default_time_periods, default_annual_variation, date_created, date_modified) "
            sql += "VALUES (%d, '%s', '%s', '%s', '%s', " % (1, code, description, note, tags)
            sql += "'%s', '%s', '%s', " % (dataStatus ,citations, defaultCodes)
            sql += "'%s', '%s', '%s', '%s');" % (timePeriods, annualVariation, createDate, modDate)
        else:
            sql = "UPDATE project SET "
            sql += "code = '%s', " % code
            sql += "description = '%s', " % description
            sql += "note = '%s', " % note
            sql += "tags = '%s', " % tags
            sql += "data_status = '%s', " % dataStatus
            sql += "citations = '%s', " % citations
            sql += "default_codes = '%s', " % defaultCodes
            sql += "default_time_periods = '%s', " % timePeriods
            sql += "default_annual_variation = '%s', " % annualVariation
            sql += "date_created = '%s', " % createDate
            sql += "date_modified = '%s' " % modDate
            sql += "WHERE id = %d;" % self.projId
        self.cur.execute(sql)
        self.conn.commit()
        self.disableProjectEdit()

    #
    # cancel project table updates

    def cancelProjectTable(self):

        if self.projectDebug:
            if self.debugFile == True:
                self.df.write(self.myself()+ '\n')
            else:
                QtGui.QMessageBox.warning(self, 'DEBUG',
                    self.myself(), QtGui.QMessageBox.Ok)

        self.readProjectTable()
        self.disableProjectEdit()

        
    ########################################################
    #               manage participant tables              #
    ########################################################

    #
    # add / update participant record to participant table widget

    def setParticipant(self,x,rec):
        # id
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[0]))
        item.setToolTip('Id')
        self.tblParticipants.setItem(x,0,item)
        # user name
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[1]))
        item.setToolTip('User Name')
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

    def readParticipantList(self):
            
        sql = "SELECT id, user_name, first_name, last_name FROM participants;"
        rs = self.cur.execute(sql)
        partData = rs.fetchall()
        # clear old data and setup row and column counts
        self.tblParticipants.clear()
        self.tblParticipants.setColumnCount(4)
        self.tblParticipants.setRowCount(len(partData))
        # set header
        header = []
        header.append('Id')
        header.append('User Name')
        header.append('First Name')
        header.append('Last Name')
        self.tblParticipants.setHorizontalHeaderLabels(header)
        # add content
        x = 0
        for rec in partData:
            self.setParticipant(x,rec)
            x = x + 1
        self.tblParticipants.setColumnWidth(0,75)
        self.tblParticipants.setColumnWidth(1,150)
        self.tblParticipants.setColumnWidth(2,200)
        self.tblParticipants.setColumnWidth(3,200)

    #
    # check if participant is selected or unselected
    
    def checkParticipantSelection(self):
        
        if len(self.tblParticipants.selectedItems()) == 0:
            # change widget states
            self.disableParticipantEdit()
        else:
            # change widget states
            self.enableParticipantEdit()
            # read information
            self.readParticipantRecord()

    #
    # set edit of participant

    def enableParticipantEdit(self):
        # other tabs & main control
        self.twSettings.setDisabled(True)
        self.twProject.setDisabled(True)
        self.twInterviews.setDisabled(True)
        self.pbDialogClose.setDisabled(True)
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

    def disableParticipantEdit(self):
        # other tabs
        self.twSettings.setEnabled(True)
        self.twProject.setEnabled(True)
        self.twInterviews.setEnabled(True)
        self.pbDialogClose.setEnabled(True)
        # controls on this tab
        self.clearParticipantValues()
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

    def clearParticipantValues(self):
        self.leParticipantUserName.setText('')
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
        self.clearAddresses()
        self.clearTelecoms()
        
    #
    # new participant

    def newParticipantEdit(self):
        self.clearParticipantValues()
        self.enableParticipantEdit()
        self.pgAddresses.setDisabled(True)
        self.pgTelecoms.setDisabled(True)
        sql = "SELECT max(id) FROM participants;"
        rs = self.cur.execute(sql)
        partData = rs.fetchall()
        if partData[0][0] == None:
            pass
        else:
            self.partId = int(partData[0][0]) + 1
        self.leParticipantUserName.setFocus()

    #
    # cancel participant edits

    def cancelParticipantEdit(self):
        self.clearParticipantValues()
        self.disableParticipantEdit()
        row = self.tblParticipants.currentRow()
        self.tblParticipants.setItemSelected(self.tblParticipants.item(row,0),False)
        self.tblParticipants.setItemSelected(self.tblParticipants.item(row,1),False)
        self.tblParticipants.setItemSelected(self.tblParticipants.item(row,2),False)
        self.tblParticipants.setItemSelected(self.tblParticipants.item(row,3),False)

    #
    # read participant

    def readParticipantRecord(self):
        self.tbxParticipants.setEnabled(True)
        row = int(self.tblParticipants.currentRow())
        self.partId = int(self.tblParticipants.item(row,0).text())
        sql = "SELECT id, user_name, first_name, last_name, "
        sql += "email_address, community, family, maiden_name, "
        sql += "gender, marital_status, birth_date, tags, note, "
        sql += "date_created FROM participants WHERE id = %d" % self.partId
        rs = self.cur.execute(sql)
        partData = rs.fetchall()
        self.leParticipantUserName.setText(partData[0][1])
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
        self.readAddressList()
        self.readTelecomList()
        self.contDate = partData[0][13]

    #
    # update participant

    def updateParticipantRecord(self):
        sql = "SELECT max(id) FROM participants;"
        rs = self.cur.execute(sql)
        partData = rs.fetchall()
        userName = self.leParticipantUserName.text()
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
            sql = "INSERT into participants (id, user_name, first_name, "
            sql += "last_name, email_address, community, family, "
            sql += "maiden_name, gender, marital_status, birth_date, tags, "
            sql += "note, date_created, date_modified) "
            sql += "VALUES (%d, '%s', '%s', '%s', '%s', " % (self.partId, userName, firstName, lastName, email)
            sql += "'%s', '%s', '%s', '%s', " % (community, family, maidenName, gender)
            sql += "'%s', '%s', '%s', " % (maritalStatus, birthDate, tags)
            sql += "'%s', '%s', '%s');" % (note, createDate, modDate)
            rCnt = self.tblParticipants.rowCount()
            self.tblParticipants.setRowCount(rCnt+1)
            self.setParticipant(rCnt, [self.partId,userName,firstName,lastName])
        else:
            sql = "UPDATE participants SET "
            sql += "user_name = '%s', " % userName
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
            self.setParticipant(self.tblParticipants.currentRow(), [self.partId,userName,firstName,lastName])
        self.cur.execute(sql)
        self.conn.commit()

        self.disableParticipantEdit()
        row = self.tblParticipants.currentRow()
        self.tblParticipants.setItemSelected(self.tblParticipants.item(row,0),False)
        self.tblParticipants.setItemSelected(self.tblParticipants.item(row,1),False)
        self.tblParticipants.setItemSelected(self.tblParticipants.item(row,2),False)
        self.tblParticipants.setItemSelected(self.tblParticipants.item(row,3),False)
        
    #
    # delete participant

    def deleteParticipantRecord(self):
        # check if participant
        sql = "SELECT count(*) FROM interviewees WHERE participant_id = %d" % self.partId
        rs = self.cur.execute(sql)
        confData = rs.fetchall()
        isParticipant = False
        if confData[0][0] > 0:
            isParticipant = True
        # check if interviewer
        sql = "SELECT count(*) FROM interviews WHERE owner_id = %d" % self.partId
        rs = self.cur.execute(sql)
        confData = rs.fetchall()
        isInterviwer = False
        if confData[0][0] > 0:
            isInterviewer = True
        if isParticipant == True or isInterviewer == True:
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
            self.disableParticipantEdit()
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

    def setAddress(self,x,rec):
        # id
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[0]))
        item.setToolTip('Id')
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

    def readAddressList(self):
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
            self.setAddress(x,rec)
            x = x + 1
        self.tblAddresses.setColumnWidth(0,75)
        self.tblAddresses.setColumnWidth(1,50)
        self.tblAddresses.setColumnWidth(2,200)
        self.disableAddressEdit()

    #
    # check if address is selected or unselected
    
    def checkAddressSelection(self):
        
        if len(self.tblAddresses.selectedItems()) == 0:
            # change widget states
            self.disableAddressEdit()
        else:
            # change widget states
            self.enableAddressEdit()
            # read information
            self.readAddressRecord()

    #
    # set edit of address

    def enableAddressEdit(self):
        # tab list and buttons
        self.frParticipants.setDisabled(True)
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

    def disableAddressEdit(self):
        # tab list and buttons
        self.frParticipants.setEnabled(True)
        # other controls
        self.clearAddressValues()
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

    def clearAddressValues(self):
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

    def newAddressEdit(self):
        self.clearAddressValues()
        self.enableAddressEdit()
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

    def cancelAddressEdit(self):
        self.clearAddressValues()
        self.disableAddressEdit()
        row = self.tblAddresses.currentRow()
        self.tblAddresses.setItemSelected(self.tblAddresses.item(row,0),False)
        self.tblAddresses.setItemSelected(self.tblAddresses.item(row,1),False)
        self.tblAddresses.setItemSelected(self.tblAddresses.item(row,2),False)

    #
    # read address

    def readAddressRecord(self):
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

    def updateAddressRecord(self):
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
            self.setAddress(rCnt, [self.addrId, addrType, lineOne])
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
            self.setAddress(self.tblAddresses.currentRow(), [self.addrId, addrType, lineOne])
        self.cur.execute(sql)
        self.conn.commit()

        self.disableAddressEdit()
        row = self.tblAddresses.currentRow()
        self.tblAddresses.setItemSelected(self.tblAddresses.item(row,0),False)
        self.tblAddresses.setItemSelected(self.tblAddresses.item(row,1),False)
        self.tblAddresses.setItemSelected(self.tblAddresses.item(row,2),False)
        
    #
    # delete address
    
    def deleteAddressRecord(self):
        sql = "DELETE FROM addresses WHERE id = %d" % self.addrId
        self.cur.execute(sql)
        self.conn.commit()
        self.clearAddressValues()
        self.disableAddressEdit()
        # remove row
        row = self.tblAddresses.currentRow()
        self.tblAddresses.removeRow(row)
        row = self.tblAddresses.currentRow()
        self.tblAddresses.setItemSelected(self.tblAddresses.item(row,0),False)
        self.tblAddresses.setItemSelected(self.tblAddresses.item(row,1),False)
        self.tblAddresses.setItemSelected(self.tblAddresses.item(row,2),False)

    #
    # clear address widgets

    def clearAddresses(self):
        self.tblAddresses.clear()
        

    ########################################################
    #           manage participant telecoms                #
    ########################################################
    
    #
    # add / update participant telecom record to telecom table widget

    def setTelecom(self,x,rec):
        # id
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[0]))
        item.setToolTip('Id')
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

    def readTelecomList(self):
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
            self.setTelecom(x,rec)
            x = x + 1
        self.tblTelecoms.setColumnWidth(0,75)
        self.tblTelecoms.setColumnWidth(1,50)
        self.tblTelecoms.setColumnWidth(2,200)
        self.disableTelecomEdit()

    #
    # check if telecom is selected or unselected
    
    def checkTelecomSelection(self):
        
        if len(self.tblTelecoms.selectedItems()) == 0:
            # change widget states
            self.disableTelecomEdit()
        else:
            # change widget states
            self.enableTelecomEdit()
            # read information
            self.readTelecomRecord()

    #
    # set edit of telecom

    def enableTelecomEdit(self):
        # tab list and buttons
        self.frParticipants.setDisabled(True)
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

    def disableTelecomEdit(self):
        # tab list and buttons
        self.frParticipants.setEnabled(True)
        # other controls
        self.clearTelecomValues()
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

    def clearTelecomValues(self):
        self.cbTelType.setCurrentIndex(0)
        self.leTelNumber.setText('')
        
    #
    # new telecom

    def newTelecomEdit(self):
        self.clearTelecomValues()
        self.enableTelecomEdit()
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

    def cancelTelecomEdit(self):
        self.clearTelecomValues()
        self.disableTelecomEdit()
        row = self.tblTelecoms.currentRow()
        self.tblTelecoms.setItemSelected(self.tblTelecoms.item(row,0),False)
        self.tblTelecoms.setItemSelected(self.tblTelecoms.item(row,1),False)
        self.tblTelecoms.setItemSelected(self.tblTelecoms.item(row,2),False)

    #
    # read telecom

    def readTelecomRecord(self):
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

    def updateTelecomRecord(self):
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
            self.setTelecom(rCnt, [self.teleId, telType, telNumber])
        else:
            sql = "UPDATE telecoms SET "
            sql += "telecom_type = '%s', " % telType
            sql += "telecom = '%s', " % telNumber
            sql += "date_created = '%s', " % createDate
            sql += "date_modified = '%s' " % modDate
            sql += "where id = %d;" % self.teleId
            self.setTelecom(self.tblTelecoms.currentRow(), [self.teleId, telType, telNumber])
        self.cur.execute(sql)
        self.conn.commit()

        self.disableTelecomEdit()
        row = self.tblTelecoms.currentRow()
        self.tblTelecoms.setItemSelected(self.tblTelecoms.item(row,0),False)
        self.tblTelecoms.setItemSelected(self.tblTelecoms.item(row,1),False)
        self.tblTelecoms.setItemSelected(self.tblTelecoms.item(row,2),False)
        
    #
    # delete telecom
    
    def deleteTelecomRecord(self):
        sql = "DELETE FROM telecoms WHERE id = %d" % self.teleId
        self.cur.execute(sql)
        self.conn.commit()
        self.clearTelecomValues()
        self.disableTelecomEdit()
        # remove row
        row = self.tblTelecoms.currentRow()
        self.tblTelecoms.removeRow(row)
        row = self.tblTelecoms.currentRow()
        self.tblTelecoms.setItemSelected(self.tblTelecoms.item(row,0),False)
        self.tblTelecoms.setItemSelected(self.tblTelecoms.item(row,1),False)
        self.tblTelecoms.setItemSelected(self.tblTelecoms.item(row,2),False)

    #
    # clear telecom widgets

    def clearTelecoms(self):
        self.tblTelecoms.clear()
        

    ########################################################
    #               manage interview tables                #
    ########################################################

    #
    # add / update interview record to interview table widget

    def setInterview(self,x,rec):
        # id
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[0]))
        item.setToolTip('Id')
        self.tblInterviews.setItem(x,0,item)
        # code
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[1]))
        item.setToolTip('Code')
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

    def readInterviewList(self):
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
        header.append('Code')
        header.append('Description')
        header.append('Status')
        self.tblInterviews.setHorizontalHeaderLabels(header)
        # add content
        x = 0
        for rec in intvData:
            self.setInterview(x,rec)
            x = x + 1
        self.disableInterviewEdit()
        self.tblInterviews.setColumnWidth(0,75)
        self.tblInterviews.setColumnWidth(1,75)
        self.tblInterviews.setColumnWidth(2,350)
        self.tblInterviews.setColumnWidth(3,75)

    #
    # check if interview is selected or unselected
    
    def checkInterviewSelection(self):
        
        if len(self.tblInterviews.selectedItems()) == 0:
            # change widget states
            self.disableInterviewEdit()
        else:
            # change widget states
            self.enableInterviewEdit()
            # read information
            self.readInterviewRecord()

    #
    # set edit of interview

    def enableInterviewEdit(self):
        # other tabs & main control
        self.twSettings.setDisabled(True)
        self.twProject.setDisabled(True)
        self.twParticipants.setDisabled(True)
        self.pbDialogClose.setDisabled(True)
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

    def disableInterviewEdit(self):
        # other tabs & main control
        self.twSettings.setEnabled(True)
        self.twProject.setEnabled(True)
        self.twParticipants.setEnabled(True)
        self.pbDialogClose.setEnabled(True)
        # controls on this tab
        self.clearInterviewValues()
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

    def clearInterviewValues(self):
        self.leInterviewCode.setText('')
        self.pteInterviewDescription.setPlainText('')
        self.dteStart.setDateTime(datetime.datetime.strptime("2000-01-01 12:00","%Y-%m-%d %H:%M"))
        self.dteEnd.setDateTime(datetime.datetime.strptime("2000-01-01 12:00","%Y-%m-%d %H:%M"))
        self.leFirstName.setText('')
        self.leInterviewTags.setText('')
        self.leInterviewLocation.setText('')
        self.pteInterviewNote.setPlainText('')
        self.cbInterviewSecurity.setCurrentIndex(0)
        self.cbInterviewer.setCurrentIndex(0)
        
    #
    # new interview

    def newInterviewEdit(self):
        self.clearInterviewValues()
        self.refreshInterviewerWidget()
        self.enableInterviewEdit()
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

    def cancelInterviewEdit(self):
        self.clearInterviewValues()
        self.disableInterviewEdit()
        row = self.tblInterviews.currentRow()
        self.tblInterviews.setItemSelected(self.tblInterviews.item(row,0),False)
        self.tblInterviews.setItemSelected(self.tblInterviews.item(row,1),False)
        self.tblInterviews.setItemSelected(self.tblInterviews.item(row,2),False)
        self.tblInterviews.setItemSelected(self.tblInterviews.item(row,3),False)

    #
    # populate interviewer combobox

    def refreshInterviewerWidget(self):
        sql = "SELECT id, first_name, last_name "
        sql += "FROM participants ORDER BY last_name, first_name;"
        rs = self.cur.execute(sql)
        partData = rs.fetchall()
        self.cbInterviewer.clear()
        self.interviewerList = []
        for part in partData:
            self.cbInterviewer.addItem("%s, %s" % (part[2],part[1]))
            self.interviewerList.append(part)

    #
    # read interview

    def readInterviewRecord(self):
        self.refreshInterviewerWidget()
        self.tbxInterview.setEnabled(True)
        row = int(self.tblInterviews.currentRow())
        self.intvId = int(self.tblInterviews.item(row,0).text())
        sql = "SELECT id, project_id, code, start_datetime, end_datetime, "
        sql += "description, interview_location, note, tags, data_status, "
        sql += "data_security, owner_id, date_created, date_modified "
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
        if intvData[0][10] == 'PU':
            self.cbInterviewSecurity.setCurrentIndex(0)
        elif intvData[0][10] == 'CO':
            self.cbInterviewSecurity.setCurrentIndex(1)
        elif intvData[0][10] == 'RS':
            self.cbInterviewSecurity.setCurrentIndex(2)
        else:
            self.cbInterviewSecurity.setCurrentIndex(3)
        x = 0
        for x in range(len(self.interviewerList)):
            if self.interviewerList[x][0] == intvData[0][11]:
                self.cbInterviewer.setCurrentIndex(x)
                break
        self.intvDate = intvData[0][12]
        self.readInterviewParticipantList()

    #
    # update interview

    def updateInterviewRecord(self):
        sql = "SELECT max(id) FROM interviews;"
        rs = self.cur.execute(sql)
        intvData = rs.fetchall()
        code = self.leInterviewCode.text()
        description = self.pteInterviewDescription.document().toPlainText()
        startDate = self.dteStart.dateTime().toPyDateTime().isoformat()[:16].replace('T',' ')
        endDate = self.dteStart.dateTime().toPyDateTime().isoformat()[:16].replace('T',' ')
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
        # owner
        ownerId = self.interviewerList[self.cbInterviewer.currentIndex()][0]
        if self.intvDate == None or self.intvDate == '':
            createDate = datetime.datetime.now().isoformat()[:10]
            modDate = createDate
        else:
            createDate = self.intvDate
            modDate = datetime.datetime.now().isoformat()[:10] 
        if intvData[0][0] == None or intvData[0][0] < self.intvId:
            sql = "INSERT into interviews (id, project_id, code, "
            sql += "start_datetime, end_datetime, description, "
            sql += "interview_location, note, tags, data_status, "
            sql += "data_security, owner_id, date_created, date_modified) "
            sql += "VALUES (%d, %d, " % (self.intvId, self.projId)
            sql += "'%s', '%s', '%s', "% (code, startDate, endDate)
            sql += "'%s', '%s', " % (description, location)
            sql += "'%s', '%s', '%s', " % (note, tags, 'N')
            sql += "'%s', %d, '%s', '%s');" % (security, ownerId, createDate, modDate)
            rCnt = self.tblInterviews.rowCount()
            self.tblInterviews.setRowCount(rCnt+1)
            self.setInterview(rCnt, [self.intvId,code,description,'N'])
        else:
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
            sql += "owner_id = %d, " % ownerId
            sql += "date_created = '%s', " % createDate
            sql += "date_modified = '%s' " % modDate
            sql += "where id = %d;" % self.intvId
            self.setInterview(self.tblInterviews.currentRow(), [self.intvId,code,description,self.interviewStatus])
        self.cur.execute(sql)
        self.conn.commit()

        self.disableInterviewEdit()
        row = self.tblInterviews.currentRow()
        self.tblInterviews.setItemSelected(self.tblInterviews.item(row,0),False)
        self.tblInterviews.setItemSelected(self.tblInterviews.item(row,1),False)
        self.tblInterviews.setItemSelected(self.tblInterviews.item(row,2),False)
        self.tblInterviews.setItemSelected(self.tblInterviews.item(row,3),False)
        
    #
    # delete interview

    def deleteInterviewRecord(self):

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
            self.disableInterviewEdit()
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

    def setInterviewParticipant(self,x,rec):
        # id
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[0]))
        item.setToolTip('Id')
        self.tblInterviewParticipants.setItem(x,0,item)
        # user name
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[1]))
        item.setToolTip('Part. Id')
        self.tblInterviewParticipants.setItem(x,1,item)
        # first name
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(str(rec[2]))
        item.setToolTip('Name')
        self.tblInterviewParticipants.setItem(x,2,item)

    #
    # read interview participant list

    def readInterviewParticipantList(self):
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
            self.setInterviewParticipant(x,rec)
            x = x + 1
        self.tblInterviewParticipants.setColumnWidth(0,75)
        self.tblInterviewParticipants.setColumnWidth(1,75)
        self.tblInterviewParticipants.setColumnWidth(2,200)
        self.disableInterviewParticipantEdit()

    #
    # check if participant is selected or unselected
    
    def checkInterviewParticipantSelection(self):
        
        if len(self.tblInterviewParticipants.selectedItems()) == 0:
            # change widget states
            self.disableInterviewParticipantEdit()
        else:
            # change widget states
            self.enableInterviewParticipantEdit()
            # read information
            self.readInterviewParticipantRecord()

    #
    # set edit of participant

    def enableInterviewParticipantEdit(self):
        # tab list and buttons
        self.frInterviews.setDisabled(True)
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

    def disableInterviewParticipantEdit(self):
        # tab list and buttons
        self.frInterviews.setEnabled(True)
        # other controls
        self.clearInterviewParticipantValues()
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

    def clearInterviewParticipantValues(self):
        self.cbIntPartName.setCurrentIndex(0)
        self.leIntPartCommunity.setText('')
        self.leIntPartFamily.setText('')
        
    #
    # new participant

    def newInterviewParticipantEdit(self):
        self.clearInterviewParticipantValues()
        self.refreshInterviewParticipantWidget()
        self.enableInterviewParticipantEdit()
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
        x = self.cbIntPartName.currentIndex()
        if len(self.participantList) > 0:
            self.leIntPartCommunity.setText(self.participantList[x][3])
            self.leIntPartFamily.setText(self.participantList[x][4])
    
    #
    # cancel participant edits

    def cancelInterviewParticipantEdit(self):
        self.clearInterviewParticipantValues()
        self.disableInterviewParticipantEdit()
        row = self.tblInterviewParticipants.currentRow()
        self.tblInterviewParticipants.setItemSelected(self.tblInterviewParticipants.item(row,0),False)
        self.tblInterviewParticipants.setItemSelected(self.tblInterviewParticipants.item(row,1),False)
        self.tblInterviewParticipants.setItemSelected(self.tblInterviewParticipants.item(row,2),False)

    #
    # populate participant combobox

    def refreshInterviewParticipantWidget(self):
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

    def readInterviewParticipantRecord(self):
        self.clearInterviewParticipantValues()
        self.refreshInterviewParticipantWidget()
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

    def updateInterviewParticipantRecord(self):
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
            self.setInterviewParticipant(rCnt, [self.intvPartId,participantId,userName])
        else:
            sql = "UPDATE interviewees SET "
            sql += "participant_id = '%s', " % participantId
            sql += "community = '%s', " % community
            sql += "family = '%s', " % family
            sql += "date_created = '%s', " % createDate
            sql += "date_modified = '%s' " % modDate
            sql += "where id = %d;" % self.intvPartId
            self.setInterviewParticipant(self.tblInterviewParticipants.currentRow(), [self.intvPartId,participantId,userName])
        self.cur.execute(sql)
        self.conn.commit()

        self.disableInterviewParticipantEdit()
        row = self.tblInterviewParticipants.currentRow()
        self.tblInterviewParticipants.setItemSelected(self.tblInterviewParticipants.item(row,0),False)
        self.tblInterviewParticipants.setItemSelected(self.tblInterviewParticipants.item(row,1),False)
        self.tblInterviewParticipants.setItemSelected(self.tblInterviewParticipants.item(row,2),False)
        
    #
    # delete participant
    
    def deleteInterviewParticipantRecord(self):
        sql = "DELETE FROM interviewees WHERE id = %d" % self.intvPartId
        self.cur.execute(sql)
        self.conn.commit()
        self.clearInterviewParticipantValues()
        self.disableInterviewParticipantEdit()
        # remove row
        row = self.tblInterviewParticipants.currentRow()
        self.tblInterviewParticipants.removeRow(row)
        row = self.tblInterviewParticipants.currentRow()
        self.tblInterviewParticipants.setItemSelected(self.tblInterviewParticipants.item(row,0),False)
        self.tblInterviewParticipants.setItemSelected(self.tblInterviewParticipants.item(row,1),False)
        self.tblInterviewParticipants.setItemSelected(self.tblInterviewParticipants.item(row,2),False)

    #
    # clear participant widgets

    def clearInterviewParticipants(self):
        self.tblInterviewParticipants.clear()
        

