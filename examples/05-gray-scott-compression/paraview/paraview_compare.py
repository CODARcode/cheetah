from paraview.simple import *

def init_camera_view(view):
    view.CameraPosition = [-124.0, 16.0, 16.0]
    view.CameraFocalPoint = [16.0, 16.0, 16.0]
    view.CameraViewUp = [0.0, 0.0, 1.0]
    view.CameraParallelProjection = 1
    view.CameraParallelScale = 1.0
    

def compareX(var='U', step=23, fn='CompressionOutput.h5', nx = 32, play=True, FTK=False):
    ResetSession()
    r1 = VisItPixieReader(FileName=fn)

    variable1 = 'Step%d/%s/original' % (step, var)
    variable2 = 'Step%d/%s/lossy' % (step, var)

    r1.CellArrays = [variable1, variable2]
    r1.Meshes = ['mesh_%dx%dx%d' % (nx, nx, nx) ]

    layout1 = GetLayout()

    renderView1 = GetActiveViewOrCreate('RenderView')
    renderView1.Update()

    layout1.SplitHorizontal(0, 0.5)

    renderView2 = CreateView('RenderView')
    layout1.AssignView(1, renderView2)
    renderView2.Update()

    slice1 = Slice(Input=r1)
    slice1.SliceType = 'Plane'
    slice1.SliceOffsetValues = [0.0]
    slice1.SliceType.Origin = [1.0, nx//2, nx//2]
    
    slice1Display1 = Show(slice1, renderView1)
    slice1Display1.Representation = 'Surface With Edges'
    
    slice1Display2 = Show(slice1, renderView2)
    slice1Display2.Representation = 'Surface With Edges'
    
    ColorBy(slice1Display1, ('CELLS', variable1))
    ColorBy(slice1Display2, ('CELLS', variable2))
    slice1Display1.SetScalarBarVisibility(renderView1, True)
    slice1Display2.SetScalarBarVisibility(renderView2, True)
    slice1.SliceType.Origin = [1.0, nx//2, nx//2]
    renderView1.Update()
    renderView2.Update()

    if(FTK):
        variable1f = 'Step%d/%s_features/original' % (step, var)
        variable2f = 'Step%d/%s_features/lossy' % (step, var)
            
        csv1 = CSVReader(FileName='FEATURES/%s/d.csv' % variable1f)
        csv1.HaveHeaders = 0

        csv2 = CSVReader(FileName='FEATURES/%s/d.csv' % variable2f)
        csv2.HaveHeaders = 0    

        tableToPoints1 = TableToPoints(Input=csv1)
        tableToPoints1.XColumn = 'Field 0'
        tableToPoints1.YColumn = 'Field 1'
        tableToPoints1.ZColumn = 'Field 2'
    
        tableToPoints2 = TableToPoints(Input=csv2)
        tableToPoints2.XColumn = 'Field 0'
        tableToPoints2.YColumn = 'Field 1'
        tableToPoints2.ZColumn = 'Field 2'
    
        tableToPointsDisplay1 = Show(tableToPoints1, renderView1)
        tableToPointsDisplay1.Representation = 'Point Gaussian'
        tableToPointsDisplay1.ColorArrayName = ['POINTS', 'Field 3']
        tableToPointsDisplay1.GaussianRadius = 0.4
        tableToPointsDisplay1.SetScalarBarVisibility(renderView1, True)
        ColorBy(tableToPointsDisplay1, ('POINTS', 'Field 3'))

        tableToPointsDisplay2 = Show(tableToPoints2, renderView2)
        tableToPointsDisplay2.Representation = 'Point Gaussian'
        tableToPointsDisplay2.ColorArrayName = ['POINTS', 'Field 3']
        tableToPointsDisplay2.GaussianRadius = 0.4    
        tableToPointsDisplay2.SetScalarBarVisibility(renderView2, True)    
        ColorBy(tableToPointsDisplay2, ('POINTS', 'Field 3'))

        UpdatePipeline(proxy=csv1)
        UpdatePipeline(proxy=csv2)
        
        renderView1.Update()
        renderView2.Update()
    
    renderView1.ResetCamera()
    renderView2.ResetCamera()

    Show()
    Render()
    
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
    s.SliceType.Origin = [x, NX2, NX2]
    text3.Text = "X = %d" % x
def end_cue(self): pass
""".replace('NX2', str(nx//2))
    scene.Cues.append(pycue)
    scene.EndTime = nx - 1
    scene.NumberOfFrames = nx
    if(play):
        scene.Play()
    return layout1, renderView1, renderView2



def compareT(var='U', X=16, fn='CompressionOutput.h5', steps=24, play=True, nx = 32, FTK=False):
    ResetSession()
    r1 = VisItPixieReader(FileName=fn)    
    r1.CellArrays = ['Step%d/%s/original' % (i, var) for i in range(steps)] + \
                    ['Step%d/%s/lossy'    % (i, var) for i in range(steps)]
    r1.Meshes = ['mesh_%dx%dx%d'%(nx,nx,nx)]    
    layout1 = GetLayout()

    renderView1 = GetActiveViewOrCreate('RenderView')
    renderView1.Update()

    layout1.SplitHorizontal(0, 0.5)

    renderView2 = CreateView('RenderView')
    layout1.AssignView(1, renderView2)

    slice1 = Slice(Input=r1)
    slice1.SliceType = 'Plane'
    slice1.SliceOffsetValues = [0.0]
    slice1.SliceType.Origin = [X, nx//2, nx//2]
    
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

    if(FTK):
        variable1f = 'Step%d/%s_features/original' % (0, var)
        variable2f = 'Step%d/%s_features/lossy' % (0, var)

        csv1 = CSVReader(FileName='FEATURES/%s/d.csv' % variable1f)
        csv1.HaveHeaders = 0
    
        csv2 = CSVReader(FileName='FEATURES/%s/d.csv' % variable2f)
        csv2.HaveHeaders = 0    
    
        tableToPoints1 = TableToPoints(Input=csv1)
        tableToPoints1.XColumn = 'Field 0'
        tableToPoints1.YColumn = 'Field 1'
        tableToPoints1.ZColumn = 'Field 2'
    
        tableToPoints2 = TableToPoints(Input=csv2)
        tableToPoints2.XColumn = 'Field 0'
        tableToPoints2.YColumn = 'Field 1'
        tableToPoints2.ZColumn = 'Field 2'
    
        tableToPointsDisplay1 = Show(tableToPoints1, renderView1)
        tableToPointsDisplay1.Representation = 'Point Gaussian'
        tableToPointsDisplay1.ColorArrayName = ['POINTS', 'Field 3']
        tableToPointsDisplay1.GaussianRadius = 0.4
        tableToPointsDisplay1.SetScalarBarVisibility(renderView1, True)
        ColorBy(tableToPointsDisplay1, ('POINTS', 'Field 3'))
    
        tableToPointsDisplay2 = Show(tableToPoints2, renderView2)
        tableToPointsDisplay2.Representation = 'Point Gaussian'
        tableToPointsDisplay2.ColorArrayName = ['POINTS', 'Field 3']
        tableToPointsDisplay2.GaussianRadius = 0.4    
        tableToPointsDisplay2.SetScalarBarVisibility(renderView2, True)    
        ColorBy(tableToPointsDisplay2, ('POINTS', 'Field 3'))
        
        renderView1.Update()
        renderView2.Update()
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

    if(FTK):
        variable1f = 'Step%d/VAR_features/original' % (t)
        variable2f = 'Step%d/VAR_features/lossy' % (t)
        csv1 = FindSource("CSVReader1")
        csv2 = FindSource("CSVReader2")
        csv1.FileName = 'FEATURES/%s/d.csv' % variable1f
        csv2.FileName = 'FEATURES/%s/d.csv' % variable2f
        views[0].Update()
        views[1].Update()
        Show()
        Render()
def end_cue(self): pass
""".replace("VAR", var).replace("FTK", str(FTK))
    scene.Cues.append(pycue)
    scene.EndTime = steps - 1
    scene.NumberOfFrames = steps
    if(play):
        scene.Play()
    return layout1, renderView1, renderView2

