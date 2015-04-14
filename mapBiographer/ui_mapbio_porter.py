# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_mapbio_porter.ui'
#
# Created: Tue Apr 14 10:07:03 2015
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

class Ui_mapbioPorter(object):
    def setupUi(self, mapbioPorter):
        mapbioPorter.setObjectName(_fromUtf8("mapbioPorter"))
        mapbioPorter.resize(400, 292)
        mapbioPorter.setMinimumSize(QtCore.QSize(400, 292))
        mapbioPorter.setMaximumSize(QtCore.QSize(400, 292))
        self.gridLayout_2 = QtGui.QGridLayout(mapbioPorter)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.hlSelectAction = QtGui.QHBoxLayout()
        self.hlSelectAction.setObjectName(_fromUtf8("hlSelectAction"))
        self.lblTransferAction = QtGui.QLabel(mapbioPorter)
        self.lblTransferAction.setMaximumSize(QtCore.QSize(150, 16777215))
        self.lblTransferAction.setObjectName(_fromUtf8("lblTransferAction"))
        self.hlSelectAction.addWidget(self.lblTransferAction)
        self.cbTransferAction = QtGui.QComboBox(mapbioPorter)
        self.cbTransferAction.setObjectName(_fromUtf8("cbTransferAction"))
        self.cbTransferAction.addItem(_fromUtf8(""))
        self.cbTransferAction.addItem(_fromUtf8(""))
        self.cbTransferAction.addItem(_fromUtf8(""))
        self.cbTransferAction.addItem(_fromUtf8(""))
        self.cbTransferAction.addItem(_fromUtf8(""))
        self.cbTransferAction.addItem(_fromUtf8(""))
        self.hlSelectAction.addWidget(self.cbTransferAction)
        self.gridLayout_2.addLayout(self.hlSelectAction, 0, 0, 1, 1)
        self.frHeritageLoginInfo = QtGui.QFrame(mapbioPorter)
        self.frHeritageLoginInfo.setFrameShape(QtGui.QFrame.NoFrame)
        self.frHeritageLoginInfo.setFrameShadow(QtGui.QFrame.Plain)
        self.frHeritageLoginInfo.setObjectName(_fromUtf8("frHeritageLoginInfo"))
        self.gridLayout = QtGui.QGridLayout(self.frHeritageLoginInfo)
        self.gridLayout.setMargin(0)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.lblUserName = QtGui.QLabel(self.frHeritageLoginInfo)
        self.lblUserName.setObjectName(_fromUtf8("lblUserName"))
        self.gridLayout.addWidget(self.lblUserName, 0, 0, 1, 1)
        self.lePassword = QtGui.QLineEdit(self.frHeritageLoginInfo)
        self.lePassword.setEchoMode(QtGui.QLineEdit.Password)
        self.lePassword.setObjectName(_fromUtf8("lePassword"))
        self.gridLayout.addWidget(self.lePassword, 1, 1, 1, 1)
        self.leUserName = QtGui.QLineEdit(self.frHeritageLoginInfo)
        self.leUserName.setObjectName(_fromUtf8("leUserName"))
        self.gridLayout.addWidget(self.leUserName, 0, 1, 1, 1)
        self.lblPassword = QtGui.QLabel(self.frHeritageLoginInfo)
        self.lblPassword.setObjectName(_fromUtf8("lblPassword"))
        self.gridLayout.addWidget(self.lblPassword, 1, 0, 1, 1)
        self.gridLayout_2.addWidget(self.frHeritageLoginInfo, 1, 0, 1, 1)
        self.lblAllProgress = QtGui.QLabel(mapbioPorter)
        self.lblAllProgress.setObjectName(_fromUtf8("lblAllProgress"))
        self.gridLayout_2.addWidget(self.lblAllProgress, 2, 0, 1, 1)
        self.pbAllProgress = QtGui.QProgressBar(mapbioPorter)
        self.pbAllProgress.setProperty("value", 0)
        self.pbAllProgress.setObjectName(_fromUtf8("pbAllProgress"))
        self.gridLayout_2.addWidget(self.pbAllProgress, 3, 0, 1, 1)
        self.lblStepProgress = QtGui.QLabel(mapbioPorter)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lblStepProgress.sizePolicy().hasHeightForWidth())
        self.lblStepProgress.setSizePolicy(sizePolicy)
        self.lblStepProgress.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.lblStepProgress.setObjectName(_fromUtf8("lblStepProgress"))
        self.gridLayout_2.addWidget(self.lblStepProgress, 4, 0, 1, 1)
        self.pbStepProgress = QtGui.QProgressBar(mapbioPorter)
        self.pbStepProgress.setProperty("value", 0)
        self.pbStepProgress.setAlignment(QtCore.Qt.AlignCenter)
        self.pbStepProgress.setTextVisible(True)
        self.pbStepProgress.setObjectName(_fromUtf8("pbStepProgress"))
        self.gridLayout_2.addWidget(self.pbStepProgress, 5, 0, 1, 1)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.pbTransfer = QtGui.QPushButton(mapbioPorter)
        self.pbTransfer.setEnabled(False)
        self.pbTransfer.setObjectName(_fromUtf8("pbTransfer"))
        self.horizontalLayout.addWidget(self.pbTransfer)
        self.pbCancel = QtGui.QPushButton(mapbioPorter)
        self.pbCancel.setEnabled(False)
        self.pbCancel.setObjectName(_fromUtf8("pbCancel"))
        self.horizontalLayout.addWidget(self.pbCancel)
        self.pbClose = QtGui.QPushButton(mapbioPorter)
        self.pbClose.setObjectName(_fromUtf8("pbClose"))
        self.horizontalLayout.addWidget(self.pbClose)
        self.gridLayout_2.addLayout(self.horizontalLayout, 6, 0, 1, 1)

        self.retranslateUi(mapbioPorter)
        QtCore.QMetaObject.connectSlotsByName(mapbioPorter)

    def retranslateUi(self, mapbioPorter):
        mapbioPorter.setWindowTitle(_translate("mapbioPorter", "Transfer Data", None))
        self.lblTransferAction.setText(_translate("mapbioPorter", "Select Action:", None))
        self.cbTransferAction.setItemText(0, _translate("mapbioPorter", "--None--", None))
        self.cbTransferAction.setItemText(1, _translate("mapbioPorter", "Create Heritage 1.x Archive", None))
        self.cbTransferAction.setItemText(2, _translate("mapbioPorter", "Create Heritage 2.x Archive", None))
        self.cbTransferAction.setItemText(3, _translate("mapbioPorter", "Create Common GIS Formats Archive", None))
        self.cbTransferAction.setItemText(4, _translate("mapbioPorter", "Download New Interviews", None))
        self.cbTransferAction.setItemText(5, _translate("mapbioPorter", "Upload Completed Interviews", None))
        self.lblUserName.setText(_translate("mapbioPorter", "User Name:", None))
        self.lblPassword.setText(_translate("mapbioPorter", "Password: ", None))
        self.lblAllProgress.setText(_translate("mapbioPorter", "Overall Progress:", None))
        self.lblStepProgress.setText(_translate("mapbioPorter", "Current Step:", None))
        self.pbTransfer.setText(_translate("mapbioPorter", "Transfer Data", None))
        self.pbCancel.setText(_translate("mapbioPorter", "Cancel", None))
        self.pbClose.setText(_translate("mapbioPorter", "Close", None))

