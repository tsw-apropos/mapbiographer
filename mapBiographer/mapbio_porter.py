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
        self.debug = True
        if self.debug:
            self.myself = lambda: inspect.stack()[1][3]
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
            self.lblURL.setVisible(True)
            self.leURL.setVisible(True)
        else:
            self.lblURL.setVisible(False)
            self.leURL.setVisible(False)

        # connect widgets to functions
        QtCore.QObject.connect(self.pbClose, QtCore.SIGNAL("clicked()"), self.transferClose)
        QtCore.QObject.connect(self.pbTransfer, QtCore.SIGNAL("clicked()"), self.transferRun)
        QtCore.QObject.connect(self.cbTransferAction, QtCore.SIGNAL("currentIndexChanged(int)"), self.actionSelect)
        QtCore.QObject.connect(self.pbImport, QtCore.SIGNAL("clicked()"), self.importPerform)
        QtCore.QObject.connect(self.pbUpload, QtCore.SIGNAL("clicked()"), self.uploadPerform)

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
            # download new interviews
            self.pbTransfer.setEnabled(True)
            self.frHeritageLogin.setVisible(True)
            self.frHeritageInfo.setVisible(False)
            self.frProgress.setVisible(True)
            self.resize(500, 350)
        elif self.actionIdx == 4:
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
    # execute tranfer action
    #
    def transferRun(self):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        # disable actions
        self.interfaceDisable()
        # check if downloading or uploading
        if self.actionIdx in (3,4) and (self.leUserName.text() == '' or self.lePassword.text() == ''):
            QtGui.QMessageBox.information(self, 'Information',
               "Your must provide user and password information for direct upload or download!", QtGui.QMessageBox.Ok)
            self.interfaceEnable()
        else:
            if self.actionIdx == 3:
                self.importToLMB()
            elif self.actionIdx == 4:
                self.exportToHeritage()
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
        #QgsMessageLog.logMessage(messageText)
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
    # Heritage Interactions
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
            req = urllib2.Request(url,data)
            response = urllib2.urlopen(req)
            return(response.read())
        except:
            return('{"result": "error", "data": "connection error"}')
            
    #
    # connect, retrieve and import information from Heritage
    #
    def importToLMB(self):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        self.pbAllProgress.setValue(50)
        self.transferReportStatus("Getting information from Heritage")
        response = self.getHeritageJson()
        if self.debug:
            QgsMessageLog.logMessage(str(response))
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
            self.importGenerateReport()
        self.resize(500, 450)
        self.pbAllProgress.setValue(0)
        self.pbStepProgress.setValue(0)
        self.transferReportStatus("")

    #
    # generate import report
    #
    def importGenerateReport(self):
        
        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        # check for existing projects
        localProjects = []
        localProjKeys = []
        for key, value in self.projDict['projects'].iteritems():
            localProjects.append(value['code'])
            localProjKeys.append(key)
        newProjects = []
        dupProjects = []
        self.addNewProjects = False
        self.addToExisting = False
        self.addParticipants = False
        # loop through dowloaded projects and documents to assess if new
        for key, value in self.downloadDict['data']['projects'].iteritems():
            if value['code'] in localProjects:
                # not new
                idx = localProjects.index(value['code'])
                nDocList = []
                dDocList = []
                # loop through document list from download
                for dKey, dValue in self.downloadDict['data']['documents'].iteritems():
                    # check if document belongs to this project
                    if str(dValue['project_id']) == key:
                        dupFound = False
                        # loop through local documents to assess if downloaded doc is new
                        for ddKey, ddValue in self.projDict['projects'][localProjKeys[idx]]['documents'].iteritems():
                            if dValue['code'] == ddValue['code']:
                                dDocList.append(dValue['code'])
                                dupFound = True
                        if dupFound == False:
                            nDocList.append(dValue['code'])
                dupProjects.append([key,value['code'],nDocList,dDocList])
            else:
                # new
                nDocList = []
                dDocList = []
                # loop through document list from download
                for dKey, dValue in self.downloadDict['data']['documents'].iteritems():
                    # check if document belongs to this project
                    if str(dValue['project_id']) == key:
                        nDocList.append(dValue['code'])
                newProjects.append([key,value['code'],nDocList,dDocList])
        # loop through participants to assess if new
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
        # generate report
        reportText = ''
        # new projects
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
        # existing projects
        if len(dupProjects) > 0:
            appendText = "Within existing projects, the following documents can be imported:\n"
            for rec in dupProjects:
                appendText += 'Project: %s \n' % rec[1]
                if len(rec[2]) > 0:
                    self.addToExisting = True
                    appendText += '%s\n' % ", ".join(rec[2])
                else:
                    appendText += 'No documents available\n'
