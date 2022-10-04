from collections import Counter
from datetime import date
import bpy
from bpy.props import *
from bpy_extras.io_utils import ExportHelper, ImportHelper
from .utils_bpy import *
from . import RoadManager
from .RoadManager import GetIntersections, GetIntersectionsCollection, inter_create, r_create, rs_create_base
from math import radians, dist
from .utils_bpy import pcoll, get_connected_faces, get_connected_verts
import mathutils
import os

RoadPropsExposed = [
    #'to_export', 
    'inter_start', 
    'inter_end', 
    'lanes', 
    'max_cars', 
    'speed', 
    'intel', 
    'short', 
    'unknown',
    ]


class RoadPropGroup(bpy.types.PropertyGroup):
    to_export: bpy.props.BoolProperty(
        name='Is a SHAR road',
        description='Marks current collection as a SHAR Road node\nIf enabled, this collection is gonna get exported',
        default=False,
        )
    def is_valid_intersection(self, object):
        return is_intersection(object, bpy.context)
    inter_start: bpy.props.PointerProperty(
        name='Start Intersection',
        type=bpy.types.Object,
        poll=is_valid_intersection,
        )
    inter_end: bpy.props.PointerProperty(
        name='End Intersection',
        type=bpy.types.Object,
        poll=is_valid_intersection,
        )
    lanes: bpy.props.IntProperty(
        name='Lanes',
        description='How many lanes are actually in this road. Soft maxed',
        default=1,
        min=1,
        soft_max=5,
        )
    max_cars: bpy.props.IntProperty(
        name='Maximum Cars',
        description='Maximum amount of traffic cars to be spawned here',
        default=5,
        min=0,
        )
    speed: bpy.props.IntProperty(
        name='Speed',
        description='Even though the .p3d file contains this data, Radical does not use this value.\nExpect something in new Mod Launcher update. Soft maxed',
        default=50,
        min=0,
        )
    intel: bpy.props.IntProperty(
        name='Intelligence',
        description='How much intellect AI car must have to use this road',
        default=0,
        min=0,
        max=50,
        )
    short: bpy.props.BoolProperty(
        description='Defines if a car can be spawned here on restart',
        name='Shortcut',
        default=False,
        )
    unknown: bpy.props.IntProperty(
        description='Radical always uses 0 for this value. No idea what it does. (if anything)',
        name='Unknown 4',
        default=0,
        )


class FileImportRoads(bpy.types.Operator, ImportHelper):
    bl_idname = 'import_scene.roads_p3dxml'
    bl_label = 'Import Roads...'
    filename_ext = '.p3dxml'
    filter_glob: bpy.props.StringProperty(
        default='*.p3dxml',
        options={'HIDDEN'},
        maxlen=255,
        )
    try_sort: bpy.props.BoolProperty(
        name='Try to sort',
        description='Attempt to sort imported road nodes based on first 2 characters in the name',
        default=True,
        )

    def execute(self, context):
        RoadManager.import_roads_and_intersections(self.filepath, self.try_sort, context)
        return {'FINISHED'}


class FileExportRoadsAndIntersects(bpy.types.Operator, ExportHelper):
    #TODO Export CustomLimits.ini limits
    #TODO Export CustomRoadBehaviour xml(?)
    #TODO "Visible only" checkbox
    #TODO! safety checks (no intersections, no roads, None intersections in roads etc.)
    bl_idname = 'export_scene.roads_p3dxml'
    bl_label = 'Export Roads...'
    filename_ext = '.p3dxml'
    filter_glob: bpy.props.StringProperty(
        default='*.p3dxml',
        options={'HIDDEN'},
        maxlen=255,
        )
    selected_only: bpy.props.BoolProperty(
        name='Selected Only',
        description='Only export Road Networks that have selected shapes and only selected intersections',
        default=False,
        )
    safe_check: bpy.props.BoolProperty(
        name='Check Validity',
        description='Check if the Road Network is valid before exporting\nNot fully crash-proof',
        default=True,
        )
    connect_margin: bpy.props.FloatProperty(
        name='Validity Margin',
        description='Value used to determine if road shapes are properly connected to their intersections',
        default=1.5,
        min=0,
        )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "selected_only")
        layout.prop(self, "safe_check")
        row = layout.row()
        row.prop(self, "connect_margin")
        row.enabled = context.active_operator.properties.safe_check

    def execute(self, context):
        road_cols = []
        inter_objs = []
        if self.selected_only:
            for obj in context.selected_objects:
                if obj.type == 'MESH' and obj.users_collection[0].road_node_prop.to_export and obj.users_collection[0] not in road_cols:
                    road_cols.append(obj.users_collection[0])
                if is_intersection(obj,context):
                    inter_objs.append(obj)
        else:
            road_cols = [x for x in bpy.data.collections if x.road_node_prop.to_export and x.objects]
            inter_objs = [x for x in bpy.data.collections['Intersections'].objects if x.users_collection]
        
        if self.safe_check:
            if RoadManager.invalid_roads(road_cols, inter_objs, self.connect_margin):
                self.report({'ERROR'}, RoadManager.invalid_roads(
                    road_cols, inter_objs, self.connect_margin))
                return {'CANCELLED'}
        self.report({'INFO'}, 'Safe check passed')
        RoadManager.export_roads_and_intersects(self.filepath, road_cols, inter_objs)
        self.report(
            {'INFO'}, f"Successfully exported {os.path.basename(self.filepath)}")
        return {'FINISHED'}

