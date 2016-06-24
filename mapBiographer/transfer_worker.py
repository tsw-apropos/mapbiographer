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
import traceback, time, os, sys, inspect, datetime, subprocess
import csv, json, zipfile, shutil, glob, urllib, urllib2
import httplib, mimetypes, mimetools, io, itertools, codecs, base64
from copy import deepcopy

#
# transferContent - a worker to transfer content to and from LMB

class transferContent(QtCore.QObject):

    #
    # class initialization
    #
    def __init__(self,actionIdx,dirName,projDict,projId,url,account,\
        password,docKeys,docList,destProjId,*args,**kwargs):

        QtCore.QObject.__init__(self,*args,**kwargs)
        self.overallPercentage = 0
        self.stepPercentage = 0
        self.actionIdx = actionIdx
        self.dirName = dirName
        self.projDict = projDict
        self.projId = projId
        self.url = url
        self.docKeys = docKeys
        self.docList = docList
        self.destProjId = destProjId
        self.customFields = self.projDict["projects"][str(self.projId)]['custom_fields']
        if account == '':
            self.account='lmb.unknown.user'
        else:
            self.account = account
        self.password = password
        self.dateTimeFormat = '%Y-%m-%dT%H:%M:%S.%f'
        
        self.debug = False
        if self.debug == True:
            self.myself = lambda: inspect.stack()[1][3]
            QgsMessageLog.logMessage(self.myself())

    #
    # run worker
    #
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
            self.exProjDir = os.path.join(self.exDir,'proj%d' % int(self.projId))
            if not os.path.exists(self.exProjDir):
                os.makedirs(self.exProjDir,0755)
            # proceed with different folder export formats
            if self.actionIdx == 1:
                # create heritage archive
                exDir = os.path.join(self.exProjDir,'heritage')
                if not os.path.exists(exDir):
                    os.makedirs(exDir,0755)
                self.stepCount = 2
                self.exportToHeritage(exDir)
            elif self.actionIdx == 2:
                # create common GIS formats archive
                # create internal structure for different archive types
                exDir = os.path.join(self.exProjDir,'gis')
                if not os.path.exists(exDir):
                    os.makedirs(exDir,0755)
                self.stepCount = 2
                self.exportToGIS(exDir)
            elif self.actionIdx == 5:
                # upload completed interviews
                exDir = os.path.join(self.exProjDir,'heritage')
                if not os.path.exists(exDir):
                    os.makedirs(exDir,0755)
                self.stepCount = 3
                self.exportToHeritage(exDir)
                self.uploadFiles(exDir)
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
    #
    def kill(self):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        self.abort = True

    #
    # update overall transfer progress
    #
    def progressUpdateOverall(self,currentStepNumber):

        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        self.overallPercentage = currentStepNumber / float(self.stepCount) * 100
        self.progressAll.emit(self.overallPercentage)


    #
    # File Management Methods
    #
    
    #
    # remove files in list
    #
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
    #
    def removeNonZipFile(self, fName):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        fRoot,fExt = os.path.splitext(fName)
        if fExt.lower() <> '.zip':
            #QgsMessageLog.logMessage(fName)
            os.remove(fName)
    
    #
    # create zip archive
    #
    def zipArchiveMake(self, srcPath, fName, excludeFileType=None, includeFileType=None):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        fzip = zipfile.ZipFile(fName, 'w', zipfile.ZIP_DEFLATED, True)
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
    # create ogg audio file
    #
    def oggCreate(self, srcFile, destFile):

        import platform
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        #
        s = QtCore.QSettings()
        rv = s.value('mapBiographer/oggencFile')
        if rv == None:
            exeName = ''
        else:
            exeName = rv
        if exeName <> '' and os.path.exists(exeName):
            callList = [exeName,srcFile,'-o',destFile]
            if platform.system() == 'Windows':
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                p = subprocess.Popen(callList, stdout=open(os.devnull,'wb'),stdin=subprocess.PIPE,stderr=open(os.devnull,'wb'),startupinfo=si)
            else:
                p = subprocess.Popen(callList, stdout=open(os.devnull,'wb'),stdin=subprocess.PIPE,stderr=open(os.devnull,'wb'))
            p.communicate()
        else:
            return(-1)
        return(0)
        

    #
    # Export Methods
    #

    #
    # export interviews from current project to LOUIS Heritage Archive
    #
    def exportToHeritage(self,exDir):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # progress notification
        self.progressUpdateOverall(1)
        self.workerStatus.emit('Gathering Project Information')
        #
        # get project information
        projFileName = os.path.join(self.dirName,'lmb-project-info.json')
        projDateTime = datetime.datetime.fromtimestamp(os.path.getmtime(projFileName))
        # process content codes
        codes = {}
        for rec in self.projDict['projects'][str(self.projId)]['default_codes']:
            codes[rec[0]] = rec[1]
        # process times of year
        timeOfYear = {}
        for rec in self.projDict['projects'][str(self.projId)]['default_time_of_year']:
            timeOfYear[rec[1]] = [int(x) for x in rec[0].split(',')]
        # process time periods
        timePeriods = {}
        for rec in self.projDict['projects'][str(self.projId)]['default_time_periods']:
            periods = rec[0].split(':')
            timePeriods[rec[1]] = {"start":periods[0].strip(), "end":periods[1].strip()}
        projInfo = {
            "code": self.projDict['projects'][str(self.projId)]['code'],
            "description": self.projDict['projects'][str(self.projId)]['description'],
            "note": self.projDict['projects'][str(self.projId)]['note'],
            "tags": ",".join(self.projDict['projects'][str(self.projId)]['tags']),
            "date_modified": datetime.datetime.now().isoformat(),
            "default_codes": codes,
            "default_time_of_year_values": timeOfYear,
            "default_time_periods": timePeriods
        }
        #
        # get document information
        #
        self.workerStatus.emit('Exporting Interviews')
        intvList = []
        for key, value in self.projDict['projects'][str(self.projId)]["documents"].iteritems():
            if value['status'] == 'T':
                intvList.append(key)
        recCount = len(intvList)
        cnt = 0
        lastPercent = 0.0
        participantIdList = []
        self.progressUpdateOverall(2)
        self.workerStatus.emit('Exporting Interviews')
        for intv in intvList:
            cnt += 1
            buildPercent = cnt / float(recCount) * 100
            if int(buildPercent) > lastPercent and buildPercent <= 99.0:
                self.progressStep.emit(buildPercent)
                lastPercent = buildPercent           
            # test if export needed
            docDict = deepcopy(self.projDict['projects'][str(self.projId)]["documents"][intv])
            zipFName = "lmb-p%d-i%d-archive.zip" % (int(self.projId),int(docDict['id']))
            intZFileName = os.path.join(exDir,zipFName)
            arcExists = False
            if os.path.exists(intZFileName):
                arcExists = True
                izfDateTime = datetime.datetime.fromtimestamp(os.path.getmtime(intZFileName))
            else:
                izfDateTime = projDateTime - datetime.timedelta(days=1)
            intvFName = "lmb-p%d-i%d-data.json" % (self.projId,docDict["id"])
            nf = os.path.join(self.dirName,"interviews",intvFName)
            if os.path.exists(nf):
                intvDateTime = datetime.datetime.fromtimestamp(os.path.getmtime(nf))
                f = open(nf,'r')
                intvDict = json.loads(f.read())
                f.close()
            else:
                intvDateTime = projDateTime - datetime.timedelta(days=1)
                intvDict = {}
            if (arcExists and (intvDateTime > izfDateTime or projDateTime > izfDateTime)) or arcExists == False:    
                # remove zip file if it exists
                if os.path.exists(intZFileName):
                    os.remove(intZFileName)
                # create document folder
                # create document directory
                docDir = os.path.join(exDir,'p%d-i%d' % (int(self.projId),int(docDict['id'])))
                if not os.path.exists(docDir):
                    os.makedirs(docDir,0755)
                # create images directory
                imageDir = os.path.join(docDir,'images')
                if not os.path.exists(imageDir):
                    os.makedirs(imageDir,0755)
                # create document dictionary
                docInfo = {
                    "id": docDict['id'],
                    "code": docDict["code"],
                    "title": docDict["title"],
                    "subject": docDict["subject"],
                    "description": docDict["description"],
                    "start_datetime": docDict["start_datetime"],
                    "end_datetime": docDict["end_datetime"],
                    "location": docDict["location"],
                    "tags": ",".join(docDict["tags"]),
                    "note": docDict["note"],
                    "default_data_security": docDict["default_data_security"],
                    "language": docDict["language"],
                    "publisher": docDict["publisher"],
                    "source": docDict["source"],
                    "citation": docDict["citation"],
                    "rights_holder": docDict["rights_holder"],
                    "rights_statement": docDict["rights_statement"],
                    "creator": docDict["creator"],
                    "multimedia_source_file": None,
                    "additional_files":[],
                    "date_modified": datetime.datetime.now().isoformat(),
                    "sections":{},
                    "participants": docDict['participants']
                }
                # add participants to list
                for key, value in docDict['participants'].iteritems():
                    participantIdList.append(value["participant_id"])
                # convert audio if available
                self.workerStatus.emit('Exporting Audio')
                intvMediaFName = "lmb-p%d-i%d-media" % (self.projId,docDict["id"])
                srcName = os.path.join(self.dirName,'media',intvMediaFName+'.wav')
                outName = os.path.join(docDir,intvMediaFName+'.ogg')
                if os.path.exists(srcName):
                    retval = self.oggCreate(srcName,outName)
                    if retval == -1:
                        messageText = 'Unable to convert audio files. '
                        messageText += "Confirm that oggenc is installed and its location set defined "
                        messageText += "the Map Biographer Manager."
                        self.workerPopup.emit(messageText,'Warning')
                    else:
                        docInfo["multimedia_source_file"] = intvMediaFName+'.ogg'
                #self.progressStep.emit(50)
                # interview sections and their geometry
                self.workerStatus.emit('Exporting Sections')
                counter = 0
                secCount = len(intvDict)
                for key, value in intvDict.iteritems():
                    counter += 1
                    #buildPercent = (counter / float(secCount) * 100 * 0.5) + 50
                    #if int(buildPercent) > lastPercent and buildPercent <= 99.0:
                    #    self.progressStep.emit(buildPercent)
                    #    lastPercent = buildPercent
                    # process dates and times
                    if value['use_period'] in ['R','U','N']:
                        dtV = value['use_period']
                        dtS = ''
                        dtE = ''
                    else:
                        dtV = 'P'
                        dtS, dtE = value['use_period'].split(':')
                        dtS = dtS.strip()
                        dtE = dtE.strip()
                    # process times of year
                    if value['time_of_year'] in ['R','U','N','SP']:
                        toyV = value['time_of_year']
                        toyM = ''
                    else:
                        toyV = 'P'
                        toyM = [int(x) for x in value['time_of_year'].split(',')]
                        #toyM = value['time_of_year']
                    # process geom and geom source
                    if value['geom_source'] in ('pt','ln','pl'):
                        #QgsMessageLog.logMessage(key)
                        geom = QgsGeometry.fromWkt(value["the_geom"])
                        if value['geom_source'] == 'pt':
                            if geom.isMultipart() == True:
                                simpleGeom = QgsGeometry.fromPoint(geom.asMultiPoint()[0])
                            else:
                                simpleGeom = geom
                        elif value['geom_source'] == 'ln':
                            if geom.isMultipart() == True:
                                simpleGeom = QgsGeometry.fromPolyline(geom.asMultiPolyline()[0])
                            else:
                                simpleGeom = geom
                        else:
                            if geom.isMultipart() == True:
                                simpleGeom = QgsGeometry.fromPolygon(geom.asMultiPolygon()[0])
                            else:
                                simpleGeom = geom
                        geomText = json.loads(simpleGeom.exportToGeoJSON())
                        geomSource = ""
                    else:
                        geomText = None
                        if value["geom_source"] <> 'ns':
                            geomSource = value["geom_source"]
                        else:
                            geomSource = ""
                    # modify media files to include path
                    mediaFiles = []
                    for rec in value['media_files']:
                        mediaFiles.append(['images/'+rec[0],rec[1]])
                    # process scale
                    if value['spatial_data_scale'] == "":
                        spatialScale = None
                    else:
                        spatialScale = value['spatial_data_scale']
                    # create section dictionary
                    sectionDict = {
                        "primary_code": value['code_type'],
                        "code_integer": value['code_integer'],
                        "data_security": value['data_security'],
                        "legacy_code": value['legacy_code'],
                        "section_text": value['section_text'],
                        "note": value['note'],
                        "media_files": mediaFiles,
                        "recording_datetime": value['recording_datetime'],
                        "use_period": dtV,
                        "use_period_start": dtS,
                        "use_period_end": dtE,
                        "time_of_year": toyV,
                        "time_of_year_array": toyM,
                        "spatial_data_source": value['spatial_data_source'],
                        "spatial_data_scale": spatialScale,
                        "tags": ','.join(value['tags']),
                        "content_codes": value['content_codes'],
                        "media_start_time": value['media_start_time'],
                        "media_end_time": value['media_end_time'],
                        "the_geom": geomText,
                        "the_geom_source": geomSource
                    }
                    # process human validation
                    if 'hvr' in value:
                        sectionDict['human_validation_required'] = True
                        sectionDict['human_validation_required_note'] = value['hvrnote']
                    else:
                        sectionDict['human_validation_required'] = False
                        sectionDict['human_validation_required_note'] = None
                    # add custom fields
                    tempDict = {}
                    for cf in self.customFields:
                        if cf['code'] in value and value[cf['code']] <> "":
                                tempDict[cf['code']] = value[cf['code']]
                    sectionDict['custom_fields'] = tempDict
                    # copy media files
                    for rec in value['media_files']:
                        srcName = os.path.join(self.dirName,'images',rec[0])
                        destName = os.path.join(imageDir,rec[0])
                        shutil.copy(srcName,destName)
                    # add section to docInfo
                    docInfo["sections"][key] = sectionDict
                # interview participants related to exported interviews
                self.workerStatus.emit('Exporting Participants')
                partInfo = {}
                for partId in participantIdList:
                    partInfo[partId] = self.projDict['participants'][str(partId)]
                    partInfo[partId]['tags'] = ','.join(partInfo[partId]['tags'])
                # commit dictionary to disk
                docFile = os.path.join(docDir,'import.json')
                fDict = {
                    "project_details": projInfo,
                    "document_details": docInfo,
                    "participant_details": partInfo
                }
                f = open(docFile,'w')
                f.write(json.dumps(fDict,indent=4))
                f.close()
                # compress outputs into zip file
                self.workerStatus.emit('Compressing Archive')
                self.zipArchiveMake(docDir, intZFileName, excludeFileType='.zip')
        # remove original files
        dirList = glob.glob(exDir+'/*')
        self.removeFilesInList(dirList)

    #
    # export interviews from current project to Common GIS Formats Archive
    #
    def exportToGIS(self,exDir):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        # progress notification
        self.progressUpdateOverall(1)
        self.workerStatus.emit('Creating Project Files')
        # export project info
        docDict = self.projDict['projects'][str(self.projId)]
        # loop through interviews to remove references to documents not exported
        # also build up a particpant dictionary
        partDict = {}
        delKeys = []
        for key, value in docDict['documents'].iteritems():
            if value['status'] <> 'T':
                delKeys.append(key)
            else:
                for pKey, pValue in value['participants'].iteritems():
                    partDict[str(pValue['participant_id'])] = self.projDict['participants'][str(pValue['participant_id'])]
        for key in delKeys:
            del docDict['documents'][key]
        # write files
        pfJ = os.path.join(exDir,'lmb-p%d-data.json' % self.projId)
        f = open(pfJ,'w')
        f.write(json.dumps(docDict,indent=4))
        f.close()
        pfJ = os.path.join(exDir,'lmb-p%d-users.json' % self.projId)
        f = open(pfJ,'w')
        f.write(json.dumps(partDict,indent=4))
        f.close()
        # export documents
        x = 0
        lastPercent = 0.0
        intCount = len(docDict['documents'])
        self.progressUpdateOverall(2)
        self.workerStatus.emit('Exporting Interviews')
        for key, value in docDict['documents'].iteritems():
            x += 1
            # progress notification
            buildPercent = x / float(intCount) * 100
            if int(buildPercent) > lastPercent and buildPercent <= 99.0:
                self.progressStep.emit(buildPercent)
                lastPercent = buildPercent           
            # identify or create gis output directory for this interview
            intvExDir = os.path.join(exDir,'p%d-i%d' % (self.projId,int(key)),'images')
            if not os.path.exists(intvExDir):
                os.makedirs(intvExDir, 0755)
            intvExDir = os.path.join(exDir,'p%d-i%d' % (self.projId,int(key)))
            # open source file
            fname = "lmb-p%d-i%d-data.json" % (self.projId,int(key))
            nf = os.path.join(self.dirName,"interviews",fname)
            if os.path.exists(nf):
                f = open(nf,'r')
                intvDict = json.loads(f.read())
                f.close()
            else:
                intvDict = {}
            pointFeatures = []
            lineFeatures = []
            polygonFeatures = []
            self.workerStatus.emit('Exporting Attributes')
            for iKey, iValue in intvDict.iteritems():
                # skip non-spatial sections
                if iValue['geom_source'] in ('pt','ln','pl') or iValue['geom_source'] <> 'ns':
                    # process content codes
                    if iValue['content_codes'] == []:
                        cCodes = ""
                    else:
                        cCodes = ','.join(iValue['content_codes'])
                    # process tags
                    if iValue['tags'] == []:
                        tags = ""
                    else:
                        tags = ','.join(iValue['tags'])
                    # process media files
                    if iValue['media_files'] == []:
                        media = ""
                    else:
                        media = ''
                        for rec in iValue['media_files']:
                            media += rec[0] + ','
                            src = os.path.join(self.dirName,'images',rec[0])
                            dest = os.path.join(intvExDir,'images',rec[0])
                            shutil.copyfile(src, dest)
                        if len(media) > 0:
                            media = media[:-1]
                    entry = {
                        "type":"Feature", 
                            "properties": {
                                "scode": iValue['section_code'],
                                "pcode": iValue['code_type'],
                                "pc_num": iValue['code_integer'],
                                "sequence": iValue['sequence'],
                                "oldcode": iValue['legacy_code'],
                                "content": cCodes,
                                "stext": iValue['section_text'],
                                "note": iValue['note'],
                                "security": iValue['data_security'],
                                "spatialsrc": iValue['spatial_data_source'],
                                "scale": iValue['spatial_data_scale'],
                                "recdatetim": iValue["recording_datetime"],
                                "use_period": iValue['use_period'],
                                "timeofyear": iValue['time_of_year'],
                                "mediastart": iValue['media_start_time'],
                                "mediaend": iValue['media_end_time'],
                                "tags": tags,
                                "media": media,
                                "geomsrc": iValue['geom_source'],
                                "created": iValue['date_created'],
                                "modified": iValue['date_modified']
                            },
                            "geometry": {}
                    }
                    if iValue['the_geom'] == "":
                        geomSrce = intvDict[iValue['geom_source']]['geom_source']
                        geom = QgsGeometry.fromWkt(intvDict[iValue['geom_source']]["the_geom"])
                        geom.convertToMultiType()
                        entry['geometry'] = json.loads(geom.exportToGeoJSON())
                    else:
                        geomSrce = iValue['geom_source']
                        geom = QgsGeometry.fromWkt(iValue["the_geom"])
                        geom.convertToMultiType()
                        entry['geometry'] = json.loads(geom.exportToGeoJSON())
                    if geomSrce == 'pt':
                        pointFeatures.append(entry)
                    elif geomSrce == 'ln':
                        lineFeatures.append(entry)
                    elif geomSrce == 'pl':
                        polygonFeatures.append(entry)
            self.workerStatus.emit('Exporting GIS Features')
            # write point file
            if len(pointFeatures) > 0:
                exportDict = {"type":"FeatureCollection",
                    "features": pointFeatures
                }
                pfJ = os.path.join(intvExDir,'lmb-p%d-i%d-points.geojson' % (self.projId,int(key)))
                f = open(pfJ,'w')
                f.write(json.dumps(exportDict,indent=4))
                f.close()
            # write line file
            if len(lineFeatures) > 0:
                exportDict = {"type":"FeatureCollection",
                    "features": lineFeatures
                }
                pfJ = os.path.join(intvExDir,'lmb-p%d-i%d-lines.geojson' % (self.projId,int(key)))
                f = open(pfJ,'w')
                f.write(json.dumps(exportDict,indent=4))
                f.close()
            # write polygon file
            if len(polygonFeatures) > 0:
                exportDict = {"type":"FeatureCollection",
                    "features": polygonFeatures
                }
                pfJ = os.path.join(intvExDir,'lmb-p%d-i%d-polygons.geojson' % (self.projId,int(key)))
                f = open(pfJ,'w')
                f.write(json.dumps(exportDict,indent=4))
                f.close()
                    
            self.convertGeoJSONToShape(intvExDir)
            # process multimedia
            self.workerStatus.emit('Exporting Audio')
            intvMediaFName = "lmb-p%d-i%d-media" % (self.projId,int(key))
            srcName = os.path.join(self.dirName,'media',intvMediaFName+'.wav')
            outName = os.path.join(intvExDir,intvMediaFName+'.ogg')
            if os.path.exists(srcName):
                retval = self.oggCreate(srcName,outName)
                if retval == -1:
                    messageText = 'Unable to convert audio files. '
                    messageText += "Confirm that oggenc is installed and its location set defined "
                    messageText += "the Map Biographer Manager."
                    self.workerPopup.emit(messageText,'Warning')
        # compress outputs into zip file
        self.workerStatus.emit('Compressing Archive')
        zipFName = 'lmb-p%d-gis.zip' % self.projId
        intZFileName = os.path.join(exDir,zipFName)
        self.zipArchiveMake(exDir, intZFileName,'.zip')
        # remove original files
        self.workerStatus.emit('Deleting Temporary Files')
        dirList = glob.glob(exDir+'/*')
        self.removeFilesInList(dirList)
        
    #
    # export convert geojson files to shape files
    #
    def convertGeoJSONToShape(self,exPath):

        if self.debug:
            QgsMessageLog.logMessage(self.myself())
        fList = glob.glob(exPath+'/*.geojson')
        for fName in fList:
            inLyr = QgsVectorLayer(fName, 'src', 'ogr')
            root, ext = os.path.splitext(fName)
            ofName = root + '.shp'
            outLyr = QgsVectorLayer(ofName,'dst', 'ogr')
            srcDP = inLyr.dataProvider()
            error = QgsVectorFileWriter.writeAsVectorFormat(inLyr, ofName, "System", None, "ESRI Shapefile")

    #
    # upload files
    #
    def uploadFiles(self,exPath):
        
        if self.debug:
            QgsMessageLog.logMessage(self.myself())
            QgsMessageLog.logMessage('int list: %s' % str(self.docList))
        srcDir = os.path.join(self.dirName,'transfer','proj%d' % int(self.projId),'heritage')
        url = self.url + '/tools/heritage/import/upload/zipfile/'
        
        self.progressUpdateOverall(3)
        self.workerStatus.emit('Uploading interviews')
        lastPercent = 0.0
        errorList = []
        successList = []
        for x in range(len(self.docKeys)):
            buildPercent = x+1 / float(len(self.docKeys)) * 100
            if int(buildPercent) > lastPercent and buildPercent <= 99.0:
                self.progressStep.emit(buildPercent)
                lastPercent = buildPercent    
            self.workerStatus.emit('uploading %s' % self.docList[x])
            fName = 'lmb-p%d-i%d-archive.zip' % (self.projId,self.docKeys[x])
            fPath = os.path.join(srcDir, fName)
            if os.path.exists(fPath):
                if self.debug:
                    QgsMessageLog.logMessage(fName)
                fields = [('username',self.account),
                    ('password',self.password),
                    ('project_id',self.destProjId),
                    ('note','%s uploaded from Map Biographer' % self.docList[x])
                ]
                bData = io.BytesIO(open(fPath,'rb').read()).getvalue()
                files = [('upload_file',fName,bData)]
                try:
                    responseData = self.post_multipart(url, fields, files)
                    responseJSON = json.loads(responseData)
                    #QgsMessageLog.logMessage(str(responseJSON))
                    if responseJSON['result'] == 'error':
                        errorList.append('%s: %s' % (self.docList[x], responseJSON['data']))
                    else:
                        successList.append([self.docList[x],self.docKeys[x]])
                except Exception, e:
                    QgsMessageLog.logMessage(str(e))
                    errorList.append('Connection error with interview %s.' % self.docList[x])
            else:
                QgsMessageLog.logMessage('upload file not found')
        if len(errorList) > 0:
            messageText = 'The following errors were encountered on upload:\n'
            for item in errorList:
                messageText += item + '\n'
            self.workerPopup.emit(messageText,'Warning')
        else:
            messageText = 'The following files were uploaded and marked as uploaded:\n'
            for item in successList:
                messageText += item[0] + ', '
                self.projDict['projects'][str(self.projId)]['documents'][str(item[1])]['status'] = 'U'
            nf = os.path.join(self.dirName,'lmb-project-info.json')
            if os.path.exists(nf):
                f = open(nf,'w')
                f.write(json.dumps(self.projDict,indent=4))
                f.close()
            self.workerPopup.emit(messageText[:-2],'Information')



