bl_info = {
    "name": "DD2 tool suite",
    "blender": (3, 6, 0),
    "version": (1, 0, 10),
    "category": "Import-Export",
}

import bpy
from bpy.types import Context, Menu, Panel, Operator
from bpy_extras.io_utils import ImportHelper, ExportHelper

import os
import platform
import numpy as np
import logging
logger = logging.getLogger("dd2_import")
logger.propagate = False
import sys

from .mesh.ui import DD2_IMPORT_PT_MeshSettingPanel_1
from .mesh.ui import DD2_IMPORT_PT_MeshSettingPanel_2
from .mesh.ui import DD2_ImportMesh
from .mesh.ui import DD2_ExportMesh

from .mdf2.ui import DD2_IMPORT_PT_Mdf2SettingPanel_1
from .mdf2.ui import DD2_IMPORT_PT_Mdf2SettingPanel_2
from .mdf2.ui import DD2_ImportMdf2
from .mdf2.ui import DD2_ExportMdf2

from .tex.ui import DD2_IMPORT_PT_TexSettingPanel_1
from .tex.ui import DD2_IMPORT_PT_TexSettingPanel_2
from .tex.ui import DD2_ImportTex
from .tex.ui import DD2_ExportTex

from .mot.ui import DD2_IMPORT_PT_MotlistSettingPanel_1
from .mot.ui import DD2_ImportMotlist

from .gpuc.ui import DD2_ImportGpuc

class ColoredFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ANSI Coloring
        grey = "\x1b[38;20m"
        yellow = "\x1b[33;20m"
        red = "\x1b[31;20m"
        bold_red = "\x1b[31;1m"
        _reset = "\x1b[0m"
        self.FORMATS = {
            logging.DEBUG: f"{grey}{self._fmt}{_reset}",
            logging.INFO: f"{grey}{self._fmt}{_reset}",
            logging.WARNING: f"{yellow}{self._fmt}{_reset}",
            logging.ERROR: f"{red}{self._fmt}{_reset}",
            logging.CRITICAL: f"{bold_red}{self._fmt}{_reset}"
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(levelname)s | %(message)s')
colored_formatter = formatter
is_windows = platform.system() == "Windows"
if not (is_windows and int(platform.release()) < 10):
    if is_windows:
        os.system("color")
    colored_formatter = ColoredFormatter('%(levelname)s | %(message)s')
handler.setFormatter(colored_formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

class DD2_CustomAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__
    
    game_path: bpy.props.StringProperty(
        name="Unpacked game path",
        subtype='DIR_PATH',
    )
    
    logging_level: bpy.props.EnumProperty(
        name="Logging level",
        items = [('DEBUG','DEBUG','','',0), 
                 ('INFO','INFO','','',1),
                 ('WARNING','WARNING','','',2),
                 ('ERROR','ERROR','','',3)],
        default = 'INFO'
    )
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="Path to the unpacked game (Up to the STM folder, for example \"C:\\XXX\\re_chunk_000\\natives\\stm\")")
        layout.prop(self, "game_path")
        
        layout.prop(self, "logging_level")


def DD2_menu_func_import(self, context):
    self.layout.operator(DD2_ImportMesh.bl_idname, text="DD2 model files (.mesh.231011879)", icon="MESH_DATA")
    self.layout.operator(DD2_ImportMdf2.bl_idname, text="DD2 material files (.mdf2.40)", icon="MATERIAL_DATA")
    self.layout.operator(DD2_ImportTex.bl_idname, text="DD2 texture files (.tex.760230703)", icon="TEXTURE_DATA")
    self.layout.operator(DD2_ImportMotlist.bl_idname, text="DD2 animation files (.motlist.751)", icon="ANIM_DATA")
    self.layout.operator(DD2_ImportGpuc.bl_idname, text="DD2 cloth sim files (.gpuc.231011972)", icon="MOD_CLOTH")

def DD2_menu_func_export(self, context):
    self.layout.operator(DD2_ExportMesh.bl_idname, text="DD2 mesh files (.mesh.231011879)", icon="MESH_DATA")
    self.layout.operator(DD2_ExportMdf2.bl_idname, text="DD2 material files (.mdf2.40)", icon="MATERIAL_DATA")
    self.layout.operator(DD2_ExportTex.bl_idname, text="DD2 texture files (.tex.760230703)", icon="TEXTURE_DATA")

def register():
    bpy.utils.register_class(DD2_ImportMesh)
    bpy.utils.register_class(DD2_ImportMdf2)
    bpy.utils.register_class(DD2_ImportTex)
    bpy.utils.register_class(DD2_ImportMotlist)
    bpy.utils.register_class(DD2_ImportGpuc)
    bpy.utils.register_class(DD2_CustomAddonPreferences)
    bpy.utils.register_class(DD2_IMPORT_PT_MeshSettingPanel_1)
    bpy.utils.register_class(DD2_IMPORT_PT_MeshSettingPanel_2)
    bpy.utils.register_class(DD2_IMPORT_PT_Mdf2SettingPanel_1)
    bpy.utils.register_class(DD2_IMPORT_PT_Mdf2SettingPanel_2)
    bpy.utils.register_class(DD2_IMPORT_PT_TexSettingPanel_1)
    bpy.utils.register_class(DD2_IMPORT_PT_TexSettingPanel_2)
    bpy.utils.register_class(DD2_IMPORT_PT_MotlistSettingPanel_1)
    bpy.types.TOPBAR_MT_file_import.append(DD2_menu_func_import)
    bpy.utils.register_class(DD2_ExportMesh)
    bpy.utils.register_class(DD2_ExportMdf2)
    bpy.utils.register_class(DD2_ExportTex)
    bpy.types.TOPBAR_MT_file_export.append(DD2_menu_func_export)
    pass

def unregister():
    bpy.utils.unregister_class(DD2_ImportMesh)
    bpy.utils.unregister_class(DD2_ImportMdf2)
    bpy.utils.unregister_class(DD2_ImportTex)
    bpy.utils.unregister_class(DD2_ImportMotlist)
    bpy.utils.unregister_class(DD2_ImportGpuc)
    bpy.utils.unregister_class(DD2_CustomAddonPreferences)
    bpy.utils.unregister_class(DD2_IMPORT_PT_MeshSettingPanel_1)
    bpy.utils.unregister_class(DD2_IMPORT_PT_MeshSettingPanel_2)
    bpy.utils.unregister_class(DD2_IMPORT_PT_Mdf2SettingPanel_1)
    bpy.utils.unregister_class(DD2_IMPORT_PT_Mdf2SettingPanel_2)
    bpy.utils.unregister_class(DD2_IMPORT_PT_TexSettingPanel_1)
    bpy.utils.unregister_class(DD2_IMPORT_PT_TexSettingPanel_2)
    bpy.utils.unregister_class(DD2_IMPORT_PT_MotlistSettingPanel_1)
    bpy.types.TOPBAR_MT_file_import.remove(DD2_menu_func_import)
    bpy.utils.unregister_class(DD2_ExportMesh)
    bpy.utils.unregister_class(DD2_ExportMdf2)
    bpy.utils.unregister_class(DD2_ExportTex)
    bpy.types.TOPBAR_MT_file_export.remove(DD2_menu_func_export)
    pass

