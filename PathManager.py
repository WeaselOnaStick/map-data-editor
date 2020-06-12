import bmesh
import bpy
from .utils_bpy import *
from .utils_p3dxml import *


def path_create():
    pass


def import_paths(filepath):
    bpy.ops.object.select_all(action='DESELECT')
    root = terra_read(filepath)
    if 'Paths' not in bpy.context.scene.collection.children:
        paths_collection = bpy.data.collections.new('Paths')
        bpy.context.scene.collection.children.link(paths_collection)
    else:
        paths_collection = bpy.data.collections['Paths']
    if not find_chunks(root, PAT):
        return "No path chunks found in the file"
    for path in find_chunks(root, PAT):
        locs = []
        for vert in path.findall('Value/*'):
            locs.append(item_to_vector(vert))

        path_mesh = bpy.data.meshes.new('Path')
        path_mesh.vertices.add(len(locs))
        path_mesh.edges.add(len(locs) - 1)
        for i, vert in enumerate(locs):
            path_mesh.vertices[i].co = vert

        for i, edge in enumerate(path_mesh.edges):
            edge.vertices[0] = i
            edge.vertices[1] = i + 1

        path_object = bpy.data.objects.new('Path', path_mesh)
        paths_collection.objects.link(path_object)
        path_object.data.update()
        path_object.select_set(True)
    bpy.context.view_layer.objects.active = path_object
    # TODO fix path object's visibility somehow. Maybe switch these objects entirely to vector curves
    return 'OK'


def export_paths(filepath, objs):
    root = p3d_et()
    for path in objs:
        chunk = write_chunk(root, PAT)
        pos = ET.SubElement(chunk, 'Value', Name='Positions')
        verts = [x.co for x in path.data.vertices]
        for v in verts:
            ET.SubElement(pos, 'Item', X=(str(v.x)),
                          Y=(str(v.z)), Z=(str(v.y)))

    write_ET(root, filepath)
