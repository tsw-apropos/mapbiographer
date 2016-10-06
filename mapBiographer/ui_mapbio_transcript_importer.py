# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_mapbio_transcript_importer.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_mapbioTranscriptImporter(object):
    def setupUi(self, mapbioTranscriptImporter):
        mapbioTranscriptImporter.setObjectName(_fromUtf8("mapbioTranscriptImporter"))
        mapbioTranscriptImporter.setWindowModality(QtCore.Qt.ApplicationModal)
        mapbioTranscriptImporter.resize(525, 253)
        mapbioTranscriptImporter.setMinimumSize(QtCore.QSize(525, 250))
        self.gridLayout = QtGui.QGridLayout(mapbioTranscriptImporter)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.hlSourceFile = QtGui.QHBoxLayout()
        self.hlSourceFile.setObjectName(_fromUtf8("hlSourceFile"))
        self.lblSourceFile = QtGui.QLabel(mapbioTranscriptImporter)
        self.lblSourceFile.setObjectName(_fromUtf8("lblSourceFile"))
        self.hlSourceFile.addWidget(self.lblSourceFile)
        self.leSourceFile = QtGui.QLineEdit(mapbioTranscriptImporter)
        self.leSourceFile.setEnabled(True)
        self.leSourceFile.setReadOnly(True)
        self.leSourceFile.setObjectName(_fromUtf8("leSourceFile"))
        self.hlSourceFile.addWidget(self.leSourceFile)
        self.tbSelectSourceFile = QtGui.QToolButton(mapbioTranscriptImporter)
        self.tbSelectSourceFile.setObjectName(_fromUtf8("tbSelectSourceFile"))
        self.hlSourceFile.addWidget(self.tbSelectSourceFile)
        self.gridLayout.addLayout(self.hlSourceFile, 0, 0, 1, 1)
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.lbNewSectionText = QtGui.QLabel(mapbioTranscriptImporter)
        self.lbNewSectionText.setObjectName(_fromUtf8("lbNewSectionText"))
        self.horizontalLayout_3.addWidget(self.lbNewSectionText)
        self.leNewSectionText = QtGui.QLineEdit(mapbioTranscriptImporter)
        self.leNewSectionText.setObjectName(_fromUtf8("leNewSectionText"))
        self.horizontalLayout_3.addWidget(self.leNewSectionText)
        self.gridLayout.addLayout(self.horizontalLayout_3, 1, 0, 1, 1)
        self.hgbSectionCodes = QtGui.QGroupBox(mapbioTranscriptImporter)
        self.hgbSectionCodes.setObjectName(_fromUtf8("hgbSectionCodes"))
        self.horizontalLayout_2 = QtGui.QHBoxLayout(self.hgbSectionCodes)
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.rbCreateCodes = QtGui.QRadioButton(self.hgbSectionCodes)
        self.rbCreateCodes.setChecked(True)
        self.rbCreateCodes.setObjectName(_fromUtf8("rbCreateCodes"))
        self.horizontalLayout_2.addWidget(self.rbCreateCodes)
        self.rbUseCodes = QtGui.QRadioButton(self.hgbSectionCodes)
        self.rbUseCodes.setObjectName(_fromUtf8("rbUseCodes"))
        self.horizontalLayout_2.addWidget(self.rbUseCodes)
        self.rbMatchCodes = QtGui.QRadioButton(self.hgbSectionCodes)
        self.rbMatchCodes.setChecked(False)
        self.rbMatchCodes.setObjectName(_fromUtf8("rbMatchCodes"))
        self.horizontalLayout_2.addWidget(self.rbMatchCodes)
        self.gridLayout.addWidget(self.hgbSectionCodes, 2, 0, 1, 1)
        self.hgbSectionCodePlacement = QtGui.QGroupBox(mapbioTranscriptImporter)
        self.hgbSectionCodePlacement.setEnabled(False)
        self.hgbSectionCodePlacement.setObjectName(_fromUtf8("hgbSectionCodePlacement"))
        self.horizontalLayout_4 = QtGui.QHBoxLayout(self.hgbSectionCodePlacement)
        self.horizontalLayout_4.setObjectName(_fromUtf8("horizontalLayout_4"))
        self.rbRightOfNSText = QtGui.QRadioButton(self.hgbSectionCodePlacement)
        self.rbRightOfNSText.setChecked(True)
        self.rbRightOfNSText.setObjectName(_fromUtf8("rbRightOfNSText"))
        self.horizontalLayout_4.addWidget(self.rbRightOfNSText)
        self.rbBelowNSText = QtGui.QRadioButton(self.hgbSectionCodePlacement)
        self.rbBelowNSText.setChecked(False)
        self.rbBelowNSText.setObjectName(_fromUtf8("rbBelowNSText"))
        self.horizontalLayout_4.addWidget(self.rbBelowNSText)
        self.gridLayout.addWidget(self.hgbSectionCodePlacement, 3, 0, 1, 1)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.pbValidate = QtGui.QPushButton(mapbioTranscriptImporter)
        self.pbValidate.setEnabled(False)
        self.pbValidate.setObjectName(_fromUtf8("pbValidate"))
        self.horizontalLayout.addWidget(self.pbValidate)
        self.pbImport = QtGui.QPushButton(mapbioTranscriptImporter)
        self.pbImport.setEnabled(False)
        self.pbImport.setObjectName(_fromUtf8("pbImport"))
        self.horizontalLayout.addWidget(self.pbImport)
        self.pbCancel = QtGui.QPushButton(mapbioTranscriptImporter)
        self.pbCancel.setObjectName(_fromUtf8("pbCancel"))
        self.horizontalLayout.addWidget(self.pbCancel)
        self.gridLayout.addLayout(self.horizontalLayout, 4, 0, 1, 1)

        self.retranslateUi(mapbioTranscriptImporter)
        QtCore.QMetaObject.connectSlotsByName(mapbioTranscriptImporter)
        mapbioTranscriptImporter.setTabOrder(self.leSourceFile, self.tbSelectSourceFile)
        mapbioTranscriptImporter.setTabOrder(self.tbSelectSourceFile, self.leNewSectionText)
        mapbioTranscriptImporter.setTabOrder(self.leNewSectionText, self.rbCreateCodes)
        mapbioTranscriptImporter.setTabOrder(self.rbCreateCodes, self.rbMatchCodes)
        mapbioTranscriptImporter.setTabOrder(self.rbMatchCodes, self.rbRightOfNSText)
        mapbioTranscriptImporter.setTabOrder(self.rbRightOfNSText, self.rbBelowNSText)
        mapbioTranscriptImporter.setTabOrder(self.rbBelowNSText, self.pbValidate)
        mapbioTranscriptImporter.setTabOrder(self.pbValidate, self.pbImport)
        mapbioTranscriptImporter.setTabOrder(self.pbImport, self.pbCancel)

    def retranslateUi(self, mapbioTranscriptImporter):
        mapbioTranscriptImporter.setWindowTitle(_translate("mapbioTranscriptImporter", "Import Features", None))
        self.lblSourceFile.setToolTip(_translate("mapbioTranscriptImporter", "The text file with the transcript.", None))
        self.lblSourceFile.setText(_translate("mapbioTranscriptImporter", "Source File:", None))
        self.leSourceFile.setToolTip(_translate("mapbioTranscriptImporter", "The text file with the transcript.", None))
        self.tbSelectSourceFile.setToolTip(_translate("mapbioTranscriptImporter", "<html><head/><body><p>Click here to set the LOUIS Map Biographer default projects directory.</p></body></html>", None))
        self.tbSelectSourceFile.setText(_translate("mapbioTranscriptImporter", "...", None))
        self.lbNewSectionText.setToolTip(_translate("mapbioTranscriptImporter", "This text should appear immediately before the start of all new sections.", None))
        self.lbNewSectionText.setText(_translate("mapbioTranscriptImporter", "New Section Text:", None))
        self.leNewSectionText.setToolTip(_translate("mapbioTranscriptImporter", "This text should appear immediately before the start of all new sections.", None))
        self.leNewSectionText.setText(_translate("mapbioTranscriptImporter", ">>NS>>", None))
        self.hgbSectionCodes.setToolTip(_translate("mapbioTranscriptImporter", "Note: If not matching old codes will be kept as legacy codes", None))
        self.hgbSectionCodes.setTitle(_translate("mapbioTranscriptImporter", "Create new sections and codes?", None))
        self.rbCreateCodes.setText(_translate("mapbioTranscriptImporter", "Yes, all new", None))
        self.rbUseCodes.setText(_translate("mapbioTranscriptImporter", "Yes, keep legacy codes", None))
        self.rbMatchCodes.setText(_translate("mapbioTranscriptImporter", "No, match and update", None))
        self.hgbSectionCodePlacement.setToolTip(_translate("mapbioTranscriptImporter", "Where should the system look for system codes in relation to the New Section Text?", None))
        self.hgbSectionCodePlacement.setTitle(_translate("mapbioTranscriptImporter", "Where is the section code in relation to the New Section Text?", None))
        self.rbRightOfNSText.setText(_translate("mapbioTranscriptImporter", "Right of NS Text", None))
        self.rbBelowNSText.setText(_translate("mapbioTranscriptImporter", "On line below NS Text", None))
        self.pbValidate.setText(_translate("mapbioTranscriptImporter", "Validate", None))
        self.pbImport.setText(_translate("mapbioTranscriptImporter", "Import", None))
        self.pbCancel.setText(_translate("mapbioTranscriptImporter", "Cancel", None))

