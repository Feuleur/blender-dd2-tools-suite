import bpy
from bpy.types import Panel
from bpy_extras.io_utils import ImportHelper, ExportHelper
import addon_utils

import os
import json
import logging
logger = logging.getLogger("dd2_import")

from .gpuc_loader import load_gpuc

def SetLoggingLevel(level):
    if level == "DEBUG":
        logger.setLevel(logging.DEBUG)
    elif level == "INFO":
        logger.setLevel(logging.INFO)
    elif level == "WARNING":
        logger.setLevel(logging.WARNING)
    elif level == "ERROR":
        logger.setLevel(logging.ERROR)

class DD2_ImportGpuc(bpy.types.Operator, ImportHelper):
    """Import from Cloth Sim file format (.gpuc)"""
    bl_idname = "dd2_import.dd2_gpuc"
    bl_label = 'Import DD2 Gpuc'
    bl_options = {'UNDO'}
    filename_ext = ".gpuc.*"
    
    files: bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)
    filter_glob: bpy.props.StringProperty(default="*.gpuc.*")
    fix_rotation: bpy.props.BoolProperty(name="Fix rotation", description="Rotate the cloth sim 90° to fit blender's frame of reference",  default=True)

    def execute(self, context):
        candidate_modules = [mod for mod in addon_utils.modules() if mod.bl_info["name"] == "DD2 tool suite"]
        if len(candidate_modules) > 1:
            logger.warning("Inconsistencies while loading the addon preferences: make sure you don't have multiple versions of the addon installed.")
        mod = candidate_modules[0]
        addon_prefs = context.preferences.addons[mod.__name__].preferences
        SetLoggingLevel(addon_prefs.logging_level)
        
        if self.files:
            folder = (os.path.dirname(self.filepath))
            filepaths = [os.path.join(folder, x.name) for x in self.files]
        else:
            filepaths = [str(self.filepath)]

        if addon_prefs.game_path == "" and self.import_material:
            self.report({"ERROR"}, "Import material was enabled, while the game path in not set in the addon preferences")
            return {"CANCELLED"}

        for filepath in filepaths:
            try:
                objs = load_gpuc(filepath, collection=None, fix_rotation=self.fix_rotation)
            except Exception as e:
                import traceback
                traceback.print_exc()
                logger.warning("Unable to load gpuc of path " + str(filepath) + ", reason = " + str(e))
                self.report({"WARNING"}, "Unable to load gpuc of path " + str(filepath) + ", reason = " + str(e))
                continue
        return {"FINISHED"}

        
