# -*- coding: utf-8 -*-
"""
/***************************************************************************
 mapBiographerPorter
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
import os, datetime, time, inspect, re, urllib, urllib2, json
from ui_mapbio_porter import Ui_mapbioPorter
from transfer_worker import transferContent


class mapBiographerPorter(QtGui.QDialog, Ui_mapbioPorter):

    #
    ########################################################
    #        Initialization and basic operation            #
    ########################################################
    #
    #
    # init method to define globals and make widget / method connections
    
    def __init__(self, iface, dirName, projDict, projId):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)
        self.iface = iface
        self.dirName = dirName
        self.projDict = projDict
        self.projId = projId
        self.actionIdx = 0
        self.downloadDict = {}
        self.resize(500, 250)
        self.frProgress.setVisible(False)

        # debug setup
        self.debug = False
        if self.debug:
            self.myself = lambda: inspect.stack()[1][3]
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
            self.lblURL.setVisible(True)
            self.leURL.setVisible(True)
            self.leURL.setText('https://aproposinfosystems.com')
        else:
            self.lblURL.setVisible(False)
            self.leURL.setVisible(False)
            self.leURL.setText('https://louistoolkit.ca')

        self.cbTransferAction.clear()
        self.cbTransferAction.addItems(['--None--','Create Heritage Archive', \
            'Create GeoJSON / Shapefile Archive','Get New Projects and Participants from Heritage',\
            'Update Current Project and Participants from Heritage','Upload Completed Interviews to Heritage'])
        # connect widgets to functions
        QtCore.QObject.connect(self.pbClose, QtCore.SIGNAL("clicked()"), self.transferClose)
        QtCore.QObject.connect(self.pbTransfer, QtCore.SIGNAL("clicked()"), self.transferRun)
        QtCore.QObject.connect(self.cbTransferAction, QtCore.SIGNAL("currentIndexChanged(int)"), self.actionSelect)
        QtCore.QObject.connect(self.pbImport, QtCore.SIGNAL("clicked()"), self.importPerform)
        QtCore.QObject.connect(self.pbUpload, QtCore.SIGNAL("clicked()"), self.uploadToHeritage)

        # configure interface
        self.interfaceEnable()

    #
    # adjust interface based on selected action
    #
    def actionSelect(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        self.actionIdx = self.cbTransferAction.currentIndex()
        if self.actionIdx == 0:
            # disable interface
            self.pbTransfer.setDisabled(True)
            self.frHeritageLogin.setVisible(False)
            self.frHeritageInfo.setVisible(False)
            self.frProgress.setVisible(False)
            self.resize(500, 250)
        elif self.actionIdx == 1:
            # create heritage archive
            self.pbTransfer.setEnabled(True)
            self.frHeritageLogin.setVisible(False)
            self.frHeritageInfo.setVisible(False)
            self.frProgress.setVisible(True)
            self.resize(500, 250)
        elif self.actionIdx == 2:
            # create GIS archive
            self.pbTransfer.setEnabled(True)
            self.frHeritageLogin.setVisible(False)
            self.frHeritageInfo.setVisible(False)
            self.frProgress.setVisible(True)
            self.resize(500, 250)
        elif self.actionIdx == 3:
            # download new projects
            self.pbTransfer.setEnabled(True)
            self.frHeritageLogin.setVisible(True)
            self.frHeritageInfo.setVisible(False)
            self.frProgress.setVisible(True)
            self.resize(500, 350)
        elif self.actionIdx == 4:
            # update existing project
            self.pbTransfer.setEnabled(True)
            self.frHeritageLogin.setVisible(True)
            self.frHeritageInfo.setVisible(False)
            self.frProgress.setVisible(True)
            self.resize(500, 350)
        elif self.actionIdx == 5:
            # upload completed interviews
            self.pbTransfer.setEnabled(True)
            self.frHeritageLogin.setVisible(True)
            self.frHeritageInfo.setVisible(False)
            self.frProgress.setVisible(True)
            self.resize(500, 350)

    #
    # disable interface for run
    #
    def interfaceDisable(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        self.cbTransferAction.setDisabled(True)
        self.pbTransfer.setDisabled(True)
        self.pbCancel.setEnabled(True)
        self.leUserName.setDisabled(True)
        self.lePassword.setDisabled(True)

    #
    # enable interface after run
    #
    def interfaceEnable(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        self.cbTransferAction.setEnabled(True)
        self.pbTransfer.setDisabled(True)
        self.pbCancel.setDisabled(True)
        self.leUserName.setEnabled(True)
        self.leUserName.setText('')
        self.lePassword.setEnabled(True)
        self.lePassword.setText('')
        self.cbTransferAction.setCurrentIndex(0)
        self.frHeritageLogin.setVisible(False)
        self.frHeritageInfo.setVisible(False)
        self.lblAllProgress.setText('Overall Progress:')
        self.lblStepProgress.setText('Current Step:')

    #
    # if close clicked notify and return blank dictionary
    #
    def transferClose(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        self.close()

    #
    ########################################################
    #                         Execution                    #
    ########################################################
    #
    #
    # execute tranfer action
    #
    def transferRun(self):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        # disable actions
        self.interfaceDisable()
        # check if downloading or uploading
        if self.actionIdx in (3,4,5) and (self.leUserName.text() == '' or self.lePassword.text() == ''):
            QtGui.QMessageBox.information(self, 'Information',
               "Your must provide user and password information for upload or download!", QtGui.QMessageBox.Ok)
            self.interfaceEnable()
        else:
            if self.actionIdx == 3:
                self.importToLMB('newProjects')
            elif self.actionIdx == 4:
                self.importToLMB('updateCurrentProject')
            elif self.actionIdx == 5:
                self.transferReportStatus("Checking Heritage datas structure before upload")
                response = self.getHeritageJson()
                self.downloadDict = json.loads(response)
                retVal = self.updateProjectReport(True)
                if retVal == 1:
                    messageText = 'Changes additions, deletions and updates were made to the '
                    messageText += 'Heritage data structure. Please update system and review '
                    messageText += 'automated changes to ensure data is valid before uploading.'
                    QtGui.QMessageBox.information(self, 'Information',
                        messageText, QtGui.QMessageBox.Ok)
                    self.close()
                elif retVal == -1:
                    messageText = 'No matching project found. '
                    QtGui.QMessageBox.information(self, 'Information',
                        messageText, QtGui.QMessageBox.Ok)
                    self.close()
                elif retVal == 0:
                    self.uploadToHeritagePreparation()
                else:
                    self.close()
            else:
                # start action process in thread
                self.errorText = ''
                # instantiate transferContent worker
                self.pbTransfer.setText('Transfer')
                account = self.leUserName.text()
                password = self.lePassword.text()
                url = self.leURL.text()
                worker = transferContent(self.actionIdx, self.dirName, \
                    self.projDict, self.projId, url, account, password, \
                    [], [], 0)
                # connect cancel to worker kill
                self.pbCancel.clicked.connect(worker.kill)
                # start the worker in a new thread
                thread = QtCore.QThread(self)
                worker.moveToThread(thread)
                # connect things together
                worker.workerFinished.connect(self.transferFinished)
                worker.workerError.connect(self.transferError)
                worker.workerStatus.connect(self.transferReportStatus)
                worker.workerPopup.connect(self.transferPopupMessage)
                worker.progressAll.connect(self.pbAllProgress.setValue)
                worker.progressStep.connect(self.pbStepProgress.setValue)
                thread.started.connect(worker.run)
                # run
                thread.start()
                # manage thread and worker
                self.thread = thread
                self.worker = worker

    #
    # transfer finished
    #
    def transferFinished(self,ret,messageText):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        # clean up the worker and thread
        self.worker.deleteLater()
        self.thread.quit()
        self.thread.wait()
        self.thread.deleteLater()
        # report status
        if ret == True:
            # report the result
            if self.actionsStatus == 'Cancelled':
                QgsMessageLog.logMessage(self.processStatus)
            elif self.actionsStatus <> 'Completed':
                # notify the user that something went wrong
                if self.errorText == '':
                    self.errorText = 'Something went wrong!'
                QgsMessageLog.logMessage([self.errorText])
        # reset the user interface
        self.pbAllProgress.setValue(0)
        self.pbStepProgress.setValue(0)
        # reset interface
        self.interfaceEnable()
        self.close()

    #
    # transfer error
    #
    def transferError(self,e,exception_string,messageText):
        
        QgsMessageLog.logMessage('Worker thread raised an exception\n' + str(exception_string), level=QgsMessageLog.CRITICAL)
        self.errorText = messageText

    #
    # report transfer status
    #
    def transferReportStatus(self,ret):

        self.actionsStatus = ret
        self.lblStepProgress.setText('Current Step: %s' % ret)

    #
    # show popup
    #
    def transferPopupMessage(self,messageText, messageType):
    
        if messageType == 'Warning':
            QtGui.QMessageBox.warning(self, 'Warning',
                messageText, QtGui.QMessageBox.Ok)
        else:
            QtGui.QMessageBox.information(self, 'Information',
                messageText, QtGui.QMessageBox.Ok)

    #
    ########################################################
    #            Communication with Heritage               #
    ########################################################
    #
    # 
    # get heritage json
    #
    def getHeritageJson(self):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        url = self.leURL.text()
        url = url + '/tools/heritage/mapbiographer/json/'
        values = {'username': self.leUserName.text(), 'password': self.lePassword.text()}
        data = urllib.urlencode(values)
        try:
            request = urllib2.Request(url,data)
            response = urllib2.urlopen(request)
            temp = response.read()
            if self.debug:
                f = open('response.json','w')
                tempDict = json.loads(temp)
                f.write(json.dumps(tempDict,indent=4))
                f.close()
            return(temp)
        except Exception, e:            
            return('{"result": "error", "data": "connection error (%s)"}' % str(e))
            
    #
    # connect, retrieve and import information from Heritage
    #
    def importToLMB(self,importType):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        self.pbAllProgress.setValue(50)
        self.transferReportStatus("Getting information from Heritage")
        response = self.getHeritageJson()
        self.downloadDict = json.loads(response)
        if self.downloadDict['result'] <> 'success':
            self.frHeritageLogin.setVisible(False)
            self.frHeritageInfo.setVisible(True)  
            self.pbCancel.setDisabled(True)
            self.pbImport.setVisible(False)
            self.pbUpload.setEnabled(False)
            self.pbUpload.setVisible(True)
            self.lblProject.setVisible(False)
            self.cbProject.setVisible(False)
            messageText = 'There was an error connecting to Heritage\n'
            messageText += self.downloadDict['data']
            self.pteReport.setPlainText(messageText)
        else:
            self.pbAllProgress.setValue(85)
            errorInfo = self.downloadDict['result']
            if importType == 'newProjects':
                self.newProjectsReport()
            else:
                retVal = self.updateProjectReport()
                if retVal == -1:
                    messageText = 'No matching project found. '
                    QtGui.QMessageBox.information(self, 'Information',
                        messageText, QtGui.QMessageBox.Ok)
                    self.close()
        self.resize(500, 450)
        self.pbAllProgress.setValue(0)
        self.pbStepProgress.setValue(0)
        self.transferReportStatus("")

    #
    # show list of what can be exported to heritage
    #
    def uploadToHeritagePreparation(self):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        # get list of documents from current project
        self.docList = []
        self.docKeys = []
        for key, value in self.projDict['projects'][str(self.projId)]['documents'].iteritems():
            if value['status'] == 'T':
                self.docList.append(value['code'])
                self.docKeys.append(int(key))
        messageText = 'Transcribed interviews from the current default project (%s) are:\n' % self.projDict['projects'][str(self.projId)]['code']
        self.frHeritageLogin.setVisible(False)
        self.frHeritageInfo.setVisible(True)  
        self.pbCancel.setDisabled(True)
        self.pbImport.setVisible(False)
        self.pbUpload.setEnabled(False)
        self.pbUpload.setVisible(True)
        self.lblProject.setVisible(False)
        self.cbProject.setVisible(False)
        if len(self.docList) > 0:
            for doc in self.docList:
                messageText += '%s\n' % doc
            # get list of projects and prompt user for action
            self.pbAllProgress.setValue(100)
            self.pbStepProgress.setValue(65)
            self.transferReportStatus("Getting information from Heritage")
            response = self.getHeritageJson()
            self.downloadDict = json.loads(response)
            if self.downloadDict['result'] <> 'success':
                messageText = 'There was an error connecting to Heritage\n'
                messageText += self.downloadDict['data']
                self.pteReport.setPlainText(messageText)
            else:
                self.pbAllProgress.setValue(75)
                errorInfo = self.downloadDict['result']
                self.uploadKeys = []
                self.cbProject.clear()
                idxMatch = None
                x = 0
                for key, value in self.downloadDict['data']['projects'].iteritems():
                    self.cbProject.addItem(value['code'])
                    if value['code'] == self.projDict['projects'][str(self.projId)]['code']:
                        idxMatch = x
                    self.uploadKeys.append(key)
                    x += 1
                if idxMatch <> None:
                    self.cbProject.setCurrentIndex(idxMatch)
                if len(self.uploadKeys) > 0:
                    self.pbUpload.setEnabled(True)
                self.lblProject.setText('Select Heritage Destination Project:')
                self.lblProject.setVisible(True)
                self.cbProject.setVisible(True)
                self.pteReport.setPlainText(messageText)
                self.pbUpload.setEnabled(True)
        else:
            messageText = 'No are no transcribed interviews ready to upload in this project'
            self.pteReport.setPlainText(messageText)
        self.resize(500, 450)
        self.pbAllProgress.setValue(0)
        self.pbStepProgress.setValue(0)
        self.transferReportStatus("")

    #
    # upload to heritage
    #
    def uploadToHeritage(self):
        
        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
         # start action process in thread
        self.errorText = ''
        # instantiate transferContent worker
        self.pbTransfer.setText('Transfer')
        account = self.leUserName.text()
        password = self.lePassword.text()
        url = self.leURL.text()
        idx = self.cbProject.currentIndex()
        worker = transferContent(self.actionIdx, self.dirName, \
            self.projDict, self.projId, url, account, password, \
            self.docKeys, self.docList, self.uploadKeys[idx])
        # connect cancel to worker kill
        self.pbCancel.clicked.connect(worker.kill)
        # start the worker in a new thread
        thread = QtCore.QThread(self)
        worker.moveToThread(thread)
        # connect things together
        worker.workerFinished.connect(self.transferFinished)
        worker.workerError.connect(self.transferError)
        worker.workerStatus.connect(self.transferReportStatus)
        worker.workerPopup.connect(self.transferPopupMessage)
        worker.progressAll.connect(self.pbAllProgress.setValue)
        worker.progressStep.connect(self.pbStepProgress.setValue)
        thread.started.connect(worker.run)
        # run
        thread.start()
        # manage thread and worker
        self.thread = thread
        self.worker = worker

    #
    ########################################################
    #                 Changes Detection                    #
    ########################################################
    #
    #
    # identify new documents in a project
    #
    def projectIdentifyNewDocuments(self, serverProjKey):
        
        nDocList = []
        dDocList = []
        localProjKey = str(self.projId)
        for dKey, dValue in self.downloadDict['data']['documents'].iteritems():
            # check if document belongs to this project
            if str(dValue['project_id']) == serverProjKey:
                dupFound = False
                # loop through local documents to assess if downloaded doc is new
                for ddKey, ddValue in self.projDict['projects'][localProjKey]['documents'].iteritems():
                    if dValue['code'] == ddValue['code']:
                        dDocList.append(dValue)
                        dupFound = True
                if dupFound == False:
                    nDocList.append(dValue)
        return(nDocList,dDocList)
        
    #
    # assess server custom field list to determine 
    # which custom fields to add, delete and update
    #
    def projectAssessCustomFields(self, customFields):
        
        newCustomFields = []
        deleteCustomFields = []
        updateCustomFields = []
        projKey = str(self.projId)
        if 'custom_fields' in self.projDict['projects'][projKey]:
            serverList = [a['code'] for a in customFields]
            localList = [a['code'] for a in self.projDict['projects'][projKey]['custom_fields']]
            commonList = list(set(localList).intersection(serverList))
            # identify updates related to required status
            updateList = []
            for lcl in self.projDict['projects'][projKey]['custom_fields']:
                if lcl['code'] in commonList:
                    for srv in customFields:
                        if lcl['code'] == srv['code'] and lcl['required'] <> srv['required']:
                            if lcl['code'] not in updateList:
                                updateList.append(lcl['code'])
                                updateCustomFields.append([lcl,srv])
            # identify deletions
            deleteList = list(set(localList).difference(serverList))
            for lcl in self.projDict['projects'][projKey]['custom_fields']:
                for a in deleteList:
                    if lcl['code'] == a:
                        deleteCustomFields.append(lcl)
            # identify additions
            addList = list(set(serverList).difference(localList))
            for srv in customFields:
                for a in addList:
                    if srv['code'] == a:
                        newCustomFields.append(srv)
        elif len(value['custom_fields']) > 0:
            for srv in customFields:
                 newCustomFields.append(srv)
        return(updateCustomFields,newCustomFields,deleteCustomFields)

    #
    # compareLists - compare lists for use periods, times of year and content codes
    #
    def projectCompareLists(self,localList,serverList):

        # Note 1: keep track of which records have been processed to avoid
        # redundant processing and processing errors
        # Note 2: the content or value is viewed as being of primary importance
        # the label is just a descriptor of that content to most comparisions
        # will be made on the basis of the value
        localUsed = []
        serverUsed = []
        updateList = []
        newList = []
        deleteList = []
        # identify updates and no changes
        for lcl in localList:
            if lcl[0] not in localUsed:
                for srv in serverList:
                    if srv[0] not in serverUsed:
                        if lcl[1] == srv[1] and lcl[2] == srv[2]:
                            localUsed.append(lcl[0])
                            serverUsed.append(srv[0])
                        elif lcl[1] == srv[1] and lcl[2] <> srv[2]:
                            localUsed.append(lcl[0])
                            serverUsed.append(srv[0])
                            updateList.append([lcl[0],lcl[1],lcl[2],srv[0],srv[1],srv[2]])
        # identify additions
        for srv in serverList:
            if srv[0] not in serverUsed:
                fldFound = False
                for lcl in localList:
                    if lcl[0] not in localUsed and srv[1] == lcl[1]:
                        fldFound = True
                if fldFound == False:
                    serverUsed.append(srv[0])
                    newList.append(srv)
        # identify deletions
        for lcl in localList:
            if lcl[0] not in localUsed:
                fldFound = False
                for srv in serverList:
                    if srv[0] not in serverUsed and srv[1] == lcl[1]:
                        fldFound = True
                if fldFound == False:
                    localUsed.append(lcl[0])
                    deleteList.append(lcl)
                    
        return(updateList,newList,deleteList)
    
    #
    # assess server use periods to determine which 
    # use periods to add, delete or update
    #
    def projectAssessUsePeriods(self, serverUsePeriods):
        
        newUsePeriods = []
        deleteUsePeriods = []
        updateUsePeriods = []
        projKey = str(self.projId)
        # create matching arrays with a sequential key, a value and a label
        localList = []
        for key in range(len(self.projDict['projects'][projKey]['default_time_periods'])):
            temp = self.projDict['projects'][projKey]['default_time_periods'][key]
            localList.append([key,temp[0],temp[1]])
        serverList = []
        for key in range(len(serverUsePeriods)):
            temp = serverUsePeriods[key]
            value = '%s : %s' % (temp['start'],temp['end'])
            label = temp['label']
            serverList.append([key,value,label])
        updateUsePeriods,newUsePeriods,deleteUsePeriods = self.projectCompareLists(localList,serverList)
        return(updateUsePeriods,newUsePeriods,deleteUsePeriods)

    #
    # assess server times of year to determine which 
    # times of year to add, delete or update
    #
    def projectAssessTimesOfYear(self, serverTimesOfYear):

        newTimesOfYear = []
        deleteTimesOfYear = []
        updateTimesOfYear = []
        projKey = str(self.projId)
        # create matching arrays with a sequential key, a value and a label
        localList = []
        for key in range(len(self.projDict['projects'][projKey]['default_time_of_year'])):
            temp = self.projDict['projects'][projKey]['default_time_of_year'][key]
            value = [int(x) for x in temp[0].split(',')]
            localList.append([key,value,temp[1]])
        serverList = []
        for key in range(len(serverTimesOfYear)):
            temp = serverTimesOfYear[key]
            serverList.append([key,temp['months'],temp['label']])
        updateTimesOfYear,newTimesOfYear,deleteTimesOfYear = self.projectCompareLists(localList,serverList)
        return(updateTimesOfYear,newTimesOfYear,deleteTimesOfYear)

    #
    # assess server content codes to determine which 
    # content codes to add, delete or update
    #
    def projectAssessContentCodes(self, serverContentCodes):

        newContentCodes = []
        deleteContentCodes = []
        updateContentCodes = []
        projKey = str(self.projId)
        # create matching arrays with a sequential key, a value and a label
        localList = []
        for key in range(len(self.projDict['projects'][projKey]['default_codes'])):
            temp = self.projDict['projects'][projKey]['default_codes'][key]
            localList.append([key,temp[0],temp[1]])
        serverList = []
        for key in range(len(serverContentCodes)):
            temp = serverContentCodes[key]
            serverList.append([key,temp['code'],temp['label']])
        updateContentCodes,newContentCodes,deleteContentCodes = self.projectCompareLists(localList,serverList)
        return(updateContentCodes,newContentCodes,deleteContentCodes)

    #
    # project report updates
    #
    def projectReportUpdates(self,updateCF,updateUP,updateToY,updateCC):

        if len(updateCF) > 0 or len(updateUP) > 0 or  len(updateToY) > 0 \
            or len(updateCC) > 0:
            updateExisting = True
            appendText = "Within the current project, the following updates are required:\n"
            # note that document updates not supported
            appendText += 'Documents: \n'
            appendText += '    Updates not supported\n'
            # custom fields
            appendText += 'Custom Fields to update: \n'
            if len(updateCF) > 0:
                for subrec in updateCF:
                    appendText += '    "%s" (%s) required changed to %s\n' % (subrec[0]['name'],subrec[0]['code'],str(subrec[1]['required']))
            else:
                appendText += '    None\n'
            # use periods
            appendText += 'Use Periods to update: \n'
            if len(updateUP) > 0:
                for subrec in updateUP:
                    appendText += '    %s - "%s" changed to "%s"\n' % (subrec[1],subrec[2],subrec[5])
            else:
                appendText += '    None\n'
            # times of year
            appendText += 'Times of Year to update: \n'
            if len(updateToY) > 0:
                for subrec in updateToY:
                    appendText += '    %s - "%s" changed to "%s"\n' % (subrec[1],subrec[2],subrec[5])
            else:
                appendText += '    None\n'
            # content codes
            appendText += 'Content Codes to update: \n'
            if len(updateCC) > 0:
                for subrec in updateCC:
                    appendText += '    %s - "%s" changed to "%s"\n' % (subrec[1],subrec[2],subrec[5])
            else:
                appendText += '    None\n'
            appendText += '\n'
        else:
            updateExisting = False
            appendText = "No updates found for existing project.\n\n"
            
        return(updateExisting,appendText)
        
    #
    # project report additions
    #
    def projectReportAdditions(self,appendText,nDocList,newCF,newUP,newToY,newCC):

        if len(nDocList) > 0 or len(newCF) > 0 or len(newUP) > 0 or \
            len(newToY) > 0 or len(newCC) > 0:
            addToExisting = True
            appendText += "Within the current project, the following additions are required:\n"
            # documents
            appendText += 'Documents to add: \n'
            if len(nDocList) > 0:
                self.addToExisting = True
                for subrec in nDocList:
                    appendText += '    %s\n' % subrec['code']
            else:
                appendText += '    None\n'
            # custom fields
            appendText += 'Custom Fields to add: \n'
            if len(newCF) > 0:
                for subrec in newCF:
                    appendText += '    %s - "%s"\n' % (subrec['code'],subrec['name'])
            else:
                appendText += '    None\n'
            # use periods
            appendText += 'Use Periods to add: \n'
            if len(newUP) > 0:
                for subrec in newUP:
                    appendText += '    %s - "%s"\n' % (subrec[1],subrec[2])
            else:
                appendText += '    None\n'
            # times of year
            appendText += 'Times of Year to add: \n'
            if len(newToY) > 0:
                for subrec in newToY:
                    appendText += '    %s - "%s"\n' % (subrec[1],subrec[2])
            else:
                appendText += '    None\n'
            # content codes
            appendText += 'Content Codes to add: \n'
            if len(newCC) > 0:
                for subrec in newCC:
                    appendText += '    %s - "%s"\n' % (subrec[1],subrec[2])
            else:
                appendText += '    None\n'
            appendText += '\n'
        else:
            addToExisting = False
            appendText += "No new information found to add for existing project.\n\n"
            
        return(addToExisting,appendText)

    #
    # project report deletions
    #
    def projectReportDeletions(self,appendText,dDocList,deleteCF,deleteUP,deleteToY,deleteCC):
    
        if len(deleteCF) > 0 or len(deleteUP) > 0 or len(deleteToY) > 0 or \
            len(deleteCC) > 0:
            deleteExisting = True
            appendText += "Within the current project, the following deletions are required:\n"
            # note that document deletes not supported
            appendText += 'Documents: \n'
            appendText += '    Deletions not supported\n'
            # custom fields
            appendText += 'Custom Fields to delete: \n'
            if len(deleteCF) > 0:
                for subrec in deleteCF:
                    appendText += '   %s - "%s"\n' % (subrec['code'],subrec['name'])
            else:
                appendText += '    None\n'
            # use periods
            appendText += 'Use Periods to delete: \n'
            if len(deleteUP) > 0:
                for subrec in deleteUP:
                    appendText += '    %s - "%s"\n' % (subrec[1],subrec[2])
            else:
                appendText += '    None\n'
            # times of year
            appendText += 'Times of Year to delete: \n'
            if len(deleteToY) > 0:
                for subrec in deleteToY:
                    appendText += '    %s - "%s"\n' % (subrec[1],subrec[2])
            else:
                appendText += '    None\n'
            # content codes
            appendText += 'Content Codes to delete: \n'
            if len(deleteCC) > 0:
                for subrec in deleteCC:
                    appendText += '    %s - "%s"\n' % (subrec[1],subrec[2])
            else:
                appendText += '    None\n'
            appendText += '\n'
        else:
            deleteExisting = False
            appendText += "No deletions required for existing project.\n"
            
        return(deleteExisting,appendText)

    #
    # project update report
    #
    def updateProjectReport(self,isUpload=False):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        # get existing project code
        projectCode = self.projDict['projects'][str(self.projId)]['code']
        self.updateExisting = False
        self.addToExisting = False
        self.deleteExisting = False
        self.addNewProjects = False
        self.addParticipants = False
        # loop through dowloaded projects and documents to assess what 
        # changes or additions are possible for the current project
        matchFound = False
        if not isinstance(self.downloadDict, dict):
            return(-1)
        for key, value in self.downloadDict['data']['projects'].iteritems():
            if value['code'] == projectCode:
                serverProjectKey = key
                #
                # this is temporary code to correct a bug in Heritage 
                # related to mixed case of the 'required' key for 
                # custom fields
                if 'custom_fields' in value:
                    for rec in value['custom_fields']:
                        if 'Required' in rec:
                            rec['required'] = rec['Required']
                            del rec['Required']
                #
                # documents
                nDocList,dDocList = self.projectIdentifyNewDocuments(serverProjectKey)
                # custom fields
                if 'custom_fields' in value:
                    updateCF,newCF,deleteCF = self.projectAssessCustomFields(value['custom_fields'])
                else:
                    updateCF = []
                    newCF = []
                    deleteCF = []
                # use periods
                updateUP,newUP,deleteUP = self.projectAssessUsePeriods(value['default_time_periods'])
                # times of year
                updateToY,newToY,deleteToY = self.projectAssessTimesOfYear(value['default_time_of_year_values'])
                # content codes
                updateCC,newCC,deleteCC = self.projectAssessContentCodes(value['default_codes'])
                matchFound = True
                break
        # participants
        nPartList = []
        dPartList = []
        for key, value in self.downloadDict['data']['participants'].iteritems():
            dupFound = False
            for lKey, lValue in self.projDict['participants'].iteritems():
                if value['code'] == lValue['code']:
                    dPartList.append(value['code'])
                    dupFound = True
            if dupFound == False:
                nPartList.append(value['code'])
        QgsMessageLog.logMessage('participants checked')
        if matchFound == True:
            if isUpload == True:
                if len(updateCF) > 0 or len(newCF) > 0 or len(deleteCF) > 0 or \
                len(updateUP) > 0 or len(newUP) > 0 or len(deleteUP) > 0 or\
                len(updateToY) > 0 or len(newToY) > 0 or len(deleteToY) > 0 or \
                len(updateCC) > 0 or len(newCC) > 0 or len(deleteCC) > 0:
                    return(1)
                else:
                    return(0)
            else:
                # generate report
                reportText = ''
                # additions
                self.projUpdate = {'newDocs':nDocList,'deleteDocs':dDocList,\
                    'updateCF':updateCF,'newCF':newCF,'deleteCF':deleteCF,\
                    'updateUP':updateUP,'newUP':newUP,'deleteUP':deleteUP,\
                    'updateToY':updateToY,'newToY':newToY,'deleteToY':deleteToY,\
                    'updateCC': updateCC,'newCC':newCC,'deleteCC':deleteCC}
                # report updates
                self.updateExisting,appendText = self.projectReportUpdates(updateCF,updateUP,updateToY,updateCC)
                self.addToExisting,appendText = self.projectReportAdditions(appendText,nDocList,newCF,newUP,newToY,newCC)
                self.deleteExisting,appendText = self.projectReportDeletions(appendText,dDocList,deleteCF,deleteUP,deleteToY,deleteCC)
                reportText += appendText
                reportText += '\n'
                buttonText = 'Update '
                if self.addToExisting or self.deleteExisting or self.updateExisting:
                    buttonText += 'Current Project'
                if self.addParticipants:
                    if len(buttonText) > 8:
                        buttonText += 'and Participants'
                    else:
                        buttonText += 'Participants'
                self.pbImport.setText(buttonText)
                # new participants
                if len(nPartList) > 0:
                    self.addParticipants = True
                    reportText += 'The following participants can be imported:\n'
                    reportText += '%s \n' % ", ".join(nPartList)
                    self.addParticipants = True
                else:
                    reportText += "No new participant records found.\n"
                    self.addParticipants = False
                if self.addToExisting or self.addParticipants or \
                    self.deleteExisting or self.updateExisting:
                    self.pbImport.setEnabled(True)
                self.nParticipants = nPartList
                self.dParticipants = dPartList
                self.frHeritageLogin.setVisible(False)
                self.pteReport.setPlainText(reportText)
                self.frHeritageInfo.setVisible(True)  
                self.pbImport.setVisible(True)
                self.pbCancel.setDisabled(True)
                self.pbUpload.setVisible(False)
                self.lblProject.setVisible(False)
                self.cbProject.setVisible(False)
                return(0)
        else:
            return(-1)

    #
    # new projects report
    #
    def newProjectsReport(self):
        
        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        localProjects = []
        localProjKeys = []
        self.updateExisting = False
        self.addToExisting = False
        self.deleteExisting = False
        self.addNewProjects = False
        self.addParticipants = False
        for key, value in self.projDict['projects'].iteritems():
            localProjects.append(value['code'])
            localProjKeys.append(key)
        newProjects = []
        # find new projects
        self.cbProject.clear()
        for key, value in self.downloadDict['data']['projects'].iteritems():
            if (value['code'] in localProjects) == False:
                # new
                nDocList = []
                dDocList = []
                # loop through document list from download
                for dKey, dValue in self.downloadDict['data']['documents'].iteritems():
                    # check if document belongs to this project
                    if str(dValue['project_id']) == key:
                        nDocList.append(dValue['code'])
                newProjects.append([key,value['code'],nDocList,dDocList])
                self.cbProject.addItem(value['code'])
        # find new participants
        nPartList = []
        dPartList = []
        for key, value in self.downloadDict['data']['participants'].iteritems():
            dupFound = False
            for lKey, lValue in self.projDict['participants'].iteritems():
                if value['code'] == lValue['code']:
                    dPartList.append(value['code'])
                    dupFound = True
            if dupFound == False:
                nPartList.append(value['code'])
        # prepare message
        reportText = ''
        # new project message
        if len(newProjects) > 0:
            self.addNewProjects = True
            reportText += "The following projects and documents can be imported:\n"
            for rec in newProjects:
                reportText += '%s: ' % rec[1]
                if len(rec[2]) > 0:
                    reportText += '%s \n' % ", ".join(rec[2])
                else:
                    reportText += '\n'
        else:
            reportText += "No new project records are available.\n"
        # new participant message
        if len(nPartList) > 0:
            self.addParticipants = True
            reportText += 'The following participants can be imported:\n'
            reportText += '%s \n' % ", ".join(nPartList)
        else:
            reportText += "No new participant records are available.\n"
        if self.addNewProjects or self.addParticipants:
            self.pbImport.setEnabled(True)
        self.pbImport.setText('Import')
        self.newProjects = newProjects
        self.nParticipants = nPartList
        self.frHeritageLogin.setVisible(False)
        self.pteReport.setPlainText(reportText)
        self.frHeritageInfo.setVisible(True)  
        self.pbImport.setVisible(True)
        self.pbCancel.setDisabled(True)
        self.pbUpload.setVisible(False)
        self.lblProject.setText('Select Heritage Project for Import:')
        self.lblProject.setVisible(True)
        self.cbProject.setVisible(True)

    #
    ########################################################
    #              Local Import Methods                    #
    ########################################################
    #
    #
    # import participants
    # 
    def importParticipants(self):
        
        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        # determine max participant id
        maxId = 0
        for key, value in self.projDict['participants'].iteritems():
            if int(key) > maxId:
                maxId = int(key)
        self.pbStepProgress.setValue(30)
        for key, value in self.downloadDict['data']['participants'].iteritems():
            if value['code'] in self.nParticipants:
                maxId += 1
                temp = {
                    "id": maxId,
                    "code": value['code'],
                    "first_name": value['first_name'],
                    "last_name": value['last_name'],
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
                if "maiden_name" in value:
                    temp["maiden_name"] = value["maiden_name"]
                    temp["subcommunity"] = value["subcommunity"]
                    temp["gender"] = value["gender"]
                    temp["marital_status"] = value["marital_status"]
                    temp["family_group"] = value["family_group"]
                    temp["note"] = value["note"]
                    temp["birth_date"] = value["birth_date"]
                    temp["email"] = value["email"]
                    temp["tags"] = value["tags"]
                    x = 0
                    for rec in value["telecoms"]:
                        x +=1
                        temp["telecoms"][str(x)] = {}
                        temp["telecoms"][str(x)]['id'] = x
                        temp["telecoms"][str(x)]['type'] = rec['type']
                        temp["telecoms"][str(x)]['telecom'] = rec['value']
                    x = 0
                    for rec in value["addresses"]:
                        x +=1
                        temp["addresses"][str(x)] = {}
                        temp["addresses"][str(x)]['id'] = x
                        temp["addresses"][str(x)]['type'] = rec['type']
                        temp["addresses"][str(x)]['address'] = rec['value']
                self.projDict["participants"][str(maxId)] = temp

    #
    # add documents
    #
    def importAddDocument(self,docSrcDict):
        
        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        # add the document to the project
        maxDocId = 0
        for dKey, dValue in self.projDict['projects'][str(self.projId)]['documents'].iteritems():
            if int(dKey) > maxDocId:
                maxDocId = int(dKey)
        # process tags
        if docSrcDict['tags'] == "":
            docTags = []
        else:
            tagList = docSrcDict['tags'].split(",")
            docTags = [tag.strip() for tag in tagList]
        # process participants
        if docSrcDict['participants'] == []:
            partDict = {}
        else:
            partDict = {}
            partKey = 0
            # step through download dict participants record
            for rec in docSrcDict['participants']:
                # get participant code
                cpCode = self.downloadDict['data']['participants'][str(rec['participant_id'])]['code']
                cpKey = None
                # match participant code to get local participant id
                for pKey,pValue in self.projDict['participants'].iteritems():
                    if pValue['code'] == cpCode:
                        cpKey = pKey
                        break
                # if participant id found, add record to document
                if cpKey <> None:
                    partKey += 1
                    partDict[str(partKey)] = {
                        "subcommunity": rec['subcommunity'], 
                        "id": partKey, 
                        "family": rec['family_group'], 
                        "participant_id": int(cpKey)
                    }
        # create record
        temp = {
            "id": maxDocId+1,
            "code": docSrcDict['code'],
            "title": docSrcDict['title'],
            "description": docSrcDict['description'],
            "location": docSrcDict['location'],
            "note": docSrcDict['note'],
            "tags": docTags,
            "default_data_security": docSrcDict['default_data_security'],
            "status": docSrcDict['data_status'],
            "creator": docSrcDict['creator'],
            "publisher": docSrcDict['publisher'],
            "subject": docSrcDict['subject'],
            "language": docSrcDict['language'],
            "source": docSrcDict['source'],
            "citation": docSrcDict['citation'],
            "rights_statement": docSrcDict['rights_statement'],
            "rights_holder": docSrcDict['rights_holder'],
            "start_datetime": docSrcDict['start_datetime'],
            "end_datetime": docSrcDict['end_datetime'],
            "participants": partDict
        }
        self.projDict['projects'][str(self.projId)]['documents'][str(maxDocId+1)] = temp

    #
    # import a single project
    #
    def importSingleProject(self,prjKey,prjSrcDict,maxId):

        maxId += 1
        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
            QgsMessageLog.logMessage('New Project Key: %d, Project Code: %s' % (maxId,prjSrcDict['code']))
        # process tags
        if prjSrcDict['tags'] == "":
            projTags = []
        else:
            tagList = prjSrcDict['tags'].split(",")
            projTags = [tag.strip() for tag in tagList]
        # process codes
        if prjSrcDict['default_codes'] == []:
            defaultCodes = []
            defCode = ""
        else:
            defaultCodes = []
            for rec in prjSrcDict['default_codes']:
                defaultCodes.append([rec['code'],rec['label']])
            defCode = defaultCodes[0][0]
        # process time periods
        if prjSrcDict['default_time_periods'] == []:
            timePeriods = []
        else:
            timePeriods = []
            for rec in prjSrcDict['default_time_periods']:
                timePeriods.append(['%s : %s' % (rec['start'],rec['end']),rec['label']])
        # process times of year
        if prjSrcDict['default_time_of_year_values'] == []:
            timesOfYear = []
        else:
            timesOfYear = []
            for rec in prjSrcDict['default_time_of_year_values']:
                timesOfYear.append([",".join(str(x) for x in rec['months']),rec['label']])
        # process documents
        docDict = {}
        intvKey = 0
        for dKey, dValue in self.downloadDict['data']['documents'].iteritems():
            if prjKey == str(dValue["project_id"]):
                intvKey += 1
                # process tags
                if dValue['tags'] == "":
                    docTags = []
                else:
                    tagList = dValue['tags'].split(",")
                    docTags = [tag.strip() for tag in tagList]
                # process participants
                if dValue['participants'] == []:
                    partDict = {}
                else:
                    partDict = {}
                    partKey = 0
                    # step through download dict participants record
                    for rec in dValue['participants']:
                        # get participant code
                        cpCode = self.downloadDict['data']['participants'][str(rec['participant_id'])]['code']
                        cpKey = None
                        # match participant code to get local participant id
                        for pKey, pValue in self.projDict['participants'].iteritems():
                            if pValue['code'] == cpCode:
                                cpKey = pKey
                                break
                        # if participant id found, add record to document
                        if cpKey <> None:
                            partKey += 1
                            partDict[str(partKey)] = {
                                "subcommunity": rec['subcommunity'], 
                                "id": partKey, 
                                "family": rec['family_group'], 
                                "participant_id": int(cpKey)
                            }
                # create record
                temp = {
                    "id": intvKey,
                    "code": dValue['code'],
                    "title": dValue['title'],
                    "description": dValue['description'],
                    "location": dValue['location'],
                    "note": dValue['note'],
                    "tags": docTags,
                    "default_data_security": dValue['default_data_security'],
                    "status": dValue['data_status'],
                    "creator": dValue['creator'],
                    "publisher": dValue['publisher'],
                    "subject": dValue['subject'],
                    "language": dValue['language'],
                    "source": dValue['source'],
                    "citation": dValue['citation'],
                    "rights_statement": dValue['rights_statement'],
                    "rights_holder": dValue['rights_holder'],
                    "start_datetime": dValue['start_datetime'],
                    "end_datetime": dValue['end_datetime'],
                    "participants": partDict
                }
                docDict[str(intvKey)] = temp
        # create document record
        if 'custom_fields' in prjSrcDict:
            cf = prjSrcDict['custom_fields']
        else:
            cf = []
        temp = {
            "id": maxId,
            "code": prjSrcDict['code'],
            "description": prjSrcDict['description'],
            "note": prjSrcDict['note'],
            "tags": projTags,
            "citation": prjSrcDict['citation'],
            "source": prjSrcDict['source'],
            "default_codes": defaultCodes,
            "default_time_periods": timePeriods,
            "default_time_of_year": timesOfYear,
            "ns_code": defCode,
            "pt_code": defCode,
            "ln_code": defCode,
            "pl_code": defCode,
            "lmb_map_settings": {},
            "custom_fields": cf,
            "documents": docDict,
            "use_heritage": True
        }
        self.projDict["projects"][str(maxId)] = temp

    #
    # import all possible projects
    #
    def importProjects(self):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        # determine max project id
        maxId = 0
        for key, value in self.projDict['projects'].iteritems():
            if int(key) > maxId:
                maxId = int(key)
        self.pbStepProgress.setValue(45)
        for key, value in self.downloadDict['data']['projects'].iteritems():
            # correct bug in heritage
            if 'custom_fields' in value:
                for fld in value['custom_fields']:
                    if 'Required' in fld:
                        fld['required'] = fld['Required']
                        del fld['Required']
            for rec in self.newProjects:
                if value['code'] == self.cbProject.currentText():
                    self.importSingleProject(key,value,maxId)
    
    #
    # update project documents to record changes to content code labels
    # 
    def projectDocumentRecordContentCodeUpdates(self,oldCC,newCC):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        for docListKey,docListValue in self.projDict['projects'][str(self.projId)]['documents'].iteritems():
            fName = os.path.join(self.dirName,'interviews','lmb-p%d-i%d-data.json' % (self.projId,docListValue['id']))
            # check if it exists:
            if os.path.exists(fName):
                # read contents
                f = open(fName,'r')
                docDict = json.loads(f.read())
                f.close()
                # change contents
                documentChanged = False
                for key, value in docDict.iteritems():
                    sectionChanged = False
                    if value['code_type'] == oldCC[0]:
                        value['note'] += 'Primary Code "%s" label changed from "%s to "%s". Please confirm content remains valid.\n' % (oldCC[0],oldCC[1],newCC[1])
                        sectionChanged = True
                    if oldCC[0] in value['content_codes']:
                        value['note'] += 'Content Code "%s" label changed from "%s" to "%s". Please confirm content remains valid.\n' % (oldCC[0],oldCC[1],newCC[1])
                        sectionChanged = True
                    if sectionChanged == True:
                        documentChanged = True
                        if 'HumanValidationRequired' not in value['tags']:
                            value['tags'].append('HumanValidationRequired')
                        value['note'] += 'Above changes made %s\n\n' % datetime.datetime.now().isoformat()[:16]
                # write file
                f = open(fName,'w')
                f.write(json.dumps(docDict,indent=4))
                f.close()
                # update document note
                if documentChanged == True:
                    if 'HumanValidationRequired' not in docListValue['tags']:
                        docListValue['tags'].append('HumanValidationRequired')

    #
    # update project documents to record changes when a custom field is deleted
    #
    def projectDocumentRecordCustomFieldDeletion(self,oldCF):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        for docListKey,docListValue in self.projDict['projects'][str(self.projId)]['documents'].iteritems():
            fName = os.path.join(self.dirName,'interviews','lmb-p%d-i%d-data.json' % (self.projId,docListValue['id']))
            if os.path.exists(fName):
                # read contents
                f = open(fName,'r')
                docDict = json.loads(f.read())
                f.close()
                # change contents
                documentChanged = False
                for key, value in docDict.iteritems():
                    sectionChanged = False
                    if oldCF['code'] in value:
                        if value[oldCF['code']] <> '':
                            value['note'] += 'Custom field "%s" (%s, Type: %s) was deleted. \nThe value was "%s". Please confirm content remains valid.\n' % (oldCF['name'],oldCF['code'],oldCF['type'],value[oldCF['code']])
                            del value[oldCF['code']]
                            sectionChanged = True
                    if sectionChanged == True:
                        documentChanged = True
                        if 'HumanValidationRequired' not in value['tags']:
                            value['tags'].append('HumanValidationRequired')
                        value['note'] += 'Above changes made %s\n\n' % datetime.datetime.now().isoformat()[:16]
                # write file
                f = open(fName,'w')
                f.write(json.dumps(docDict,indent=4))
                f.close()
                # update document note
                if documentChanged == True:
                    if 'HumanValidationRequired' not in docListValue['tags']:
                        docListValue['tags'].append('HumanValidationRequired')
    
    #
    # update project documents when a use period value is deleted
    #
    def projectDocumentRecordUsePeriodDeletion(self,oldUP):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        for docListKey,docListValue in self.projDict['projects'][str(self.projId)]['documents'].iteritems():
            fName = os.path.join(self.dirName,'interviews','lmb-p%d-i%d-data.json' % (self.projId,docListValue['id']))
            if os.path.exists(fName):
                # read contents
                f = open(fName,'r')
                docDict = json.loads(f.read())
                f.close()
                # change contents
                documentChanged = False
                for key, value in docDict.iteritems():
                    sectionChanged = False
                    if value['use_period'] == oldUP[0]:
                        value['note'] += 'Use Period "%s" (%s) was deleted. Please confirm content remains valid.\n' % (oldUP[0],oldUP[1])
                        value['use_period'] = 'U'
                        sectionChanged = True
                    if sectionChanged == True:
                        documentChanged = True
                        if 'HumanValidationRequired' not in value['tags']:
                            value['tags'].append('HumanValidationRequired')
                        value['note'] += 'Above changes made %s\n\n' % datetime.datetime.now().isoformat()[:16]
                # write file
                f = open(fName,'w')
                f.write(json.dumps(docDict,indent=4))
                f.close()
                # update document note
                if documentChanged == True:
                    if 'HumanValidationRequired' not in docListValue['tags']:
                        docListValue['tags'].append('HumanValidationRequired')
        
    #
    # update project documents when a time of year value is deleted
    #
    def projectDocumentRecordTimeOfYearDeletion(self,oldToY):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        for docListKey,docListValue in self.projDict['projects'][str(self.projId)]['documents'].iteritems():
            fName = os.path.join(self.dirName,'interviews','lmb-p%d-i%d-data.json' % (self.projId,docListValue['id']))
            if os.path.exists(fName):
                # read contents
                f = open(fName,'r')
                docDict = json.loads(f.read())
                f.close()
                # change contents
                documentChanged = False
                for key, value in docDict.iteritems():
                    sectionChanged = False
                    if value['time_of_year'] == oldToY[0]:
                        value['note'] += 'Time Period "%s" (%s) was deleted. Please confirm content remains valid.\n' % (oldToY[0],oldToY[1])
                        value['time_of_year'] = 'U'
                        sectionChanged = True
                    if sectionChanged == True:
                        documentChanged = True
                        if 'HumanValidationRequired' not in value['tags']:
                            value['tags'].append('HumanValidationRequired')
                        value['note'] += 'Above changes made %s\n\n' % datetime.datetime.now().isoformat()[:16]
                # write file
                f = open(fName,'w')
                f.write(json.dumps(docDict,indent=4))
                f.close()
                # update document note
                if documentChanged == True:
                    if 'HumanValidationRequired' not in docListValue['tags']:
                        docListValue['tags'].append('HumanValidationRequired')
        
    #
    # update project documents when a content code is deleted
    # 
    def projectDocumentRecordContentCodeDeletion(self,oldCC):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        for docListKey,docListValue in self.projDict['projects'][str(self.projId)]['documents'].iteritems():
            fName = os.path.join(self.dirName,'interviews','lmb-p%d-i%d-data.json' % (self.projId,docListValue['id']))
            if os.path.exists(fName):
                # read contents
                f = open(fName,'r')
                docDict = json.loads(f.read())
                f.close()
                # change contents
                documentChanged = False
                for key, value in docDict.iteritems():
                    sectionChanged = False
                    if value['code_type'] == oldCC[0]:
                        value['note'] += 'Primary Code "%s" (%s( was deleted. Please confirm content remains valid.\n' % (oldCC[0],oldCC[1])
                        value['code_type'] = self.projDict['projects'][str(self.projId)]['ns_code']
                        sectionChanged = True
                    if oldCC[0] in value['content_codes']:
                        value['note'] += 'Content Code "%s" (%s) was deleted. Please confirm content remains valid.\n' % (oldCC[0],oldCC[1])
                        del value['content_codes'][value['content_codes'].index(oldCC[0])]
                        sectionChanged = True
                    if sectionChanged == True:
                        documentChanged = True
                        if 'HumanValidationRequired' not in value['tags']:
                            value['tags'].append('HumanValidationRequired')
                        value['note'] += 'Above changes made %s\n\n' % datetime.datetime.now().isoformat()[:16]
                # write file
                f = open(fName,'w')
                f.write(json.dumps(docDict,indent=4))
                f.close()
                # update document note
                if documentChanged == True:
                    if 'HumanValidationRequired' not in docListValue['tags']:
                        docListValue['tags'].append('HumanValidationRequired')
                        
    #
    # import process additions
    #
    def importProcessAdditions(self):
        
        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        # documents
        for rec in self.projUpdate['newDocs']:
            self.importAddDocument(rec)
        # custom fields
        for rec in self.projUpdate['newCF']:
            if 'custom_fields' in self.projDict['projects'][str(self.projId)]:
                self.projDict['projects'][str(self.projId)]['custom_fields'].append(rec)
            else:
                self.projDict['projects'][str(self.projId)]['custom_fields'] = [rec]
        # use periods
        for rec in self.projUpdate['newUP']:
            self.projDict['projects'][str(self.projId)]['default_time_periods'].append([rec[1],rec[2]])
        # times of year
        for rec in self.projUpdate['newToY']:
            self.projDict['projects'][str(self.projId)]['default_time_of_year'].append([",".join(str(x) for x in rec[1]),rec[2]])
        # content codes
        for rec in self.projUpdate['newCC']:
            self.projDict['projects'][str(self.projId)]['default_codes'].append([rec[1],rec[2]])

    #
    # import process updates
    #
    def importProcessUpdates(self):
        
        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        # custom fields
        for srv in self.projUpdate['updateCF']:
            for cCF in self.projDict['projects'][str(self.projId)]['custom_fields']:
                if srv[1]['code'] == cCF['code']:
                    cCF['required'] = srv[1]['required']
                    break
        # use periods
        self.pbStepProgress.setValue(45)
        for srv in self.projUpdate['updateUP']:
            for cUP in self.projDict['projects'][str(self.projId)]['default_time_periods']:
                if srv[4] == cUP[0]:
                    cUP[1] = srv[5]
                    break
        # times of year
        self.pbStepProgress.setValue(65)
        for srv in self.projUpdate['updateToY']:
            for cToY in self.projDict['projects'][str(self.projId)]['default_time_of_year']:
                sToY = [",".join(str(x) for x in srv[4]),srv[5]]
                if sToY[0] == cToY[0]:
                    cToY[1] = srv[5]
                    break
        # content codes
        self.pbStepProgress.setValue(75)
        for srv in self.projUpdate['updateCC']:
            for cCC in self.projDict['projects'][str(self.projId)]['default_codes']:
                if srv[4] == cCC[0]:
                    self.projectDocumentRecordContentCodeUpdates(cCC,[srv[4],srv[5]])
                    cCC[1] = srv[5]
                    break

    #
    # import process deletions
    # 
    def importProcessDeletions(self):
        
        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        # custom fields
        for srv in self.projUpdate['deleteCF']:
            cfCnt = len(self.projDict['projects'][str(self.projId)]['custom_fields'])
            for x in range(cfCnt):
                temp = self.projDict['projects'][str(self.projId)]['custom_fields'][x]
                if srv['code'] == temp['code']:
                    self.projectDocumentRecordCustomFieldDeletion(temp)
                    del self.projDict['projects'][str(self.projId)]['custom_fields'][x]
                    break
        # use periods
        self.pbStepProgress.setValue(45)
        for srv in self.projUpdate['deleteUP']:
            upCnt = len(self.projDict['projects'][str(self.projId)]['default_time_periods'])
            for x in range(upCnt):
                temp = self.projDict['projects'][str(self.projId)]['default_time_periods'][x]
                if srv[1] == temp[0]:
                    self.projectDocumentRecordUsePeriodDeletion(temp)
                    del self.projDict['projects'][str(self.projId)]['default_time_periods'][x]
                    break
        # times of year
        self.pbStepProgress.setValue(65)
        for srv in self.projUpdate['deleteToY']:
            sToY = ",".join(str(x) for x in srv[1])
            toyCnt = len(self.projDict['projects'][str(self.projId)]['default_time_of_year'])
            for x in range(toyCnt):
                temp = self.projDict['projects'][str(self.projId)]['default_time_of_year'][x]
                if sToY == temp[0]:
                    self.projectDocumentRecordTimeOfYearDeletion(temp)
                    del self.projDict['projects'][str(self.projId)]['default_time_of_year'][x]
                    break
        # content codes
        self.pbStepProgress.setValue(75)
        for srv in self.projUpdate['deleteCC']:
            ccCnt = len(self.projDict['projects'][str(self.projId)]['default_codes'])
            for x in range(ccCnt):
                temp = self.projDict['projects'][str(self.projId)]['default_codes'][x]
                if srv[1] == temp[0]:
                    self.projectDocumentRecordContentCodeDeletion(temp)
                    del self.projDict['projects'][str(self.projId)]['default_codes'][x]
                    break

    #
    # import data into local LMB instance
    #
    def importPerform(self):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        # add participants first because referenced by other parts
        stepCount = 0
        if self.addParticipants:
            stepCount += 1
        if self.addNewProjects:
            stepCount += 1
        if self.addToExisting:
            stepCount += 1
        if self.deleteExisting:
            stepCount += 1
        if self.updateExisting:
            stepCount += 1
        cStep = 0
        # add participants
        if self.addParticipants:
            cStep += 1
            self.pbAllProgress.setValue(cStep/float(stepCount)*100)
            self.pbStepProgress.setValue(0)
            if self.debug == True:
                QgsMessageLog.logMessage('%s (adding participants)' % self.myself())
            self.importParticipants()
            self.pbStepProgress.setValue(80)
            self.projectFileSave()
        # add new projects and all their content
        if self.addNewProjects:
            cStep += 1
            self.pbAllProgress.setValue(cStep/float(stepCount)*100)
            self.pbStepProgress.setValue(0)
            if self.debug == True:
                QgsMessageLog.logMessage('%s (adding new projects)' % self.myself())
            self.importProjects()
            self.pbStepProgress.setValue(90)
            self.projectFileSave()
        # add to existing project
        if self.addToExisting:
            cStep += 1
            self.pbAllProgress.setValue(cStep/float(stepCount)*100)
            self.pbStepProgress.setValue(0)
            if self.debug == True:
                QgsMessageLog.logMessage('%s (adding to existing project)' % self.myself())
            self.pbStepProgress.setValue(25)
            self.importProcessAdditions()
            self.pbStepProgress.setValue(80)
            self.projectFileSave()
        # update existing
        if self.updateExisting:
            cStep += 1
            self.pbAllProgress.setValue(cStep/float(stepCount)*100)
            self.pbStepProgress.setValue(0)
            if self.debug == True:
                QgsMessageLog.logMessage('%s (updating exising project)' % self.myself())
            self.pbStepProgress.setValue(25)
            self.importProcessUpdates()
            self.pbStepProgress.setValue(90)
            self.projectFileSave()
        # delete existing
        if self.deleteExisting:
            cStep += 1
            self.pbAllProgress.setValue(cStep/float(stepCount)*100)
            self.pbStepProgress.setValue(0)
            if self.debug == True:
                QgsMessageLog.logMessage('%s (deleting from existing project)' % self.myself())
            self.pbStepProgress.setValue(25)
            self.importProcessDeletions()
            self.pbStepProgress.setValue(90)
            self.projectFileSave()
        # done reset interface
        self.pbAllProgress.setValue(0)
        self.pbStepProgress.setValue(0)
        self.transferClose()

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
            