class IntersectCreate(bpy.types.Operator):
    """Create a road intersection"""
    bl_idname = 'object.intersect_create'
    bl_label = 'Create Intersection'
    bl_options = {'REGISTER', 'UNDO'}
    name: bpy.props.StringProperty(
        name='Intersection Name',
        default='wzIntersection',
        )
    radius: bpy.props.FloatProperty(
        description='Radius of the intersection',
        name='Radius',
        min=0,
        default=3,
        )
    road_beh: bpy.props.IntProperty(
        description="3 - traffic doesn't stop\n1 - traffic stops before going through (emulates irl traffic lights)\n0 - used primarily in bonus game tracks\n2,4 - unknown",
        name='Road behaviour',
        min=0,
        max=4,
        default=1,
        )
    location: bpy.props.FloatVectorProperty(
        name='Location',
        subtype='XYZ',
        unit='LENGTH',
        options={'HIDDEN'},
        )

    def invoke(self, context, event):
        self.location = context.scene.cursor.location
        return self.execute(context)

    def execute(self, context):
        int_obj = RoadManager.inter_create(self.name, self.location, self.radius, self.road_beh, GetIntersectionsCollection(context))
        int_obj.show_name = context.window_manager.intersection_names_visible
        return {'FINISHED'}

def is_intersection(object : bpy.types.Object, context):
    return object is not None and object.type == 'EMPTY' and object.empty_display_type == 'SPHERE' and object.users_collection[0] == GetIntersectionsCollection(context)

class IntersectionsCreateAtFaces(bpy.types.Operator):
    """Automatically create intersections at selected faces"""
    bl_idname = 'object.intersect_create_at_faces'
    bl_label = 'Create Intersections At Faces'
    bl_options = {'REGISTER', 'UNDO'}

    rad_methods_enum = [
        ("MAX",     "Maximum",  "",0),
        ("MIN",     "Minimum",  "",1),
        ("AVG",     "Average",  "",2),
        ("CONST",   "Constant", "",3)
    ]
    rad_method: bpy.props.EnumProperty(
        items=rad_methods_enum,
        name="Radius Calculation Method",
        default='MAX',
    )
    rad_const: bpy.props.FloatProperty(
        name = "Constant Radius",
        default=20,
        min=0,
        soft_min=0.005,
    )

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH'

    def execute(self, context):
        target_obj = context.object
        og_mode = str(target_obj.mode)
        target_mesh = bpy.types.Mesh(target_obj.data)
        if og_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        for poly in target_mesh.polygons:
            if not poly.select : continue
            if      self.rad_method == 'MAX':
                r = max([(target_obj.matrix_world @ target_mesh.vertices[x].co - target_obj.matrix_world @ poly.center).length for x in poly.vertices])
            elif    self.rad_method == 'MIN':
                r = min([(target_obj.matrix_world @ target_mesh.vertices[x].co - target_obj.matrix_world @ poly.center).length for x in poly.vertices])
            elif    self.rad_method == 'AVG':
                r = sum([(target_obj.matrix_world @ target_mesh.vertices[x].co - target_obj.matrix_world @ poly.center).length for x in poly.vertices])/len(poly.vertices[:])
            elif    self.rad_method == 'CONST':
                r = self.rad_const
            inter_create("wzIntersection", target_obj.matrix_world @ poly.center, r, 1, GetIntersectionsCollection(context))
        bpy.ops.object.mode_set(mode = og_mode)
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, "rad_method")
        if self.rad_method == 'CONST':
            col.prop(self, "rad_const")

class RoadEditOperator:

    @classmethod
    def poll(cls, context):
        if get_current_road_collection(context):
            return get_current_road_collection(context).road_node_prop.to_export
        else:
            return False


class RShapeEditOperator:
    """RShapeEditOperator"""

    @classmethod
    def poll(cls, context):
        return bool(get_current_road_collection(context))


class RoadCreate(bpy.types.Operator):
    """Create new road collection"""
    bl_idname = 'object.road_create'
    bl_label = 'Create New Road Collection'
    road_name: bpy.props.StringProperty(name='Base Road Name',default='wzRoadNode')
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        RoadManager.r_create(context, self.road_name)
        return {'FINISHED'}


