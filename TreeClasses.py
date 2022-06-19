from email.policy import default
import bpy
from time import time
from bpy.props import *
from bpy_extras.io_utils import ExportHelper, ImportHelper
from . import TreeManager as TM
from os import path
from .utils_p3dxml import *

def GetMarkersCollection(context):
    if "IntersectMarkers" not in context.scene.collection.children:
            marker_col = bpy.data.collections.new("IntersectMarkers")
            context.scene.collection.children.link(marker_col)
    else:
        marker_col = context.scene.collection.children["IntersectMarkers"]
    return marker_col

class LoadIntersectPoints(bpy.types.Operator, ImportHelper):
    """Load Intersect markers from p3dxml that contains Intersect (0x3F00003) chunks"""
    bl_idname = 'import_scene.intersect_points'
    bl_label = "Load Intersect Markers"
    filename_ext = '.p3dxml'
    filter_glob: bpy.props.StringProperty(default='*.p3dxml',
                                          options={'HIDDEN'},
                                          maxlen=255)
    def execute(self, context):
        marker_col = GetMarkersCollection(context)
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


class CreateMarkersFromMeshOperator(bpy.types.Operator):
    """Create intersect markers from selected mesh objects via raycasts from 20x20 grid.\n(CAN BE VERY SLOW FOR HUGE MESHES\nUse in such case "Create Markers Grid From Meshes")"""
    bl_idname = "object.create_intersect_markers_from_mesh"
    bl_label = "Create Markers From Meshes (Ray Cast)"
    bl_options = {'REGISTER'}

    #check that we actually have mesh objects selected
    @classmethod
    def poll(cls, context):
        return context.selected_objects and 'MESH' in [x.type for x in context.selected_objects]
         

    def execute(self, context):
        marker_col = GetMarkersCollection(context)
        
        mesh_objs = [x for x in context.selected_objects if x.type == 'MESH']

        depsgraph = context.evaluated_depsgraph_get()
        #mesh_objs = [x.evaluated_get(depsgraph) for x in mesh_objs]

        markers_locs = TM.create_markers_from_meshes(mesh_objs,depsgraph)
        for loc in markers_locs:
            a = bpy.data.objects.new("iMarker", None)
            a.location = loc
            marker_col.objects.link(a)
        return {'FINISHED'}

class CreateMarkersGridFromMeshOperator(bpy.types.Operator):
    """Create simple 20x20 XY grid of markers bounding the mesh"""
    bl_idname = "object.create_intersect_markers_grid_from_mesh"
    bl_label = "Create Markers Grid From Meshes"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects and 'MESH' in [x.type for x in context.selected_objects]

    
    individual: bpy.props.BoolProperty(
        name="Use Individual Meshes",
        description="Use individual object's bounds to create multiple grids",
        default=False,
    )

    select_markers: bpy.props.BoolProperty(
        name="Select Created Markers",
        default = False,
    )

    def execute(self, context):
        marker_col = GetMarkersCollection(context)
        mesh_objs = [x for x in context.selected_objects if x.type == 'MESH']

        markers_locs = TM.create_markers_grid_from_meshes(mesh_objs, individual=self.individual)

        if self.select_markers:
            for x in context.selected_objects:
                x.select_set(False)
        for loc in markers_locs:
            a = bpy.data.objects.new("iMarker", None)
            a.location.xy = loc
            marker_col.objects.link(a)
            if self.select_markers:
                a.select_set(True)
        return {'FINISHED'}

class ResetMarkers(bpy.types.Operator):
    """Reset intersect markers"""
    bl_idname = "object.reset_intersect_markers"
    bl_label = "Reset Intersect Markers"
    bl_options = {'REGISTER'}

    def execute(self, context):
        markers_col = GetMarkersCollection(context)
        for obj in markers_col.objects:
            bpy.data.objects.remove(obj)
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
        name = "Grid Cell Size",
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
        layout = self.layout
        layout.operator('import_scene.intersect_points', icon='IMPORT')
        layout.operator('object.create_intersect_markers_grid_from_mesh', icon='MESH_GRID')
        layout.operator('object.create_intersect_markers_from_mesh', icon='SHADERFX')
        layout.operator('object.reset_intersect_markers', icon='TRASH')
        layout.operator('export_scene.grid_tree', icon='EXPORT')

to_register = [
    GridTreeExport,
    LoadIntersectPoints,
    CreateMarkersGridFromMeshOperator,
    CreateMarkersFromMeshOperator,
    ResetMarkers,
    MDE_PT_TreeFileManagment,
]