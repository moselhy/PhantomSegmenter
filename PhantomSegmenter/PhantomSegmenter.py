import os, sys
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging

#
# PhantomSegmenter
#

class PhantomSegmenter(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Phantom Segmenter"
    self.parent.categories = ["Segmentation"]
    self.parent.dependencies = []
    self.parent.contributors = ["Colin McCurdy, Mohamed Moselhy (Western University)"]
    self.parent.helpText = """
This module automatically segments a phantom using 3DSlicer's Grow From Seeds algorithm
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Colin McCurdy and Mohamed Moselhy
"""

#
# PhantomSegmenterWidget
#

class PhantomSegmenterWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Instantiate and connect widgets ...

    #
    # Import from Volume Node Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    #
    # input volume selector
    #
    self.inputSelector = slicer.qMRMLNodeComboBox()
    self.inputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputSelector.selectNodeUponCreation = True
    self.inputSelector.addEnabled = True
    self.inputSelector.removeEnabled = True
    self.inputSelector.renameEnabled = True
    self.inputSelector.noneEnabled = False
    self.inputSelector.showHidden = False
    self.inputSelector.showChildNodeTypes = False
    self.inputSelector.setMRMLScene( slicer.mrmlScene )
    self.inputSelector.setToolTip( "Pick the input to the algorithm." )

    self.inputModeLabel = qt.QLabel("Pick input mode:")
    self.loadFromVolume = qt.QRadioButton("Load from Volume")
    self.loadFromVolume.checked = True
    self.loadFromDicom = qt.QRadioButton("Load from DICOM")

    self.loadFromVolume.connect("clicked(bool)", self.onSelect)
    self.loadFromDicom.connect("clicked(bool)", self.onSelect)

    self.inputDicomSelector = ctk.ctkDirectoryButton()
    self.inputDicomSelector.caption = 'Input DICOMs'
    self.inputDicomSelector.connect("directoryChanged(QString)", self.onSelect)

    parametersFormLayout.addRow(self.inputModeLabel)
    parametersFormLayout.addRow(self.loadFromVolume, self.inputSelector)
    parametersFormLayout.addRow(self.loadFromDicom, self.inputDicomSelector)

    #
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.toolTip = "Run the algorithm."
    self.applyButton.enabled = False
    self.layout.addWidget(self.applyButton)

    # connections
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)

    # Add vertical spacer
    self.layout.addStretch(1)

    # Refresh Apply button state
    self.onSelect()


  def cleanup(self):
    pass

  def onSelect(self):
    if self.loadFromDicom.checked:
      for root, dirs, files in os.walk(self.inputDicomSelector.directory):
        for file in files:
          if file.lower().endswith('.dcm') or file.lower().endswith('.ima'):
            self.applyButton.enabled = True
            return

    elif self.loadFromVolume.checked and self.inputSelector.currentNode():
        self.applyButton.enabled = True

    else:
      self.applyButton.enabled = False

  def onApplyButton(self):
    logic = PhantomSegmenterLogic()

#
# PhantomSegmenterLogic
#


