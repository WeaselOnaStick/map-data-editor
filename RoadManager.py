from math import pi
from time import time
import bpy
import bmesh
import bpy_extras.object_utils
from . import utils_math
from .utils_p3dxml import *
add_object = bpy_extras.object_utils.object_data_add


def inter_create(inter_name, position, radius, behaviour):
    if 'Intersections' not in bpy.data.collections:
        int_col = bpy.data.collections.new('Intersections')
        bpy.context.scene.collection.children.link(int_col)
    else:
        int_col = bpy.data.collections['Intersections']
    inter = bpy.data.objects.new(inter_name, None)
    inter.inter_road_beh = behaviour
    inter.empty_display_type = 'SPHERE'
    ad = inter.animation_data_create()
    dr = ad.drivers.new('empty_display_size')
    dr.driver.type = 'SCRIPTED'
    dr.driver.expression = '1'
    dsy = ad.drivers.new('scale', index=1)
    dsy.driver.type = 'SCRIPTED'
    dsy.driver.use_self = True
    dsy.driver.expression = 'self.scale[0]'
    dsz = ad.drivers.new('scale', index=2)
    dsz.driver.type = 'SCRIPTED'
    dsz.driver.use_self = True
    dsz.driver.expression = 'self.scale[0]'
    inter.location = position
    inter.scale[0] = radius
    int_col.objects.link(inter)
    return inter


def r_create(context, road_name):
    if 'Road Nodes' not in bpy.data.collections:
        road_col = bpy.data.collections.new('Road Nodes')
        bpy.context.scene.collection.children.link(road_col)
    else:
        road_col = bpy.data.collections['Road Nodes']
    col = bpy.data.collections.new(road_name)
    col.road_node_prop.to_export = True
    road_col.children.link(col)
    layer_col = context.view_layer.layer_collection.children['Road Nodes'].children[col.name]
    context.view_layer.active_layer_collection = layer_col
    return col


def r_import(name, start_inter, end_inter, lanes, max_cars, speed, intel, short, unknown, try_sort=False):
    """same as r_create but for predefined roads such as imported ones. Adds the road to master/Road Nodes collection"""
    col = bpy.data.collections.new(name)
    props = col.road_node_prop
    props.to_export = True
    props.inter_start = bpy.data.objects[start_inter]
    props.inter_end = bpy.data.objects[end_inter]
    props.lanes = lanes
    props.max_cars = max_cars
    props.speed = speed
    props.intel = intel
    props.short = short
    props.unknown = unknown
    if 'Road Nodes' not in bpy.data.collections:
        road_col = bpy.data.collections.new('Road Nodes')
        bpy.context.scene.collection.children.link(road_col)
    else:
        road_col = bpy.data.collections['Road Nodes']
    if try_sort:
        zone = name[:2]
        if zone in bpy.data.collections:
            road_col = bpy.data.collections[zone]
        else:
            road_col = bpy.data.collections.new(zone)
            bpy.data.collections['Road Nodes'].children.link(road_col)
    road_col.children.link(col)
    return col


def rs_create_base(collection, a=None, b=None, c=None, d=None, name='RoadShape'):
    M = bpy.data.meshes.new(name)
    loc = a
    r_v = [Vector(), (b - a) / 2, b - a, b + (c - b) / 2 - a, c - a, c + (d - c) / 2 - a, d - a, d + (a - d) / 2 - a]
    r_f = [(0, 1, 3, 7), (1, 2, 3), (3, 4, 5), (3, 5, 6, 7)]
    M.from_pydata(r_v, [], r_f)
    M.update()
    r_obj = bpy.data.objects.new(name, M)
    r_obj.location = loc
    collection.objects.link(r_obj)
    r_obj.show_in_front = True
    r_obj.display_type = 'WIRE'
    r_obj.show_all_edges = True
    return r_obj


def rs_create_straight(collection, context, kwargs):
    points = utils_math.create_straight(start=(context.scene.cursor.location + kwargs['loc']),
                                        rotation=(kwargs['rot']),
                                        resolution=(kwargs['resolution']),
                                        width=(kwargs['width']),
                                        length=(kwargs['length']))
    for i, vvvv in enumerate(points):
        rs_create_base(collection, *vvvv, name=f"StraightRoadShape{i}")