class RoadDelete(bpy.types.Operator, RoadEditOperator):
    """Delete current road and all its shapes"""
    bl_idname = 'object.road_delete'
    bl_label = 'Delete This Road Collection'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.data.collections.remove(get_current_road_collection(context))
        return {'FINISHED'}


class RoadDuplicate(bpy.types.Operator, RoadEditOperator):
    """Duplicate current road with all its shapes"""
    bl_idname = 'object.road_duplicate'
    bl_label = 'Duplicate This Road Collection'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        old_col = get_current_road_collection(context)
        new_col = old_col.copy()
        get_col_parent(old_col).children.link(new_col)
        for obj in new_col.objects:
            new_col.objects.unlink(obj)

        for i, ob in enumerate(old_col.all_objects):
            ob_data = ob.data
            n_ob = ob.copy()
            n_ob.data = ob_data.copy()
            new_col.objects.link(n_ob)

        for obj in context.selected_objects:
            obj.select_set(False)

        for obj in new_col.all_objects:
            obj.select_set(True)

        return {'FINISHED'}


class RoadCreateAdjacent(bpy.types.Operator, RoadEditOperator): #Dirty macro
    """Create a new road, shift it adjacently and flip its direction"""
    bl_idname = 'object.road_create_adjacent'
    bl_label = 'Create Adjacent Road'
    bl_options = {'REGISTER', 'UNDO'}
    direction: bpy.props.BoolProperty(name='To Right', default=True)

    def execute(self, context):
        bpy.ops.object.road_shape_select()
        bpy.ops.object.road_duplicate()
        bpy.ops.object.road_shape_shift_adjacent(direction=(self.direction))
        bpy.ops.object.road_shape_flip()
        return {'FINISHED'}


class RoadSeparate(bpy.types.Operator, RShapeEditOperator):
    """Create a new road and move selected shapes into it"""
    bl_idname = 'object.road_separate'
    bl_label = 'Separate by Selection'

    @classmethod
    def poll(cls, context):
        if get_current_road_collection(context):
            return not all([x.select_get() for x in get_current_road_collection(context).objects]) and RShapeEditOperator.poll(context)
        else:
            return False

    def execute(self, context):
        new_obj = list(context.selected_objects)
        old_col = get_current_road_collection(context)
        new_col = old_col.copy()
        get_col_parent(old_col).children.link(new_col)
        for obj in new_col.all_objects:
            new_col.objects.unlink(obj)

        for ob in new_obj:
            new_col.objects.link(ob)
            old_col.objects.unlink(ob)

        return {'FINISHED'}

class RoadCreateFromSelectedQuads(bpy.types.Operator):
    """Select a continuous strip of quads in any mesh and create a new road from them"""
    bl_idname = 'object.road_create_from_quads'
    bl_label = 'New Road From Selected Quads'
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH'

    def execute(self, context):
        #Not advised to refactor this inside RoadManager.py

        target_obj = context.object
        target_mesh = bpy.types.Mesh(target_obj.data)
        og_mode = str(target_obj.mode)
        if og_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        polys = [x for x in target_mesh.polygons if x.select]
        edges = [x for x in target_mesh.edges if x.select]
        active_poly = target_mesh.polygons[target_mesh.polygons.active]

        # handle invalid input
        if not polys:
            self.report({'ERROR_INVALID_INPUT'}, "No faces selected")
            bpy.ops.object.mode_set(mode = og_mode)
            return {'CANCELLED'}

        if not all([len(x.vertices) == 4 for x in polys]):
            self.report({'ERROR_INVALID_INPUT'}, "Non-Quad faces selected")
            bpy.ops.object.mode_set(mode = og_mode)
            return {'CANCELLED'}

        if len(polys) == 1:
            road_collection = r_create(context)
            rs_create_base(road_collection,*[target_mesh.vertices[x].co @ target_obj.matrix_world for x in polys[0].vertices[:]])
            return {'FINISHED'}


        qverts = [] #Quad Verts
        for x in polys:
            qverts += x.vertices[:]        
        qverts_c = Counter(qverts) #Quad Verts Counted
        single_qverts = [x for x in qverts_c if qverts_c[x] == 1]

        if set(qverts_c.values()) != {1,2} or len(single_qverts) != 4:
            self.report({'ERROR_INVALID_INPUT'}, "Disconnected strip of quads selected")
            bpy.ops.object.mode_set(mode = og_mode)
            return {'CANCELLED'}

        if not any([x in single_qverts for x in active_poly.vertices[:]]):
            self.report({'ERROR_INVALID_INPUT'}, "Active quad not at the start of the strip")
            bpy.ops.object.mode_set(mode = og_mode)
            return {'CANCELLED'}

        road_quads = []
        
        def quad_process(road_quads, p : bpy.types.MeshPolygon, a : int, d : int, b = None, c = None):
            if b is None or c is None:
                b = (set(get_connected_verts(a, edges)) & set(p.vertices[:]) - {a,d}).pop()
                c = (set(get_connected_verts(d, edges)) & set(p.vertices[:]) - {a,d}).pop()
            road_quads.append(tuple([target_obj.matrix_world @ target_mesh.vertices[x].co for x in (a,b,c,d)]))
            return b,c

        #find first quad points + orientation
        #find id of last quad
        a,d = None, None
        poly_s, poly_e = active_poly, None #polygon at the Start and End
        a,d = set(single_qverts) & set(poly_s.vertices[:])
        a_co = target_mesh.vertices[a].co
        d_co = target_mesh.vertices[d].co
        aa = (set(get_connected_verts(a, edges)) & set(poly_s.vertices[:]) - {a,d}).pop()
        aa_co = target_mesh.vertices[aa].co
        if ((d_co-a_co).cross(aa_co-a_co)).dot(poly_s.normal) < 0:
            a,d = d,a
        a,d = quad_process(road_quads, poly_s, a, d)
        
        poly_e = [x for x in polys if any([y in single_qverts for y in x.vertices[:]]) and x != active_poly][0]

        #poly_cur = get_connected_faces(poly_s, polys)[0]
        poly_cur = poly_s
        polys_travelled = {poly_s}
        while poly_cur != poly_e:
            poly_cur = (set(get_connected_faces(poly_cur, polys)) - polys_travelled).pop()
            polys_travelled.add(poly_cur)
            a,d = quad_process(road_quads, poly_cur, a, d)

        #keep finding connected+selected polys until it's ID matches that of last quad
        if len(road_quads) != len(polys):
            self.report({'WARNING'}, "Something's wrong...")

        #loop over added quads, create road shapes and add them to road collection
        #print(road_quads)
        
        #create road collection

        road_collection = r_create(context)
        for q_co in road_quads:
            rs_create_base(road_collection,*q_co)
        
        bpy.ops.object.mode_set(mode = og_mode)

        return {'FINISHED'}


