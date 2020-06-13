import bmesh
import bpy

from .utils_bpy import *
from .utils_p3dxml import *


def fence_create(a=Vector((0, 0, 0)), b=Vector((15, 15, 0))):
    a.z = 0
    b.z = 0
    if 'Fences' not in bpy.context.scene.collection.children:
        fence_collection = bpy.data.collections.new('Fences')
        bpy.context.scene.collection.children.link(fence_collection)
    else:
        fence_collection = bpy.data.collections['Fences']
    fc = bpy.data.curves.new('Fence', 'CURVE')
    fc.dimensions = '2D'
    fc.extrude = 50
    fcs = fc.splines.new('NURBS')
    fcs.points.add(1)
    fcs.points[0].co = a.to_4d()
    fcs.points[1].co = b.to_4d()
    fcs.use_endpoint_u = True
    fco = bpy.data.objects.new('Fence', fc)
    fence_collection.objects.link(fco)


def fence_flip(obj):
    p = obj.data.splines[0].points
    a = p[0].co.copy()
    b = p[1].co.copy()
    p[0].co = b
    p[1].co = a


def curve_to_fences(objs):
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for obj in objs:
        for spline in obj.data.splines:
            sp_points = [x.co for x in spline.points] + \
                [x.co for x in spline.bezier_points]
            for i in range(len(sp_points) - 1):
                fence_create(sp_points[i], sp_points[(i + 1)])

        bpy.data.objects.remove(obj)


def import_fences(filepath):
    root = terra_read(filepath)
    for fence in find_chunks(root, FEN):
        fence_data = list(fence)[0]
        fence_create(find_xyz(fence_data, 'Start'),
                     find_xyz(fence_data, 'End'))


def invalid_fences(objs):
    naughty = []
    for ob in objs:
        if ob.type != 'CURVE':
            naughty.append(f"{ob.name} is not a CURVE object")
            continue
        if ob.users_collection[0].name != 'Fences':
            naughty.append(f'{ob.name} is not inside "Fences" collection')
            continue
        if len(ob.data.splines) != 1:
            naughty.append(f"{ob.name} has {len(ob.data.splines)} splines instead of 1")
            continue
        if len(ob.data.splines[0].points) != 2:
            naughty.append(f"{ob.name} has {len(ob.data.splines[0].points)} spline points instead of 2")
            continue
        if ob.data.splines[0].type != 'NURBS':
            naughty.append(f"{ob.name}\'s spline type is not \"NURBS\" ")
            continue

    if not naughty:
        return False
    return '\n'.join(naughty)


def export_fences(filepath, objs):
    root = p3d_et()
    for obj in objs:
        fen = write_chunk(root, FEN)
        fen2 = write_chunk(fen, FEN2)
        start = obj.data.splines[0].points[0].co.copy().to_3d()
        end = obj.data.splines[0].points[1].co.copy().to_3d()
        start.z = 0
        end.z = 0
        no = (end - start).cross(Vector((0, 0, 1))).normalized()
        no.z = 0
        no.negate()
        write_xyz(fen2, 'Start', *start)
        write_xyz(fen2, 'End', *end)
        write_xyz(fen2, 'Normal', *no)

    write_ET(root, filepath)
