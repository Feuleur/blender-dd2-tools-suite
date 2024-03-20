import bpy

import numpy as np
import os
import logging
logger = logging.getLogger("dd2_import")

from .tex_parser import TexParser

def load_tex(filepath, use_loaded=False, use_png_cache=False, overwrite_png_cache=False):
    image_name = os.path.basename(filepath)
    
    if use_loaded:
        if image_name in bpy.data.images:
            return bpy.data.images[image_name]
    
    if use_png_cache and not overwrite_png_cache:
        dir_name = os.path.dirname(filepath)
        png_name = image_name + ".png"
        if os.path.exists(os.path.join(dir_name, png_name)):
            parser = TexParser(path=filepath)
            img = bpy.data.images.load(os.path.join(dir_name, png_name))
            if parser.DXGI_format.endswith("_SRGB"):
                img.colorspace_settings.name = "sRGB"
            else:
                img.colorspace_settings.name = "Non-Color"
            img.name = image_name
            img.alpha_mode="CHANNEL_PACKED"
            return img
    
    parser = TexParser(path=filepath)
    img_array, could_read = parser.read()

    if could_read:
        img = bpy.data.images.new(image_name, width=img_array.shape[1], height=img_array.shape[0], alpha=True, float_buffer=False, is_data=True)
        
        if use_png_cache:
            dir_name = os.path.dirname(filepath)
            png_name = image_name + ".png"
            img.filepath = os.path.join(dir_name, png_name)
        img.file_format = 'PNG'
        img.pixels = (np.flip(img_array, 0).astype(np.float16)/255).ravel()
        if use_png_cache:
            img.save()
        else:
            img.pack()
        if parser.DXGI_format.endswith("_SRGB"):
            img.colorspace_settings.name = "sRGB"
        img.alpha_mode="CHANNEL_PACKED"
        return img
    else:
        raise RuntimeError("Texture data format not supported (format=" + parser.DXGI_format + ")")
