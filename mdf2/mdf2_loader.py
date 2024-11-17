import bpy
from mathutils import Matrix, Vector

import numpy as np
import os
import logging
logger = logging.getLogger("dd2_import")

from .mdf2_parser import Mdf2Parser
from ..common.murmurhash import murmurhash_32
from ..tex.tex_loader import load_tex

shader_types = {
    0:"Standard",
    1:"Decal",
    2:"DecalWithMetallic",
    3:"DecalNRMR",
    4:"Transparent",
    5:"Distortion",
    6:"PrimitiveMesh",
    7:"PrimitiveSolidMesh",
    8:"Water",
    9:"SpeedTree",
    10:"GUI",
    11:"GUIMesh",
    12:"GUIMeshTransparent",
    13:"ExpensiveTransparent",
    14:"Forward",
    15:"RenderTarget",
    16:"PostProcess",
    17:"PrimitiveMaterial",
    18:"PrimitiveSolidMaterial",
    19:"SpineMaterial"
}

flag1_bits = {
    0:"BaseTwoSideEnable",
    1:"BaseAlphaTestEnable",
    2:"ShadowCastDisable",
    3:"VertexShaderUsed",
    4:"EmissiveUsed",
    5:"TessellationEnable",
    6:"EnableIgnoreDepth",
    7:"AlphaMaskUsed"
}

flag2_bits = {
    0:"ForcedTwoSideEnable",
    1:"TwoSideEnable"
}

flag3_bits = {
    0:"RoughTransparentEnable",
    1:"ForcedAlphaTestEnable",
    2:"AlphaTestEnable",
    3:"SSSProfileUsed",
    4:"EnableStencilPriority",
    5:"RequireDualQuaternion",
    6:"PixelDepthOffsetUsed",
    7:"NoRayTracing"
}

def create_img_node(game_path, nodes, filepath, position, use_loaded_tex=False, use_png_cache=False, overwrite_png_cache=False, use_HD_texture=False):
    node_img = nodes.new(type='ShaderNodeTexImage')
    node_img.location = Vector(position)
    
    # UNFORTUNATELY the default textures in systems/rendering are fucked, I have no idea if they changed the format or if it's a genuine error.
    # In the meantime, I included the default textures from Rise in the addon to temporarily fix it
    default_tex_swap = {
        "systems/rendering/nullwhite.tex":"tex_swap/nullwhite.tex",
        "systems/rendering/nullnormalroughness.tex":"tex_swap/nullnormalroughness.tex",
        "systems/rendering/nullnormalroughnessocclusion.tex":"tex_swap/nullnormalroughnessocclusion.tex",
        "systems/rendering/nullnormal.tex":"tex_swap/nullnormal.tex",
        "mastermaterial/textures/nullwhitearray_msk4.tex":"tex_swap/nullwhite.tex",
        "mastermaterial/textures/nulldetailmap_msk4.tex":"tex_swap/nullnormalroughness.tex",
        "mastermaterial/textures/nullnormalopt.tex":"tex_swap/nullnormalroughness.tex",
    }
    if filepath.lower() in default_tex_swap.keys():
        use_png_cache = False
        filepath = os.path.join(os.path.dirname(__file__), default_tex_swap[filepath.lower()])

    # A few files have some fucked up names
    new_filepath = None
    filepath = filepath.replace("@", "")
    #print(filepath)
    #filepath = filepath.lower()
    if use_HD_texture:
        new_filepath = os.path.join(game_path, "streaming", filepath + ".760230703")
        if not os.path.isfile(new_filepath):
            new_filepath = os.path.join(game_path, "streaming", filepath + ".760230703.STM")
    if not use_HD_texture or not os.path.isfile(new_filepath):
        new_filepath = os.path.join(game_path, filepath + ".760230703")
        if not os.path.isfile(new_filepath):
            new_filepath = os.path.join(game_path, filepath + ".760230703.STM")
    if not os.path.isfile(new_filepath):
        logger.warning("Could not load texture, file does not exists (path=" + new_filepath + ")")
        return node_img

    try:
        img = load_tex(new_filepath, use_loaded=use_loaded_tex, use_png_cache=use_png_cache, overwrite_png_cache=overwrite_png_cache)
    except Exception as e:
        logger.warning("Could not load texture, exception during parsing (path=" + new_filepath + ", exception=" + str(e) + ")")
        img = None
    if img is not None:
        node_img.image = img
        node_img.extension = "REPEAT"
    #else:
        #logger.warning("Could not load texture, parser returned None (path=" + new_filepath + ")")
    return node_img

