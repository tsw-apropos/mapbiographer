# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_mapbio_navigator.ui'
#
# Created: Fri Apr 10 09:58:42 2015
#      by: PyQt4 UI code generator 4.11.2
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

class Ui_mapbioNavigator(object):
    def setupUi(self, mapbioNavigator):
        mapbioNavigator.setObjectName(_fromUtf8("mapbioNavigator"))
        mapbioNavigator.resize(294, 224)
        self.dockWidgetContents = QtGui.QWidget()
        self.dockWidgetContents.setObjectName(_fromUtf8("dockWidgetContents"))
        self.gridLayout = QtGui.QGridLayout(self.dockWidgetContents)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.flMapLayers = QtGui.QFormLayout()
        self.flMapLayers.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.flMapLayers.setObjectName(_fromUtf8("flMapLayers"))
        self.lblBase = QtGui.QLabel(self.dockWidgetContents)
        self.lblBase.setObjectName(_fromUtf8("lblBase"))
        self.flMapLayers.setWidget(0, QtGui.QFormLayout.LabelRole, self.lblBase)
        self.cbBase = QtGui.QComboBox(self.dockWidgetContents)
        self.cbBase.setMinimumSize(QtCore.QSize(135, 0))
        self.cbBase.setObjectName(_fromUtf8("cbBase"))
        self.flMapLayers.setWidget(0, QtGui.QFormLayout.FieldRole, self.cbBase)
        self.pbBoundary = QtGui.QPushButton(self.dockWidgetContents)
        self.pbBoundary.setMinimumSize(QtCore.QSize(133, 0))
        self.pbBoundary.setObjectName(_fromUtf8("pbBoundary"))
        self.flMapLayers.setWidget(1, QtGui.QFormLayout.LabelRole, self.pbBoundary)
        self.pbReference = QtGui.QPushButton(self.dockWidgetContents)
        self.pbReference.setObjectName(_fromUtf8("pbReference"))
        self.flMapLayers.setWidget(1, QtGui.QFormLayout.FieldRole, self.pbReference)
        self.pbViewFeatures = QtGui.QPushButton(self.dockWidgetContents)
        self.pbViewFeatures.setMinimumSize(QtCore.QSize(133, 0))
        self.pbViewFeatures.setObjectName(_fromUtf8("pbViewFeatures"))
        self.flMapLayers.setWidget(2, QtGui.QFormLayout.LabelRole, self.pbViewFeatures)
        self.pbFeatureLabels = QtGui.QPushButton(self.dockWidgetContents)
        self.pbFeatureLabels.setObjectName(_fromUtf8("pbFeatureLabels"))
        self.flMapLayers.setWidget(2, QtGui.QFormLayout.FieldRole, self.pbFeatureLabels)
        self.pbZoomToStudyArea = QtGui.QPushButton(self.dockWidgetContents)
        self.pbZoomToStudyArea.setObjectName(_fromUtf8("pbZoomToStudyArea"))
        self.flMapLayers.setWidget(3, QtGui.QFormLayout.FieldRole, self.pbZoomToStudyArea)
        self.pbZoomFull = QtGui.QPushButton(self.dockWidgetContents)
        self.pbZoomFull.setObjectName(_fromUtf8("pbZoomFull"))
        self.flMapLayers.setWidget(3, QtGui.QFormLayout.LabelRole, self.pbZoomFull)
        self.pbZoomIn = QtGui.QPushButton(self.dockWidgetContents)
        self.pbZoomIn.setMinimumSize(QtCore.QSize(133, 0))
        self.pbZoomIn.setObjectName(_fromUtf8("pbZoomIn"))
        self.flMapLayers.setWidget(4, QtGui.QFormLayout.LabelRole, self.pbZoomIn)
        self.pbZoomOut = QtGui.QPushButton(self.dockWidgetContents)
        self.pbZoomOut.setObjectName(_fromUtf8("pbZoomOut"))
        self.flMapLayers.setWidget(4, QtGui.QFormLayout.FieldRole, self.pbZoomOut)
        self.gridLayout.addLayout(self.flMapLayers, 0, 0, 1, 1)
        mapbioNavigator.setWidget(self.dockWidgetContents)

        self.retranslateUi(mapbioNavigator)
        QtCore.QMetaObject.connectSlotsByName(mapbioNavigator)

    def retranslateUi(self, mapbioNavigator):
        mapbioNavigator.setWindowTitle(_translate("mapbioNavigator", "LOUIS Map Biographer - Navigation", None))
        self.lblBase.setText(_translate("mapbioNavigator", "Select Base Map", None))
        self.pbBoundary.setText(_translate("mapbioNavigator", "Hide Boundary", None))
        self.pbReference.setText(_translate("mapbioNavigator", "Show Reference", None))
        self.pbViewFeatures.setText(_translate("mapbioNavigator", "Hide Features", None))
        self.pbFeatureLabels.setText(_translate("mapbioNavigator", "Hide Labels", None))
        self.pbZoomToStudyArea.setText(_translate("mapbioNavigator", "Zoom Study Area", None))
        self.pbZoomFull.setText(_translate("mapbioNavigator", "Zoom Full Extent", None))
        self.pbZoomIn.setText(_translate("mapbioNavigator", "Zoom In", None))
        self.pbZoomOut.setText(_translate("mapbioNavigator", "Zoom Out", None))

