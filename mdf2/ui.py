import bpy
from bpy.types import Panel
from bpy_extras.io_utils import ImportHelper, ExportHelper

import os
import json
import logging
logger = logging.getLogger("dd2_import")

from .mdf2_loader import load_mdf2
from .mdf2_writer import export_materials, write_mdf2

def SetLoggingLevel(level):
    if level == "DEBUG":
        logger.setLevel(logging.DEBUG)
    elif level == "INFO":
        logger.setLevel(logging.INFO)
    elif level == "WARNING":
        logger.setLevel(logging.WARNING)
    elif level == "ERROR":
        logger.setLevel(logging.ERROR)

class IMPORT_PT_Mdf2SettingPanel_1(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Import Settings"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "DD2_IMPORT_OT_dd2_mdf2"
    
    def draw(self, context):
        layout = self.layout
        sfile = context.space_data
        operator = sfile.active_operator
        
        #layout.prop(operator, 'LOD')
        #layout.prop(operator, 'fix_rotation')
        #layout.prop(operator, 'fix_scale')
        #layout.prop(operator, 'rename_bones')
        #layout.prop(operator, 'connect_bones')
        #layout.prop(operator, 'import_material')
        #layout.prop(operator, 'add_VM_geonode')


class IMPORT_PT_Mdf2SettingPanel_2(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Texture Settings"
    bl_parent_id = "IMPORT_PT_Mdf2SettingPanel_1"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "DD2_IMPORT_OT_dd2_mdf2"

    def draw(self, context):
        layout = self.layout
        
        sfile = context.space_data
        operator = sfile.active_operator
        #layout.enabled = operator.import_material
        layout.prop(operator, 'use_png_cache')
        row = layout.row()
        row.enabled = operator.use_png_cache
        row.prop(operator, 'overwrite_png_cache')
        layout.prop(operator, 'use_HD_texture')


class ImportMdf2(bpy.types.Operator, ImportHelper):
    """Import from Mdf2 file format (.mdf2)"""
    bl_idname = "dd2_import.dd2_mdf2"
    bl_label = 'Import DD2 Mdf2'
    bl_options = {'UNDO'}
    filename_ext = ".mdf2.*"
    

    files: bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)
    filter_glob: bpy.props.StringProperty(default="*.mdf2.*")
    use_png_cache: bpy.props.BoolProperty(name="Use PNG cache", description="Save a copy of imported .tex in a .png file next to it (subsequent imports will be much faster)", default=True)
    overwrite_png_cache: bpy.props.BoolProperty(name="Overwrite PNG cache", description="Overwrite cached .png", default=False)
    use_HD_texture: bpy.props.BoolProperty(name="Use HD textures", description="Attempt to use images from the streaming/ folder", default=False)
    
    def draw(self, context):
        pass

    def execute(self, context):
        addon_prefs = context.preferences.addons["dd2_tool_suite"].preferences
        SetLoggingLevel(addon_prefs.logging_level)

        if addon_prefs.game_path == "":
            self.report({"ERROR"}, "Please fill the game path in the addon preferences")
            return {'CANCELLED'}

        folder = (os.path.dirname(self.filepath))
        filepaths = [os.path.join(folder, x.name) for x in self.files]
        for filepath in filepaths:

            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "all_materials_template_alias.json"), "r") as json_in:
                material_template = json.load(json_in)


            logger.info("Linking node groups...")
            node_group_blend_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mdf2", "new_materials_groups.blend")
            #print(node_group_blend_file)
            if not os.path.exists(node_group_blend_file):
                self.report({"ERROR"}, "Could not access node group .blend file")
                return {"CANCELLED"}
            logger.info("Importing nodes...")
            installed = [i.name for i in bpy.data.node_groups]
            por = []

            with bpy.data.libraries.load(node_group_blend_file, link = False) as (data_from, data_to):
                for group in data_from.node_groups:
                    if not group in installed:
                        por.append(group)
                data_to.node_groups = por
            #print()

            load_mdf2(addon_prefs.game_path, filepath, material_template=material_template, use_loaded_mat=False, use_loaded_tex=True, use_png_cache=self.use_png_cache, overwrite_png_cache=self.overwrite_png_cache, use_HD_texture=self.use_HD_texture)
            for group in por:
                if group.users == 0:
                    bpy.data.node_groups.remove(group)

        return {"FINISHED"}


class ExportMdf2(bpy.types.Operator, ExportHelper):
    """Export to DD2 material file format (.mdf2)"""
    bl_idname = "dd2_export.dd2_mdf2"
    bl_label = 'Export DD2 MDF2'
    filename_ext = ".40"
    filter_glob: bpy.props.StringProperty(default="*.mdf2*", options={'HIDDEN'})

    def execute(self, context):
        selected_objects = context.selected_objects
        try:
            material_datas, beware_export = export_materials(selected_objects)
            data, beware_write = write_mdf2(material_datas)
            with open(self.filepath, "wb") as file_out:
                file_out.write(data)
            beware = beware_export or beware_write
            if beware:
                logger.warning("Export to " + self.filepath + " done, but warning were generated: make sure everything went correctly by checking the python console. ")
                self.report({"WARNING"}, "Export done, but warning were generated: make sure everything went correctly by checking the python console")
            else:
                logger.info("Export to " + self.filepath + " done! ")
                self.report({"INFO"}, "Export done!")
            return {"FINISHED"}
        except Exception as e:
           logger.error("Could not export .mdf2 (path=" + self.filepath + ", exception=" + str(e) + ") ")
           self.report({"ERROR"}, "Could not export .mdf2 (path=" + self.filepath + ", exception=" + str(e) + ") ")
           return {"CANCELLED"}

        