class RoadsAutoConnect(bpy.types.Operator):
    """Automatically select the closest intersections to the road's first and last shape.\nMake sure vertices overlap and road node collection only has valid road shapes!"""
    bl_idname = "object.roads_auto_connect"
    bl_label = "Auto-Assign Intersections"
    bl_options = {'REGISTER', 'UNDO'}

    target_filters_enum = [
        ("ALL", "All", "Affect all road nodes in master collection", 0),
        ("ACTIVE", "Only Active Node", "Affect only currently active node indicated on the side bar", 1),
        ("VISIBLE", "Only Visible Nodes", "Affect all road nodes in master collection that aren't hidden", 2),
        ("SELECT", "Nodes With Selected Shapes", "Affect road nodes if any of their road shapes are selected", 3),
    ]
    target_filter : bpy.props.EnumProperty(
        name = "Roads To Connect",
        items = target_filters_enum,
        #default='ALL',
        default='ACTIVE',
    )
    error_margin : bpy.props.FloatProperty(
        name='Error Margin',
        description='Error margin for checking if road shapes are connected',
        min=0,
        soft_min=0.0001,
        default=0.05
    )

    def execute(self, context):

        inters_dict = {inter : inter.location for inter in GetIntersectionsCollection(context).objects}
        
        if self.target_filter == 'ALL':
            target_roads = RoadManager.GetRoadsCollection(context).children
        elif self.target_filter == 'ACTIVE':
            target_roads = [get_current_road_collection(context)]
        elif self.target_filter == 'VISIBLE':
            target_roads = [x for x in RoadManager.GetRoadsCollection(context).children if not (context.view_layer.layer_collection.children['Road Nodes'].children[x.name].hide_viewport or x.hide_viewport)]
        elif self.target_filter == 'SELECT':
            target_roads = [x for x in RoadManager.GetRoadsCollection(context).children if any([y.select_get() for y in x.objects])]

        for road in target_roads:
            start_shape, end_shape = None, None

            # get first and last road shapes
                # count each A and B vert (in world coordinates)
                # first road shape is shape with A that only appears once
                # last  road shape is shape with B that only appears once

            for rshape in road.objects:
                a_stick, b_stick = False, False # A or B has "sticky" overlapping verts other than themselves
                a = rshape.matrix_world @ rshape.data.vertices[0].co
                b = rshape.matrix_world @ rshape.data.vertices[2].co

                for other_rshape in road.objects:
                    if rshape == other_rshape: continue

                    ao = other_rshape.matrix_world @ other_rshape.data.vertices[0].co
                    bo = other_rshape.matrix_world @ other_rshape.data.vertices[2].co

                    if (bo-a).length < self.error_margin:
                        a_stick = True
                    if (ao-b).length < self.error_margin:
                        b_stick = True
                    
                    #rshape is definitely in the middle
                    if (a_stick, b_stick) == (True, True):
                        break
                        
                if      (a_stick, b_stick) == (True, True):
                    continue
                elif    (a_stick, b_stick) == (True, False):
                    end_shape = rshape
                elif    (a_stick, b_stick) == (False, True):
                    start_shape = rshape

                

            
            if start_shape is None or end_shape is None:
                self.report({'ERROR'}, "Something went wrong. Make sure road shapes have been updated and margin isn't too small")
                return {'CANCELLED'}

            start_co = (start_shape.matrix_world    @ start_shape.data.vertices[0].co   + start_shape.matrix_world  @ start_shape.data.vertices[6].co)/2
            end_co   = (end_shape.matrix_world      @ end_shape.data.vertices[0].co     + end_shape.matrix_world    @ end_shape.data.vertices[6].co)/2

            #print('-------------DEBUG------------')
            #print(start_co.xyz)
            #print(end_co.xyz)
            # assign inter closest to first road shape as start
            # assign inter closest to last road shape as end


            
            road.road_node_prop.inter_start = sorted(inters_dict.items(), key= lambda x: (x[1]-start_co).length)[0][0]
            road.road_node_prop.inter_end = sorted(inters_dict.items(), key= lambda x: (x[1]-end_co).length)[0][0]

        #self.report({'WARNING'}, "WIP")
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        col = layout.grid_flow()
        r = col.row()
        r.label(text='Roads To Connect: ')
        r = col.row()
        r.prop(self, 'target_filter', text='')
        if self.target_filter == 'ALL':
            n = len(RoadManager.GetRoadsCollection(context).children)
        elif self.target_filter == 'ACTIVE':
            n = 1
        elif self.target_filter == 'VISIBLE':
            n = len([x for x in RoadManager.GetRoadsCollection(context).children if not (context.view_layer.layer_collection.children['Road Nodes'].children[x.name].hide_viewport or x.hide_viewport)])
        elif self.target_filter == 'SELECT':
            n = len([x for x in RoadManager.GetRoadsCollection(context).children if any([y.select_get() for y in x.objects])])
        col.prop(self, "error_margin")
        col.label(text=f"(This will affect {n} road node{'s' if n != 1 else ''})")