class PhantomSegmenterLogic(ScriptedLoadableModuleLogic):
  def __init__(self, dcmpath):
    self.dcmpath = dcmpath
    if not os.path.exist(dcmpath):
      raise IOError("Error: This path does not exist " + dcmpath)

  def run(self):
    # use an external file to convert a dicom volume to nrrd format
    # input from the system should be the directory containing all of the dicom volumes you wish to convert
    # Each volume should be in a separate folder
    converter = NrrdConverter()

    # convert each folder contents (full DICOM set) to a nrrd volume
    vols = converter.convertNrrd(self.dcmpath)

    logging.error(str(len(vols)))

    # for each volume we will perform the segmentation
    # much of this code is based off of https://subversion.assembla.com/svn/slicerrt/trunk/SlicerRt/samples/PythonScripts/SegmentGrowCut/SegmentGrowCutSimple.py
    for vol in vols:
      # setup the segmentation node for our DICOM volume - "masterVolumeNode"
      masterVolumeNode = vol
      segmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
      segmentationNode.SetName(vol.GetName())
      segmentationNode.CreateDefaultDisplayNodes()
      segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(masterVolumeNode)

      # create segment seed(s) for phantom volume
      volSeedPositions = ([50.5,24.9,32.4], [-50.5,24.9,32.4],[-50.5,24.9,-62.4]) # change these based on phantom location in image
      append = vtk.vtkAppendPolyData()
      for volSeedPosition in volSeedPositions:
        # create a seed as a sphere
        volSeed = vtk.vtkSphereSource()
        volSeed.SetCenter(volSeedPosition) 
        volSeed.SetRadius(10) # change this based on size of phantom or preference
        volSeed.Update()
        append.AddInputData(volSeed.GetOutput())

      append.Update()
      
      # add segmentation to the segmentationNode. "PhantomVolume" can be any string, and the following double array is colour.
      volSegID = segmentationNode.AddSegmentFromClosedSurfaceRepresentation(append.GetOutput(), "PhantomVolume", [1.0,0.0,0.0])

      # create segment seed(s) for the background noise
      bgSeedPositions = ([47,124,8],[-47,-80,8],[44,-90,32], [63,-83,6], [-68,106,-56]) # change these based on where the background/noise is in your image
      appendBg = vtk.vtkAppendPolyData()
      for bgSeedPos in bgSeedPositions:
        bgSeed = vtk.vtkSphereSource()
        bgSeed.SetCenter(bgSeedPos) 
        bgSeed.SetRadius(10)# change this based on background size
        bgSeed.Update()
        appendBg.AddInputData(bgSeed.GetOutput())

      appendBg.Update()
      
      # add background segmentation to the segmentationNode. Change the name or colour inputs based on preference.
      segmentationNode.AddSegmentFromClosedSurfaceRepresentation(appendBg.GetOutput(), "Background", [0.0,1.0,0.0])

      # create segmentation seed(s) for any additional feature that you wish to segment out
      featSeedPositions = ([32, -35, -11],[-28,-35,11],[-50,-35,11],[-15,42,18],[-15,30,18]) # change this based on the location of feature(s)
      appendFeat = vtk.vtkAppendPolyData()
      for featSeedPos in featSeedPositions:
        featSeed = vtk.vtkSphereSource()
        featSeed.SetCenter(featSeedPos) 
        featSeed.SetRadius(2) # small sphere for small features. Change depending on size of objects in your phantom
        featSeed.Update()
        appendFeat.AddInputData(featSeed.GetOutput())

      appendFeat.Update()
      
      # add feature segmentation seeds to the segmentationNode. Change the name or colour based on preference.
      segmentationNode.AddSegmentFromClosedSurfaceRepresentation(appendFeat.GetOutput(), "Feature", [0.0,0.0,1.0])

      # startup segmentEditor to grow seeds and any additional effects
      segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
      # segmentEditorWidget.show() # this is for debugging if you need to!
      segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
      segmentEditorNode = slicer.vtkMRMLSegmentEditorNode()
      slicer.mrmlScene.AddNode(segmentEditorNode)
      segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)
      segmentEditorWidget.setSegmentationNode(segmentationNode)
      segmentEditorWidget.setMasterVolumeNode(masterVolumeNode)

      # grow from seeds
      segmentEditorWidget.setActiveEffectByName("Grow from seeds")
      effect = segmentEditorWidget.activeEffect()
      effect.self().onPreview()
      
      # for troubleshooting / editing the seed growth, stop before the onApply() function
      effect.self().onApply()

      # grow the background further into the phantom volume segmentation
      # i needed this as my images had a noisy edge to the phantom volume, so it picked up to much noise as phantom volume
      segmentEditorWidget.setActiveEffectByName("Margin")
      mEffect = segmentEditorWidget.activeEffect()
      segmentEditorWidget.setCurrentSegmentID('Background') # change this based on your needs: does a segment not get all of your volume, or too much?
      mEffect.setParameter('MarginSizeMm', 8.0) # change 8.0 based on how well your segmentation performed. Change to negative if you need to shrink instead of grow.
      mEffect.self().onApply()

      # cleanup segment editor node
      slicer.mrmlScene.RemoveNode(segmentEditorNode)


