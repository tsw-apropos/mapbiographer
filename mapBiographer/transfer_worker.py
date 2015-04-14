# -*- coding: utf-8 -*-
"""
/***************************************************************************
 transferContent
                                 A QGIS plugin
 Effectively conduct direct to digital map biographies and traditional land
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
import traceback, time, os, sys, inspect, datetime
import csv, json, zipfile, shutil, glob
from pyspatialite import dbapi2 as sqlite
from pydub import AudioSegment

#
# transferContent - a worker to transfer content to and from LMB

class transferContent(QtCore.QObject):

    #
    # class initialization
    
    def __init__(self,actionIdx,dirName,dbName,account,password,*args,**kwargs):

        QtCore.QObject.__init__(self,*args,**kwargs)
        self.overallPercentage = 0
        self.stepPercentage = 0
        self.actionIdx = actionIdx
        self.dirName = dirName
        self.dbName = dbName
        if account == '':
            self.account='lmb.unknown.user'
        else:
            self.account = account
        self.password = password
        self.dateTimeFormat = '%Y-%m-%dT%H:%M:%S.%f'
        # set current project
        conn = sqlite.connect(os.path.join(self.dirName,self.dbName))
        cur = conn.cursor()
        sql = "SELECT code FROM project;"
        rs = cur.execute(sql)
        self.pCode = rs.fetchall()[0][0]
        
        self.debug = False
        if self.debug == True:
            self.myself = lambda: inspect.stack()[1][3]
            QgsMessageLog.logMessage(self.myself())

    #
    # run worker
    
    def run(self):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        try:
            self.workerStatus.emit('Transfer started')
            messageText = ''
            # create transfer folder
            self.exDir = os.path.join(self.dirName,'transfer')
            if not os.path.exists(self.exDir):
                os.makedirs(self.exDir,0755)
            # create project folder
            self.exProjDir = os.path.join(self.exDir,self.pCode)
            if not os.path.exists(self.exProjDir):
                os.makedirs(self.exProjDir,0755)
            # proceed with different folder export formats
            if self.actionIdx == 1:
                # create heritage 1.x archive
                # create a destination directory if needed
                exDir = os.path.join(self.exProjDir,'heritage1')
                if not os.path.exists(exDir):
                    os.makedirs(exDir,0755)
                # export the files
                self.exportToHeritageV1(exDir)
            elif self.actionIdx == 2:
                # create heritage 2.x archive
                exDir = os.path.join(self.exProjDir,'heritage2')
                if not os.path.exists(exDir):
                    os.makedirs(exDir,0755)
                self.exportToHeritageV2(exDir)
            elif self.actionIdx == 3:
                # create common GIS formats archive
                # create internal structure for different archive types
                exDir = os.path.join(self.exProjDir,'commongis')
                if not os.path.exists(exDir):
                    os.makedirs(exDir,0755)
                self.exportToGIS(exDir)
            elif self.actionIdx == 4:
                # download new interviews
                exDir = os.path.join(self.exProjDir,'heritage2')
                if not os.path.exists(exDir):
                    os.makedirs(exDir,0755)
                messageTex = "Not implemented yet"
                raise Exception('incomplete error')
            elif self.actionIdx == 5:
                # upload completed interviews
                exDir = os.path.join(self.exProjDir,'heritage2')
                if not os.path.exists(exDir):
                    os.makedirs(exDir,0755)
                messageTex = "Not implemented yet"
                raise Exception('incomplete error')
            self.workerStatus.emit('Completed')
            self.workerFinished.emit(True,messageText)
        except Exception, e:
            import traceback
            if messageText == '':
                messageText == 'An error occurred'
            self.workerError.emit(e, traceback.format_exc(),messageText)
            self.workerFinished.emit(False,messageText)
        self.kill()

    #
    # kill worker

    def kill(self):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        self.abort = True

    #
    # update overall transfer progress

    def progressUpdateOverall(self,currentStepNumber):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        self.overallPercentage = currentStepNumber / float(self.stepCount) * 100
        self.progressAll.emit(self.overallPercentage)


    #
    # File Management
    #
    
    #
    # remover files in list

    def removeFilesInList(self, dirList):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        for entry in dirList:
            if os.path.isdir(entry):
                nDirList = glob.glob(entry+'/*')
                self.removeFilesInList(nDirList)
                os.rmdir(entry)
            else:
                self.removeNonZipFile(entry)

    #
    # remove file

    def removeNonZipFile(self, fName):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        fRoot,fExt = os.path.splitext(fName)
        if fExt <> '.zip':
            os.remove(fName)
    
    #
    # create zip archive
    
    def zipArchiveMake(self, srcPath, fName, excludeFileType=None, includeFileType=None):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        fzip = zipfile.ZipFile(fName, 'w', zipfile.ZIP_DEFLATED)
        abs_src = os.path.abspath(srcPath)
        for dirname, subdirs, files in os.walk(srcPath):
            for filename in files:
                if excludeFileType <> None:
                    if os.path.splitext(filename)[1] <> excludeFileType:
                        absname = os.path.abspath(os.path.join(dirname, filename))
                        arcname = absname[len(abs_src) + 1:]
                        fzip.write(absname, arcname)
                elif includeFileType <> None:
                    if os.path.splitext(filename)[1] == includeFileType:
                        absname = os.path.abspath(os.path.join(dirname, filename))
                        arcname = absname[len(abs_src) + 1:]
                        fzip.write(absname, arcname)
                else:
                    absname = os.path.abspath(os.path.join(dirname, filename))
                    arcname = absname[len(abs_src) + 1:]
                    fzip.write(absname, arcname)
        fzip.close()

    #
    # create mp3 audio file

    def mp3Create(self, srcFile, destFile):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        if os.name == 'posix':
            src = AudioSegment.from_wav(srcFile)
            src.export(destFile, format='mp3')
        else:
            exeName = 'c:/Program Files/ffmpeg/bin/ffmpeg.exe'
            if os.path.exists(exeName):
                callList = [exeName,'-i',srcFile,destFile]
                p = subprocess.Popen(callList, stdout=open(os.devnull,'wb'), stdin=subprocess.PIPE, stderr=open(os.devnull,'wb'),shell=True)
                p.communicate()
            else:
                return(-1)
        return(0)

    #
    # create ogg audio file

    def oggCreate(self, srcFile, destFile):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        if os.name == 'posix':
            src = AudioSegment.from_wav(srcFile)
            src.export(destFile, format='ogg')
        else:
            exeName = 'c:/Program Files/ffmpeg/bin/ffmpeg.exe'
            if os.path.exists(exeName):
                callList = [exeName,'-i',srcFile,destFile]
                p = subprocess.Popen(callList, stdout=open(os.devnull,'wb'), stdin=subprocess.PIPE, stderr=open(os.devnull,'wb'),shell=True)
                p.communicate()
            else:
                return(-1)
        return(0)
        

    #
    # Export Management
    #

    #
    # export interviews to LOUIS Heritage v1 format archvie

    def exportToHeritageV1(self,exDir):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # progress notification
        self.stepCount = 2
        self.progressUpdateOverall(1)
        self.workerStatus.emit('Creating Project Files')
        # get project information
        conn = sqlite.connect(os.path.join(self.dirName,self.dbName))
        cur = conn.cursor()
        sql = "SELECT code,description,note,tags, "
        sql += "content_codes,dates_and_times, "
        sql += "times_of_year,date_modified FROM project"
        rs = cur.execute(sql)
        pData = rs.fetchall()
        pCode = pData[0][0]
        # get list of interviews
        sql = "SELECT id, project_id, code, start_datetime, end_datetime, "
        sql += "description, interview_location, note, tags, data_status, "
        sql += "data_security, interviewer, date_modified FROM interviews "
        sql += "WHERE data_status == 'RC'"
        rs = cur.execute(sql)
        intvList = rs.fetchall()
        intCnt = len(intvList)
        # write project files
        # heritage users file
        pofH = os.path.join(exDir,pData[0][0]+'_users.ini')
        f = open(pofH,'w')
        f.write('[user]\n')
        f.write('username=%s\n' % self.account)
        f.write('password=passwordhidden\n')
        f.close()
        # heritage project file
        pfH = os.path.join(exDir,pData[0][0]+'.ini')
        f = open(pfH,'w')
        f.write('owner=%s\n' % self.account)
        f.write('code=%s\n' % pData[0][0])
        f.write('description=%s\n' % pData[0][1])
        f.write('note=%s\n' % pData[0][2])
        f.write('tags=%s\n' % pData[0][3])
        f.write('default_codes=%s\n' % str(pData[0][4].split('\n')).replace("u'","'"))
        f.write('default_time_periods=%s\n' % str(pData[0][4].split('\n')).replace("u'","'"))
        f.write('default_annual_variation=%s\n' % str(pData[0][6].split('\n')).replace("u'","'"))
        f.write('date_modified=%s\n' % pData[0][7])
        f.close()
        # progress notification
        self.progressUpdateOverall(1)
        self.workerStatus.emit('Exporting Interviews')
        x = 0
        lastPercent = 0.0
        intCount = len(intvList)
        for intvData in intvList:
            x += 1
            # progress notification
            buildPercent = x / float(intCount) * 100
            if int(buildPercent) > lastPercent and buildPercent <= 99.0:
                self.progressStep.emit(buildPercent)
                lastPercent = buildPercent           
            # export data
            # identify or create heritage output directory for this interview
            intvExDir = os.path.join(exDir,'doc_'+intvData[2],'images')
            if not os.path.exists(intvExDir):
                os.makedirs(intvExDir, 0755)
            intvExDir = os.path.join(exDir,'doc_'+intvData[2])
            # get participants
            sql = "SELECT a.id, a.participant_code, a.first_name, a.last_name, a.email_address, "
            sql += "b.community, b.family, a.maiden_name, a.gender, a.marital_status, "
            sql += "a.birth_date, a.tags, a.note, b.date_modified "
            sql += "FROM participants a, interviewees b "
            sql += "WHERE a.id = b.participant_id AND "
            sql += "b.interview_id = %d " % intvData[0]
            rs = cur.execute(sql)
            partData = rs.fetchall()
            # export interview
            self.exportHeritageInterviewV1(intvData,partData,intvExDir,cur)
            # process multimedia
            # check if audio file exists
            srcName = os.path.join(self.dirName,intvData[2]+'.wav')
            outName = os.path.join(intvExDir,intvData[2]+'.mp3')
            if os.path.exists(srcName):
                retval = self.mp3Create(srcName,outName)
                if retval == -1:
                    messageText = 'Unable to convert audio files. '
                    if os.name <> 'posix':
                        messageText += 'Could not find\n C:\Program Files\ffmpeg\bin\ffmpeg.exe'
                    else:
                        messageText += "Confirm that pydub library is installed and functioning."
                    QtGui.QMessageBox.warning(self, 'Warning',
                           messageText, QtGui.QMessageBox.Ok)
            # compress outputs into zip file
            zipFName = intvData[2] + '_part1.zip'
            intZFileName = os.path.join(exDir,zipFName)
            self.zipArchiveMake(intvExDir, intZFileName, excludeFileType='.kml')
            zipFName = intvData[2] + '_part2.zip'
            intZFileName = os.path.join(exDir,zipFName)
            self.zipArchiveMake(intvExDir, intZFileName, includeFileType='.kml')
            # remove original files
            dirList = glob.glob(exDir+'/*')
            self.removeFilesInList(dirList)

    #
    # export interview in heritage format

    def exportHeritageInterviewV1(self,intvData,partData,outDir,cur):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # users first
        contribList = ''
        ofName = os.path.join(outDir,intvData[2]+'_users.ini')
        f = open(ofName,'w')
        for participant in partData:
            contribList += participant[1]+','
            f.write('[user]\n')
            f.write('username=%s\n' % participant[1])
            f.write('account_security=INACTIVE\n')
            f.write('active=false\n')
            f.write('password=passwordhidden\n')
            f.write('first_name=%s\n' % participant[2])
            f.write('last_name=%s\n' % participant[3])
            f.write('email=%s\n' % participant[4])
            f.write('community_affiliation=%s\n' % participant[5])
            f.write('family_group=%s\n' % participant[6])
            f.write('maiden_name=%s\n' % participant[7])
            f.write('gender=%s\n' % participant[8])
            f.write('marital_status=%s\n' % participant[9])
            f.write('birth_date=%s\n' % participant[10])
            f.write('tags=%s\n' % participant[11])
            f.write('note=%s\n' % participant[12])
            f.write('\n')
        f.close()
        contribList = contribList[:-1]
        # interview file header
        ofName = os.path.join(outDir,intvData[2]+'.ini')
        #QgsMessageLog.logMessage('printing intvData')
        #QgsMessageLog.logMessage(str(intvData))
        f = open(ofName,'w')
        f.write('owner=%s\n' % intvData[11])
        f.write('code=%s\n' % intvData[2])
        f.write('description=%s\n' % intvData[5])
        f.write('start_date=%s\n' % intvData[3])
        f.write('end_date=%s\n' % intvData[4])
        f.write('location=%s\n' % intvData[6])
        f.write('note=%s\n' % intvData[7])
        f.write('tags=%s\n' % intvData[8])
        f.write('security_code=%s\n' % intvData[10])
        f.write('date_modified=%s\n' % intvData[12])
        f.write('contributors=%s\n' % contribList)
        f.write('\n')
        # get sections
        sql = "SELECT sequence_number, section_code, section_text, note, "
        sql += "date_time, date_time_start, date_time_end, time_of_year, "
        sql += "time_of_year_months, spatial_data_source, spatial_data_scale, "
        sql += "geom_source, content_codes || ',' || tags as tags, media_start_time, media_end_time, "
        sql += "data_security, date_created, date_modified, media_files, id "
        sql += "FROM interview_sections WHERE interview_id = %d " % intvData[0]
        sql += "ORDER by sequence_number;"
        rs = cur.execute(sql)
        secData = rs.fetchall()
        firstPoint = True
        firstLine = True
        firstPolygon = True
        for section in secData:
            f.write('[section=%s]\n' % section[1])
            f.write('sequence_number=%s\n' % section[0])
            if section[2] == None:
                f.write('section_text=\n')
            else:
                f.write('section_text=%s\n' % section[2])
            if section[3] == None:
                f.write('note=\n')
            else:
                f.write('note=%s\n' % section[3])
            if section[4] in ['R','U','N','SP']:
                f.write('use_period=%s\n' % section[4])
            else:
                f.write('use_period=P\n')
                upS, upE = section[4].split(':')
                f.write('use_period_start=%s\n' % upS.strip())
                f.write('use_period_end=%s\n' % upE.strip())
            if section[7] in ['R','U','N']:
                f.write('annual_variation=%s\n' % section[7])
            else:
                f.write('annual_variation=SE\n')
                f.write('annual_variation_months=%s\n' % section[7])
            f.write('spatial_source=%s\n' % section[9])
            f.write('spatial_scale=%s\n' % section[10])
            if not section[11] in ['ns','pt','ln','pl']:
                f.write('refers_to=%s\n' % section[11])
            f.write('tags=%s\n' % section[12])
            f.write('audio_start=%s\n' % section[13][3:])
            f.write('audio_end=%s\n' % section[14][3:])
            f.write('security_code=%s\n' % section[15])
            f.write('date_created=%s\n' % section[16])
            f.write('date_modified=%s\n' % section[17])
            if not section[18] is None and section[18] <> '':
                cmFiles = section[18].split('|||')
                if len(cmFiles) > 0:
                    if cmFiles[0] == '':
                        cmFiles = cmFiles[1:]
                    imgIdx = 1
                    for item in cmFiles:
                        if '||' in item:
                            sFileName,caption = item.split('||')
                            if os.path.exists(sFileName):
                                path, sFile = os.path.split(sFileName)
                                dFileName = os.path.join(outDir,'images',sFile)
                                shutil.copy(sFileName,dFileName)
                                f.write('image%d=%s\n' % (imgIdx,sFile))
                                f.write('image%dcaption=%s\n' % (imgIdx,caption))
                                imgIdx += 1
            f.write('\n')
            if section[11] == 'pt':
                sql = "SELECT section_code, AsKml(geom) "
                sql += "FROM points WHERE interview_id = %d AND " % intvData[0]
                sql += "section_id = %d " % section[19]
                rs = cur.execute(sql)
                featData = rs.fetchall()[0]
                ofn = os.path.join(outDir,intvData[2]+'_points.kml')
                if firstPoint:
                    self.kmlFileWrite(ofn,featData,intvData[2])
                    firstPoint = False
                else:
                    self.kmlFileWrite(ofn,featData,intvData[2],True)
            elif section[11] == 'ln':
                sql = "SELECT section_code, AsKml(geom) "
                sql += "FROM lines WHERE interview_id = %d AND " % intvData[0]
                sql += "section_id = %d " % section[19]
                rs = cur.execute(sql)
                featData = rs.fetchall()[0]
                ofn = os.path.join(outDir,intvData[2]+'_lines.kml')
                if firstLine:
                    self.kmlFileWrite(ofn,featData,intvData[2])
                    firstLine = False
                else:
                    self.kmlFileWrite(ofn,featData,intvData[2],True)
            elif section[11] == 'pl':
                sql = "SELECT section_code, AsKml(geom) "
                sql += "FROM polygons WHERE interview_id = %d AND " % intvData[0]
                sql += "section_id = %d " % section[19]
                rs = cur.execute(sql)
                featData = rs.fetchall()[0]
                ofn = os.path.join(outDir,intvData[2]+'_polygons.kml')
                if firstPolygon:
                    self.kmlFileWrite(ofn,featData,intvData[2])
                    firstPolygon = False
                else:
                    self.kmlFileWrite(ofn,featData,intvData[2],True)
        f.close()

    #
    # write minimal kml file

    def kmlFileWrite(self,outFName,recordInfo,intvCode,append=False):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        if append:
            rf = open(outFName,'r')
            lns = rf.readlines()
            rf.close()
            f = open(outFName,'w')
            for ln in lns:
                if '</Document>' in ln:
                    break
                else:
                    f.write(ln)
        else:
            f = open(outFName,'w')
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<kml xmlns="http://www.opengis.net/kml/2.2">\n')
            f.write("    <Document>\n")
            f.write("        <name>Heritage Features</name>\n")
        f.write("        <Placemark>\n")
        f.write("            <name>%s</name>\n" % recordInfo[0])
        f.write("            <description>Feature from %s</description>\n" % intvCode)
        f.write("            %s\n" % recordInfo[1])
        f.write("        </Placemark>\n")
        f.write("    </Document>\n")
        f.write("</kml>\n")
        f.close()

    #
    # export interviews to LOUIS Heritage v2 format archive

    def exportToHeritageV2(self,exDir):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # create images directory
        imageDir = os.path.join(exDir,'images')
        if not os.path.exists(imageDir):
            os.makedirs(imageDir,0755)
        # progress notification
        self.stepCount = 8
        self.progressUpdateOverall(1)
        self.workerStatus.emit('Creating Project Dictionary')
        # get project information
        conn = sqlite.connect(os.path.join(self.dirName,self.dbName))
        cur = conn.cursor()
        # create dictionary shell
        projDict = {'project': {}, 'interviews': {}, 'interview_sections': {}, \
                    'interviewees': {}, 'participants': {}, 'addresses': {}, \
                    'telecoms': {}}
        # project 
        sql = "SELECT code,description,note,tags, "
        sql += "content_codes,dates_and_times, "
        sql += "times_of_year,date_modified FROM project"
        rs = cur.execute(sql)
        pData = rs.fetchall()
        pCode = pData[0][0]
        projDict['project'] = {'code': pCode, 'description': pData[0][1], \
            'note': pData[0][2], 'tags': pData[0][3], \
            'content_codes': pData[0][4], 'dates_and_times': pData[0][5], \
            'times_of_year': pData[0][6], 'date_modified': pData[0][7]}
        self.progressUpdateOverall(2)
        self.workerStatus.emit('Exporting Interviews')
        # interviews
        projDict['interviews'] = {'recs': {}}
        sql = "SELECT id, project_id, code, start_datetime, end_datetime, "
        sql += "description, interview_location, note, tags, data_status, "
        sql += "data_security, interviewer, date_modified FROM interviews "
        sql += "WHERE data_status == 'RC'"
        rs = cur.execute(sql)
        intvList = rs.fetchall()
        x = 0
        lastPercent = 0.0
        recCount = len(intvList)
        for intv in intvList:
            x += 1
            buildPercent = x / float(recCount) * 100
            if int(buildPercent) > lastPercent and buildPercent <= 99.0:
                self.progressStep.emit(buildPercent)
                lastPercent = buildPercent           
            projDict['interviews']['recs'][x] = {'id': intv[0], \
                'project_id': intv[1], 'code': intv[2], \
                'start_datetime':intv[3], 'end_datetime':intv[4], \
                'description':intv[5], 'interview_location':intv[6], \
                'note': intv[7], 'tags':intv[8], 'data_security':intv[10], \
                'interviewer':intv[11], 'date_modified': intv[12]}
            # convert audio if available
            srcName = os.path.join(self.dirName,intv[2]+'.wav')
            outName = os.path.join(exDir,intv[2]+'.ogg')
            if os.path.exists(srcName):
                retval = self.oggCreate(srcName,outName)
                if retval == -1:
                    messageText = 'Unable to convert audio files. '
                    if os.name <> 'posix':
                        messageText += 'Could not find\n C:\Program Files\ffmpeg\bin\ffmpeg.exe'
                    else:
                        messageText += "Confirm that pydub library is installed and functioning."
                    QtGui.QMessageBox.warning(self, 'Warning',
                           messageText, QtGui.QMessageBox.Ok)
        # interview sections and their geometry
        self.progressUpdateOverall(3)
        self.workerStatus.emit('Exporting Interview Sections')
        projDict['interview_sections'] = {'recs': {}}
        sql = "SELECT b.id, b.interview_id, b.sequence_number, "
        sql += "b.section_code, b.section_text, b.note, "
        sql += "b.date_time, b.time_of_year, b.spatial_data_source, "
        sql += "b.spatial_data_scale, b.geom_source, b.content_codes, "
        sql += "b.media_start_time, b.media_end_time, b.data_security, "
        sql += "b.media_files, b.date_modified "
        sql += "FROM interviews a, interview_sections b "
        sql += "WHERE a.id = b.interview_id AND a.data_status == 'RC'"
        rs = cur.execute(sql)
        secList = rs.fetchall()
        x = 0
        lastPercent = 0.0
        recCount = len(secList)
        for sec in secList:
            x += 1
            buildPercent = x / float(recCount) * 100
            if int(buildPercent) > lastPercent and buildPercent <= 99.0:
                self.progressStep.emit(buildPercent)
                lastPercent = buildPercent           
            # set values for date and time start and end
            if sec[6] in ['R','U','N','SP']:
                dtV = sec[6]
                dtS = ''
                dtE = ''
            else:
                dtV = 'P'
                dtS, dtE = sec[6].split(':')
                dtS = dtS.strip()
                dtE = dtE.strip()
            # set values for time of year
            if sec[7] in ['R','U','N']:
                toyV = sec[7]
                toyM = ''
            else:
                toyV = 'SE'
                toyM = sec[7]
            # get geometry or reference
            if sec[10] == 'pt':
                sql = "SELECT id, interview_id, section_id, section_code, "
                sql += "AsGeoJSON(geom) FROM points WHERE section_code = '%s'" % sec[3]
                rs = cur.execute(sql)
                geoText = rs.fetchall()[0][4]
            elif sec[10] == 'ln':
                sql = "SELECT id, interview_id, section_id, section_code, "
                sql += "AsGeoJSON(geom) FROM lines WHERE section_code = '%s'" % sec[3]
                rs = cur.execute(sql)
                geoText = rs.fetchall()[0][4]
            elif sec[10] == 'pl':
                sql = "SELECT id, interview_id, section_id, section_code, "
                sql += "AsGeoJSON(geom) FROM polygons WHERE section_code = '%s'" % sec[3]
                rs = cur.execute(sql)
                geoText = rs.fetchall()[0][4]
            elif sec[10] == 'ns':
                geoText = ''
            else:
                geoText = sec[10]
            # copy media files
            imageInfo = []
            if not sec[15] is None and sec[15] <> '':
                cmFiles = sec[15].split('|||')
                if len(cmFiles) > 0:
                    if cmFiles[0] == '':
                        cmFiles = cmFiles[1:]
                    for item in cmFiles:
                        if '||' in item:
                            sFileName,caption = item.split('||')
                            if os.path.exists(sFileName):
                                path, sFile = os.path.split(sFileName)
                                dFileName = os.path.join(imageDir,sFile)
                                shutil.copy(sFileName,dFileName)
                                imageInfo.append([sFile,caption])
            # create dictionary record
            projDict['interview_sections']['recs'][x] = {
                'id':sec[0],'interview_id':sec[1],'sequence_number':sec[2], \
                'section_code':sec[3],'section_text':sec[4],'note':sec[5], \
                'date_time':dtV,'date_time_start':dtS,'date_time_end':dtE, \
                'time_of_year':toyV,'time_of_year_months':toyM, \
                'spatial_data_source':sec[8],'spatial_data_scale':sec[9],
                'geomText':geoText,'content_codes':sec[11], \
                'media_start_time':sec[12],'media_end_time':sec[13], \
                'data_security':sec[14],'media_files':imageInfo,'date_modified':sec[16]}
        # interviewees
        self.progressUpdateOverall(4)
        self.workerStatus.emit('Exporting Interviewees')
        projDict['interviewees'] = {'recs': {}}
        sql = "SELECT a.id, a.interview_id, a.participant_id, "
        sql += "a.community, a.family, a.date_modified "
        sql += "FROM interviewees a, interviews b "
        sql += "WHERE a.interview_id = b.id AND b.data_status == 'RC'"
        rs = cur.execute(sql)
        intvEList = rs.fetchall()
        x = 0
        lastPercent = 0.0
        recCount = len(intvEList)
        for rec in intvEList:
            x += 1
            buildPercent = x / float(recCount) * 100
            if int(buildPercent) > lastPercent and buildPercent <= 99.0:
                self.progressStep.emit(buildPercent)
                lastPercent = buildPercent           
            projDict['interviewees']['recs'][x] = {'id':rec[0], \
                'interview_id':rec[1],'participant_id':rec[2], \
                'community':rec[3],'family':rec[4],'date_modified':rec[5]}
        # participants
        self.progressUpdateOverall(5)
        self.workerStatus.emit('Exporting Participants')
        projDict['participants'] = {'recs': {}}
        sql = "SELECT a.id, a.participant_code, a.first_name, "
        sql += "a.last_name, a.email_address, a.community, "
        sql += "a.family, a.maiden_name, a.gender, a.birth_date, a.tags, "
        sql += "a.note, a.date_modified "
        sql += "FROM participants a, interviewees b, interviews c "
        sql += "WHERE a.id = b.participant_id AND "
        sql += "b.interview_id = c.id AND c.data_status == 'RC'"
        rs = cur.execute(sql)
        partList = rs.fetchall()
        x = 0
        lastPercent = 0.0
        recCount = len(partList)
        for part in partList:
            x += 1
            buildPercent = x / float(recCount) * 100
            if int(buildPercent) > lastPercent and buildPercent <= 99.0:
                self.progressStep.emit(buildPercent)
                lastPercent = buildPercent           
            projDict['participants']['recs'][x] = {'id':part[0], \
                'participant_code':part[1],'first_name':part[2], \
                'last_name':part[3],'email':part[4],'community':part[5], \
                'family':part[6],'maiden_name':part[7],'gender':part[8], \
                'birth_date':part[9],'tags':part[10],'note':part[11], \
                'date_modified':part[12]}
        # addresses
        self.progressUpdateOverall(6)
        self.workerStatus.emit('Exporting Addresses')
        projDict['addresses'] = {'recs': {}}
        sql = "SELECT a.id, a.participant_id, a.address_type, "
        sql += "a.line_one, a.line_two, a.city, "
        sql += "a.province, a.country, a.postal_code, a.date_modified "
        sql += "FROM addresses a, participants b, interviewees c, interviews d "
        sql += "WHERE b.id = a.participant_id AND b.id = c.participant_id AND "
        sql += "c.interview_id = d.id AND d.data_status == 'RC'"
        rs = cur.execute(sql)
        addrList = rs.fetchall()
        x = 0
        lastPercent = 0.0
        recCount = len(addrList)
        for addr in addrList:
            x += 1
            buildPercent = x / float(recCount) * 100
            if int(buildPercent) > lastPercent and buildPercent <= 99.0:
                self.progressStep.emit(buildPercent)
                lastPercent = buildPercent           
            projDict['addresses']['recs'][x] = {'id':addr[0], \
                'participant_id':addr[1],'address_type':addr[2], \
                'line_one':addr[3],'line_two':addr[4],'city':addr[5], \
                'province':addr[6],'country':addr[7],'postal_code':addr[8], \
                'date_modified':addr[9]}
        # telecoms
        self.progressUpdateOverall(7)
        self.workerStatus.emit('Exporting Telecoms')
        projDict['telecoms'] = {'recs': {}}
        sql = "SELECT a.id, a.participant_id, a.telecom_type, "
        sql += "a.telecom, a.date_modified "
        sql += "FROM telecoms a, participants b, interviewees c, interviews d "
        sql += "WHERE b.id = a.participant_id AND b.id = c.participant_id AND "
        sql += "c.interview_id = d.id AND d.data_status == 'RC'"
        rs = cur.execute(sql)
        teleList = rs.fetchall()
        x = 0
        lastPercent = 0.0
        recCount = len(teleList)
        for tele in teleList:
            x += 1
            buildPercent = x / float(recCount) * 100
            if int(buildPercent) > lastPercent and buildPercent <= 99.0:
                self.progressStep.emit(buildPercent)
                lastPercent = buildPercent           
            projDict['telecoms']['recs'][x] = {'id':tele[0], \
                'participant_id':tele[1],'telecom_type':tele[2], \
                'telecom':addr[3],'date_modified':tele[4]}
        # commit dictionary to disk
        projFile = os.path.join(exDir,pCode+'_heritage2.json')
        f = open(projFile,'w')
        f.write(json.dumps(projDict))
        f.close()
        # progress notification
        self.progressUpdateOverall(8)
        self.workerStatus.emit('Compressing Archive')
        # compress outputs into zip file
        zipFName = self.pCode + '.zip'
        intZFileName = os.path.join(exDir,zipFName)
        self.zipArchiveMake(exDir, intZFileName, excludeFileType='.zip')
        # remove original files
        dirList = glob.glob(exDir+'/*')
        self.removeFilesInList(dirList)

    #
    # export interviews to common GIS formats archive

    def exportToGIS(self,exDir):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # progress notification
        self.stepCount = 2
        self.progressUpdateOverall(1)
        self.workerStatus.emit('Creating Project Files')
        # get project information
        # get project information
        conn = sqlite.connect(os.path.join(self.dirName,self.dbName))
        cur = conn.cursor()
        sql = "SELECT code,description,note,tags, "
        sql += "default_codes,dates_and_times, "
        sql += "times_of_year,date_modified FROM project"
        rs = cur.execute(sql)
        pData = rs.fetchall()
        pCode = pData[0][0]
        # get list of interviews
        sql = "SELECT id, project_id, code, start_datetime, end_datetime, "
        sql += "description, interview_location, note, tags, data_status, "
        sql += "data_security, interviewer, date_modified FROM interviews "
        sql += "WHERE data_status == 'RC'"
        rs = cur.execute(sql)
        intvList = rs.fetchall()
        intCnt = len(intvList)
        # write project files
        # json users file
        pofJ= os.path.join(exDir,pData[0][0]+'_users.json')
        f = open(pofJ,'w')
        f.write('{"users":[{\n')
        f.write('    "%s":[{\n' % self.account)
        f.write('        "password":"passwordhidden"\n')
        f.write('    }]\n}]}\n')
        f.close()
        # json project file
        pfJ = os.path.join(exDir,pData[0][0]+'.json')
        f = open(pfJ,'w')
        f.write('{"attributes":[{\n')
        f.write('    "owner":"%s",\n' % self.account)
        f.write('    "code":"%s",\n' % pData[0][0])
        f.write('    "description":"%s",\n' % pData[0][1])
        f.write('    "note":"%s",\n' % pData[0][2])
        f.write('    "tags":"%s",\n' % pData[0][3])
        f.write('    "default_codes":"%s",\n' % str(pData[0][4].split('\n')).replace('[','{').replace(']','}').replace("u'","'"))
        f.write('    "default_time_periods":"%s",\n' % str(pData[0][5].split('\n')).replace('[','{').replace(']','}').replace("u'","'"))
        f.write('    "default_annual_variation":"%s",\n' % str(pData[0][6].split('\n')).replace('[','{').replace(']','}').replace("u'","'"))
        f.write('    "date_modified":"%s"\n' % pData[0][7])
        f.write('}]}\n')
        f.close()
        x = 0
        lastPercent = 0.0
        intCount = len(intvList)
        for intvData in intvList:
            x += 1
            # progress notification
            buildPercent = x / float(intCount) * 100
            if int(buildPercent) > lastPercent and buildPercent <= 99.0:
                self.progressStep.emit(buildPercent)
                lastPercent = buildPercent           
            # export data
            # identify or create heritage output directory for this interview
            intvExDir = os.path.join(exDir,'doc_'+intvData[2],'images')
            if not os.path.exists(intvExDir):
                os.makedirs(intvExDir, 0755)
            intvExDir = os.path.join(exDir,'doc_'+intvData[2])
            # get participants
            sql = "SELECT a.id, a.participant_code, a.first_name, a.last_name, a.email_address, "
            sql += "b.community, b.family, a.maiden_name, a.gender, a.marital_status, "
            sql += "a.birth_date, a.tags, a.note, b.date_modified "
            sql += "FROM participants a, interviewees b "
            sql += "WHERE a.id = b.participant_id AND "
            sql += "b.interview_id = %d " % intvData[0]
            rs = cur.execute(sql)
            partData = rs.fetchall()
            # export interview
            self.exportJSONInterview(intvData,partData,intvExDir,cur)
            self.convertGeoJSONToShape(intvExDir)
             # process multimedia
            # check if audio file exists
            wfName = os.path.join(self.dirName,intvData[2]+'.wav')
            mp3Name = os.path.join(intvExDir,intvData[2]+'.mp3')
            if os.path.exists(wfName):
                self.mp3Create(wfName,mp3Name)
            # compress outputs into zip file
            zipFName = intvData[2] + '.zip'
            intZFileName = os.path.join(exDir,zipFName)
            self.zipArchiveMake(intvExDir, intZFileName)
            # remove original files
            dirList = glob.glob(exDir+'/*')
            self.removeFilesInList(dirList)

    #
    # export interview in json format

    def exportJSONInterview(self,intvData,partData,outDir,cur):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # users first
        contribList = ''
        ofName = os.path.join(outDir,intvData[2]+'_users.json')
        f = open(ofName,'w')
        f.write('{"users":[{\n')
        for participant in partData:
            f.write(',')
            contribList += participant[1]+','
            f.write('    "%s":[{\n' % participant[1])
            f.write('        "account_security":"INACTIVE",\n')
            f.write('        "active":"false",\n')
            f.write('        "password":"passwordhidden",\n')
            f.write('        "first_name":"%s",\n' % participant[2])
            f.write('        "last_name":"%s",\n' % participant[3])
            f.write('        "email":"%s",\n' % participant[4])
            f.write('        "community_affiliation":"%s",\n' % participant[5])
            f.write('        "family_group":"%s",\n' % participant[6])
            f.write('        "maiden_name":"%s",\n' % participant[7])
            f.write('        "gender":"%s",\n' % participant[8])
            f.write('        "marital_status":"%s",\n' % participant[9])
            f.write('        "birth_date":"%s",\n' % participant[10])
            f.write('        "tags":"%s",\n' % participant[11])
            f.write('        "note":"%s"\n' % participant[12])
            f.write('    }]\n')
        f.write('}]}\n')
        f.close()
        contribList = contribList[:-1]
        # interview file header
        ofName = os.path.join(outDir,intvData[2]+'.json')
        f = open(ofName,'w')
        f.write('{"attributes":[{\n')
        f.write('    "interviewer":"%s",\n' % intvData[11])
        f.write('    "code":"%s",\n' % intvData[2])
        f.write('    "description":"%s",\n' % intvData[5])
        f.write('    "start_date":"%s",\n' % intvData[3])
        f.write('    "end_date":"%s",\n' % intvData[4])
        f.write('    "location":"%s",\n' % intvData[6])
        f.write('    "note":"%s",\n' % intvData[7])
        f.write('    "tags":"%s",\n' % intvData[8])
        f.write('    "security_code":"%s",\n' % intvData[10])
        f.write('    "date_modified":"%s",\n' % intvData[12])
        f.write('    "contributors":"%s",\n' % contribList)
        f.write('    "sections":[{\n')
        # get sections
        sql = "SELECT sequence_number, section_code, section_text, note, "
        sql += "date_time, date_time_start, date_time_end, time_of_year, "
        sql += "time_of_year_months, spatial_data_source, spatial_data_scale, "
        sql += "geom_source, content_codes || ',' || tags as tags, media_start_time, media_end_time, "
        sql += "data_security, date_created, date_modified, media_files, id, "
        sql += "content_codes, tags as othertags "
        sql += "FROM interview_sections WHERE interview_id = %d " % intvData[0]
        sql += "ORDER by sequence_number;"
        rs = cur.execute(sql)
        secData = rs.fetchall()
        firstPoint = True
        firstLine = True
        firstPolygon = True
        firstSection = True
        for section in secData:
            if firstSection:
                firstSection = False
            else:
                f.write(',')
            f.write('        "%s":[{\n' % section[1])
            f.write('        "sequence_number":"%s",\n' % section[0])
            f.write('        "section_text":"%s",\n' % section[2])
            f.write('        "note":"%s",\n' % section[3])
            f.write('        "date_time":"%s",\n' % section[4])
            f.write('        "time_of_year":"%s",\n' % section[7])
            f.write('        "spatial_data_source":"%s",\n' % section[9])
            f.write('        "spatial_data_scale":"%s",\n' % section[10])
            f.write('        "geom_source":"%s",\n' % section[11])
            f.write('        "tags":"%s",\n' % section[12])
            f.write('        "media_start_time":"%s",\n' % section[13])
            f.write('        "media_end_time":"%s",\n' % section[14])
            f.write('        "data_security":"%s",\n' % section[15])
            f.write('        "date_created":"%s",\n' % section[16])
            f.write('        "date_modified":"%s"\n' % section[17])
            f.write('    }]\n')
            ## NEED TO INSERT CODE TO TRACK FILE NAMES AND THEN CONVERT THEM
            if section[11] == 'pt':
                sql = "SELECT section_code, AsGeoJSON(Transform(geom,4326)) "
                sql += "FROM points WHERE interview_id = %d AND " % intvData[0]
                sql += "section_id = %d " % section[19]
                rs = cur.execute(sql)
                featData = rs.fetchall()[0]
                ofn = os.path.join(outDir,intvData[2]+'_points.geojson')
                if firstPoint:
                    self.geojsonFileWrite(ofn,featData,intvData[2],section)
                    firstPoint = False
                else:
                    self.geojsonFileWrite(ofn,featData,intvData[2],section,True)
            elif section[11] == 'ln':
                sql = "SELECT section_code, AsGeoJSON(Transform(geom,4326)) "
                sql += "FROM lines WHERE interview_id = %d AND " % intvData[0]
                sql += "section_id = %d " % section[19]
                rs = cur.execute(sql)
                featData = rs.fetchall()[0]
                ofn = os.path.join(outDir,intvData[2]+'_lines.geojson')
                if firstLine:
                    self.geojsonFileWrite(ofn,featData,intvData[2],section)
                    firstLine = False
                else:
                    self.geojsonFileWrite(ofn,featData,intvData[2],section,True)
            elif section[11] == 'pl':
                sql = "SELECT section_code, AsGeoJSON(Transform(geom,4326)) "
                sql += "FROM polygons WHERE interview_id = %d AND " % intvData[0]
                sql += "section_id = %d " % section[19]
                rs = cur.execute(sql)
                featData = rs.fetchall()[0]
                ofn = os.path.join(outDir,intvData[2]+'_polygons.geojson')
                if firstPolygon:
                    self.geojsonFileWrite(ofn,featData,intvData[2],section)
                    firstPolygon = False
                else:
                    self.geojsonFileWrite(ofn,featData,intvData[2],section,True)
        f.write('    }]\n}]}\n')
        f.close()
        
    #
    # write geojson file

    def geojsonFileWrite(self,outFName,recordInfo,intvCode,sData,append=False):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        if append:
            rf = open(outFName,'r')
            lns = rf.readlines()
            rf.close()
            f = open(outFName,'w')
            for ln in lns:
                if ln == '    ]\n':
                    f.write(',')
                    break
                else:
                    f.write(ln)
        else:
            f = open(outFName,'w')
            f.write('{"type":"FeatureCollection",\n')
            f.write('    "features":[\n')
        f.write('        {"type":"Feature",\n')
        f.write('            "properties":{\n')
        f.write('                "s_code":"%s",\n' % recordInfo[0])
        f.write('                "s_dt_tm":"%s",\n' % sData[4])
        f.write('                "s_tm_yr":"%s",\n' % sData[7])
        f.write('                "sptl_src":"%s",\n' % sData[9])
        f.write('                "sptl_scal":"%s",\n' % sData[10])       
        f.write('                "s_text":"%s",\n' % sData[2])
        f.write('                "s_ct_cds":"%s",\n' % sData[20])
        f.write('                "s_tags":"%s",\n' % sData[21])
        f.write('                "source":"Feature from %s"},\n' % intvCode)
        f.write('            "geometry":%s\n' % recordInfo[1])
        f.write('        }\n')
        f.write('    ]\n')
        f.write('}\n')
        f.close()

    #
    # export convert geojson files to shape files

    def convertGeoJSONToShape(self,exPath):

        fList = glob.glob(exPath+'/*.geojson')
        for fName in fList:
            inLyr = QgsVectorLayer(fName, 'src', 'ogr')
            root, ext = os.path.splitext(fName)
            ofName = root + '.shp'
            outLyr = QgsVectorLayer(ofName,'dst', 'ogr')
            srcDP = inLyr.dataProvider()
            error = QgsVectorFileWriter.writeAsVectorFormat(inLyr, ofName, "System", None, "ESRI Shapefile")


    progressAll = QtCore.pyqtSignal(int)
    progressStep = QtCore.pyqtSignal(int)
    workerStatus = QtCore.pyqtSignal(str)
    workerError = QtCore.pyqtSignal(Exception, basestring, str)
    workerFinished = QtCore.pyqtSignal(bool,str)
            
