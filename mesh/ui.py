import bpy
from bpy.types import Panel
from bpy_extras.io_utils import ImportHelper, ExportHelper

import os
import json
import logging
logger = logging.getLogger("dd2_import")

from .mesh_loader import load_mesh
from .mesh_writer import write_mesh
from ..mdf2.mdf2_loader import load_mdf2
from ..common.apply_geonode import apply_shellfur_geonode

def SetLoggingLevel(level):
    if level == "DEBUG":
        logger.setLevel(logging.DEBUG)
    elif level == "INFO":
        logger.setLevel(logging.INFO)
    elif level == "WARNING":
        logger.setLevel(logging.WARNING)
    elif level == "ERROR":
        logger.setLevel(logging.ERROR)

class DD2_IMPORT_PT_MeshSettingPanel_1(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Import Settings"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "DD2_IMPORT_OT_dd2_mesh"
    
    def draw(self, context):
        layout = self.layout
        sfile = context.space_data
        operator = sfile.active_operator
        
        #layout.prop(operator, 'filter_glob')
        layout.prop(operator, 'LOD')
        layout.prop(operator, 'fix_rotation')
        layout.prop(operator, 'connect_bones')
        layout.prop(operator, 'import_material')
        row = layout.row()
        row.enabled = operator.import_material
        row.prop(operator, 'simplify_mat')
        row = layout.row()
        row.enabled = operator.import_material
        row.prop(operator, 'use_loaded_mat')
        row = layout.row()
        row.enabled = operator.import_material and not operator.simplify_mat
        row.prop(operator, 'add_shellfur_geonode')




class DD2_IMPORT_PT_MeshSettingPanel_2(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Texture Settings"
    bl_parent_id = "DD2_IMPORT_PT_MeshSettingPanel_1"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "DD2_IMPORT_OT_dd2_mesh"

    def draw(self, context):
        layout = self.layout
        
        sfile = context.space_data
        operator = sfile.active_operator
        layout.enabled = operator.import_material
        layout.prop(operator, 'use_png_cache')
        row = layout.row()
        row.enabled = operator.use_png_cache
        row.prop(operator, 'overwrite_png_cache')
        layout.prop(operator, 'use_HD_texture')


class DD2_ImportMesh(bpy.types.Operator, ImportHelper):
    """Import from Mesh file format (.mesh)"""
    bl_idname = "dd2_import.dd2_mesh"
    bl_label = 'Import DD2 Mesh'
    bl_options = {'UNDO'}
    filename_ext = ".mesh.*"
    
    files: bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)
    filter_glob: bpy.props.StringProperty(default="*.mesh.*")
    LOD: bpy.props.IntProperty(name="LoD", description="Import a specific Level of Detail (lower is more detailed)", default=0, min=0, max=10, step=1)
    fix_rotation: bpy.props.BoolProperty(name="Fix rotation", description="Rotate the mesh 90° to fit blender's frame of reference",  default=True)
    connect_bones: bpy.props.BoolProperty(name="Connect bones", description="Connect the bones to their children when available, WILL break animations",  default=False)
    import_material: bpy.props.BoolProperty(name="Import material", description="Import the material .mdf2 file",  default=False)
    simplify_mat: bpy.props.BoolProperty(name="Simplify materials", description="Erase the unused properties and textures from the imported material. This will cause issues if you want to export the material as a .mdf2 file afterward", default=True)
    use_loaded_mat: bpy.props.BoolProperty(name="Reuse loaded materials", description="Use already loaded materials when available, may cause glitches when two objects have similarly named materials", default=True)
    add_shellfur_geonode: bpy.props.BoolProperty(name="Import Shellfur geonode", description="Import the fur textures as a geonode modifier. If using cycles, make sure you have enough transparent light bounces to support it, by default blender doesn't have enough and it will show as black blobs on the mesh",  default=False)
    use_png_cache: bpy.props.BoolProperty(name="Use PNG cache", description="Save a copy of imported .tex in a .png file next to it (subsequent imports will be much faster)", default=True)
    overwrite_png_cache: bpy.props.BoolProperty(name="Overwrite PNG cache", description="Overwrite cached .png", default=False)
    use_HD_texture: bpy.props.BoolProperty(name="Use HD textures", description="Attempt to use images from the streaming/ folder", default=True)

    def draw(self, context):
        pass

    def execute(self, context):
        addon_prefs = context.preferences.addons["blender-dd2-tools-suite"].preferences
        SetLoggingLevel(addon_prefs.logging_level)
        
        if self.files:
            folder = (os.path.dirname(self.filepath))
            filepaths = [os.path.join(folder, x.name) for x in self.files]
        else:
            filepaths = [str(self.filepath)]

        if addon_prefs.game_path == "" and self.import_material:
            self.report({"ERROR"}, "Import material was enabled, while the game path in not set in the addon preferences")
            return {"CANCELLED"}

        if self.import_material:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mdf2", "all_materials_template_alias.json"), "r") as json_in:
                material_template = json.load(json_in)

            logger.info("Linking node groups...")
            node_group_blend_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mdf2", "new_materials_groups.blend")
            if not os.path.exists(node_group_blend_file):
                self.report({"ERROR"}, "Could not access node group .blend file")
                return {"CANCELLED"}
            logger.info("Importing nodes...")
            installed = [i.name for i in bpy.data.node_groups]
            por = []
            with bpy.data.libraries.load(node_group_blend_file, link = False) as (data_from, data_to):
                for i in data_from.node_groups:
                    if not i in installed:
                        por.append(i)
                data_to.node_groups = por

        for filepath in filepaths:
            try:
                objs = load_mesh(filepath, collection=None, LOD=self.LOD, fix_rotation=self.fix_rotation, connect_bones=self.connect_bones)

                if self.import_material:
                    logger.info("Attempting to find the mdf2 file...")
                    mesh_basename = os.path.basename(filepath)
                    mesh_dirname = os.path.dirname(filepath)
                    mesh_rawname = ".".join(mesh_basename.split(".")[:-2])
                    mdf2_filepath = os.path.join(mesh_dirname, mesh_rawname + ".mdf2.40")

                    if not os.path.exists(mdf2_filepath):
                        from glob import glob
                        candidate_filepaths = glob(mesh_dirname + "/*.mdf2.40")
                        print(candidate_filepaths)
                        if len(candidate_filepaths) > 0:
                            mdf2_filepath = candidate_filepaths[0]
                    logger.info("Found mdf2 file: " + mdf2_filepath)

                    try:
                        load_mdf2(addon_prefs.game_path, mdf2_filepath, material_template=material_template, use_loaded_mat=self.use_loaded_mat, simplify_mat=self.simplify_mat, use_loaded_tex=True, use_png_cache=self.use_png_cache, overwrite_png_cache=self.overwrite_png_cache, use_HD_texture=self.use_HD_texture)
                        if self.add_shellfur_geonode:
                            for obj in objs:
                                apply_shellfur_geonode(obj)

                    except Exception as e:
                        logger.warning("Unable to load material of path " + str(mdf2_filepath) + ", reason = " + str(e))
                        self.report({"WARNING"}, "Unable to load material of path " + str(mdf2_filepath) + ", reason = " + str(e))
                        continue
            except Exception as e:
                logger.warning("Unable to load mesh of path " + str(filepath) + ", reason = " + str(e))
                self.report({"WARNING"}, "Unable to load mesh of path " + str(filepath) + ", reason = " + str(e))
                continue
        if self.import_material:
            for group in por:
                if group.users == 0:
                    bpy.data.node_groups.remove(group)
        return {"FINISHED"}


class DD2_ExportMesh(bpy.types.Operator, ExportHelper):
    """Export to DD2 mesh file format (.mesh.231011879)"""
    bl_idname = "dd2_export.dd2_mesh"
    bl_label = 'Export DD2 Mesh'
    filename_ext = ".231011879"
    filter_glob: bpy.props.StringProperty(default="*.mesh*", options={'HIDDEN'})

    def execute(self, context):
        selected_objects = context.selected_objects
        data = write_mesh(selected_objects)
        with open(self.filepath, "wb") as file_out:
            file_out.write(data)
        logger.info("Export to " + self.filepath + " done! ")
        self.report({"INFO"}, "Export done, make sure everything went correctly by checking the python console!")
        return {"FINISHED"}

        
