import bpy
import os
from os import path


def get_current_coll(context):
    if len(context.selected_objects) >= 1 and context.selected_objects[0].users_collection[0].road_node_prop.to_export:
        return context.selected_objects[0].users_collection[0]
    if context.object and context.object.users_collection[0].road_node_prop.to_export:
        return context.object.users_collection[0]
    if context.view_layer.active_layer_collection.collection != context.scene.collection:
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


reminder = 'remind weasel to add text here'