#            
# The following three functions were adapted from comments posted to entry here:
# http://code.activestate.com/recipes/146306-http-client-to-post-using-multipartform-data/
#
    #
    # take inputs, call encode and then post
    #
    def post_multipart(self, url, fields, files):
        """
        Post fields and files to an http host as multipart/form-data.
        fields is a sequence of (name, value) elements for regular form fields.
        files is a sequence of (name, filename, value) elements for data to be uploaded as files
        Return the server's response page.
        """
        processDebug = False
        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        content_type, body = self.encode_multipart_formdata(fields, files)
        headers = {'Content-Type': content_type.encode('ascii'),
                   'Content-Length': str(len(body)).encode('ascii')}
        if processDebug == True:
            QgsMessageLog.logMessage(str(headers))
        #NOTE: url must be encoded as ascii or may encounter unicode decode errors
        #      on upload because of mixed encodings
        request = urllib2.Request(url.encode('ascii'), body, headers)
        if processDebug == True:
            QgsMessageLog.logMessage('opening url')
        try:
            response = urllib2.urlopen(request)
        except Exception, e:
            QgsMessageLog.logMessage(str(e))
        except:
            QgsMessageLog.logMessage(str(sys.exc_info()[0]))
        if processDebug == True:
            QgsMessageLog.logMessage('reading response')
        responseData = response.read()
        if processDebug == True:
            QgsMessageLog.logMessage('response read')
            QgsMessageLog.logMessage(str(responseData))
        return responseData

    #
    # encode body 
    #
    def encode_multipart_formdata(self, fields, files):
        """
        fields is a sequence of (name, value) elements for regular form fields.
        files is a sequence of (name, filename, value) elements for data to be uploaded as files
        Return (content_type, body) ready for httplib.HTTP instance
        """
        if self.debug == True:
            QgsMessageLog.logMessage(self.myself())
        BOUNDARY = mimetools.choose_boundary()
        CRLF = u'\r\n'
        L = []
        for (key, value) in fields:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"' % key)
            L.append('')
            L.append(value)
        for (key, filename, value) in files:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
            L.append('Content-Type: application/zip' )
            L.append('')
            L.append(value)
        L.append('--' + BOUNDARY + '--')
        L.append('')
        body = '\r\n'.join(str(x) for x in L)
        content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
        return content_type, body
    
    #
    # get content type - not used as known for LMB uses
    #
#    def get_content_type(self, filename):
#        return mimetypes.guess_type(filename)[0] or 'application/octet-stream'


    progressAll = QtCore.pyqtSignal(int)
    progressStep = QtCore.pyqtSignal(int)
    workerStatus = QtCore.pyqtSignal(str)
    workerPopup = QtCore.pyqtSignal(str, str)
    workerError = QtCore.pyqtSignal(Exception, basestring, str)
    workerFinished = QtCore.pyqtSignal(bool,str)
