from math import radians, degrees
from mathutils import Matrix, Vector, Quaternion, Euler
from math import pi
from time import time
import bpy
import bmesh
import bpy_extras.object_utils
from . import utils_math
from .utils_p3dxml import *
from .utils_bpy import reminder, pcoll
add_object = bpy_extras.object_utils.object_data_add

locator_types = [
    ('EVENT', 'Type 0 (Event Locator)',
     'Used to trigger various types of events in the game', 'DECORATE_KEYFRAME', 0),
    ('SCRIPT', 'Type 1 (Script Locator)', 'TODO', 'WORDWRAP_ON', 1),
    ('LOCATOR', 'Type 2 (Locator)',
     "Used to position Wasp Cameras, gag models and gag triggers. This type of locator has no effect unless it's referenced by a script.\nGag triggers are different from most Trigger Volumes in that they're created dynamically at runtime instead of being in a P3D file", pcoll['WASP'].icon_id, 2),
    ('CAR', 'Type 3 (Car Start Locator)',
     'Used to position cars, characters and other miscellaneous things in scripts and missions', 'AUTO', 3),
    ('SPLINE', 'Type 4 (Spline Locator)', 'TODO', 'IPO_BEZIER', 4),
    ('ZONE', 'Type 5 (Zone Event Locator)',
     'Executes the DynaLoad data string specified inside its chunk when the player enters one if its Trigger Volumes', 'UGLYPACKAGE', 5),
    ('OCCLUSION', 'Type 6 (Occlusion Locator)', 'TODO', 'SELECT_SUBTRACT', 6),
    ('INTERIOR', 'Type 7 (Interior Entrance Locator)', 'TODO', 'HOME', 7),
    ('DIRECTION', 'Type 8 (Directional Locator)',
     'Used to position the player when they enter an interior', 'CON_ROTLIKE', 8),
    ('ACTION', 'Type 9 (Action Event Locator)', 'Used to create various "action buttons" in the world that the player triggers either by pressing action on them or by entering the trigger. These are used for collectibles such as wrenches and collector cards as well as skin shops. They can also be used to control animated world objects in various ways', 'SEQUENCE', 9),
    ('CAM', 'Type 12 (Static Cam Locator)', 'TODO', 'CAMERA_DATA', 12),
    ('PED', 'Type 13 (Ped Group Locator) ',
     'Changes the active Ped Group to the one specified inside it when the player enters its Trigger Volumes', pcoll['PATH_PED'].icon_id, 13),
    ('COIN', 'Type 14 (Coin Locator)',
     'When this type of locator is loaded, the game will place a coin at its position', pcoll['COIN'].icon_id, 14)
]
# Locator_Types_Dictionary
LTD = {x[4]: x[0] for x in locator_types}
LTD_rev = {x[0]: x[4] for x in locator_types}
event_description = 'Event 2 - Mission Waypoint\nEvent 4 - Death Trigger\nEvent 5 - Interior Exit\nEvent 6 - Airvent\nEvent 7 - Triggers the event "L2_light_city_day" in "ambience.rms".\nEvent 23 - Triggers the event "L2_railyard_day" in "ambience.rms".\nEvent 46 - Triggers the event "L1_Burns_Mansion_Interior" in "ambience.rms".\nEvent 48 - Jump Zone\nEvent 61 - Triggers the event "Social_Club" in the current music RMS. Pushes "pause_region" to the top of the stack in "ambience.rms". It\'s unclear which music event is used to do this.\nEvent 65 - Modifies the lighting using the color in the parameter field'
action_types = [
    ('AutomaticDoor', 'Automatic Door', reminder,
     pcoll['AutomaticDoor'].icon_id, 1),
    ('AutoPlayAnim', 'Autoplay Animation', reminder, 'PLAY', 2),
    ('CollectorCard', 'Collector Card', reminder,
        pcoll['CollectorCard'].icon_id, 5),
    ('DestroyObject', 'Destroy Object', reminder,
        pcoll['PowerCoupling'].icon_id, 6),
    ('Doorbell', 'Doorbell', reminder, pcoll['Doorbell'].icon_id, 7),
    ('Nitro', 'Nitro', reminder, pcoll['Nitro'].icon_id, 10),
    ('PlayAnim', 'Play Animation', reminder, 'PLAY', 12),
    ('PlayOnce', 'Play Once', reminder, 'FF', 14),
    ('PurchaseSkin', 'Purchase Skin', reminder,
        pcoll['PurchaseSkin'].icon_id, 18),
    ('SummonVehiclePhone', 'Summon Vehicle Phone',
        reminder, pcoll['SummonVehiclePhone'].icon_id, 19),
    ('Teleport', 'Teleport', reminder, pcoll['Teleport'].icon_id, 24),
    ('ToggleOnOff', 'Toggle OnOff', reminder, 'PROP_OFF', 25),
    ('Wrench', 'Wrench', reminder, pcoll['Wrench'].icon_id, 28)
]
AT = {x[4]: x[0] for x in action_types}
AT_rev = {x[0]: x[4] for x in action_types}
#TODO add support for Custom trigger actions? https://docs.donutteam.com/docs/lucasmodlauncher/hacks/custom-trigger-actions

