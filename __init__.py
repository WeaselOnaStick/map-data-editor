from math import *
import bpy
import bpy_extras.object_utils
from bpy_extras.io_utils import ExportHelper, ImportHelper
import bpy.utils.previews
import os
from . import RoadClasses
from . import PathClasses
from . import FenceClasses
from . import LocatorClasses
from . import utils_p3dxml
from . import LocatorManager
from . import utils_bpy
import inspect
bl_info = {'name': "Weasel's Map Data Editor",
           'author': 'Weasel On A Stick',
           'version': (0, 7, 6),
           'blender': (2, 82, 7),
           'location': 'View3D > Sidebar > WMDE',
           'description': 'Edit SHAR map data, including: roads, paths, fences and locators',
           'tracker_url': 'https://donutteam.com/@WOAS',
           'wiki_url': 'https://donutteam.com/@WOAS',
           'category': 'Import-Export'}


class WMDE_Preferences(bpy.types.AddonPreferences):
    bl_idname = __name__
    RoadsEnabled: bpy.props.BoolProperty(name='Enable Roads Module',
                                         default=True)
    PathsEnabled: bpy.props.BoolProperty(name='Enable Paths Module',
                                         default=True)
    FencesEnabled: bpy.props.BoolProperty(name='Enable Fences Module',
                                          default=True)
    LocatorsEnabled: bpy.props.BoolProperty(name='Enable Locators Module (WIP)',
                                            default=False)

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, 'RoadsEnabled')
        col.prop(self, 'PathsEnabled')
        col.prop(self, 'FencesEnabled')
        col.prop(self, 'LocatorsEnabled')


class FileSplitTerra(bpy.types.Operator, ImportHelper):
    bl_idname = 'import_scene.split_roads'
    bl_label = 'Split *TERRA.p3dxml'
    filename_ext = '.p3dxml'
    filter_glob: bpy.props.StringProperty(default='*.p3dxml',
                                          options={'HIDDEN'},
                                          maxlen=255)

    def execute(self, context):
        utils_p3dxml.split_terra(self.filepath)
        self.report(
            {'INFO'}, f"several files have been created at {os.path.split(self.filepath)[0]}\n")
        return {'FINISHED'}


class DummyOP(bpy.types.Operator):
    """DummyOP"""
    bl_idname = 'object.dummy'
    bl_label = "Weasel's debugger"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        fp = r"d:\GAMES\The Simpsons Hit And Run\stuff\dev\Map Data Editor\exports\level1.p3dxml"
        LocatorManager.export_locators(context.selected_objects, fp)
        return {'FINISHED'}


classes = [WMDE_Preferences, FileSplitTerra, DummyOP]
subclasses = [RoadClasses, PathClasses, FenceClasses, LocatorClasses]
parents = [bpy.types.Operator, bpy.types.PropertyGroup, bpy.types.Panel]
for cls in subclasses:
    classes += [x[1] for x in inspect.getmembers(cls, inspect.isclass) if any(
        [issubclass(x[1], tryparent) for tryparent in parents])]


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Collection.road_node_prop = bpy.props.PointerProperty(
        type=(RoadClasses.RoadPropGroup),
        name='WMDE Road Node Properties'
    )
    bpy.types.Object.inter_road_beh = bpy.props.IntProperty(name='Road Behaviour',
                                                            description="3 - traffic doesn't stop\n1 - traffic stops before going through (emulates irl traffic lights)\n0 - used primarily in bonus game tracks\n2,4 - unknown",
                                                            min=0,
                                                            max=4
                                                            )
    bpy.types.Object.locator_prop = bpy.props.PointerProperty(
        type=(LocatorClasses.LocatorPropGroup),
        name='WMDE Locator Properties'
    )


def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)
    del bpy.types.Collection.road_node_prop
    del bpy.types.Object.inter_road_beh
    del bpy.types.Object.locator_prop


if __name__ == '__main__':
    register()