def rs_create_ellip(collection, args):
    for i, vvvv in enumerate((utils_math.build_arc)(**args, **{'origin': bpy.context.scene.cursor})):
        rs_create_base(collection, *vvvv, **{'name': f"EllipticRoadShape{i}"})


def rs_create_from_bezier(context):
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.convert(target='MESH', keep_original=False)
    leftover_mesh = context.object
    points = bpy.context.selected_objects[0].data.vertices
    points = utils_math.curve_mesh_to_road([x.co for x in points])
    for shape in points:
        rs_create_base(context.object.users_collection[0], *shape)

    bpy.data.objects.remove(leftover_mesh)


def misc_create_bezier(context, collection):
    curve = bpy.data.curves.new('BezierRoadShape', 'CURVE')
    curve.dimensions = '3D'
    spline = curve.splines.new('BEZIER')
    spline.bezier_points.add(1)
    bzp = spline.bezier_points
    bzp[0].handle_left = Vector((-7.1884, -12.703, 0.0))
    bzp[0].co = Vector((-4.3203, -9.7527, 0.0))
    bzp[0].handle_right = Vector((-1.4522, -6.8024, 0.0))
    bzp[0].tilt = pi / 2
    bzp[1].handle_left = Vector((0.0, -4.1146, 0.0))
    bzp[1].co = Vector((0.0, 0.0, 0.0))
    bzp[1].handle_right = Vector((-0.0, 4.1146, 0.0))
    bzp[1].tilt = pi / 2
    curve.extrude = 3
    curve_obj = bpy.data.objects.new('BezierRoadShape', curve)
    collection.objects.link(curve_obj)
    curve_obj.display_type = 'WIRE'
    curve_obj.show_in_front = True
    curve_obj.location = context.scene.cursor.location #< Fixed "prepare bezier curve" operator to place curve at cursor (See previous commit, oops)


def rs_edit_upd(obj):
    """takes an object then fixes support verts and sets origin to zero'th vert"""
    verts = [x.co for x in obj.data.vertices]
    if verts[0] != Vector():
        fix = Vector(verts[0])
        for i in range(len(verts)):
            obj.data.vertices[i].co = obj.data.vertices[i].co - fix

        obj.data.update()
        obj.location += fix
    verts[1] = (verts[2] + verts[0]) / 2
    verts[3] = (verts[2] + verts[4]) / 2
    verts[5] = (verts[4] + verts[6]) / 2
    verts[7] = (verts[6] + verts[0]) / 2
    for i in range(len(verts)):
        obj.data.vertices[i].co = verts[i]

    obj.data.update()


def rs_edit_width(shape_obj, delta, pivot):
    newlocs = utils_math.edit_width(*[x.co.copy() for x in shape_obj.data.vertices][::2], delta, pivot)
    for i, v in enumerate(newlocs):
        shape_obj.data.vertices[i*2].co = v
    rs_edit_upd(shape_obj)


def rs_edit_flip(shape_obj):
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    verts = shape_obj.data.vertices
    t = Vector(verts[0].co)
    verts[0].co = verts[4].co
    verts[4].co = t
    shape_obj.data.update()
    t = Vector(verts[2].co)
    verts[2].co = verts[6].co
    verts[6].co = t
    shape_obj.data.update()
    rs_edit_upd(shape_obj)


def rs_edit_shift_adjacent(shape_obj, direction=False):
    rs_edit_upd(shape_obj)
    locs = [x.co.copy() for x in list(shape_obj.data.vertices)[::2]]
    locs = list((utils_math.create_adjacent)(*locs, **{'right': direction}))
    for i in range(len(locs)):
        shape_obj.data.vertices[(i * 2)].co = locs[i]

    rs_edit_upd(shape_obj)


