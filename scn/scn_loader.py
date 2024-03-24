import bpy
import json
import os
import math
from mathutils import Vector, Euler, Quaternion, Matrix
import subprocess
import logging
logger = logging.getLogger("dd2_import")
import random

from .scn_parser import ScnParser
from ..mesh.mesh_loader import load_mesh
from ..mdf2.mdf2_loader import load_mdf2

def load_scn_new(game_path, filepath, mesh_cache, mesh_hashes, use_png_cache=True, overwrite_png_cache=False, use_HD_texture=False, enable_foliage=False, enable_flow=False, enable_swinging=False):
    
    #scn_list = parse_scn(filepath)
    scn_name = ".".join(os.path.basename(filepath).split(".")[:-1])
    parser = ScnParser(path=filepath)
    object_list = parser.read()

    master_collection = bpy.context.scene.collection
    if scn_name not in bpy.data.collections.keys():
        scene_collection = bpy.data.collections.new(scn_name)
        master_collection.children.link(scene_collection)
    else:
        scene_collection = bpy.data.collections[scn_name]
    #print(object_list)
    for obj in object_list:
        if obj is None:
            continue
        #print(obj["object_name"])
        if "mesh_path" not in obj.keys():
            logger.info("Object " + obj["object_name"] + " did not contain mesh file.")
            continue
        #print(obj)
        mesh_filepath = os.path.join(game_path, obj["mesh_path"] + ".231011879")
        
        obj_pos = Vector([obj["pos_x"], -obj["pos_z"], obj["pos_y"]])
        obj_rot = Vector([obj["rot_w"], obj["rot_x"], obj["rot_y"], obj["rot_z"]])
        obj_scl = Vector([obj["scl_x"], obj["scl_y"], obj["scl_z"]])
        obj_parent_id = obj["parent"]
        while True:
            if obj_parent_id is None:
                break
            parent = object_list[obj_parent_id]
            parent_pos = Vector([parent["pos_x"], -parent["pos_z"], parent["pos_y"]])
            parent_rot = Vector([parent["rot_w"], parent["rot_x"], parent["rot_y"], parent["rot_z"]])
            parent_scl = Vector([parent["scl_x"], parent["scl_y"], parent["scl_z"]])
            obj_pos += parent_pos
            #obj_rot.rotate(parent_rot)
            #obj_scl *= parent_scl
            obj_parent_id = object_list[obj_parent_id]["parent"]
        
        local_collection = bpy.data.collections.new(obj["object_name"])
        scene_collection.children.link(local_collection)
        
        random_value = float(random.randint(0,10000))
        
        if mesh_filepath in mesh_cache:
            cached_data = mesh_cache[mesh_filepath]
            for cached_obj in cached_data:
                current_obj = bpy.data.objects.new(cached_obj["object_name"], bpy.data.meshes[mesh_hashes[cached_obj["mesh_hash"]]])
                local_collection.objects.link(current_obj)
                
                # Position the object
                if current_obj.parent is None:
                    current_obj.location = obj_pos
                    current_obj.rotation_mode = "QUATERNION"
                    current_obj.rotation_quaternion = obj_rot
                    current_obj.rotation_quaternion.rotate(Euler([math.radians(90),0,0]))
                    current_obj.scale = obj_scl
                
                current_obj.material_slots[0].link = 'OBJECT'
                current_obj.material_slots[0].material = bpy.data.materials[cached_obj["material_name"]]
                
                # Add the geonode modifier
                if enable_swinging and "geonode_modifier_name" in cached_obj.keys():
                    geonode_modifier = current_obj.modifiers.new(name="Swing", type="NODES")
                    geonode_modifier.node_group = bpy.data.node_groups[cached_obj["geonode_modifier_name"]]
                    geonode_modifier_inputs = [x for x in geonode_modifier.keys() if (not x.endswith("_use_attribute") and not x.endswith("_attribute_name"))]
                    
                    for k,v in cached_obj["geonode_modifier_params"].items():
                        geonode_modifier[k] = v
                    for param_i in range(len(geonode_modifier_inputs)):
                        param = geonode_modifier.node_group.inputs[param_i+1]
                        if param.name == "Random":
                            geonode_modifier[geonode_modifier_inputs[param_i]] = random_value
        else:
            #print("Load mesh ", mesh_filepath)
            try:
                current_objs = load_mesh(mesh_filepath, collection=local_collection, LOD=0, fix_rotation=False, obj_name=obj["object_name"])
            except Exception as e:
                logger.warning("Could not load mesh, exception during parsing (path=" + mesh_filepath + ", exception=" + str(e) + ")")
                continue
            
            for current_obj in current_objs:
                # For Meshes, link their data according to the mesh hash
                if current_obj.type == "MESH":
                    mesh_hash = hash(str([x.co for x in current_obj.data.vertices]))
                    if mesh_hash in mesh_hashes:
                        to_delete_name = current_obj.data.name
                        current_obj.data = bpy.data.meshes[mesh_hashes[mesh_hash]]
                        bpy.data.meshes.remove(bpy.data.meshes[to_delete_name])
                    else:
                        mesh_hashes[mesh_hash] = current_obj.data.name
                # Position the object
                if current_obj.parent is None:
                    current_obj.location = obj_pos
                    current_obj.rotation_mode = "QUATERNION"
                    current_obj.rotation_quaternion = obj_rot
                    current_obj.rotation_quaternion.rotate(Euler([math.radians(90),0,0]))
                    current_obj.rotation_mode = "XYZ"
                    if current_obj.type == "MESH":
                        current_obj.scale = obj_scl
            
            
            if "mat_path" in obj.keys():
                mdf2_filepath = os.path.join(game_path, obj["mat_path"] + ".40")
                try:
                    mats = load_mdf2(game_path, mdf2_filepath, use_loaded_mat=True, use_loaded_tex=True, use_png_cache=use_png_cache, overwrite_png_cache=overwrite_png_cache, use_HD_texture=use_HD_texture, mat_prefix=obj["object_name"], enable_foliage=enable_foliage, enable_flow=enable_flow)
                except Exception as e:
                    logger.error("Could not load material, exception during parsing (path=" + mdf2_filepath + ", exception=" + str(e) + ")")
            if enable_swinging:
                # Add the geonodes
                geonode_materials = [
                    "Emissive.mmtr",
                    "Lamp.mmtr",
                    "Lamp_Dissolve.mmtr",
                    "Swing.mmtr",
                    "Swing_Trans.mmtr",
                    "Swing_AlphaTest.mmtr",
                    "Swing_Transparent.mmtr",
                    "Decal_Swing_Trans.mmtr"
                ]
                for current_obj_i, current_obj in enumerate(current_objs):
                    if "mat_path" in obj.keys() and current_obj.type == "MESH" and current_obj.material_slots[0].material.use_nodes:
                        for node in current_obj.material_slots[0].material.node_tree.nodes:
                            if node.type == "GROUP" and node.node_tree.name.endswith("_post") and node.node_tree.name[:-len("_post")] in geonode_materials:
                                geonode_modifier = current_obj.modifiers.new(name="Swing", type="NODES")
                                geonode_modifier.node_group = bpy.data.node_groups[node.node_tree.name[:-len("_post")] + "_geonode"]
                                geonode_modifier_inputs = [x for x in geonode_modifier.keys() if (not x.endswith("_use_attribute") and not x.endswith("_attribute_name"))]
                                for param_i in range(len(geonode_modifier_inputs)):
                                    param = geonode_modifier.node_group.inputs[param_i+1]
                                    if param.name in node.inputs:
                                        if type(geonode_modifier[geonode_modifier_inputs[param_i]]) != float:
                                            if len(geonode_modifier[geonode_modifier_inputs[param_i]]) == 3:
                                                geonode_modifier[geonode_modifier_inputs[param_i]] = node.inputs[param.name].default_value[:3]
                                            else:
                                                geonode_modifier[geonode_modifier_inputs[param_i]] = node.inputs[param.name].default_value
                                        else:
                                            geonode_modifier[geonode_modifier_inputs[param_i]] = node.inputs[param.name].default_value
                                    if param.name == "Random":
                                        geonode_modifier[geonode_modifier_inputs[param_i]] = random_value
                                break
            
            
            # Put data in cache
            cached_data = []
            cache_compatible = True
            #mat_counter = 0
            for current_obj_i, current_obj in enumerate(current_objs):
                if not ("mat_path" in obj.keys() and current_obj.type == "MESH"):
                    cache_compatible = False
                    continue
                cached_obj = {}
                cached_obj["mesh_hash"] = hash(str([x.co for x in current_obj.data.vertices]))
                cached_obj["object_name"] = current_obj.name
                cached_obj["material_name"] = current_obj.material_slots[0].material.name
                if enable_swinging:
                    geonode_modifiers = [x for x in current_obj.modifiers if x.type == "NODES"]
                    if len(geonode_modifiers) > 0:
                        cached_obj["geonode_modifier_name"] = geonode_modifiers[0].node_group.name
                        geonode_params = {}
                        geonode_modifier_inputs = [x for x in geonode_modifiers[0].keys() if (not x.endswith("_use_attribute") and not x.endswith("_attribute_name"))]
                        for geonode_modifier_input in geonode_modifier_inputs:
                            geonode_params[geonode_modifier_input] = geonode_modifiers[0][geonode_modifier_input]
                        cached_obj["geonode_modifier_params"] = geonode_params
                cached_data.append(cached_obj)
                #mat_counter += 1
            if cache_compatible:
                mesh_cache[mesh_filepath] = cached_data
