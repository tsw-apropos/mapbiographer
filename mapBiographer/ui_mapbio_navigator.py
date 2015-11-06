# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_mapbio_navigator.ui'
#
# Created: Mon Apr 27 13:48:20 2015
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
        mapbioNavigator.resize(338, 142)
        self.dockWidgetContents = QtGui.QWidget()
        self.dockWidgetContents.setObjectName(_fromUtf8("dockWidgetContents"))
        self.gridLayout_2 = QtGui.QGridLayout(self.dockWidgetContents)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.lblBase = QtGui.QLabel(self.dockWidgetContents)
        self.lblBase.setObjectName(_fromUtf8("lblBase"))
        self.horizontalLayout.addWidget(self.lblBase)
        self.cbBase = QtGui.QComboBox(self.dockWidgetContents)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.cbBase.sizePolicy().hasHeightForWidth())
        self.cbBase.setSizePolicy(sizePolicy)
        self.cbBase.setMinimumSize(QtCore.QSize(133, 0))
        self.cbBase.setObjectName(_fromUtf8("cbBase"))
        self.horizontalLayout.addWidget(self.cbBase)
        self.gridLayout_2.addLayout(self.horizontalLayout, 0, 0, 1, 1)
        self.gridLayout = QtGui.QGridLayout()
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.cbBoundary = QtGui.QCheckBox(self.dockWidgetContents)
        self.cbBoundary.setObjectName(_fromUtf8("cbBoundary"))
        self.gridLayout.addWidget(self.cbBoundary, 0, 0, 1, 1)
        self.cbFeatures = QtGui.QCheckBox(self.dockWidgetContents)
        self.cbFeatures.setObjectName(_fromUtf8("cbFeatures"))
        self.gridLayout.addWidget(self.cbFeatures, 0, 1, 1, 1)
        self.cbReference = QtGui.QCheckBox(self.dockWidgetContents)
        self.cbReference.setObjectName(_fromUtf8("cbReference"))
        self.gridLayout.addWidget(self.cbReference, 1, 0, 1, 1)
        self.cbLabels = QtGui.QCheckBox(self.dockWidgetContents)
        self.cbLabels.setObjectName(_fromUtf8("cbLabels"))
        self.gridLayout.addWidget(self.cbLabels, 1, 1, 1, 1)
        self.gridLayout_2.addLayout(self.gridLayout, 1, 0, 1, 1)
        mapbioNavigator.setWidget(self.dockWidgetContents)

        self.retranslateUi(mapbioNavigator)
        QtCore.QMetaObject.connectSlotsByName(mapbioNavigator)

    def retranslateUi(self, mapbioNavigator):
        mapbioNavigator.setWindowTitle(_translate("mapbioNavigator", "LOUIS Map Biographer - Navigation", None))
        self.lblBase.setText(_translate("mapbioNavigator", "Select Base Map:", None))
        self.cbBoundary.setText(_translate("mapbioNavigator", "Show Boundary", None))
        self.cbFeatures.setText(_translate("mapbioNavigator", "Show Features", None))
        self.cbReference.setText(_translate("mapbioNavigator", "Show Reference", None))
        self.cbLabels.setText(_translate("mapbioNavigator", "Show Feature Labels", None))

