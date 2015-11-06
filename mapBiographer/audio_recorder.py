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
import pyaudio, wave

#
# setup audio thread
#

class audioRecorder(QtCore.QObject):

    #
    # initialize worker

    def __init__( self, dirName, afPrefix, audioDeviceIndex, paRecordInstance, afName, *args, **kwargs ):

        QtCore.QObject.__init__(self, *args, **kwargs)
        self.state = 'Initialized'
        self.status.emit(self.state)
        self.abort = False
        self.merge = False
        self.afPrefix = afPrefix
        self.dirName = dirName
        self.partNum = 1
        self.afName = afName
        self.audioDeviceIndex = audioDeviceIndex
        self.paRecordInstance = paRecordInstance
        #
        # have two options for writing audio files
        #   bufferedWrite = True - stores data in memory and then writes file
        #   bufferedWrite = False - writes continually to disk
        #
        self.bufferedWrite = True

    #
    # setup run loop for worker

    def run( self ):

        try:
            self.state = 'recording'
            self.status.emit(self.state)
            while self.abort == False:
                afName = self.afPrefix + '-%03d.wav' % self.partNum
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

    def stop( self ):
        self.abort = True
        self.state ='stopped'
        self.status.emit(self.state)

    #
    # have means to kill process, stop recording and consolidate recordings

    def stopNMerge( self ):
        self.merge = True
        self.stop()

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
        # set parameters and start
        stream = self.paRecordInstance.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=self.audioDeviceIndex,
                frames_per_buffer=CHUNK)

        if self.bufferedWrite == True:
            # option 1 - store to array and then write to file
            # have array to store frames
            frames = []
            # do this as long as worker state value is set to recording
            while self.state == 'recording':
                data = stream.read(CHUNK)
                frames.append(data)
            # once recording stops close stream
            stream.stop_stream()
            stream.close()
            # save output to file
            if self.state in ('stopped','stopped with error'):
                wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(self.paRecordInstance.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
                wf.close()
        else:
            # option 2 - write to disk as it happens should increase system
            # robustness assuming disk can handle continual writing
            # create output file
            wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(self.paRecordInstance.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            # do this as long as worker state value is set to recording
            while self.state == 'recording':
                data = stream.read(CHUNK)
                wf.writeframes(data)
            # grab anything else that might be coming in 
            data = stream.read(CHUNK)
            # once recording stops close stream
            stream.stop_stream()
            stream.close()
            # write last data chunk
            wf.writeframes(data)
            # save output to file
            wf.close()
            # consolidate if appropriate
        if self.merge == True:
            self.consolidateRecordings()

    #
    # consolidate audio - merge different audio files for an interview together

    def consolidateRecordings(self):

        # get list of audio files
        contents = os.listdir(os.path.join(self.dirName,"media"))
        cCnt = len(self.afName)
        match1 = [elem for elem in contents if elem[:cCnt] == self.afName]
        inFiles = [elem for elem in match1 if elem[len(elem)-4:] == '.wav']
        inFiles.sort()
        outFName = self.afPrefix+'.wav'
        if len(inFiles) == 1:
            # rename existing file
            os.rename(os.path.join(self.dirName,"media",inFiles[0]),outFName)
        elif len(inFiles) > 1   :
            output = wave.open(outFName, 'wb')
            x = 1
            for infile in inFiles:
                fileName = os.path.join(self.dirName,"media",infile)
                w = wave.open(fileName, 'rb')
                # write output file
                if x == 1:
                    output.setparams(w.getparams())
                    x += 1
                output.writeframes(w.readframes(w.getnframes()))
                w.close()
            output.close()
            # delete source files
            for inFile in inFiles:
                os.remove(os.path.join(self.dirName,"media",inFile))

    # set class signals
    status = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(Exception, basestring)
