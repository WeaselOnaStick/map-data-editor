#import bmesh
import bpy

from .utils_bpy import *
from .utils_p3dxml import *
from mathutils import *

def get_fence_collection(context):
    if 'Fences' not in context.scene.collection.children:
        fence_collection = bpy.data.collections.new('Fences')
        context.scene.collection.children.link(fence_collection)
    else:
        fence_collection = bpy.data.collections['Fences']
    return fence_collection

def fence_create(a=Vector((0, 0, 0)), b=Vector((15, 15, 0))):
    """Returns a curve object with single spline made of points a,b"""
    a.z = 0
    b.z = 0
    fc = bpy.data.curves.new('Fence', 'CURVE')
    fc.dimensions = '2D'
    fc.extrude = 50
    fcs = fc.splines.new('POLY')
    fcs.points.add(1)
    fcs.points[0].co = a.to_4d()
    fcs.points[1].co = b.to_4d()
    fcs.use_endpoint_u = True
    fcs.use_smooth = False
    fco = bpy.data.objects.new('Fence', fc)
    fco.lock_rotation = [True,True,False] # Prevent fences from being rotated on XY axis
    return fco


def fence_flip(obj):
    for spline in obj.data.splines:
        pts = spline.points
        for i in range(len(pts)//2):
            a = pts[i].co.copy()
            b = pts[-i-1].co.copy()
            pts[i].co = b
            pts[-i-1].co = a


def import_fences(filepath):
    """Returns a list of fence objs"""
    fences = []
    root = terra_read(filepath)
    for fence in find_chunks(root, FEN):
        fence_data = list(fence)[0]
        fences.append(fence_create(find_xyz(fence_data, 'Start'), find_xyz(fence_data, 'End')))
    return fences

def fence_flippable(obj : bpy.types.Object):
    return obj is not None and obj.type == 'CURVE' and obj.data.splines

def export_fences(filepath, objs):
    """If found 'faulty' fences were True"""
    no_faults = True
    root = p3d_et()
    for obj in objs:
        obj = bpy.types.Object(obj)
        if not obj.data.splines: 
            continue
        if obj.modifiers:
            no_faults = False
            print(f"{obj.name} has modifiers. Result may be unexpected")
        MW = Matrix(obj.matrix_world)
        if MW.to_euler().x != 0 or MW.to_euler().y != 0:
            no_faults = False
            print(f"{obj.name} has non-zero XY rotation! Result may be unexpected")
        for spline in obj.data.splines:
            spline = bpy.types.Spline(spline)
            for i in range(1,len(spline.points)):
                fen = write_chunk(root, FEN)
                fen2 = write_chunk(fen, FEN2)
                start = obj.matrix_world @ spline.points[i-1].co.to_3d()
                end = obj.matrix_world @ spline.points[i].co.to_3d()
                start.z = 0
                end.z = 0
                no = (end - start).cross(Vector((0, 0, 1))).normalized()
                no.z = 0
                no.negate()
                write_xyz(fen2, 'Start', *start)
                write_xyz(fen2, 'End', *end)
                write_xyz(fen2, 'Normal', *no)

    write_ET(root, filepath)
    return no_faults