def locator_can_have_volume(object):
    return object.locator_prop.loctype not in [LTD[2], LTD[3], LTD[8], LTD[14]]


def volume_create(name="Volume", parent=None, is_rect=True, location=Vector(), rotation=Euler(), scale=Vector((1, 1, 1))):
    vol_obj = bpy.data.objects.new(name, None)
    if is_rect:
        vol_obj.empty_display_type = 'CUBE'
    else:
        vol_obj.empty_display_type = 'SPHERE'
    parent.users_collection[0].objects.link(vol_obj)
    vol_obj.scale = scale
    vol_obj.rotation_euler = rotation
    vol_obj.parent = parent
    if parent:
        vol_obj.location = location - parent.location
    return vol_obj

def locator_matrix_create(name="Locator Matrix", parent=None, location=Vector(), rotation=Euler()):
    lm_obj = bpy.data.objects.new(name, None)
    parent.users_collection[0].objects.link(lm_obj)
    lm_obj.location = location - parent.location
    lm_obj.rotation_euler = rotation
    lm_obj.parent = parent
    lm_obj.empty_display_type="ARROWS"
    parent.locator_prop.loc_matrix = lm_obj
    parent.locator_prop.use_custom_loc_matrix = True
    return lm_obj

def locator_create(name="Locator", location=Vector(), loctype='EVENT', volume_kwargs={}):
    if 'Locators' not in bpy.context.scene.collection.children:
        locator_collection = bpy.data.collections.new('Locators')
        bpy.context.scene.collection.children.link(locator_collection)
    else:
        locator_collection = bpy.data.collections['Locators']
    loc_obj = bpy.data.objects.new(name, None)
    loc_obj.empty_display_type = 'PLAIN_AXES'
    loc_obj.location = location
    loc_obj.locator_prop.is_locator = True
    loc_obj.locator_prop.loctype = loctype
    if volume_kwargs:
        volume_create(**volume_kwargs, parent=loc_obj)
    locator_collection.objects.link(loc_obj)
    return loc_obj


def locator_spline_create(points : list, name="Spline", parent=None, cam_name=''):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    spline = curve.splines.new('NURBS')
    spline.use_endpoint_u = True
    spline.points.add(len(points)-1)
    origin = points[0].copy()
    for i,p in enumerate(points):
        spline.points[i].co = (Vector(points[i])-Vector(origin)).to_4d()
    spline.order_u = 3


    curve_obj = bpy.data.objects.new(name, curve)
    parent.users_collection[0].objects.link(curve_obj)
    curve_obj.parent = parent
    curve_obj.location = -parent.location.copy() + origin.copy()
    parent.locator_prop.loc_spline = curve_obj
    parent.locator_prop.loc_spline_cam_name = cam_name
    return curve_obj

