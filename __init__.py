from math import *
from typing import Text
from mathutils import Vector
import bpy
from bpy_extras.io_utils import ExportHelper, ImportHelper
import bpy.utils.previews
import os
from . import RoadClasses
from . import PathClasses
from . import FenceClasses
from . import LocatorClasses
from . import TreeClasses
from . import InstanceClasses
from . import SharMemIOClasses
from . import utils_p3dxml
from .utils_shar_mem_io import *

import inspect
bl_info = {'name': "WMDE - Weasel's Map Data Editor",
           'author': 'Weasel On A Stick',
           'version': (2, 1, 0),
           'blender': (2, 82, 7),
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
    SHARMemIO: bpy.props.BoolProperty(
        name='Enable SHAR Memory IO Module (Requires Pymem)',
        description='This module allows this add-on to talk to the currently running process of Simpsons.exe and read/write various data on the fly', 
        default=True)
    

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, 'RoadsEnabled')
        col.prop(self, 'PathsEnabled')
        col.prop(self, 'FencesEnabled')
        col.prop(self, 'LocatorsEnabled')
        col.prop(self, 'MiscEnabled')
        shar_mem_io_box = col.box()
        shar_mem_io_box.prop(self, 'SHARMemIO')
        shar_mem_io_row = shar_mem_io_box.row()
        shar_mem_io_row.operator('wmde.install_pymem',icon='IMPORT')
        op2 = shar_mem_io_row.operator('wmde.install_pymem', text="Uninstall Pymem", icon='TRASH')
        op2.uninstall = True


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

class InstallPymemOperator(bpy.types.Operator):
    bl_idname = "wmde.install_pymem"
    bl_label = "Install Pymem"

    uninstall : bpy.props.BoolProperty(
        name="Uninstall",
        default=False,
        options={'HIDDEN'},
    )

    def execute(self, context):
        import subprocess
        import sys
        if self.uninstall:
            subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", 'pymem'])
            self.report({'INFO'}, "Pymem uninstalled!")
        else:
            subprocess.check_call([sys.executable, "-m", "pip", "install", 'pymem'])
            self.report({'INFO'}, "Pymem installed!")
        return {'FINISHED'}


class DummyOP(bpy.types.Operator):
    """DummyOP"""
    bl_idname = 'object.dummy'
    bl_label = "Weasel's debugger"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return {'FINISHED'}


classes = [WMDE_Preferences, FileSplitTerra, DummyOP, InstallPymemOperator]
subclasses = [RoadClasses, PathClasses, FenceClasses, LocatorClasses, TreeClasses, InstanceClasses, SharMemIOClasses]

for cls in subclasses:
    if cls.to_register:
        classes += cls.to_register
    
    # old code that would dynamically add classes from [subclasses]
    #parents = [bpy.types.Operator, bpy.types.PropertyGroup, bpy.types.Panel]
    #new_classes = [x[1] for x in inspect.getmembers(cls, inspect.isclass) if any([issubclass(x[1], tryparent) for tryparent in parents])]
    #print(cls.__name__ + ":" + str([x.__name__ for x in new_classes]))


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Collection.road_node_prop = bpy.props.PointerProperty(
        type=RoadClasses.RoadPropGroup,
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
    
    bpy.types.Scene.SMIO = bpy.props.PointerProperty(
        type=(SharMemIOClasses.SMIOPropGroup),
        name="SHAR Memory IO",
    )


def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)
    del bpy.types.Collection.road_node_prop
    del bpy.types.Object.inter_road_beh
    del bpy.types.Object.locator_prop
    del bpy.types.Scene.SMIO


if __name__ == '__main__':
    register()
