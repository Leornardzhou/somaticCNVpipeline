#!/usr/bin/python
import os,sys,inspect
import numpy as np

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 
import common
import config as cfg





def getNormalCN(chrom, gender):
	normalCN = 2.
	if chrom in ['chrX', 'chrY'] and gender == 'M':
		normalCN = 1.
	elif chrom == 'chrY' and gender == 'F':
		normalCN = 0.
	return normalCN





def mergeSegCN(seg1, seg2, intD=False):
	currentWeight = seg1['end'] - seg1['start']
	nextWeight = seg2['end'] - seg2['start']
	weightedAverageCN = np.average([seg1['CN'], seg2['CN']], weights = [currentWeight, nextWeight])
	
	if intD:
		currentIntdist = abs(np.round(seg1['CN']) - seg1['CN'])
		nextIntdist = abs(np.round(seg2['CN']) - seg2['CN'])
		weightedAverageIntdist = np.average([currentIntdist, nextIntdist], weights = [currentWeight, nextWeight])
		mergeIntdist = abs(np.round(weightedAverageCN) - weightedAverageCN)
		
		return weightedAverageCN, weightedAverageIntdist, mergeIntdist

	else:
		return weightedAverageCN
	
	
	
	

def mergeCNinitial(dataDict, gender):
	newData = [dataDict[0]]

	for i in dataDict[1:]:
		addData = i

		if newData[-1]['chrom'] == i['chrom'] and np.round(newData[-1]['CN']) == np.round(i['CN']):
	#		currentWeight = newData[-1]['end'] - newData[-1]['start']
	#		nextWeight = i['end'] - i['start']
	#		weightedAverageCN = np.average([newData[-1]['CN'], i['CN']], weights = [currentWeight, nextWeight])
			weightedAverageCN, weightedAverageIntdist, mergeIntdist = mergeSegCN(newData[-1], i, intD=True)
	#		mergeIntdist = abs(np.round(weightedAverageCN) - weightedAverageCN)

	#		currentIntdist = abs(np.round(newData[-1]['CN']) - newData[-1]['CN'])
	#		nextIntdist = abs(np.round(i['CN']) - i['CN'])
	#		weightedAverageIntdist = np.average([currentIntdist, nextIntdist], weights = [currentWeight, nextWeight])

			#previously was <=
			if mergeIntdist < weightedAverageIntdist or np.round(i['CN']) == getNormalCN(i['chrom'], gender):
			#	print 'passed', weightedAverageIntdist, mergeIntdist
				prevMerge = newData.pop()
				addData =	{
					'chrom': i['chrom'], 
					'start': prevMerge['start'], 
					'end': i['end'], 
					'CN': weightedAverageCN
					}
			#else:
			#	print 'failed', weightedAverageIntdist, mergeIntdist

		newData.append(addData)

	return newData





def FUnC(dataDict, binDict, cutoffDict, gender):
	dataDict[-1]['end'] = max(binDict.keys())-1

	#for each entry, calc bin size, compare to cutoffDict
	for i in range(len(dataDict)):
		normalCN = getNormalCN(dataDict[i]['chrom'], gender)
		thisSize = binDict[dataDict[i]['end']+1] - binDict[dataDict[i]['start']]
		dataDict[i]['bins'] = thisSize
		
		if np.round(dataDict[i]['CN']) == normalCN:
			dataDict[i]['pass'] = 'eup'
		elif abs(np.round(dataDict[i]['CN']) - dataDict[i]['CN']) <= cutoffDict[thisSize]:
			dataDict[i]['pass'] = 'cnv'
		else:
			dataDict[i]['pass'] = 'no'
			
#	for i in dataDict:
#		print i['chrom'], i['start'], i['end'], i['CN'], i['bins'], i['pass']

	return dataDict





def mergeCNfinal(funcDict, numBins, binDict, gender, outDir, sample):
	"""		
	First, CNV calls < 3 bins are combined with the most similar neighbor (euploid or CNV)
	Second, adjacent passing CNVs with the same copy number (on same chrom) are combined into one call
	Third, small segments (<= 25 bins) that fail as CNV calls are either
		Combined with neighboring CNVs IF 
			Both are on the same chromosome
			Both have the same copy number
			Both pass FUnC
			Both are > 25 bins
			(because this indicates the baseline CN in this locus is not euploid)
		Otherwise, converted to euploid
	Euploid regions obviously stay euploid
	Large segments (>25 bins) are automatically treated as euploid too
	"""
	
	#pass 1: merge passing CNVs if same CN and same chrom#
	merge1 = [funcDict[0]]
	for i, j in enumerate(funcDict[1:]):
		thisEntry = j
		if j['pass'] == funcDict[i]['pass'] == 'cnv': #both entries passed FUnC
			if j['chrom'] == funcDict[i]['chrom']: #both entries on the same chromosome
				if np.round(j['CN']) == np.round(funcDict[i]['CN']): #both entries have the same copy number
					print 'NEED TO MERGE'
					print merge1[-1]
					print j
					raise SystemExit
					#thisEntry = ?
					#####################
		merge1.append(thisEntry)
				
	
	
	cnvList = []
	
	#go through every segment call
	for i in range(len(funcDict)):
		if funcDict[i]['chrom'] == 'chrY':
			break		
		normalCN = getNormalCN(funcDict[i]['chrom'], gender)


	raise SystemExit
	
	outfile = outDir + sample + 'CNVlist.txt'
	OUT = open(outfile, 'w')
	OUT.write('Chromosome\tStart\tEnd\tCopyNumber\n')
	for i in cnvList:
		OUT.write(i['chrom'])
		OUT.write('\t')
		OUT.write(str(refArray[[i['abspos']]]['chrStart']))
		OUT.write('\t')
		OUT.write(str(refArray[i]['abspos']['chrStart'] + refArray[i]['size'] - 1))
		OUT.write('\t')
		OUT.write(str(np.round(i['CN'])))
		OUT.write('\n')
	OUT.close





