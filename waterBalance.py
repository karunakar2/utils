#!/bin/python
import matplotlib.pyplot as plt
import math
import numpy as np

fName = "bridgePa-model-avgPET.csv"

rainDepth = []
PET = []
AET = []
drainage = []
SM = []
fT = []
smObs = []

with open(fName,"r") as f:
    for line in f:
        temp = line.split(',')
        if temp:
            rainDepth.append(float(temp[1]))
            PET.append(float(temp[2]))
            smObs.append(float(temp[3])/100)
        #print(line)

#plt.plot(rainDepth)
#plt.scatter(rainDepth,PET)
#plt.axis([0, 60, 0, 10])
#plt.show()

#consts
#loams #sand #coeffcients
layerDepth =108/0.463 #376 /0.453 #mm
# Model parameter
initialSaturation                =   0.117 #0.095 # Initial condition                                                          #not much of influence
fieldCapacity	            =   0.2*layerDepth #0.155*layerDepth # mm Field capacity                                    #due to the implicit nature almost rounds off
Psi_av_L                            =   89* -1/layerDepth #111 * -1/layerDepth # Psi/L parameter of infiltration
satInfRate                         =  1.32 *0.5#21.8 * 0.5# mm/h Ks parameter of infiltration
drainageInfiltrationRate    =  1.15* 10.4/24 #2.122E6 # mm/h Ks param eter of drainage
brookCoreyExponent       =  2.4 # exponent of drainage

# Thresholds for numerical computations
maxIter         = 100;
noData          =-9999;
smErThreshold =	0.01; 	# Water Content
infiltrationThreshold = 0.01;	# Infiltration

# Parameter initialization
cumInfTemp	=	0;
infFrontDepth	=	0.00001;				#cumulative infiltration
W_init		=	noData;
smWatVol_prev	=	initialSaturation*fieldCapacity;	# initial condition in mm
cumulativeRain	=	0;
actInfRate	=	0;	                            	# hourly infiltration
ii		=	1;

f = open(fName[:-3]+'out',"w")
f.write('rainDepth,SM,AET,drainage\n')
for timeStep in range(0,len(PET)):			#throughout the time steps
    smWatVol=smWatVol_prev
    miter=0		                                          # miterative solution within each time step
    errSM=1000	                                                        # make sure it passes through following loop in the first instance
    AET.append(0)
    drainage.append(0)
    while errSM>smErThreshold:	                            #smVol error check
        # infiltration computation (Green-Ampt)
        miter=miter+1;  				#J starts at 1 till 100
        #fT.append(cumulativeRain) 
        if (cumulativeRain<=0.001):                                  #should be false when rained and after 3 steps || no rain sofar
            #print('no rain',timeStep)
            if  (rainDepth[timeStep]>0):		            #if it rained at this step
                W_init=smWatVol		            #using soilmoisture vol from intial condition
                Psi=Psi_av_L*(fieldCapacity-W_init);              # dryCond || avg psi * smdeficit |soil water matric capillary head
                #fT.append(Psi)
                #print(timeStep,miter,Psi_av_L, Psi)
            else:					#reset if there's no rain
                W_init=noData;
                ii=1					##reset reduced infiltration rate if dry, see ln 80
                cumInfTemp=0;
                infFrontDepth=0.00001;

        if W_init != noData: 	##neq|| indicative of rained by now, see line 68
            if miter>1:		##if all params (line 99 onwards) are estimated atleast once
                ii=ii-1##zero if no rain so far
            ##Reduced infiltration rate
            #actInfRate=(ii==1)*1000+(ii!=1)*satInfRate*(1-Psi/infFrontDepth)#limit to 1000, initially will be large because of small infFrontDepth, see line 46
            actInfRate=(ii==1)*100*satInfRate+(ii!=1)*satInfRate*(1-Psi/infFrontDepth) #the infiltration rates can be two orders high for diff. densities
            if actInfRate >(2*satInfRate):
                #print('abnormal infiltration rates', actInfRate,Psi/infFrontDepth)
                actInfRate = 2*satInfRate
            
            if actInfRate>rainDepth[timeStep]:
                actInfRate=rainDepth[timeStep]	# restrict max to rainfall at that point of time
                infFrontDepth+=rainDepth[timeStep]
            else:				
                cumInfTemp=infFrontDepth;
                erInf=1000;
                while erInf>infiltrationThreshold: # iteration to estimate the partial infiltration rate by progressive correction to front depth
                    #print('infiltration error',erInf)
                    cumInfErFn=cumInfTemp- Psi*math.log((infFrontDepth-Psi)/(cumInfTemp-Psi))+satInfRate;
                    erInf=abs((infFrontDepth-cumInfErFn)/infFrontDepth);
                    infFrontDepth=infFrontDepth+0.01;
                actInfRate=infFrontDepth-cumInfTemp;
            cumInfTemp=infFrontDepth;
            #fT.append(infFrontDepth)
            ##fT.append(actInfRate)
            ii=ii+1

        AET[timeStep]=PET[timeStep]*smWatVol/fieldCapacity						#actual evaporation
        try:
            drainage[timeStep]=drainageInfiltrationRate*math.pow((smWatVol/fieldCapacity),(brookCoreyExponent)) #drainage percolation
        except Exception as e:
            drainage[timeStep] = 0
            print(smWatVol/fieldCapacity,'BC error')
        smWatVol_now=smWatVol_prev+(actInfRate-AET[timeStep]-drainage[timeStep]);

        if smWatVol_now>=fieldCapacity:
            smWatVol_now=fieldCapacity	# can't exceed field capacity

        errSM=abs((smWatVol_now-smWatVol)/fieldCapacity);
        #print(errSM)
        smWatVol=smWatVol_now;

        if(smWatVol<0):
            print('error, negative soil moisture')
            
		
        if miter==maxIter:
            print('exceeded iterations at timestep', timeStep)
            break				#break if doesn't converge with 100steps
	
    smWatVol_prev=smWatVol_now;
    SM.append(smWatVol_now/fieldCapacity)		#in percentage to hundred i.e fraction 0-1

    if timeStep>3:
        #cumulativeRain=sum(rainDepth(timeStep-3:timeStep))		#cumulative, always 1 step behind
        #cumulativeRain = sum(rainDepth[timeStep-1:timeStep])
        cumulativeRain = rainDepth[timeStep]

    #write to a file for manual check
    f.write(str(rainDepth[timeStep])+','+str(SM[timeStep])+','+str(AET[timeStep])+','+str(drainage[timeStep])+'\n')
f.close()

print(sum(drainage)/sum(rainDepth))
print(sum(AET)*2/365/10,sum(drainage),':AET-day, G-annual')
print(np.sqrt(np.mean((np.array(SM)-np.array(smObs))**2)))
#plt.plot(fT)

fig = plt.figure(figsize = (12,9))
ax = plt.subplot(311)
axes = [ax, ax.twinx()]
axes[0].plot(SM,color="orange")
axes[0].set_ylabel('SM',color="orange")
axes[1].plot(rainDepth,color="green")
axes[1].set_ylabel('Rain',color="green")

ax = plt.subplot(312)
axes = [ax, ax.twinx()]
axes[0].plot(AET,color="blue")
axes[0].set_ylabel('AET',color="blue")
axes[1].plot(drainage,color="green")
axes[1].set_ylabel('G',color="green")

ax = plt.subplot(313)
ax.plot(SM,color="orange")
ax.set_ylabel('SM',color="orange")
ax.plot(smObs,color="blue")
ax.set_ylabel('ob SM',color="blue")

plt.show()
