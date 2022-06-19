import bpy
from bpy_extras.io_utils import ExportHelper, ImportHelper
from .utils_bpy import reminder
from .FenceManager import *


class FileImportFences(bpy.types.Operator, ImportHelper):
    bl_idname = 'import_scene.fences_p3dxml'
    bl_label = 'Import Fences...'
    filename_ext = '.p3dxml'
    filter_glob: bpy.props.StringProperty(
        default='*.p3dxml',
        options={'HIDDEN'},
        maxlen=255,
        )

    def execute(self, context):
        fence_objs = import_fences(self.filepath)
        for obj in fence_objs:
            get_fence_collection(context).objects.link(obj)
        return {'FINISHED'}


class FileExportFences(bpy.types.Operator, ExportHelper):
    bl_idname = 'export_scene.fences_p3dxml'
    bl_label = 'Export Fences...'
    filename_ext = '.p3dxml'
    filter_glob: bpy.props.StringProperty(
        default='*.p3dxml',
        options={'HIDDEN'},
        maxlen=255,
        )
    selected_only: bpy.props.BoolProperty(
        name='Selected Only',
        description='Only export selected fences',
        default=False,
        )

    def execute(self, context):
        if self.selected_only:
            objs = context.selected_objects
            if not objs:
                self.report({'ERROR_INVALID_INPUT'}, 'No Fences selected!')
                return {'CANCELLED'}
        else:
            if 'Fences' not in bpy.data.collections:
                self.report({'ERROR'}, 'No "Fences" collection found')
                return {'CANCELLED'}
            objs = bpy.data.collections['Fences'].objects
        result = export_fences(self.filepath, objs)
        if result:
            self.report({'INFO'}, f"Successfully exported {len(objs)} fences")
        else:
            self.report({'WARNING'}, f"Successfully exported {len(objs)} fences but some reported errors, check console for details")
        return {'FINISHED'}


class FenceCreate(bpy.types.Operator):
    bl_idname = 'object.fence_create'
    bl_label = 'Create Basic Fence'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        fence_obj = fence_create(context.scene.cursor.location, context.scene.cursor.location + Vector((10,30,0)))
        get_fence_collection(context).objects.link(fence_obj)
        fence_obj.select_set(True)
        context.view_layer.objects.active = fence_obj
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}


class FenceFlip(bpy.types.Operator):
    bl_idname = 'object.fence_flip'
    bl_label = 'Flip Fences'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return fence_flippable(context.object)

    def execute(self, context):
        for obj in context.selected_objects:
            if fence_flippable(obj):
                fence_flip(obj)
        return {'FINISHED'}


# class FenceRip(bpy.types.Operator):
#     bl_idname = 'object.fence_rip'
#     bl_label = 'Rip Poly Curve'

#     @classmethod
#     def poll(cls, context):
#         objs = context.selected_objects
#         if not objs:
#             return False
#         for ob in objs:
#             if ob.type != 'CURVE':
#                 return False
#             if ob.data.splines[0].type != 'POLY':
#                 return False
#         return True

#     def execute(self, context):
#         rip_polys_to_fences(context.selected_objects)
#         return{'FINISHED'}


# class FenceApplyTran(bpy.types.Operator):
#     bl_idname = 'object.fence_apply_tran'
#     bl_label = 'Apply Fence Transforms'

#     @classmethod
#     def poll(cls, context):
#         if not context.selected_objects:
#             return False
#         for ob in context.selected_objects:
#             if ob.type != 'CURVE':
#                 return False
#         return True

#     def execute(self, context):
#         bpy.ops.object.mode_set(mode='OBJECT')
#         objs = context.selected_objects
#         for fobj in objs:
#             fobj.data.dimensions = '3D'
#         bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
#         for fobj in objs:
#             fobj.data.dimensions = '2D'
#         return{'FINISHED'}


class FenceModule:
    @classmethod
    def poll(cls, context):
        return context.preferences.addons[__package__].preferences.FencesEnabled


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
        col = layout.column()
        col.prop((context.area.spaces[0].overlay), 'show_face_orientation', text='Display Face Orientation', icon='NORMALS_FACE')
        col.operator((FenceCreate.bl_idname), icon='PLUS')
        col.operator((FenceFlip.bl_idname), icon='UV_SYNC_SELECT')

to_register = [
    FenceCreate,
    FenceFlip,
    FileExportFences,
    FileImportFences,
    MDE_PT_FenceFileManagement,
    MDE_PT_Fences,
]