def GetRailCamProps(locator_obj : bpy.types.Object) -> dict:
    DataDict = {}
    DataDict['Name']       = locator_obj.locator_prop.loc_spline_rail_cam_name
    DataDict['Behaviour']       = locator_obj.locator_prop.loc_spline_behaviour
    DataDict['MinRadius']       = locator_obj.locator_prop.loc_spline_min_radius
    DataDict['MaxRadius']       = locator_obj.locator_prop.loc_spline_max_radius
    DataDict['TrackRail']       = locator_obj.locator_prop.loc_spline_track_rail
    DataDict['TrackDist']       = locator_obj.locator_prop.loc_spline_track_dist
    DataDict['ReverseSense']    = locator_obj.locator_prop.loc_spline_reverse_sense
    DataDict['FOV']             = locator_obj.locator_prop.loc_spline_FOV
    DataDict['TargetOffset']    = locator_obj.locator_prop.loc_spline_target_offset
    DataDict['AxisPlay']        = locator_obj.locator_prop.loc_spline_axis_play
    DataDict['PositionLag']     = locator_obj.locator_prop.loc_spline_position_lag
    DataDict['TargetLag']       = locator_obj.locator_prop.loc_spline_target_lag
    return DataDict

def SetRailCamProps(locator_obj : bpy.types.Object, DataDict : dict):
    locator_obj.locator_prop.loc_spline_rail_cam_name   = DataDict['Name']     
    locator_obj.locator_prop.loc_spline_behaviour       = DataDict['Behaviour']       
    locator_obj.locator_prop.loc_spline_min_radius      = DataDict['MinRadius']       
    locator_obj.locator_prop.loc_spline_max_radius      = DataDict['MaxRadius']       
    locator_obj.locator_prop.loc_spline_track_rail      = DataDict['TrackRail']       
    locator_obj.locator_prop.loc_spline_track_dist      = DataDict['TrackDist']       
    locator_obj.locator_prop.loc_spline_reverse_sense   = DataDict['ReverseSense']    
    locator_obj.locator_prop.loc_spline_FOV             = DataDict['FOV']             
    locator_obj.locator_prop.loc_spline_target_offset   = DataDict['TargetOffset']    
    locator_obj.locator_prop.loc_spline_axis_play       = DataDict['AxisPlay']        
    locator_obj.locator_prop.loc_spline_position_lag    = DataDict['PositionLag']     
    locator_obj.locator_prop.loc_spline_target_lag      = DataDict['TargetLag'] 

def locator_create_cam(target_pos=Vector(), follow_player=False, FOV=70, cam_name="Camera", target_name="Target", parent=None):
    cam_data = bpy.data.cameras.new(cam_name)
    cam_data.lens_unit = 'FOV'
    cam_data.angle = radians(FOV)

    cam_obj = bpy.data.objects.new(cam_name, cam_data)
    target_obj = bpy.data.objects.new(target_name, None)

    track_constr = cam_obj.constraints.new('TRACK_TO')
    track_constr.target = target_obj
    track_constr.track_axis = 'TRACK_NEGATIVE_Z'
    track_constr.up_axis = 'UP_Y'

    parent.users_collection[0].objects.link(cam_obj)
    parent.users_collection[0].objects.link(target_obj)

    parent.locator_prop.cam_obj = cam_obj
    parent.locator_prop.cam_follow_player = follow_player

    cam_obj.parent = parent
    target_obj.parent = parent
    target_obj.location = target_pos.copy() - parent.location.copy()

    return cam_obj,target_obj


