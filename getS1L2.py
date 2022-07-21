#!/usr/bin/python
from bs4 import BeautifulSoup
from http.cookiejar import CookieJar
from urllib.request import urlopen
from urllib.request import HTTPBasicAuthHandler
from urllib.request import HTTPPasswordMgrWithDefaultRealm
from urllib.request import HTTPCookieProcessor
from urllib.request import build_opener, install_opener
from urllib.request import Request
#import requests
#from requests.auth import HTTPBasicAuth

import re
import sys
import datetime
import time
import glob 
import gdal
import os, subprocess
#import numpy as np
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
##------------------------------------------------------------------------------
sys.path.append('C:\\Users\\karunakar.kintada\\AppData\\Local\\Programs\\Python\\Python38-32\\Scripts')
import gdal_merge as gm
import gdal_calc as gc

##------------------------------------------------------------------------------

basePath = "https://n5eil01u.ecs.nsidc.org/SMAP/SPL2SMAP_S.002/"
gridCodes = ["176E41S","176E40S","176E39S","176E38S","177E41S","177E40S","177E39S","177E38S",]
regBoundBox = [176,-40.5,178,-38.5]

cookie_jar = None #place holder for cookies

##------------------------------------------------------------------------------
existHDF = glob.glob('SMAP_L2_SM_SP_*.h5')
print(len(existHDF),' files on disk')
#print(existHDF)

##---------------------------------------------------------------------------------
def initAuth(uname,pswd):
    password_manager = HTTPPasswordMgrWithDefaultRealm()
    password_manager.add_password(None, "https://urs.earthdata.nasa.gov", uname, pswd)
    cookie_jar = CookieJar()

    # Install all the handlers.
    opener = build_opener(
        HTTPBasicAuthHandler(password_manager),
        #urllib2.HTTPHandler(debuglevel=1),    # Uncomment these two lines to see
        #urllib2.HTTPSHandler(debuglevel=1),   # details of the requests/responses
        HTTPCookieProcessor(cookie_jar))
    install_opener(opener)

##------------------------------------------------------------------------------
def getBaseLinks(url,yr,mon,dat):
    try:
        html_page = urlopen(url)
        soup = BeautifulSoup(html_page,features="html.parser")
        links = []

        #print(soup.findAll('a'))
        for link in soup.findAll('a', attrs={'href': re.compile(str(yr)+"."+str(mon).zfill(2)+"."+str(dat).zfill(2))}):
            links.append(link.get('href'))

        #print(links)
        return list(dict.fromkeys(links))

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
                #print(link.get('href'))
                if (link.get('href'))[-2:] == 'h5':
                    #return link.get('href')
                    links.append(link.get('href'))

        return list(dict.fromkeys(links))

    except Exception as e:
        print(e)

def fetchHDF(fName,webPath):
    Response = urlopen(webPath+'/'+fName)

    downloaded_file = open(fName, "wb")
    downloaded_file.write(Response.read())
    downloaded_file.close()


def hdf2Tiff(fName):
    print(fName,' h2t')
    src_hdf = gdal.Open(fName, gdal.GA_ReadOnly)
    if src_hdf is None:
        print('h2tif: GDAL failed to open '+fName)
    else:
        src_band = gdal.Open(src_hdf.GetSubDatasets()[32][0], gdal.GA_ReadOnly)
        src_mat = src_band.ReadAsArray()
        lat_band = gdal.Open(src_hdf.GetSubDatasets()[20][0], gdal.GA_ReadOnly)
        lat_mat = lat_band.ReadAsArray()
        lon_band = gdal.Open(src_hdf.GetSubDatasets()[22][0], gdal.GA_ReadOnly)
        lon_mat = lon_band.ReadAsArray()
        #can't do it file way on windows as of now,
##        dst = gdal.Translate('src.vrt',src_band,format="VRT")
##        dst = None
##        dst = gdal.Translate('lat.vrt',lat_band,format="VRT")
##        dst = None
##        dst = gdal.Translate('lon.vrt',lon_band, format="VRT")
##        dst = None

