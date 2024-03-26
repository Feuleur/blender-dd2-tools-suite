import bpy
from bpy.types import Panel
from bpy_extras.io_utils import ImportHelper, ExportHelper
import addon_utils

import os
import numpy as np

import logging
logger = logging.getLogger("dd2_import")

from .tex_loader import load_tex
from .tex_writer import write_tex

def SetLoggingLevel(level):
    if level == "DEBUG":
        logger.setLevel(logging.DEBUG)
    elif level == "INFO":
        logger.setLevel(logging.INFO)
    elif level == "WARNING":
        logger.setLevel(logging.WARNING)
    elif level == "ERROR":
        logger.setLevel(logging.ERROR)

class DD2_IMPORT_PT_TexSettingPanel_1(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Import Settings"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "DD2_IMPORT_OT_dd2_tex"
    
    def draw(self, context):
        layout = self.layout
        sfile = context.space_data
        operator = sfile.active_operator
        

class DD2_IMPORT_PT_TexSettingPanel_2(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Texture Settings"
    bl_parent_id = "DD2_IMPORT_PT_TexSettingPanel_1"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "DD2_IMPORT_OT_dd2_tex"

    def draw(self, context):
        layout = self.layout
        
        sfile = context.space_data
        operator = sfile.active_operator
        
        layout.prop(operator, 'use_png_cache')
        row = layout.row()
        row.enabled = operator.use_png_cache
        row.prop(operator, 'overwrite_png_cache')


class DD2_ImportTex(bpy.types.Operator, ImportHelper):
    """Import from Tex file format (.tex.*)"""
    bl_idname = "dd2_import.dd2_tex"
    bl_label = 'Import DD2 Tex'
    bl_options = {'UNDO'}
    filename_ext = ".tex.*"
    
    files: bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)
    filter_glob: bpy.props.StringProperty(default="*.tex.*")
    use_png_cache: bpy.props.BoolProperty(name="Use PNG cache", description="Save a copy of imported .tex in a .png file next to it (subsequent imports will be much faster)", default=False)
    overwrite_png_cache: bpy.props.BoolProperty(name="Overwrite PNG cache", description="Overwrite cached .png", default=False)
    
    def draw(self, context):
        pass

    def execute(self, context):
        candidate_modules = [mod for mod in addon_utils.modules() if mod.bl_info["name"] == "DD2 tool suite"]
        if len(candidate_modules) > 1:
            logger.warning("Inconsistencies while loading the addon preferences: make sure you don't have multiple versions of the addon installed.")
        mod = candidate_modules[0]
        addon_prefs = context.preferences.addons[mod.__name__].preferences
        SetLoggingLevel(addon_prefs.logging_level)
        
        folder = (os.path.dirname(self.filepath))
        filepaths = [os.path.join(folder, x.name) for x in self.files]
        for filepath in filepaths:
            self.import_tex(filepath)
        return {"FINISHED"}
    
    def import_tex(self, filepath):
        load_tex(filepath, use_loaded=False, use_png_cache=self.use_png_cache, overwrite_png_cache=self.overwrite_png_cache)


class DD2_ExportTex(bpy.types.Operator, ExportHelper):
    """Export to DD2 texture file format (.tex.760230703)"""
    bl_idname = "dd2_export.dd2_tex"
    bl_label = 'Export DD2 Tex'
    filename_ext = ".760230703"
    filter_glob: bpy.props.StringProperty(default="*.tex*", options={'HIDDEN'})

    def execute(self, context):
        try:
            selected_nodes = []
            active_object = bpy.context.active_object
            if active_object is not None:
                active_material = active_object.active_material
                if active_material is not None:
                    active_node_tree = active_material.node_tree
                    if active_node_tree is not None:
                        node_list = active_node_tree.nodes
                        for node in node_list:
                            if node.select:
                                if node.type != "TEX_IMAGE":
                                    raise RuntimeError("Only select one image node! ")
                                else:
                                    selected_nodes.append(node)
            if len(selected_nodes) > 1:
                raise RuntimeError("Select no more than one image node! ")
            if len(selected_nodes) == 0:
                raise RuntimeError("No selected node! ")

            selected_image = selected_nodes[0].image
            texture_data = {
                "data":np.flip(np.array(selected_image.pixels).reshape(selected_image.size[0], selected_image.size[1], -1), 0).flatten(),
                "width":selected_image.size[0],
                "height":selected_image.size[0],
                "space":selected_image.colorspace_settings.name
            }
            data = write_tex(texture_data)
            with open(self.filepath, "wb") as file_out:
                file_out.write(data)
            logger.info("Export to " + self.filepath + " done! ")
            self.report({"INFO"}, "Export done, make sure everything went correctly by checking the python console!")
            return {"FINISHED"}
        except Exception as e:
            logger.error("Could not export .tex (path=" + self.filepath + ", exception=" + str(e) + ") ")
            self.report({"ERROR"}, "Could not export .tex (path=" + self.filepath + ", exception=" + str(e) + ") ")
            return {"CANCELLED"}