def import_locators(filepath):
    #TODO import_locators add sort option by type?
    root = terra_read(filepath)
    if 'Type' in root.attrib and root.attrib['Type'] == LOC:
        loc_list = [root]
    else:
        loc_list = find_chunks(root, LOC)
    for locator in loc_list:
        locname = find_val(locator, "Name")
        loctype = LTD[int(find_val(locator, "LocatorType"))]
        locpos = find_xyz(locator, "Position")
        loc_obj = locator_create(name=locname, location=locpos, loctype=loctype)

        # Type 0 (EVENT) support
        if loctype == 'EVENT':
            loc_data = locator.find("*[@Name='Data']")
            loc_obj.locator_prop.event = int(find_val(loc_data, "Unknown"))
            if find_val(loc_data, "Unknown2"):
                loc_obj.locator_prop.has_parameter = True
                if loc_obj.locator_prop.event == 65:
                    clr = hex(int(find_val(loc_data, "Unknown2")))[2:]
                    a = round(int(clr[0:2],16)/255,4)
                    r = round(int(clr[2:4],16)/255,4)
                    g = round(int(clr[4:6],16)/255,4)
                    b = round(int(clr[6:8],16)/255,4)
                    loc_obj.locator_prop.event_65_color = (r,g,b,a)
                loc_obj.locator_prop.parameter = find_val(loc_data, "Unknown2")

        
        # Type 1 (SCRIPT) support
        if loctype == 'SCRIPT':
            loc_data = locator.find("*[@Name='Data']")
            loc_obj.locator_prop.script_string = find_val(loc_data, "Unknown")

        # Type 3 (CAR) Support
        if loctype == 'CAR':
            loc_data = locator.find("*[@Name='Data']")
            loc_obj.rotation_euler[2] = radians(float(find_val(loc_data, "Rotation")))
            if "Value" in loc_data.find("*[@Name='ParkedCar']").attrib:
                loc_obj.locator_prop.parked_car = bool(int(find_val(loc_data, "ParkedCar")))
            if "Value" in loc_data.find("*[@Name='FreeCar']").attrib:
                loc_obj.locator_prop.free_car = find_val(loc_data, "FreeCar")


        # Type 4 (SPLINE) support
        if loctype == 'SPLINE':
            spline_chunk = find_chunks(locator, "0x3000007")[0]
            spline_name = find_val(spline_chunk, "Name")
            point_list = []
            for i in spline_chunk.find("*[@Name='Positions']"):
                point_list.append(item_to_vector(i))
            locator_spline_create(point_list,name=spline_name,parent=loc_obj, cam_name=spline_name)
            RailCamPropsDict = B64ToRailCam(find_val(find_chunks(spline_chunk, "0x300000A")[0],"Data"))
            RailCamPropsDict["Name"] = find_val(find_chunks(spline_chunk, "0x300000A")[0],"Name")
            SetRailCamProps(loc_obj,RailCamPropsDict)


        # Type 5 (ZONE) Support
        if loctype == 'ZONE':
            loc_data = locator.find("*[@Name='Data']")
            loc_obj.locator_prop.dynaload_string = find_val(loc_data, "DynaLoadData")

        # Type 6 (OCCLUSION) support
        if loctype == 'OCCLUSION':
            loc_data = locator.find("*[@Name='Data']")
            loc_obj.locator_prop.occlusions = int(find_val(loc_data, "Occlusions"))
        
        # Type 7 (INTERIOR) and 8 (DIRECTION) Support
        if loctype in ['INTERIOR', 'DIRECTION']:
            loc_data = locator.find("*[@Name='Data']")
            if loctype == 'INTERIOR':
                loc_obj.locator_prop.interior_name = find_val(loc_data, "InteriorName")
            matrix_chunk = loc_data.find("*[@Name='Matrix']")
            m0 = (float(matrix_chunk[0].attrib['X']), float(matrix_chunk[0].attrib['Y']), float(matrix_chunk[0].attrib['Z']))
            m1 = (float(matrix_chunk[1].attrib['X']), float(matrix_chunk[1].attrib['Y']), float(matrix_chunk[1].attrib['Z']))
            m2 = (float(matrix_chunk[2].attrib['X']), float(matrix_chunk[2].attrib['Y']), float(matrix_chunk[2].attrib['Z']))
            m = Matrix([m0,m1,m2])
            mq = m.to_quaternion()
            mq.y,mq.z = mq.z,mq.y
            loc_obj.locator_prop.rotation_matrix = mq.to_euler()
        
        
        # Type 9 (ACTION) Support
        if loctype == 'ACTION':
            loc_data = locator.findall("*[@Name='Data']/*[@Name='Unknown']/*")
            loc_obj.locator_prop.action_unknown = loc_data[0].attrib['Value']
            loc_obj.locator_prop.action_unknown2 = loc_data[1].attrib['Value']
            loc_obj.locator_prop.action_type = loc_data[2].attrib['Value']

        
        if loctype in ['EVENT', 'ACTION'] and find_locrot_LOM(locator):
            locator_matrix_create(
                name=f"{locname} Locator Matrix",
                parent=loc_obj,
                location=find_locrot_LOM(locator)[0],
                rotation=find_locrot_LOM(locator)[1],
                )
        
        for volume in find_volumes(locator):
            volume_create(parent=loc_obj, **volume)

        # Type 12 (CAM) Support
        if loctype == 'CAM':
            loc_data = locator.find("*[@Name='Data']")
            target_pos = find_xyz(loc_data, "TargetPosition")
            fov = float(find_val(loc_data, "FOV"))
            follow_player = bool(int(find_val(loc_data, "FollowPlayer")))
            locator_create_cam(target_pos, follow_player, fov, locname+" Camera", locname+" Target", parent=loc_obj)


        # Type 13 (PED) Support
        if loctype == 'PED':
            loc_data = locator.find("*[@Name='Data']")
            loc_obj.locator_prop.ped_group = int(find_val(loc_data, "Unknown"))


