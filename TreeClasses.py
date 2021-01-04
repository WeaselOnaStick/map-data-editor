import bpy
from time import time
from bpy.props import *
from bpy_extras.io_utils import ExportHelper, ImportHelper
from . import TreeManager as TM
from os import path
from .utils_p3dxml import *

class FileExportTree(bpy.types.Operator, ExportHelper):
    bl_idname = 'export_scene.tree_p3dxml'
    bl_label = 'Export Tree'
    filename_ext = '.p3dxml'
    filter_glob: bpy.props.StringProperty(default='*.p3dxml',
                                          options={'HIDDEN'},
                                          maxlen=255)

    def execute(self, context):
        return {'FINISHED'}

class LoadIntersectPoints(bpy.types.Operator, ImportHelper):
    """Select a p3dxml file that contains Intersect (0x3F00003) chunks"""
    bl_idname = 'import_scene.intersect_points'
    bl_label = "Load intersect markers"
    filename_ext = '.p3dxml'
    filter_glob: bpy.props.StringProperty(default='*.p3dxml',
                                          options={'HIDDEN'},
                                          maxlen=255)
    def execute(self, context):
        if "IntersectMarkers" not in context.scene.collection.children:
            marker_col = bpy.data.collections.new("IntersectMarkers")
            context.scene.collection.children.link(marker_col)
        else:
            marker_col = context.scene.collection.children["IntersectMarkers"]
        root = terra_read(self.filepath)
        for i in find_chunks(root, "0x3F00003"):
            bbox = find_chunks(i, "0x10003")[0]
            if find_xyz(bbox, "Low").xy not in [j.location.xy for j in marker_col.objects]:
                a = bpy.data.objects.new("iMarker", None)
                a.location = find_xyz(bbox, "Low")
                marker_col.objects.link(a)
            if find_xyz(bbox, "High").xy not in [j.location.xy for j in marker_col.objects]:
                b = bpy.data.objects.new("iMarker", None)
                b.location = find_xyz(bbox, "High")
                marker_col.objects.link(b)
        return {'FINISHED'}                                    

class GridTreeExport(bpy.types.Operator, ExportHelper):
    """Generate Tree based on Intersect Markers"""
    bl_idname = "export_scene.grid_tree"
    bl_label = "Generate Grid Tree"
    bl_description = "Generate Grid Tree"

    filename_ext = '.p3dxml'
    filter_glob: bpy.props.StringProperty(default='*.p3dxml',
                                          options={'HIDDEN'},
                                          maxlen=255)

    grid_size: bpy.props.FloatProperty(
        name = "(!) Grid Cell Size",
        description = "Don't change unless you know what you're doing!",
        default = 20,
    )

    def execute(self, context):
        if "IntersectMarkers" not in context.scene.collection.children or not context.scene.collection.children["IntersectMarkers"].objects:
            self.report({'ERROR'}, "No Intersect Markers found!")
            return {"CANCELLED"}
        t_start = time()
        t = TM.grid_generate(marker_set = [x.location for x in context.scene.collection.children["IntersectMarkers"].objects], gridsize = self.grid_size)
        TM.export_tree(t, self.filepath)
        a = t.root.children_count()
        b = time() - t_start
        self.report({'INFO'}, f"Finished exporting {a} Node Tree in {b:.3f} secs")
        print(f"Finished exporting {a} Node Tree in {b:.3f} secs")
        return {"FINISHED"}



class MiscModule:
    @classmethod
    def poll(cls, context):
        return context.preferences.addons[__package__].preferences.MiscEnabled

class MDE_PT_TreeFileManagment(bpy.types.Panel, MiscModule):
    bl_label = "Tree Generation"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WMDE Misc'
    bl_order = 6
    
    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text='', icon='GRID')

    def draw(self, context):
        #TODO have panel that displays current tree basic info. split grid_tree into tree *creation* and tree *export*
        #TODO maybe add "visualize tree" operator for "fun"
        layout = self.layout
        layout.operator('import_scene.intersect_points', icon='IMPORT')
        layout.operator('export_scene.grid_tree', icon='EXPORT')
        #layout.operator('object.dummy', icon='MONKEY')

