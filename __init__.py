from math import *
import bpy
import bpy.utils.previews
from . import RoadClasses
from . import PathClasses
from . import FenceClasses
from . import LocatorClasses
from . import TreeClasses
from . import InstanceClasses


bl_info = {'name': "WMDE - Weasel's Map Data Editor",
           'author': 'Weasel On A Stick',
           'version': (2, 2, 2),
           'blender': (2, 93),
           'location': 'View3D > Sidebar > WMDE',
           'description': 'Edit SHAR map data, including: roads, paths, fences, locators, k-d Tree and other stuff',
           'tracker_url': 'https://github.com/WeaselOnaStick/map-data-editor/issues',
           'wiki_url': 'https://github.com/WeaselOnaStick/map-data-editor/wiki',
           'category': 'Import-Export'}


class WMDE_Preferences(bpy.types.AddonPreferences):
    bl_idname = __name__
    RoadsEnabled: bpy.props.BoolProperty(
        name='Enable Roads Module',
        default=True)
    PathsEnabled: bpy.props.BoolProperty(
        name='Enable Paths Module',
        default=True)
    FencesEnabled: bpy.props.BoolProperty(
        name='Enable Fences Module', 
        default=True)
    LocatorsEnabled: bpy.props.BoolProperty(
        name='Enable Locators Module', 
        default=True)
    MiscEnabled: bpy.props.BoolProperty(
        name='Enable Misc Module', 
        default=True)
    

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, 'RoadsEnabled')
        col.prop(self, 'PathsEnabled')
        col.prop(self, 'FencesEnabled')
        col.prop(self, 'LocatorsEnabled')
        col.prop(self, 'MiscEnabled')

classes = [WMDE_Preferences]
subclasses = [RoadClasses, PathClasses, FenceClasses, LocatorClasses, TreeClasses, InstanceClasses]

# class WOASdebugOperator(bpy.types.Operator):
#     bl_idname = "object.woasdebug"
#     bl_label = "WOASdebug"

#     def execute(self, context):
#         from .utils_p3dxml import B64ToRailCam
#         from .utils_p3dxml import RailCamToB64
#         input_data = "AgAAAM3MTD7NzMw+AQAAAG8SAzsAAAAAAABUQgAAgL/2KFy+AAAAAArXIz0AAAAAAAAAQZqZmT6amZk+"
#         print(B64ToRailCam(input_data))
#         return {'FINISHED'}

# classes.append(WOASdebugOperator)

# add *Classes.py classes to registry list
for cls in subclasses:
    if cls.to_register:
        classes += cls.to_register


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Collection.road_node_prop = bpy.props.PointerProperty(
        type=RoadClasses.RoadPropGroup,
        name='WMDE Road Node Properties'
    )
    bpy.types.Object.inter_road_beh = bpy.props.IntProperty(
        name='Road Behaviour',
        description="3 - traffic doesn't stop\n1 - traffic stops before going through (emulates irl traffic lights)\n0 - used primarily in bonus game tracks\n2,4 - unknown",
        min=0,
        max=4
        )
    bpy.types.Object.locator_prop = bpy.props.PointerProperty(
        type=(LocatorClasses.LocatorPropGroup),
        name='WMDE Locator Properties'
    )

    bpy.types.WindowManager.intersection_names_visible = bpy.props.BoolProperty(
        default=True,
        set=set_intersection_names_visible,
        get=get_intersection_names_visible,
        )

from .RoadClasses import GetIntersectionsCollection
def set_intersection_names_visible(self, value):
    self["intersection_names_visible"] = value
    for int_obj in GetIntersectionsCollection(bpy.context).objects:
            int_obj.show_name = bpy.context.window_manager.intersection_names_visible

def get_intersection_names_visible(self):
    return self["intersection_names_visible"]

def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)
    del bpy.types.Collection.road_node_prop
    del bpy.types.Object.inter_road_beh
    del bpy.types.Object.locator_prop
    del bpy.types.WindowManager.intersection_names_visible


if __name__ == '__main__':
    register()