#CANCELLED (??)

# class RoadsBatchEditProps(bpy.types.Operator):
#     bl_idname = "object.roads_batch_edit_props"
#     bl_label = "Batch Properties Edit"
#     bl_options = {'REGISTER', 'UNDO'}

#     new_road_props = bpy.props.PointerProperty(type=RoadPropGroup)

#     def execute(self, context):
#         self.report({'WARNING'}, "WIP")
#         return {'FINISHED'}

#     def invoke(self, context, event):
#         wm = context.window_manager
#         return wm.invoke_props_dialog(self)

#     def draw(self, context):
#         layout = self.layout
#         col = layout.column()
#         col.label(text='LOLOLOLOLOL')
#         col.prop(self, "new_road_props")


class RShapeAddOperator:
    """RShapeAddOperator"""

    @classmethod
    def poll(cls, context):
        if get_current_road_collection(context):
            return get_current_road_collection(context).road_node_prop.to_export
        else:
            return False

class RShapeSelect(bpy.types.Operator):
    """Select/Deselect all road shapes of current road"""
    bl_idname = 'object.road_shape_select'
    bl_label = 'De-/Select Linked Road Shapes'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not get_current_road_collection(context):
            return False
        else:
            return get_current_road_collection(context).road_node_prop.to_export and get_current_road_collection(context).objects

    def execute(self, context):
        if all([x.select_get() for x in get_current_road_collection(context).objects]):
            n_des = False
        else:
            n_des = True
        for obj in get_current_road_collection(context).objects:
            obj.select_set(n_des)

        return {'FINISHED'}


class RShapeUpdate(bpy.types.Operator, RShapeEditOperator):
    """Update support geometry of selected road shapes"""
    bl_idname = 'object.road_shape_update'
    bl_label = 'Update Road Shapes'

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        if context.active_object.type != 'MESH' or (len(context.active_object.users_collection) > 1) or (not context.active_object.users_collection[0].road_node_prop.to_export):
            self.report({'ERROR'}, "Please change active object to a valid road shape object")
            return {'CANCELLED'}
        objects = context.selected_objects
        for obj in objects:
            if obj.type != 'MESH': obj.select_set(False)
        bpy.ops.object.transform_apply()
        for obj in objects:
            if obj.type != 'MESH':
                continue
            else:
                RoadManager.rs_edit_upd(obj)
        return {'FINISHED'}


