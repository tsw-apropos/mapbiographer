# -*- coding: utf-8 -*-
"""
/***************************************************************************
 mapBiographerImporter
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
import os, datetime, time, inspect, re
from ui_mapbio_importer import Ui_mapbioImporter

class mapBiographerImporter(QtGui.QDialog, Ui_mapbioImporter):

    #
    #####################################################
    #                basic functionality                #
    #####################################################
    #
    #
    # init method to define globals and make widget / method connections
    #
    def __init__(self, iface, projDict, intvDict, dirName, optionalFields, customFields, lastDir):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)
        self.iface = iface
        self.dirName = dirName
        self.projDict = projDict
        self.intvDict = intvDict
        self.lastDir = lastDir
        self.optionalFields = optionalFields
        self.customFields = customFields
        self.setModal(True)
        
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
        QtCore.QObject.connect(self.cbSuggestFields, QtCore.SIGNAL("stateChanged(int)"), self.suggestFields)
        # disable import when these things change
        QtCore.QObject.connect(self.cbLegacyCode, QtCore.SIGNAL("currentIndexChanged(int)"), self.disableImport)
        QtCore.QObject.connect(self.cbSectionCode, QtCore.SIGNAL("currentIndexChanged(int)"), self.disableImport)
        QtCore.QObject.connect(self.cbPrimaryCode, QtCore.SIGNAL("currentIndexChanged(int)"), self.disableImport)
        QtCore.QObject.connect(self.cbSequence, QtCore.SIGNAL("currentIndexChanged(int)"), self.disableImport)
        QtCore.QObject.connect(self.cbSecurity, QtCore.SIGNAL("currentIndexChanged(int)"), self.disableImport)
        QtCore.QObject.connect(self.cbContentCodes, QtCore.SIGNAL("currentIndexChanged(int)"), self.disableImport)
        QtCore.QObject.connect(self.cbTags, QtCore.SIGNAL("currentIndexChanged(int)"), self.disableImport)
        QtCore.QObject.connect(self.cbRecordingDate, QtCore.SIGNAL("currentIndexChanged(int)"), self.disableImport)
        QtCore.QObject.connect(self.cbUsePeriod, QtCore.SIGNAL("currentIndexChanged(int)"), self.disableImport)
        QtCore.QObject.connect(self.cbTimeOfYear, QtCore.SIGNAL("currentIndexChanged(int)"), self.disableImport)
        # 
        self.customFieldsConfigure()
        self.clearFieldLists()
        # disable import button
        self.pbImport.setDisabled(True)

    #
    # extend show event
    #
    def show(self):
        QtGui.QDialog.show(self)
        self.selectSource()
    #
    # disable import button
    #
    def disableImport(self):

        self.pbImport.setDisabled(True)

    #
    # clear comboboxes
    #
    def clearFieldLists(self):
        # clear controls and enter basic defaults
        self.cbPrimaryCode.clear()
        self.cbPrimaryCode.addItem('--None--')
        self.cbSequence.clear()
        self.cbSequence.addItem('--None--')
        self.cbLegacyCode.clear()
        self.cbLegacyCode.addItem('--None--')
        self.cbSpatialRef.clear()
        self.cbSpatialRef.addItem('--None--')
        self.cbSectionCode.clear()
        self.cbSectionCode.addItem('--Create On Import--')
        self.cbSecurity.clear()
        self.cbSecurity.addItem('--None--')
        self.cbContentCodes.clear()
        self.cbContentCodes.addItem('--None--')
        self.cbTags.clear()
        self.cbTags.addItem('--None--')
        self.cbRecordingDate.clear()
        self.cbRecordingDate.addItem('--None--')
        self.cbUsePeriod.clear()
        self.cbUsePeriod.addItem('--None--')
        self.cbTimeOfYear.clear()
        self.cbTimeOfYear.addItem('--None--')
        self.lwANFields.clear()
        self.lwNFields.clear()
        self.lwASFields.clear()
        self.lwSFields.clear()
        self.customFieldsClearFieldLists()

    #
    # select source file and populate controls
    #
    def selectSource(self):

        self.importDict = {}
        fname = QtGui.QFileDialog.getOpenFileName(self, 'Select Shapefile or GeoJSON file', self.lastDir, '*.shp *.geojson')
        self.lastDir, temp = os.path.split(fname)
        if os.path.exists(fname):
            self.leSourceFile.setText(fname)
            # open layer
            self.inputLayer = QgsVectorLayer(fname, 'input', 'ogr')
            # get field names
            fields = self.inputLayer.dataProvider().fields().toList()
            x = 0
            self.fieldDict = {}
            self.clearFieldLists()
            for field in fields:
                self.fieldDict[field.name()] = [x,field.typeName()]
                if field.typeName() == 'String':
                    self.cbPrimaryCode.addItem(field.name())
                    self.cbLegacyCode.addItem(field.name())
                    self.cbSectionCode.addItem(field.name())
                    self.cbSpatialRef.addItem(field.name())
                    self.cbSecurity.addItem(field.name())
                    self.cbContentCodes.addItem(field.name())
                    self.cbTags.addItem(field.name())
                    if self.cbTimeOfYear.isVisible() == True:
                        self.cbTimeOfYear.addItem(field.name())
                    self.lwANFields.addItem(field.name())
                    self.lwASFields.addItem(field.name())
                    if self.cbUsePeriod.isVisible == True:
                        self.cbUsePeriod.addItem(field.name())
                    self.cbRecordingDate.addItem(field.name())
                elif field.typeName() in ('Integer','Integer64'):
                    self.cbLegacyCode.addItem(field.name())
                    self.cbSequence.addItem(field.name())
                elif field.typeName() == 'Real':
                    self.cbLegacyCode.addItem(field.name())
                elif field.typeName() == 'Date':
                    self.cbRecordingDate.addItem(field.name())
                self.customFieldsPopulate(field)
                x += 1
            self.pbValidate.setEnabled(True)
        self.disableImport()
        self.suggestFields()

    #
    # suggest fields
    #
    def suggestFields(self):
        
        if self.cbSuggestFields.isChecked() and self.pbValidate.isEnabled():
            # legacy code
            for i in range(self.cbLegacyCode.count()):
                if self.cbLegacyCode.itemText(i).lower() in ('legacycode','legcode','lcode'):
                    self.cbLegacyCode.setCurrentIndex(i)
                    break
            # section code
            for i in range(self.cbSectionCode.count()):
                if self.cbSectionCode.itemText(i).lower() in ('sectioncode','sectncode','scode'):
                    self.cbSectionCode.setCurrentIndex(i)
                    break
            # spatial reference
            for i in range(self.cbSpatialRef.count()):
                if self.cbSpatialRef.itemText(i).lower() in ('spatialreference','spatialref','sref'):
                    self.cbSpatialRef.setCurrentIndex(i)
                    break
            # primary code
            for i in range(self.cbPrimaryCode.count()):
                if self.cbPrimaryCode.itemText(i).lower() in ('primarycode','primcode','pcode'):
                    self.cbPrimaryCode.setCurrentIndex(i)
                    break
            # sequence
            for i in range(self.cbSequence.count()):
                if self.cbSequence.itemText(i).lower() in ('sequence','newseq','seq'):
                    self.cbSequence.setCurrentIndex(i)
                    break
            # security code
            for i in range(self.cbSecurity.count()):
                if self.cbSecurity.itemText(i).lower() in ('securitycode','security','sectycode'):
                    self.cbSecurity.setCurrentIndex(i)
                    break
            # content codes
            for i in range(self.cbContentCodes.count()):
                if self.cbContentCodes.itemText(i).lower() in ('contentcodes','contcodes','ccodes'):
                    self.cbContentCodes.setCurrentIndex(i)
                    break
            # tags
            for i in range(self.cbTags.count()):
                if self.cbTags.itemText(i).lower() in ('tags','sectntags'):
                    self.cbTags.setCurrentIndex(i)
                    break
            # recording datetime
            for i in range(self.cbRecordingDate.count()):
                if self.cbRecordingDate.itemText(i).lower() in ('intvdate','recordingdate','recdate'):
                    self.cbRecordingDate.setCurrentIndex(i)
                    break
            # use period
            for i in range(self.cbUsePeriod.count()):
                if self.cbUsePeriod.itemText(i).lower() in ('useperiod','uperiod'):
                    self.cbUsePeriod.setCurrentIndex(i)
                    break
            # time of year
            for i in range(self.cbTimeOfYear.count()):
                if self.cbTimeOfYear.itemText(i).lower() in ('timeofyear','timeyear','toy'):
                    self.cbTimeOfYear.setCurrentIndex(i)
                    break
            # time of year
            for i in range(self.cbTimeOfYear.count()):
                if self.cbTimeOfYear.itemText(i).lower() in ('timeofyear','timeyear','toy'):
                    self.cbTimeOfYear.setCurrentIndex(i)
                    break
            # clear notes and section selections
            self.lwANFields.clear()
            self.lwNFields.clear()
            self.lwASFields.clear()
            self.lwSFields.clear()            
            fields = self.inputLayer.dataProvider().fields().toList()
            fNList = []
            for field in fields:
                if field.typeName() == 'String':
                    self.lwANFields.addItem(field.name())
                    self.lwASFields.addItem(field.name())
                    fNList.append(field.name())
            # note
            for i in range(len(fNList)):
                if fNList[i] in ('note','notes'):
                    self.lwANFields.setCurrentItem(self.lwANFields.item(i))
                    self.addNoteField()
                    break
            # section text
            for i in range(len(fNList)):
                if fNList[i] in ('sectiontext','sectext'):
                    self.lwASFields.setCurrentItem(self.lwASFields.item(i))
                    self.addSectionField()
                    break
            # custom fields
            for wi in self.customWidgets:
                for i in range(wi['widget'].count()):
                    if wi['widget'].itemText(i) == wi['code']:
                        wi['widget'].setCurrentIndex(i)
                        break

    #
    # validate inputs
    #
    def validateInputs(self):

        features = self.inputLayer.getFeatures()
        codeList = self.projDict["default_codes"]
        validCodeList = []
        for code in codeList:
            validCodeList.append(code[0])
        # validate section code values
        validSection = True
        validContent = True
        validSecurity = True
        validCodes = True
        validUsePeriod = True
        validTimeOfYear = True
        validRecordingDate = True
        validSpatialRef = True
        validCustomFields = True
        # get reference info
        validUsePeriodList = ['R','U','N']
        codeList = self.projDict["default_time_periods"]
        for code in codeList:
            validUsePeriodList.append(code[0])
        validTimeOfYearList = ['R','U','N','SP']
        codeList = self.projDict["default_time_of_year"]
        for code in codeList:
            validTimeOfYearList.append(code[0])
        # get field indexes
        if self.cbSectionCode.currentText() <> '--Create On Import--':
            SectionIdx = self.fieldDict[self.cbSectionCode.currentText()][0]
        else:
            SectionIdx = -1
        if self.cbPrimaryCode.currentText() <> '--None--':
            PrimaryIdx = self.fieldDict[self.cbPrimaryCode.currentText()][0]
        else:
            PrimaryIdx = -1
        if self.cbSequence.currentText() <> '--None--':
            SequenceIdx = self.fieldDict[self.cbSequence.currentText()][0]
        else:
            SequenceIdx = -1
        if self.cbSecurity.currentText() <> '--None--':
            SecurityIdx = self.fieldDict[self.cbSecurity.currentText()][0]
        else:
            SecurityIdx = -1
        if self.cbContentCodes.currentText() <> '--None--':
            ContentIdx = self.fieldDict[self.cbContentCodes.currentText()][0]
        else:
            ContentIdx = -1
        if self.cbUsePeriod.currentText() <> '--None--':
            UsePeriodIdx = self.fieldDict[self.cbUsePeriod.currentText()][0]
        else:
            UsePeriodIdx = -1
        if self.cbTimeOfYear.currentText() <> '--None--':
            TimeOfYearIdx = self.fieldDict[self.cbTimeOfYear.currentText()][0]
        else:
            TimeOfYearIdx = -1
        if self.cbRecordingDate.currentText() <> '--None--':
            RecordingDateIdx = self.fieldDict[self.cbRecordingDate.currentText()][0]
        else:
            RecordingDateIdx = -1
        if self.cbSpatialRef.currentText() <> '--None--':
            SpatialRefIdx = self.fieldDict[self.cbSpatialRef.currentText()][0]
        else:
            SpatialRefIdx = -1
        # create lists to record problems
        problemSections = []
        problemContent = []
        problemSecurity = []
        problemCodes = []
        problemUsePeriod = []
        problemTimeOfYear = []
        problemRecordingDate = []
        problemSpatialRef = []
        sectionCodeList = []
        spatialRefList = []
        problemCustomFields = []
        # step through features and identify problems
        for feature in features:
            attrs = feature.attributes()
            if SectionIdx <> -1:
                testVal = re.findall(r'\D+', str(attrs[SectionIdx]))[0]
                if not testVal in validCodeList:
                    problemSections.append(str(attrs[SectionIdx]))
            if PrimaryIdx <> -1:
                testVal = str(attrs[PrimaryIdx])
                if not testVal in validCodeList:
                    if not testVal in problemContent:
                        problemContent.append(testVal)
            if SecurityIdx <> -1:
                testVal = str(attrs[SecurityIdx])
                if not testVal in ['PU','CO','PR']:
                    if not testVal in problemSecurity:
                        problemSecurity.append(testVal)
            if ContentIdx <> -1:
                featCodes = str(attrs[ContentIdx]).split(',')
                for code in featCodes:
                    if not code.strip() in validCodeList:
                        if not code.strip() in problemCodes:
                            problemCodes.append(code.strip())
            if UsePeriodIdx <> -1:
                testVal = str(attrs[UsePeriodIdx])
                if not testVal in validUsePeriodList:
                    # test if correct format for custom use period
                    testList = testVal.split(':')
                    if len(testList) == 2:
                        notValidDates = False
                        try:
                            sDate = datetime.datetime.strptime(tv[0].strip(), "%Y-%m-%d")
                            eDate = datetime.datetime.strptime(tv[1].strip(), "%Y-%m-%d")
                            if sDate > eDate:
                                notValidDates = True
                        except:
                            notValidDates = True
                    else:
                        notValidDates = True
                    if notValidDates and not testVal in problemUsePeriod:
                        problemUsePeriod.append(testVal)
            if TimeOfYearIdx <> -1:
                testVal = str(attrs[TimeOfYearIdx])
                if not testVal in validTimeOfYearList:
                    # test if correct format for custom time of year
                    testList = testVal.split(',')
                    notValidMonth = False
                    for tv in testList:
                        try:
                            if int(tv) < 0 and int(tv) > 12:
                                notValidMonth = True
                        except:
                            notValidMonth = True
                    if notValidMonth and not testVal in problemTimeOfYear:
                        problemTimeOfYear.append(testVal)
            if RecordingDateIdx <> -1:
                try:
                    testVal = str(attrs[RecordingDateIdx])
                    tDate = datetime.datetime.strptime(testVal, "%Y-%m-%d %H:%M")
                except:
                    try:
                        tDate = datetime.datetime.strptime(testVal, "%Y-%m-%d")
                    except:
                        try:
                            tDate = datetime.datetime.strptime(testVal, "%Y%m%d")
                        except:
                            try:
                                testVal = attrs[RecordingDateIdx]
                                if isinstance(testVal, QtCore.QDate) or isinstance(testVal, QtCore.QDateTime):
                                    pass
                                else:
                                    raise
                            except:
                                testVal = attrs[RecordingDateIdx]
                                if not testVal is None and not isinstance(testVal, QtCore.QPyNullVariant):
                                    problemRecordingDate.append(testVal)
            if SpatialRefIdx <> -1:
                # record values and section code list for comparison
                sectionCodeList.append(str(attrs[SectionIdx]))
                spatialRefList.append(str(attrs[SpatialRefIdx]))
            status,errors = self.customFieldsValidate(attrs)
            if status == True:
                for err in errors:
                    problemCustomFields.append(err)
        if SpatialRefIdx <> -1:
            # compare to see if problems exist
            for spatialRef in spatialRefList:
                if not (spatialRef.lower().strip() in ('pt','ln','pl','') or spatialRef in sectionCodeList):
                    problemSpatialRef.append(spatialRef)
        # assess and report
        problemsExist = False
        fname = os.path.join(self.dirName,datetime.datetime.now().isoformat()[:-16]+'lmb_import_validation.log')
        f = open(fname,'w')
        if len(problemSections) == 0:
            f.write('Section codes valid or unused\n')
        else:
            problemsExist = True
            f.write('Invalid section codes values in field %s:\n' % self.cbSectionCode.currentText())
            for code in problemSections:
                f.write(code + '\n')
        f.write('\n')
        if len(problemContent) == 0:
            f.write('Primary code valid or unused\n')
        else:
            problemsExist = True
            f.write('Invalid primary code values in field %s:\n' % self.cbPrimaryCode.currentText())
            for code in problemContent:
                f.write(code + '\n')
        f.write('\n')
        if len(problemSecurity) == 0:
            f.write('Security codes valid or unused\n')
        else:
            problemsExist = True
            f.write('Invalid security code values in field %s:\n' % self.cbSecurity.currentText())
            for code in problemSecurity:
                f.write(code + '\n')
        f.write('\n')
        if len(problemCodes) == 0:
            f.write('Content codes valid or unused\n')
        else:
            problemsExist = True
            f.write('Invalid content code values in field %s:\n' % self.cbContentCodes.currentText())
            for code in problemCodes:
                f.write(code + '\n')
        f.write('\n')
        if len(problemUsePeriod) == 0:
            f.write('Use period valid or unused\n')
        else:
            problemsExist = True
            f.write('Invalid use period values in field %s:\n' % self.cbUsePeriod.currentText())
            for code in problemUsePeriod:
                f.write(code + '\n')
        f.write('\n')
        if len(problemTimeOfYear) == 0:
            f.write('Time of year valid or unused\n')
        else:
            problemsExist = True
            f.write('Invalid time of year values in field %s:\n' % self.cbTimeOfYear.currentText())
            for code in problemTimeOfYear:
                f.write(code + '\n')
        f.write('\n')
        if len(problemRecordingDate) == 0:
            f.write('Recording date valid or unused\n')
        else:
            problemsExist = True
            f.write('Invalid recording date values in field %s.\n' % self.cbRecordingDate.currentText())
            f.write('Must be text field formatted as YYYY-MM-DD HH:MM or YYYY-MM-DD or date field.\nProblems values were:\n')
            for code in problemRecordingDate:
                f.write(code + '\n')
        if len(problemSpatialRef) == 0:
            f.write('Spatial reference valid or unused\n')
        else:
            problemsExist = True
            f.write('Invalid spatial reference values in field %s.\n' % self.cbSpatialRef.currentText())
            for code in problemSpatialRef:
                f.write(code + '\n')
        if len(problemCustomFields) == 0:
            f.write('Custom field values valid or unused.\n')
        else:
            problemsExist = True
            f.write('Invalid custom field values.\n')
            for code in problemCustomFields:
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
    #
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
    #
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
    #
    def addNoteField(self):

        nNText = self.lwANFields.currentItem().text()
        self.lwNFields.addItem(nNText)
        self.lwANFields.takeItem(self.lwANFields.currentRow())
        self.disableImport()

    #
    # remove note field
    #
    def removeNoteField(self):

        nText = self.lwNFields.currentItem().text()
        self.lwANFields.addItem(nText)
        self.lwNFields.takeItem(self.lwNFields.currentRow())
        self.disableImport()

    #
    # add section field
    #
    def addSectionField(self):

        nSText = self.lwASFields.currentItem().text()
        self.lwSFields.addItem(nSText)
        self.lwASFields.takeItem(self.lwASFields.currentRow())
        self.disableImport()

    #
    # remove section field
    #
    def removeSectionField(self):

        sText = self.lwSFields.currentItem().text()
        self.lwASFields.addItem(sText)
        self.lwSFields.takeItem(self.lwSFields.currentRow())
        self.disableImport()

    #
    # if import clicked notify and return dictionary of required info for import process
    #
    def runImport(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
            
        inputLayer = None
        self.importDict = {}
        self.importDict['source'] = self.leSourceFile.text()
        self.importDict['legacyCode'] = self.cbLegacyCode.currentText()
        self.importDict['sectionCode'] = self.cbSectionCode.currentText()
        self.importDict['spatialRef'] = self.cbSpatialRef.currentText()
        self.importDict['primaryCode'] = self.cbPrimaryCode.currentText()
        self.importDict['sequence'] = self.cbSequence.currentText()
        self.importDict['security'] = self.cbSecurity.currentText()
        self.importDict['contentCodes'] = self.cbContentCodes.currentText()
        self.importDict['tags'] = self.cbTags.currentText()
        self.importDict['recordingDate'] = self.cbRecordingDate.currentText()
        self.importDict['usePeriod'] = self.cbUsePeriod.currentText()
        self.importDict['timeOfYear'] = self.cbTimeOfYear.currentText()
        if self.cbSpatialDataSource.currentIndex() == 0:
            self.importDict['spatialDataSource'] = 'PM'
        elif self.cbSpatialDataSource.currentIndex() == 1:
            self.importDict['spatialDataSource'] = 'OS'
        elif self.cbSpatialDataSource.currentIndex() == 2:
            self.importDict['spatialDataSource'] = 'HG'
        elif self.cbSpatialDataSource.currentIndex() == 3:
            self.importDict['spatialDataSource'] = 'CG'
        self.importDict['spatialDataScale'] = str(self.spbxSpatialDataScale.value())
        self.customFieldsAddToImportDict()
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
        self.close()

    #
    # return data
    #
    def returnData(self):
        return(self.importDict,self.lastDir)

    #
    # if cancel clicked notify and return blank dictionary
    #
    def cancelImport(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        self.close()
    
    #
    #####################################################
    #                 custom fields                     #
    #####################################################
    #
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
            rCnt = self.grFields.rowCount()
            # text box type to create option to list text fields
            # create and place label
            label = QtGui.QLabel()
            label.setText(cf['name'])
            self.grFields.addWidget(label,rCnt,0)
            label.setVisible(True)
            # create widget
            widget = QtGui.QComboBox()
            self.grFields.addWidget(widget,rCnt,1)
            widget.setVisible(True)
            # create dictionary selection, validation and import
            codes = []
            if cf['type'] == 'sl':
                argList = cf['args'].split('\n')
                for arg in argList:
                    a,b = arg.split('=')
                    codes.append(a)
            else:
                codes = ''
            self.customWidgets.append({'code':cf['code'],'label':label,'type':cf['type'],'widget':widget,'codes':codes})

    #
    # populate custom field options
    #
    def customFieldsPopulate(self,field):
        
        for wi in self.customWidgets:
            if field.typeName() == 'String' and wi['type'] in ('ta','tb','sl','dt','tm','d&t','url'):
                wi['widget'].addItem(field.name())
            elif field.typeName() in ('Integer','Integer64') and wi['type'] == 'in':
                wi['widget'].addItem(field.name())
            elif field.typeName() == 'Real' and wi['type'] == 'dm':
                wi['widget'].addItem(field.name())
            elif field.typeName() == 'Date' and wi['type'] == 'dt':
                wi['widget'].addItem(field.name())

    #
    # clear custom field field lists
    #
    def customFieldsClearFieldLists(self):
        
        for wi in self.customWidgets:
            wi['widget'].clear()
            wi['widget'].addItem('--None--')

    #
    # custom fields validate
    #
    def customFieldsValidate(self,attrs):
        
        customFieldErrors = False
        customFieldErrorList = []
        for wi in self.customWidgets:
            if wi['widget'].currentText() <> '--None--':
                cfIdx = self.fieldDict[wi['widget'].currentText()][0]
                testVal = str(attrs[cfIdx])
                if wi['type'] == 'sl':
                    testVal = str(attrs[cfIdx])
                    if testVal not in wi['codes']:
                        customFieldErrors = True
                        customFieldErrorList.append('%s with value %s' % (wi['label'],testVal))
                elif wi['type'] == 'dt':
                    try:
                        tDate = datetime.datetime.strptime(testVal, "%Y-%m-%d")
                    except:
                        try:
                            testVal = attrs[RecordingDateIdx]
                            if isinstance(testVal, QtCore.QDate) or isinstance(testVal, QtCore.QDateTime):
                                pass
                            else:
                                raise
                        except:
                            testVal = attrs[RecordingDateIdx]
                            if not testVal is None and not isinstance(testVal, QtCore.QPyNullVariant):
                                customFieldErrors = True
                                customFieldErrorList.append('%s with value %s' % (wi['label'],str(testVal)))
                elif wi['type'] == 'tm':
                    try:
                        testVal = '2000-01-01 ' + str(attrs[RecordingDateIdx])
                        tTime = datetime.datetime.strptime(testVal, "%Y-%m-%d %H:%M")
                    except:
                        try:
                            testVal = attrs[RecordingDateIdx]
                            if isinstance(testVal, QtCore.QDateTime):
                                pass
                            else:
                                raise
                        except:
                            testVal = attrs[RecordingDateIdx]
                            if not testVal is None and not isinstance(testVal, QtCore.QPyNullVariant):
                                customFieldErrors = True
                                customFieldErrorList.append('%s with value %s' % (wi['label'],str(testVal)))
                elif wi['type'] == 'd&t':
                    try:
                        testVal = str(attrs[RecordingDateIdx])
                        tDate = datetime.datetime.strptime(testVal, "%Y-%m-%d %H:%M")
                    except:
                        try:
                            testVal = attrs[RecordingDateIdx]
                            if isinstance(testVal, QtCore.QDateTime):
                                pass
                            else:
                                raise
                        except:
                            testVal = attrs[RecordingDateIdx]
                            if not testVal is None and not isinstance(testVal, QtCore.QPyNullVariant):
                                customFieldErrors = True
                                customFieldErrorList.append('%s with value %s' % (wi['label'],str(testVal)))
        return(customFieldErrors,customFieldErrorList)

    #
    # custom fields add to import dictionary
    #
    def customFieldsAddToImportDict(self):

        cf = {}
        for wi in self.customWidgets:
            cf[wi['code']] = [wi['widget'].currentText(),wi['type']]
        self.importDict['lmb-custom-fields'] = cf
