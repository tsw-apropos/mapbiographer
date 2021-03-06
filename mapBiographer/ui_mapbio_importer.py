# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_mapbio_importer.ui'
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

class Ui_mapbioImporter(object):
    def setupUi(self, mapbioImporter):
        mapbioImporter.setObjectName(_fromUtf8("mapbioImporter"))
        mapbioImporter.setWindowModality(QtCore.Qt.ApplicationModal)
        mapbioImporter.resize(715, 608)
        self.gridLayout = QtGui.QGridLayout(mapbioImporter)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.vlLeftPanel = QtGui.QVBoxLayout()
        self.vlLeftPanel.setObjectName(_fromUtf8("vlLeftPanel"))
        self.hlSourceFile = QtGui.QHBoxLayout()
        self.hlSourceFile.setObjectName(_fromUtf8("hlSourceFile"))
        self.lblSourceFile = QtGui.QLabel(mapbioImporter)
        self.lblSourceFile.setObjectName(_fromUtf8("lblSourceFile"))
        self.hlSourceFile.addWidget(self.lblSourceFile)
        self.leSourceFile = QtGui.QLineEdit(mapbioImporter)
        self.leSourceFile.setEnabled(True)
        self.leSourceFile.setMinimumSize(QtCore.QSize(230, 0))
        self.leSourceFile.setReadOnly(True)
        self.leSourceFile.setObjectName(_fromUtf8("leSourceFile"))
        self.hlSourceFile.addWidget(self.leSourceFile)
        self.tbSelectSourceFile = QtGui.QToolButton(mapbioImporter)
        self.tbSelectSourceFile.setObjectName(_fromUtf8("tbSelectSourceFile"))
        self.hlSourceFile.addWidget(self.tbSelectSourceFile)
        self.vlLeftPanel.addLayout(self.hlSourceFile)
        self.hlFieldMapping = QtGui.QHBoxLayout()
        self.hlFieldMapping.setObjectName(_fromUtf8("hlFieldMapping"))
        self.lblFieldMapping = QtGui.QLabel(mapbioImporter)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.lblFieldMapping.setFont(font)
        self.lblFieldMapping.setObjectName(_fromUtf8("lblFieldMapping"))
        self.hlFieldMapping.addWidget(self.lblFieldMapping)
        self.cbSuggestFields = QtGui.QCheckBox(mapbioImporter)
        self.cbSuggestFields.setChecked(True)
        self.cbSuggestFields.setObjectName(_fromUtf8("cbSuggestFields"))
        self.hlFieldMapping.addWidget(self.cbSuggestFields)
        self.vlLeftPanel.addLayout(self.hlFieldMapping)
        self.scFields = QtGui.QScrollArea(mapbioImporter)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scFields.sizePolicy().hasHeightForWidth())
        self.scFields.setSizePolicy(sizePolicy)
        self.scFields.setMinimumSize(QtCore.QSize(350, 0))
        self.scFields.setFrameShadow(QtGui.QFrame.Sunken)
        self.scFields.setWidgetResizable(True)
        self.scFields.setObjectName(_fromUtf8("scFields"))
        self.scaFieldList = QtGui.QWidget()
        self.scaFieldList.setGeometry(QtCore.QRect(0, 0, 348, 511))
        self.scaFieldList.setObjectName(_fromUtf8("scaFieldList"))
        self.grFields = QtGui.QGridLayout(self.scaFieldList)
        self.grFields.setContentsMargins(-1, 0, 0, 0)
        self.grFields.setHorizontalSpacing(0)
        self.grFields.setObjectName(_fromUtf8("grFields"))
        self.cbSequence = QtGui.QComboBox(self.scaFieldList)
        self.cbSequence.setObjectName(_fromUtf8("cbSequence"))
        self.grFields.addWidget(self.cbSequence, 7, 1, 1, 1)
        self.cbSpatialDataSource = QtGui.QComboBox(self.scaFieldList)
        self.cbSpatialDataSource.setObjectName(_fromUtf8("cbSpatialDataSource"))
        self.cbSpatialDataSource.addItem(_fromUtf8(""))
        self.cbSpatialDataSource.addItem(_fromUtf8(""))
        self.cbSpatialDataSource.addItem(_fromUtf8(""))
        self.cbSpatialDataSource.addItem(_fromUtf8(""))
        self.grFields.addWidget(self.cbSpatialDataSource, 19, 1, 1, 1)
        self.spbxSpatialDataScale = QtGui.QSpinBox(self.scaFieldList)
        self.spbxSpatialDataScale.setMinimum(1)
        self.spbxSpatialDataScale.setMaximum(10000000)
        self.spbxSpatialDataScale.setSingleStep(10000)
        self.spbxSpatialDataScale.setProperty("value", 250000)
        self.spbxSpatialDataScale.setObjectName(_fromUtf8("spbxSpatialDataScale"))
        self.grFields.addWidget(self.spbxSpatialDataScale, 20, 1, 1, 1)
        self.cbSecurity = QtGui.QComboBox(self.scaFieldList)
        self.cbSecurity.setObjectName(_fromUtf8("cbSecurity"))
        self.grFields.addWidget(self.cbSecurity, 8, 1, 1, 1)
        self.lblSequence = QtGui.QLabel(self.scaFieldList)
        self.lblSequence.setObjectName(_fromUtf8("lblSequence"))
        self.grFields.addWidget(self.lblSequence, 7, 0, 1, 1)
        self.lblSectionCode = QtGui.QLabel(self.scaFieldList)
        self.lblSectionCode.setObjectName(_fromUtf8("lblSectionCode"))
        self.grFields.addWidget(self.lblSectionCode, 1, 0, 1, 1)
        self.lblSecurity = QtGui.QLabel(self.scaFieldList)
        self.lblSecurity.setObjectName(_fromUtf8("lblSecurity"))
        self.grFields.addWidget(self.lblSecurity, 8, 0, 1, 1)
        self.lblSpatialRef = QtGui.QLabel(self.scaFieldList)
        self.lblSpatialRef.setObjectName(_fromUtf8("lblSpatialRef"))
        self.grFields.addWidget(self.lblSpatialRef, 3, 0, 1, 1)
        self.lblSpatialDataScale = QtGui.QLabel(self.scaFieldList)
        self.lblSpatialDataScale.setObjectName(_fromUtf8("lblSpatialDataScale"))
        self.grFields.addWidget(self.lblSpatialDataScale, 20, 0, 1, 1)
        self.lblSpatialDataSource = QtGui.QLabel(self.scaFieldList)
        self.lblSpatialDataSource.setObjectName(_fromUtf8("lblSpatialDataSource"))
        self.grFields.addWidget(self.lblSpatialDataSource, 19, 0, 1, 1)
        self.cbSectionCode = QtGui.QComboBox(self.scaFieldList)
        self.cbSectionCode.setObjectName(_fromUtf8("cbSectionCode"))
        self.grFields.addWidget(self.cbSectionCode, 1, 1, 1, 1)
        self.cbLegacyCode = QtGui.QComboBox(self.scaFieldList)
        self.cbLegacyCode.setObjectName(_fromUtf8("cbLegacyCode"))
        self.grFields.addWidget(self.cbLegacyCode, 0, 1, 1, 1)
        self.lblLegacyCode = QtGui.QLabel(self.scaFieldList)
        self.lblLegacyCode.setObjectName(_fromUtf8("lblLegacyCode"))
        self.grFields.addWidget(self.lblLegacyCode, 0, 0, 1, 1)
        self.cbSpatialRef = QtGui.QComboBox(self.scaFieldList)
        self.cbSpatialRef.setObjectName(_fromUtf8("cbSpatialRef"))
        self.grFields.addWidget(self.cbSpatialRef, 3, 1, 1, 1)
        self.cbContentCodes = QtGui.QComboBox(self.scaFieldList)
        self.cbContentCodes.setObjectName(_fromUtf8("cbContentCodes"))
        self.grFields.addWidget(self.cbContentCodes, 9, 1, 1, 1)
        self.lblContentCodes = QtGui.QLabel(self.scaFieldList)
        self.lblContentCodes.setObjectName(_fromUtf8("lblContentCodes"))
        self.grFields.addWidget(self.lblContentCodes, 9, 0, 1, 1)
        self.lblTags = QtGui.QLabel(self.scaFieldList)
        self.lblTags.setObjectName(_fromUtf8("lblTags"))
        self.grFields.addWidget(self.lblTags, 10, 0, 1, 1)
        self.cbTags = QtGui.QComboBox(self.scaFieldList)
        self.cbTags.setObjectName(_fromUtf8("cbTags"))
        self.grFields.addWidget(self.cbTags, 10, 1, 1, 1)
        self.lblRecordingDate = QtGui.QLabel(self.scaFieldList)
        self.lblRecordingDate.setObjectName(_fromUtf8("lblRecordingDate"))
        self.grFields.addWidget(self.lblRecordingDate, 11, 0, 1, 1)
        self.cbRecordingDate = QtGui.QComboBox(self.scaFieldList)
        self.cbRecordingDate.setObjectName(_fromUtf8("cbRecordingDate"))
        self.grFields.addWidget(self.cbRecordingDate, 11, 1, 1, 1)
        self.lblUsePeriod = QtGui.QLabel(self.scaFieldList)
        self.lblUsePeriod.setObjectName(_fromUtf8("lblUsePeriod"))
        self.grFields.addWidget(self.lblUsePeriod, 13, 0, 1, 1)
        self.cbUsePeriod = QtGui.QComboBox(self.scaFieldList)
        self.cbUsePeriod.setObjectName(_fromUtf8("cbUsePeriod"))
        self.grFields.addWidget(self.cbUsePeriod, 13, 1, 1, 1)
        self.lblTimeOfYear = QtGui.QLabel(self.scaFieldList)
        self.lblTimeOfYear.setObjectName(_fromUtf8("lblTimeOfYear"))
        self.grFields.addWidget(self.lblTimeOfYear, 15, 0, 1, 1)
        self.cbTimeOfYear = QtGui.QComboBox(self.scaFieldList)
        self.cbTimeOfYear.setObjectName(_fromUtf8("cbTimeOfYear"))
        self.grFields.addWidget(self.cbTimeOfYear, 15, 1, 1, 1)
        self.lblPrimaryCode = QtGui.QLabel(self.scaFieldList)
        self.lblPrimaryCode.setObjectName(_fromUtf8("lblPrimaryCode"))
        self.grFields.addWidget(self.lblPrimaryCode, 4, 0, 1, 1)
        self.cbPrimaryCode = QtGui.QComboBox(self.scaFieldList)
        self.cbPrimaryCode.setMinimumSize(QtCore.QSize(175, 0))
        self.cbPrimaryCode.setObjectName(_fromUtf8("cbPrimaryCode"))
        self.grFields.addWidget(self.cbPrimaryCode, 4, 1, 1, 1)
        self.scFields.setWidget(self.scaFieldList)
        self.vlLeftPanel.addWidget(self.scFields)
        self.gridLayout.addLayout(self.vlLeftPanel, 0, 0, 1, 1)
        self.line = QtGui.QFrame(mapbioImporter)
        self.line.setFrameShape(QtGui.QFrame.VLine)
        self.line.setFrameShadow(QtGui.QFrame.Sunken)
        self.line.setObjectName(_fromUtf8("line"))
        self.gridLayout.addWidget(self.line, 0, 1, 1, 1)
        self.vlRightPanel = QtGui.QVBoxLayout()
        self.vlRightPanel.setObjectName(_fromUtf8("vlRightPanel"))
        self.hlNoteFields = QtGui.QHBoxLayout()
        self.hlNoteFields.setObjectName(_fromUtf8("hlNoteFields"))
        self.vlANFields = QtGui.QVBoxLayout()
        self.vlANFields.setObjectName(_fromUtf8("vlANFields"))
        self.lblAvailableNoteFields = QtGui.QLabel(mapbioImporter)
        self.lblAvailableNoteFields.setObjectName(_fromUtf8("lblAvailableNoteFields"))
        self.vlANFields.addWidget(self.lblAvailableNoteFields)
        self.lwANFields = QtGui.QListWidget(mapbioImporter)
        self.lwANFields.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.lwANFields.setProperty("showDropIndicator", False)
        self.lwANFields.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.lwANFields.setObjectName(_fromUtf8("lwANFields"))
        self.vlANFields.addWidget(self.lwANFields)
        self.hlNoteFields.addLayout(self.vlANFields)
        self.vlNoteFieldButtons = QtGui.QVBoxLayout()
        self.vlNoteFieldButtons.setObjectName(_fromUtf8("vlNoteFieldButtons"))
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.vlNoteFieldButtons.addItem(spacerItem)
        self.tbAddNoteField = QtGui.QToolButton(mapbioImporter)
        self.tbAddNoteField.setEnabled(False)
        self.tbAddNoteField.setArrowType(QtCore.Qt.RightArrow)
        self.tbAddNoteField.setObjectName(_fromUtf8("tbAddNoteField"))
        self.vlNoteFieldButtons.addWidget(self.tbAddNoteField)
        self.tbRemoveNoteField = QtGui.QToolButton(mapbioImporter)
        self.tbRemoveNoteField.setEnabled(False)
        self.tbRemoveNoteField.setArrowType(QtCore.Qt.LeftArrow)
        self.tbRemoveNoteField.setObjectName(_fromUtf8("tbRemoveNoteField"))
        self.vlNoteFieldButtons.addWidget(self.tbRemoveNoteField)
        self.hlNoteFields.addLayout(self.vlNoteFieldButtons)
        self.vlNoteFields = QtGui.QVBoxLayout()
        self.vlNoteFields.setObjectName(_fromUtf8("vlNoteFields"))
        self.lblNoteFields = QtGui.QLabel(mapbioImporter)
        self.lblNoteFields.setObjectName(_fromUtf8("lblNoteFields"))
        self.vlNoteFields.addWidget(self.lblNoteFields)
        self.lwNFields = QtGui.QListWidget(mapbioImporter)
        self.lwNFields.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.lwNFields.setProperty("showDropIndicator", False)
        self.lwNFields.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.lwNFields.setObjectName(_fromUtf8("lwNFields"))
        self.vlNoteFields.addWidget(self.lwNFields)
        self.hlNoteFields.addLayout(self.vlNoteFields)
        self.vlRightPanel.addLayout(self.hlNoteFields)
        self.line_3 = QtGui.QFrame(mapbioImporter)
        self.line_3.setFrameShape(QtGui.QFrame.HLine)
        self.line_3.setFrameShadow(QtGui.QFrame.Sunken)
        self.line_3.setObjectName(_fromUtf8("line_3"))
        self.vlRightPanel.addWidget(self.line_3)
        self.hlTextFields = QtGui.QHBoxLayout()
        self.hlTextFields.setObjectName(_fromUtf8("hlTextFields"))
        self.vlATFields = QtGui.QVBoxLayout()
        self.vlATFields.setObjectName(_fromUtf8("vlATFields"))
        self.lblAvailableTextFields = QtGui.QLabel(mapbioImporter)
        self.lblAvailableTextFields.setObjectName(_fromUtf8("lblAvailableTextFields"))
        self.vlATFields.addWidget(self.lblAvailableTextFields)
        self.lwASFields = QtGui.QListWidget(mapbioImporter)
        self.lwASFields.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.lwASFields.setProperty("showDropIndicator", False)
        self.lwASFields.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.lwASFields.setObjectName(_fromUtf8("lwASFields"))
        self.vlATFields.addWidget(self.lwASFields)
        self.hlTextFields.addLayout(self.vlATFields)
        self.vlTextFieldButtons = QtGui.QVBoxLayout()
        self.vlTextFieldButtons.setObjectName(_fromUtf8("vlTextFieldButtons"))
        spacerItem1 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.vlTextFieldButtons.addItem(spacerItem1)
        self.tbAddSectionField = QtGui.QToolButton(mapbioImporter)
        self.tbAddSectionField.setEnabled(False)
        self.tbAddSectionField.setArrowType(QtCore.Qt.RightArrow)
        self.tbAddSectionField.setObjectName(_fromUtf8("tbAddSectionField"))
        self.vlTextFieldButtons.addWidget(self.tbAddSectionField)
        self.tbRemoveSectionField = QtGui.QToolButton(mapbioImporter)
        self.tbRemoveSectionField.setEnabled(False)
        self.tbRemoveSectionField.setArrowType(QtCore.Qt.LeftArrow)
        self.tbRemoveSectionField.setObjectName(_fromUtf8("tbRemoveSectionField"))
        self.vlTextFieldButtons.addWidget(self.tbRemoveSectionField)
        self.hlTextFields.addLayout(self.vlTextFieldButtons)
        self.vlTextFields = QtGui.QVBoxLayout()
        self.vlTextFields.setObjectName(_fromUtf8("vlTextFields"))
        self.lblTextFields = QtGui.QLabel(mapbioImporter)
        self.lblTextFields.setObjectName(_fromUtf8("lblTextFields"))
        self.vlTextFields.addWidget(self.lblTextFields)
        self.lwSFields = QtGui.QListWidget(mapbioImporter)
        self.lwSFields.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.lwSFields.setProperty("showDropIndicator", False)
        self.lwSFields.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.lwSFields.setObjectName(_fromUtf8("lwSFields"))
        self.vlTextFields.addWidget(self.lwSFields)
        self.hlTextFields.addLayout(self.vlTextFields)
        self.vlRightPanel.addLayout(self.hlTextFields)
        self.line_2 = QtGui.QFrame(mapbioImporter)
        self.line_2.setFrameShape(QtGui.QFrame.HLine)
        self.line_2.setFrameShadow(QtGui.QFrame.Sunken)
        self.line_2.setObjectName(_fromUtf8("line_2"))
        self.vlRightPanel.addWidget(self.line_2)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.pbValidate = QtGui.QPushButton(mapbioImporter)
        self.pbValidate.setEnabled(False)
        self.pbValidate.setObjectName(_fromUtf8("pbValidate"))
        self.horizontalLayout.addWidget(self.pbValidate)
        self.pbImport = QtGui.QPushButton(mapbioImporter)
        self.pbImport.setEnabled(False)
        self.pbImport.setObjectName(_fromUtf8("pbImport"))
        self.horizontalLayout.addWidget(self.pbImport)
        self.pbCancel = QtGui.QPushButton(mapbioImporter)
        self.pbCancel.setObjectName(_fromUtf8("pbCancel"))
        self.horizontalLayout.addWidget(self.pbCancel)
        self.vlRightPanel.addLayout(self.horizontalLayout)
        self.gridLayout.addLayout(self.vlRightPanel, 0, 2, 1, 1)
        self.line.raise_()

        self.retranslateUi(mapbioImporter)
        self.cbSpatialDataSource.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(mapbioImporter)
        mapbioImporter.setTabOrder(self.leSourceFile, self.tbSelectSourceFile)
        mapbioImporter.setTabOrder(self.tbSelectSourceFile, self.lwANFields)
        mapbioImporter.setTabOrder(self.lwANFields, self.tbAddNoteField)
        mapbioImporter.setTabOrder(self.tbAddNoteField, self.tbRemoveNoteField)
        mapbioImporter.setTabOrder(self.tbRemoveNoteField, self.lwNFields)
        mapbioImporter.setTabOrder(self.lwNFields, self.lwASFields)
        mapbioImporter.setTabOrder(self.lwASFields, self.tbAddSectionField)
        mapbioImporter.setTabOrder(self.tbAddSectionField, self.tbRemoveSectionField)
        mapbioImporter.setTabOrder(self.tbRemoveSectionField, self.lwSFields)
        mapbioImporter.setTabOrder(self.lwSFields, self.pbCancel)
        mapbioImporter.setTabOrder(self.pbCancel, self.pbValidate)
        mapbioImporter.setTabOrder(self.pbValidate, self.pbImport)

    def retranslateUi(self, mapbioImporter):
        mapbioImporter.setWindowTitle(_translate("mapbioImporter", "Import Features", None))
        self.lblSourceFile.setText(_translate("mapbioImporter", "Source File:", None))
        self.tbSelectSourceFile.setToolTip(_translate("mapbioImporter", "<html><head/><body><p>Click here to set the LOUIS Map Biographer default projects directory.</p></body></html>", None))
        self.tbSelectSourceFile.setText(_translate("mapbioImporter", "...", None))
        self.lblFieldMapping.setText(_translate("mapbioImporter", "Field Mapping", None))
        self.cbSuggestFields.setText(_translate("mapbioImporter", "Suggest Fields", None))
        self.cbSpatialDataSource.setItemText(0, _translate("mapbioImporter", "Paper Map", None))
        self.cbSpatialDataSource.setItemText(1, _translate("mapbioImporter", "On Screen", None))
        self.cbSpatialDataSource.setItemText(2, _translate("mapbioImporter", "Handheld GPS", None))
        self.cbSpatialDataSource.setItemText(3, _translate("mapbioImporter", "Corrected GPS", None))
        self.lblSequence.setText(_translate("mapbioImporter", "Sequence", None))
        self.lblSectionCode.setText(_translate("mapbioImporter", "Section Code", None))
        self.lblSecurity.setText(_translate("mapbioImporter", "Security", None))
        self.lblSpatialRef.setText(_translate("mapbioImporter", "Spatial Reference", None))
        self.lblSpatialDataScale.setText(_translate("mapbioImporter", "Spatial Data Scale", None))
        self.lblSpatialDataSource.setText(_translate("mapbioImporter", "Spatial Data Source", None))
        self.lblLegacyCode.setText(_translate("mapbioImporter", "Legacy Code", None))
        self.lblContentCodes.setText(_translate("mapbioImporter", "Content Codes", None))
        self.lblTags.setText(_translate("mapbioImporter", "Tags", None))
        self.lblRecordingDate.setText(_translate("mapbioImporter", "Recording Date", None))
        self.lblUsePeriod.setText(_translate("mapbioImporter", "Use Period", None))
        self.lblTimeOfYear.setText(_translate("mapbioImporter", "Time of Year", None))
        self.lblPrimaryCode.setText(_translate("mapbioImporter", "Primary Code", None))
        self.lblAvailableNoteFields.setText(_translate("mapbioImporter", "Available Fields", None))
        self.tbAddNoteField.setText(_translate("mapbioImporter", "...", None))
        self.tbRemoveNoteField.setText(_translate("mapbioImporter", "...", None))
        self.lblNoteFields.setText(_translate("mapbioImporter", "Section Note Fields", None))
        self.lblAvailableTextFields.setText(_translate("mapbioImporter", "Available Fields", None))
        self.tbAddSectionField.setText(_translate("mapbioImporter", "...", None))
        self.tbRemoveSectionField.setText(_translate("mapbioImporter", "...", None))
        self.lblTextFields.setText(_translate("mapbioImporter", "Section Text Fields", None))
        self.pbValidate.setText(_translate("mapbioImporter", "Validate", None))
        self.pbImport.setText(_translate("mapbioImporter", "Import", None))
        self.pbCancel.setText(_translate("mapbioImporter", "Cancel", None))