def FUnCone(sample, species, segmentDir, CNVdir, ploidy, gender):
	
	#import config info#
	interpretVars = cfg.Interpret()
	refArray = common.importInfoFile(interpretVars.binDict[species], [0, 1, 2, 4, 5], 'normref', skiprows=1)

	binDict = {y:x for x,y in enumerate(refArray['abspos'])} #make dict of ref array so I can calculate bin number
	binDict[refArray[-1]['abspos'] + refArray[-1]['size']+1] = len(refArray) #fix for last bin not having the correct end position#
	
	cutoffArray = np.loadtxt(interpretVars.cutoffFile, skiprows=1, dtype={'names': ('bins', 'intD'), 'formats': ('int', 'float')})
	cutoffDict = {x['bins']: x['intD'] for x in cutoffArray}
	
	
	
	#load segment data#
	segData, segArray = common.importSegData(sample, segmentDir, refArray)
	segData['CN'] = segData['CN'] * ploidy
	dataDict = [ {y: x[y] for y in segData.dtype.names} for x in segData ]

	
	
	#merge adjacent segments that have the same copy number, when merging improves intD#
	mergeDataDict = mergeCNinitial(dataDict, gender)
	
	
	
	#run FUnC#
	funcDataDict = FUnC(mergeDataDict, binDict, cutoffDict, gender)
	numFail = [x['pass'] for x in funcDataDict].count('no')
	numPass = [x['pass'] for x in funcDataDict].count('cnv')
	

	
	#second merge and write output file#
	mergeCNfinal(funcDataDict, len(refArray), binDict, gender, CNVdir, sample)
	raise SystemExit
	
	printText = '\t\tFinished performing FUnC on ' + sample + ', removed ' + str(numFail) + ' of ' + str(numFail + numPass) + ' CNV calls'
	print(printText)

	
	
	
####OLD-delete when second merge works
def junk(dataDict, numBins, binDict, gender, outDir, sample):
	cnvList = []
	
	#go through every segment call
	for i in range(len(dataDict)):
		if dataDict['i']['chrom'] == 'chrY':
			break		
		normalCN = getNormalCN(dataDict[i]['chrom'], gender)
			
		#if CNV passes, check if it should be merged with previous segment
		if dataDict[i]['pass'] == 'cnv':
			if i == 0:
				cnvList.append(dataDict[i])
			elif np.round(dataDict[i]['CN']) == np.round(dataDict[i-1]['CN']) and dataDict[i]['chrom'] == dataDict[i-1]['chrom']:
				cnvList[-1] = {'chrom': dataDict[i]['chrom'],
							  'start': cnvList[-1]['start'],
							  'end': dataDict[i]['end'],
							  'cn': np.round(np.mean([dataDict[i]['CN'], dataDict[i-1]['CN']])),
							  'pass': 'cnv'}
			else:
				cnvList.append(dataDict[i])
				

		###THIS REQUIRES MORE REWORKING, ITS CREATING SYNTAX ERRORS AND IS WRITTEN WAY TO COMPLICATEDLY
			#As a placeholder, I'm just skipping over it for now
		#if a CNV doesn't pass
		elif dataDict[i]['pass'] == 'no':
			mergeTest = False
			
			#if less than 25 bins
			thisSize = binDict[dataDict[i]['abspos'] + dataDict[i]['size']] - binDict[dataDict[i]['abspos']]
			if thisSize <= 25:
				pass
				#and both surrounding segments on same chrom 
					#with same CN that pass, merge w/ them (do they need to be large too?)
				
				#and prior seg on same chrom, next seg on diff chrom
					#with same CN that pass, merge w/ it
				
				#and prior seg on diff chrom, next seg on same chrom
					#with same CN that pass, merge w/ it
				
				
				
		#	if (binDict[dataDict[i]['abspos'] + dataDict[i]['size']] - binDict[dataDict[i]['abspos']] <= 25 and \
 		#	((i == 0 or np.round(binDict[i-1]['CN']) == np.round(binDict[i]['CN'])) and binDict[i-1]['chrom']) == np.round(binDict[i]['chrom'])) and \
		#	   (np.round(binDict[i+1]['CN']) == np.round(binDict[i]['CN'])) and binDict[i+1]['chrom']) == np.round(binDict[i]['chrom']) and \
		#	   ((i == 0 or binDict[i-1]['pass'] == 'cnv') and binDict[i+1]['pass'] == 'cnv') \
		#	):
				
			if mergeTest:
				cnvList[-1] = {'chrom': dataDict[i]['chrom'],
							  'start': cnvList[-1]['start'],
							  'end': dataDict[i]['end'],
							  'cn': np.round(np.mean([dataDict[i]['CN'], dataDict[i-1]['CN']])),
							  'pass': 'cnv'}
	#			mergeTest = False
				
				
			#in any other situation (more than 25 bins, euploid call, lack of concordance), convert to euploid
			else:
				continue #Wait, this isn't doing any sort of conversion...is that fine? I think so...

	raise SystemExit
