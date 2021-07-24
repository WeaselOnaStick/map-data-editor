import bpy
import bpy.props
from bpy.types import Object
from .utils_shar_mem_io import *
from mathutils import Euler

def SMIO_refresh(self, context):
    if bpy.app.timers.is_registered(update_SMIO):
        bpy.app.timers.unregister(update_SMIO)
    bpy.app.timers.register(update_SMIO)

class SMIOPropGroup(bpy.types.PropertyGroup):
    Refresh_Rate: bpy.props.FloatProperty(
        name="IO Refresh Rate",
        description="How many times per second will the add-on read data from the game. Set to 0 to stop reading",
        default = 10,
        soft_max=60,
        soft_min=1,
        min=0.00,
        update=SMIO_refresh,
    )
    Sync_Cursor: bpy.props.BoolProperty(
        name="Sync 3D Cursor With Player Position",
        default=False,
        description="If set, in-game position and rotation will be written to 3D cursor"
    )
    Key_Object: bpy.props.BoolProperty(
        name="Key An Object",
        description="When enabled, allows you to key location and rotation of an object using in-game position and rotation",
        update=SMIO_refresh,
    )
    Object_To_Key: bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="Object To Key",
        description="If set, in-game position and rotation will be written to this object"
    )
    Extend_Keying: bpy.props.BoolProperty(
        name="Extend Scene Duration",
        description="When enabled, extends scene duration while keying an object"
    )
    Player_Position: bpy.props.FloatVectorProperty(
        name='Player Position',
        size=3,
        subtype='TRANSLATION',
        default=(0,0,0),
    )
    Player_Rotation : bpy.props.FloatProperty(
        name = 'Player Rotation',
        subtype='ANGLE',
        unit='ROTATION',
    )
    Car_Position: bpy.props.FloatVectorProperty(
        name='Car Position',
        size=3,
        subtype='TRANSLATION',
        default=(0,0,0),
    )
    Car_Rotation: bpy.props.FloatVectorProperty(
        name='Car Rotation',
        size=3,
        unit='ROTATION',
        subtype='EULER',
        default=(0,0,0),
    )

class SharMemIOModule:
    @classmethod
    def poll(cls, context):
        return context.preferences.addons[__package__].preferences.SHARMemIO

SMIO_data = {}

def update_SMIO():
    context = bpy.context
    global SMIO_data
    SMIO_data = SMIO_read()
    if SMIO_data:
        #print(SMIO_data)
        SMIO = context.scene.SMIO

        if SMIO_data.get('Car_Position'):
            SMIO.Car_Position = SMIO_data.get('Car_Position')
        if SMIO_data.get('Car_Rotation'):
            SMIO.Car_Rotation = SMIO_data.get('Car_Rotation')
        if SMIO_data.get('Player_Position'):
            SMIO.Player_Position = SMIO_data.get('Player_Position')
        if SMIO_data.get('Player_Rotation'):
            SMIO.Player_Rotation = SMIO_data.get('Player_Rotation')

        if SMIO.Sync_Cursor:
            cursor = context.scene.cursor
            context.scene.cursor.rotation_mode = 'XYZ'
            if SMIO_data.get('Player In Car'):
                cursor.location = SMIO.Car_Position
                cursor.rotation_euler = SMIO.Car_Rotation
            else:
                cursor.location = SMIO.Player_Position
                cursor.rotation_euler = Euler((0,0,SMIO.Player_Rotation), 'XYZ')

        if SMIO.Key_Object and SMIO.Object_To_Key:
            #print(SMIO.Key_Object)
            if SMIO.Extend_Keying and (context.scene.frame_end-context.scene.frame_current<40):
                context.scene.frame_end += 40

            ObjectToKey = SMIO.Object_To_Key
            if SMIO_data.get('Player In Car'):
                ObjectToKey.location = SMIO.Car_Position
                ObjectToKey.rotation_euler = SMIO.Car_Rotation
            else:
                ObjectToKey.location = SMIO.Player_Position
                ObjectToKey.rotation_euler = Euler((0,0,SMIO.Player_Rotation), 'XYZ')

            ObjectToKey.keyframe_insert(data_path='location',frame=context.scene.frame_current)
            ObjectToKey.keyframe_insert(data_path='rotation_euler',frame=context.scene.frame_current)
    
    if context.scene.SMIO.Refresh_Rate > 0:
        return 1.0/context.scene.SMIO.Refresh_Rate
    else:
        return


class MDE_OT_SMIO_refresh(bpy.types.Operator, SharMemIOModule):
    bl_idname = "scene.smio_refresh"
    bl_label = "Refresh Memory IO"

    def execute(self, context):
        SMIO_refresh(self, context)
        return {'FINISHED'}


class MDE_OT_Teleport_To_Cursor(bpy.types.Operator):
    bl_idname = "scene.smio_teleport_to_cursor"
    bl_label = "Teleport To 3D Cursor"

    def execute(self, context):
        SMIO_Teleport_To(context.scene.cursor.location)
        return {'FINISHED'}


class MDE_PT_SHARMEMIO(bpy.types.Panel, SharMemIOModule):
    bl_label = "SHAR Memory IO"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WMDE Misc'
    
    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text='', icon='MEMORY')

    def draw(self, context):
        layout = self.layout
        box=layout.box()
        if not SMIO_data:
            box.label(text="Simpsons.exe is not running",icon='ERROR')
        else:
            box.label(text="Simpsons.exe")
            for data_key in SMIO_data.keys():
                if data_key in ['Player_Position', 'Player_Rotation', 'Car_Position', 'Car_Rotation',]:
                    tbox = box.box()
                    tbox.prop(context.scene.SMIO,data_key)
                    #tbox.enabled = False
                else:
                    box.label(text=data_key + " : " + str(SMIO_data[data_key]))
        box.operator("scene.smio_refresh", icon='FILE_REFRESH')
        box.prop(context.scene.SMIO, "Refresh_Rate")
        box.operator('scene.smio_teleport_to_cursor',icon='URL')
        box.prop(context.scene.SMIO, "Sync_Cursor")
        kbox = box.box()
        kbox.prop(context.scene.SMIO, "Key_Object")
        trow = kbox.row()
        trow.prop(context.scene.SMIO, "Object_To_Key")
        trow.enabled = context.scene.SMIO.Key_Object
        trow = kbox.row()
        trow.prop(context.scene.SMIO, "Extend_Keying")
        trow.enabled = bool(context.scene.SMIO.Key_Object)
        trow = kbox.row()
        if context.screen.is_animation_playing:
            trow.operator("screen.animation_play", text = 'PAUSE', icon = 'PAUSE')
        else:
            trow.operator("screen.animation_play", text = 'PLAY', icon = 'PLAY')
        trow.enabled = context.scene.SMIO.Key_Object
        trow.scale_x = 1

        

to_register = [
    SMIOPropGroup,
    MDE_OT_SMIO_refresh,
    MDE_OT_Teleport_To_Cursor,
    MDE_PT_SHARMEMIO,
]