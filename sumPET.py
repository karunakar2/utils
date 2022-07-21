import glob
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

PETfiles = glob.glob('RW-MOD16A2.A*.merged.wgs84.tiff')

for fName in PETfiles:
    try :
        A = A + mpimg.imread(fName);
    except:
        A = mpimg.imread(fName);

plt.imshow(A);
plt.show()
#plt.imwrite(A,'AVG.tif','tif');