class RShapeCreateElliptic(bpy.types.Operator, RShapeAddOperator):
    """Create a set of roadshapes forming an ellipse"""
    bl_idname = 'object.road_shape_create_elliptic'
    bl_label = 'Create Elliptic Road'
    bl_options = {'REGISTER', 'UNDO'}
    angle: bpy.props.FloatProperty(
        description='Angle of the curve',
        name='Angle',
        soft_min=(-360),
        soft_max=360,
        precision=1,
        step=5,
        subtype='ANGLE',
        default=(radians(90)))
    radius: bpy.props.FloatProperty(
        description='Radius of the curve',
        name='Radius',
        min=0,
        default=24)
    resolution: bpy.props.IntProperty(
        description='Amount of road shapes in a curve',
        name='Quality',
        min=2,
        soft_max=20,
        default=6)
    width: bpy.props.FloatProperty(
        description='Entire width of the road',
        name='Width',
        min=0.001,
        soft_max=12,
        default=6)
    scale: bpy.props.FloatVectorProperty(
        name='Scale along',
        min=0.001,
        subtype='XYZ',
        default=(1, 1, 0))
    offset: bpy.props.FloatVectorProperty(
        name='offset along',
        subtype='XYZ',
        unit='LENGTH')

    def execute(self, context):
        RoadManager.rs_create_ellip(get_current_road_collection(context), self.as_keywords())
        return {'FINISHED'}


class RShapeCreateStraight(bpy.types.Operator, RShapeAddOperator):
    """Create a set of roadshapes in a straight line"""
    bl_idname = 'object.road_shape_create_straight'
    bl_label = 'Create Straight Road'
    bl_options = {'REGISTER', 'UNDO'}
    loc: bpy.props.FloatVectorProperty(
        name='Location',
       subtype='XYZ',
       unit='LENGTH',
       )
    rot: bpy.props.FloatVectorProperty(
        name='Rotation',
        subtype='EULER',
        unit='ROTATION',
        )
    resolution: bpy.props.IntProperty(
        description='Amount of road shapes in an array',
        name='Quality',
        min=1,
        soft_max=20,
        default=5,
        )
    width: bpy.props.FloatProperty(
        description='Entire width of the road',
        name='Width',
        min=0.001,
        soft_max=4,
        default=6,
        unit='LENGTH',
        )
    length: bpy.props.FloatProperty(
        description='Entire length of the road',
        name='Length',
        min=0.001,
        default=30,
        unit='LENGTH',
        )

    def invoke(self, context, event):
        self.loc_x = context.scene.cursor.location.x
        self.loc_y = context.scene.cursor.location.y
        self.loc_z = context.scene.cursor.location.z
        return self.execute(context)

    def execute(self, context):
        RoadManager.rs_create_straight(get_current_road_collection(context), context, self.as_keywords())
        return {'FINISHED'}


class RShapePrepareCurve(bpy.types.Operator, RShapeAddOperator):
    """RShapePrepareCurve"""
    bl_idname = 'object.road_shape_prepare_bezier'
    bl_label = 'Prepare Bezier Road'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curve_obj = RoadManager.misc_create_bezier(context)
        get_current_road_collection(context).objects.link(curve_obj)
        for obj in context.selected_objects:
            obj.select_set(False)
        context.view_layer.objects.active = curve_obj
        curve_obj.select_set(True)
        return {'FINISHED'}

def ContextIsRCurve(context):
    if not context.selected_objects:
        return False
    if len(context.selected_objects) != 1:
        return False
    if context.selected_objects[0].type != 'CURVE':
        return False
    if context.object.data.extrude == 0.0:
        return False
    if context.object.data.dimensions != '3D':
        return False
    if len(context.object.data.splines) != 1:
        return False
    if context.object.data.splines[0].type != 'BEZIER':
        return False
    return True


class RShapeFinalizeCurve(bpy.types.Operator):
    """RShapeFinalizeCurve"""
    bl_idname = 'object.road_shape_finalize_bezier'
    bl_label = 'Finalize Bezier Road'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return ContextIsRCurve(context)

    def execute(self, context):
        bpy.ops.object.mode_set(mode='OBJECT')
        RoadManager.rs_create_from_bezier(context)
        return {'FINISHED'}


class RShapeShiftAdjacent(bpy.types.Operator, RShapeEditOperator):
    bl_idname = 'object.road_shape_shift_adjacent'
    bl_label = 'Shift Adjacent'
    bl_options = {'REGISTER', 'UNDO'}
    direction: bpy.props.BoolProperty(name='To Right',
                                      default=True)

    def execute(self, context):
        objects = context.selected_objects
        for obj in objects:
            if obj.type != 'MESH':
                continue
            else:
                RoadManager.rs_edit_shift_adjacent(obj, self.direction)

        return {'FINISHED'}


