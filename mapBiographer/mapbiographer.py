# -*- coding: utf-8 -*-
"""
/***************************************************************************
 mapBiographer
                                 A QGIS plugin
 Effectively onduct direct to digital map biographies and traditional land
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
# Import the PyQt and QGIS libraries
from PyQt4 import QtCore, QtGui
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from mapbio_settings import mapBiographerSettings
from mapbio_transcriber import mapBiographerTranscriber
import os.path


class mapBiographer:

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QtCore.QSettings().value("locale/userLocale")[0:2]
        localePath = os.path.join(self.plugin_dir, 'i18n', 'mapbiographer_{}.qm'.format(locale))

        if os.path.exists(localePath):
            self.translator = QTranslator()
            self.translator.load(localePath)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

    def initGui(self):
        # Add toolbar 
        self.toolBar = self.iface.addToolBar("LOUIS Map Biographer")
        self.toolBar.setObjectName("mapBiographer")

        # Manage Action
        self.manageAction = QtGui.QAction(
            QtGui.QIcon(":/plugins/mapbiographer/settings.png"),
            u"Manage Interviews", self.iface.mainWindow())
        # connect the action to the run method
        self.manageAction.triggered.connect(self.manage)
        self.toolBar.addAction(self.manageAction)
        
        # LMB Action
        self.lmbAction = QtGui.QAction(
            QtGui.QIcon(":/plugins/mapbiographer/interview.png"),
            u"Conduct, Import and Transcribe Interviews", self.iface.mainWindow())
        # connection action to run method
        self.lmbAction.triggered.connect(self.lmb)
        self.toolBar.addAction(self.lmbAction)

        # add to menu
        self.iface.addPluginToMenu(u"&LOUIS Map Biographer", self.manageAction)
        self.iface.addPluginToMenu(u"&LOUIS Map Biographer", self.lmbAction)

    def unload(self):
        # Remove the plugin menu item and icon
        self.iface.removePluginMenu(u"&LOUIS Map Biographer", self.manageAction)
        self.iface.removePluginMenu(u"&LOUIS Map Biographer", self.lmbAction)

        # remove tool bar
        self.toolBar.hide()
        self.toolBar = None

    # open settings dialog
    def manage(self):

        # Create the dialog (after translation) and keep reference
        self.dlg = mapBiographerSettings(self.iface)
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()

    # open lmb operations panel
    def lmb(self):

        # save tool bar and panel state
        geom = self.iface.mainWindow().saveGeometry()
        state = self.iface.mainWindow().saveState()
        s = QtCore.QSettings()
        s.setValue('mapBiographer/geom', geom)
        s.setValue('mapBiographer/state', state)
        # hide everything
        interfaceObjects = self.iface.mainWindow().children()
        for obj in interfaceObjects:
            if 'QDockWidget' in str(obj.__class__):
                if obj.isVisible() == True:
                    obj.hide()
            elif 'QToolBar' in str(obj.__class__):
                if obj.isVisible() == True:
                    obj.hide()
            elif 'PythonConsole' in str(obj.__class__):
                if obj.isVisible() == True:
                    obj.hide()
        # display panel
        self.panel = mapBiographerTranscriber(self.iface)
  
