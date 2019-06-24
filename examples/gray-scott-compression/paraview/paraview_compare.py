from paraview.simple import *

def init_camera_view(view):
    view.CameraPosition = [-124.0, 16.0, 16.0]
    view.CameraFocalPoint = [16.0, 16.0, 16.0]
    view.CameraViewUp = [0.0, 0.0, 1.0]
    view.CameraParallelProjection = 1
    view.CameraParallelScale = 1.0
    
def compareX(var='U', step=23, fn='CompressionOutput.h5', nx = 32, play=True):
    ResetSession()
    r1 = VisItPixieReader(FileName=fn)

    variable1 = 'Step%d/%s/original' % (step, var)
    variable2 = 'Step%d/%s/lossy' % (step, var)
    r1.CellArrays = [variable1, variable2]

    layout1 = GetLayout()

    renderView1 = GetActiveViewOrCreate('RenderView')
    renderView1.Update()

    layout1.SplitHorizontal(0, 0.5)

    renderView2 = CreateView('RenderView')
    layout1.AssignView(1, renderView2)

    slice1 = Slice(Input=r1)
    slice1.SliceType = 'Plane'
    slice1.SliceOffsetValues = [0.0]
    slice1.SliceType.Origin = [1.0, 16.0, 16.0]
    
    slice1Display1 = Show(slice1, renderView1)
    slice1Display1.Representation = 'Surface With Edges'
    
    slice1Display2 = Show(slice1, renderView2)
    slice1Display2.Representation = 'Surface With Edges'
    
    ColorBy(slice1Display1, ('CELLS', variable1))
    ColorBy(slice1Display2, ('CELLS', variable2))
    slice1Display1.SetScalarBarVisibility(renderView1, True)
    slice1Display2.SetScalarBarVisibility(renderView2, True)
    slice1.SliceType.Origin = [1.0, 16.0, 16.0]
    renderView1.Update()
    renderView2.Update()

    renderView1.ResetCamera()
    renderView2.ResetCamera()

    AddCameraLink(renderView1, renderView2, "view 1-2")

    r1Display1 = Show(r1, renderView1)
    r1Display2 = Show(r1, renderView2)

    r1Display1.DataAxesGrid.GridAxesVisibility = 1
    r1Display2.DataAxesGrid.GridAxesVisibility = 1

    text1 = Text()
    text2 = Text()

    text1.Text = '%s, original, time = %d' % (var, step)
    text2.Text = '%s, lossy, time = %d' % (var, step)

    text1Display = Show(text1, renderView1)
    text2Display = Show(text2, renderView2)

    text3 = Text()
    text3.Text = "X = 1"
    text3Display1 = Show(text3, renderView1)
    text3Display2 = Show(text3, renderView2)
    text3Display1.WindowLocation = 'LowerCenter'
    text3Display2.WindowLocation = 'LowerCenter'    
    
    init_camera_view(renderView1)
    renderView1.ResetCamera()
    init_camera_view(renderView2)
    renderView2.ResetCamera()

    Show()
    Render()

    scene = GetAnimationScene()

    pycue = PythonAnimationCue()
    pycue.Script= """
from paraview.simple import *
def start_cue(self): pass
def tick(self):
    s = FindSource("Slice1")
    text3 = FindSource("Text3")
    t = int(self.GetClockTime())
    x = t + 1
    s.SliceType.Origin = [x, 16.0, 16.0]
    text3.Text = "X = %d" % x
def end_cue(self): pass
"""
    scene.Cues.append(pycue)
    scene.EndTime = nx - 1
    scene.NumberOfFrames = nx
    if(play):
        scene.Play()
    return layout1, renderView1, renderView2


def compareT(var='U', X=16, fn='CompressionOutput.h5', steps=24, play=True):
    ResetSession()
    r1 = VisItPixieReader(FileName=fn)    
    r1.CellArrays = ['Step%d/%s/original' % (i, var) for i in range(steps)] + \
                    ['Step%d/%s/lossy'    % (i, var) for i in range(steps)]
    
    layout1 = GetLayout()

    renderView1 = GetActiveViewOrCreate('RenderView')
    renderView1.Update()

    layout1.SplitHorizontal(0, 0.5)

    renderView2 = CreateView('RenderView')
    layout1.AssignView(1, renderView2)

    slice1 = Slice(Input=r1)
    slice1.SliceType = 'Plane'
    slice1.SliceOffsetValues = [0.0]
    slice1.SliceType.Origin = [X, 16.0, 16.0]
    
    slice1Display1 = Show(slice1, renderView1)
    slice1Display1.Representation = 'Surface With Edges'
    
    slice1Display2 = Show(slice1, renderView2)
    slice1Display2.Representation = 'Surface With Edges'
    
    ColorBy(slice1Display1, ('CELLS', r1.CellArrays[0]))
    ColorBy(slice1Display2, ('CELLS', r1.CellArrays[24]))
    slice1Display1.SetScalarBarVisibility(renderView1, True)
    slice1Display2.SetScalarBarVisibility(renderView2, True)
    renderView1.Update()
    renderView2.Update()

    renderView1.ResetCamera()
    renderView2.ResetCamera()

    AddCameraLink(renderView1, renderView2, "view 1-2")

    r1Display1 = Show(r1, renderView1)
    r1Display2 = Show(r1, renderView2)

    r1Display1.DataAxesGrid.GridAxesVisibility = 1
    r1Display2.DataAxesGrid.GridAxesVisibility = 1

    text1 = Text()
    text2 = Text()

    text1.Text = '%s, original, X=%s' % (var, X)
    text2.Text = '%s, lossy, X=%d' % (var, X)

    text1Display = Show(text1, renderView1)
    text2Display = Show(text2, renderView2)

    annotateTime1 = AnnotateTime()
    annotateTime2 = AnnotateTime()

    annotateTime1Display = Show(annotateTime1, renderView1)
    annotateTime2Display = Show(annotateTime2, renderView2)

    annotateTime1Display.WindowLocation = 'LowerCenter'
    annotateTime2Display.WindowLocation = 'LowerCenter'

    annotateTime1.Format = 'time = %.1f'
    annotateTime2.Format = 'time = %.1f'

    init_camera_view(renderView1)
    renderView1.ResetCamera()
    init_camera_view(renderView2)
    renderView2.ResetCamera()

    Show()
    Render()

    scene = GetAnimationScene()

    pycue = PythonAnimationCue()
    pycue.Script= """
from paraview.simple import *
def start_cue(self): pass
def tick(self):
    r = FindSource("VisItPixieReader1")
    s = FindSource("Slice1")
    views = GetViews()
    sd1 = Show(s, views[0])
    sd2 = Show(s, views[1])
    t = int(self.GetClockTime())
    ColorBy(sd1, ('CELLS', 'Step%d/VAR/original' % t ))
    ColorBy(sd2, ('CELLS', 'Step%d/VAR/lossy'    % t ))
def end_cue(self): pass
""".replace("VAR", var)
    scene.Cues.append(pycue)
    scene.EndTime = steps - 1
    scene.NumberOfFrames = steps
    if(play):
        scene.Play()
    return layout1, renderView1, renderView2



