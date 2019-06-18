from paraview.simple import *
import commands

vars = ['U', 'V']
Xs = [1, 16]
Ts = [0, 23]

layout1 = GetLayout()

for var in vars:
    for X in Xs:
        layout1, view1, view2 = compareT(var=var, X=X, play=False)
        SaveAnimation('movies/%s_X%d.avi' % (var, X) , layout1, SaveAllViews=1,
                      ImageResolution=[2240, 860],
                      FrameWindow=[0, 23])
        view1.CameraPosition = [-91.79570803687004, -4.511485753227961, 32.24697211000749]
        view1.CameraFocalPoint = [15.499600000000001, 15.499600000000001, 15.499600000000001]
        view1.CameraViewUp = [0.15086337019508542, 0.018286246269876367, 0.9883854798259323]
        view1.CameraParallelScale = 28.579531145209504
        view1.CameraParallelProjection = 1
        SaveAnimation('movies/%s_X%d_a.avi' % (var, X) , layout1, SaveAllViews=1,
                      ImageResolution=[2240, 860],
                      FrameWindow=[0, 23])        

for var in vars:
    for T in Ts:
        layout1, view1, view2 = compareX(var=var, step=T, play=False)
        SaveAnimation('movies/%s_T%d.avi' % (var, T) , layout1, SaveAllViews=1,
                      ImageResolution=[2240, 860],
                      FrameWindow=[0, 31])        
        view1.CameraPosition = [-91.79570803687004, -4.511485753227961, 32.24697211000749]
        view1.CameraFocalPoint = [15.499600000000001, 15.499600000000001, 15.499600000000001]
        view1.CameraViewUp = [0.15086337019508542, 0.018286246269876367, 0.9883854798259323]
        view1.CameraParallelScale = 28.579531145209504
        view1.CameraParallelProjection = 1
        SaveAnimation('movies/%s_T%d_a.avi' % (var, T) , layout1, SaveAllViews=1,
                      ImageResolution=[2240, 860],
                      FrameWindow=[0, 31])        
