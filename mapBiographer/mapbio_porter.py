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
from pyspatialite import dbapi2 as sqlite
import os, datetime, time
from ui_mapbio_porter import Ui_mapbioPorter
from transfer_worker import transferContent
import inspect, re

class mapBiographerPorter(QtGui.QDialog, Ui_mapbioPorter):

    #
    # init method to define globals and make widget / method connections
    
    def __init__(self, iface, dirName, dbName):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)
        self.iface = iface
        self.dirName = dirName
        self.dbName = dbName
        self.actionIdx = 0
        self.account= ''
        self.password = ''

        # debug setup
        self.debug = False
        if self.debug:
            self.myself = lambda: inspect.stack()[1][3]
            QgsMessageLog.logMessage(self.myself())

        # connect widgets to functions
        QtCore.QObject.connect(self.pbClose, QtCore.SIGNAL("clicked()"), self.transferClose)
        QtCore.QObject.connect(self.pbTransfer, QtCore.SIGNAL("clicked()"), self.transferRun)
        QtCore.QObject.connect(self.cbTransferAction, QtCore.SIGNAL("currentIndexChanged(int)"), self.actionSelect)

        # configure interface
        self.interfaceEnable()

    #
    # adjust interface based on selected action

    def actionSelect(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        self.actionIdx = self.cbTransferAction.currentIndex()
        if self.actionIdx == 0:
            # disable interface
            self.pbTransfer.setDisabled(True)
            self.frHeritageLoginInfo.setVisible(False)
        elif self.actionIdx == 1:
            # create heritage 1.x archive
            self.pbTransfer.setEnabled(True)
            self.frHeritageLoginInfo.setVisible(False)
        elif self.actionIdx == 2:
            # create heritage 2.x archive
            self.pbTransfer.setEnabled(True)
            self.frHeritageLoginInfo.setVisible(False)
        elif self.actionIdx == 3:
            # create common GIS formats archive
            self.pbTransfer.setEnabled(True)
            self.frHeritageLoginInfo.setVisible(False)
        elif self.actionIdx == 4:
            # download new interviews
            self.pbTransfer.setEnabled(True)
            self.frHeritageLoginInfo.setVisible(True)
        elif self.actionIdx == 5:
            # upload completed interviews
            self.pbTransfer.setEnabled(True)
            self.frHeritageLoginInfo.setVisible(True)

    #
    # disable interface for run

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
        self.frHeritageLoginInfo.setVisible(False)
        self.lblAllProgress.setText('Overall Progress:')
        self.lblStepProgress.setText('Current Step:')

    #
    # if close clicked notify and return blank dictionary

    def transferClose(self):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        self.close()

    #
    # execute tranfer action

    def transferRun(self):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        # disable actions
        self.interfaceDisable()
        # start action process in thread
        self.errorText = ''
        self.account = self.leUserName.text()
        self.password = self.lePassword.text()
        # instantiate transferContent worker
        if self.actionIdx in [4,5] and (self.account == '' or self.password == ''):
            QtGui.QMessageBox.information(self, 'Information',
               "Your must provide user and password information for your louistk.ca account for direct upload or download!", QtGui.QMessageBox.Ok)
            self.interfaceEnable
        else:
            worker = transferContent(self.actionIdx, self.dirName, self.dbName, self.account, self.password)
            # connect cancel to worker kill
            self.pbCancel.clicked.connect(worker.kill)
            # start the worker in a new thread
            thread = QtCore.QThread(self)
            worker.moveToThread(thread)
            # connect things together
            worker.workerFinished.connect(self.transferFinished)
            worker.workerError.connect(self.transferError)
            worker.workerStatus.connect(self.transferReportStatus)
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

    def transferError(self,e,exception_string,messageText):
        
        QgsMessageLog.logMessage('Worker thread raised an exception\n' + str(exception_string), level=QgsMessageLog.CRITICAL)
        self.errorText = messageText
        #self.interfaceEnable()

    #
    # report transfer status

    def transferReportStatus(self,ret):

        self.actionsStatus = ret
        self.lblStepProgress.setText('Current Step: %s' % ret)

    
