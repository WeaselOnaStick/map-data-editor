import bpy
import bpy.props
from .utils_shar_mem_io import *
from mathutils import Euler

#TODO TeleportToInGame Operator
#TODO LocsToCurve Operator

class SMIOPropGroup(bpy.types.PropertyGroup):
    Refresh_Rate: bpy.props.FloatProperty(
        name="IO Refresh Rate",
        description="How many times per second will the add-on read data from the game. Set to 0 to stop reading",
        default = 10,
        soft_max=60,
        soft_min=1,
        min=0.00,
    )
    Sync_Cursor: bpy.props.BoolProperty(
        name="Sync 3D Cursor With Player Position",
        default=False,
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
    global SMIO_data
    SMIO_data = SMIO_read()
    if SMIO_data:
        #print(SMIO_data)
        SMIO = bpy.context.scene.SMIO

        if SMIO_data.get('Car_Position'):
            SMIO.Car_Position = SMIO_data.get('Car_Position')
        if SMIO_data.get('Car_Rotation'):
            SMIO.Car_Rotation = SMIO_data.get('Car_Rotation')
        if SMIO_data.get('Player_Position'):
            SMIO.Player_Position = SMIO_data.get('Player_Position')
        if SMIO_data.get('Player_Rotation'):
            SMIO.Player_Rotation = SMIO_data.get('Player_Rotation')

        if SMIO.Sync_Cursor:
            if SMIO_data.get('Player In Car'):
                bpy.context.scene.cursor.location = SMIO.Car_Position
                bpy.context.scene.cursor.rotation_euler = SMIO.Car_Rotation
            else:
                bpy.context.scene.cursor.location = SMIO.Player_Position
                bpy.context.scene.cursor.rotation_euler = Euler((0,0,SMIO.Player_Rotation), 'XYZ')
    if bpy.context.scene.SMIO.Refresh_Rate > 0:
        return 1.0/bpy.context.scene.SMIO.Refresh_Rate
    else:
        return

class SMIO_refresh(bpy.types.Operator, SharMemIOModule):
    bl_idname = "scene.smio_refresh"
    bl_label = "Refresh Memory IO"

    def execute(self, context):
        if bpy.app.timers.is_registered(update_SMIO):
            bpy.app.timers.unregister(update_SMIO)
        bpy.app.timers.register(update_SMIO)
        return {'FINISHED'}


class Teleport_To_Cursor(bpy.types.Operator):
    bl_idname = "scene.teleport_to_cursor"
    bl_label = "Teleport To 3D Cursor"

    def execute(self, context):
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
                    tbox.enabled = False
                else:
                    box.label(text=data_key + " : " + str(SMIO_data[data_key]))
        box.operator("scene.smio_refresh", icon='FILE_REFRESH')
        box.prop(context.scene.SMIO, "Refresh_Rate")
        box.prop(context.scene.SMIO, "Sync_Cursor")
        

to_register = [
    SMIOPropGroup,
    SMIO_refresh,
    MDE_PT_SHARMEMIO,
]