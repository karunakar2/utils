import math
import datetime

import requests
import xml.etree.ElementTree as ET
import urllib.parse

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

from intersect import intersection

from matplotlib.dates import DateFormatter
import matplotlib.ticker as mtick
import matplotlib.pyplot as plt

baseUrl='https://data.hbrc.govt.nz/Envirodata/EMAR.hts?'
def guagingSites():
	measurement = 'Stage%20[Gauging%20Results]'
	apiExt = 'Service=Hilltop&Request=SiteList&Location=Yes&Measurement='+measurement
	#slist = pd.read_xml(baseUrl+urllib.parse.quote_plus(apiExt))
	slist = pd.read_xml(baseUrl+apiExt)
	slist.replace('None',float('nan'),inplace=True)
	slist.dropna(subset=['Name'],inplace=True)
	siteList = slist['Name'].values
	#print(siteList)
	return siteList

def line_format(label):
    """
    Convert time label to the format of pandas line plot
    """
    month = label.month_name()[:2] + str(label.year)[-2:]
    #if month == 'J':
    #    month += f'\n{label.year}'
    return month


def powlaw(x, a, b, c) :
    return a * np.power(x, b) + c #https://nrfa.ceh.ac.uk/ratings-datums different to this
def linlaw(x, a, b) :
    return a + x * b

def curve_fit_log(xdata, ydata) :
    """Fit data to a power law with weights according to a log scale"""
    # Weights according to a log scale
    # Apply fscalex
    xdata_log = np.log10(xdata)
    # Apply fscaley
    ydata_log = np.log10(ydata)
    # Fit linear
    popt_log, pcov_log = curve_fit(linlaw, xdata_log, ydata_log)
    #print(popt_log, pcov_log)
    ydatafit = np.power(10, linlaw(xdata_log, *popt_log))
    return (popt_log, pcov_log, np.power(10,xdata_log), ydatafit)

def curve_fit_pow(xdata, ydata) :
    """Fit data to a power law with weights according to a log scale"""
    # Fit power
    popt_pow, pcov_pow = curve_fit(powlaw, xdata, ydata)
    #print(popt_log, pcov_log)
    ydatafit = powlaw(xdata, *popt_pow)
    return (popt_pow, pcov_pow, xdata, ydatafit)

def getGaugings(site,sDate,eDate):
    global baseUrl
    apiExt = 'Service=Hilltop&Request=GetData&Measurement=Stage%20[Gauging%20Results]'
    apiExt += '&To='+str(eDate)+'&Interval=1%20hour&method=Average&Site='
    apiExt1 = apiExt + site.replace(' ','%20')
    #print(baseUrl+apiExt1)
    if sDate != None:
        apiExt += '&From='+str(sDate)
    
    #print(baseUrl+apiExt1)
    #print(baseUrl+apiExt1)
    #df = pd.read_xml(baseUrl+apiExt1)
    #display(df)
    
    response = requests.get(baseUrl+apiExt1)
    root = ET.fromstring(response.text)
    thisData = {}
    myColumns = {}
    myDivisor = {}
    for child in root:
        for thisChild in child:
            if thisChild.tag == 'DataSource':
                for children in thisChild:
                    temp = list(children.attrib.keys())
                    if len(temp)>0:
                        #print(children.attrib[temp[0]])
                        colKey = children.attrib[temp[0]]
                        if children.tag == 'ItemInfo':
                            for data in children:
                                if data.tag == 'ItemName':
                                    colVal = data.text #string
                                if data.tag == 'Divisor':
                                    divVal = float(data.text) #number
                        myColumns[int(colKey)] = colVal
                        myDivisor[int(colKey)] = divVal
                pass
            if thisChild.tag == 'Data':
                for children in thisChild:
                    temp = []
                    for data in children:
                        if data.tag == 'T':
                            key = data.text
                        else:
                            temp.append(float(data.text))
                    if len(temp) > 0:
                        thisData[key] = temp
    
    myDivisor[0] = 1 #have to do it for that unknown column
    myDf = pd.DataFrame(data=thisData).T
    myDf = myDf.apply(lambda x: x/myDivisor[x.name])
    myDf.rename(columns=myColumns,inplace=True)
    myDf.index.name = 'timestamp'
    myDf.index = pd.to_datetime(myDf.index)
    display(myDf)
    myDf.plot(y='Flow',logy=True)
    plt.show()
    return myDf
    
