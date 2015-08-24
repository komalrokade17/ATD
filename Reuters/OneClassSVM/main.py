import os, re
import numpy as np
from sklearn import svm
from sklearn import metrics

LDAPath = '/home/studadmin/Dropbox/ATDFinal/lda'
path = '/home/studadmin/Dropbox/ATDFinal/Reuters'

anom_per = 50

seed0 = 3181914101
np.random.seed(seed0)
N = 9469
trainfile = path + '/data/trdocs.txt'
testfile = path + '/data/tdocs'+str(anom_per) + '.txt'
tlblfile = path + '/data/tlbls'+str(anom_per) + '.txt'


anomlist = ['coffee','ship']
fp = open(tlblfile)
lbllist = fp.readlines()
fp.close()

# read training docs
fp = open(trainfile,'r')
rawdocs = fp.readlines()
fp.close()
Dtr = len(rawdocs)

trX = np.zeros((Dtr,N))
for d,doc in enumerate(rawdocs):
	wrds = re.findall('([0-9]*):[0-9]*',doc)
	cnts = re.findall('[0-9]*:([0-9]*)',doc)
	total = np.sum([float(x) for x in cnts])
	for n,w in enumerate(wrds):
		#trX[d,int(w)] = 1.0
		trX[d,int(w)] = float(cnts[n])/total

# read test docs
fp = open(testfile,'r')
rawdocs = fp.readlines()
fp.close()
Dt = len(rawdocs)

tX = np.zeros((Dt,N))
for d,doc in enumerate(rawdocs):
	wrds = re.findall('([0-9]*):[0-9]*',doc)
	cnts = re.findall('[0-9]*:([0-9]*)',doc)
	total = np.sum([float(x) for x in cnts])
	for n,w in enumerate(wrds):
		#tX[d,int(w)] = 1.0
		tX[d,int(w)] = float(cnts[n])/total


nulist = np.arange(1e-5, 0.4, 0.05)
Mlist = np.arange(14,32,2)
F1score = np.zeros((len(Mlist), len(nulist)))
fpres = open('results.txt','w')
fpres.write('')
fpres.close()

for n1,nu in enumerate(nulist):
	# train svm
	clf = svm.OneClassSVM(nu=nu, kernel="linear")
	clf.fit(trX)

	# test svm
	pred_test = clf.predict(tX)

	for m1,M in enumerate(Mlist):
		if n1==0:
			# run lda on test data
			seed = np.random.randint(seed0)
			cmdtxt = LDAPath + '/lda ' + str(seed) + ' est 0.1 ' + str(M) + ' ' + LDAPath + '/settings2.txt ' + testfile + ' seeded dirlda' + str(M) 
			print('Running LDA on test set')
			os.system(cmdtxt + ' > /dev/null')

		test_theta = np.loadtxt('dirlda'+str(M)+'/final.gamma')
		sumtheta = np.sum(test_theta,1)
		test_theta = test_theta/sumtheta.reshape(-1,1)		

		# hard assign each doc to a topic to form the groups
		group_assgnmt = np.argmax(test_theta,1)

		# count number of anomalies in each cluster
		anomcnt = np.zeros(M)
		anomind = np.where(pred_test == -1)[0]
		for x in anomind:
			g = group_assgnmt[x]
			anomcnt[g] += 1.0

		for g in range(M): # normalize by # samples in each group
			anomcnt[g] = anomcnt[g]/float(len(np.where(group_assgnmt==g)[0]))
		maxgroupind = np.argsort(-anomcnt)

		flist = list()
		reclist = list()
		preclist = list()
		auclist = list()

		fpres = open('results.txt','a')
		fpres.write('************************************\n')
		for g in maxgroupind[0:2]:

			ind = np.where(group_assgnmt == g)[0]
			Ssize = len(ind)

			step_num = np.zeros(len(anomlist))
			step_recall = np.zeros(len(anomlist))
			step_precision = np.zeros(len(anomlist))
			step_F1 = np.zeros(len(anomlist))
			step_auc = np.zeros(len(anomlist))

			for a0,anomlbl in enumerate(anomlist):
				a = [1 for x in lbllist if anomlbl in x]
				Danom = float(len(a))
				rec = np.zeros(Ssize)
				prec = np.zeros(Ssize)
				l = 1
				tp = 0
				for i in range(Ssize):
					doclbl = lbllist[ind[i]]
					if anomlbl in doclbl:
						tp += 1.0
					prec[i] = (tp/(i+1.0))
					rec[i] = (tp/Danom)

				step_num[a0] = tp
				step_recall[a0] = rec[-1]
				step_precision[a0] = prec[-1]
				if (rec[-1]+prec[-1]) > 0:
					step_F1[a0] = 2.0*prec[-1]*rec[-1]/(rec[-1]+prec[-1])
				if Ssize < 2:
					step_auc[a0] = 0.0
				else:
					step_auc[a0] = metrics.auc(rec, prec)

			# assign this group to the lbl of argmax(step_num)
			a0 = np.argmax(step_num)
			flist.append(step_F1[a0])
			reclist.append(step_recall[a0])
			preclist.append(step_precision[a0])
			auclist.append(step_auc[a0])

			fpres.write('group %d: size = %d, anomscore = %f, anomlbl = %s, recall = %f, precision = %f, auc = %f, f1 = %f\n' %(g,Ssize,anomcnt[g],anomlist[a0],step_recall[a0],step_precision[a0],step_auc[a0],step_F1[a0]))

		F1score[m1,n1] = np.mean(flist)
		print('M = %d, nu = %f, F1-score = %f' %(M, nu, F1score[m1,n1]))
		fpres.write('M = %d, nu = %f, F1-score = %f\n' %(M, nu, F1score[m1,n1]))
		fpres.close()

fpres = open('results.txt','a')
fpres.write('############################################\n')
amax = np.argmax(F1score)
m1 = amax/len(nulist)
n1 = amax%len(nulist)
fpres.write('Best F1-score: M = %d, nu = %f, F1-score = %f' %(Mlist[m1],nulist[n1],F1score[m1,n1]))
fpres.close()