class RShapeShift(bpy.types.Operator, RShapeEditOperator):
    bl_idname = 'object.road_shape_shift'
    bl_label = 'Shift'
    bl_options = {'REGISTER', 'UNDO'}
    distance: bpy.props.FloatProperty(name='Distance', subtype='DISTANCE', unit='LENGTH')

    def execute(self, context):
        objects = context.selected_objects
        objl = len(objects)
        for obj in objects:
            if obj.type != 'MESH':
                continue
            else:
                RoadManager.rs_edit_shift(obj, self.distance)

        context.view_layer.objects.active = objects[0]
        objects[0].select_set(True)
        return {'FINISHED'}

    def invoke(self, context, event):
        v = context.selected_objects[0].data.vertices
        self.distance = (v[(-1)].co - v[0].co).length * 2
        return self.execute(context)


class RShapeAdjustWidth(bpy.types.Operator, RShapeEditOperator):
    bl_idname = 'object.road_shape_adjust_width'
    bl_label = 'Adjust Width'
    bl_options = {'REGISTER', 'UNDO'}
    delta: bpy.props.FloatProperty(name='Adjust width by', subtype='DISTANCE', unit='LENGTH', default=0.3)

    pivots = [
        ("LEFT", "Left", "", "TRIA_RIGHT", 0),
        ("CENTER", "Center", "", "ARROW_LEFTRIGHT", 1),
        ("RIGHT", "Right", "", "TRIA_LEFT", 2)
    ]
    pivot: bpy.props.EnumProperty(items=pivots, name="pivot side", default='CENTER')

    def execute(self, context):
        objects = context.selected_objects
        for obj in objects:
            RoadManager.rs_edit_width(obj, self.delta, self.pivot)
        return {'FINISHED'}

    def invoke(self, context, event):
        v = context.selected_objects[0].data.vertices
        self.distance = (v[(-1)].co - v[0].co).length * 2
        return self.execute(context)


class RShapeFlip(bpy.types.Operator, RShapeEditOperator):
    """RShapeFlip"""
    bl_idname = 'object.road_shape_flip'
    bl_label = 'Flip Direction'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        cur_col = get_current_road_collection(context)
        all_shapes_selected = all([x.select_get() for x in cur_col.objects])
        if cur_col.road_node_prop.inter_start is not None:
            if cur_col.road_node_prop.inter_end is not None:
                if all_shapes_selected:
                    cur_col.road_node_prop.inter_start, cur_col.road_node_prop.inter_end = cur_col.road_node_prop.inter_end, cur_col.road_node_prop.inter_start
        objects = context.selected_objects
        to_select = None
        objl = len(objects)
        for i, obj in enumerate(objects):
            if obj.type != 'MESH':
                continue
            elif i > objl:
                break
            else:
                RoadManager.rs_edit_flip(shape_obj=obj)

        return {'FINISHED'}


class RoadModule:
    @classmethod
    def poll(cls, context):
        return context.preferences.addons[__package__].preferences.RoadsEnabled


class MDE_PT_RoadFileManagement(bpy.types.Panel, RoadModule):
    bl_label = 'File Management'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WMDE Roads'
    bl_order = 0

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text='', icon='FILE')

    def draw(self, context):
        layout = self.layout
        layout.operator(FileImportRoads.bl_idname, icon='IMPORT')
        layout.operator(FileExportRoadsAndIntersects.bl_idname, icon='EXPORT')


class MDE_PT_Intersections(bpy.types.Panel, RoadModule):
    bl_label = 'Intersections'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WMDE Roads'
    bl_order = 1

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text=' ', icon='SPHERE')

    def draw(self, context):
        layout = self.layout
        layout.operator(IntersectCreate.bl_idname, icon='PLUS')
        layout.operator(IntersectionsCreateAtFaces.bl_idname, icon='FACESEL')
        if context.window_manager.intersection_names_visible:
            layout.prop(context.window_manager, "intersection_names_visible", text="Intersection Names ON", icon='HIDE_OFF')
        else:
            layout.prop(context.window_manager, "intersection_names_visible", text="Intersection Names OFF", icon='HIDE_ON')
        if context.object and is_intersection(context.object, context):
            layout.prop(context.object, 'scale', index=0, text='Radius')
            layout.prop(context.object, 'inter_road_beh')