#            if self.addToExisting:
            reportText += appendText
            reportText += '\n'
        # new participants
        if len(nPartList) > 0:
            self.addParticipants = True
            reportText += 'The following participants can be imported:\n'
            reportText += '%s \n' % ", ".join(nPartList)
        else:
            reportText += "No new participant records are available.\n"
        if self.addToExisting or self.addNewProjects or self.addParticipants:
            self.pbImport.setEnabled(True)
        self.newProjects = newProjects
        self.dupProjects = dupProjects
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
        cStep = 0
        if self.addParticipants:
            cStep += 1
            self.pbAllProgress.setValue(cStep/float(stepCount)*100)
            self.pbStepProgress.setValue(0)
            if self.debug == True:
                QgsMessageLog.logMessage('%s (adding participants)' % self.myself())
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
            self.pbStepProgress.setValue(80)
            self.projectFileSave()
        # add new projects and their documents second
        if self.addNewProjects:
            cStep += 1
            self.pbAllProgress.setValue(cStep/float(stepCount)*100)
            self.pbStepProgress.setValue(0)
            if self.debug == True:
                QgsMessageLog.logMessage('%s (adding new projects)' % self.myself())
            # determine max project id
            maxId = 0
            for key, value in self.projDict['projects'].iteritems():
                if int(key) > maxId:
                    maxId = int(key)
            self.pbStepProgress.setValue(45)
            for key, value in self.downloadDict['data']['projects'].iteritems():
                for rec in self.newProjects:
                    if value['code'] == rec[1]:
                        maxId += 1
                        if self.debug == True:
                            QgsMessageLog.logMessage('projkey %d, code %s' % (maxId,value['code']))
                        # process tags
                        if value['tags'] == "":
                            projTags = []
                        else:
                            tagList = value['tags'].split(",")
                            projTags = [tag.strip() for tag in tagList]
                        # process codes
                        if value['default_codes'] == []:
                            defaultCodes = []
                            defCode = ""
                        else:
                            defaultCodes = []
                            for rec in value['default_codes']:
                                defaultCodes.append([rec['code'],rec['label']])
                            defCode = defaultCodes[0][0]
                        # process time periods
                        if value['default_time_periods'] == []:
                            timePeriods = []
                        else:
                            timePeriods = []
                            for rec in value['default_time_periods']:
                                timePeriods.append(['%s : %s' % (rec['start'],rec['end']),rec['label']])
                        # process times of year
                        if value['default_time_of_year_values'] == []:
                            timesOfYear = []
                        else:
                            timesOfYear = []
                            for rec in value['default_time_of_year_values']:
                                timesOfYear.append([",".join(str(x) for x in rec['months']),rec['label']])
                        # process documents
                        docDict = {}
                        intvKey = 0
                        for dKey, dValue in self.downloadDict['data']['documents'].iteritems():
                            if key == str(dValue["project_id"]):
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
                        temp = {
                            "id": maxId,
                            "code": value['code'],
                            "description": value['description'],
                            "note": value['note'],
                            "tags": projTags,
                            "citation": value['citation'],
                            "source": value['source'],
                            "default_codes": defaultCodes,
                            "default_time_periods": timePeriods,
                            "default_time_of_year": timesOfYear,
                            "ns_code": defCode,
                            "pt_code": defCode,
                            "ln_code": defCode,
                            "pl_code": defCode,
                            "lmb_map_settings": {},
                            "documents": docDict
                        }
                        self.projDict["projects"][str(maxId)] = temp
            self.pbStepProgress.setValue(90)
            self.projectFileSave()
        # add new documents to existing projects
        if self.addToExisting:
            cStep += 1
            self.pbAllProgress.setValue(cStep/float(stepCount)*100)
            self.pbStepProgress.setValue(0)
            if self.debug == True:
                QgsMessageLog.logMessage('%s (adding to existing projects)' % self.myself())
            # step through existing project list 
            self.pbStepProgress.setValue(25)
            for rec in self.dupProjects:
                # step through new documents to be added to existing projects
                for docCode in rec[2]:
                    # find the document record
                    for key, value in self.downloadDict['data']['documents'].iteritems():
                        if value['code'] == docCode:
                            # find the right project
                            projId = None
                            for ldKey, ldValue in self.projDict['projects'].iteritems():
                                if ldValue['code'] == self.downloadDict['data']['projects'][rec[0]]['code']:
                                    projId = int(ldKey)
                                    break
                            # if project found, add document to that project
                            if projId <> None:
                                # add the document to the project
                                maxDocId = 0
                                for dKey, dValue in self.projDict['projects'][str(projId)]['documents'].iteritems():
                                    if int(dKey) > maxDocId:
                                        maxDocId = int(dKey)
                                # process tags
                                if value['tags'] == "":
                                    docTags = []
                                else:
                                    tagList = value['tags'].split(",")
                                    docTags = [tag.strip() for tag in tagList]
                                # process participants
                                if value['participants'] == []:
                                    partDict = {}
                                else:
                                    partDict = {}
                                    partKey = 0
                                    # step through download dict participants record
                                    for rec in value['participants']:
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
                                    "code": value['code'],
                                    "title": value['title'],
                                    "description": value['description'],
                                    "location": value['location'],
                                    "note": value['note'],
                                    "tags": docTags,
                                    "default_data_security": value['default_data_security'],
                                    "status": value['data_status'],
                                    "creator": value['creator'],
                                    "publisher": value['publisher'],
                                    "subject": value['subject'],
                                    "language": value['language'],
                                    "source": value['source'],
                                    "citation": value['citation'],
                                    "rights_statement": value['rights_statement'],
                                    "rights_holder": value['rights_holder'],
                                    "start_datetime": value['start_datetime'],
                                    "end_datetime": value['end_datetime'],
                                    "participants": partDict
                                }
                                self.projDict['projects'][str(projId)]['documents'][str(maxDocId+1)] = temp
            self.pbStepProgress.setValue(80)
            self.projectFileSave()
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
            
    #
    # upload to heritage
    #
    def exportToHeritage(self):

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
    def uploadPerform(self):
        
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