def rs_edit_shift(shape_obj, distance):
    rs_edit_upd(shape_obj)
    locs = [x.co.copy() for x in list(shape_obj.data.vertices)[::2]]
    locs = list((utils_math.create_shifted)(*locs, **{'distance': distance}))
    for i in range(len(locs)):
        shape_obj.data.vertices[(i * 2)].co = locs[i]

    rs_edit_upd(shape_obj)


def rs_evaluate_verts(road_shape):
    """Takes road shape mesh object. returns list of verts in global space"""
    locs = []
    for i in [0, 2, 4, 6]:
        locs.append(road_shape.matrix_world @ road_shape.data.vertices[i].co)
    return locs


def import_roads_and_intersections(filepath, try_sort):
    root = terra_read(filepath)
    import_intersects(root)
    import_roads(root, try_sort)


def import_roads(root, try_sort):
    time_start = time()
    road_counter = 0
    road_shape_counter = 0
    all_road_shapes = chunks_to_dict_by_name(find_chunks(root, RDS))
    all_roads = find_chunks(root, ROA)
    for road in all_roads:
        road_counter += 1
        r_name = find_val(road, 'Name')
        start_inter = find_val(road, 'StartIntersectionLocatorNode')
        end_inter = find_val(road, 'EndIntersectionLocatorNode')
        max_cars = int(find_val(road, 'MaximumCars'))
        speed = int(find_val(road, 'Unknown2'))
        intel = int(find_val(road, 'Unknown3'))
        unkown = int(find_val(road, 'Unknown4'))
        noreset = int(find_val(road, 'NoReset'))
        lanes = False
        r_col = r_import(r_name, start_inter, end_inter, 2, max_cars, speed, intel, noreset, unkown, try_sort=try_sort)
        for road_seg in find_chunks(road, RSG):
            road_shape_counter += 1
            road_seg_name = find_val(road_seg, 'CubeShape')
            a = find_xyz_from_transform_mat(road_seg)
            b = a + find_xyz(all_road_shapes[road_seg_name], 'Position')
            c = a + find_xyz(all_road_shapes[road_seg_name], 'Position2')
            d = a + find_xyz(all_road_shapes[road_seg_name], 'Position3')
            if not lanes:
                lanes = int(find_val(all_road_shapes[road_seg_name], 'Lanes'))
            rs_create_base(r_col, a, b, c, d, name=road_seg_name)

        r_col.road_node_prop.lanes = lanes

    print(f"Imported {road_counter} Roads and {road_shape_counter} Road Shapes in {time() - time_start:.3f} seconds")


def import_intersects(root):
    time_start = time()
    inter_counter = 0
    for i in find_chunks(root, INS):
        inter_counter += 1
        name = find_val(i, 'Name')
        pos = find_xyz(i, 'Position')
        rad = float(find_val(i, 'Radius'))
        beh = int(find_val(i, 'TrafficBehaviour'))
        if name not in bpy.data.objects:
            inter_create(name, pos, rad, beh)

    print(f"Imported {inter_counter} Intersections in {time() - time_start:.3f} seconds")


def invalid_roads(road_cols, inter_objs, margin):
    print("\tChecking intersection validity")
    check = roads_have_invalid_intersections(road_cols)
    if check:
        return check
    print("\tChecking graph validity")
    check = roads_are_disconnected(road_cols, inter_objs)
    if check:
        return check
    print("\tChecking connection validity")
    check = roads_improperly_connected(road_cols, margin)
    if check:
        return check
    return False


def roads_are_disconnected(road_cols, inter_objs):
    graph = {}
    for inter in inter_objs:
        nbrs = set()
        for node in [x for x in road_cols if inter in [x.road_node_prop.inter_start, x.road_node_prop.inter_end]]:
            if inter.name == node.road_node_prop.inter_start:
                nbrs.add(node.road_node_prop.inter_end.name)
            else:
                nbrs.add(node.road_node_prop.inter_start.name)

        graph[inter.name] = nbrs

    if utils_math.is_connected(graph):
        return False
    else:
        return 'The following island is disconnected from the rest of the network: ' + utils_math.is_connected(graph)


