# -*- coding: utf-8 -*-
"""
/***************************************************************************
 audioRecorder
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

class audioRecorder(QtCore.QObject):

    #
    # initialize worker

    def __init__( self, afPrefix, audioDeviceIndex, *args, **kwargs ):
        QtCore.QObject.__init__(self, *args, **kwargs)
        self.state = 'Initialized'
        self.status.emit(self.state)
        self.abort = False
        self.afPrefix = afPrefix
        self.partNum = 1
        self.audioDeviceIndex = audioDeviceIndex

    #
    # setup run loop for worker

    def run( self ):
        #partNum = 1
        try:
            self.state = 'recording'
            self.status.emit(self.state)
            while self.abort == False:
                afName = self.afPrefix + '_%d.wav' % self.partNum
                self.doRecording(afName)
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
    # set the part number for the recordings so we can support pauses
    # and consolidation after an interview completes

    def setRecordingPart(self, partNo):
        self.partNum = partNo

    #
    # do the actual recording

    def doRecording(self,fName):

        # set recording parameters
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100
        WAVE_OUTPUT_FILENAME = fName
        # create pyaudio stream object
        p = pyaudio.PyAudio()
        # set parameters and start
        stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=self.audioDeviceIndex,
                frames_per_buffer=CHUNK)
        # have array to store frames
        frames = []
        # do this as long as worker state value is set to recording
        while self.state == 'recording':
            data = stream.read(CHUNK)
            frames.append(data)
        # once recording stops close stream
        stream.stop_stream()
        stream.close()
        p.terminate()
        # save output to file
        if self.state in ('stopped','stopped with error'):
            wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()

    # set class signals
    status = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(Exception, basestring)
