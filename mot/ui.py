import bpy
from bpy.types import Panel
from bpy_extras.io_utils import ImportHelper, ExportHelper

import os

import logging
logger = logging.getLogger("dd2_import")

from .mot_loader import load_motlist

def SetLoggingLevel(level):
    if level == "DEBUG":
        logger.setLevel(logging.DEBUG)
    elif level == "INFO":
        logger.setLevel(logging.INFO)
    elif level == "WARNING":
        logger.setLevel(logging.WARNING)
    elif level == "ERROR":
        logger.setLevel(logging.ERROR)
        
class IMPORT_PT_MotlistSettingPanel_1(Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Import Settings"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "DD2_IMPORT_OT_dd2_motlist"

    def draw(self, context):
        layout = self.layout
        sfile = context.space_data
        operator = sfile.active_operator

        #layout.prop(operator, 'set_fake_user')

class ImportMotlist(bpy.types.Operator, ImportHelper):
    """Import from Motlist file format (.motlist)"""
    bl_idname = "dd2_import.dd2_motlist"
    bl_label = 'Import DD2 Motlist'
    bl_options = {'UNDO'}
    filename_ext = ".motlist.*"
    
    files: bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)
    filter_glob: bpy.props.StringProperty(default="*.motlist.*")
    #set_fake_user: bpy.props.BoolProperty(name="Keep animations on file save", description="Unused animations are deleted when a .blend file is saved unless explicitely set not to (this is a vanilla blender behavior). Enabling this will flag the imported animations to not lose them.", default=False)

    def draw(self, context):
        pass

    def execute(self, context):
        addon_prefs = context.preferences.addons["dd2_tool_suite"].preferences
        SetLoggingLevel(addon_prefs.logging_level)
        
        folder = (os.path.dirname(self.filepath))
        filepaths = [os.path.join(folder, x.name) for x in self.files]
        
        selected_objects = context.selected_objects
        armature = None
        for obj in selected_objects:
            if obj.type == "ARMATURE":
                armature = obj
                break
        if armature is None:
            self.report({"ERROR"}, "No armature selected! ")
            return {"CANCELLED"}
        
        for filepath in filepaths:
            import traceback
            try:
                load_motlist(filepath, armature.data)
            except Exception as e:
                logger.error("Error while loading motlist " + filepath + ", reason = " + str(e))
                self.report({"ERROR"}, "Error while loading motlist " + filepath + ", reason = " + str(e))
                traceback.print_exc()
                return {"CANCELLED"}
        return {"FINISHED"}