class MDE_PT_Roads(bpy.types.Panel, RoadModule):
    bl_label = "Road Nodes"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WMDE Roads'
    bl_order = 2

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(icon='AUTO')
        row.label(text="  ", icon='OPTIONS')

    def draw(self, context):
        layout = self.layout
        layout.operator(RoadCreate.bl_idname, icon='PLUS')
        layout.operator(RoadCreateFromSelectedQuads.bl_idname, icon='FACESEL')
        layout.operator(RoadsAutoConnect.bl_idname, icon='SHADERFX')
        
        cur_road_col = get_current_road_collection(context)
        if not cur_road_col:
            layout.label(text="No Road Node Detected")
            return
        layout.label(text=f"{cur_road_col.name} ({len(cur_road_col.objects)} Shapes)")
        layout.operator(RoadDelete.bl_idname, icon='TRASH')
        layout.operator(RoadDuplicate.bl_idname, icon='DUPLICATE')
        layout.operator(RoadCreateAdjacent.bl_idname, icon='UV_ISLANDSEL')
        layout.operator(RoadSeparate.bl_idname, icon='UNLINKED')
        box = layout.box()
        box.label(text=f"Road properties:", icon='PROPERTIES')
        grid = box.grid_flow(row_major=True)
        if cur_road_col.road_node_prop.to_export:
            for road_prop in RoadPropsExposed:
                if road_prop in ['inter_start', 'inter_end']:
                    col = grid.column()
                    col.prop(cur_road_col.road_node_prop, road_prop)
                else:
                    grid.prop(cur_road_col.road_node_prop, road_prop)
                if road_prop == 'inter_end':
                    if cur_road_col.road_node_prop.inter_start == cur_road_col.road_node_prop.inter_end:
                        warning_box = grid.box()
                        warning_box.label(text="Start and End Match!", icon = 'ERROR')
                        warning_box.label(text="This causes the game to crash!")
                    if cur_road_col.road_node_prop.inter_start is None or not is_intersection(cur_road_col.road_node_prop.inter_start, context):
                        warning_box = grid.box()
                        warning_box.label(text="Invalid Start Intersection!", icon = 'ERROR')
                        warning_box.label(text="This causes the game to crash!")
                    if cur_road_col.road_node_prop.inter_end is None or not is_intersection(cur_road_col.road_node_prop.inter_end, context):
                        warning_box = grid.box()
                        warning_box.label(text="Invalid End Intersection!", icon = 'ERROR')
                        warning_box.label(text="This causes the game to crash!")
        elif cur_road_col.name not in ['Intersections', 'Master Collection']:
            grid.prop(cur_road_col.road_node_prop, "is_shar_road")


class MDE_PT_RoadShapes(bpy.types.Panel, RoadModule):
    bl_label = 'Road Shapes'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WMDE Roads'
    bl_order = 3

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(icon='AUTO')
        row.label(text='', icon='EDITMODE_HLT')

    def draw(self, context):
        layout = self.layout
        cur_road_col = get_current_road_collection(context)
        if not cur_road_col:
            layout.label(text="No Road Node Detected")
            return
        grd = layout.grid_flow()
        grd.label(text='Editing')
        grd.operator(RShapeSelect.bl_idname, icon='RESTRICT_SELECT_OFF')
        grd.operator(RShapeUpdate.bl_idname, icon='FILE_REFRESH')
        grd.operator(RShapeAdjustWidth.bl_idname, icon='ARROW_LEFTRIGHT')
        grd.operator(RShapeFlip.bl_idname, icon='UV_SYNC_SELECT')
        grd.operator(RShapeShift.bl_idname, icon='PAUSE')
        grd.operator(RShapeShiftAdjacent.bl_idname, icon='FRAME_NEXT')
        grd = layout.grid_flow()
        grd.label(text='Creating')
        grd.operator(RShapeCreateStraight.bl_idname, icon_value=(pcoll['RSHAPE_SINGLE'].icon_id))
        grd.operator(RShapeCreateElliptic.bl_idname, icon='CURVE_NCIRCLE')
        box = layout.box()
        box.label(text='Create bezier', icon='MOD_CURVE')
        col = box.column()
        col.operator(RShapePrepareCurve.bl_idname, icon='CURVE_DATA')
        if ContextIsRCurve(context):
            rcurve_prop = col.column_flow()
            rcurve_prop.prop((context.object.data), 'resolution_u', text='Quality')
            rcurve_prop.prop((context.object.data), 'extrude', text='Width')
            rcurve_prop.operator(RShapeFinalizeCurve.bl_idname, icon='OUTLINER_OB_CURVE')


to_register = [
    FileExportRoadsAndIntersects,
    FileImportRoads,
    IntersectCreate,
    IntersectionsCreateAtFaces,
    MDE_PT_Intersections,
    MDE_PT_RoadFileManagement,
    MDE_PT_RoadShapes,
    MDE_PT_Roads,
    RShapeAdjustWidth,
    RShapeCreateElliptic,
    RShapeCreateStraight,
    RShapeFinalizeCurve,
    RShapeFlip,
    RShapePrepareCurve,
    RShapeSelect,
    RShapeShift,
    RShapeShiftAdjacent,
    RShapeUpdate,
    RoadCreate,
    RoadCreateFromSelectedQuads,
    RoadsAutoConnect,
    RoadCreateAdjacent,
    RoadDelete,
    RoadDuplicate,
    RoadPropGroup,
    RoadSeparate,
    ]