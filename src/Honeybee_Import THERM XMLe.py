#
# Honeybee: A Plugin for Environmental Analysis (GPL) started by Mostapha Sadeghipour Roudsari
# 
# This file is part of Honeybee.
# 
# Copyright (c) 2013-2015, Chris Mackey <Chris@MackeyArchitecture.com.com> 
# Honeybee is free software; you can redistribute it and/or modify 
# it under the terms of the GNU General Public License as published 
# by the Free Software Foundation; either version 3 of the License, 
# or (at your option) any later version. 
# 
# Honeybee is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the 
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Honeybee; If not, see <http://www.gnu.org/licenses/>.
# 
# @license GPL-3.0+ <http://spdx.org/licenses/GPL-3.0+>


"""
Use this component to read the content of a THERM XML file into Grasshopper.  The component will extract both THERM polygons and boundary conditions along with all of their properties.
-
Provided by Honeybee 0.0.57

    Args:
        _thermXMLFile: A filepath to a therm XML file on your machine.
    Returns:
        readMe!:...
        thermPolygons: The therm polygons within the therm XML file.
        thermBCs: The therm boundary conditions within the therm XML file.
"""


import Rhino as rc
import scriptcontext as sc
import Grasshopper.Kernel as gh
import os

ghenv.Component.Name = 'Honeybee_Import THERM XMLe'
ghenv.Component.NickName = 'importTHERM'
ghenv.Component.Message = 'VER 0.0.57\nJAN_13_2016'
ghenv.Component.Category = "Honeybee"
ghenv.Component.SubCategory = "12 | WIP"
#compatibleHBVersion = VER 0.0.56\nJAN_12_2015
#compatibleLBVersion = VER 0.0.59\nFEB_01_2015
try: ghenv.Component.AdditionalHelpFromDocStrings = "4"
except: pass


w = gh.GH_RuntimeMessageLevel.Warning
e = gh.GH_RuntimeMessageLevel.Error


