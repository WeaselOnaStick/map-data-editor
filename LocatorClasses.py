import bpy
from bpy.props import *
from bpy_extras.io_utils import ExportHelper, ImportHelper
from mathutils import Vector
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
        description='',
    )
    use_custom_loc_matrix: bpy.props.BoolProperty(
        name="Custom Locator Matrix",
        description="By default WMDE creates locator matrix as duplicate of locator. You might wanna change that depending on the locator",
    )
    loc_matrix: bpy.props.PointerProperty(
        name="Locator Matrix",
        type=bpy.types.Object,
        description="Locator Matrix is used in different locator types differently. Current type doesn't have a description"
    )
    # Type 0 (EVENT) support
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
    # Type 1 (SCRIPT) Support
    script_string: bpy.props.StringProperty(
        name='Unknown',
        description='',
    )
    # Type 3 (CAR) Support
    parked_car: bpy.props.BoolProperty(
        name="ParkedCar",
    )
    free_car: bpy.props.StringProperty(
        name="FreeCar",
        description="Leave empty to disable"
    )
    # Type 4 (SPLINE) support
    loc_spline: bpy.props.PointerProperty(
        name="Locator Spline",
        type=bpy.types.Object,
        description="Locator spline constrains game camera to sit on the spline and follow player"
    )
    loc_spline_cam_name: bpy.props.StringProperty(
        name="Unknown",
        description="Camera name?"
    )
    # Type 5 (ZONE) Support
    dynaload_string: bpy.props.StringProperty(
        name="Dyna Load Data",
        description="These strings define instructions to load and unload zones of the world (file names relative to the \"art\" folder)"
    )
    # Type 6 (OCCLUSION) support
    occlusions: bpy.props.IntProperty(
        name="Occlusions",
        description="Purpose of this is still unknown. Maybe YOU can figure it out?",
        default=0,
    )
    # Type 7 (INTERIOR) Support
    interior_name: bpy.props.StringProperty(
        name="InteriorName",
        description="Name of the interior"
    )
    rotation_matrix : bpy.props.FloatVectorProperty(
        name="Rotation",
        subtype="EULER",
        unit="ROTATION",
        size=3,
    )
    # Type 8 (DIRECTION) Support uses same matrix as above

    # Type 9 (ACTION) Support
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
    # Type 12 (CAM) Support
    cam_obj: bpy.props.PointerProperty(
        name="Camera Object",
        type=bpy.types.Object,
        #description="",
    )
    cam_follow_player: bpy.props.BoolProperty(
        name="Follow Player"
    )


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
    bl_label = "Add Spherical Volume"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        vol_obj = LM.volume_create(parent=get_cur_locator(context), is_rect=False, location=context.scene.cursor.location)
        context.view_layer.objects.active = vol_obj
        vol_obj.select_set(True)
        return {'FINISHED'}


class MDE_OP_volume_create_cube(bpy.types.Operator, volume_filter):
    bl_idname = "object.mde_op_vol_create_cube"
    bl_label = "Add Cuboid Volume"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        vol_obj = LM.volume_create(parent=get_cur_locator(context), is_rect=True, location=context.scene.cursor.location)
        context.view_layer.objects.active = vol_obj
        vol_obj.select_set(True)
        return {'FINISHED'}


class MDE_OP_locator_matrix_create(bpy.types.Operator):
    bl_idname = "object.loc_matrix_create"
    bl_label = "Create Locator Matrix"


    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        lm_obj = LM.locator_matrix_create(parent=get_cur_locator(context),location=context.scene.cursor.location)
        lm_obj.select_set(True)
        context.view_layer.objects.active = lm_obj
        return {'FINISHED'}


class MDE_OP_locator_matrix_delete(bpy.types.Operator):
    bl_idname = "object.loc_matrix_delete"
    bl_label = "Delete Locator Matrix"

    def execute(self, context):
        cur_loc = get_cur_locator(context)
        cur_loc.select_set(True)
        context.view_layer.objects.active = cur_loc
        bpy.data.objects.remove(cur_loc.locator_prop.loc_matrix)
        return {'FINISHED'}


class MDE_OP_loc_spline_create(bpy.types.Operator):
    bl_idname = "object.loc_spline_create"
    bl_label = "Create Locator Spline"


    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        spline_obj = LM.locator_spline_create(
            parent=get_cur_locator(context),
            points=[
                context.scene.cursor.location + Vector((0,0,0)),
                context.scene.cursor.location + Vector((1,1,0)),
                context.scene.cursor.location + Vector((0,2,0)),
                ])
        spline_obj.select_set(True)
        context.view_layer.objects.active = spline_obj
        return {'FINISHED'}


class MDE_OP_locator_spline_delete(bpy.types.Operator):
    bl_idname = "object.loc_spline_delete"
    bl_label = "Delete Locator Spline"

    def execute(self, context):
        cur_loc = get_cur_locator(context)
        cur_loc.select_set(True)
        context.view_layer.objects.active = cur_loc
        bpy.data.curves.remove(cur_loc.locator_prop.loc_spline.data)
        return {'FINISHED'}

