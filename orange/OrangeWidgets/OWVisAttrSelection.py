import orange
import orngFSS
import statc
import orngCI
from Numeric import *
from LinearAlgebra import *

###########################################################################################
##### FUNCTIONS FOR CALCULATING ATTRIBUTE ORDER USING Oblivious decision graphs
###########################################################################################
def replaceAttributes(index1, index2, merged, data):
	attrs = list(data.domain)
	attrs.remove(data.domain[index1])
	attrs.remove(data.domain[index2])
	domain = orange.Domain(attrs+ [merged])
	return data.select(domain)


def getFunctionalList(data):
	bestQual = -10000000
	bestAttr = -1
	testAttrs = []

	dataShort = orange.Preprocessor_dropMissing(data)
	# remove continuous attributes from data
	disc = []
	for i in range(len(dataShort.domain.attributes)):
		# keep only discrete attributes that have more than one value
		if dataShort.domain.attributes[i].varType == orange.VarTypes.Discrete and len(dataShort.domain.attributes[i].values) > 1: disc.append(dataShort.domain.attributes[i].name)
	if disc == []: return []
	discData = dataShort.select(disc + [dataShort.domain.classVar.name])

	remover = orngCI.AttributeRedundanciesRemover(noMinimization = 1)
	newData = remover(discData, weight = 0)

	for attr in newData.domain.attributes: testAttrs.append(attr.name)

	# compute the best attribute combination
	for i in range(len(newData.domain.attributes)):
		vals, qual = orngCI.FeatureByMinComplexity(newData, [newData.domain.attributes[i], newData.domain.classVar])
		if qual > bestQual:
			bestQual = qual
			bestAttr = newData.domain.attributes[i].name
			mergedVals = vals
			mergedVals.name = newData.domain.classVar.name

	if bestAttr == -1: return []
	outList = [bestAttr]
	newData = replaceAttributes(bestAttr, newData.domain.classVar, mergedVals, newData)
	testAttrs.remove(bestAttr)
	
	while (testAttrs != []):
		bestQual = -10000000
		for attrName in testAttrs:
			vals, qual = orngCI.FeatureByMinComplexity(newData, [mergedVals, attrName])
			if qual > bestQual:
				bestqual = qual
				bestAttr = attrName

		vals, qual = orngCI.FeatureByMinComplexity(newData, [mergedVals, bestAttr])
		mergedVals = vals
		mergedVals.name = newData.domain.classVar.name
		newData = replaceAttributes(bestAttr, newData.domain.classVar, mergedVals, newData)
		outList.append(bestAttr)
		testAttrs.remove(bestAttr)

	# new attributes have "'" at the end of their names. we have to remove that in ored to identify them in the old domain
	for index in range(len(outList)):
		if outList[index][-1] == "'": outList[index] = outList[index][:-1]
	return outList


###########################################################################################
##### FUNCTIONS FOR CALCULATING ATTRIBUTE ORDER USING Fisher discriminant analysis
###########################################################################################
def fisherDiscriminant(rawdata, data, indices, classIndex):
	matrixDict = {}
	if classIndex in indices: indices.remove(classIndex)

	for i in range(len(rawdata)):
		valid = 1
		for index in indices:
			if data[index][i] == "?": valid = 0
		if not valid: continue

		example = []
		for index in indices: example.append(data[index][i])
		if not matrixDict.has_key(rawdata[i].getclass().value): matrixDict[rawdata[i].getclass().value] = []
		matrixDict[rawdata[i].getclass().value].append(example)



	means = {}
	normArrays ={}
	scatters = {}
	suma = array([0.0]*len(indices))
	for key in matrixDict.keys():
		#f = open("E:\\temp\\data\\" + key + ".txt", "wt")
		#f.write(str(array(matrixDict[key]).tolist()))
		#f.close()
		arr = array(matrixDict[key])
		means[key] = sum(arr)/ float(len(matrixDict[key]))
		normArrays[key] = arr - means[key]
		scatters[key] = matrixmultiply(transpose(normArrays[key]), normArrays[key])
		for val in normArrays[key]:
			suma = suma + val*transpose(val)
		
	meanDiff = means[matrixDict.keys()[0]] - means[matrixDict.keys()[1]]
	res = abs(meanDiff)/suma
	res = res/sum(res)
	ret = [[matrixDict.keys()[0], matrixDict.keys()[1], res.tolist()]]
	return ret	

		

	ret = []
	for i in range(len(matrixDict.keys())):
		for j in range(i+1, len(matrixDict.keys())):
			key1 = matrixDict.keys()[i]
			key2 = matrixDict.keys()[j]
			try:
				sc =  scatters[key1] + scatters[key2]
				m = transpose(means[key1] - means[key2])
				w = matrixmultiply(inverse(sc), m)
				suma=0.0
				for val in w: suma += float(abs(val))
				w = w / suma
				ret.append([key1, key2, w.tolist()])
			except:
				print "singularity at ", key1, " and ", key2
	return ret
	


