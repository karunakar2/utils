#!/usr/bin/python
from bs4 import BeautifulSoup
from http.cookiejar import CookieJar
from urllib.request import urlopen
from urllib.request import HTTPBasicAuthHandler
from urllib.request import HTTPPasswordMgrWithDefaultRealm
from urllib.request import HTTPCookieProcessor
from urllib.request import build_opener, install_opener
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

##---------------------------------------------------------------------------------
#some constants to be defined as to where to fetch data from.
queryParam = "Geophysical_Data_sm_rootzone[1317:1340][3810:3836]"
#basePath = "https://n5eil01u.ecs.nsidc.org/SMAP/SPL4SMGP.004/"
openDapPath = 'https://n5eil02u.ecs.nsidc.org/opendap/SMAP/SPL4SMGP.004/'
##---------------------------------------------------------------------------------

def initAuth(uname,pswd):
    #This code was adapted from https://wiki.earthdata.nasa.gov/display/EL/How+To+Access+Data+With+Python Last edited Jan 26, 2017 G. Deemer""" 
     #==========================================================================
     # The following code block is used for HTTPS authentication
     #==========================================================================
    password_manager = HTTPPasswordMgrWithDefaultRealm()
    password_manager.add_password(None, "https://urs.earthdata.nasa.gov", uname, pswd)

    # Create a cookie jar for storing cookies. This is used to store and return
    # the session cookie given to use by the data server (otherwise it will just
    # keep sending us back to Earthdata Login to authenticate).  Ideally, we
    # should use a file based cookie jar to preserve cookies between runs. This
    # will make it much more efficient.
    cookie_jar = CookieJar()

    # Install all the handlers.
    opener = build_opener(
        HTTPBasicAuthHandler(password_manager),
        #urllib2.HTTPHandler(debuglevel=1),    # Uncomment these two lines to see
        #urllib2.HTTPSHandler(debuglevel=1),   # details of the requests/responses
        HTTPCookieProcessor(cookie_jar))
    install_opener(opener)

    # Create and submit the requests. There are a wide range of exceptions that
    # can be thrown here, including HTTPError and URLError. These should be
    # caught and handled.

#===========================================================================
# Open a requeset to grab filenames within a directory. Print optional
#===========================================================================

##DirResponse = urllib2.urlopen(url)
##htmlPage = DirResponse.read()
##
##listFiles = [x.split(">")[0].replace('"', "")
##                     for x in htmlPage.split("><a href=") if x.split(">")[0].endswith('.h5"') == True]

# Display the contents of the python list declared in the HTMLParser class
# print Files #Uncomment to print a list of the files

# Define function for batch downloading
##def BatchJob(Files, cookie_jar):
##   for dat in Files:
##      print "downloading: ", dat
##      JobRequest = urllib2.Request(url+dat)
##      JobRequest.add_header('cookie', cookie_jar) # Pass the saved cookie into additional HTTP request
##     JobRedirect_url = urllib2.urlopen(JobRequest).geturl() + '&app_type=401'
##
##     # Request the resource at the modified redirect url
##     Request = urllib2.Request(JobRedirect_url)
##     Response = urllib2.urlopen(Request)
##     f = open( dat, 'wb')
##     f.write(Response.read())
##     f.close()
##     Response.close()
## print "Files downloaded to: ", os.path.dirname(os.path.realpath(__file__))


##------------------------------------------------------------------------------
def getBaseLinks(url,yr,mon):
    print('path for the date requested',yr,mon)
    try:
        html_page = urlopen(url).read()
        soup = BeautifulSoup(html_page,features="html.parser")
        links = []

        #print(soup.findAll('a'))
        for link in soup.findAll('a', attrs={'href': re.compile(str(yr)+"."+str(mon).zfill(2))}):
            links.append(link.get('href'))
            #print(link)

        return links

    except Exception as e:
        print(e)

def getHdfLinks(url):
    print('listing available h5 at '+url)
    try:
        html_page = urlopen(url).read()
        soup = BeautifulSoup(html_page,features="html.parser")
        links = []

        #print(soup.findAll('a'))
        for link in soup.findAll('a', attrs={'href': re.compile('.h5.html'), 'itemprop': True}):
            links.append(link.get('href')[:-5])
                
        return links

    except Exception as e:
        print(e)

