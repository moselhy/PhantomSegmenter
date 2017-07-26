class NrrdConverter(object):

	def __init__(self, dcmpath):
		self.dcmpath = dcmpath

	def convertNrrd(self):
		import os, shutil, dicom, sys, logging, subprocess, slicer
		dcmDict = {}
		volArray = []


		pathwalk = os.walk(self.dcmpath)
		for root, dirs, files in pathwalk:
			for filename in files:
				filename = os.path.join(root, filename)
				ds = dicom.read_file(filename)
				seriesNumber = ds.SeriesNumber

				if seriesNumber not in dcmDict:
					dcmDict[seriesNumber] = []
				
				dcmDict[seriesNumber].append(filename)


		userpath = os.path.expanduser('~')
		tmpfolder = os.path.join(userpath, "Documents", "Temporary")
		if os.path.exists(tmpfolder):
			shutil.rmtree(tmpfolder)

		for sn, dcmlist in dcmDict.items():
			snfolder = os.path.join(tmpfolder, str(sn))
			os.makedirs(snfolder)
			for dcm in dcmlist:
				shutil.copy(dcm, snfolder)

			outputVolume = os.path.join(snfolder, "completevolume.nrrd")
			converterpath = os.path.normpath(r"C:\Users\cmccu\Documents\slicerweek\convertToNrrd\DicomToNrrdConverter.exe")
			runnerpath = os.path.join(os.path.split(converterpath)[0], "runner.bat")
			execString = runnerpath + " " + converterpath + " --inputDicomDirectory " + snfolder + " --outputVolume " + outputVolume
			# logging.info(execString)
			os.system(execString)
			
			volNode = slicer.util.loadVolume(outputVolume, returnNode = True)[1]
			volNode.SetName(str(sn))
			volArray.append(volNode)
			
		return volArray
			
		shutil.rmtree(tmpfolder)