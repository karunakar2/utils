import glob
import os, subprocess

def extractValidation():
    collectedSM2Rainfiles = glob.glob('daily.rainfall_*_10km.tif')
    
    with open('stations.txt','r') as f:
        temp = f.readlines()
        temp = temp
        stns = [line.rstrip().split(',') for line in temp]

    for fName in collectedSM2Rainfiles:
        print(fName)
        for stn in stns:
            #print (stn, fName)
            result = os.popen("gdallocationinfo -wgs84 -valonly {0} {1} {2}".format(fName, stn[2],stn[1])).read()
            #print(result)
            try:
                result = float(result)
                if result > 800 :
                    result = '-999'
                else :
                    result = str(result)
            except ValueError:
                result = '-999'

            with open(stn[0]+'.csv','a') as f:
                f.write(fName[15:25]+','+result+'\n')    #fName[12:19]
                f.flush()

extractValidation()
