import bpy
from bpy.props import *
from bpy_extras.io_utils import ExportHelper, ImportHelper
from .PathManager import *
from .utils_bpy import pcoll
from . import utils_math


def object_is_path_curve(obj):
    if obj.type != 'CURVE':
        return False
    if len(obj.data.splines) != 1:
        return False
    if obj.data.splines[0].type != 'POLY':
        return False
    return True


class FileImportPaths(bpy.types.Operator, ImportHelper):
    bl_idname = 'import_scene.paths_p3dxml'
    bl_label = 'Import Paths...'
    filename_ext = '.p3dxml'
    filter_glob: bpy.props.StringProperty(
        default='*.p3dxml',
        options={'HIDDEN'},
        maxlen=255,
    )

    def execute(self, context):
        result = import_paths(self.filepath)
        if result != 'OK':
            self.report(type={'ERROR'}, message=result)
            return {'FINISHED'}
        else:
            return {'FINISHED'}


class FileExportPaths(bpy.types.Operator, ExportHelper):
    bl_idname = 'export_scene.paths_p3dxml'
    bl_label = 'Export Paths...'
    filename_ext = '.p3dxml'
    filter_glob: bpy.props.StringProperty(default='*.p3dxml',
                                          options={
                                              'HIDDEN'},
                                          maxlen=255)
    selected_only: bpy.props.BoolProperty(name='Selected Only',
                                          description='Only export selected path objects',
                                          default=False)

    def execute(self, context):
        result = None
        if self.selected_only:
            objs = [x for x in context.selected_objects if object_is_path_curve(x)]
            if not objs:
                self.report({'ERROR_INVALID_INPUT'}, 'No valid path objects selected!')
                return {'CANCELLED'}
        else:
            if 'Paths' not in bpy.data.collections:
                self.report({'ERROR'}, 'No "Paths" collection found')
                return {'CANCELLED'}
            objs = [x for x in bpy.data.collections['Paths'].objects if object_is_path_curve(x)]

        invalid_objs = [] # Apparently this game freezes and dies if a Path has more than exactly 32 points. Go figure
        for path_obj in objs:
            if len(path_obj.data.splines[0].points) > 32:
                invalid_objs.append(path_obj)


        valid_objs = [x for x in objs if not x in invalid_objs]
                

        result = export_paths(self.filepath, valid_objs)
        if result == 0:
            self.report({'WARNING', "No paths exported"})
            return {'CANCELLED'}
        elif invalid_objs and not valid_objs:
            self.report({'ERROR'}, "All paths exceed maximum length (32)")
            return {'CANCELLED'}
        elif invalid_objs and valid_objs:
            self.report({'WARNING'}, f"{len(invalid_objs)} paths exceeded maximum length (32), have been selected and not exported to prevent crash")
            bpy.ops.object.select_all(action='DESELECT')
            for o in invalid_objs:
                o.select_set(True)
            return {'FINISHED'}
        else:
            self.report({'INFO'}, f"Successfully exported {result} paths to {self.filepath}")
            return {'FINISHED'}


class PathCreateBasic(bpy.types.Operator):
    bl_idname = 'object.path_create_basic'
    bl_label = 'Create Basic Path'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        path_create_basic(cursor=context.scene.cursor)
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}


class PathCreateCircular(bpy.types.Operator):
    bl_idname = 'object.path_create_circular'
    bl_label = 'Create Circular Path'
    bl_options = {'REGISTER', 'UNDO'}

    radius: bpy.props.FloatProperty(
        description='Radius of the curve',
        name='Radius',
        min=0,
        default=8,
        )
    resolution: bpy.props.IntProperty(
        description='Amount of spline points to generate',
        name='Resolution',
        min=2,
        soft_max=20,
        default=6,
        )
    offset: bpy.props.FloatVectorProperty(
        name='Offset',
        subtype='XYZ',
        unit='LENGTH',
        )
    rotation: bpy.props.FloatVectorProperty(
        name='Rotation',
        subtype='EULER',
        unit='ROTATION',
        )
    scale: bpy.props.FloatVectorProperty(
        name='Scale',
        subtype='XYZ',
        min=0.01,
        default=(1, 1),
        size=2,
        )

    def execute(self, context):
        path_create_circular(cursor=context.scene.cursor, kwargs=self.as_keywords())
        return {'FINISHED'}

class PathModule:

    @classmethod
    def poll(cls, context):
        return context.preferences.addons[__package__].preferences.PathsEnabled


class MDE_PT_PathFileManagement(bpy.types.Panel, PathModule):
    bl_label = 'File Management'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WMDE Paths'
    bl_order = 0

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text='', icon='FILE')

    def draw(self, context):
        layout = self.layout
        layout.operator('import_scene.paths_p3dxml', icon='IMPORT')
        layout.operator('export_scene.paths_p3dxml', icon='EXPORT')


class MDE_PT_Paths(bpy.types.Panel, PathModule):
    bl_label = 'Pedestrian Paths'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WMDE Paths'
    bl_order = 4

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text='', icon_value=(pcoll['PATH_PED'].icon_id))

    def draw(self, context):
        layout = self.layout
        layout.operator((PathCreateBasic.bl_idname), icon='CURVE_PATH')
        layout.operator((PathCreateCircular.bl_idname), icon='LIGHT_POINT')

to_register = [
    FileExportPaths,
    FileImportPaths,
    MDE_PT_PathFileManagement,
    MDE_PT_Paths,
    PathCreateBasic,
    PathCreateCircular,
    ]