class MDE_OP_loc_cam_create(bpy.types.Operator):
    bl_idname = "object.loc_cam_create"
    bl_label = "Create Static Camera"


    def execute(self, context):
        cur_loc = get_cur_locator(context)
        bpy.ops.object.select_all(action='DESELECT')
        cam_obj,target_obj = LM.locator_create_cam(target_pos = context.scene.cursor.location, parent = cur_loc)
        target_obj.select_set(True)
        context.view_layer.objects.active = target_obj
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
        col = layout.column()
        col.operator("object.mde_op_locator_create", icon='PLUS')
        locator = get_cur_locator(context)
        col.separator(factor=1.5)
        if not locator:
            col.label(text=f"No Locator Selected")
        if locator:
            col.label(text=f"{locator.name}")
            box = layout.box()
            row = box.row(align=True)
            row.label(text="Locator Type:")
            row.prop(locator.locator_prop, "loctype", text="")
            if locator.locator_prop.loctype in ['EVENT','SCRIPT','SPLINE','ZONE','OCCLUSION','INTERIOR','ACTION','CAM','PED']:
                #TODO operator: flip currently active empty from sphere <-> cube
                box.operator("object.mde_op_vol_create_sphere", icon='SPHERE')
                box.operator("object.mde_op_vol_create_cube", icon='CUBE')
            
            if locator.locator_prop.loctype in ['EVENT','ACTION']:
                matrix_box = box.box()
                matrix_box.prop(locator.locator_prop, "use_custom_loc_matrix")
                row = matrix_box.row(align=True)
                row.label(text="Locator Matrix")
                row.prop(locator.locator_prop, "loc_matrix", text="")
                row.enabled = locator.locator_prop.use_custom_loc_matrix
                col = matrix_box.column(align=True)
                row = col.row()
                row.operator("object.loc_matrix_create", icon='PLUS')
                row.enabled = locator.locator_prop.use_custom_loc_matrix and not locator.locator_prop.loc_matrix
                row = col.row()
                row.operator("object.loc_matrix_delete", icon='TRASH')
                row.enabled = bool(locator.locator_prop.loc_matrix)
                
            


            # Type 0 (EVENT) support
            if locator.locator_prop.loctype == 'EVENT':
                box.prop(locator.locator_prop, "event")
                box.prop(locator.locator_prop, "has_parameter")
                grd = box.grid_flow()
                grd.enabled = locator.locator_prop.has_parameter
                grd.prop(locator.locator_prop, "parameter")

            # Type 1 (SCRIPT) support
            if locator.locator_prop.loctype == 'SCRIPT':
                box.prop(locator.locator_prop, "script_string")

            # Type 3 (CAR) Support
            if locator.locator_prop.loctype == 'CAR':
                box.prop(locator.locator_prop, "free_car")
                box.prop(locator.locator_prop, "parked_car")

            # Type 4 (SPLINE) support
            if locator.locator_prop.loctype == 'SPLINE':
                box = box.box()
                row = box.row()
                row.label(text="Spline")
                row.prop(locator.locator_prop, "loc_spline", text="")
                col = box.column()
                row = col.row()
                row.operator("object.loc_spline_create", icon='PLUS')
                row.enabled = not locator.locator_prop.loc_spline
                row = col.row()
                row.operator("object.loc_spline_delete", icon='TRASH')
                row.enabled = bool(locator.locator_prop.loc_spline)
                row = col.row()
                row.label(text="Unknown")
                row.prop(locator.locator_prop, "loc_spline_cam_name", text="")

            # Type 5 (ZONE) Support
            if locator.locator_prop.loctype == 'ZONE':
                box.prop(locator.locator_prop, "dynaload_string")
                box.operator("wm.url_open", text="Dyna Load Data Strings", icon='QUESTION').url="https://docs.donutteam.com/docs/hitandrun/misc/dyna-load-data"

            # Type 6 (OCCLUSION) support
            if locator.locator_prop.loctype == 'OCCLUSION':
                box.prop(locator.locator_prop, "occlusions")

            
            # Type 7 (INTERIOR) and 8 (DIRECTION) Support
            if locator.locator_prop.loctype == 'INTERIOR':
                row = box.row()
                row.label(text="Interior Name")
                row.prop(locator.locator_prop, "interior_name", text="")

            if locator.locator_prop.loctype in ['INTERIOR', 'DIRECTION']:
                box.prop(locator.locator_prop, "rotation_matrix")

            # Type 9 (ACTION) Support
            if locator.locator_prop.loctype == 'ACTION':
                box.prop(locator.locator_prop, "action_type")
                box.prop(locator.locator_prop, "action_unknown")
                box.prop(locator.locator_prop, "action_unknown2")
                
            # Type 12 (CAM) Support
            if locator.locator_prop.loctype == 'CAM':
                box.prop(locator.locator_prop, "cam_obj")
                if locator.locator_prop.cam_obj:
                    box.prop(locator.locator_prop.cam_obj.data, "angle")
                else:
                    row = box.row()
                    row.label(text="No camera found!")
                    row.operator("object.loc_cam_create", icon='PLUS', text="Create Camera")
                box.prop(locator.locator_prop, "cam_follow_player")

            
            # Type 13 (PED) Support
            if locator.locator_prop.loctype == 'PED':
                pass
