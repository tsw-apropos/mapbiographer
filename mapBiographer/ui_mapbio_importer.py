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
        mapbioImporter.resize(745, 473)
        self.gridLayout = QtGui.QGridLayout(mapbioImporter)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.verticalLayout_2 = QtGui.QVBoxLayout()
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
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
        self.verticalLayout_2.addLayout(self.hlNoteFields)
        self.line_3 = QtGui.QFrame(mapbioImporter)
        self.line_3.setFrameShape(QtGui.QFrame.HLine)
        self.line_3.setFrameShadow(QtGui.QFrame.Sunken)
        self.line_3.setObjectName(_fromUtf8("line_3"))
        self.verticalLayout_2.addWidget(self.line_3)
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
        self.verticalLayout_2.addLayout(self.hlTextFields)
        self.line_2 = QtGui.QFrame(mapbioImporter)
        self.line_2.setFrameShape(QtGui.QFrame.HLine)
        self.line_2.setFrameShadow(QtGui.QFrame.Sunken)
        self.line_2.setObjectName(_fromUtf8("line_2"))
        self.verticalLayout_2.addWidget(self.line_2)
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
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.gridLayout.addLayout(self.verticalLayout_2, 0, 2, 1, 1)
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.hlSourceFile = QtGui.QHBoxLayout()
        self.hlSourceFile.setObjectName(_fromUtf8("hlSourceFile"))
        self.lblSourceFile = QtGui.QLabel(mapbioImporter)
        self.lblSourceFile.setObjectName(_fromUtf8("lblSourceFile"))
        self.hlSourceFile.addWidget(self.lblSourceFile)
        self.leSourceFile = QtGui.QLineEdit(mapbioImporter)
        self.leSourceFile.setEnabled(True)
        self.leSourceFile.setReadOnly(True)
        self.leSourceFile.setObjectName(_fromUtf8("leSourceFile"))
        self.hlSourceFile.addWidget(self.leSourceFile)
        self.tbSelectSourceFile = QtGui.QToolButton(mapbioImporter)
        self.tbSelectSourceFile.setObjectName(_fromUtf8("tbSelectSourceFile"))
        self.hlSourceFile.addWidget(self.tbSelectSourceFile)
        self.verticalLayout.addLayout(self.hlSourceFile)
        self.lblFieldMapping = QtGui.QLabel(mapbioImporter)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.lblFieldMapping.setFont(font)
        self.lblFieldMapping.setObjectName(_fromUtf8("lblFieldMapping"))
        self.verticalLayout.addWidget(self.lblFieldMapping)
        self.formLayout = QtGui.QFormLayout()
        self.formLayout.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.lblSectionCode = QtGui.QLabel(mapbioImporter)
        self.lblSectionCode.setObjectName(_fromUtf8("lblSectionCode"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.lblSectionCode)
        self.cbSectionCode = QtGui.QComboBox(mapbioImporter)
        self.cbSectionCode.setObjectName(_fromUtf8("cbSectionCode"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.FieldRole, self.cbSectionCode)
        self.lblPrimaryCode = QtGui.QLabel(mapbioImporter)
        self.lblPrimaryCode.setObjectName(_fromUtf8("lblPrimaryCode"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.LabelRole, self.lblPrimaryCode)
        self.cbPrimaryCode = QtGui.QComboBox(mapbioImporter)
        self.cbPrimaryCode.setMinimumSize(QtCore.QSize(175, 0))
        self.cbPrimaryCode.setObjectName(_fromUtf8("cbPrimaryCode"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.FieldRole, self.cbPrimaryCode)
        self.lblSecurity = QtGui.QLabel(mapbioImporter)
        self.lblSecurity.setObjectName(_fromUtf8("lblSecurity"))
        self.formLayout.setWidget(4, QtGui.QFormLayout.LabelRole, self.lblSecurity)
        self.cbSecurity = QtGui.QComboBox(mapbioImporter)
        self.cbSecurity.setObjectName(_fromUtf8("cbSecurity"))
        self.formLayout.setWidget(4, QtGui.QFormLayout.FieldRole, self.cbSecurity)
        self.lblTags = QtGui.QLabel(mapbioImporter)
        self.lblTags.setObjectName(_fromUtf8("lblTags"))
        self.formLayout.setWidget(6, QtGui.QFormLayout.LabelRole, self.lblTags)
        self.cbTags = QtGui.QComboBox(mapbioImporter)
        self.cbTags.setObjectName(_fromUtf8("cbTags"))
        self.formLayout.setWidget(6, QtGui.QFormLayout.FieldRole, self.cbTags)
        self.cbUsePeriod = QtGui.QComboBox(mapbioImporter)
        self.cbUsePeriod.setObjectName(_fromUtf8("cbUsePeriod"))
        self.formLayout.setWidget(8, QtGui.QFormLayout.FieldRole, self.cbUsePeriod)
        self.lblUsePeriod = QtGui.QLabel(mapbioImporter)
        self.lblUsePeriod.setObjectName(_fromUtf8("lblUsePeriod"))
        self.formLayout.setWidget(8, QtGui.QFormLayout.LabelRole, self.lblUsePeriod)
        self.lblTimeOfYear = QtGui.QLabel(mapbioImporter)
        self.lblTimeOfYear.setObjectName(_fromUtf8("lblTimeOfYear"))
        self.formLayout.setWidget(9, QtGui.QFormLayout.LabelRole, self.lblTimeOfYear)
        self.cbTimeOfYear = QtGui.QComboBox(mapbioImporter)
        self.cbTimeOfYear.setObjectName(_fromUtf8("cbTimeOfYear"))
        self.formLayout.setWidget(9, QtGui.QFormLayout.FieldRole, self.cbTimeOfYear)
        self.lblSpatialDataSource = QtGui.QLabel(mapbioImporter)
        self.lblSpatialDataSource.setObjectName(_fromUtf8("lblSpatialDataSource"))
        self.formLayout.setWidget(10, QtGui.QFormLayout.LabelRole, self.lblSpatialDataSource)
        self.cbSpatialDataSource = QtGui.QComboBox(mapbioImporter)
        self.cbSpatialDataSource.setObjectName(_fromUtf8("cbSpatialDataSource"))
        self.cbSpatialDataSource.addItem(_fromUtf8(""))
        self.cbSpatialDataSource.addItem(_fromUtf8(""))
        self.cbSpatialDataSource.addItem(_fromUtf8(""))
        self.cbSpatialDataSource.addItem(_fromUtf8(""))
        self.formLayout.setWidget(10, QtGui.QFormLayout.FieldRole, self.cbSpatialDataSource)
        self.lblSpatialDataScale = QtGui.QLabel(mapbioImporter)
        self.lblSpatialDataScale.setObjectName(_fromUtf8("lblSpatialDataScale"))
        self.formLayout.setWidget(11, QtGui.QFormLayout.LabelRole, self.lblSpatialDataScale)
        self.spbxSpatialDataScale = QtGui.QSpinBox(mapbioImporter)
        self.spbxSpatialDataScale.setMinimum(1)
        self.spbxSpatialDataScale.setMaximum(10000000)
        self.spbxSpatialDataScale.setSingleStep(10000)
        self.spbxSpatialDataScale.setProperty("value", 250000)
        self.spbxSpatialDataScale.setObjectName(_fromUtf8("spbxSpatialDataScale"))
        self.formLayout.setWidget(11, QtGui.QFormLayout.FieldRole, self.spbxSpatialDataScale)
        self.lblContentCodes = QtGui.QLabel(mapbioImporter)
        self.lblContentCodes.setObjectName(_fromUtf8("lblContentCodes"))
        self.formLayout.setWidget(5, QtGui.QFormLayout.LabelRole, self.lblContentCodes)
        self.cbContentCodes = QtGui.QComboBox(mapbioImporter)
        self.cbContentCodes.setObjectName(_fromUtf8("cbContentCodes"))
        self.formLayout.setWidget(5, QtGui.QFormLayout.FieldRole, self.cbContentCodes)
        self.lblLegacyCode = QtGui.QLabel(mapbioImporter)
        self.lblLegacyCode.setObjectName(_fromUtf8("lblLegacyCode"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.lblLegacyCode)
        self.cbLegacyCode = QtGui.QComboBox(mapbioImporter)
        self.cbLegacyCode.setObjectName(_fromUtf8("cbLegacyCode"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.cbLegacyCode)
        self.lblRecordingDate = QtGui.QLabel(mapbioImporter)
        self.lblRecordingDate.setObjectName(_fromUtf8("lblRecordingDate"))
        self.formLayout.setWidget(7, QtGui.QFormLayout.LabelRole, self.lblRecordingDate)
        self.cbRecordingDate = QtGui.QComboBox(mapbioImporter)
        self.cbRecordingDate.setObjectName(_fromUtf8("cbRecordingDate"))
        self.formLayout.setWidget(7, QtGui.QFormLayout.FieldRole, self.cbRecordingDate)
        self.lblSequence = QtGui.QLabel(mapbioImporter)
        self.lblSequence.setObjectName(_fromUtf8("lblSequence"))
        self.formLayout.setWidget(3, QtGui.QFormLayout.LabelRole, self.lblSequence)
        self.cbSequence = QtGui.QComboBox(mapbioImporter)
        self.cbSequence.setObjectName(_fromUtf8("cbSequence"))
        self.formLayout.setWidget(3, QtGui.QFormLayout.FieldRole, self.cbSequence)
        self.verticalLayout.addLayout(self.formLayout)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)
        self.line = QtGui.QFrame(mapbioImporter)
        self.line.setFrameShape(QtGui.QFrame.VLine)
        self.line.setFrameShadow(QtGui.QFrame.Sunken)
        self.line.setObjectName(_fromUtf8("line"))
        self.gridLayout.addWidget(self.line, 0, 1, 1, 1)
        self.line.raise_()

        self.retranslateUi(mapbioImporter)
        self.cbSpatialDataSource.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(mapbioImporter)
        mapbioImporter.setTabOrder(self.leSourceFile, self.tbSelectSourceFile)
        mapbioImporter.setTabOrder(self.tbSelectSourceFile, self.cbSectionCode)
        mapbioImporter.setTabOrder(self.cbSectionCode, self.cbPrimaryCode)
        mapbioImporter.setTabOrder(self.cbPrimaryCode, self.cbSecurity)
        mapbioImporter.setTabOrder(self.cbSecurity, self.cbContentCodes)
        mapbioImporter.setTabOrder(self.cbContentCodes, self.cbTags)
        mapbioImporter.setTabOrder(self.cbTags, self.cbUsePeriod)
        mapbioImporter.setTabOrder(self.cbUsePeriod, self.cbTimeOfYear)
        mapbioImporter.setTabOrder(self.cbTimeOfYear, self.cbSpatialDataSource)
        mapbioImporter.setTabOrder(self.cbSpatialDataSource, self.spbxSpatialDataScale)
        mapbioImporter.setTabOrder(self.spbxSpatialDataScale, self.lwANFields)
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
        self.lblSourceFile.setText(_translate("mapbioImporter", "Source File:", None))
        self.tbSelectSourceFile.setToolTip(_translate("mapbioImporter", "<html><head/><body><p>Click here to set the LOUIS Map Biographer default projects directory.</p></body></html>", None))
        self.tbSelectSourceFile.setText(_translate("mapbioImporter", "...", None))
        self.lblFieldMapping.setText(_translate("mapbioImporter", "Field Mapping / Default Values", None))
        self.lblSectionCode.setText(_translate("mapbioImporter", "Section Code Field:", None))
        self.lblPrimaryCode.setText(_translate("mapbioImporter", "Primary Code Field:", None))
        self.lblSecurity.setText(_translate("mapbioImporter", "Security Field:", None))
        self.lblTags.setText(_translate("mapbioImporter", "Tags Field:", None))
        self.lblUsePeriod.setText(_translate("mapbioImporter", "Use Period Field:", None))
        self.lblTimeOfYear.setText(_translate("mapbioImporter", "Time of Year Field:", None))
        self.lblSpatialDataSource.setText(_translate("mapbioImporter", "Spatial Data Source", None))
        self.cbSpatialDataSource.setItemText(0, _translate("mapbioImporter", "Paper Map", None))
        self.cbSpatialDataSource.setItemText(1, _translate("mapbioImporter", "On Screen", None))
        self.cbSpatialDataSource.setItemText(2, _translate("mapbioImporter", "Handheld GPS", None))
        self.cbSpatialDataSource.setItemText(3, _translate("mapbioImporter", "Corrected GPS", None))
        self.lblSpatialDataScale.setText(_translate("mapbioImporter", "Spatial Data Scale", None))
        self.lblContentCodes.setText(_translate("mapbioImporter", "Content Codes Field:", None))
        self.lblLegacyCode.setText(_translate("mapbioImporter", "Legacy Code Field:", None))
        self.lblRecordingDate.setText(_translate("mapbioImporter", "Recording Date:", None))
        self.lblSequence.setText(_translate("mapbioImporter", "Sequence Field:", None))