def myStageFn(site,sDate,eDate,samples=33):
    myDf = getGaugings(site,sDate,eDate)
    #remove negative flow values
    myDf = myDf[myDf['Flow']>0] #log methods are not happy usually
    myDf = myDf[myDf['Stage']>0]
    myDf.sort_values(by=['Stage'],inplace=True)
    #get a power fit to estimate the central tendency
    xt=np.array(myDf['Flow'].values)
    yt=np.array(myDf['Stage'].values)
    #get a power fit
    poptP, pcovP, flowFPow, stageFPow = curve_fit_pow(xt, yt)
    """
    #sort them, pandas is way easier though
    print(flowFPow, stageFPow)
    stageFPow = [x for _, x in sorted(zip(flowFPow, stageFPow), key=lambda pair: pair[0])]
    flowFPow.sort()
    print(flowFPow, stageFPow)
    """
    print(poptP,'SFcoefs')
    myDf['pFitStage'] = powlaw(myDf['Flow'], *poptP)
    myDf['pStageErr'] = myDf['Stage'] - myDf['pFitStage']
    #try a log fit, may be works better at low flows
    poptL, pcovL, flowFLog, stageFLog = curve_fit_log(xt, yt)
    """
    #sort them
    stageFLog = [x for _, x in sorted(zip(flowFLog, stageFLog), key=lambda pair: pair[0])] #zip(Y,X)
    flowFLog.sort()
    """
    myDf['lFitStage'] = np.power(10,linlaw(np.log10(myDf['Flow']), *poptL))
    myDf['lStageErr'] = myDf['Stage'] - myDf['lFitStage']
    
    ax = myDf.plot(y=['pFitStage','Stage'],logy=True)
    myDf.plot(y=['lFitStage'],ax=ax)
    plt.show()
    
    ax = myDf.plot(y=['pStageErr','lStageErr'])
    plt.show()
    
    transitionFlow = 0 #always power
    try:
        flowArray = np.arange(myDf['Flow'].min(),myDf['Flow'].max(),10)
        powArray  = powlaw(flowArray,*poptP)
        logArray  = np.power(10,linlaw(np.log10(flowArray),*poptL))
        iFlow,iStage = intersection(flowArray, powArray, flowArray, logArray)
        transitionFlow = iFlow
    except:
        print('iter run')
        assumedEr = 2/100
        for thisFlow in np.arange(myDf['Flow'].min(),myDf['Flow'].max(),10000):
            pVal = powlaw(thisFlow,*poptP)
            lVal = np.power(10,linlaw(np.log10(thisFlow),*poptL))
            #print(pVal,lVal)
            if (1-assumedEr)*pVal <= lVal <= (1+assumedEr)*pVal:
                transitionFlow = thisFlow
                break
    print('flow characteristics change at ', transitionFlow)
    
    #sample some points
    myVar = myDf['Flow']
    floMin = math.floor(math.log10(myVar[myVar>0].min()))
    floMax = math.ceil(math.log10(myVar.max()))
    bins = np.logspace(floMin, floMax, num = samples) #exponents here
    #bins = np.geomspace(floMin, floMax, num = samples)
    bins = np.insert(bins,[0,len(bins)],[floMin/2,floMax*2])
    
    data = {}
    assumedEr = (100/samples)/100
    print('window margin',assumedEr*100,'%')
    #alt from pow fit of data and variation
    for fMin,fMax in zip(bins[:-1],bins[1:]):
        #redDf = myDf[myVar.between(fMin,fMax)].copy()
        thisFlow = round((fMin+fMax)/2,2)
        redDf = myDf[myVar.between(thisFlow*(1-assumedEr),thisFlow*(1+assumedEr))].copy()
        if thisFlow <= transitionFlow:
            data[thisFlow] = [np.power(10,linlaw(np.log10(thisFlow),*poptL)),redDf['lStageErr'].mean(),redDf['lStageErr'].std(),redDf['lStageErr'].median()]
        else:
            data[thisFlow] = [powlaw(thisFlow,*poptP),redDf['pStageErr'].mean(),redDf['pStageErr'].std(),redDf['pStageErr'].median()]
        #print(temp,np.power(10,linlaw(np.log10(temp), *poptL)),powlaw(temp, *poptP))
        #data[temp] = [powlaw(temp, *poptP),redDf['pStageErr'].mean(),redDf['pStageErr'].std()]
        #data[temp] = [np.power(10,linlaw(np.log10(temp), *poptL)),redDf['lStageErr'].mean(),redDf['lStageErr'].std()]
        
    erDf = pd.DataFrame(data=data).T
    erDf.rename(columns={0:'fitStage',1:'erMean',2:'stdev',3:'erMed'},inplace=True)
    erDf.dropna(inplace=True)
    erDf.index.name = 'Flow'
    #erDf['meanErrPc'] = erDf['stdev']/erDf['fitStage']
    erDf['meanErrPc'] = np.abs(erDf['erMean'])/erDf['fitStage']
    erDf['min'] = erDf['fitStage']+(erDf['erMean']-erDf['stdev'])
    erDf['min'] = erDf['min'].apply(lambda x: x if x>0.01 else float('nan'))
    erDf['max'] = erDf['fitStage']+(erDf['erMean']+erDf['stdev'])
    display(erDf)
    ax = erDf.plot(title=str(site),kind='bar',y='meanErrPc')
    # manipulate
    vals = ax.get_yticks()
    ax.set_yticklabels(['{:,.1%}'.format(x) for x in vals])
    plt.show()
    
    #plt.figure(figsize=(10, 5))#,title=site)
    fig, ax = plt.subplots()
    myDf.plot(x='Stage', y='Flow',logx=True, logy=True, kind='scatter',title=site,ax=ax)
    stageFLog, flowFLog = zip(*sorted(zip(stageFLog, flowFLog)))
    ax.plot(stageFLog, flowFLog, color='red', label='log fit')
    stageFPow, flowFPow = zip(*sorted(zip(stageFPow, flowFPow)))
    ax.plot(stageFPow, flowFPow, color='green', label='Pow fit')
    ax.plot(erDf['min'],erDf.index,color='orange', label='-1Sig')
    ax.plot(erDf['max'],erDf.index,color='yellow', label='+1Sig')
    #plt.xlim([myDf['Stage'].min(),myDf['Stage'].max()])
    #plt.ylim([myVar[myVar>0].min(),myVar.max()])
    plt.legend(loc="upper left")
    plt.show()

    
