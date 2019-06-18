from paraview.simple import *
# from paraview_compare import *
import commands

vars = ['U', 'V']
Xs = [1, 16]
Ts = [0, 23]

layout1 = GetLayout()

for var in vars:
    for X in Xs:
        print("var = %s, X = %d" % (var, X))
        compareT(var=var, X=X)
        commands.getstatusoutput("sleep 5")
        SaveAnimation('movies/%s_X%d.avi' % (var, X) , layout1, SaveAllViews=1,
                      ImageResolution=[2240, 860],
                      FrameWindow=[0, 23])
        commands.getstatusoutput("sleep 5")

for var in vars:
    for T in Ts:
        compareX(var=var, step=T)
        commands.getstatusoutput("sleep 5")        
        print("var = %s, X = %d" % (var, T))        
        SaveAnimation('movies/%s_T%d.avi' % (var, T) , layout1, SaveAllViews=1,
                      ImageResolution=[2240, 860],
                      FrameWindow=[0, 23])        
        commands.getstatusoutput("sleep 5")
