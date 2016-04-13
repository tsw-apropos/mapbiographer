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
import os, datetime, time, json, sys
import inspect, imp
import platform, subprocess
from qgis.utils import plugins

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
        # lmb config and files
        self.dirName = '.'
        self.projFile = ''
        self.oggencFile = ''
        self.projDict = {}
        self.heritageCommunity = 'N/A'
        self.heritageUser = 'N/A'
        self.enableReference = False
        self.settingsEnableEdit = False
        self.baseGroups = []
        self.projCodeList = []
        self.docCodeList = []
        self.partCodeList = []
        
        # object variables
        self.projDate = None
        self.contDate = None
        self.addrDate = None
        self.teleDate = None
        self.intvDate = None
        self.intvPartDate = None
        self.projId = None
        self.projIdMax = 0
        self.partId = 1
        self.partIdMax = 0
        self.addrId = 1
        self.addrIdMax = 0
        self.teleId = 1
        self.teleIdMax = 0
        self.intvId = 1
        self.intvIdMax = 0
        self.intvPartId = 1
        self.intvPartIdMax = 0
        self.participantList = []
        self.interviewerList = []
        self.interviewStatus = 'N'

        self.setWindowTitle('LMB Manager')

        # signal / slot connections
        # main form
        QtCore.QObject.connect(self.pbDialogClose, QtCore.SIGNAL("clicked()"), self.closeDialog)
        # map biographer settings tab actions
        # qgis settings
        QtCore.QObject.connect(self.tbSelectProjectDir, QtCore.SIGNAL("clicked()"), self.qgsSettingsGetDir)
        QtCore.QObject.connect(self.cbCurrentProject, QtCore.SIGNAL("currentIndexChanged(int)"), self.qgsSettingsSelectCreateProject)
        QtCore.QObject.connect(self.tbOggEnc, QtCore.SIGNAL("clicked()"), self.qgsSettingsGetOgg)
        QtCore.QObject.connect(self.pbSaveSettings, QtCore.SIGNAL("clicked()"), self.qgsSettingsSave)
        QtCore.QObject.connect(self.pbCancelSettings, QtCore.SIGNAL("clicked()"), self.qgsSettingsCancel)
        QtCore.QObject.connect(self.pbDeleteProject, QtCore.SIGNAL("clicked()"), self.projectDelete)
        QtCore.QObject.connect(self.pbSystemTest, QtCore.SIGNAL("clicked()"), self.qgsTestSystem)
        QtCore.QObject.connect(self.leOggEnc, QtCore.SIGNAL("textChanged(const QString&)"), self.qgsSettingsEnableEdit)
        # lmb project settings
        QtCore.QObject.connect(self.cbMaxScale, QtCore.SIGNAL("currentIndexChanged(int)"), self.projectSetMapScaleDown)
        QtCore.QObject.connect(self.cbMinScale, QtCore.SIGNAL("currentIndexChanged(int)"), self.projectSetMapScaleUp)
        QtCore.QObject.connect(self.cbZoomRangeNotices, QtCore.SIGNAL("currentIndexChanged(int)"), self.projectMapSettingsEnableEdit)
        QtCore.QObject.connect(self.tbSelectQgsProject, QtCore.SIGNAL("clicked()"), self.qgisProjectRead)
        QtCore.QObject.connect(self.tblBaseGroups, QtCore.SIGNAL("itemSelectionChanged()"), self.qgisBaseGroupEnableRemoval)
        QtCore.QObject.connect(self.pbAddBaseGroup, QtCore.SIGNAL("clicked()"), self.qgisBaseGroupAdd)
        QtCore.QObject.connect(self.pbRemoveBaseGroup, QtCore.SIGNAL("clicked()"), self.qgisBaseGroupRemove)
        QtCore.QObject.connect(self.cbBoundaryLayer, QtCore.SIGNAL("currentIndexChanged(int)"), self.qgisBoundaryLayerUpdate)
        QtCore.QObject.connect(self.cbEnableReference, QtCore.SIGNAL("currentIndexChanged(int)"), self.qgisReferenceLayerSetStatus)
        QtCore.QObject.connect(self.cbReferenceLayer, QtCore.SIGNAL("currentIndexChanged(int)"), self.qgisReferenceLayerUpdate)
        QtCore.QObject.connect(self.pbSaveProjectMapSettings, QtCore.SIGNAL("clicked()"), self.projectMapSettingsSave)
        QtCore.QObject.connect(self.pbCancelProjectMapSettings, QtCore.SIGNAL("clicked()"), self.projectMapSettingsCancel)
        QtCore.QObject.connect(self.pbTransfer, QtCore.SIGNAL("clicked()"), self.transferData)
        #
        # project details tab states
        QtCore.QObject.connect(self.leProjectCode, QtCore.SIGNAL("textChanged(QString)"), self.projectDetailsEnableEdit)
        QtCore.QObject.connect(self.pteProjectDescription, QtCore.SIGNAL("textChanged()"), self.projectDetailsEnableEdit)
        QtCore.QObject.connect(self.leProjectTags, QtCore.SIGNAL("textChanged(QString)"), self.projectDetailsEnableEdit)
        QtCore.QObject.connect(self.pteProjectNote, QtCore.SIGNAL("textChanged()"), self.projectDetailsEnableEdit)
        QtCore.QObject.connect(self.pteContentCodes, QtCore.SIGNAL("textChanged()"), self.projectDetailsEnableEdit)
        QtCore.QObject.connect(self.pteDateAndTime, QtCore.SIGNAL("textChanged()"), self.projectDetailsEnableEdit)
        QtCore.QObject.connect(self.pteTimeOfYear, QtCore.SIGNAL("textChanged()"), self.projectDetailsEnableEdit)
        QtCore.QObject.connect(self.tbSortCodes, QtCore.SIGNAL("clicked()"), self.projectSortCodeList)
        QtCore.QObject.connect(self.cbDefaultCode, QtCore.SIGNAL("currentIndexChanged(int)"), self.projectDetailsEnableEdit)
        QtCore.QObject.connect(self.cbPointCode, QtCore.SIGNAL("currentIndexChanged(int)"), self.projectDetailsEnableEdit)
        QtCore.QObject.connect(self.cbLineCode, QtCore.SIGNAL("currentIndexChanged(int)"), self.projectDetailsEnableEdit)
        QtCore.QObject.connect(self.cbPolygonCode, QtCore.SIGNAL("currentIndexChanged(int)"), self.projectDetailsEnableEdit)
        QtCore.QObject.connect(self.pbProjectDetailsSave, QtCore.SIGNAL("clicked()"), self.projectDetailsSave)
        QtCore.QObject.connect(self.pbProjectDetailsCancel, QtCore.SIGNAL("clicked()"), self.projectDetailsCancel)
        #
        # people basic info actions
        QtCore.QObject.connect(self.pbParticipantNew, QtCore.SIGNAL("clicked()"), self.participantNew)
        QtCore.QObject.connect(self.pbParticipantCancel, QtCore.SIGNAL("clicked()"), self.participantCancelEdit)
        QtCore.QObject.connect(self.pbParticipantSave, QtCore.SIGNAL("clicked()"), self.participantSave)
        QtCore.QObject.connect(self.pbParticipantDelete, QtCore.SIGNAL("clicked()"), self.participantDelete)
        # people basic info states
        QtCore.QObject.connect(self.tblParticipants, QtCore.SIGNAL("itemSelectionChanged()"), self.participantCheckSelection)
        # people address actions
        QtCore.QObject.connect(self.pbAddNew, QtCore.SIGNAL("clicked()"), self.addressNew)
        QtCore.QObject.connect(self.pbAddCancel, QtCore.SIGNAL("clicked()"), self.addressCancelEdit)
        QtCore.QObject.connect(self.pbAddSave, QtCore.SIGNAL("clicked()"), self.addressSave)
        QtCore.QObject.connect(self.pbAddDelete, QtCore.SIGNAL("clicked()"), self.addressDelete)
        # people address states
        QtCore.QObject.connect(self.tblAddresses, QtCore.SIGNAL("itemSelectionChanged()"), self.addressCheckSelection)
        # people telecom actions
        QtCore.QObject.connect(self.pbTelNew, QtCore.SIGNAL("clicked()"), self.telecomNew)
        QtCore.QObject.connect(self.pbTelCancel, QtCore.SIGNAL("clicked()"), self.telecomCancelEdits)
        QtCore.QObject.connect(self.pbTelSave, QtCore.SIGNAL("clicked()"), self.telecomSave)
        QtCore.QObject.connect(self.pbTelDelete, QtCore.SIGNAL("clicked()"), self.telecomDelete)
        # people telecom states
        QtCore.QObject.connect(self.tblTelecoms, QtCore.SIGNAL("itemSelectionChanged()"), self.telecomCheckSelection)
        #
        # interview basic info actions
        QtCore.QObject.connect(self.pbIntNew, QtCore.SIGNAL("clicked()"), self.interviewNew)
        QtCore.QObject.connect(self.pbIntCancel, QtCore.SIGNAL("clicked()"), self.interviewCancelEdits)
        QtCore.QObject.connect(self.pbIntSave, QtCore.SIGNAL("clicked()"), self.interviewSave)
        QtCore.QObject.connect(self.pbIntDelete, QtCore.SIGNAL("clicked()"), self.interviewDelete)
        # interview basic info states
        QtCore.QObject.connect(self.tblInterviews, QtCore.SIGNAL("itemSelectionChanged()"), self.interviewCheckSelection)
        # interview participant actions
        QtCore.QObject.connect(self.pbIntPartNew, QtCore.SIGNAL("clicked()"), self.interviewParticipantNew)
        QtCore.QObject.connect(self.pbIntPartCancel, QtCore.SIGNAL("clicked()"), self.interviewParticipantCancel)
        QtCore.QObject.connect(self.pbIntPartSave, QtCore.SIGNAL("clicked()"), self.interviewParticipantSave)
        QtCore.QObject.connect(self.pbIntPartDelete, QtCore.SIGNAL("clicked()"), self.interviewParticipantDelete)
        # interview participant states
        QtCore.QObject.connect(self.tblInterviewParticipants, QtCore.SIGNAL("itemSelectionChanged()"), self.interviewParticipantCheckSelection)
        # participant edit selection
        QtCore.QObject.connect(self.cbIntPartName, QtCore.SIGNAL("currentIndexChanged(int)"), self.interviewParticipantSelection)
        
        # event trigger control variables
        self.qgsProjectChanged = True
        self.projectState = 'load'

        try:
            self.qgsSettingsRead()
            self.projectDetailsDisableEdit()
            self.projectMapSettingsDisableEdit()
            self.qgsSettingsDisableEdit()
            self.participantDisableEdit()
            self.interviewDisableEdit()
        except:
            self.projectDisable()
            self.projectDetailsDisableEdit()
            self.projectMapSettingsDisableEdit()
            self.qgsSettingsDisableEdit()
            self.participantDisableEdit()
            self.interviewDisableEdit()
        
        self.projectState = 'edit'

    #
    # close dialog
    #
    def closeDialog(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        tv = self.iface.layerTreeView()
        tv.selectionModel().clear()
        self.iface.newProject()
        self.close()


    #
    ########################################################
    #               Map Biographer Settings Tab            #
    ########################################################
    #
    # read qgis LMB settings
    #
    def qgsSettingsRead(self):

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
        # select project
        rv = s.value('mapBiographer/projectId')
        if rv == None:
            self.projId = None
        else:
            self.projId = int(rv)
        # oggenc executable
        rv = s.value('mapBiographer/oggencFile')
        if rv == None:
            self.oggencFile = ''
        else:
            self.oggencFile = rv
        self.leOggEnc.setText(self.oggencFile)
        if os.path.exists(os.path.join(self.dirName,'lmb-project-info.json')):
            self.projectFileRead()
        else:
            self.projectFileCreate()

    #
    # get project directory
    #
    def qgsSettingsGetDir(self):
        
        lmbdir = QtGui.QFileDialog.getExistingDirectory(self, 'Select Directory')
        if lmbdir == '':
            lmbdir = '.'
        self.leProjectDir.setText(lmbdir)
        self.dirName = lmbdir
        self.projectFileCreate()
        intvDir = os.path.join(self.dirName,"interviews")
        if not os.path.exists(intvDir):
            os.mkdir(intvDir)
        imgDir = os.path.join(self.dirName,"images")
        if not os.path.exists(imgDir):
            os.mkdir(imgDir)
        mediaDir = os.path.join(self.dirName,"media")
        if not os.path.exists(mediaDir):
            os.mkdir(mediaDir)
        self.projectListRefresh()
        self.qgsSettingsEnableEdit()

    #
    # select or project
    #
    def qgsSettingsSelectCreateProject(self):
        
        if self.projectState <> 'load':
            self.qgsSettingsEnableEdit()
            if self.debug:
                QgsMessageLog.logMessage(self.myself())
            if self.cbCurrentProject.currentIndex() == 1:
                # create new project
                newName, ok = QtGui.QInputDialog.getText(self, 'Project Code', 'Enter code for new project:')
                if ok:
                    newName = newName.strip()
                    if newName in self.projCodeList:
                        messageText = "The project code %s already exists. A unique code is required" % newName
                        response = QtGui.QMessageBox.warning(self, 'Warning',
                            messageText, QtGui.QMessageBox.Ok)
                    else:
                        self.projCodeList.append(newName)
                        self.projCodeList = list(set(self.projCodeList))
                        self.projIdMax += 1
                        self.projDict["projects"][str(self.projIdMax)] = {
                            "id":self.projIdMax,
                            "code": newName,
                            "description": "",
                            "note": "",
                            "tags": [],
                            "citation": "",
                            "source": "",
                            "default_codes": [
                                ["S","Section"]
                            ],
                            "default_time_periods": [],
                            "default_time_of_year": [],
                            "ns_code": "S",
                            "pt_code": "S",
                            "ln_code": "S",
                            "pl_code": "S",
                            "lmb_map_settings": {},
                            "documents": {}
                        }
                        self.projId = self.projIdMax
                        self.cbCurrentProject.addItem(newName)
                        self.cbCurrentProject.setCurrentIndex(self.cbCurrentProject.count()-1)
                        self.projectFileSave()
                else:
                    self.projId = None
                    self.cbCurrentProject.setCurrentIndex(0)
            elif self.cbCurrentProject.currentIndex() == 0:
                # select no project
                self.projId = None
            elif self.cbCurrentProject.currentIndex() > 1:
                # select an existing project
                for key,value in self.projDict["projects"].iteritems():
                    if value["code"] == self.cbCurrentProject.currentText():
                        self.projId = key

    #
    # enable settings buttons
    #
    def qgsSettingsEnableEdit(self):

        if self.pbDialogClose.isEnabled():
            if self.debug:
                QgsMessageLog.logMessage(self.myself())
            # enable save and cancel
            self.pbSaveSettings.setEnabled(True)
            self.pbCancelSettings.setEnabled(True)
            self.pbSystemTest.setDisabled(True)
            if self.pbDeleteProject.isEnabled():
                self.pbDeleteProject.setDisabled(True)
            self.twMapBioSettings.tabBar().setDisabled(True)
            self.frProjectMapSettings.setDisabled(True)
            # other tabs
            self.tbProjectDetails.setDisabled(True)
            self.tbPeople.setDisabled(True)
            self.tbInterviews.setDisabled(True)
            # dialog close
            self.pbDialogClose.setDisabled(True)

    #
    # disable settings buttons
    #
    def qgsSettingsDisableEdit(self):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # disable save and cancel
        self.pbSaveSettings.setDisabled(True)
        self.pbCancelSettings.setDisabled(True)
        self.pbSystemTest.setEnabled(True)
        if self.cbCurrentProject.count() > 2 and self.projId <> None:
            self.pbDeleteProject.setEnabled(True)
        self.twMapBioSettings.tabBar().setEnabled(True)
        self.frProjectMapSettings.setEnabled(True)
        # other tabs
        self.tbProjectDetails.setEnabled(True)
        self.tbPeople.setEnabled(True)
        self.tbInterviews.setEnabled(True)
        # dialog close
        self.pbDialogClose.setEnabled(True)
        
        
    #
    # save qgis LMB settings
    #
    def qgsSettingsSave(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        s = QtCore.QSettings()
        s.setValue('mapBiographer/projectDir', self.dirName)
        s.setValue('mapBiographer/projectId', self.projId)
        s.setValue('mapBiographer/oggencFile', self.oggencFile)
        self.qgsSettingsDisableEdit()
        if self.projId <> None:
            self.projectLoad()
        else:
            self.qgisProjectClear()
            self.projectMapSettingsCancel()
    #
    # cancel LMB settings
    #
    def qgsSettingsCancel(self):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.qgsSettingsRead()
        self.qgsSettingsDisableEdit()
        self.projectLoad()
    #
    # set location oggenc program
    #
    def qgsSettingsGetOgg(self):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        oef = QtGui.QFileDialog.getOpenFileName(self, 'Select oggenc executable')
        if os.path.exists(oef):
            self.oggencFile = oef
            self.leOggEnc.setText(oef)
        else:
            self.oggencFile = ''
            self.leOggEnc.setText('')
        self.qgsSettingsEnableEdit()
        
    #   
    # test system libraries and plugins
    #
    
    def qgsTestSystem(self):
        
        try:
            # test basic audio
            import pyaudio, wave
            messageText = 'PyAudio is installed and audio is enabled.'
            # test audio conversion
            callList = [self.leOggEnc.text(),'--version']
            try:
                retText = subprocess.check_output(callList)
                oggVer = retText[retText.rindex(' ')+1:-1]
                messageText = messageText + ' Oggenc2 executable found. Version is %s.' % oggVer
            except:
                messageText = messageText + ' Oggenc2 executable could not be found.'
            # test plugins
            if 'redLayer' in plugins:
                if 'joinmultiplelines' in plugins:
                    messageText = messageText + ' The Red Layer and Multiline Join Plugins are installed.'
                else:
                    messageText = messageText + ' The Red Layer Plugin is installed but the Multiline Join plugin is missing.'
                    messageText = messageText + ' Please install missing plugin.'
            else:
                if 'joinmultiplelines' in plugins:
                    messageText = messageText + ' The Red Layer Plugin is missing. The Multiline Join plugin is installed.'
                    messageText = messageText + ' Please install missing plugin.'
                else:
                    messageText = messageText + ' The Red Layer Plugin and the Multiline Join plugin are missing.'
                    messageText = messageText + ' Please install missing plugins.'
            QtGui.QMessageBox.information(self, 'System Status',
                messageText, QtGui.QMessageBox.Ok)
            return(0)
        except:
            messageText = 'PyAudio is not installed. Please install manually.'
            # test audio conversion
            callList = [self.leOggEnc.text(),'--version']
            try:
                retText = subprocess.check_output(callList)
                oggVer = retText[retText.rindex(' ')+1:-1]
                messageText = messageText + ' Oggenc2 executable found. Version is %s.' % oggVer
            except:
                messageText = messageText + ' Oggenc2 executable could not be found.'
            # test plugins
            if 'redLayer' in plugins:
                if 'joinmultiplelines' in plugins:
                    messageText = messageText + ' The Red Layer and Multiline Join Plugins are installed.'
                else:
                    messageText = messageText + ' The Red Layer Plugin is installed but the Multiline Join plugin is missing.'
                    messageText = messageText + ' Please install missing plugin.'
            else:
                if 'joinmultiplelines' in plugins:
                    messageText = messageText + ' The Red Layer Plugin is missing. The Multiline Join plugin is installed.'
                    messageText = messageText + ' Please install missing plugin.'
                else:
                    messageText = messageText + ' The Red Layer Plugin and the Multiline Join plugin are missing.'
                    messageText = messageText + ' Please install missing plugins.'
            QtGui.QMessageBox.critical(self, 'Error',
                messageText, QtGui.QMessageBox.Ok)
            return(0)
    #
    # setup audio libraries
    #
    # NOTE: This is an experimental function and has too many dependecies to function
    #       so it has been replaced with a simple test function above
    #
    #
    #
    def qgsSetupAudio(self):
        
        # test if pyaudio is present
        try:
            import pyaudio, wave
            messageText = 'PyAudio is already installed and audio is enabled.'
            QtGui.QMessageBox.information(self, 'Audio Enabled',
                messageText, QtGui.QMessageBox.Ok)
            return(0)
        except:
            pass
        if platform.system().lower() == 'linux':
            messageText = 'PyAudio is not installed. Please install manually.'
            QtGui.QMessageBox.warning(self, 'Action Needed',
                messageText, QtGui.QMessageBox.Ok)
            return(0)
        elif platform.system().lower() == 'windows':
            # test if pip is present
            try:
                import pip
                pip_present = True
            except:
                pip_present = False
                messageText = 'Pip is not installed. Please install manually and try again.'
                QtGui.QMessageBox.critical(self, 'Error',
                    messageText, QtGui.QMessageBox.Ok)
                return(0)            
            if pip_present == True:
                try:
                    pip.main(['install','--user','pyaudio'])
                    messageText = 'PyAudio was installed successfully. Audio is enabled.'
                    QtGui.QMessageBox.information(self, 'Audio Installed',
                        messageText, QtGui.QMessageBox.Ok)
                    return(0)
                except:
                    messageText = 'Unable to install PyAudio. Please install manually.'
                    QtGui.QMessageBox.critical(self, 'Error',
                        messageText, QtGui.QMessageBox.Ok)
                    return(0)
            else:
                return(0)
        else:
            # test if pip is present
            try:
                import pip
                pip_present = True
            except:
                pip_present = False
                messageText = 'Pip is not installed. Please install manually and try again.'
                QtGui.QMessageBox.critical(self, 'Error',
                    messageText, QtGui.QMessageBox.Ok)
                return(0)            
            if pip_present == True:
                try:
                    pip.main(['install','--user','pyaudio'])
                    messageText = 'PyAudio was installed successfully. Audio is enabled.'
                    QtGui.QMessageBox.information(self, 'Audio Installed',
                        messageText, QtGui.QMessageBox.Ok)
                    return(0)
                except:
                    messageText = 'Unable to install PyAudio. Please install manually.'
                    QtGui.QMessageBox.critical(self, 'Error',
                        messageText, QtGui.QMessageBox.Ok)
                    return(0)
            else:
                return(0)
            

    #
    ########################################################
    #                   LMB File Functions                 #
    ########################################################
    #
    # create lmb project file
    #
    def projectFileCreate(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # make sure path exist
        if os.path.exists(self.dirName):
            nf = os.path.join(self.dirName,'lmb-project-info.json') 
            # only create file if one does not exist
            if os.path.exists(nf) == False:
                f = open(nf,'w')
                self.projDict = {"projects":{},"participants":{}}
                f.write(json.dumps(self.projDict,indent=4))
                f.close()

    #
    # read lmb project file
    #
    def projectFileRead(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # connect
        nf = os.path.join(self.dirName,'lmb-project-info.json')
        if os.path.exists(nf):
            f = open(nf,'r')
            self.projDict = json.loads(f.read())
            f.close()
            self.projectListRefresh()
            self.projectLoad()

    #
    # write lmb file
    #
    def projectFileSave(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # connect
        nf = os.path.join(self.dirName,'lmb-project-info.json')
        if os.path.exists(nf):
            f = open(nf,'w')
            f.write(json.dumps(self.projDict,indent=4))
            f.close()

    #
    # delete lmb project
    #
    def projectDelete(self):
        
        if self.projId <> None:
            if len(self.projDict["projects"][str(self.projId)]["documents"]) > 0:
                messageText = "Can not delete project %s " % self.projDict["projects"][str(self.projId)]["code"]
                messageText += "because it contains content.If you wish to delete it you must delete "
                messageText += "its interviews first."
                QtGui.QMessageBox.warning(self, 'Warning',
                   messageText, QtGui.QMessageBox.Ok)
            else:
                del self.projDict["projects"][str(self.projId)]
                self.projectFileSave()
                self.projectFileRead()
                self.projectDetailsEnableEdit()
                self.projectMapSettingsDisableEdit()
                self.qgsSettingsDisableEdit()
                self.participantDisableEdit()
                self.interviewDisableEdit()

    #
    # refresh project list
    #
    def projectListRefresh(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # populate project database list
        self.cbCurrentProject.clear()
        self.cbCurrentProject.addItem('--None Selected--')
        self.cbCurrentProject.addItem('Create New Project')
        idx = 0
        x = 0
        self.projIdMax = 0
        if self.projDict <> {} and len(self.projDict["projects"]) > 0:
            for key,value in self.projDict["projects"].iteritems():
                self.projCodeList.append(value["code"])
                x += 1
                self.cbCurrentProject.addItem(value["code"])
                if self.projId <> None and int(key) == self.projId:
                    idx = x + 1
                if int(key) > self.projIdMax:
                    self.projIdMax = int(key)
 
        self.cbCurrentProject.setCurrentIndex(idx)


    # 
    # project codes convert list to Text
    #
    def projectCodesListToText(self, codeList):

        codeText = ''
        for item in codeList:
            codeText += item[0] + " = " + item[1] + "\n"
        
        return(codeText)

    #
    # project codes text to list
    #
    def projectCodesTextToList(self, codeText):

        tempList = codeText.split("\n")
        codeList = []
        for item in tempList:
            if "=" in item:
                parts = item.split("=")
                codeList.append([parts[0].strip(),parts[1].strip()])
        
        return(codeList)
        
    #
    # project sort code list
    #
    def projectSortCodeList(self):
        
        codeList = self.projectCodesTextToList(self.pteContentCodes.toPlainText())
        codeList.sort()
        self.pteContentCodes.setPlainText(self.projectCodesListToText(codeList))
        
    #
    ########################################################
    #      Map Biographer Projects and Project Tabs        #
    ########################################################
    #
    # enable project
    #
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
    #
    def projectDisable(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # main tabs
        self.tbProjectDetails.setDisabled(True)
        self.tbPeople.setDisabled(True)
        self.tbInterviews.setDisabled(True)
        self.pbTransfer.setDisabled(True)
        
    #
    # load project
    #
    def projectLoad(self):

        self.projectState = 'load'

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        if self.projId <> None:
            self.projectLoadMapSettings()
            self.projectLoadDetails()
            self.participantListRead()
            self.interviewListRead()

        self.projectState = 'edit'

    #
    # load project map settings
    #
    def projectLoadMapSettings(self):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        mapData = self.projDict["projects"][str(self.projId)]["lmb_map_settings"]
        if mapData <> {}:
            idx = self.cbMaxScale.findText(mapData["max_scale"],QtCore.Qt.MatchExactly)
            if idx <> -1:
                self.cbMaxScale.setCurrentIndex(idx)
            else:
                self.cbMaxScale.setCurrentIndex(0)
            idx = self.cbMinScale.findText(mapData["min_scale"],QtCore.Qt.MatchExactly)
            if idx <> -1:
                self.cbMinScale.setCurrentIndex(idx)
            else:
                self.cbMinScale.setCurrentIndex(0)
            idx = self.cbZoomRangeNotices.findText(mapData["zoom_notices"],QtCore.Qt.MatchExactly)
            if idx <> -1:
                self.cbZoomRangeNotices.setCurrentIndex(idx)
            else:
                self.cbZoomRangeNotices.setCurrentIndex(0)
            if os.path.exists(mapData["qgis_project"]):
                self.leQgsProject.setText(mapData["qgis_project"])
                self.qgisProjectLoad(mapData["qgis_project"])
            else:
                self.leQgsProject.setText("")
                self.qgisProjectClear()
            idx = self.cbBoundaryLayer.findText(mapData["boundary_layer"],QtCore.Qt.MatchExactly)
            if idx <> -1:
                self.cbBoundaryLayer.setCurrentIndex(idx)
            else:
                self.cbBoundaryLayer.setCurrentIndex(0)
            idx = self.cbEnableReference.findText(mapData["enable_reference"],QtCore.Qt.MatchExactly)
            if idx <> -1:
                self.cbEnableReference.setCurrentIndex(idx)
            else:
                self.cbEnableReference.setCurrentIndex(0)
            idx = self.cbReferenceLayer.findText(mapData["reference_layer"],QtCore.Qt.MatchExactly)
            if idx <> -1:
                self.cbReferenceLayer.setCurrentIndex(idx)
            else:
                self.cbReferenceLayer.setCurrentIndex(0)
        else:
            self.cbMaxScale.setCurrentIndex(0)
            self.cbMinScale.setCurrentIndex(0)
            self.cbZoomRangeNotices.setCurrentIndex(0)
            self.qgisProjectClear()
            
    #
    # enable editing of project settings
    #
    def projectMapSettingsEnableEdit(self):
     
        if self.projectState <> 'load' and self.pbDialogClose.isEnabled():
            if self.debug:
                QgsMessageLog.logMessage(self.myself())
            # enable save and cancel
            self.pbSaveProjectMapSettings.setEnabled(True)
            self.pbCancelProjectMapSettings.setEnabled(True)
            self.pbTransfer.setDisabled(True)
            self.twMapBioSettings.tabBar().setDisabled(True)
            self.tbSelectProjectDir.setDisabled(True)
            self.cbCurrentProject.setDisabled(True)
            # other tabs
            self.tbProjectDetails.setDisabled(True)
            self.tbPeople.setDisabled(True)
            self.tbInterviews.setDisabled(True)
            # dialog close
            self.pbDialogClose.setDisabled(True)
        
        
    #
    # disable editing of project settings
    #
    def projectMapSettingsDisableEdit(self):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # disable save and cancel
        self.pbSaveProjectMapSettings.setDisabled(True)
        self.pbCancelProjectMapSettings.setDisabled(True)
        self.pbTransfer.setEnabled(True)
        self.twMapBioSettings.tabBar().setEnabled(True)
        self.tbSelectProjectDir.setEnabled(True)
        self.cbCurrentProject.setEnabled(True)
        # other tabs
        self.tbProjectDetails.setEnabled(True)
        self.tbPeople.setEnabled(True)
        self.tbInterviews.setEnabled(True)
        # dialog close
        self.pbDialogClose.setEnabled(True)
    
    #
    # save map settings and reset interface
    #
    def projectMapSettingsSave(self):
        
        # use temp variable to keep lines shorter
        temp = {}
        temp["max_scale"] = self.cbMaxScale.currentText()
        temp["min_scale"] = self.cbMinScale.currentText()
        temp["zoom_notices"] = self.cbZoomRangeNotices.currentText()
        temp["qgis_project"] = self.leQgsProject.text()
        temp["base_groups"] = self.baseGroups
        temp["boundary_layer"] = self.cbBoundaryLayer.currentText()
        temp["enable_reference"] = self.cbEnableReference.currentText()
        if self.cbEnableReference.currentText() == "No":
            temp["reference_layer"] = ''
        else:
            temp["reference_layer"] = self.cbReferenceLayer.currentText()
        self.projDict["projects"][str(self.projId)]["lmb_map_settings"] = temp
        self.projectFileSave()
        self.projectMapSettingsDisableEdit()
        
    #
    # cancel changes to map settinns and reset interface
    #
    def projectMapSettingsCancel(self):
        
        self.projectFileRead()
        self.projectLoad()
        self.projectMapSettingsDisableEdit()
        
    #
    # update code list and combo boxes
    #
    def projectUpdateCodeLists(self, projData):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        self.cbDefaultCode.clear()
        self.cbPointCode.clear()
        self.cbLineCode.clear()
        self.cbPolygonCode.clear()
        x = 0
        ns_idx = 0
        pt_idx = 0
        ln_idx = 0
        pl_idx = 0
        for item in projData["default_codes"]:
            text = "%s (%s)" % tuple(item)
            self.cbDefaultCode.addItem(text)
            self.cbPointCode.addItem(text)
            self.cbLineCode.addItem(text)
            self.cbPolygonCode.addItem(text)
            if item[0] == projData["ns_code"]:
                ns_idx = x
            if item[0] == projData["pt_code"]:
                pt_idx = x
            if item[0] == projData["ln_code"]:
                ln_idx = x
            if item[0] == projData["pl_code"]:
                pl_idx = x
            x += 1
        self.cbDefaultCode.setCurrentIndex(ns_idx)
        self.cbPointCode.setCurrentIndex(pt_idx)
        self.cbLineCode.setCurrentIndex(ln_idx)
        self.cbPolygonCode.setCurrentIndex(pl_idx)

    #
    # load project details
    #
    def projectLoadDetails(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        projData = self.projDict["projects"][str(self.projId)]
        self.leProjectCode.setText(projData["code"])
        self.pteProjectDescription.setPlainText(projData["description"])
        self.pteProjectNote.setPlainText(projData["note"])
        self.leProjectTags.setText(",".join(projData["tags"]))
        self.pteProjectCitation.setPlainText(projData["citation"])
        self.pteProjectSource.setPlainText(projData["source"])
        self.pteDateAndTime.setPlainText(self.projectCodesListToText(projData["default_time_periods"]))
        self.pteTimeOfYear.setPlainText(self.projectCodesListToText(projData["default_time_of_year"]))
        self.pteContentCodes.setPlainText(self.projectCodesListToText(projData["default_codes"]))
        self.projectUpdateCodeLists(projData)

    #
    # enable project edit
    #
    def projectDetailsEnableEdit(self):

        if self.projectState <> 'load' and self.pbDialogClose.isEnabled():
            if self.debug:
                QgsMessageLog.logMessage(self.myself())
            # other tabs & main control
            self.pbDialogClose.setDisabled(True)
            self.twMapBioSettings.tabBar().setDisabled(True)
            # controls on this tab
            self.pbProjectDetailsSave.setEnabled(True)
            self.pbProjectDetailsCancel.setEnabled(True)
            # dialog close
            self.pbDialogClose.setDisabled(True)

    #
    # disable project edit
    #
    def projectDetailsDisableEdit(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # other tabs & main control
        self.pbDialogClose.setEnabled(True)
        self.twMapBioSettings.tabBar().setEnabled(True)
        # controls on this tab
        self.pbProjectDetailsSave.setDisabled(True)
        self.pbProjectDetailsCancel.setDisabled(True)
        # dialog close
        self.pbDialogClose.setEnabled(True)

    #
    # project details save
    #
    def projectDetailsSave(self):
        
        projData = self.projDict["projects"][str(self.projId)]
        projData["description"] = self.pteProjectDescription.toPlainText()
        projData["note"] = self.pteProjectNote.toPlainText()
        tagText = self.leProjectTags.text()
        if tagText == "":
            projTags = []
        else:
            tagList = tagText.split(",")
            projTags = [tag.strip() for tag in tagList]
        projData["tags"] = projTags
        projData["citation"] = self.pteProjectCitation.toPlainText()
        projData["source"] = self.pteProjectSource.toPlainText()
        projData["default_time_periods"] = self.projectCodesTextToList(self.pteDateAndTime.toPlainText())
        projData["default_time_of_year"] = self.projectCodesTextToList(self.pteTimeOfYear.toPlainText())
        projData["default_codes"] = self.projectCodesTextToList(self.pteContentCodes.toPlainText())
        #
        # check if default codes have been removed
        oldList = self.projDict["projects"][str(self.projId)]["default_codes"]
        newList = projData["default_codes"]
        missingCodes = []
        nx_idx = 0
        pt_idx = 0
        ln_idx = 0
        pl_idx = 0
        for oldCode in oldList:
            matchFound = False
            for newCode in newList:
                if oldCode[0] == newCode[0]:
                    matchFound = True
                    break
            if matchFound == False:
                missingCodes.append[oldCode]
        if len(missingCodes) == 0:
            idx = self.cbDefaultCode.currentIndex()
            projData["ns_code"] = oldList[idx][0]
            idx = self.cbPointCode.currentIndex()
            projData["pt_code"] = oldList[idx][0]
            idx = self.cbLineCode.currentIndex()
            projData["ln_code"] = oldList[idx][0]
            idx = self.cbPolygonCode.currentIndex()
            projData["pl_code"] = oldList[idx][0]
            self.projDict["projects"][str(self.projId)] = projData
            self.projectFileSave()
            # update list in case additional codes were added
            self.projectUpdateCodeLists(projData)
            self.projectDetailsDisableEdit()
        else:
            pass
            # generate warning
        # check if the missing codes are used as defaults
        #for oldCode in missingCodes:
        #    messageText = "The codes following content codes have been removed: " % missingCodes[:-1]
        #    response = QtGui.QMessageBox.warning(self, 'Warning',
        #        messageText, QtGui.QMessageBox.Ok)
        #    
        # check if a code used in an interview has been deleted
        
    #
    # project details cancel
    #
    def projectDetailsCancel(self):

        self.projectFileRead()
        self.projectLoad()
        self.projectDetailsDisableEdit()
        
    #
    # project set map scale up
    #
    def projectSetMapScaleDown(self):
        
        if self.cbMaxScale.currentIndex() > self.cbMinScale.currentIndex():
            self.cbMinScale.setCurrentIndex(self.cbMaxScale.currentIndex())
        self.projectMapSettingsEnableEdit()

    #
    # project set map scale down
    #
    def projectSetMapScaleUp(self):
        
        if self.cbMaxScale.currentIndex() > self.cbMinScale.currentIndex():
            self.cbMaxScale.setCurrentIndex(self.cbMinScale.currentIndex())
        self.projectMapSettingsEnableEdit()


    ########################################################
    #           LMB Project QGIS Project Settings          #
    ########################################################
    #
    # read QGIS proejct
    #
    def qgisProjectRead(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        projectName = QtGui.QFileDialog.getOpenFileName(self, 'Select QGIS project', self.dirName, '*.qgs')
        if os.path.exists(projectName):
            self.qgsProjectChanged = True
            self.leQgsProject.setText(projectName)
            self.qgsProject = projectName
            self.qgisProjectLoad(projectName)
#        else:
#            self.leQgsProject.setText('')
#            self.qgsProject = ''
#            self.qgisProjectClear()
        self.projectMapSettingsEnableEdit()

    #
    # load QgsProject
    #
    def qgisProjectLoad( self, projectName ):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        s = QtCore.QSettings()
        if projectName == '':
            self.iface.newProject()
        elif QgsProject.instance().fileName() <> projectName:
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
            try:
                rv = self.projDict["projects"][str(self.projId)]["lmb_map_settings"]["base_groups"]
            except:
                rv = []
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
                    item.setText(unicode(rec))
                    item.setToolTip('Base Map Group')
                    self.tblBaseGroups.setItem(x,0,item)
                    x = x + 1
                self.baseGroups = validGroups
            # set boundary layer
            try:
                rv = self.projDict["projects"][str(self.projId)]["lmb_map_settings"]["boundary_layer"]
            except:
                rv = ''
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
            try:
                rv = self.projDict["projects"][str(self.projId)]["lmb_map_settings"]["enable_reference"]
            except:
                rv = "No"
            if rv == "Yes":
                self.cbEnableReference.setCurrentIndex(1)
                self.cbReferenceLayer.setEnabled(True)
                self.enableReference = True
                try:
                    rv = self.projDict["projects"][str(self.projId)]["lmb_map_settings"]["reference_layer"]
                except:
                    rv = ''
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
    # set no QGIS project
    #
    def qgisProjectClear(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.iface.newProject()
        self.leQgsProject.setText('')
        self.qgsProject = ''
        self.tblBaseGroups.clear()
        self.tblBaseGroups.setRowCount(0)
        self.tblBaseGroups.setColumnCount(0)
        self.baseGroups = []
        self.cbProjectGroups.clear()
        self.cbBoundaryLayer.clear()
        self.boundaryLayer = ''
        self.cbEnableReference.setCurrentIndex(0)
        self.enableReference = False
        self.cbReferenceLayer.clear()
        self.cbReferenceLayer.setDisabled(True)
        self.referenceLayer = ''

    #
    # udpate boundary
    #
    def qgisBoundaryLayerUpdate(self):

        if self.projectState <> 'load':
            if self.debug:
                QgsMessageLog.logMessage(self.myself())
            #
            if self.cbBoundaryLayer.count() > 0:
                idx = self.cbBoundaryLayer.currentIndex()
                if idx < 0:
                    idx = 0
                self.boundaryLayer = self.projectLayers[idx]
                self.projectMapSettingsEnableEdit()

    #
    # enable reference layer
    #
    def qgisReferenceLayerSetStatus(self):

        if self.projectState <> 'load':
            if self.debug:
                QgsMessageLog.logMessage(self.myself())
            #
            if self.cbEnableReference.currentIndex() == 0:
                self.cbReferenceLayer.setDisabled(True)
                self.enableReference = False
            else:
                self.cbReferenceLayer.setEnabled(True)
                self.enableReference = True
                self.cbReferenceLayer.setCurrentIndex(0)
            self.projectMapSettingsEnableEdit()

    #
    # update reference
    #
    def qgisReferenceLayerUpdate(self):

        if self.projectState <> 'load':
            if self.debug:
                QgsMessageLog.logMessage(self.myself())
            #
            if self.enableReference == True and self.cbReferenceLayer.count() > 0:
                self.projectMapSettingsEnableEdit()

    #
    # enable base group removal
    #
    def qgisBaseGroupEnableRemoval(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        if len(self.tblBaseGroups.selectedItems()) > 0:
            self.pbRemoveBaseGroup.setEnabled(True)
        else:
            self.pbRemoveBaseGroup.setDisabled(True)

    #
    # add base groups
    #
    def qgisBaseGroupAdd(self):

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
            item.setText(unicode(grp))
            item.setToolTip('Base Map Group')
            self.tblBaseGroups.setItem(tblIdx,0,item)
            # add to list
            self.baseGroups.append(grp)
        self.projectMapSettingsEnableEdit()
        
    #
    # remove base groups
    #
    def qgisBaseGroupRemove(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())

        txt = self.tblBaseGroups.currentItem().text()
        self.tblBaseGroups.removeRow(self.tblBaseGroups.currentRow())
        self.baseGroups.remove(txt)
        self.projectMapSettingsEnableEdit()

    #
    ########################################################
    #      Map Biographer Manage Participants              #
    ########################################################
    #
    # read participant list
    #
    def participantListRead(self):
            
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # get data and set row and column dimensions
        partData = self.projDict["participants"]
        self.tblParticipants.clear()
        self.tblParticipants.setColumnCount(4)
        self.tblParticipants.setRowCount(len(partData))
        # set header
        header = []
        header.append('Id')
        header.append('Code')
        header.append('First Name')
        header.append('Last Name')
        self.tblParticipants.setHorizontalHeaderLabels(header)
        # add content
        x = 0
        self.partIdMax = 0
        for key,value in partData.iteritems():
            self.participantSet(x,value)
            x = x + 1
            if int(key) > self.partIdMax:
                self.partIdMax = int(key)
            self.partCodeList.append(value["code"])
        self.tblParticipants.setColumnWidth(0,25)
        self.tblParticipants.setColumnWidth(1,80)
        self.tblParticipants.setColumnWidth(2,80)
        self.tblParticipants.setColumnWidth(3,80)

    #
    # add / update participant record to participant table widget
    #
    def participantSet(self,x,prDict):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # id
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(unicode(prDict["id"]))
        item.setToolTip('Participant Id')
        self.tblParticipants.setItem(x,0,item)
        # user name
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(unicode(prDict["code"]))
        item.setToolTip('Participant Code')
        self.tblParticipants.setItem(x,1,item)
        # first name
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(unicode(prDict["first_name"]))
        item.setToolTip('First Name')
        self.tblParticipants.setItem(x,2,item)
        # last name
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(unicode(prDict["last_name"]))
        item.setToolTip('Last Name')
        self.tblParticipants.setItem(x,3,item)
        return(item)

    #
    # select and read participant
    #
    def participantSelectRead(self):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.tbxParticipants.setEnabled(True)
        row = self.tblParticipants.currentRow()
        self.partId = int(self.tblParticipants.item(row,0).text())
        self.participantRead()
        self.addressListRead()
        self.telecomListRead()
        
    #
    # read participant
    #
    def participantRead(self):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        partData = self.projDict["participants"][str(self.partId)]
        self.leParticipantCode.setText(partData["code"])
        self.leFirstName.setText(partData["first_name"])
        self.leLastName.setText(partData["last_name"])
        self.leEmail.setText(partData["email_address"])
        self.leCommunity.setText(partData["subcommunity"])
        self.leFamily.setText(partData["family"])
        self.leMaidenName.setText(partData["maiden_name"])
        if partData["gender"] == 'M':
            self.cbGender.setCurrentIndex(1)
        elif partData["gender"] == 'F':
            self.cbGender.setCurrentIndex(2)
        elif partData["gender"] == 'R':
            self.cbGender.setCurrentIndex(3)
        elif partData["gender"] == 'O':
            self.cbGender.setCurrentIndex(4)
        else:
            self.cbGender.setCurrentIndex(0)
        if partData["marital_status"] == 'S':
            self.cbMaritalStatus.setCurrentIndex(1)
        elif partData["marital_status"] == 'M':
            self.cbMaritalStatus.setCurrentIndex(2)
        elif partData["marital_status"] == 'D':
            self.cbMaritalStatus.setCurrentIndex(3)
        elif partData["marital_status"] == 'R':
            self.cbMaritalStatus.setCurrentIndex(4)
        elif partData["marital_status"] == 'O':
            self.cbMaritalStatus.setCurrentIndex(5)
        else:
            self.cbMaritalStatus.setCurrentIndex(0)
        self.leBirthDate.setText(partData["birth_date"])
        self.leParticipantTags.setText(",".join(partData["tags"]))
        self.pteParticipantNote.setPlainText(partData["note"])

    #
    # check if participant is selected or unselected
    #
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
            self.participantSelectRead()

    #
    # set edit of participant
    #
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
    #
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
    #
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
        self.tblAddresses.clear()
        self.tblTelecoms.clear()
        
    #
    # new participant
    #
    def participantNew(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.pgAddresses.setDisabled(True)
        self.pgTelecoms.setDisabled(True)
        self.partIdMax += 1
        self.partId = self.partIdMax
        temp = {
            "id": self.partId,
            "code": "newcode%d" % self.partId,
            "first_name": "",
            "last_name": "",
            "email_address": "",
            "family": "",
            "community": "",
            "subcommunity": "",
            "maiden_name": "",
            "gender": "U",
            "marital_status": "U",
            "birth_date": "",
            "tags": [],
            "note": "",
            "addresses": {},
            "telecoms": {}
        }
        self.partCodeList.append("newcode%d" % self.partId)
        self.projDict["participants"][str(self.partId)] = temp
        self.projectFileSave()
        rCnt = len(self.projDict["participants"])
        self.tblParticipants.setRowCount(rCnt)
        item = self.participantSet(rCnt-1,temp)
        self.tblParticipants.setCurrentCell(item.row(),0)
        self.participantRead()
        self.leParticipantCode.setFocus()
        self.participantEnableEdit()

    #
    # update participant
    #
    def participantSave(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        # use temp variable to keep lines shorter
        partCode = self.leParticipantCode.text().strip()
        oldCode = self.projDict["participants"][str(self.partId)]["code"]
        if partCode <> oldCode and partCode in self.partCodeList:
            messageText = "The Participant Code %s is not unique. " % partCode
            messageText += "Modify the code and try again to save."
            response = QtGui.QMessageBox.warning(self, 'Warning',
               messageText, QtGui.QMessageBox.Ok)
        else:
            self.partCodeList.append(partCode)
            self.partCodeList = list(set(self.partCodeList))
            temp = {}
            temp["id"] = self.partId
            # if the participant code changes remove from list to allow reuse if needed
            if oldCode <> partCode:
                self.partCodeList.remove(oldCode)
            temp["code"] = partCode
            temp["first_name"] = self.leFirstName.text()
            temp["last_name"] = self.leLastName.text()
            temp["email_address"] = self.leEmail.text()
            temp["subcommunity"] = self.leCommunity.text()
            temp["family"] = self.leFamily.text()
            temp["maiden_name"] = self.leMaidenName.text()
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
            temp["gender"] = gender
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
            temp["marital_status"] = maritalStatus
            temp["birth_date"] = self.leBirthDate.text()
            tagText = self.leParticipantTags.text()
            if tagText == "":
                partTags = []
            else:
                tagList = tagText.split(",")
                partTags = [tag.strip() for tag in tagList]
            temp["tags"] = partTags
            temp["note"] = self.pteParticipantNote.toPlainText()
            temp["addresses"] = self.projDict["participants"][str(self.partId)]["addresses"]
            temp["telecoms"] = self.projDict["participants"][str(self.partId)]["telecoms"]
            self.projDict["participants"][str(self.partId)]= temp
            self.projectFileSave()
            row = self.tblParticipants.currentRow()
            self.participantSet(row,temp)
            self.participantClearValues()
            self.participantDisableEdit()
            self.tblParticipants.clearSelection()
        
    #
    # cancel participant edits
    #
    def participantCancelEdit(self):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.participantClearValues()
        self.participantDisableEdit()
        self.tblParticipants.clearSelection()

    #
    # delete participant
    #
    def participantDelete(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        # check if participant in a document
        isParticipant = False
        for key,value in self.projDict["projects"].iteritems():
            for dKey, dValue in value["documents"].iteritems():
                for pKey, pValue in dValue["participants"].iteritems():
                    if pValue["participant_id"] == self.partId:
                        isParticipant = True
        if isParticipant == True:
            QtGui.QMessageBox.warning(self, 'Warning',
               "Can not delete this person. Currently referenced in an interview.", QtGui.QMessageBox.Ok)
        else:
            del self.projDict["participants"][str(self.partId)]
            self.projectFileSave()
            self.participantDisableEdit()
            row = self.tblParticipants.currentRow()
            self.tblParticipants.removeRow(row)
            self.tblParticipants.clearSelection()
        
    #
    ########################################################
    #     Map Biographer Manage Participant Addresses      #
    ########################################################
    #
    # read participant address list
    #
    def addressListRead(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        addrData = self.projDict["participants"][str(self.partId)]["addresses"]
        # clear old data and setup row and column counts
        self.tblAddresses.clear()
        self.tblAddresses.setColumnCount(3)
        self.tblAddresses.setRowCount(len(addrData))
        # set header
        header = []
        header.append('Id')
        header.append('Type')
        header.append('Address')
        self.tblAddresses.setHorizontalHeaderLabels(header)
        # add content
        x = 0
        self.addrIdMax = 0
        for key, value in addrData.iteritems():
            self.addressSet(x,value)
            x = x + 1
            if int(key) > self.addrIdMax:
                self.addrIdMax = int(key)
        self.tblAddresses.setColumnWidth(0,25)
        self.tblAddresses.setColumnWidth(1,75)
        self.tblAddresses.setColumnWidth(2,300)
        self.addressDisableEdit()

    #
    # add / update address record to participant address table widget
    #
    def addressSet(self,x,adDict):

        # id
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(unicode(adDict["id"]))
        item.setToolTip('Map Biographer Participant Id')
        self.tblAddresses.setItem(x,0,item)
        # address type
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(unicode(adDict["type"]))
        item.setToolTip('Type')
        self.tblAddresses.setItem(x,1,item)
        # line one
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(unicode(adDict["address"][:25].replace('\n',' '))+'...')
        item.setToolTip('Address')
        self.tblAddresses.setItem(x,2,item)
        return(item)

    #
    # select and read address
    #
    def addressSelectRead(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        row = int(self.tblAddresses.currentRow())
        self.addrId = int(self.tblAddresses.item(row,0).text())
        self.addressRead()
        
    #
    # read address
    #
    def addressRead(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        addrData = self.projDict["participants"][str(self.partId)]["addresses"][str(self.addrId)]
        if addrData["type"] == 'H':
            self.cbAddType.setCurrentIndex(0)
        elif addrData["type"] == 'W':
            self.cbAddType.setCurrentIndex(1)
        elif addrData["type"] == 'P':
            self.cbAddType.setCurrentIndex(2)
        else:
            self.cbAddType.setCurrentIndex(3)
        self.pteAddress.setPlainText(addrData["address"])

    #
    # check if address is selected or unselected
    #
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
            self.addressSelectRead()

    #
    # enable edit of address
    #
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
        self.pteAddress.setEnabled(True)

    #
    # disable edit of address
    #
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
        self.pteAddress.setDisabled(True)

    #
    # clear address values
    #
    def addressClearValues(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.cbAddType.setCurrentIndex(0)
        self.pteAddress.setPlainText('')
        
    #
    # new address
    #
    def addressNew(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.addressClearValues()
        self.addressEnableEdit()
        self.cbAddType.setFocus()
        self.addressEnableEdit()
        self.pbAddDelete.setDisabled(True)
        
    #
    # update address
    #
    def addressSave(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        # read values from form
        if self.cbAddType.currentIndex() == 0:
            addrType = 'H'
        elif self.cbAddType.currentIndex() == 1:
            addrType = 'W'
        elif self.cbAddType.currentIndex() == 2:
            addrType = 'P'
        else:
            addrType = 'O'
        # if inserting new increment add id and add row
        if self.pbAddDelete.isEnabled() == False:
            self.addrIdMax += 1
            self.addrId = self.addrIdMax
            rCnt = len(self.projDict["participants"][str(self.partId)]["addresses"])+1            
            self.tblAddresses.setRowCount(rCnt)
            row = rCnt -1
        else:
            row = self.tblAddresses.currentRow()
        temp = {
            "id": self.addrId,
            "type": addrType,
            "address": self.pteAddress.document().toPlainText()
        }
        self.projDict["participants"][str(self.partId)]["addresses"][str(self.addrId)] = temp
        self.projectFileSave()
        self.addressSet(row,temp)
        self.addressDisableEdit()
        self.addressClearValues()
        self.tblAddresses.clearSelection()

    #
    # cancel address edits
    #
    def addressCancelEdit(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.addressClearValues()
        self.addressDisableEdit()
        self.tblAddresses.clearSelection()

    #
    # delete address
    #
    def addressDelete(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        del self.projDict["participants"][str(self.partId)]["addresses"][str(self.addrId)]
        self.projectFileSave()
        self.addressClearValues()
        self.addressDisableEdit()
        # remove row
        row = self.tblAddresses.currentRow()
        self.tblAddresses.removeRow(row)
        self.tblAddresses.clearSelection()

    #
    ########################################################
    #    Map Biographer Manage Participant Telecoms        #
    ########################################################
    #
    # read participant telecom list
    #
    def telecomListRead(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        telData = self.projDict["participants"][str(self.partId)]["telecoms"]
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
        self.teleIdMax = 0
        for key, value in telData.iteritems():
            self.telecomSet(x,value)
            x = x + 1
            if int(key) > self.teleIdMax:
                self.teleIdMax = int(key)
        self.tblTelecoms.setColumnWidth(0,25)
        self.tblTelecoms.setColumnWidth(1,75)
        self.tblTelecoms.setColumnWidth(2,300)
        self.telecomDisableEdit()

    #
    # add / update participant telecom record to telecom table widget
    #
    def telecomSet(self,x,telDict):

        # id
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(unicode(telDict["id"]))
        item.setToolTip('Map Biographer Participant Id')
        self.tblTelecoms.setItem(x,0,item)
        # user name
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(unicode(telDict["type"]))
        item.setToolTip('Type')
        self.tblTelecoms.setItem(x,1,item)
        # first name
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(unicode(telDict["telecom"]))
        item.setToolTip('Telecom')
        self.tblTelecoms.setItem(x,2,item)
        return(item)

    #
    # select and read address
    #
    def telecomSelectRead(self):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        row = int(self.tblTelecoms.currentRow())
        self.teleId = int(self.tblTelecoms.item(row,0).text())
        self.telecomRead()

    #
    # read telecom
    #
    def telecomRead(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        QgsMessageLog.logMessage(str(self.teleId))
        telData = self.projDict["participants"][str(self.partId)]["telecoms"][str(self.teleId)]
        if telData["type"] == 'H':
            self.cbTelType.setCurrentIndex(0)
        elif telData["type"] == 'W':
            self.cbTelType.setCurrentIndex(1)
        elif telData["type"] == 'M':
            self.cbTelType.setCurrentIndex(2)
        elif telData["type"] == 'P':
            self.cbTelType.setCurrentIndex(3)
        elif telData["type"] == 'F':
            self.cbTelType.setCurrentIndex(4)
        else:
            self.cbTelType.setCurrentIndex(3)
        self.leTelNumber.setText(telData["telecom"])

    #
    # check if telecom is selected or unselected
    #
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
            self.telecomSelectRead()

    #
    # set edit of telecom
    #
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
    #
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
    #
    def telecomClearValues(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.cbTelType.setCurrentIndex(0)
        self.leTelNumber.setText('')
        
    #
    # new telecom
    #
    def telecomNew(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.telecomClearValues()
        self.telecomEnableEdit()
        self.cbTelType.setFocus()
        self.telecomEnableEdit()
        self.pbTelDelete.setDisabled(True)
                
    #
    # update telecom
    #
    def telecomSave(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
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
        # if inserting new increment add id and add row
        if self.pbTelDelete.isEnabled() == False:
            self.teleIdMax += 1
            self.teleId = self.teleIdMax
            rCnt = len(self.projDict["participants"][str(self.partId)]["telecoms"])+ 1
            self.tblTelecoms.setRowCount(rCnt)
            row = rCnt-1
        else:
            row = self.tblTelecoms.currentRow()
        temp = {
            "id": self.teleId,
            "type": telType,
            "telecom": self.leTelNumber.text()
        }
        self.projDict["participants"][str(self.partId)]["telecoms"][str(self.teleId)] = temp
        self.projectFileSave()
        self.telecomSet(row,temp)
        self.telecomDisableEdit()
        self.telecomClearValues()
        self.tblTelecoms.clearSelection()
        
    #
    # cancel telecom edits
    #
    def telecomCancelEdits(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.telecomClearValues()
        self.telecomDisableEdit()
        self.tblTelecoms.clearSelection()

    #
    # delete telecom
    #
    def telecomDelete(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        del self.projDict["participants"][str(self.partId)]["telecoms"][str(self.teleId)]
        self.projectFileSave()
        self.telecomClearValues()
        self.telecomDisableEdit()
        # remove row
        row = self.tblTelecoms.currentRow()
        self.tblTelecoms.removeRow(row)
        self.tblTelecoms.clearSelection()

    #
    ########################################################
    #    Map Biographer Manage Interviews                  #
    ########################################################
    #
    # read interview list
    #
    def interviewListRead(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        intvData = self.projDict["projects"][str(self.projId)]["documents"]
        self.intvCodeList = []
        # clear old data and setup row and column counts
        self.tblInterviews.clear()
        self.tblInterviews.setColumnCount(4)
        self.tblInterviews.setRowCount(len(intvData))
        # set header
        header = []
        header.append('Id')
        header.append('Code')
        header.append('Title')
        header.append('Status')
        self.tblInterviews.setHorizontalHeaderLabels(header)
        # add content
        x = 0
        self.intvIdMax = 0
        for key,value in intvData.iteritems():
            self.intvCodeList.append(value["code"])
            self.interviewSet(x,value)
            x = x + 1
            if int(key) > self.intvIdMax:
                self.intvIdMax = int(key)
        self.interviewDisableEdit()
        self.tblInterviews.setColumnWidth(0,25)
        self.tblInterviews.setColumnWidth(1,75)
        self.tblInterviews.setColumnWidth(2,120)
        self.tblInterviews.setColumnWidth(3,50)
        self.tblInterviews.sortItems(0,QtCore.Qt.AscendingOrder)

    #
    # add / update interview record to interview table widget
    #
    def interviewSet(self,x,itDict):

        # id
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setData(0,int(itDict["id"]))
        item.setToolTip('Map Biographer Interview Id')
        self.tblInterviews.setItem(x,0,item)
        # code
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(unicode(itDict["code"]))
        item.setToolTip('Interview Code')
        self.tblInterviews.setItem(x,1,item)
        # description
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(unicode(itDict["title"]))
        item.setToolTip('Description')
        self.tblInterviews.setItem(x,2,item)
        # status
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(unicode(itDict["status"]))
        item.setToolTip('Status')
        self.tblInterviews.setItem(x,3,item)
        return(item)

    #
    # select and read interview
    #
    def interviewSelectRead(self):
        
        self.tbxInterview.setEnabled(True)
        row = int(self.tblInterviews.currentRow())
        self.intvId = int(self.tblInterviews.item(row,0).text())
        self.interviewRead()
        
    #
    # read interview
    #
    def interviewRead(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        intvData = self.projDict["projects"][str(self.projId)]["documents"][str(self.intvId)]
        self.leInterviewCode.setText(intvData["code"])
        self.leInterviewTitle.setText(intvData["title"])
        self.pteInterviewDescription.setPlainText(intvData["description"])
        self.leInterviewLocation.setText(intvData["location"])
        self.pteInterviewNote.setPlainText(intvData["note"])
        self.leInterviewTags.setText(",".join(intvData["tags"]))
        self.interviewStatus = intvData["status"]
        if self.interviewStatus == 'U':
            self.cbInterviewStatus.setCurrentIndex(3)
        elif self.interviewStatus == 'T':
            self.cbInterviewStatus.setCurrentIndex(2)
        elif self.interviewStatus == 'C':
            self.cbInterviewStatus.setCurrentIndex(1)
        else:
            self.cbInterviewStatus.setCurrentIndex(0)
        if intvData["default_data_security"] == 'PU':
            self.cbInterviewSecurity.setCurrentIndex(0)
        elif intvData["default_data_security"] == 'CO':
            self.cbInterviewSecurity.setCurrentIndex(1)
        else:
            self.cbInterviewSecurity.setCurrentIndex(2)
        self.leInterviewCreator.setText(intvData["creator"])
        self.leInterviewPublisher.setText(intvData["publisher"])
        self.leSubject.setText(intvData["subject"])
        self.leLanguage.setText(intvData["language"])
        self.pteSource.setPlainText(intvData["source"])
        self.pteCitation.setPlainText(intvData["citation"])
        self.pteRightsStatement.setPlainText(intvData["rights_statement"])
        self.leRightsHolder.setText(intvData["rights_holder"])
        self.dteStart.setDateTime(datetime.datetime.strptime(intvData["start_datetime"],"%Y-%m-%d %H:%M"))
        self.dteEnd.setDateTime(datetime.datetime.strptime(intvData["end_datetime"],"%Y-%m-%d %H:%M"))
        self.interviewParticipantListRefresh()
        self.interviewParticipantListRead()

    #
    # check if interview is selected or unselected
    #
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
            self.interviewSelectRead()

    #
    # set edit of interview
    #
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
    #
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
    #
    def interviewClearValues(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.leInterviewCode.setText("")
        self.leInterviewTitle.setText("")
        self.pteInterviewDescription.setPlainText("")
        self.leInterviewLocation.setText("")
        self.pteInterviewNote.setPlainText("")
        self.leInterviewTags.setText("")
        self.cbInterviewStatus.setCurrentIndex(0)
        self.cbInterviewSecurity.setCurrentIndex(0)
        self.leInterviewCreator.setText("")
        self.leInterviewPublisher.setText("")
        self.leSubject.setText("")
        self.leLanguage.setText("")
        self.pteSource.setPlainText("")
        self.pteCitation.setPlainText("")
        self.pteRightsStatement.setPlainText("")
        self.leRightsHolder.setText("")
        self.dteStart.setDateTime(datetime.datetime.strptime("2000-01-01 12:00","%Y-%m-%d %H:%M"))
        self.dteEnd.setDateTime(datetime.datetime.strptime("2000-01-01 12:00","%Y-%m-%d %H:%M"))
        
    #
    # new interview
    #
    def interviewNew(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        #self.tblInterviews.sortItems(0,QtCore.Qt.AscendingOrder)
        self.interviewClearValues()
        self.interviewEnableEdit()
        self.intvIdMax += 1
        self.intvId = self.intvIdMax
        nCode = "newcode%s" % self.intvId
        self.intvCodeList.append(nCode)
        temp = {
            "id": self.intvId,
            "code": nCode,
            "title": "",
            "description": "",
            "location": "",
            "note": "",
            "tags": [],
            "default_data_security": "PR",
            "status": "N",
            "creator": "",
            "publisher": "",
            "subject": "",
            "language": "",
            "source": "",
            "citation": "",
            "rights_statement": "",
            "rights_holder": "",
            "start_datetime": "2000-01-01 13:00",
            "end_datetime": "2000-01-01 14:00",
            "participants": {}
        }
        self.projDict["projects"][str(self.projId)]["documents"][str(self.intvId)] = temp
        rCnt = len(self.projDict["projects"][str(self.projId)]["documents"])
        self.tblInterviews.setRowCount(rCnt)
        item = self.interviewSet(rCnt-1,temp)
        self.tblInterviews.setCurrentCell(item.row(),0)
        self.interviewRead()
        self.leInterviewCode.setFocus()
        self.interviewEnableEdit()
        self.projectFileSave()
        
    #
    # update interview
    #
    def interviewSave(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        # security
        if self.cbInterviewSecurity.currentIndex() == 0:
            security = 'PU'
        elif self.cbInterviewSecurity.currentIndex() == 1:
            security = 'CO'
        else:
            security = 'PR'
        # data status
        if self.cbInterviewStatus.currentIndex() == 0:
            self.interviewStatus = 'N'
        elif self.cbInterviewStatus.currentIndex() == 1:
            self.interviewStatus = 'C'
        elif self.cbInterviewStatus.currentIndex() == 2:
            self.interviewStatus = 'T'
        elif self.cbInterviewStatus.currentIndex() == 3:
            self.interviewStatus = 'U'
        temp = self.projDict["projects"][str(self.projId)]["documents"][str(self.intvId)]
        temp["title"] = self.leInterviewTitle.text()
        temp["description"] = self.pteInterviewDescription.document().toPlainText()
        temp["location"] = self.leInterviewLocation.text()
        temp["note"] = self.pteInterviewNote.document().toPlainText()
        tagText = self.leInterviewTags.text()
        if tagText == "":
            intvTags = []
        else:
            tagList = tagText.split(",")
            intvTags = [tag.strip() for tag in tagList]
        temp["tags"] = intvTags
        temp["default_data_security"] = security
        temp["status"] = self.interviewStatus
        temp["creator"] = self.leInterviewCreator.text()
        temp["publisher"] = self.leInterviewPublisher.text()
        temp["subject"] = self.leSubject.text()
        temp["language"] = self.leLanguage.text()
        temp["source"] = self.pteSource.toPlainText()
        temp["citation"] = self.pteCitation.toPlainText()
        temp["rights_statement"] = self.pteRightsStatement.toPlainText()
        temp["rights_holder"] = self.leRightsHolder.text()
        temp["start_datetime"] = self.dteStart.dateTime().toPyDateTime().isoformat()[:16].replace('T',' ')
        temp["end_datetime"] = self.dteEnd.dateTime().toPyDateTime().isoformat()[:16].replace('T',' ')
        self.projDict["projects"][str(self.projId)]["documents"][str(self.intvId)] = temp
        # check to see if code is changed and is unique
        nCode = self.leInterviewCode.text().strip()
        saveOk = False
        if temp["code"] <> nCode:
            if nCode in self.intvCodeList:
                messageText = 'This interview code %s is not unique. A unique code is required.' % nCode
                response = QtGui.QMessageBox.warning(self, 'Warning',
                   messageText, QtGui.QMessageBox.Ok )
            else:
                del self.intvCodeList[self.intvCodeList.index(temp["code"])]
                temp["code"] = nCode
                self.intvCodeList.append(nCode)
                saveOk = True
        else:
            saveOk = True
        if saveOk:
            self.projectFileSave()
            row = self.tblInterviews.currentRow()
            self.interviewSet(row,temp)
            self.interviewDisableEdit()
            self.interviewClearValues()
            self.tblInterviews.clearSelection()
        
    #
    # cancel interview edits
    #
    def interviewCancelEdits(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.interviewClearValues()
        self.interviewDisableEdit()
        self.tblInterviews.clearSelection()

    #
    # delete interview
    #
    def interviewDelete(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        # need to add code here to check for documents with content and confirm or prevent
        # deletion, including deletion of media files
        intvFileName = "lmb-p%d-i%d-data.json" % (self.projId,self.intvId)
        if os.path.exists(os.path.join(self.dirName, intvFileName)):
            hasContent = True
        else:
            hasContent = False
        if hasContent == True:
            messageText = "Can not delete interview %s " % self.projDict["projects"][str(self.projId)]["documents"][str(self.intvId)]["code"]
            messageText += "because it contains content.If you wish to delete it you must delete "
            messageText += "the interview file '%s' " % intvFileName
            messageText += "and any associated multimedia files from disk first."
            QtGui.QMessageBox.warning(self, 'Warning',
               messageText, QtGui.QMessageBox.Ok)
        else:
            docCode = self.projDict["projects"][str(self.projId)]["documents"][str(self.intvId)]["code"]
            del self.projDict["projects"][str(self.projId)]["documents"][str(self.intvId)]
            del self.intvCodeList[self.intvCodeList.index(docCode)]
            self.projectFileSave()
            self.interviewClearValues()
            self.interviewDisableEdit()
            # remove row
            row = self.tblInterviews.currentRow()
            self.tblInterviews.removeRow(row)
            self.tblInterviews.clearSelection()

    #
    ########################################################
    #            manage interview participants             #
    ########################################################
    #
    # populate participant list combobox
    #
    def interviewParticipantListRefresh(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.participantList = []
        self.cbIntPartName.clear()
        partData = self.projDict["participants"]
        for key, value in partData.iteritems():
            self.participantList.append([value["last_name"],value["first_name"],value["subcommunity"],value["family"],value["id"]])
        self.participantList.sort()
        for item in self.participantList:
            self.cbIntPartName.addItem("%s, %s" % (item[0],item[1]))

    #
    # read interview participant list
    #
    def interviewParticipantListRead(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        partData = self.projDict["projects"][str(self.projId)]["documents"][str(self.intvId)]["participants"]
        # clear old data and setup row and column counts
        self.tblInterviewParticipants.clear()
        self.tblInterviewParticipants.setColumnCount(3)
        self.tblInterviewParticipants.setRowCount(len(partData))
        # set header
        header = []
        header.append('Id')
        header.append('Participant Id')
        header.append('Name')
        self.tblInterviewParticipants.setHorizontalHeaderLabels(header)
        # add content
        x = 0
        self.intvPartIdMax = 0
        for key,value in partData.iteritems():
            self.interviewParticipantSet(x,value)
            x = x + 1
            if int(key) > self.intvPartIdMax:
                self.intvPartIdMax = int(key)
        self.tblInterviewParticipants.setColumnWidth(0,25)
        self.tblInterviewParticipants.setColumnWidth(1,125)
        self.tblInterviewParticipants.setColumnWidth(2,200)
        self.interviewParticipantDisableEdit()

    #
    # add / update interview participant record to participant table widget
    #
    def interviewParticipantSet(self,x,ipDict):

        # id
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(unicode(ipDict["id"]))
        item.setToolTip('Map Biographer Interview Id')
        self.tblInterviewParticipants.setItem(x,0,item)
        # participant_id
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(unicode(ipDict["participant_id"]))
        item.setToolTip('Map Biographer Participant Id')
        self.tblInterviewParticipants.setItem(x,1,item)
        # last and first name
        partDict = self.projDict["participants"][str(ipDict["participant_id"])]
        partName = "%s, %s" % (partDict["last_name"],partDict["first_name"])
        item = QtGui.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setText(partName)
        item.setToolTip('Name')
        self.tblInterviewParticipants.setItem(x,2,item)
        return(item)

    #
    # select and read participant
    #
    def interviewParticipantSelectRead(self):
        
        self.interviewParticipantClearValues()
        row = self.tblInterviewParticipants.currentRow()
        self.intvPartId = int(self.tblInterviewParticipants.item(row,0).text())
        self.interviewParticipantRead()
        
    #
    # read participant
    #
    def interviewParticipantRead(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        partRec = self.projDict["projects"][str(self.projId)]["documents"][str(self.intvId)]["participants"][str(self.intvPartId)]
        partId = partRec["participant_id"]
        for x in range(self.cbIntPartName.count()):
            if self.participantList[x][4] == partId:
                self.cbIntPartName.setCurrentIndex(x)
                break
        if self.cbIntPartName.count() > 0:
            self.leIntPartCommunity.setText(partRec["subcommunity"])
            self.leIntPartFamily.setText(partRec["family"])

    #
    # check if participant is selected or unselected
    #
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
            self.interviewParticipantSelectRead()

    #
    # set edit of participant
    #
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
    #
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
    #
    def interviewParticipantClearValues(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.cbIntPartName.setCurrentIndex(0)
        self.leIntPartCommunity.setText('')
        self.leIntPartFamily.setText('')
        
    #
    # update when participant selected
    #
    def interviewParticipantSelection(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        x = self.cbIntPartName.currentIndex()
        if len(self.participantList) > 0:
            self.leIntPartCommunity.setText(self.participantList[x][2])
            self.leIntPartFamily.setText(self.participantList[x][3])
    
    #
    # new participant
    #
    def interviewParticipantNew(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.interviewParticipantClearValues()
        self.interviewParticipantEnableEdit()
        if len(self.participantList) > 0:
            self.cbIntPartName.setCurrentIndex(0)
            self.leIntPartCommunity.setText(self.participantList[0][2])
            self.leIntPartFamily.setText(self.participantList[0][3])
        self.cbIntPartName.setFocus()
        self.interviewParticipantEnableEdit()
        self.pbIntPartDelete.setDisabled(True)

    #
    # update participant
    #
    def interviewParticipantSave(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        if self.pbIntPartDelete.isEnabled() == False:
            self.intvPartIdMax += 1
            self.intvPartId = self.intvPartIdMax
            rCnt = len(self.projDict["projects"][str(self.projId)]["documents"][str(self.intvId)]["participants"])+1
            self.tblInterviewParticipants.setRowCount(rCnt)
            row = rCnt-1
        else:
            row = self.tblInterviewParticipants.currentRow()
        x = self.cbIntPartName.currentIndex()
        temp = {
            "id": self.intvPartId,
            "participant_id": self.participantList[x][4],
            "subcommunity": self.leIntPartCommunity.text(),
            "family": self.leIntPartFamily.text()
        }
        self.projDict["projects"][str(self.projId)]["documents"][str(self.intvId)]["participants"][str(self.intvPartId)] = temp
        self.projectFileSave()
        self.interviewParticipantSet(row,temp)
        self.interviewParticipantDisableEdit()
        self.interviewParticipantClearValues()
        self.tblInterviewParticipants.clearSelection()

    #
    # cancel participant edits
    #
    def interviewParticipantCancel(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        self.interviewParticipantClearValues()
        self.interviewParticipantDisableEdit()
        self.tblInterviewParticipants.clearSelection()

    #
    # delete participant
    #
    def interviewParticipantDelete(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        del self.projDict["projects"][str(self.projId)]["documents"][str(self.intvId)]["participants"][str(self.intvPartId)]
        self.projectFileSave()
        self.interviewParticipantClearValues()
        self.interviewParticipantDisableEdit()
        # remove row
        row = self.tblInterviewParticipants.currentRow()
        self.tblInterviewParticipants.removeRow(row)
        self.tblInterviewParticipants.clearSelection()

    #
    ########################################################
    #     Map Biographer Data Transfer Functions           #
    ########################################################
    #
    # open transfer dialog and selection actions
    #
    def transferData(self):

        self.importDialog = mapBiographerPorter(self.iface, self.dirName, self.projDict, self.projId)
        # show the dialog
        self.importDialog.show()
        # Run the dialog event loop
        result = self.importDialog.exec_()
        # reset after done
        self.projectState = 'load'
        try:
            self.qgsSettingsRead()
            self.projectDetailsDisableEdit()
            self.projectMapSettingsDisableEdit()
            self.qgsSettingsDisableEdit()
            self.participantDisableEdit()
            self.interviewDisableEdit()
        except:
            self.projectDisable()
            self.projectDetailsDisableEdit()
            self.projectMapSettingsDisableEdit()
            self.qgsSettingsDisableEdit()
            self.participantDisableEdit()
            self.interviewDisableEdit()
        self.projectState = 'edit'
        # close after done
        #self.closeDialog()