def getCellLatLon(url):
    print('fetching (once) lat lon to build the grids '+url)
    try:
            thsIndices = queryParam.split('[')
            #print(thsIndices)
            html_page = urlopen(url+'.ascii?cell_lon['+thsIndices[1]+'['+thsIndices[2]).read()
            soup = BeautifulSoup(html_page,features="html.parser")
            #print(soup.contents)
            lonData = []
            for ele in soup.contents :
                if ele.find(','):
                    ele = ele.replace(',','')
                if ele.find('\n'):
                    subEle = ele.split('\n')
                    lonData.extend(subEle)
                else:
                    lonData.append(ele)
            #print((lonData[1].split())[1:])

            html_page = urlopen(url+'.ascii?cell_lat['+thsIndices[1]+'['+thsIndices[2]).read()
            soup = BeautifulSoup(html_page,features="html.parser")
            #print(soup.contents)
            latData = []
            for ele in soup.contents :
                if ele.find(','):
                    ele = ele.replace(',','')
                if ele.find('\n'):
                    subEle = ele.split('\n')
                    latData.extend(subEle)
                else:
                    latData.append(ele)
            latData = latData[1:]
            if latData[len(latData)-1] == '' :
                latData = latData[:-1]

            #print(latData)

            return [(lonData[1].split())[1:],[ (x.split())[1] for x in latData ] ]
    except Exception as e:
        print(e)

def getSMAProotZone(url):
    html_page = urlopen(url+'.ascii?'+queryParam)
    soup = BeautifulSoup(html_page,features="html.parser")
    smData = []
    for ele in soup.contents :
        if ele.find(','):
            ele = ele.replace(',','')
        if ele.find('\n'):
            subEle = ele.split('\n')
            smData.extend(subEle)
        else:
            smData.append(ele)
    #print(smData)
    smData = smData[1:]
    if smData[len(smData)-1] == '' :
        smData = smData[:-1]   

    buff = [ x.split() for x in smData]
    #print(buff)
    
    return [ x[1:] for x in buff ]

def buildTiff(lonLat,smGrid,target):
    #fd, tpath = tempfile.mkstemp(suffix='.csv')
    #fd1, vpath = tempfile.mkstemp(suffix='.vrt')
    #print(path,fd)
    try:
        #with os.fdopen(fd, 'w') as tmp:
        tpath = target[:-14]+'.csv'
        with open(tpath,'w') as tmp:
            tmp.write('lon,lat,Z\n')
            for i, x in enumerate(smGrid): #iter over lat
                for j, y in enumerate(x): #iter over lon
                    if y == '-9999':
                        smGrid[i][j] = float('NaN')
                    # do stuff with temp file
                    tmp.write(str(lonLat[0][j])+','+str(lonLat[1][i])+','+str(smGrid[i][j])+'\n')
                    tmp.flush()
            tmp.close()

        #print(os.path.exists(tpath))
        while not os.path.exists(tpath):
            print('waiting for file ',tpath)
            time.sleep(1)

        #conversion circus
        #build a vrt file
        #with os.fdopen(fd1, 'w') as tmp:
        vpath = target[:-14]+'.vrt'
        with open(vpath,'w') as tmp:
            tmp.write('<OGRVRTDataSource>\n')
            tmp.write('\t<OGRVRTLayer name="'+target[:-14]+'">\n')
            tmp.write('\t\t<SrcDataSource relativeToVRT="1">CSV:'+Path(tpath).name+'</SrcDataSource>\n')
            tmp.write('\t\t<GeometryType>wkbPoint25D</GeometryType>\n')
            tmp.write('\t\t<LayerSRS>EPSG:4326</LayerSRS>\n')
            tmp.write('\t\t<GeometryField separator="," encoding="PointFromColumns" x="lon" y="lat" z="Z"/>\n')
            tmp.write('\t</OGRVRTLayer>\n')
            tmp.write('</OGRVRTDataSource>')
            tmp.flush()
            tmp.close()

        cpath = target[:-14]+'.csvt'
        with open(cpath,'w') as tmp:
            tmp.write('"Real","Real","Real"')
            tmp.flush()
            tmp.close()
            
        gridopt = gdal.GridOptions(format='GTiff',algorithm='linear:nodata=-9999:')
        output = gdal.Grid(target[:-14]+'.tif', vpath, options=gridopt)  
    except Exception as e:
        print(e,' error')
    #finally:
        #os.remove(tpath)
        #os.remove(vpath)
        #print(tpath,'\n',vpath)

def runProc(yr,mon):
    subDirs = getBaseLinks(openDapPath,yr,mon)
    for subDir in subDirs :
        files2Download = getHdfLinks(openDapPath+subDir)
        #print(files2Download)
        for file in files2Download :
            if firstQuery:
                lonLat = getCellLatLon(openDapPath+subDir[:-13]+file)
                firstQuery = False
            rzSm = getSMAProotZone(openDapPath+subDir[:-13]+file)
            buildTiff(lonLat,rzSm,file)
    

#=========================================================================
# Call the function to download all files in url
#=========================================================================

######BatchJob(Files, cookie_jar) # Comment out to prevent downloading to your working directory

##---------------------------------------------------------------------------------
if __name__ == "__main__":
    uname = 'karunakar.kintada@gmail.com'
    pswd = 'Jeypore!00'
    firstQuery = True
    
    initAuth(uname,pswd)

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
