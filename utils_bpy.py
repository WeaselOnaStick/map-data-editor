import bpy
import os
from os import path

def get_connected_verts(x : int,edges : bpy.types.MeshEdges):
    """return list of verts indexes that share an edge with vert x"""
    ans = []
    for e in edges:
        if  x == e.vertices[0]:
            ans.append(e.vertices[1])
        elif x == e.vertices[1]:
            ans.append(e.vertices[0])
    return ans

def get_connected_faces(x : bpy.types.MeshPolygon, faces : bpy.types.MeshPolygons):
    """return list of MeshPolygon (not indexes) that share a vertex"""
    x_verts_set = set(x.vertices[:])
    return [f for f in faces if x_verts_set & set(f.vertices[:]) and f != x]

def get_current_road_collection(context):
    """IF current selection is related to a proper road collection (active outliner collection, active object is inside a collection, etc.), returns that collection"""
    if len(context.selected_objects) >= 1 and context.selected_objects[0].users_collection[0].road_node_prop.to_export:
        return context.selected_objects[0].users_collection[0]
    if context.object and context.object.users_collection[0].road_node_prop.to_export:
        return context.object.users_collection[0]
    if context.view_layer.active_layer_collection.collection.road_node_prop.to_export:
        return context.view_layer.active_layer_collection.collection
    return False


def get_col_parent(collection):
    if collection.name == 'Master Collection':
        return bpy.context.scene.collection
    for col in bpy.data.collections:
        if collection.name in col.children:
            return col


pcoll = bpy.utils.previews.new()
icons_dir = path.join(path.dirname(__file__), 'icons')
for icon in [path.splitext(icon)[0] for icon in os.listdir(icons_dir) if path.splitext(icon)[1] == '.png']:
    pcoll.load(icon, path.join(icons_dir, icon+".png"), 'IMAGE')
# Access icons by filename and icon id: pcoll['{filename}'].icon_id


reminder = 'TODO'
