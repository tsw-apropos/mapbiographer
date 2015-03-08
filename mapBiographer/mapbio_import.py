# -*- coding: utf-8 -*-
"""
/***************************************************************************
 mapBiographerImport
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
import os, datetime, time
from ui_mapbio_import import Ui_dlgImportFeatures
import inspect, re

class mapBioImport(QtGui.QDialog, Ui_dlgImportFeatures):

    #
    # init method to define globals and make widget / method connections
    
    def __init__(self, iface, conn, cur, dirName):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)
        self.iface = iface
        self.conn = conn
        self.cur = cur
        self.dirName = dirName

        # debug setup
        self.debug = False
        if self.debug:
            self.myself = lambda: inspect.stack()[1][3]
            QgsMessageLog.logMessage(self.myself())

        # defaults
        self.returnState = 'no button'
        self.importDict = {}

        # connect widgets to functions
        QtCore.QObject.connect(self.tbSelectSourceFile, QtCore.SIGNAL("clicked()"), self.selectSource)
        QtCore.QObject.connect(self.pbValidate, QtCore.SIGNAL("clicked()"), self.validateInputs)
        QtCore.QObject.connect(self.pbImport, QtCore.SIGNAL("clicked()"), self.runImport)
        QtCore.QObject.connect(self.pbCancel, QtCore.SIGNAL("clicked()"), self.cancelImport)
        QtCore.QObject.connect(self.lwANFields, QtCore.SIGNAL("itemSelectionChanged()"), self.setNoteFieldActions)
        QtCore.QObject.connect(self.lwNFields, QtCore.SIGNAL("itemSelectionChanged()"), self.setNoteFieldActions)
        QtCore.QObject.connect(self.lwASFields, QtCore.SIGNAL("itemSelectionChanged()"), self.setSectionFieldActions)
        QtCore.QObject.connect(self.lwSFields, QtCore.SIGNAL("itemSelectionChanged()"), self.setSectionFieldActions)
        QtCore.QObject.connect(self.tbAddNoteField, QtCore.SIGNAL("clicked()"), self.addNoteField)
        QtCore.QObject.connect(self.tbRemoveNoteField, QtCore.SIGNAL("clicked()"), self.removeNoteField)
        QtCore.QObject.connect(self.tbAddSectionField, QtCore.SIGNAL("clicked()"), self.addSectionField)
        QtCore.QObject.connect(self.tbRemoveSectionField, QtCore.SIGNAL("clicked()"), self.removeSectionField)
        # disable import when these things change
        QtCore.QObject.connect(self.cbSectionCode, QtCore.SIGNAL("currentIndexChanged(int)"), self.disableImport)
        QtCore.QObject.connect(self.cbPrimaryCode, QtCore.SIGNAL("currentIndexChanged(int)"), self.disableImport)
        QtCore.QObject.connect(self.cbSecurity, QtCore.SIGNAL("currentIndexChanged(int)"), self.disableImport)
        QtCore.QObject.connect(self.cbContentCodes, QtCore.SIGNAL("currentIndexChanged(int)"), self.disableImport)
        QtCore.QObject.connect(self.cbTags, QtCore.SIGNAL("currentIndexChanged(int)"), self.disableImport)
        QtCore.QObject.connect(self.cbDatesTimes, QtCore.SIGNAL("currentIndexChanged(int)"), self.disableImport)
        QtCore.QObject.connect(self.cbTimeOfYear, QtCore.SIGNAL("currentIndexChanged(int)"), self.disableImport)

        # clear controls and enter basic defaults
        self.cbPrimaryCode.clear()
        self.cbPrimaryCode.addItem('--None--')
        self.cbSectionCode.clear()
        self.cbSectionCode.addItem('--Create On Import--')
        self.cbSecurity.clear()
        self.cbSecurity.addItem('--None--')
        self.cbContentCodes.clear()
        self.cbContentCodes.addItem('--None--')
        self.cbTags.clear()
        self.cbTags.addItem('--None--')
        self.cbDatesTimes.clear()
        self.cbDatesTimes.addItem('--None--')
        self.cbTimeOfYear.clear()
        self.cbTimeOfYear.addItem('--None--')
        self.lwANFields.clear()
        self.lwNFields.clear()
        self.lwASFields.clear()
        self.lwSFields.clear()

        # disable import button
        self.pbImport.setDisabled(True)

    #
    # disable import button

    def disableImport(self):

        self.pbImport.setDisabled(True)

    #
    # select source file and populate controls

    def selectSource(self):

        self.importDict = {}
        fname = QtGui.QFileDialog.getOpenFileName(self, 'Select Shapefile', '.', '*.shp')
        if os.path.exists(fname):
            self.leSourceFile.setText(fname)
            # open layer
            self.inputLayer = QgsVectorLayer(fname, 'input', 'ogr')
            # get field names
            fields = self.inputLayer.dataProvider().fields().toList()
            x = 0
            self.fieldDict = {}
            for field in fields:
                self.fieldDict[field.name()] = [x,field.typeName()]
                if field.typeName() == 'String':
                    self.cbPrimaryCode.addItem(field.name())
                    self.cbSectionCode.addItem(field.name())
                    self.cbSecurity.addItem(field.name())
                    self.cbContentCodes.addItem(field.name())
                    self.cbTags.addItem(field.name())
                    self.cbTimeOfYear.addItem(field.name())
                    self.lwANFields.addItem(field.name())
                    self.lwASFields.addItem(field.name())
                    self.cbDatesTimes.addItem(field.name())
                elif field.typeName() == 'Integer':
                    self.cbSectionCode.addItem(field.name())
                elif field.typeName() == 'Real':
                    self.cbSectionCode.addItem(field.name())
                x += 1
            self.pbValidate.setEnabled(True)
        self.disableImport()

    #
    # validate inputs

    def validateInputs(self):

        features = self.inputLayer.getFeatures()
        sql = "SELECT content_codes FROM project"
        rs = self.cur.execute(sql)
        codeList = rs.fetchall()[0][0].split('\n')
        validCodeList = []
        for code in codeList:
            validCodeList.append(code.split('=')[0].strip())
        # validate primary code values
        validContent = True
        if self.cbPrimaryCode.currentText() <> '--None--':
            idx = self.fieldDict[self.cbPrimaryCode.currentText()][0]
            problemContent = []
            for feature in features:
                attrs = feature.attributes()
                if not str(attrs[idx]) in validCodeList:
                    if not str(attrs[idx]) in problemContent:
                        problemContent.append(str(attrs[idx]))
            if len(problemContent) > 0:
                validContent = False
        # validate security values
        validSecurity = True
        if self.cbSecurity.currentText() <> '--None--':
            idx = self.fieldDict[self.cbSecurity.currentText()][0]
            problemSecurity = []
            for feature in features:
                attrs = feature.attributes()
                if not str(attrs[idx]) in ['PU','CO','PR']:
                    if not str(attrs[idx]) in problemSecurity:
                        problemSecurity.append(str(attrs[idx]))
            if len(problemSecurity) > 0:
                validSecurity = False
        # validate content code values
        validCodes = True
        if self.cbContentCodes.currentText() <> '--None--':
            idx = self.fieldDict[self.cbTags.currentText()][0]
            problemCodes = []
            for feature in features:
                attrs = feature.attributes()
                featCodes = str(attrs[idx]).split(',')
                for code in featCodes:
                    if not code.strip() in validCodeList:
                        if not str(attrs[idx]) in problemCodes:
                            problemCodes.append(tag.strip())
            if len(problemCodes) > 0:
                validCodes = False
        # validate date times
        validDatesTimes = True
        if self.cbDatesTimes.currentText() <> '--None--':
            # get reference info
            validDatesTimesList = ['R','U','N']
            sql = "SELECT dates_and_times FROM project"
            rs = self.cur.execute(sql)
            codeList = rs.fetchall()[0][0].split('\n')
            for code in codeList:
                validDatesTimesList.append(code.split('=')[0].strip())
            # check import source
            idx = self.fieldDict[self.cbUsePeriod.currentText()][0]
            problemDatesTimes = []
            for feature in features:
                attrs = feature.attributes()
                if not str(attrs[idx]) in validDatesTimesList:
                    if not str(attrs[idx]) in problemDatesTimes:
                        problemDatesTimes.append(str(attrs[idx]))
            if len(problemDatesTimes) > 0:
                validDatesTimes = False
        # validate time of year
        validTimeOfYear = True
        if self.cbTimeOfYear.currentText() <> '--None--':
            # get reference info
            validTimeOfYearList = ['R','U','N','SP','SE','Y']
            sql = "SELECT times_of_year FROM project"
            rs = self.cur.execute(sql)
            codeList = rs.fetchall()[0][0].split('\n')
            for code in codeList:
                validTimeOfYearList.append(code.split('=')[0].strip())
            # check import source
            idx = self.fieldDict[self.cbTimeOfYear.currentText()][0]
            problemTimeOfYear = []
            for feature in features:
                attrs = feature.attributes()
                if not str(attrs[idx]) in validTimeOfYearList:
                    if not str(attrs[idx]) in problemTimeOfYear:
                        problemTimeOfYear.append(str(attrs[idx]))
            if len(problemTimeOfYear) > 0:
                validTimeOfYear = False
        # write report
        fname = os.path.join(self.dirName,datetime.datetime.now().isoformat()[:-16]+'lmb_import_validation.log')
        f = open(fname,'w')
        problemsExist = False
        if validContent:
            f.write('Primary code valid or unused\n')
        else:
            problemsExist = True
            f.write('Invalid primary code values in field %s:\n' % self.cbPrimaryCode.currentText())
            for code in problemContent:
                f.write(code + '\n')
        f.write('\n')
        if validSecurity:
            f.write('Security codes valid or unused\n')
        else:
            problemsExist = True
            f.write('Invalid security code values in field %s:\n' % self.cbSecurity.currentText())
            for code in problemSecurity:
                f.write(code + '\n')
        f.write('\n')
        if validCodes:
            f.write('Content codes valid or unused\n')
        else:
            problemsExist = True
            f.write('Invalid content code values in field %s:\n' % self.cbContentCodes.currentText())
            for code in problemTags:
                f.write(code + '\n')
        f.write('\n')
        if validDatesTimes:
            f.write('Dates and Times valid or unused\n')
        else:
            problemsExist = True
            f.write('Invalid date and times values in field %s:\n' % self.cbDatesTimes.currentText())
            for code in problemUsePeriods:
                f.write(code + '\n')
        f.write('\n')
        if validTimeOfYear:
            f.write('Time of year valid or unused\n')
        else:
            problemsExist = True
            f.write('Invalid time of year values in field %s:\n' % self.cbTimeOfYear.currentText())
            for code in problemTimeOfYear:
                f.write(code + '\n')
        f.close()
        if problemsExist:
            warningText = "Problems were identified with the selected inputs."
            warningText += "Please see the following file for details: \n %s\n" % fname
            warningText += 'Can not proceed with import'
            QtGui.QMessageBox.warning(self, 'Invalid Values',
                    warningText, QtGui.QMessageBox.Ok)
        else:
            self.pbImport.setEnabled(True)

    #
    # set note field actions

    def setNoteFieldActions(self):

        if self.lwANFields.currentRow() <> -1:
            self.tbAddNoteField.setEnabled(True)
        else:
            self.tbAddNoteField.setDisabled(True)
        if self.lwNFields.currentRow() <> -1:
            self.tbRemoveNoteField.setEnabled(True)
        else:
            self.tbRemoveNoteField.setDisabled(True)

    #
    # set section field actions

    def setSectionFieldActions(self):

        if self.lwASFields.currentRow() <> -1:
            self.tbAddSectionField.setEnabled(True)
        else:
            self.tbAddSectionField.setDisabled(True)
        if self.lwSFields.currentRow() <> -1:
            self.tbRemoveSectionField.setEnabled(True)
        else:
            self.tbRemoveSectionField.setDisabled(True)

    #
    # add note field

    def addNoteField(self):

        nNText = self.lwANFields.currentItem().text()
        self.lwNFields.addItem(nNText)
        self.lwANFields.takeItem(self.lwANFields.currentRow())
        self.disableImport()

    #
    # remove note field

    def removeNoteField(self):

        nText = self.lwNFields.currentItem().text()
        self.lwANFields.addItem(nText)
        self.lwNFields.takeItem(self.lwNFields.currentRow())
        self.disableImport()

    #
    # add section field

    def addSectionField(self):

        nSText = self.lwASFields.currentItem().text()
        self.lwSFields.addItem(nSText)
        self.lwASFields.takeItem(self.lwASFields.currentRow())
        self.disableImport()

    #
    # remove section field

    def removeSectionField(self):

        sText = self.lwSFields.currentItem().text()
        self.lwASFields.addItem(sText)
        self.lwSFields.takeItem(self.lwSFields.currentRow())
        self.disableImport()

    #
    # if import clicked notify and return dictionary of required info for import process

    def runImport(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
            
        inputLayer = None
        self.importDict = {}
        self.importDict['source'] = self.leSourceFile.text()
        self.importDict['primaryCode'] = self.cbPrimaryCode.currentText()
        self.importDict['sectionCode'] = self.cbSectionCode.currentText()
        self.importDict['security'] = self.cbSecurity.currentText()
        self.importDict['contentCodes'] = self.cbContentCodes.currentText()
        self.importDict['tags'] = self.cbTags.currentText()
        self.importDict['datesTimes'] = self.cbDatesTimes.currentText()
        self.importDict['timeOfYear'] = self.cbTimeOfYear.currentText()
        self.importDict['notes'] = ''
        cnt = self.lwNFields.count()
        for x in range(cnt):
            self.importDict['notes'] = self.importDict['notes'] + self.lwNFields.item(x).text() + ','
        if len(self.importDict['notes']) > 0:
            self.importDict['notes'] = self.importDict['notes'][:-1]
        self.importDict['sections'] = ''
        cnt = self.lwSFields.count()
        for x in range(cnt):
            self.importDict['sections'] = self.importDict['sections'] + self.lwSFields.item(x).text() + ','
        if len(self.importDict['sections']) > 0:
            self.importDict['sections'] = self.importDict['sections'][:-1]
        if self.cbSpatialDataSource.currentIndex() == 0:
            self.importDict['spatialDataSource'] = 'PM'
        elif self.cbSpatialDataSource.currentIndex() == 1:
            self.importDict['spatialDataSource'] = 'OS'
        elif self.cbSpatialDataSource.currentIndex() == 2:
            self.importDict['spatialDataSource'] = 'HG'
        elif self.cbSpatialDataSource.currentIndex() == 3:
            self.importDict['spatialDataSource'] = 'CG'
        self.importDict['spatialDataScale'] = str(self.spbxSpatialDataScale.value())
        self.close()

    #
    # return data

    def returnData(self):
        return(self.importDict)

    #
    # if cancel clicked notify and return blank dictionary

    def cancelImport(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        self.close()

    
