import bpy
from bpy.props import *
from bpy_extras.io_utils import ExportHelper, ImportHelper
from os import path
from .utils_p3dxml import *

class Export_instance_listOperator(bpy.types.Operator, ExportHelper):    
    bl_idname = "export_scene.list_instance"
    bl_label = "Export Instance List"
    filename_ext = '.p3dxml'
    filter_glob: bpy.props.StringProperty(
        default='*.p3dxml',
        options={'HIDDEN'},
        maxlen=255)
    selected_only: bpy.props.BoolProperty(
        name='Selected Only',
        description='Only export selected objects',
        default=True)
    OSD_name: bpy.props.StringProperty(
        name="Old Scenegraph Drawable Name",
        description="Name of the drawable to instance within the list",
        default="untitled drawable",
        )

    def execute(self, context):
        listname = os.path.splitext(os.path.basename(self.filepath))[0]
        OSD_name = self.OSD_name
        if self.selected_only:
            objs = list(context.selected_objects)
        else:
            objs = list(context.scene.collection.all_objects)
        root = p3d_et()
        InstanceList = write_chunk(root, "0x3000008")
        write_val(InstanceList, "Name", listname)
        write_val(InstanceList, "Data", "")
        Scenegraph = write_chunk(InstanceList, "0x120100")
        write_val(Scenegraph, "Name", listname)
        write_val(Scenegraph, "Data", "AAAAAA==")
        OSR = write_chunk(Scenegraph, "0x120101")
        write_val(OSR, "Data", "")
        OSB = write_chunk(OSR, "0x120102")
        write_val(OSB, "Name", "root")
        OST = write_chunk(OSB, "0x120103")
        write_val(OST, "Name", listname)
        write_mat_xyz(OST, "Transform", *(0,0,0))
        for i,obj in enumerate(objs):
            OSTi = write_chunk(OST, "0x120103")
            write_val(OSTi, "Name", OSD_name+str(i+1))
            write_locrot_to_mat(OSTi, obj, "Transform")
            OSD = write_chunk(OSTi, "0x120107")
            write_val(OSD, "Name", OSD_name)
            write_val(OSD, "DrawableName", OSD_name)
            write_val(OSD, "IsTranslucent", 0)
            OSSO = write_chunk(OSD, "0x12010A")
            write_val(OSSO, "SortOrder", 0.5)
        write_ET(root, self.filepath)
        self.report({'INFO'}, f"Successfully exported {len(objs)} objects")
        return {'FINISHED'}


class Import_instance_listOperator(bpy.types.Operator, ImportHelper):

    #TODO: Importing lists fucks up rotation if active object doesn't have those applied
    bl_idname = "import_scene.list_instance"
    bl_label = "Import Instance List"
    filename_ext = '.p3dxml'
    filter_glob: bpy.props.StringProperty(
        default='*.p3dxml',
        options={'HIDDEN'},
        maxlen=255)

    active_obj_as_model: bpy.props.BoolProperty(
        name="Use Active Object As Instance Model",
        default=False,
    )

    def execute(self, context):
        if self.active_obj_as_model and not context.active_object:
            self.report(type={'ERROR'}, message="No Active Object Selected!")
            return{'CANCELLED'}

        if self.active_obj_as_model:
            instance_source = context.active_object.data
        else:
            instance_source = None

        root = terra_read(self.filepath)
        if root.attrib['Type'] == "0x3000008":
            IL = root
        elif find_chunks(root, "0x3000008"):
            IL = find_chunks(root, "0x3000008")[0]
        else:
            self.report(type={'WARNING'}, message="No Instance List Chunks Found!")
            return {'FINISHED'}
        instance_name = find_val(IL, "Name")
        Scenegraph = find_chunks(IL, "0x120100")[0]
        OSR = find_chunks(Scenegraph, "0x120101")[0] # Old Scenegraph Root
        OSB = find_chunks(OSR, "0x120102")[0] # Old Scenegraph Branch
        Master_Transform = find_chunks(OSB, "0x120103")[0]
        MT_locrot = (find_xyz_from_mat(Master_Transform,"Transform"),find_euler_from_mat(Master_Transform,"Transform"))
        tree_coll = bpy.data.collections.new(instance_name+"_instances")
        context.collection.children.link(tree_coll)
        for leaf in find_chunks(Master_Transform, "0x120103"):
            leaf_obj = bpy.data.objects.new(find_val(leaf,"Name"),instance_source)
            if leaf_obj.data is None:
                leaf_obj.empty_display_type = 'ARROWS'
            leaf_obj.location = find_xyz_from_mat(leaf, "Transform")
            leaf_obj.location += MT_locrot[0]
            leaf_obj.rotation_euler = find_euler_from_mat(leaf, "Transform")
            leaf_obj.rotation_euler.rotate(MT_locrot[1])
            tree_coll.objects.link(leaf_obj)
        return {'FINISHED'}


class MiscModule:
    @classmethod
    def poll(cls, context):
        return context.preferences.addons[__package__].preferences.MiscEnabled

class MDE_PT_InstanceFileManagment(bpy.types.Panel, MiscModule):
    bl_label = "Instance Lists"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'WMDE Misc'
    bl_order = 6
    
    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text='', icon='MOD_INSTANCE')

    def draw(self, context):
        layout = self.layout
        layout.operator('import_scene.list_instance', icon='IMPORT')
        layout.operator('export_scene.list_instance', icon='EXPORT')
        #layout.operator('object.dummy', icon='MONKEY')

to_register = [
    Export_instance_listOperator,
    Import_instance_listOperator,
    MDE_PT_InstanceFileManagment,
]