###########################################################################################
##### FUNCTIONS FOR CALCULATING ATTRIBUTE ORDER USING CORRELATION
###########################################################################################

def insertToSortedList(array, val, names):
	for i in range(len(array)):
		if val > array[i][0]:
			array.insert(i, [val, names])
			return
	array.append([val, names])

# does value exist in array? return index in array if yes and -1 if no
def member(array, value):
	for i in range(len(array)):
		for j in range(len(array[i])):
			if array[i][j]==value:
				return i
	return -1
		

# insert two attributes to the array in such a way, that it will preserve the existing ordering of the attributes
def insertToCorrList(array, attr1, attr2):
	index1 = member(array, attr1)
	index2 = member(array, attr2)
	if index1 == -1 and index2 == -1:
		array.append([attr1, attr2])
	elif (index1 != -1 and index2 == -1) or (index1 == -1 and index2 != -1):
		if index1 == -1:
			index = index2
			newVal = attr1
			existingVal = attr2
		else:
			index = index1
			newVal = attr2
			existingVal = attr1
			
		# we insert attr2 into existing set at index index1
		pos = array[index].index(existingVal)
		if pos < len(array[index])/2:   array[index].insert(0, newVal)
		else:						   array[index].append(newVal)
	else:
		# we merge the two lists in one
		if index1 == index2: return
		array[index1].extend(array[index2])
		array.remove(array[index2])
	

# create such a list of attributes, that attributes with high correlation lie together
def getCorrelationList(data):
	# create ordinary list of data values	
	dataList = []
	dataNames = []
	for index in range(len(data.domain)):
		if data.domain[index].varType != orange.VarTypes.Continuous: continue
		temp = []
		for i in range(len(data)):
			temp.append(data[i][index])
		dataList.append(temp)
		dataNames.append(data.domain[index].name)

	# compute the correlations between attributes
	correlations = []
	for i in range(len(dataNames)):
		for j in range(i+1, len(dataNames)):
			val, prob = statc.pearsonr(dataList[i], dataList[j])
			insertToSortedList(correlations, abs(val), [i,j])
			#print "correlation between %s and %s is %f" % (dataNames[i], dataNames[j], val)

	i=0
	mergedCorrs = []
	while i < len(correlations) and correlations[i][0] > 0.1:
		insertToCorrList(mergedCorrs, correlations[i][1][0], correlations[i][1][1])
		i+=1

	hiddenList = []
	for i in range(len(correlations)):
		if member(mergedCorrs, correlations[i][1][0]) == -1 and dataNames[correlations[i][1][0]] not in hiddenList:
			hiddenList.append(dataNames[correlations[i][1][0]])
		if member(mergedCorrs, correlations[i][1][1]) == -1 and dataNames[correlations[i][1][1]] not in hiddenList:
			hiddenList.append(dataNames[correlations[i][1][1]])

	shownList = []
	for i in range(len(mergedCorrs)):
		for j in range(len(mergedCorrs[i])):
			shownList.append(dataNames[mergedCorrs[i][j]])

	if len(dataNames) == 1: shownList += dataNames
	return (shownList, hiddenList)