def roads_have_invalid_intersections(road_cols):
    invalid_roads = []
    for rc in road_cols:
        if rc.road_node_prop.inter_start is None or rc.road_node_prop.inter_end is None or rc.road_node_prop.inter_start.name == rc.road_node_prop.inter_end.name:
            invalid_roads.append(rc.name)
    if not invalid_roads:
        return False
    return str('Following road nodes have invalid intersections ' + ', '.join(invalid_roads))


def roads_improperly_connected(road_cols, margin=1.5):
    faulty_nodes = {}
    for node in road_cols:
        all_verts = []
        connected = [0, 0]
        int_start = node.road_node_prop.inter_start
        int_end = node.road_node_prop.inter_end
        for x in node.objects:
            all_verts += rs_evaluate_verts(x)

        for x in all_verts:
            if (x - int_start.location).length <= int_start.scale[0] + margin:
                connected[0] += 1
                if (x - int_start.location).length - int_start.scale[0] > margin:
                    margin = (x - int_start.location).length - int_start.scale[0]

        for x in all_verts:
            if (x - int_end.location).length <= int_end.scale[0] + margin:
                connected[1] += 1
                if (x - int_end.location).length - int_end.scale[0] > margin:
                    margin = (x - int_end.location).length - int_end.scale[0]

        if connected != [2, 2]:
            if connected[0] < 2:
                faulty_nodes[node.name] = ' @ Start Intersection'
            elif connected[1] < 2:
                faulty_nodes[node.name] = ' @ End Intersection'
            elif connected[0] < 2 and connected[1] < 2:
                faulty_nodes[node.name] = ' @ Both Start and End Intersections'

    if not faulty_nodes:
        return False
    else:
        faulty_nodes = '\n'.join([x + str(faulty_nodes.get(x)) for x in faulty_nodes])
        return str(f"Following road nodes are not properly connected to their corresponding intersection(s):\n{faulty_nodes}")


def export_roads_and_intersects(filepath, road_cols, inter_objs):
    root = p3d_et()
    for inter_ob in inter_objs:
        inter_et = write_chunk(root, INS)
        write_val(inter_et, 'Name', inter_ob.name)
        write_xyz(inter_et, 'Position', *inter_ob.location)
        write_val(inter_et, 'Radius', inter_ob.scale[0])
        write_val(inter_et, 'TrafficBehaviour', inter_ob.inter_road_beh)

    for node_col in road_cols:
        locs = []
        for road_ob in node_col.objects:
            rs_edit_upd(road_ob)
            dat_seg = write_chunk(root, RDS)
            points = rs_evaluate_verts(road_ob)
            points = [points[0], *[x - points[0] for x in points[1:]]]
            write_val(dat_seg, 'Name', road_ob.name)
            write_val(dat_seg, 'Lanes', node_col.road_node_prop.lanes)
            write_xyz(dat_seg, 'Position', *points[1])
            write_xyz(dat_seg, 'Position2', *points[2])
            write_xyz(dat_seg, 'Position3', *points[3])
            locs.append(points[0])

        node_et = write_chunk(root, ROA)
        write_val(node_et, 'Name', node_col.name)
        write_val(node_et, 'StartIntersectionLocatorNode', node_col.road_node_prop.inter_start.name)
        write_val(node_et, 'EndIntersectionLocatorNode', node_col.road_node_prop.inter_end.name)
        write_val(node_et, 'MaximumCars', node_col.road_node_prop.max_cars)
        write_val(node_et, 'NoReset', int(node_col.road_node_prop.short))
        write_val(node_et, 'Unknown2', node_col.road_node_prop.speed)
        write_val(node_et, 'Unknown3', node_col.road_node_prop.intel)
        write_val(node_et, 'Unknown4', node_col.road_node_prop.unknown)
        for i, road_ob in enumerate(node_col.objects):
            seg_et = write_chunk(node_et, RSG)
            write_val(seg_et, 'Name', road_ob.name)
            write_val(seg_et, 'CubeShape', road_ob.name)
            write_mat_xyz(seg_et, 'Transform', *locs[i])
            write_mat_xyz(seg_et, 'Unknown')

    write_ET(root, filepath)