class PhantomSegmenterLogicSample(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def hasImageData(self,volumeNode):
    """This is an example logic method that
    returns true if the passed in volume
    node has valid image data
    """
    if not volumeNode:
      logging.debug('hasImageData failed: no volume node')
      return False
    if volumeNode.GetImageData() is None:
      logging.debug('hasImageData failed: no image data in volume node')
      return False
    return True

  def isValidInputOutputData(self, inputVolumeNode, outputVolumeNode):
    """Validates if the output is not the same as input
    """
    if not inputVolumeNode:
      logging.debug('isValidInputOutputData failed: no input volume node defined')
      return False
    if not outputVolumeNode:
      logging.debug('isValidInputOutputData failed: no output volume node defined')
      return False
    if inputVolumeNode.GetID()==outputVolumeNode.GetID():
      logging.debug('isValidInputOutputData failed: input and output volume is the same. Create a new volume for output to avoid this error.')
      return False
    return True

  def takeScreenshot(self,name,description,type=-1):
    # show the message even if not taking a screen shot
    slicer.util.delayDisplay('Take screenshot: '+description+'.\nResult is available in the Annotations module.', 3000)

    lm = slicer.app.layoutManager()
    # switch on the type to get the requested window
    widget = 0
    if type == slicer.qMRMLScreenShotDialog.FullLayout:
      # full layout
      widget = lm.viewport()
    elif type == slicer.qMRMLScreenShotDialog.ThreeD:
      # just the 3D window
      widget = lm.threeDWidget(0).threeDView()
    elif type == slicer.qMRMLScreenShotDialog.Red:
      # red slice window
      widget = lm.sliceWidget("Red")
    elif type == slicer.qMRMLScreenShotDialog.Yellow:
      # yellow slice window
      widget = lm.sliceWidget("Yellow")
    elif type == slicer.qMRMLScreenShotDialog.Green:
      # green slice window
      widget = lm.sliceWidget("Green")
    else:
      # default to using the full window
      widget = slicer.util.mainWindow()
      # reset the type so that the node is set correctly
      type = slicer.qMRMLScreenShotDialog.FullLayout

    # grab and convert to vtk image data
    qpixMap = qt.QPixmap().grabWidget(widget)
    qimage = qpixMap.toImage()
    imageData = vtk.vtkImageData()
    slicer.qMRMLUtils().qImageToVtkImageData(qimage,imageData)

    annotationLogic = slicer.modules.annotations.logic()
    annotationLogic.CreateSnapShot(name, description, type, 1, imageData)

  def run(self, inputVolume, outputVolume, imageThreshold, enableScreenshots=0):
    """
    Run the actual algorithm
    """

    if not self.isValidInputOutputData(inputVolume, outputVolume):
      slicer.util.errorDisplay('Input volume is the same as output volume. Choose a different output volume.')
      return False

    logging.info('Processing started')

    # Compute the thresholded output volume using the Threshold Scalar Volume CLI module
    cliParams = {'InputVolume': inputVolume.GetID(), 'OutputVolume': outputVolume.GetID(), 'ThresholdValue' : imageThreshold, 'ThresholdType' : 'Above'}
    cliNode = slicer.cli.run(slicer.modules.thresholdscalarvolume, None, cliParams, wait_for_completion=True)

    # Capture screenshot
    if enableScreenshots:
      self.takeScreenshot('PhantomSegmenterTest-Start','MyScreenshot',-1)

    logging.info('Processing completed')

    return True


class PhantomSegmenterTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_PhantomSegmenter1()

  def test_PhantomSegmenter1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    import urllib
    downloads = (
        ('http://slicer.kitware.com/midas3/download?items=5767', 'FA.nrrd', slicer.util.loadVolume),
        )

    for url,name,loader in downloads:
      filePath = slicer.app.temporaryPath + '/' + name
      if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
        logging.info('Requesting download %s from %s...\n' % (name, url))
        urllib.urlretrieve(url, filePath)
      if loader:
        logging.info('Loading %s...' % (name,))
        loader(filePath)
    self.delayDisplay('Finished with download and loading')

    volumeNode = slicer.util.getNode(pattern="FA")
    logic = PhantomSegmenterLogic()
    self.assertIsNotNone( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')


class NrrdConverter(object):

  def convertNrrd(self, dcmpath):
    import os, shutil, dicom, sys, logging, subprocess, slicer
    dcmDict = {}
    volArray = []


    pathwalk = os.walk(dcmpath)
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