##############################################
# SELECT ATTRIBUTES ##########################
##############################################
def selectAttributes(data, graph, attrContOrder, attrDiscOrder):
	shown = []; hidden = []	# initialize outputs

	## both are RELIEF
	if attrContOrder == "RelieF" and attrDiscOrder == "RelieF":
		newAttrs = orngFSS.attMeasure(data, orange.MeasureAttribute_relief(k=20, m=50))
		for item in newAttrs:
			if float(item[1]) > 0.01:   shown.append(item[0])
			else:					   hidden.append(item[0])
		return (shown, hidden)

	## both are NONE
	elif attrContOrder == "None" and attrDiscOrder == "None":
		for item in data.domain.attributes:	shown.append(item.name)
		return (shown, hidden)

	###############################
	# sort continuous attributes
	if attrContOrder == "None":
		for item in data.domain:
			if item.varType == orange.VarTypes.Continuous: shown.append(item.name)
	elif attrContOrder == "RelieF":
		newAttrs = orngFSS.attMeasure(data, orange.MeasureAttribute_relief(k=20, m=50))
		for item in newAttrs:
			if data.domain[item[0]].varType != orange.VarTypes.Continuous: continue
			if float(item[1]) > 0.01:   shown.append(item[0])
			else:					   hidden.append(item[0])
	elif attrContOrder == "Correlation":
		(shown, hidden) = getCorrelationList(data)	# get the list of continuous attributes sorted by using correlation
	elif attrContOrder == "Fisher discriminant" and data.domain.classVar:
		indices = []; names = []
		for i in range(len(data.domain)):
			if data.domain[i].varType != orange.VarTypes.Continuous: continue

			# if graph didn't yet scale the data then show all continuous attributes
			if graph.noJitteringScaledData == []: shown.append(data.domain[i].name)
			else:
				indices.append(i);
				names.append(data.domain[i].name)
		classIndex = list(data.domain).index(data.domain.classVar)
		if classIndex in indices: indices.remove(classIndex)

		attrs = fisherDiscriminant(data, graph.noJitteringScaledData, indices, classIndex)
		tempW = [0] * len(indices)
		#f = open("E:\\temp.txt", "wt")
		#for name in names: f.write(name + "\t")
		#f.write("\n")
		for (key1, key2, w) in attrs:
			for i in range(len(w)):
				#f.write("%.3f\t" % w[i])
				tempW[i] += abs(w[i])
			#f.write("\n")
		#f.close()

		# normalize tempW
		sumW = float(sum(tempW))
		for i in range(len(tempW)):
			tempW[i] = tempW[i] / sumW

		suma = 0
		print tempW
		while suma < 0.9:
			index = tempW.index(max(tempW))
			print names[index], tempW[index]
			suma += tempW[index]
			shown.append(names[index])
			names.remove(names[index])
			tempW.remove(tempW[index])

		for name in names: hidden.append(name)
	else:
		print "Incorrect value for attribute order"

	################################
	# sort discrete attributes
	if attrDiscOrder == "None":
		for item in data.domain.attributes:
			if item.varType == orange.VarTypes.Discrete: shown.append(item.name)
	elif attrDiscOrder == "RelieF":
		newAttrs = orngFSS.attMeasure(data, orange.MeasureAttribute_relief(k=20, m=50))
		for item in newAttrs:
			if data.domain[item[0]].varType != orange.VarTypes.Discrete: continue
			if item[0] == data.domain.classVar.name: continue
			if float(item[1]) > 0.01:   shown.append(item[0])
			else:					   hidden.append(item[0])
	elif attrDiscOrder == "GainRatio" or attrDiscOrder == "Gini":
		if attrDiscOrder == "GainRatio":   measure = orange.MeasureAttribute_gainRatio()
		else:								   measure = orange.MeasureAttribute_gini()
		if data.domain.classVar.varType != orange.VarTypes.Discrete:
			measure = orange.MeasureAttribute_relief(k=20, m=50)

		# create new table with only discrete attributes
		attrs = []
		for attr in data.domain.attributes:
			if attr.varType == orange.VarTypes.Discrete: attrs.append(attr)
		attrs.append(data.domain.classVar)
		dataNew = data.select(attrs)
		newAttrs = orngFSS.attMeasure(dataNew, measure)
		for item in newAttrs:
				shown.append(item[0])

	elif attrDiscOrder == "Oblivious decision graphs":
			shown.append(data.domain.classVar.name)
			attrs = getFunctionalList(data)
			for item in attrs:
				shown.append(item)
			for attr in data.domain.attributes:
				if attr.name not in shown and attr.varType == orange.VarTypes.Discrete:
					hidden.append(attr.name)
	else:
		print "Incorrect value for attribute order"

	#################################
	# if class attribute hasn't been added yet, we add it
	if data.domain.classVar.name not in shown and data.domain.classVar.name not in hidden:
		shown.append(data.domain.classVar.name)


	return (shown, hidden)