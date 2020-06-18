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


def locator_create(name="Locator", location=Vector(), loctype='EVENT', volume_kwargs={}):
    if 'Locators' not in bpy.context.scene.collection.children:
        locator_collection = bpy.data.collections.new('Locators')
        bpy.context.scene.collection.children.link(locator_collection)
    else:
        locator_collection = bpy.data.collections['Locators']
    loc_obj = bpy.data.objects.new(name, None)
    loc_obj.empty_display_type = 'ARROWS'
    loc_obj.location = location
    loc_obj.locator_prop.is_locator = True
    loc_obj.locator_prop.loctype = loctype
    if volume_kwargs:
        volume_create(**volume_kwargs, parent=loc_obj)
    locator_collection.objects.link(loc_obj)
    return loc_obj

# TODO Type 4 and 12 cam locators here somehow?


def locator_create_cam():
    pass


def import_locators(filepath):
    # TODO import_locators add sort option by type?
    root = terra_read(filepath)
    for locator in find_chunks(root, LOC):
        locname = find_val(locator, "Name")
        loctype = LTD[int(find_val(locator, "LocatorType"))]
        locpos = find_xyz(locator, "Position")
        loc_obj = locator_create(
            name=locname, location=locpos, loctype=loctype)
        # EVENT SUPPORT
        if loctype == 'EVENT':
            loc_data = locator.find("*[@Name='Data']")
            loc_obj.locator_prop.event = int(find_val(loc_data, "Unknown"))
            if find_val(loc_data, "Unknown2"):
                loc_obj.locator_prop.has_parameter = True
                loc_obj.locator_prop.parameter = int(
                    find_val(loc_data, "Unknown2"))
        # CAR SUPPORT
        if loctype == 'CAR':
            loc_data = locator.find("*[@Name='Data']")
            loc_obj.rotation_euler[2] = radians(
                float(find_val(loc_data, "Rotation")))
            if "Value" in loc_data.find("*[@Name='ParkedCar']").attrib:
                loc_obj.locator_prop.parked_car = bool(
                    int(find_val(loc_data, "ParkedCar")))
            if "Value" in loc_data.find("*[@Name='FreeCar']").attrib:
                loc_obj.locator_prop.free_car = find_val(loc_data, "FreeCar")
        # ACTION SUPPORT
        if loctype == 'ACTION':
            loc_data = locator.findall("*[@Name='Data']/*[@Name='Unknown']/*")
            print(f"found action data! {list(loc_data)}")
            loc_obj.locator_prop.action_unknown = loc_data[0].attrib['Value']
            loc_obj.locator_prop.action_unknown2 = loc_data[1].attrib['Value']
            loc_obj.locator_prop.action_type = loc_data[2].attrib['Value']
        if loctype in ['EVENT', 'ACTION'] and find_locrot_LOM(locator):
            loc_obj.rotation_euler = find_locrot_LOM(locator)[1]
        for volume in find_volumes(locator):
            volume_create(parent=loc_obj, **volume)
        # CAM SUPPORT
        if loctype == 'CAM':
            # TODO Type 12 Cam chunk import support
            pass


def invalid_locators(objs):
    """return False if everything is ok. return an error message string otherwise"""
    return "Safe checking not yet supported"


def export_locators(objs, filepath):
    root = p3d_et()
    print(f"Got input: {objs}")
    input_objs = []
    input_objs = [
        loc_obj for loc_obj in objs if loc_obj.locator_prop.is_locator]
    input_objs = input_objs + [vol_obj.parent for vol_obj in objs
                               if (vol_obj.parent
                                   and vol_obj.parent not in objs
                                   and vol_obj.parent.locator_prop.is_locator)]
    for loc_obj in input_objs:
        locator = write_chunk(root, LOC)
        write_val(locator, "Name", loc_obj.name)
        write_val(locator, "LocatorType", str(
            LTD_rev[loc_obj.locator_prop.loctype]))
        write_xyz(locator, "Position", *loc_obj.location)
        for vol_obj in loc_obj.children:
            write_volume(locator, vol_obj)
        # Locator Matrix (BASE ONLY, DOESN'T FULLY WORK)
        if loc_obj.locator_prop.loctype in ['EVENT', 'ACTION']:
            loc_mat = write_chunk(locator, LOM)
            write_locrot_to_mat(loc_mat, loc_obj)
        loc_data = ET.SubElement(locator, "Value", {"Name": "Data"})
        # Type 0 support
        if loc_obj.locator_prop.loctype == 'EVENT':
            write_val(loc_data, "Unknown", loc_obj.locator_prop.event)
            if loc_obj.locator_prop.has_parameter:
                write_val(loc_data, "Unknown2", loc_obj.locator_prop.parameter)
        # Type 3 Support
        if loc_obj.locator_prop.loctype == 'CAR':
            write_val(loc_data, "Rotation", degrees(
                loc_obj.matrix_world.to_euler()[2]))
            write_val(loc_data, "ParkedCar", int(
                loc_obj.locator_prop.parked_car))
            if loc_obj.locator_prop.free_car:
                write_val(loc_data, "FreeCar", loc_obj.locator_prop.free_car)
        # Type 9 Support
        if loc_obj.locator_prop.loctype == 'ACTION':
            write_val(loc_data, "Unknown2", 3)
            write_val(loc_data, "Unknown3", 1)
            un_data = ET.SubElement(loc_data, "Value", {"Name": "Unknown"})
            ET.SubElement(un_data, "Item", {"Value": loc_obj.locator_prop.action_unknown})
            ET.SubElement(un_data, "Item", {"Value": loc_obj.locator_prop.action_unknown2})
            ET.SubElement(un_data, "Item", {"Value": loc_obj.locator_prop.action_type})
        # Type 12 Support
        if loc_obj.locator_prop.loctype == 'CAM':
            write_val(loc_data, "Unknown", 0.04)
            write_val(loc_data, "Unknown2", 0.04)
            write_val(loc_data, "Unknown3", 0)
            write_val(loc_data, "Unknown4", 0)
            write_val(loc_data, "Unknown5", 0)
            write_xyz(loc_data, "TargetPosition", 0, 0, 0)
            write_val(loc_data, "FOV", degrees(loc_obj.locator_prop.cam_dat.angle))
            write_val(loc_data, "FollowPlayer", int(loc_obj.locator_prop.cam_follow_player))
    write_ET(root, filepath)
