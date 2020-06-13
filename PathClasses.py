import bpy
from bpy.props import *
from bpy_extras.io_utils import ExportHelper, ImportHelper
from .PathManager import import_paths, export_paths
from .utils_bpy import pcoll


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
    bl_label = 'Import Pedestrian Paths'
    filename_ext = '.p3dxml'
    filter_glob: bpy.props.StringProperty(default='*.p3dxml',
                                          options={
                                              'HIDDEN'},
                                          maxlen=255)

    def execute(self, context):
        result_message = import_paths(self.filepath)
        if result_message != 'OK':
            self.report(type={'ERROR'}, message=result_message)
            return {'FINISHED'}
        else:
            return {'FINISHED'}


class FileExportPaths(bpy.types.Operator, ExportHelper):
    bl_idname = 'export_scene.paths_p3dxml'
    bl_label = 'Export Pedestrian Paths'
    filename_ext = '.p3dxml'
    filter_glob: bpy.props.StringProperty(default='*.p3dxml',
                                          options={
                                              'HIDDEN'},
                                          maxlen=255)
    selected_only: bpy.props.BoolProperty(name='Export Selected Paths Only',
                                          description='Only export selected path objects',
                                          default=False)

    def execute(self, context):
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
        result = export_paths(self.filepath, objs)
        if result == 0:
            self.report({'WARNING', "No paths exported"})
        else:
            self.report({'INFO'}, f"Successfully exported {result} paths to {self.filepath}")
        return {'FINISHED'}


class PathCreate(bpy.types.Operator):
    bl_idname = 'object.path_create'
    bl_label = 'Create a Path'

    def execute(self, context):
        print('nothing was done')
        return {
            'FINISHED'}


class PathDelete(bpy.types.Operator):
    bl_idname = 'object.path_delete'
    bl_label = 'Delete this path'

    def execute(self, context):
        print('nothing was done')
        return {
            'FINISHED'}


class PathModule:

    @classmethod
    def poll(cls, context):
        return context.preferences.addons["map_data_editor"].preferences.PathsEnabled


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
        box = layout.box()
        grd = box.grid_flow(row_major=True, align=True)
        grd.label(text="#TODO")
        # TODO actually make path operators
