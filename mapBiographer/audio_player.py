# -*- coding: utf-8 -*-
"""
/***************************************************************************
 audioPlayer
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

from qgis.core import *
from PyQt4 import QtCore, QtGui
import traceback, datetime, time, os, math, sys
import pyaudio
import wave

#
# setup audio thread
#

class audioPlayer(QtCore.QObject):

    #
    # initialize worker

    def __init__( self, afName, audioDeviceIndex, startPoint, endPoint, *args, **kwargs ):
        QtCore.QObject.__init__(self, *args, **kwargs)
        self.state = 'Initialized'
        self.status.emit(self.state)
        self.abort = False
        self.afName = afName
        self.audioDeviceIndex = audioDeviceIndex
        self.startPoint = startPoint
        self.endPoint = endPoint

    #
    # setup run loop for worker

    def run( self ):
        try:
            self.state = 'playing'
            self.status.emit(self.state)
            while self.abort == False:
                self.doPlaying(self.afName,self.startPoint,self.endPoint)
            if self.abort == True:
                self.status.emit(self.state)
        except Exception, e:
            import traceback
            self.error.emit(e, traceback.format_exc())
            self.state = 'stopped with error'
            self.status.emit(self.state)

    #
    # have means to kill process and stop recording appropriately

    def kill( self ):
        self.abort = True
        self.state ='stopped'

    #
    # do the actual recording

    def doPlaying(self,fName,startPoint,endPoint):

        # set recording parameters
        CHUNK = 1024
        # open wave file
        wf = wave.open(self.afName, 'rb')
        # convert start and end in seconds to file references
        fr = wf.getframerate()
        fStart = startPoint * fr
        fEnd = endPoint * fr
        # create pyaudio stream object
        p = pyaudio.PyAudio()
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True)
        wf.setpos(fStart)
        # do this as long as worker state value is set to recording
        data = wf.readframes(CHUNK)
        pos = wf.tell()
        while data != '' and pos <= fEnd and self.state == 'playing':
            stream.write(data)
            data = wf.readframes(CHUNK)
            pos = wf.tell()
            self.progress.emit(int(pos/fr))
        # once recording stops close stream
        stream.stop_stream()
        stream.close()
        p.terminate()
        wf.close()
        # stop process
        self.kill()

    # set class signals
    status = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(Exception, basestring)
    progress = QtCore.pyqtSignal(int)

