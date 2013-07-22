# cca <master> <inputFile> <outputFile> <label1> <label2> <k> <c>
# 
# compute canonical correlations on two data sets
# input is a local text file or a file in HDFS
# format should be rows of ' ' separated values
# first entry in each row indicates which dataset
# - example: space (rows) x time (cols)
# - rows should be whichever dim is larger
# 'label1' and 'label2' specify the datasets
# 'k' is number of principal components for dim reduction
# 'c' is the number of canonical correlations to return
# writes components to text (in input space)


import sys
import os
from numpy import *
from scipy.linalg import *
from scipy.signal import butter, lfilter
import logging
from pyspark import SparkContext

if len(sys.argv) < 8:
  print >> sys.stderr, \
  "(ica) usage: cca <master> <inputFile> <outputFile> <label1> <label2> <k> <c>"
  exit(-1)

def parseVector(line):
    return array([float(x) for x in line.split(' ')])

def butterBandpass(lowcut, highcut, fs, order=5):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a

def butterBandpassFilter(data, lowcut, highcut, fs, order=5):
    b, a = butterBandpass(lowcut, highcut, fs, order=order)
    y = lfilter(b, a, data)
    return y

# parse inputs
sc = SparkContext(sys.argv[1], "cca")
inputFile = str(sys.argv[2])
label1 = int(sys.argv[4])
label2 = int(sys.argv[5])
k = int(sys.argv[6])
c = int(sys.argv[7])
outputFile = "cca-"+str(sys.argv[3])+"-labels-"+str(label1)+"-"+str(label2)+"-k-"+str(k)+"-cc-"+str(c)
if not os.path.exists(outputFile):
    os.makedirs(outputFile)
logging.basicConfig(filename=outputFile+'/'+'stdout.log',level=logging.INFO,format='%(asctime)s %(message)s',datefmt='%m/%d/%Y %I:%M:%S %p')

# load data and split according to label
logging.info("(cca) loading data...")
lines = sc.textFile(inputFile)
data = lines.map(parseVector)
data1 = data.filter(lambda x : x[0] == label1).cache()
data2 = data.filter(lambda x : x[0] == label2).cache()

# get dims
n1 = data1.count()
n2 = data2.count()
m1 = len(data1.first())-1
m2 = len(data2.first())-1

# remove label
data1 = data1.map(lambda x : x[1:m1+1])
data2 = data2.map(lambda x : x[1:m2+1])

# remove means
logging.info("(cca) mean subtraction")
data1mean = data1.reduce(lambda x,y : x+y) / n1
data1sub = data1.map(lambda x : x - data1mean)
data2mean = data2.reduce(lambda x,y : x+y) / n2
data2sub = data2.map(lambda x : x - data2mean)

# filter data
logging.info("(cca) bandpass filtering")
data1sub = data1sub.map(lambda x : butterBandpassFilter(x,0.02,0.4,1,6))

# do dimensionality reduction
logging.info("(cca) reducing dimensionality")
cov1 = data1sub.map(lambda x : outer(x,x)).reduce(lambda x,y : (x + y)) / (n1 - 1)
w1, v1 = eig(cov1)
v1 = v1[:,argsort(w1)[::-1]];
cov2 = data2sub.map(lambda x : outer(x,x)).reduce(lambda x,y : (x + y)) / (n1 - 1)
w2, v2 = eig(cov2)
v2 = v2[:,argsort(w2)[::-1]];

# mean subtract inputs to cca
x1 = v1[:,0:k]
x2 = v2[:,0:k]
x1 = x1-mean(x1,axis=0)
x2 = x2-mean(x2,axis=0)

# do cca
logging.info("(cca) computing canonical correlations")
q1,r1,p1 = qr(x1,mode='economic',pivoting=True)
q2,r2,p2 = qr(x2,mode='economic',pivoting=True)
l,d,m = svd(dot(transpose(q1),q2))
A = lstsq(r1,l * sqrt(n1-1))[0]
B = lstsq(r2,transpose(m) * sqrt(n2-1))[0]
A = A[argsort(p1)[::1],:]
B = B[argsort(p2)[::1],:]

# write output
logging.info("(cca) writing results...")
for ic in range(0,c):
	time1 = dot(v1[:,0:k],A[:,ic])
	out1 = data1sub.map(lambda x : inner(x,dot(v1[:,0:k],A[:,ic])))
	savetxt(outputFile+"/"+"label-"+str(label1)+"-cc-"+str(ic)+".txt",out1.collect(),fmt='%.8f')
	savetxt(outputFile+"/"+"label-"+str(label1)+"-time-"+str(ic)+".txt",time1,fmt='%.8f')
	time2 = dot(v2[:,0:k],B[:,ic])
	out2 = data2sub.map(lambda x : inner(x,dot(v2[:,0:k],B[:,ic])))
	savetxt(outputFile+"/"+"label-"+str(label2)+"-cc-"+str(ic)+".txt",out2.collect(),fmt='%.8f')
	savetxt(outputFile+"/"+"label-"+str(label2)+"-time-"+str(ic)+".txt",time2,fmt='%.8f')


