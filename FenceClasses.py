import bpy
from bpy_extras.io_utils import ExportHelper, ImportHelper
from .utils_bpy import reminder
from .FenceManager import *


class FileImportFences(bpy.types.Operator, ImportHelper):
    bl_idname = 'import_scene.fences_p3dxml'
    bl_label = 'Import Fences'
    filename_ext = '.p3dxml'
    filter_glob: bpy.props.StringProperty(default='*.p3dxml',
                                          options={
                                              'HIDDEN'},
                                          maxlen=255)

    def execute(self, context):
        import_fences(self.filepath)
        return {
            'FINISHED'}


class FileExportFences(bpy.types.Operator, ExportHelper):
    bl_idname = 'export_scene.fences_p3dxml'
    bl_label = 'Export Fences'
    filename_ext = '.p3dxml'
    filter_glob: bpy.props.StringProperty(default='*.p3dxml',
                                          options={
                                              'HIDDEN'},
                                          maxlen=255)
    selected_only: bpy.props.BoolProperty(name='Export Selected Fences Only',
                                          description='Only export selected fences',
                                          default=False)
    safe_check: bpy.props.BoolProperty(name='Check Fence Validity',
                                       description='Check if the Fences are valid blender objects',
                                       default=True)

    def execute(self, context):
        if self.selected_only:
            objs = context.selected_objects
            if not objs:
                self.report({'ERROR_INVALID_INPUT'}, 'No Fences selected!')
                return {
                    'CANCELLED'}
        else:
            if 'Fences' not in bpy.data.collections:
                self.report({'ERROR'}, 'No "Fences" collection found')
                return {
                    'CANCELLED'}
            objs = bpy.data.collections['Fences'].objects
        if self.safe_check:
            if invalid_fences(objs):
                self.report({'ERROR'}, invalid_fences(objs))
                return {
                    'CANCELLED'}
        export_fences(self.filepath, objs)
        self.report(
            {'INFO'}, f"Successfully exported {len(objs)} Fences to {self.filepath}")
        return {
            'FINISHED'}


class FenceCreateFromCurve(bpy.types.Operator):
    bl_idname = 'object.fence_curve_finalize'
    bl_label = 'Finalize fence curve'

    @classmethod
    def poll(cls, context):
        return bool(invalid_fences(context.selected_objects))

    def execute(self, context):
        curve_to_fences(context.selected_objects)
        return {'FINISHED'}


class FenceCreate(bpy.types.Operator):
    bl_idname = 'object.fence_create'
    bl_label = 'Create a Base Fence'
    bl_options = {'REGISTER', 'UNDO'}
    end: bpy.props.FloatVectorProperty(
        name='Relative End Point',
        size=2,
        subtype='XYZ',
        default=(10, 30),
    )

    def execute(self, context):
        fence_create(
            context.scene.cursor.location,
            context.scene.cursor.location + self.end.to_3d())
        return {'FINISHED'}


class FenceFlip(bpy.types.Operator):
    bl_idname = 'object.fence_flip'
    bl_label = 'Flip Selected Fences'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        objs = [x.users_collection[0].name ==
                'Fences' for x in context.selected_objects]
        return all(objs) and objs

    def execute(self, context):
        for obj in context.selected_objects:
            fence_flip(obj)

        return {'FINISHED'}


class FenceModule:

    @classmethod
    def poll(cls, context):
        return context.preferences.addons["map_data_editor"].preferences.FencesEnabled


class MDE_PT_FenceFileManagement(bpy.types.Panel, FenceModule):
    bl_label = 'File Management'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WMDE Fences'
    bl_order = 0

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text='', icon='FILE')

    def draw(self, context):
        layout = self.layout
        layout.operator('import_scene.fences_p3dxml', icon='IMPORT')
        layout.operator('export_scene.fences_p3dxml', icon='EXPORT')


class MDE_PT_Fences(bpy.types.Panel, FenceModule):
    bl_label = 'Fences'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WMDE Fences'
    bl_order = 4

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text='', icon='FILE_FONT')

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop((context.area.spaces[0].overlay), 'show_face_orientation', text='Display Fence Orientation')
        col = layout.column()
        col.operator((FenceCreate.bl_idname), icon='PLUS')
        col.operator((FenceFlip.bl_idname), icon='UV_SYNC_SELECT')
        col.operator((FenceCreateFromCurve.bl_idname), icon='OUTLINER_OB_CURVE')