def invalid_locators(objs):
    """return False if everything is ok. return an error message string otherwise"""
    return "Safe checking not yet supported"


def export_locators(objs, filepath):
    root = p3d_et()
    input_objs = []
    input_objs = [loc_obj for loc_obj in objs if loc_obj.locator_prop.is_locator]
    input_objs += [child_obj.parent for child_obj in objs if (child_obj.parent and child_obj.parent.locator_prop.is_locator and child_obj.parent not in input_objs)]
    for loc_obj in input_objs:
        locator = write_chunk(root, LOC)
        write_val(locator, "Name", loc_obj.name)
        write_val(locator, "LocatorType", str(
            LTD_rev[loc_obj.locator_prop.loctype]))
        write_xyz(locator, "Position", *loc_obj.location)

        # Locator Matrix 
        if loc_obj.locator_prop.loctype in ['EVENT', 'ACTION']:
            loc_mat = write_chunk(locator, LOM)
            if loc_obj.locator_prop.use_custom_loc_matrix and loc_obj.locator_prop.loc_matrix:
                write_locrot_to_mat(loc_mat, loc_obj.locator_prop.loc_matrix)
            else:
                write_locrot_to_mat(loc_mat, loc_obj)
        
        loc_data = ET.SubElement(locator, "Value", {"Name": "Data"})
        
        # Type 0 (EVENT) support
        if loc_obj.locator_prop.loctype == 'EVENT':
            write_val(loc_data, "Unknown", loc_obj.locator_prop.event)
            if loc_obj.locator_prop.has_parameter:
                if loc_obj.locator_prop.event == 65:
                    r = hex(int(loc_obj.locator_prop.event_65_color[0]*255))[2:4]
                    g = hex(int(loc_obj.locator_prop.event_65_color[1]*255))[2:4]
                    b = hex(int(loc_obj.locator_prop.event_65_color[2]*255))[2:4]
                    a = hex(int(loc_obj.locator_prop.event_65_color[3]*255))[2:4]

                    clr = int(a+r+g+b,16)
                    loc_obj.locator_prop.parameter = str(clr)
                    write_val(loc_data, "Unknown2", clr)

                else:
                    write_val(loc_data, "Unknown2", loc_obj.locator_prop.parameter)
            else:
                write_val(loc_data, "Unknown2")
        
        
        # Type 1 (SCRIPT) support
        if loc_obj.locator_prop.loctype == 'SCRIPT':
            write_val(loc_data, "Unknown", loc_obj.locator_prop.script_string)
        
        
        # Type 3 (CAR) Support
        if loc_obj.locator_prop.loctype == 'CAR':
            write_val(loc_data, "Rotation", degrees(loc_obj.matrix_world.to_euler()[2]))
            write_val(loc_data, "ParkedCar", int(loc_obj.locator_prop.parked_car))
            if loc_obj.locator_prop.free_car:
                write_val(loc_data, "FreeCar", loc_obj.locator_prop.free_car)


        # Type 4 (SPLINE) support
        if loc_obj.locator_prop.loctype == 'SPLINE':
            spline_chunk = write_chunk(locator, "0x3000007")
            write_val(spline_chunk, "Name", loc_obj.locator_prop.loc_spline.name)
            positions = write_val(spline_chunk, "Positions")
            for spline_point in loc_obj.locator_prop.loc_spline.data.splines[0].points:
                coords = loc_obj.locator_prop.loc_spline.matrix_world @ spline_point.co.to_3d()
                write_xyz(positions, name=None, x=coords.x, y=coords.y, z=coords.z, element='Item')

            Unknown = write_chunk(spline_chunk, "0x300000A")
            DataDict = GetRailCamProps(loc_obj)
            write_val(Unknown, "Name", DataDict["Name"])
            write_val(Unknown, "Data", RailCamToB64(DataDict))

        
        
        # Type 5 (ZONE) Support
        if loc_obj.locator_prop.loctype == 'ZONE':
            write_val(loc_data, "DynaLoadData", loc_obj.locator_prop.dynaload_string)


        
        # Type 6 (OCCLUSION) support
        if loc_obj.locator_prop.loctype == 'OCCLUSION':
            write_val(loc_data, "Occlusions", loc_obj.locator_prop.occlusions)



        # Type 7 (INTERIOR) and 8 (DIRECTION) Support
        if loc_obj.locator_prop.loctype in ['INTERIOR', 'DIRECTION']:
            if loc_obj.locator_prop.loctype == 'INTERIOR':
                write_val(loc_data, "InteriorName", loc_obj.locator_prop.interior_name)
            rot = loc_obj.locator_prop.rotation_matrix.to_quaternion().copy()
            rot.y,rot.z = rot.z,rot.y
            rot = rot.to_matrix()
            matrix_el = ET.SubElement(loc_data, "Value", Name="Matrix")
            ET.SubElement(matrix_el, "Item", X=str(rot[0][0]), Y=str(rot[0][1]), Z=str(rot[0][2]))
            ET.SubElement(matrix_el, "Item", X=str(rot[1][0]), Y=str(rot[1][1]), Z=str(rot[1][2]))
            ET.SubElement(matrix_el, "Item", X=str(rot[2][0]), Y=str(rot[2][1]), Z=str(rot[2][2]))


        # Type 9 (ACTION) Support
        if loc_obj.locator_prop.loctype == 'ACTION':
            write_val(loc_data, "Unknown2", 3)
            write_val(loc_data, "Unknown3", 1)
            un_data = ET.SubElement(loc_data, "Value", {"Name": "Unknown"})
            if loc_obj.locator_prop.action_type == 'Wrench':
                loc_obj.locator_prop.action_unknown = loc_obj.name
                loc_obj.locator_prop.action_unknown2 = loc_obj.name
            ET.SubElement(un_data, "Item", {"Value": loc_obj.locator_prop.action_unknown})
            ET.SubElement(un_data, "Item", {"Value": loc_obj.locator_prop.action_unknown2})
            ET.SubElement(un_data, "Item", {"Value": loc_obj.locator_prop.action_type})

        # Type 12 (CAM) Support
        if loc_obj.locator_prop.loctype == 'CAM':
            if not loc_obj.locator_prop.cam_obj.constraints:
                write_xyz(loc_data, "TargetPosition", *Vector())
            else:
                t = loc_obj.locator_prop.cam_obj.constraints[0].target
                target_pos = t.matrix_world.to_translation()
                write_xyz(loc_data, "TargetPosition", *target_pos)
            write_val(loc_data, "FOV", degrees(loc_obj.locator_prop.cam_obj.data.angle))
            write_val(loc_data, "Unknown", 0.04) 
            write_val(loc_data, "FollowPlayer", value=str(int(loc_obj.locator_prop.cam_follow_player)))
            write_val(loc_data, "Unknown2", 0.04)
            write_val(loc_data, "Unknown3", 0)
            write_val(loc_data, "Unknown4", 0)
            write_val(loc_data, "Unknown5", 0)

        # Type 13 (PED) Support
        if loc_obj.locator_prop.loctype == 'PED':
            write_val(loc_data, "Unknown", loc_obj.locator_prop.ped_group)

        for vol_obj in [x for x in loc_obj.children if x.empty_display_type in ['CUBE','SPHERE']]:
            write_volume(locator, vol_obj)
        
    write_ET(root, filepath)
