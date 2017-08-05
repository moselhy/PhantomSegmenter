cmake_minimum_required(VERSION 2.8.9)

project(PhantomSegmenter)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/moselhy/PhantomSegmenter")
set(EXTENSION_CATEGORY "Segmentation")
set(EXTENSION_CONTRIBUTORS "Colin McCurdy (Western University), Mohamed Moselhy (Western University)")
set(EXTENSION_DESCRIPTION "Automatically segment a Phantom using Grow from Seeds")
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/PhantomSegmenter.png")
set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/PhantomSegmenter/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a space separated string, a list or 'NA' if any

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(PhantomSegmenter)
add_subdirectory(SegmentEditorEffect)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
