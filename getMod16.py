#!/usr/bin/python
from bs4 import BeautifulSoup
from urllib.request import urlopen
import re
import sys
import datetime
import requests
from requests.auth import HTTPBasicAuth
import glob 
import gdal
import os, subprocess
import numpy as np

import matplotlib.pyplot as plt
##------------------------------------------------------------------------------
sys.path.append('C:\\Users\\karunakar.kintada\\AppData\\Local\\Programs\\Python\\Python38-32\\Scripts')
import gdal_merge as gm
import gdal_calc as gc
##------------------------------------------------------------------------------

basePath = "https://e4ftl01.cr.usgs.gov/MOLT/MOD13Q1.006/"
gridCodes = ["h31v12","h31v13"]
regBoundBox = [176,-40.5,178,-38.5]
uname = 'karunakar.kintada@gmail.com'
pwd = 'Jeypore!00'

##------------------------------------------------------------------------------
existHDF = glob.glob('MOD13Q1.*.hdf')
#print('files on disk')
#print(existHDF)


##------------------------------------------------------------------------------
def getBaseLinks(url,yr,mon):
    try:
        html_page = urlopen(url)
        soup = BeautifulSoup(html_page,features="html.parser")
        links = []

        #print(soup.findAll('a'))
        for link in soup.findAll('a', attrs={'href': re.compile(str(yr)+"."+str(mon).zfill(2))}):
            links.append(link.get('href'))

        return links

    except Exception as e:
        print(e)

def getHdfLinks(url):
    try:
        html_page = urlopen(url)
        soup = BeautifulSoup(html_page,features="html.parser")
        links = []

        #print(soup.findAll('a'))
        for gridCode in gridCodes :
            for link in soup.findAll('a', attrs={'href': re.compile(gridCode)}):
                if (link.get('href'))[-3:] == 'hdf':
                    #return link.get('href')
                    links.append(link.get('href'))

        return links

    except Exception as e:
        print(e)

def fetchHDF(fName,webPath):
    with requests.session() as s:
        print(fName,'fetch')
        url_earthdata = s.request('get', webPath+fName)
        #print(url_earthdata.url)
        stream_mod13 = requests.get(url_earthdata.url,auth=HTTPBasicAuth(uname,pwd), stream=True)

        downloaded_file = open(fName, "wb")
        for chunk in stream_mod13.iter_content(chunk_size=256):
            if chunk:
                downloaded_file.write(chunk)
                downloaded_file.flush()
        downloaded_file.close()
        #print(url_mod13File.text)

def hdf2Tiff(fName):
    print(fName,'h2t')
    src_hdf = gdal.Open(fName, gdal.GA_ReadOnly)
    if src_hdf is None:
        print('kk: GDAL failed to open '+fName)
    else:
        src_band = gdal.Open(src_hdf.GetSubDatasets()[0][0], gdal.GA_ReadOnly) #0 is 1st subdataset NDVI PET, check GDALinfo
        dst = gdal.Translate(fName[:-4]+'_PET.tiff',src_band,format="GTiff")
        dst = None

def mergeSameDayTiffs(fileNameList):
    print((fileNameList[0])[:-28],'msd')
    cmdString = ['',"-o", (fileNameList[0])[:-28]+"merged.tiff"]
    fileNameString = [x[:-4]+'_PET.tiff' for x in fileNameList]
    cmdString.extend(fileNameString)
    #print(cmdString)
    gm.main(cmdString)
    return (fileNameList[0])[:-28]+"merged.tiff"

def clip2Region(fName):
    print(fName,'clip')
    pixSize = 0.00892857142857143/2 #degrees
    options = gdal.WarpOptions(dstSRS='EPSG:4326', xRes=pixSize, yRes=pixSize, outputType=gdal.GDT_Int16, outputBoundsSRS='EPSG:4326', outputBounds=regBoundBox)
    wgsFile = gdal.Warp(fName[:-4]+"wgs84.tiff", fName, options=options) #
    wgsFile = None
    return fName[:-4]+"wgs84.tiff"

def scaleTiff(fName):
    print(fName,'normalise')
    gc.Calc("A*0.0001", A=fName, outfile='c-'+fName, NoDataValue=-9999.0, type='Float32')
    return 'c-'+fName

def extractValidation(ini):
    collectedPETfiles = glob.glob(ini+'-MOD13Q1.*.merged.wgs84.tiff')
    
    with open('stations.txt','r') as f:
        temp = f.readlines()
        stns = [line.split() for line in temp]

    for fName in collectedPETfiles:
        print(fName)
        for stn in stns:
            #print (stn, fName)
            result = os.popen("gdallocationinfo -wgs84 -valonly {0} {1} {2}".format(fName, stn[2],stn[1])).read()
            #print(result)
            try:
                result = float(result)
                if result > 1000 :
                    result = '-999'
                else :
                    result = str(result)
            except ValueError:
                result = '-999'

            if(ini == 'KK-RW'):
                thisYear = int(fName[15:19])
                thisDate = int(fName[19:22])
            if(ini == 'RW'):
                thisYear = int(fName[12:16])
                thisDate = int(fName[16:19])
            print(thisYear,thisDate)   
            fmtdDate = datetime.datetime(thisYear, 1, 1) + datetime.timedelta(thisDate - 1)    
            with open(stn[0],'a') as f:
                f.write(str(fmtdDate)+','+result+'\n')    #fName[12:19]
                f.flush()

def runProc(yr,mon):
    print('data sets for ',yr,mon)
    subDirs = getBaseLinks(basePath,yr,mon)
    print('files for select month')
    print(subDirs)
    
    for subDir in subDirs :
        files2Download = getHdfLinks(basePath+subDir)
        for fName in files2Download:
            if fName in str(existHDF):
                print(fName+' exists on disks: kk')
            else:
                fetchHDF(fName,basePath+subDir)

            #make it to TIFF
            hdf2Tiff(fName)

        fName = mergeSameDayTiffs(files2Download)
        fName = clip2Region(fName)
        fName = scaleTiff(fName)

##---------------------------------------------------
if __name__ == "__main__":
    
    now = datetime.datetime.now()

    print(sys.argv,' args')

    if len(sys.argv) == 1:
        yr = now.year
        mon = now.month
        runProc(yr,mon)
    elif len(sys.argv) == 2 :
        for myr in range(int(sys.argv[1]),(now.year+1)):
            for mmon in range(1,13):
                runProc(myr,mmon)
    else:
        yr = sys.argv[1]
        mon = sys.argv[2]
        runProc(yr,mon)

    #print(yr,mon)
        
    extractValidation('KK-RW')


##    f1 = open('files.tmp','w')
##    with open('latestMod16Files.txt','w') as f:
##        for subDir in subDirs :
##            for fName in getHdfLinks(basePath+subDir):
##                #f.write(basePath+subDir+fName+'\n')
##                f.write(fName+'\n')
##                f1.write(fName+' ')
##    f1.close()
