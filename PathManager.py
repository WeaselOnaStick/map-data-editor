import bmesh
import bpy
from .utils_bpy import *
from .utils_p3dxml import *
from . import utils_math


def path_create():
    pass


def get_paths_collection():
    if 'Paths' not in bpy.context.scene.collection.children:
        paths_collection = bpy.data.collections.new('Paths')
        bpy.context.scene.collection.children.link(paths_collection)
    else:
        paths_collection = bpy.data.collections['Paths']
    return paths_collection


def import_paths(filepath):
    bpy.ops.object.select_all(action='DESELECT')
    root = terra_read(filepath)
    paths_collection = get_paths_collection()
    if not find_chunks(root, PAT):
        return "No path chunks found in the file"
    for path in find_chunks(root, PAT):
        locs = []
        for vert in path.findall('Value/*'):
            locs.append(item_to_vector(vert).to_4d())
        path_curve = bpy.data.curves.new(name='Path', type='CURVE')
        path_spline = path_curve.splines.new(type='POLY')
        path_spline.points.add(len(locs)-1)
        for i, vert in enumerate(locs):
            path_spline.points[i].co = vert
        path_object = bpy.data.objects.new('Path', path_curve)
        paths_collection.objects.link(path_object)
        path_object.select_set(True)
        path_object.show_wire = True
        path_object.show_in_front = True
    bpy.context.view_layer.objects.active = path_object
    return 'OK'


def export_paths(filepath, objs):
    root = p3d_et()
    counter = 0
    for path in objs:
        chunk = write_chunk(root, PAT)
        pos = ET.SubElement(chunk, 'Value', Name='Positions')
        verts = [x.co for x in path.data.splines[0].points]
        for v in verts:
            ET.SubElement(pos, 'Item', X=(str(v.x)), Y=(str(v.z)), Z=(str(v.y)))
        counter += 1
    write_ET(root, filepath)
    return counter


def path_create_circular(cursor, kwargs):
    paths_collection = get_paths_collection()
    path_curve = bpy.data.curves.new(name='Path', type='CURVE')
    path_spline = path_curve.splines.new(type='POLY')
    path_spline.points.add(kwargs['resolution'])
    spline_pts = utils_math.build_circle(**kwargs, origin=cursor.location.copy())
    for i, spline_point in enumerate(spline_pts):
        path_spline.points[i].co = spline_point.to_4d()
    path_object = bpy.data.objects.new('Path', path_curve)
    paths_collection.objects.link(path_object)
    path_object.select_set(True)
    bpy.context.view_layer.objects.active = path_object
    path_object.show_wire = True
    path_object.show_in_front = True
