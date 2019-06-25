# trace generated using paraview version 5.6.0
#
# To ensure correct image size when batch processing, please search 
# for and uncomment the line `# renderView*.ViewSize = [*,*]`

#### import the simple module from the paraview
from paraview.simple import *
#### disable automatic camera reset on 'Show'
paraview.simple._DisableFirstRenderCameraReset()

# find view
renderView1 = FindViewOrCreate('RenderView1', viewtype='RenderView')
# uncomment following to set a specific view size
# renderView1.ViewSize = [686, 574]

# set active view
SetActiveView(renderView1)

#### saving camera placements for all active views

# current camera placement for renderView1
renderView1.CameraPosition = [-91.79570803687004, -4.511485753227961, 32.24697211000749]
renderView1.CameraFocalPoint = [15.499600000000001, 15.499600000000001, 15.499600000000001]
renderView1.CameraViewUp = [0.15086337019508542, 0.018286246269876367, 0.9883854798259323]
renderView1.CameraParallelScale = 28.579531145209504
renderView1.CameraParallelProjection = 1

#### uncomment the following to render all views
# RenderAllViews()
# alternatively, if you want to write images, you can use SaveScreenshot(...).