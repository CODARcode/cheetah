from paraview.simple import *
r1 = VisItPixieReader(FileName='CompressionOutput.h5')
Show()
Render()

import sys
#variable = input("What time step, variable to visualize? [ Step0/U/lossy ]\n")
#print(variable)
#sys.stdout.flush()

#r1.CellArrays = [ str(variable) ]
variable1 = 'Step23/U/original'
variable2 = 'Step23/U/lossy'
r1.CellArrays = [variable1, variable2]

layout1 = GetLayout()
#layout1.Initialize()
#print(dir(layout1))

# split cell


# set active view

renderView1 = GetActiveViewOrCreate('RenderView')
renderView1.Update()
# layout1.AssignView(0, renderView1)

layout1.SplitHorizontal(0, 0.5)

renderView2 = CreateView('RenderView')
layout1.AssignView(1, renderView2)


slice1 = Slice(Input=r1)
slice1.SliceType = 'Plane'
slice1.SliceOffsetValues = [0.0]
slice1.SliceType.Origin = [16.0, 16.0, 16.0]

slice1Display1 = Show(slice1, renderView1)
slice1Display1.Representation = 'Surface With Edges'

slice1Display2 = Show(slice1, renderView2)
slice1Display2.Representation = 'Surface With Edges'

ColorBy(slice1Display1, ('CELLS', variable1))
ColorBy(slice1Display2, ('CELLS', variable2))
#ColorBy(slice1Display, ('CELLS', 'Step0/U/lossy'))
slice1Display1.SetScalarBarVisibility(renderView1, True)
slice1Display2.SetScalarBarVisibility(renderView2, True)
slice1.SliceType.Origin = [15, 16.0, 16.0]
renderView1.Update()
renderView2.Update()
#Show()
#Render()

renderView1.ResetCamera()
renderView2.ResetCamera()

AddCameraLink(renderView1, renderView2, "view 1-2")

r1Display1 = Show(r1, renderView1)
r1Display2 = Show(r1, renderView2)

r1Display1.DataAxesGrid.GridAxesVisibility = 1
r1Display2.DataAxesGrid.GridAxesVisibility = 1

text1 = Text()
text2 = Text()

text1.Text = 'U, step=23, original'
text2.Text = 'U, step=23, lossy'

text1Display = Show(text1, renderView1)
text2Display = Show(text2, renderView2)

annotateTime1 = AnnotateTime()
annotateTime2 = AnnotateTime()

# show data in view
annotateTime1Display = Show(annotateTime1, renderView1)
annotateTime2Display = Show(annotateTime2, renderView2)

# Properties modified on annotateTime1Display
annotateTime1Display.WindowLocation = 'LowerCenter'
annotateTime2Display.WindowLocation = 'LowerCenter'

# Properties modified on annotateTime1
annotateTime1.Format = 'X: %f'
annotateTime2.Format = 'X: %f'


#### saving camera placements for all active views

# current camera placement for renderView1

"""
renderView1.CameraPosition = [-115.52747115602145, 16.000000953674316, 16.000000953674316]
renderView1.CameraFocalPoint = [15.091140508651733, 16.000000953674316, 16.000000953674316]
renderView1.CameraViewUp = [0.0, 0.0, 1.0]
renderView1.CameraParallelScale = 33.80658434366769
"""

renderView1.CameraPosition = [-124.0, 16.0, 16.0]
renderView1.CameraFocalPoint = [16.0, 16.0, 16.0]
renderView1.CameraViewUp = [0.0, 0.0, 1.0]
renderView1.CameraParallelProjection = 1
renderView1.CameraParallelScale = 1.0

renderView1.ResetCamera()

renderView2.CameraPosition = [-124.0, 16.0, 16.0]
renderView2.CameraFocalPoint = [16.0, 16.0, 16.0]
renderView2.CameraViewUp = [0.0, 0.0, 1.0]
renderView2.CameraParallelProjection = 1
renderView2.CameraParallelScale = 1.0

renderView2.ResetCamera()


# 

Show()
Render()

scene = GetAnimationScene()

t1 = GetAnimationTrack('Origin', index=0, proxy=slice1.SliceType)

keyf0=CompositeKeyFrame()
keyf0.Interpolation='Ramp'
keyf0.KeyTime=0
keyf0.KeyValues=[0]

keyf1=CompositeKeyFrame()
keyf1.KeyTime=1
keyf1.KeyValues=[31]

t1.KeyFrames=[keyf0, keyf1]
t1.EndTime=1
scene.EndTime=1
scene.NumberOfFrames=128

scene.Play()