def main(thermXMLFile):
    #Call the relevant classes
    lb_preparation = sc.sticky["ladybug_Preparation"]()
    
    #Make a series of lists to be filled
    thermPolygons = []
    thermBCs = []
    
    #Check if the result file exists.
    if not os.path.isfile(thermXMLFile):
        warning = "Cannot find the result file. Check the location of the file on your machine. \n If it is not there, make sure that you have opened THERM and run your .thmx file before using this component. \n Also, before you run the file in THERM, make sure that you go to Options > Preferences > Simulation and check 'Save Conrad results file (.O).'"
        print warning
        ghenv.Component.AddRuntimeMessage(w, warning)
        return -1
    
    #Define some parameters to be changes while the file is open.
    polygonTrigger = False
    newPolygonTrigger = False
    polygonVertices = []
    planeReorientation = None
    rhinoOrig = None
    conversionFactor = lb_preparation.checkUnits()
    conversionFactor = 1/(conversionFactor*1000)
    unitsScale = rc.Geometry.Transform.Scale(rc.Geometry.Plane.WorldXY, conversionFactor, conversionFactor, conversionFactor)
    
    #Open the file and begin extracting the relevant bits of information.
    thermFi = open(thermXMLFile, 'r')
    for lineCount, line in enumerate(thermFi):
        if '<Polygons>' in line: polygonTrigger = True
        elif '</Polygons>' in line: polygonTrigger = False
        #Try to extract the transformations from the file header.
        elif '<Notes>' in line and '</Notes>' in line:
            if 'RhinoUnits-' in line and 'RhinoOrigin-' in line and 'RhinoXAxis-' in line:
                origRhinoUnits = line.split(',')[0].split('RhinoUnits-')[-1]
                origRhinoOrigin = line.split('),')[0].split('RhinoOrigin-(')[-1].split(',')
                origRhinoXaxis = line.split('),')[1].split('RhinoXAxis-(')[-1].split(',')
                origRhinoYaxis = line.split('),')[2].split('RhinoYAxis-(')[-1].split(',')
                origRhinoZaxis = line.split(')</Notes>')[0].split('RhinoZAxis-(')[-1].split(',')
                
                rhinoOrig = rc.Geometry.Point3d(float(origRhinoOrigin[0]), float(origRhinoOrigin[1]), float(origRhinoOrigin[2]))
                thermPlane = rc.Geometry.Plane(rhinoOrig, rc.Geometry.Plane.WorldXY.XAxis, rc.Geometry.Plane.WorldXY.YAxis)
                basePlane = rc.Geometry.Plane(rhinoOrig, rc.Geometry.Vector3d(float(origRhinoXaxis[0]), float(origRhinoXaxis[1]), float(origRhinoXaxis[2])), rc.Geometry.Vector3d(float(origRhinoYaxis[0]), float(origRhinoYaxis[1]), float(origRhinoYaxis[2])))
                basePlaneNormal = rc.Geometry.Vector3d(float(origRhinoZaxis[0]), float(origRhinoZaxis[1]), float(origRhinoZaxis[2]))
                planeReorientation = rc.Geometry.Transform.ChangeBasis(basePlane, thermPlane)
            else:
                warning = "Cannot find any transformation data in the header of the THERM file. \n Result geometry will be imported to the Rhino model origin."
                print warning
        
        #Try to extract the polygons from the file header.
        if polygonTrigger == True:
            if '<Polygon ID' in line:
                newPolygonTrigger = True
                polygonVertices = []
            elif '</Polygon>' in line:
                newPolygonTrigger = False
                #Make the vertices into a brep and append it to the list.
                polygonLineGeo = rc.Geometry.PolylineCurve(polygonVertices)
                closingLine = rc.Geometry.PolylineCurve([polygonLineGeo.PointAtStart, polygonLineGeo.PointAtEnd])
                allPolygonLine = rc.Geometry.PolylineCurve.JoinCurves([polygonLineGeo, closingLine], sc.doc.ModelAbsoluteTolerance)[0]
                finalPolygonGeo = rc.Geometry.Brep.CreatePlanarBreps(allPolygonLine)[0]
                thermPolygons.append(finalPolygonGeo)
            elif '<Point index=' in line:
                xCoord = float(line.split('x="')[-1].split('"')[0])
                yCoord = float(line.split('y="')[-1].split('"')[0])
                polygonVertex = rc.Geometry.Point3d(xCoord, yCoord, 0)
                polygonVertices.append(polygonVertex)
    thermFi.close()
    
    #Transform the geometry to be at the correct scale in the Rhino scene.
    for geo in thermPolygons:
        geo.Transform(unitsScale)
    if planeReorientation != None:
        for geo in thermPolygons:
            geo.Transform(planeReorientation)
        joinedPolygons = rc.Geometry.Brep.JoinBreps(thermPolygons, sc.doc.ModelAbsoluteTolerance)[0]
        thermBB = joinedPolygons.GetBoundingBox(rc.Geometry.Plane.WorldXY)
        thermOrigin = rc.Geometry.BoundingBox.Corner(thermBB, True, True, True)
        vecDiff = rc.Geometry.Point3d.Subtract(rhinoOrig, thermOrigin)
        planeTransl = rc.Geometry.Transform.Translation(vecDiff.X, vecDiff.Y, vecDiff.Z)
        for geo in thermPolygons:
            geo.Transform(planeTransl)
    
    return thermPolygons, thermBCs


#If Honeybee or Ladybug is not flying or is an older version, give a warning.
initCheck = True

#Ladybug check.
if not sc.sticky.has_key('ladybug_release') == True:
    initCheck = False
    print "You should first let Ladybug fly..."
    ghenv.Component.AddRuntimeMessage(w, "You should first let Ladybug fly...")
else:
    try:
        if not sc.sticky['ladybug_release'].isCompatible(ghenv.Component): initCheck = False
    except:
        initCheck = False
        warning = "You need a newer version of Ladybug to use this compoent." + \
        "Use updateLadybug component to update userObjects.\n" + \
        "If you have already updated userObjects drag Ladybug_Ladybug component " + \
        "into canvas and try again."
        ghenv.Component.AddRuntimeMessage(w, warning)
#Honeybee check.
if not sc.sticky.has_key('honeybee_release') == True:
    initCheck = False
    print "You should first let Honeybee fly..."
    ghenv.Component.AddRuntimeMessage(w, "You should first let Honeybee fly...")
else:
    try:
        if not sc.sticky['honeybee_release'].isCompatible(ghenv.Component): initCheck = False
        if sc.sticky['honeybee_release'].isInputMissing(ghenv.Component): initCheck = False
    except:
        initCheck = False
        warning = "You need a newer version of Honeybee to use this compoent." + \
        "Use updateHoneybee component to update userObjects.\n" + \
        "If you have already updated userObjects drag Honeybee_Honeybee component " + \
        "into canvas and try again."
        ghenv.Component.AddRuntimeMessage(w, warning)


#If the intital check is good, run the component.
if initCheck and _thermXMLFile:
    result = main(_thermXMLFile)
    if result != -1:
        thermPolygons, thermBCs = result