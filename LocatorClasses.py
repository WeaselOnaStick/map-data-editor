import bpy
from bpy.props import *
from bpy_extras.io_utils import ExportHelper, ImportHelper
from .utils_bpy import reminder
from . import LocatorManager as LM
from os import path


class LocatorPropGroup(bpy.types.PropertyGroup):

    is_locator: bpy.props.BoolProperty(
        name='Is a SHAR locator',
        description='Enables locator properties for this object',
        default=False
    )
    loctype: bpy.props.EnumProperty(
        items=LM.locator_types,
        name='Locator Type',
        description=''
    )
    # Type 0 support
    event: bpy.props.IntProperty(
        name='Event',
        description=LM.event_description,
        min=0,
    )
    has_parameter: bpy.props.BoolProperty(
        name='Has Parameter',
    )
    parameter: bpy.props.IntProperty(
        name='Parameter',
        min=0
    )
    # Type 3 support
    parked_car: bpy.props.BoolProperty(
        name="ParkedCar",
    )
    free_car: bpy.props.StringProperty(
        name="FreeCar",
        description="Leave empty to disable"
    )
    # Type 9 support
    action_type: bpy.props.EnumProperty(
        items=LM.action_types,
        name='Action Event Type'
    )
    action_unknown: bpy.props.StringProperty(
        name="Unknown"
    )
    action_unknown2: bpy.props.StringProperty(
        name="Unknown 2"
    )
    # Type 12 support
    cam_follow_player: bpy.props.BoolProperty(
        name="Follow Player"
    )
    cam_dat: bpy.props.PointerProperty(type=bpy.types.Camera, name="Camera")


class FileImportLocators(bpy.types.Operator, ImportHelper):
    bl_idname = 'import_scene.locators_p3dxml'
    bl_label = 'Import Locators'
    filename_ext = '.p3dxml'
    filter_glob: bpy.props.StringProperty(default='*.p3dxml',
                                          options={'HIDDEN'},
                                          maxlen=255)

    def execute(self, context):
        LM.import_locators(self.filepath)
        return {'FINISHED'}


class FileExportLocators(bpy.types.Operator, ExportHelper):
    bl_idname = 'export_scene.locators_p3dxml'
    bl_label = 'Export Locators'
    filename_ext = '.p3dxml'
    filter_glob: bpy.props.StringProperty(default='*.p3dxml',
                                          options={'HIDDEN'},
                                          maxlen=255)
    selected_only: bpy.props.BoolProperty(name='Export Selected Locators',
                                          description='Only export selected locator objects',
                                          default=True)
    safe_check: bpy.props.BoolProperty(name='Check Locators Validity',
                                       description='Check if specific locators have/don\'t have a trigger volume',
                                       default=False)

    def execute(self, context):
        if self.selected_only:
            locator_objs = context.selected_objects
        else:
            if 'Locators' in context.scene.collection.children:
                locator_objs = context.scene.collection.children['Locators'].all_objects
            else:
                self.report(
                    {'ERROR'}, "No \"Locators\" collection found in Master Collection")
                return{'CANCELLED'}
        if self.safe_check:
            if LM.invalid_locators(locator_objs):
                self.report({'ERROR'}, LM.invalid_locators(locator_objs))
                return {'CANCELLED'}
        self.report({'INFO'}, 'Safe check passed')
        LM.export_locators(locator_objs, self.filepath)
        self.report(
            {'INFO'}, f"Successfully exported {path.basename(self.filepath)}")
        return {'FINISHED'}


def get_cur_locator(context):
    if context.object:
        if context.object.locator_prop.is_locator:
            return context.object
        elif context.object.parent and context.object.parent.locator_prop.is_locator:
            return context.object.parent


class volume_filter:
    @ classmethod
    def poll(cls, context):
        if get_cur_locator(context):
            return LM.locator_can_have_volume(get_cur_locator(context))


class MDE_OP_locator_create(bpy.types.Operator):
    bl_idname = "object.mde_op_locator_create"
    bl_label = "Create Locator"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        loc_obj = LM.locator_create(location=context.scene.cursor.location)
        context.view_layer.objects.active = loc_obj
        loc_obj.select_set(True)
        return {'FINISHED'}


class MDE_OP_volume_create_sphere(bpy.types.Operator, volume_filter):
    bl_idname = "object.mde_op_vol_create_sphere"
    bl_label = "Create Spherical Volume"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        vol_obj = LM.volume_create(parent=get_cur_locator(context), is_rect=False, location=context.scene.cursor.location)
        context.view_layer.objects.active = vol_obj
        vol_obj.select_set(True)
        return {'FINISHED'}


class MDE_OP_volume_create_cube(bpy.types.Operator, volume_filter):
    bl_idname = "object.mde_op_vol_create_cube"
    bl_label = "Create Cuboid Volume"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        vol_obj = LM.volume_create(parent=get_cur_locator(context), is_rect=True, location=context.scene.cursor.location)
        context.view_layer.objects.active = vol_obj
        vol_obj.select_set(True)
        return {'FINISHED'}


class LocatorModule:

    @ classmethod
    def poll(cls, context):
        return context.preferences.addons[__package__].preferences.LocatorsEnabled


class MDE_PT_LocatorFileManagement(bpy.types.Panel, LocatorModule):
    bl_label = "File Management"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WMDE Locators'
    bl_order = 5

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text='', icon='FILE')

    def draw(self, context):
        layout = self.layout
        layout.operator('import_scene.locators_p3dxml', icon='IMPORT')
        layout.operator('export_scene.locators_p3dxml', icon='EXPORT')


class MDE_PT_Locators(bpy.types.Panel, LocatorModule):
    bl_label = 'Locators'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WMDE Locators'
    bl_order = 6

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text='', icon='EMPTY_AXIS')

    def draw(self, context):
        layout = self.layout
        col = layout.column_flow()
        col.operator("object.mde_op_locator_create", icon='OBJECT_ORIGIN')
        locator = get_cur_locator(context)
        if locator:
            col.separator(factor=1.5)
            col.operator("object.mde_op_vol_create_sphere", icon='SPHERE')
            col.operator("object.mde_op_vol_create_cube", icon='CUBE')
            box = layout.box()
            box.prop(locator.locator_prop, "loctype")
            if locator.locator_prop.loctype == 'EVENT':
                box.prop(locator.locator_prop, "event")
                box.prop(locator.locator_prop, "has_parameter")
                grd = box.grid_flow()
                grd.enabled = locator.locator_prop.has_parameter
                grd.prop(locator.locator_prop, "parameter")
            if locator.locator_prop.loctype == 'CAR':
                box.prop(locator.locator_prop, "free_car")
                box.prop(locator.locator_prop, "parked_car")
            if locator.locator_prop.loctype == 'ACTION':
                box.prop(locator.locator_prop, "action_type")
                box.prop(locator.locator_prop, "action_unknown")
                box.prop(locator.locator_prop, "action_unknown2")
            if locator.locator_prop.loctype == 'CAM':
                box.prop(locator.locator_prop, "cam_dat")
                if locator.locator_prop.cam_dat:
                    box.prop(locator.locator_prop.cam_dat, "angle")
                else:
                    box.label(text="No camera found!")
                box.prop(locator.locator_prop, "cam_follow_player")