##        options_list = ['-a_srs EPSG:4326','-a_ullr '+str(float((fName[-18:-17]=='W')*'-'+fName[-21:-18])-0.5)+' '+str(float((fName[-15:-14]=='S')*'-'+fName[-17:-15])+0.5)+' '+str(float((fName[-18:-17]=='W')*'-'+fName[-21:-18])+0.5)+' '+str(float((fName[-15:-14]=='S')*'-'+fName[-17:-15])-0.5)]
##        options_string = " ".join(options_list)
##        print(options_string)
##        dst = gdal.Translate(fName[:-3]+'_SM.tiff',src_band,format="GTiff",options=options_string)
##        dst = None

        #print(len(lat_mat))
        #sticking to iteration, gives us some time not to hit servers immediately and get banned
        with open("temp.csv",'w') as f:
            f.writelines('lon,lat,sm\n')
            for row in range(0,len(src_mat)):
                for col in range(0,len(src_mat[1])):
                    f.writelines(str(lon_mat[row][col])+','+str(lat_mat[row][col])+','+str(src_mat[row][col])+'\n')
            f.flush()
            
        #grid it, takes care of the distortions at higher latitudes
        gridopt = gdal.GridOptions(format='GTiff',algorithm='linear:nodata=-9999.0:')
        output = gdal.Grid(fName[:-3]+'.tif', 'temp.vrt', options=gridopt)
        #output = gdal.Grid('temp.tif', 'temp.vrt', options=gridopt)
        #output = None
        #gc.Calc("(A>0)*A+(A<=0)*-9999", A='temp.tif',outfile=fName[:-3]+'.tif')#can't do it unless output is flushed tricky

def mergeSameDayTiffs(fileNameList):
    if(len(fileNameList)>1):
        #print(fileNameList)
        print((fileNameList[0])[:-45],' msd')
        for  mfile in fileNameList:
            gc.Calc("(A>0)*A+(A<=0)*-9999", A=mfile[:-3]+'.tif',outfile=mfile[:-3]+'_f.tif',NoDataValue=-9999.0)
        fileNameString = [x[:-3]+'_f.tif' for x in fileNameList]
##        cmdString = ['',"-o", (fileNameList[0])[:-45]+"_merged.tiff","-n -9999"]
##        print(fileNameString)
##        cmdString.extend(fileNameString)
##        #print(cmdString)
##        gm.main(cmdString)
        ds = gdal.Warp(fileNameList[0][:-45]+"_merged.tif",fileNameString)
        ds = None
        return (fileNameList[0])[:-45]+"_merged.tif"
    else:
        print('single file')

def extractValidation(ini):
    collectedPETfiles = glob.glob('*_merged.tif')
    print('have to loop through '+len(collectedPETfiles)+' files')
    
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
                if result > 1 :
                    result = '-9999'
                else :
                    result = str(result)
            except ValueError:
                result = '-9999'

            if(ini == 'raw'):
                fmtdDate = fName[21:30]
            with open(stn[0],'a') as f:
                f.write(str(fmtdDate)+','+result+'\n')    #fName[12:19]
                f.flush()

def runProc(yr,mon,dat):
    print('data sets for ',yr,mon,dat)
    subDirs = getBaseLinks(basePath,yr,mon,dat)
    print('files for select month')
    print(subDirs)
    
    for subDir in subDirs :
        files2Download = getHdfLinks(basePath+subDir)
        #print(files2Download)
        for fName in files2Download:
            if fName in str(existHDF):
                print(fName+' exists on disks: kk')
            else:
                fetchHDF(fName,basePath+subDir)

            #make it to TIFF
            hdf2Tiff(fName)

        if(len(files2Download)>1):
            fName = mergeSameDayTiffs(files2Download)
        elif(len(files2Download)==1):
            os.popen(' copy '+files2Download[0][:-37]+' '+files2Download[0][:-37]+'merged.tif')

##---------------------------------------------------
if __name__ == "__main__":
    uname = 'karunakar.kintada@gmail.com'
    pswd = 'Jeypore!00'
    initAuth(uname,pswd)
    now = datetime.datetime.now()

    print(sys.argv,' args')

    if len(sys.argv) == 1:
        yr = now.year
        mon = now.month
        dat = now.day
        runProc(yr,mon,dat)
    elif len(sys.argv) == 2 :
        for myr in range(int(sys.argv[1]),(now.year+1)):
            for mmon in range(1,13):
                for mdat in range(1,32): #its k, if it tries and fails over 31st day
                    runProc(myr,mmon,mdat)
    elif len(sys.argv) == 3:
        for myr in range(int(sys.argv[1]),(now.year+1)):
            for mmon in range(int(sys.argv[2]),13):
                for mdat in range(1,32):
                    runProc(myr,mmon,mdat)
    else:
        yr = sys.argv[1]
        mon = sys.argv[2]
        dat = sys.argv[3]
        runProc(yr,mon,dat)

    #print(yr,mon)
        
    extractValidation('raw')

    print('done')