def load_mdf2(game_path, filepath, material_template={}, use_loaded_mat=False, simplify_mat=True, use_loaded_tex=False, use_png_cache=False, overwrite_png_cache=False, use_HD_texture=False, mat_prefix="", enable_foliage=False, enable_flow=False):
    parser = Mdf2Parser(path=filepath)
    mat_dict = parser.read()
    returned_mats = []
    for mat_raw_name, mat_values in mat_dict.items():
        mat_name = mat_prefix + mat_raw_name
        if len(mat_name) > 55:
            #FUCK blender
            mat_name = "HASHED_" + str(abs(int(hash(mat_name)))).zfill(20)
        if use_loaded_mat:
            if mat_name in bpy.data.materials and bpy.data.materials[mat_name].use_nodes:
                returned_mats.append(bpy.data.materials[mat_name])
                continue
        if mat_name not in bpy.data.materials or bpy.data.materials[mat_name].use_nodes == True:
            mat = bpy.data.materials.new(name=mat_name)
        else:
            mat = bpy.data.materials[mat_name]
        
        if mat.use_nodes == False:
            mat.use_nodes = True
        
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        
        general_frame_x = -1650.0
        general_frame_y = 500.0
        property_frame_x = -1400.0
        property_frame_y = 500.0
        texture_frame_x = -1000.0
        texture_frame_y = 500.0
        general_frame = nodes.new(type='NodeFrame')
        general_frame.label = "General"
        property_frame = nodes.new(type='NodeFrame')
        property_frame.label = "Properties"
        texture_frame = nodes.new(type='NodeFrame')
        texture_frame.label = "Texture paths for export are in the custom properties"
        texture_frame.label_size = 12
        
        
        node_BSDF = nodes["Principled BSDF"]
        nodes.remove(node_BSDF)
        dd2_shader_node = nodes.new(type='ShaderNodeGroup')
        dd2_shader_node.location = Vector((-500.0, 500.0))
        dd2_shader_node.node_tree = bpy.data.node_groups["DD2Shader"]
        dd2_shader_node.label = "DD2Shader"
        node_output = nodes["Material Output"]

        links.new(dd2_shader_node.outputs["Shader"], node_output.inputs["Surface"])
        
        mat["mmtr_path"] = str(mat_values["mmtr_path"])
        if mat_values["shader_type"] in shader_types.keys():
            mat["shader_type"] = shader_types[mat_values["shader_type"]]
        else:
            mat["shader_type"] = mat_values["shader_type"]

        # Flag 1
        mat["flag1"] = mat_values["flag1"]
        #for i in range(8):
            #mat[flag1_bits[i]] = bool((mat_values["flag1"] >> i) & 1)

        # Flag 2
        mat["flag2"] = mat_values["flag2"]
        #for i in range(2):
            #mat[flag2_bits[i]] = bool((mat_values["flag2"] >> i) & 1)

        # Flag 3
        mat["flag3"] = mat_values["flag3"]
        #for i in range(8):
            #mat[flag3_bits[i]] = bool((mat_values["flag3"] >> i) & 1)

        # Phong coef
        mat["phong"] = mat_values["phong"]
        #mat["Phong"] = float(((mat_values["flag3"] >> i) & 1) / 255.0)

        # Unknown hash
        mat["unknown_hash1"] = mat_values["unknown_hash1"]
        mat["unknown_hash2"] = mat_values["unknown_hash2"]

        # Buffers
        mat["buffer_count"] = len(mat_values["buffers"])
        for buffer_i, buffer_data in enumerate(mat_values["buffers"]):
            mat["buffer_type_"+str(buffer_i)] = str(buffer_data["buffer_type"])
            mat["buffer_file_path_"+str(buffer_i)] = str(buffer_data["file_path"])
            mat["buffer_unk1_"+str(buffer_i)] = int(buffer_data["unk1"])
            mat["buffer_unk2_"+str(buffer_i)] = int(buffer_data["unk2"])

        node_UVMap1 = nodes.new(type='ShaderNodeUVMap')
        node_UVMap1.location = Vector((general_frame_x, general_frame_y-0.0))
        node_UVMap1.uv_map = "UV1"
        node_UVMap1.parent = general_frame
        node_UVMap2 = nodes.new(type='ShaderNodeUVMap')
        node_UVMap2.location = Vector((general_frame_x, general_frame_y-100.0))
        node_UVMap2.uv_map = "UV2"
        node_UVMap2.parent = general_frame
        node_VertexColor = nodes.new(type='ShaderNodeVertexColor')
        node_VertexColor.location = Vector((general_frame_x, general_frame_y-200.0))
        node_VertexColor.layer_name = "Attribute"
        node_VertexColor.parent = general_frame
        node_geometry = nodes.new(type='ShaderNodeNewGeometry')
        node_geometry.location = Vector((general_frame_x, general_frame_y-300.0))
        node_geometry.parent = general_frame
        node_object_info = nodes.new(type='ShaderNodeObjectInfo')
        node_object_info.location = Vector((general_frame_x, general_frame_y-500.0))
        node_object_info.parent = general_frame
        
        if mat_values["mmtr_path"] in material_template.keys():
            group_name = material_template[mat_values["mmtr_path"]]["alias"]
        else:
            group_name = mat_values["mmtr_path"]
        group_name_original = mat_values["mmtr_path"].split("/")[-1]
        
        if group_name + "_pre" not in bpy.data.node_groups or group_name + "_post" not in bpy.data.node_groups:
            # Unknown mat, doing our best
            logger.warning("Unknown material encountered (path=" + filepath + ", name=" + group_name + ")")
            for property_i, property_type in enumerate(mat_values["properties"].keys()):
                property_value = mat_values["properties"][property_type]
                if type(property_value) is list:
                    node_RGB = nodes.new(type='ShaderNodeRGB')
                    node_RGB.location = Vector((property_frame_x, property_frame_y))
                    property_frame_y -= 200.0
                    node_RGB.parent = property_frame
                    node_RGB.outputs["Color"].default_value = Vector(property_value)
                    node_RGB.label = property_type                    
                else:
                    node_unknownvalue = nodes.new(type='ShaderNodeValue')
                    node_unknownvalue.location = Vector((property_frame_x, property_frame_y))
                    property_frame_y -= 100.0
                    node_unknownvalue.label = property_type
                    node_unknownvalue.parent = property_frame
                    node_unknownvalue.outputs["Value"].default_value = property_value 
            for texture_i, texture_type in enumerate(mat_values["textures"].keys()):
                texture_path = mat_values["textures"][texture_type]
                node_position = (texture_frame_x, texture_frame_y)
                texture_frame_y -= 300.0
                node_img = create_img_node(game_path, nodes, texture_path, node_position, use_loaded_tex=use_loaded_tex, use_png_cache=use_png_cache, overwrite_png_cache=overwrite_png_cache, use_HD_texture=use_HD_texture)
                node_img.parent = texture_frame
                node_img.label = texture_type
                mat[texture_type] = texture_path
                
                if texture_type in ["BaseDielectricMap"]:
                    links.new(node_UVMap1.outputs["UV"], node_img.inputs["Vector"])
                    links.new(node_img.outputs["Color"], nodes["Principled BSDF"].inputs["Base Color"])
                    #links.new(node_img.outputs["Alpha"], nodes["Principled BSDF"].inputs["Metallic"])
                
                if texture_type in ["AlphaMap"]:
                    links.new(node_UVMap1.outputs["UV"], node_img.inputs["Vector"])
                    links.new(node_img.outputs["Color"], nodes["Principled BSDF"].inputs["Alpha"])
                    mat.blend_method = "HASHED"
                    mat.shadow_method = "HASHED"
                
        else:
            # Known mat
            multimaps = {}
            #multimaps = {
                #"Env_Wave.mmtr":["wave_displacementmap"],
                #"Env_Water.mmtr":["BaseMap", "NormalMap", "AlphaMap"],
                #"VertexColorBlend_B_Magma.mmtr":["BaseDielectricMap", "BaseDielectricMap_R", "BaseDielectricMap_G", "BaseDielectricMap_B", "NormalRoughnessMap", "NormalRoughnessMap_R", "NormalRoughnessMap_G", "NormalRoughnessMap_B"],
                #"Flow_Transparent.mmtr":["BaseMap", "AlphaMap", "NormalRoughnessMap"],
                #"FLOW_CLOUD.mmtr":["BaseMap", "AlphaMap", "NormalRoughnessMap"],
                #"Flow.mmtr":["BaseMap", "AlphaMap", "NormalRoughnessMap"],
                #"Flow_A.mmtr":["BaseMap", "AlphaMap", "NormalRoughnessMap"],
                #"Flow_B.mmtr":["BaseMap", "AlphaMap", "NormalRoughnessMap"],
                #"Flow_VertexAlpha.mmtr":["BaseMap", "AlphaMap", "NormalRoughnessMap"],
                #"Env_Water_WM.mmtr":["BaseMap", "AlphaMap", "NormalMap"],
                #"WaterColor.mmtr":["BaseMap", "NormalMap"],
                #"Env_WaterColor_WM.mmtr":["BaseMap", "NormalMap"],
                #"Env_WaterColor_Standard.mmtr":["BaseMap", "NormalMap"],
                #"Env_WaterColor_Decal.mmtr":["BaseMap", "NormalMap"],
                #"Env_JuekiNuma.mmtr":["BaseMap", "NormalMap"]
            #}
            
            mmtr_pre = nodes.new(type='ShaderNodeGroup')
            mmtr_pre.location = Vector((-1200.0, 500.0))
            mmtr_pre.node_tree = bpy.data.node_groups[group_name + "_pre"]
            mmtr_pre.label = group_name_original
            
            mmtr_post = nodes.new(type='ShaderNodeGroup')
            mmtr_post.location = Vector((-700.0, 500.0))
            mmtr_post.node_tree = bpy.data.node_groups[group_name + "_post"]
            mmtr_post.label = group_name_original
            
            for property_i, property_type in enumerate(mat_values["properties"].keys()):
                property_value = mat_values["properties"][property_type]

                # Skip creating the property if simplification is enabled
                if simplify_mat:
                    enable_node = False
                    for node in mmtr_pre.node_tree.nodes:
                        if node.type == "GROUP_INPUT":
                            if len(node.outputs[property_type].links) != 0:
                                enable_node = True
                            break
                    for node in mmtr_post.node_tree.nodes:
                        if node.type == "GROUP_INPUT":
                            if len(node.outputs[property_type].links) != 0:
                                enable_node = True
                            break
                    if not enable_node:
                        continue


                if type(property_value) is list:
                    node_listvalues = []
                    #for single_value_i, single_value in enumerate(property_value):
                        #node_value = nodes.new(type='ShaderNodeValue')
                        #node_value.location = Vector((property_frame_x + single_value_i*100, property_frame_y - property_i*100.0))
                        #node_value.label = property_type + "_" + str(single_value_i)
                        #node_value.outputs["Value"].default_value = single_value
                        #node_value.parent = property_frame
                        #node_listvalues.append(node_value)
                    if mmtr_pre.inputs[property_type].type == "RGBA":
                        mmtr_pre.inputs[property_type].default_value = Vector(property_value)
                        mmtr_post.inputs[property_type].default_value = Vector(property_value)
                        node_RGB = nodes.new(type='ShaderNodeRGB')
                        node_RGB.location = Vector((property_frame_x, property_frame_y))
                        property_frame_y -= 200.0
                        node_RGB.parent = property_frame
                        node_RGB.outputs["Color"].default_value = Vector(property_value)
                        node_RGB.label = property_type
                        links.new(node_RGB.outputs["Color"], mmtr_pre.inputs[property_type])
                        links.new(node_RGB.outputs["Color"], mmtr_post.inputs[property_type])
                    elif mmtr_pre.inputs[property_type].type == "VECTOR":
                        mmtr_pre.inputs[property_type].default_value = Vector(property_value[:3])
                        mmtr_post.inputs[property_type].default_value = Vector(property_value[:3])
                        node_XYZ = nodes.new(type='ShaderNodeCombineXYZ')
                        node_XYZ.location = Vector((property_frame_x, property_frame_y))
                        property_frame_y -= 150.0
                        node_XYZ.parent = property_frame
                        node_XYZ.inputs["X"].default_value = property_value[0]
                        node_XYZ.inputs["Y"].default_value = property_value[1]
                        node_XYZ.inputs["Z"].default_value = property_value[2]
                        node_XYZ.label = property_type
                        node_W = nodes.new(type='ShaderNodeValue')
                        node_W.location = Vector((property_frame_x, property_frame_y))
                        property_frame_y -= 100.0
                        node_W.parent = property_frame
                        node_W.outputs["Value"].default_value = property_value[3]
                        node_W.label = property_type + "_W"
                        links.new(node_XYZ.outputs["Vector"], mmtr_pre.inputs[property_type])
                        links.new(node_XYZ.outputs["Vector"], mmtr_post.inputs[property_type])
                else:
                    mmtr_pre.inputs[property_type].default_value = property_value
                    mmtr_post.inputs[property_type].default_value = property_value
                    node_value = nodes.new(type='ShaderNodeValue')
                    node_value.location = Vector((property_frame_x, property_frame_y))
                    property_frame_y -= 100.0
                    node_value.label = property_type
                    node_value.outputs["Value"].default_value = property_value 
                    node_value.parent = property_frame
                    links.new(node_value.outputs["Value"], mmtr_pre.inputs[property_type])
                    links.new(node_value.outputs["Value"], mmtr_post.inputs[property_type])
                    
            #if "Frame" in mmtr_pre.inputs or "Frame" in mmtr_post.inputs:
                #if "grass" in group_name.lower() and not enable_foliage:
                    #pass
                #elif "flow" in group_name.lower() and not enable_flow:
                    #pass
                #else:
                    #frame_count = nodes.new(type='ShaderNodeGroup')
                    #frame_count.location = Vector((general_frame_x, general_frame_y-700.0))
                    #frame_count.node_tree = bpy.data.node_groups["FrameCount"]
                    #frame_count.parent = general_frame
                    #if "Frame" in mmtr_pre.inputs:
                        #links.new(frame_count.outputs["Frame"], mmtr_pre.inputs["Frame"])
                    #if "Frame" in mmtr_post.inputs:
                        #links.new(frame_count.outputs["Frame"], mmtr_post.inputs["Frame"])
            
            links.new(node_UVMap1.outputs["UV"], mmtr_pre.inputs["TexCoord1"])
            links.new(node_UVMap2.outputs["UV"], mmtr_pre.inputs["TexCoord2"])
            links.new(node_VertexColor.outputs["Color"], mmtr_pre.inputs["VertexColor"])
            links.new(node_VertexColor.outputs["Color"], mmtr_post.inputs["VertexColor"])

            try:
                links.new(node_geometry.outputs["Normal"], mmtr_post.inputs["Geometry"])
            except:
                pass
            for output in mmtr_pre.outputs.keys():
                try:
                    links.new(mmtr_pre.outputs[output], mmtr_post.inputs[output])
                except:
                    pass
            
            for texture_i, texture_type in enumerate(mat_values["textures"].keys()):
                texture_path = mat_values["textures"][texture_type]
                mat[texture_type] = texture_path

                # Skip creating the texture if simplification is enabled
                if simplify_mat:
                    enable_texture = False
                    for node in mmtr_pre.node_tree.nodes:
                        if node.type == "GROUP_INPUT":
                            if len(node.outputs[texture_type + "_RGB"].links) != 0 or len(node.outputs[texture_type + "_A"].links) != 0:
                                enable_texture = True
                            break
                    for node in mmtr_post.node_tree.nodes:
                        if node.type == "GROUP_INPUT":
                            if len(node.outputs[texture_type + "_RGB"].links) != 0 or len(node.outputs[texture_type + "_A"].links) != 0:
                                enable_texture = True
                            break
                    if not enable_texture:
                        continue

                if group_name in multimaps and texture_type in multimaps[group_name]:
                    node_position = (texture_frame_x, texture_frame_y)
                    texture_frame_y -= 250.0
                    img_node_1 = create_img_node(game_path, nodes, texture_path, node_position, use_loaded_tex=use_loaded_tex, use_png_cache=use_png_cache, overwrite_png_cache=overwrite_png_cache, use_HD_texture=use_HD_texture)
                    img_node_1.parent = texture_frame

                    img_node_1.label = texture_type
                    node_position = (texture_frame_x, texture_frame_y)
                    texture_frame_y -= 300.0
                    img_node_2 = create_img_node(game_path, nodes, texture_path, node_position, use_loaded_tex=use_loaded_tex, use_png_cache=use_png_cache, overwrite_png_cache=overwrite_png_cache, use_HD_texture=use_HD_texture)
                    img_node_2.parent = texture_frame
                    img_node_2.label = texture_type + " FLOW WARPING"
                    links.new(mmtr_pre.outputs["vector_" + texture_type + "_1"], img_node_1.inputs["Vector"])
                    links.new(mmtr_pre.outputs["vector_" + texture_type + "_2"], img_node_2.inputs["Vector"])
                    links.new(img_node_1.outputs["Color"], mmtr_post.inputs[texture_type + "_RGB_1"])
                    links.new(img_node_2.outputs["Color"], mmtr_post.inputs[texture_type + "_RGB_2"])
                    links.new(img_node_1.outputs["Alpha"], mmtr_post.inputs[texture_type + "_A_1"])
                    links.new(img_node_2.outputs["Alpha"], mmtr_post.inputs[texture_type + "_A_2"])
                    links.new(node_object_info.outputs["Location"], mmtr_pre.inputs["Random"])
                else:
                    node_position = (texture_frame_x, texture_frame_y)
                    texture_frame_y -= 300.0
                    node_img = create_img_node(game_path, nodes, texture_path, node_position, use_loaded_tex=use_loaded_tex, use_png_cache=use_png_cache, overwrite_png_cache=overwrite_png_cache, use_HD_texture=use_HD_texture)
                    node_img.parent = texture_frame
                    node_img.label = texture_type
                    
                    if texture_type in [
                        "FlowMap", 
                        "FlowMap_ALB", 
                        "FlowMap_REF", 
                    ]:
                        #links.new(mmtr_pre.outputs["vector_" + texture_type], node_img.inputs["Vector"])
                        links.new(node_img.outputs["Color"], mmtr_pre.inputs[texture_type + "_RGB"])
                        links.new(node_img.outputs["Alpha"], mmtr_pre.inputs[texture_type + "_A"])
                    else:
                        links.new(mmtr_pre.outputs["vector_" + texture_type], node_img.inputs["Vector"])
                        links.new(node_img.outputs["Color"], mmtr_post.inputs[texture_type + "_RGB"])
                        links.new(node_img.outputs["Alpha"], mmtr_post.inputs[texture_type + "_A"])
            
            has_alpha = ("Fur_HeightMap" in mat_values["textures"].keys() or
                "AlphaTranslucentOcclusionSSSMap" in mat_values["textures"].keys() or
                "AlphaTranslucentOcclusionCavityMap" in mat_values["textures"].keys() or
                "AlphaMap" in mat_values["textures"].keys() or
                "NormalRoughnessAlphaMap" in mat_values["textures"].keys() or
                group_name in ["Character_Eyelash", "Character_Eyebrow", "Character_Hair", "Character_HairCap"]
            )
            if group_name in [
                "Character_EnemyLarge_Dragon",
                "Character_Enemy_PoisonLizard",
                "Character_Enemy_RockLizard",
                "Character_Enemy_RockLizard_EmissiveAnim"]:
                has_alpha = False

            for mmtr_output_key in mmtr_post.outputs.keys():
                try:
                    if mmtr_output_key == "Alpha" and not has_alpha:
                        continue

                    links.new(mmtr_post.outputs[mmtr_output_key], dd2_shader_node.inputs[mmtr_output_key])
                except:
                    pass
            #if "Translucency Color" not in mmtr_post.outputs.keys():
                #links.new(mmtr_post.outputs["Base Color"], dd2_shader_node.inputs["Translucency Color"])

            for mmtr_output_key in mmtr_post.outputs.keys():
                try:
                    links.new(mmtr_post.outputs[mmtr_output_key], node_output.inputs[mmtr_output_key])
                except:
                    pass
            #if "Displacement" in mmtr_post.outputs and "VertexShaderUsed" in mat.keys() and mat["VertexShaderUsed"]:
                #links.new(mmtr_post.outputs["Displacement"], nodes["Material Output"].inputs["Displacement"])
                #mat.cycles.displacement_method = "BOTH"
            #if "Translucency Color" in mmtr_post.outputs:
                #translucency_node = nodes.new(type='ShaderNodeGroup')
                #translucency_node.location = Vector((300.0, 300.0))
                #translucency_node.node_tree = bpy.data.node_groups["Translucency"]
                #translucency_node.label = "Translucency"
                #links.new(mmtr_post.outputs["Translucency Color"], translucency_node.inputs["Translucency Color"])
                #links.new(mmtr_post.outputs["Alpha"], translucency_node.inputs["Alpha"])
                #links.new(mmtr_post.outputs["Normal"], translucency_node.inputs["Normal"])
                #links.new(nodes["Principled BSDF"].outputs["BSDF"], translucency_node.inputs["BSDF"])
                #links.new(translucency_node.outputs["Shader"], nodes["Material Output"].inputs["Surface"])
                #nodes["Material Output"].location = Vector((500.0, 300.0))
            if has_alpha:
                mat.blend_method = "HASHED"
                mat.shadow_method = "HASHED"
            #pass
        
        
        returned_mats.append(mat)
    return returned_mats
