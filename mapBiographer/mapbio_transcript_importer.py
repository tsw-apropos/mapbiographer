# -*- coding: utf-8 -*-
"""
/***************************************************************************
 mapBiographerTranscriptImporter
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
from ui_mapbio_transcript_importer import Ui_mapbioTranscriptImporter

class mapBiographerTranscriptImporter(QtGui.QDialog, Ui_mapbioTranscriptImporter):

    #
    # init method to define globals and make widget / method connections
    
    def __init__(self, iface, projDict, intvDict, dirName):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)
        self.iface = iface
        self.dirName = dirName
        self.projDict = projDict
        self.intvDict = intvDict

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
        QtCore.QObject.connect(self.rbCreateCodes, QtCore.SIGNAL("toggled(bool)"), self.setCodes)
        QtCore.QObject.connect(self.rbUseCodes, QtCore.SIGNAL("toggled(bool)"), self.setCodes)
        QtCore.QObject.connect(self.rbMatchCodes, QtCore.SIGNAL("toggled(bool)"), self.setCodes)
        QtCore.QObject.connect(self.rbRightOfNSText, QtCore.SIGNAL("toggled(bool)"), self.disableImport)
        QtCore.QObject.connect(self.rbBelowNSText, QtCore.SIGNAL("toggled(bool)"), self.disableImport)

        # disable import button
        self.pbImport.setDisabled(True)

    #
    # disable import button

    def disableImport(self):

        self.pbImport.setDisabled(True)

    #
    # create or find codes
    
    def setCodes(self):
        
        if self.rbCreateCodes.isChecked() == True:
            self.hgbSectionCodePlacement.setDisabled(True)
        else:
            self.hgbSectionCodePlacement.setEnabled(True)
        self.disableImport()
        
    #
    # select source file and populate controls

    def selectSource(self):

        self.importDict = {}
        fname = QtGui.QFileDialog.getOpenFileName(self, 'Select text file', self.dirName, '*.txt')
        if os.path.exists(fname):
            self.leSourceFile.setText(fname)
            self.pbValidate.setEnabled(True)
        self.disableImport()

    #
    # validate inputs

    def validateInputs(self):

        # read in text file
        f = open(self.leSourceFile.text(),'r')
        textLines = [line.decode('utf-8').strip() for line in f.readlines()]
        f.close()
        # process text
        self.sectionCnt = 0
        self.sectionList = []
        self.codeList = []
        self.nsText = self.leNewSectionText.text()
        if self.rbCreateCodes.isChecked():
            findCodes = False
        else:
            findCodes = True
        if self.rbRightOfNSText.isChecked():
            lookRight = True
        else:
            lookRight = False
        noteNext = False
        sectionText = ''
        for line in textLines:
            if line.startswith(self.nsText) == True:
                # add text to previous section
                if self.sectionCnt > 0:
                    self.sectionList[self.sectionCnt-1][2] = sectionText
                    sectionText = ''
                # find codes if needed
                if findCodes == True:
                    if lookRight:
                        tempCode = line[len(self.nsText):].strip()
                        if tempCode <> '':
                            self.codeList.append(tempCode)
                        else:
                            tempCode = ''
                        self.sectionList.append([self.sectionCnt,tempCode,''])
                        noteNext = False
                    else:
                        noteNext = True
                else:
                    self.sectionList.append([self.sectionCnt,'',''])
                self.sectionCnt += 1
            elif noteNext == True:
                if line <> '':
                    tempCode = line.strip()
                    self.codeList.append(tempCode)
                else:
                    tempCode = ''
                self.sectionList.append([self.sectionCnt-1,tempCode,''])
                noteNext = False
            else:
                sectionText = sectionText + line + '\n'
        # add last part of file to last section
        if self.sectionCnt > 0:
            self.sectionList[self.sectionCnt-1][2] = sectionText
            sectionText = ''
        # check if matching is happening and report match count
        if self.rbMatchCodes.isChecked() == True:
            self.updateRecs = True
            self.matchCount = 0
            self.updateList = []
            for key, value in self.intvDict.iteritems():
                for section in self.sectionList:
                    if key == section[1]:
                        self.updateList.append(section)
                        self.matchCount += 1
            noticeText = "%d sections out of %d in the transcript matched. " % (self.matchCount, self.sectionCnt)
            noticeText += "Do you wish to update the matching sections?"
            response = QtGui.QMessageBox.information(self, 'Validation Summary',
                    noticeText, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if response == QtGui.QMessageBox.Yes:
                proceed = True
            else:
                proceed = False
                self.updateList = []
        else:
            self.updateRecs = False
            noticeText = "%d sections were found in the transcript. " %  self.sectionCnt
            noticeText += "Do you wish to append them to the interview?"
            response = QtGui.QMessageBox.information(self, 'Validation Summary',
                    noticeText, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if response == QtGui.QMessageBox.Yes:
                proceed = True
                self.updateList = self.sectionList
            else:
                proceed = False
                self.updateList = []
        if proceed == True:
            self.pbImport.setEnabled(True)

    #
    # if import clicked notify and return dictionary of required info for import process

    def runImport(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        self.close()

    #
    # return data

    def returnData(self):
        return(self.updateList,self.updateRecs)

    #
    # if cancel clicked notify and return blank dictionary

    def cancelImport(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        self.updateList = []
        self.updateRecs = False
        self.close()

    