def myWidthFn(site,sDate,eDate,samples=33):
    myDf = getGaugings(site,sDate,eDate)
    #remove negative flow values
    myDf = myDf[myDf['Flow']>0] #log methods are not happy usually
    myDf = myDf[myDf['Width']>0]
    #get a power fit to estimate the central tendency
    xt=np.array(myDf['Flow'].values)
    yt=np.array(myDf['Width'].values)
    #get a power fit
    poptP, pcovP, flowFPow, WidthFPow = curve_fit_pow(xt, yt)
    print(poptP,'SFcoefs')
    myDf['pFitWidth'] = powlaw(myDf['Flow'], *poptP)
    myDf['pWidthErr'] = myDf['Width'] - myDf['pFitWidth']
    #try a log fit, may be works better at low flows
    poptL, pcovL, flowFLog, WidthFLog = curve_fit_log(xt, yt)
    myDf['lFitWidth'] = np.power(10,linlaw(np.log10(myDf['Flow']), *poptL))
    myDf['lWidthErr'] = myDf['Width'] - myDf['lFitWidth']
    
    ax = myDf.plot(y=['pFitWidth','Width'],logy=True)
    myDf.plot(y=['lFitWidth'],ax=ax)
    plt.show()
    
    ax = myDf.plot(y=['pWidthErr','lWidthErr'])
    plt.show()
    
    transitionFlow = 0 #always power
    try:
        flowArray = np.arange(myDf['Flow'].min(),myDf['Flow'].max(),10)
        powArray  = powlaw(flowArray,*poptP)
        logArray  = np.power(10,linlaw(np.log10(flowArray),*poptL))
        iFlow,iWidth = intersection(flowArray, powArray, flowArray, logArray)
        transitionFlow = iFlow
    except:
        print('iter run')
        assumedEr = 2/100
        for thisFlow in np.arange(myDf['Flow'].min(),myDf['Flow'].max(),10000):
            pVal = powlaw(thisFlow,*poptP)
            lVal = np.power(10,linlaw(np.log10(thisFlow),*poptL))
            #print(pVal,lVal)
            if (1-assumedEr)*pVal <= lVal <= (1+assumedEr)*pVal:
                transitionFlow = thisFlow
                break
    print('flow characteristics change at ', transitionFlow)
    
    #sample some points
    myVar = myDf['Flow']
    floMin = math.floor(math.log10(myVar[myVar>0].min()))
    floMax = math.ceil(math.log10(myVar.max()))
    bins = np.logspace(floMin, floMax, num = samples) #exponents here
    #bins = np.geomspace(floMin, floMax, num = samples)
    bins = np.insert(bins,[0,len(bins)],[floMin/2,floMax*2])
    
    data = {}
    assumedEr = (100/samples)/100
    print('window margin',assumedEr*100,'%')
    #alt from pow fit of data and variation
    for fMin,fMax in zip(bins[:-1],bins[1:]):
        #redDf = myDf[myVar.between(fMin,fMax)].copy()
        thisFlow = round((fMin+fMax)/2,2)
        redDf = myDf[myVar.between(thisFlow*(1-assumedEr),thisFlow*(1+assumedEr))].copy()
        if thisFlow <= transitionFlow:
            data[thisFlow] = [np.power(10,linlaw(np.log10(thisFlow),*poptL)),redDf['lWidthErr'].mean(),redDf['lWidthErr'].std(),redDf['lWidthErr'].median()]
        else:
            data[thisFlow] = [powlaw(thisFlow,*poptP),redDf['pWidthErr'].mean(),redDf['pWidthErr'].std(),redDf['pWidthErr'].median()]
        #print(temp,np.power(10,linlaw(np.log10(temp), *poptL)),powlaw(temp, *poptP))
        #data[temp] = [powlaw(temp, *poptP),redDf['pWidthErr'].mean(),redDf['pWidthErr'].std()]
        #data[temp] = [np.power(10,linlaw(np.log10(temp), *poptL)),redDf['lWidthErr'].mean(),redDf['lWidthErr'].std()]
        
    erDf = pd.DataFrame(data=data).T
    erDf.rename(columns={0:'fitWidth',1:'erMean',2:'stdev',3:'erMed'},inplace=True)
    erDf.dropna(inplace=True)
    erDf.index.name = 'Flow'
    #erDf['meanErrPc'] = erDf['stdev']/erDf['fitWidth']
    erDf['meanErrPc'] = np.abs(erDf['erMean'])/erDf['fitWidth']
    erDf['min'] = erDf['fitWidth']+(erDf['erMean']-erDf['stdev'])
    erDf['min'] = erDf['min'].apply(lambda x: x if x>0.01 else float('nan'))
    erDf['max'] = erDf['fitWidth']+(erDf['erMean']+erDf['stdev'])
    display(erDf)
    ax = erDf.plot(title=str(site),kind='bar',y='meanErrPc')
    # manipulate
    vals = ax.get_yticks()
    ax.set_yticklabels(['{:,.1%}'.format(x) for x in vals])
    plt.show()
    
    #plt.figure(figsize=(10, 5))#,title=site)
    fig, ax = plt.subplots()
    myDf.plot(x='Width', y='Flow',logx=True, logy=True, kind='scatter',title=site,ax=ax)
    WidthFLog, flowFLog = zip(*sorted(zip(WidthFLog, flowFLog)))
    ax.plot(WidthFLog, flowFLog, color='red', label='log fit')
    WidthFPow, flowFPow = zip(*sorted(zip(WidthFPow, flowFPow)))
    ax.plot(WidthFPow, flowFPow, color='green', label='Pow fit')
    ax.plot(erDf['min'],erDf.index,color='orange', label='-1Sig')
    ax.plot(erDf['max'],erDf.index,color='yellow', label='+1Sig')
    #plt.xlim([myDf['Width'].min(),myDf['Width'].max()])
    #plt.ylim([myVar[myVar>0].min(),myVar.max()])
    plt.legend(loc="upper left")
    plt.show()