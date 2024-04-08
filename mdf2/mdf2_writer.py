import bpy

import struct
import math
import time
import os
import json
import logging
logger = logging.getLogger("dd2_import")

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

#def mmh3(key, lenght, seed):
    #c1 = 0xcc9e2d51
    #c2 = 0x1b873593
    #r1 = 15
    #r2 = 13
    #n = 0xe6546b64
    
    #hash = seed
    
    #def rol(n,rotations,width):
        #return (2**width-1)&(n<<rotations|n>>(width-rotations))

    #def ROL(a, b, size):
        #return (a>>b) | (a<<(8*size-b))
    #while True:
        #k = int.frombytes(key[:4], "big")
        #key = key[4:]
        #k *= c1
        #k = rol(k, r1, 32)
        #k *= 2
        
        #hash = hash ^ k
        #hash = rol(hash, r2, 32)
        #hash = (hash*m) + n

def murmurhash_32( key, seed = 0x0 ): 
    def fmix( h ):
        h ^= h >> 16
        h  = ( h * 0x85ebca6b ) & 0xFFFFFFFF
        h ^= h >> 13
        h  = ( h * 0xc2b2ae35 ) & 0xFFFFFFFF
        h ^= h >> 16
        return h
    length = len( key )
    nblocks = int( length / 4 )
    h1 = seed
    c1 = 0xcc9e2d51
    c2 = 0x1b873593
    for block_start in range( 0, nblocks * 4, 4 ):
        k1 = key[ block_start + 3 ] << 24 | \
             key[ block_start + 2 ] << 16 | \
             key[ block_start + 1 ] <<  8 | \
             key[ block_start + 0 ]
        k1 = ( c1 * k1 ) & 0xFFFFFFFF
        k1 = ( k1 << 15 | k1 >> 17 ) & 0xFFFFFFFF 
        k1 = ( c2 * k1 ) & 0xFFFFFFFF
        h1 ^= k1
        h1  = ( h1 << 13 | h1 >> 19 ) & 0xFFFFFFFF 
        h1  = ( h1 * 5 + 0xe6546b64 ) & 0xFFFFFFFF
    tail_index = nblocks * 4
    k1 = 0
    tail_size = length & 3
    if tail_size >= 3:
        k1 ^= key[ tail_index + 2 ] << 16
    if tail_size >= 2:
        k1 ^= key[ tail_index + 1 ] << 8
    if tail_size >= 1:
        k1 ^= key[ tail_index + 0 ]
    if tail_size > 0:
        k1  = ( k1 * c1 ) & 0xFFFFFFFF
        k1  = ( k1 << 15 | k1 >> 17 ) & 0xFFFFFFFF 
        k1  = ( k1 * c2 ) & 0xFFFFFFFF
        h1 ^= k1
    unsigned_val = fmix( h1 ^ length )
    return unsigned_val

class Writer():
    def __init__(self):
        self.data = b""
    
    def tell(self):
        return len(self.data)
    
    def write(self, kind, value):
        self.data += struct.pack(kind, value)

    def write_list(self, kind, value):
        self.data += struct.pack(str(len(value))+kind, *value)
    
    def writeAt(self, kind, offset, value):
        self.data = self.data[:offset] + struct.pack(kind, value) + self.data[offset+struct.calcsize(kind):]
    
    def writeUInt64(self, value):
        self.write("Q", value)
    
    def writeUInt64s(self, value):
        self.write_list("Q", value)

    def writeUInt(self, value):
        self.write("I", value)
    
    def writeUInts(self, value):
        self.write_list("I", value)

    def writeUInt64At(self, offset, value):
        self.writeAt("Q", offset, value)

    def writeUIntAt(self, offset, value):
        self.writeAt("I", offset, value)
    
    def writeIntAt(self, offset, value):
        self.writeAt("i", offset, value)
    
    def writeFloat(self, value):
        self.write("f", value)
    
    def writeFloats(self, value):
        self.write_list("f", value)
        
    def writeHalf(self, value):
        self.write("e", value)
    
    def writeHalfs(self, value):
        self.write_list("e", value)
    
    def writeUShort(self, value):
        self.write("H", value)
        
    def writeUShorts(self, value):
        self.write_list("H", value)
    
    def writeUByte(self, value):
        if math.isnan(value):
            value = 0
        if value > 255:
            value = 255
        if value < 0:
            value = 0
        self.write("B", value)
    
    def writeUBytes(self, value):
        self.write_list("B", value)
    
    def writeByte(self, value):
        if math.isnan(value):
            value = 0
        if value > 127:
            value = 127
        if value < -128:
            value = -128
        self.write("b", value)
    
    def writeBytes(self, value):
        self.write_list("b", value)

    def writeString(self, value):
        for char in value:
            self.write("B", ord(char))
        self.write("B", 0)
    
    def writeStringUTF(self, value):
        for char in value:
            self.write("H", ord(char))
        self.write("H", 0)

    def padUntilAlligned(self, size):
        for pad_i in range((size - (len(self.data)%size))%size):
            self.writeUByte(0)


def export_materials(selected_objects, skip_uv_islands=False, force_buffer_export=False):
    beware = False

    try:
        with open(os.path.join(os.path.dirname(__file__), "all_materials_template_alias.json"), "r") as json_in:
            material_template_dict = json.load(json_in)
    except Exception as e:
        raise RuntimeError("Error while trying to load the material template file: exception = " + str(e))

    mesh_object_count = 0
    # Going over all objects in the collection, keeping the valid meshes and the armatures
    # This is mostly to force the user to check if their shit is correctly set, I could fix a lot of stuff myself but
    # that would imply modifying the user's scene, and I don't want to have that responsability
    obj_ids = []
    lods = []
    available_materials = []

    for obj in selected_objects:
        try:
            if obj.type == "MESH":
                mesh_object_count += 1
                splitted_name = obj.name.split("_")
                if len(splitted_name) >= 3:
                    try:
                        lod = int(splitted_name[0][len("LOD"):])
                        group = int(splitted_name[1][len("G"):])
                        submesh = int(splitted_name[2][len("S"):])
                        lods.append(lod)
                    except:
                        beware = True
                        raise RuntimeError("Could not deduce LOD, GROUP and SUBMESH data from object name: make sure the object name is in the format \"LOD<number>_G<number>_S<number>_...\"")
                    # Check triangulation
                    for polygon in obj.data.polygons:
                        if len(polygon.loop_indices) != 3:
                            beware = True
                            raise RuntimeError("Mesh is not triangulated! ")
                    # Check UV1
                    if len(obj.data.uv_layers) == 0:
                        beware = True
                        raise RuntimeError("Mesh does not have UVs! ")
                    if not skip_uv_islands:
                        # Check for uv island separation
                        # What this checks is the proper attribution of data to vertices instead of face corners, but it's HARD
                        # It does that by checking if any vertice has more than 2 uv coordinates attributed to it. Technically it's missing cases like color attribution for example, but fuck it
                        for uv_layer in obj.data.uv_layers:
                            vertice_uv_coords = {}
                            for loop, uv in zip(obj.data.loops, uv_layer.uv):
                                if loop.vertex_index not in vertice_uv_coords.keys():
                                    vertice_uv_coords[loop.vertex_index] = uv.vector
                                else:
                                    if (vertice_uv_coords[loop.vertex_index] - uv.vector).length > 0.01:
                                        beware = True
                                        raise RuntimeError("Mesh's UV islands aren't physically separated. .mesh files only support data attributed to vertices instead of face corners like in blender, so you'll have to split the vertices of each UV island. Do that by going in uv editing mode, selecting everything, F3->Seams from islands, selecting one of the seam in edit mode, Shift->G then \"seam\", and tapping \"V\" once.")
                    if len(obj.material_slots) == 1 and obj.material_slots != None and obj.material_slots[0].name != "":
                        material = obj.material_slots[0].name
                    else:
                        beware = True
                        raise RuntimeError("Mesh has no material! ")
                    # Making sure there are no duplicates
                    obj_id = str(lod).zfill(3) + str(group).zfill(3) + str(submesh).zfill(3)
                    if obj_id not in obj_ids:
                        obj_ids.append(obj_id)
                        if material not in available_materials:
                            available_materials.append(material)
                    else:
                        beware = True
                        raise RuntimeError("Object of lod " + str(lod) + ", group " + str(group) + " and submesh " + str(submesh) + " found more than once! ")

                else:
                    beware = True
                    raise RuntimeError("Could not find lod/group/submesh info in its name! ")
            else:
                beware = True
                raise RuntimeError("Not a mesh! ")
        except Exception as e:
            beware = True
            logger.warning("Skipped object " + obj.name + ", reason = " + str(e))
            continue

    if len(obj_ids) == 0:
        beware = True
        raise RuntimeError("No valid meshes found: started with " + str(mesh_object_count) + " meshes but got 0 after filtering for issues. Check the system console for the reasons each were skipped. ")

    available_materials = available_materials[::-1]
    if len(available_materials) == 0:
        raise RuntimeError("No materials could be extracted from the selection! ")

    logger.info("Found the following materials: " + str(available_materials))
    material_datas = []
    for material_name in available_materials:
        logger.info("Analysing material " + material_name)
        material = bpy.data.materials[material_name]

        nodes = material.node_tree.nodes
        
        if "mmtr_path" not in material.keys():
            raise RuntimeError("Missing mmtr_path custom property in the material.")

        try:
            material_type = str(material["mmtr_path"])
        except:
            raise RuntimeError("Could not convert mmtr_path value to string.")
        if material_type not in material_template_dict.keys():
            raise RuntimeError("mmtr_path not found in the material reference dictionnary (mmtr_path = " + material_type + ")")

        # Find everything
        #properties_nodes_raw = []
        properties_nodes_dict = {}
        for node in nodes:
            if node.type in ["RGB", "VALUE", "COMBXYZ"]:
                if node.parent is not None and node.parent.type == "FRAME" and node.parent.label == "Properties" and node.label in material_template_dict[material_type]["properties"]:
                    if node.label in properties_nodes_dict.keys():
                        logger.warning("Property " + str(node.label) + " found multiple times.")
                        beware = True
                    properties_nodes_dict[node.label] = node
                    #properties_nodes_raw.append([node, node.label])
                    
        #properties_nodes_raw.sort(key = lambda x: -x[1].y)
        #properties_nodes = [x[0] for x in properties_nodes_raw]

        shader_types_rvrs = {v:k for k,v in shader_types.items()}
        flag1_bits_rvrs = {v:k for k,v in flag1_bits.items()}
        flag2_bits_rvrs = {v:k for k,v in flag2_bits.items()}
        flag3_bits_rvrs = {v:k for k,v in flag3_bits.items()}

        shader_type = 0
        if "shader_type" in material.keys() and type(material["shader_type"]) == str:
            if material["shader_type"] in shader_types_rvrs:
                shader_type = shader_types_rvrs[material["shader_type"]]


        flag1 = 0
        if "flag1" in material.keys():
            flag1 = material["flag1"]
        #for flag1_key in flag1_bits_rvrs.keys():
            #if flag1_key in material.keys() and type(material[flag1_key]) == bool:
                #flag1 += (2**flag1_bits_rvrs[flag1_key]) * int(material[flag1_key])

        flag2 = 0
        if "flag2" in material.keys():
            flag2 = material["flag2"]
        #for flag2_key in flag2_bits_rvrs.keys():
            #if flag2_key in material.keys() and type(material[flag2_key]) == bool:
                #flag2 += (2**flag2_bits_rvrs[flag2_key]) * int(material[flag2_key])

        flag3 = 0
        if "flag3" in material.keys():
            flag3 = material["flag3"]
        #for flag3_key in flag3_bits_rvrs.keys():
            #if flag3_key in material.keys() and type(material[flag3_key]) == bool:
                #flag3 += (2**flag3_bits_rvrs[flag3_key]) * int(material[flag3_key])

        phong = 0
        if "phong" in material.keys():
            phong = material["phong"]
        #if "Phong" in material.keys() and type(material["Phong"]) == float:
            #try:
                #phong = int(material["Phong"]*255.0)
                #if phong < 0:
                    #phong = 0
                #if phong > 255:
                    #phong = 255
            #except:
                #phong = 0

        unknown_hash1 = 0
        unknown_hash2 = 0
        if "unknown_hash1" in material.keys():
            unknown_hash1 = material["unknown_hash1"]
        if "unknown_hash2" in material.keys():
            unknown_hash2 = material["unknown_hash2"]

        buffers = []
        if not force_buffer_export:
            try:
                if "buffer_count" in material.keys():
                    buffer_count = int(material["buffer_count"])
                    for buffer_i in range(buffer_count):
                        buffer_data = {}
                        buffer_data["buffer_type"] = material["buffer_type_"+str(buffer_i)]
                        buffer_data["buffer_file_path"] = material["buffer_file_path_"+str(buffer_i)]
                        buffer_data["unk1"] = material["buffer_unk1_"+str(buffer_i)]
                        buffer_data["unk2"] = material["buffer_unk2_"+str(buffer_i)]
                        buffers.append(buffer_data)
            except Exception as e:
                logger.warning("Skipped buffer: this may happen when a material from an older version is exported. reason = " + str(e))
                buffers = []
        else:
            buffers = [
                {
                    "buffer_type":"RainAddressBuffer",
                    "buffer_file_path":"MaterialShader/ByteAddressBuffer/CharacterRainByteAddressBuffer.gpbf",
                    "unk1":0,
                    "unk2":1
                },
                {
                    "buffer_type":"CharacterFadeBuffer",
                    "buffer_file_path":"MaterialShader/ByteAddressBuffer/CharacterFadeByteAddressBuffer.gpbf",
                    "unk1":0,
                    "unk2":1
                }
            ]

        material_texture_data = {}
        for texture_type in material_template_dict[material_type]["textures"]:
            try:
                if texture_type in material.keys():
                    try:
                        material_texture_data[texture_type] = str(material[texture_type])
                    except:
                        raise RuntimeError("Could not convert value to string.")
                else:
                    raise RuntimeError("Texture type not found in the material properties.")
            except Exception as e:
                logger.warning("Skipped texture " + str(texture_type) + ", reason = " + str(e))
                beware = True

        if set(material_texture_data.keys()) != set(material_template_dict[material_type]["textures"]):
            raise RuntimeError("Missing textures for material: " + str(set(material_texture_data.keys()) ^ set(material_template_dict[material_type]["textures"])))

        material_property_data = {}
        logger.info("Found " + str(len(properties_nodes_dict)) + " candidate properties nodes.")
        for property_name, property_type in material_template_dict[material_type]["properties"].items():
            if property_name not in properties_nodes_dict.keys():
                continue

            property_node = properties_nodes_dict[property_name]

            if property_type == "list":
                if property_node.type == "RGB":
                    material_property_data[property_name] = [
                        property_node.outputs["Color"].default_value[0],
                        property_node.outputs["Color"].default_value[1],
                        property_node.outputs["Color"].default_value[2],
                        property_node.outputs["Color"].default_value[3]
                    ]
                elif property_node.type == "COMBXYZ":
                    material_property_data[property_name] = [
                        property_node.inputs["X"].default_value,
                        property_node.inputs["Y"].default_value,
                        property_node.inputs["Z"].default_value,
                        1.0
                    ]
                else:
                    raise RuntimeError("Expected node of type RGB or COMBXYZ.")
            else:
                if property_node.type == "VALUE":
                    material_property_data[property_name] = property_node.outputs["Value"].default_value
                else:
                    raise RuntimeError("Expected node of type VALUE.")

        if set(material_property_data.keys()) != set(material_template_dict[material_type]["properties"].keys()):
            raise RuntimeError("Missing properties for material: " + str(set(material_property_data.keys()) ^ set(material_template_dict[material_type]["properties"].keys())))
        
        material_datas.append({
            "material_name":material_name, 
            "material_type":material_type, 
            "material_texture_data":material_texture_data, 
            "material_property_data":material_property_data,
            "shader_type":shader_type,
            "flag1":flag1,
            "flag2":flag2,
            "phong":phong,
            "flag3":flag3,
            "unknown_hash1":unknown_hash1,
            "unknown_hash2":unknown_hash2,
            "buffers":buffers
        })
    return material_datas, beware

def write_mdf2(material_datas):
    beware = False

    writer = Writer()
    writer.writeUInt(4605005) # Magic
    writer.writeUShort(1) # ?
    writer.writeUShort(len(material_datas)) # material count
    writer.padUntilAlligned(16)
    material_offsets_list = []
    for material_i, material_data in enumerate(material_datas):
        material_offsets_list.append({})
        material_offsets_list[material_i]["name_offset"] = writer.tell()
        writer.writeUInt64(0) # name offset
        writer.writeUInt(murmurhash_32(material_data["material_name"].encode("utf-16LE"), 0xFFFFFFFF)) # name hash
        prop_block_size = 0
        for property_name, property_value in material_data["material_property_data"].items():
            if type(property_value) == list:
                prop_block_size += 16
            else:
                prop_block_size += 4
        while prop_block_size%16 != 0:
            prop_block_size += 4
        writer.writeUInt(prop_block_size) # property block size
        writer.writeUInt(len(material_data["material_property_data"])) # property count
        writer.writeUInt(len(material_data["material_texture_data"])) # property count
        writer.writeUInt(len(material_data["buffers"])) #
        writer.writeUInt(len(material_data["buffers"])) # buffer count, but not dealing with them atm
        writer.writeUInt(material_data["shader_type"]) # Shader type
        writer.writeUByte(material_data["flag1"]) # flags 
        writer.writeUByte(material_data["flag2"]) # flags
        writer.writeUByte(material_data["phong"])
        writer.writeUByte(material_data["flag3"]) # flags 
        writer.writeUShort(material_data["unknown_hash1"])
        writer.writeUShort(material_data["unknown_hash2"])
        writer.writeUInt64(0) # Always 0
        material_offsets_list[material_i]["property_header_offset"] = writer.tell()
        writer.writeUInt64(0) # property header offset
        material_offsets_list[material_i]["texture_header_offset"] = writer.tell()
        writer.writeUInt64(0) # texture header offset
        material_offsets_list[material_i]["buffer_header_offset"] = writer.tell()
        writer.writeUInt64(0) # buffer header offset
        material_offsets_list[material_i]["properties_data_offset"] = writer.tell()
        writer.writeUInt64(0) # properties data offset
        material_offsets_list[material_i]["mmtr_path_offset"] = writer.tell()
        writer.writeUInt64(0) # mmtr path offset
        writer.writeUInt64(0) # Always 0
    textures_offsets_list = []
    for material_i, material_data in enumerate(material_datas):
        writer.writeUInt64At(material_offsets_list[material_i]["texture_header_offset"], writer.tell())
        textures_offsets_list.append({})
        for texture_type, texture_path in material_data["material_texture_data"].items():
            textures_offsets_list[material_i][texture_type] = {}
            textures_offsets_list[material_i][texture_type]["texture_type_offset"] = writer.tell()
            writer.writeUInt64(0)
            writer.writeUInt(murmurhash_32(texture_type.encode("utf-16LE"), 0xFFFFFFFF)) # name hash
            writer.writeUInt(murmurhash_32(texture_type.encode("utf-8"), 0xFFFFFFFF)) # name hash
            textures_offsets_list[material_i][texture_type]["texture_path_offset"] = writer.tell()
            writer.writeUInt64(0) #TODO
            writer.writeUInt64(0) #TODO
    properties_offsets_list = []
    
    for material_i, material_data in enumerate(material_datas):
        properties_counter = 0
        writer.writeUInt64At(material_offsets_list[material_i]["property_header_offset"], writer.tell())
        properties_offsets_list.append({})
        for property_name, property_value in material_data["material_property_data"].items():
            properties_offsets_list[material_i][property_name] = {}
            properties_offsets_list[material_i][property_name]["property_name_offset"] = writer.tell()
            writer.writeUInt64(0)
            writer.writeUInt(murmurhash_32(property_name.encode("utf-16LE"), 0xFFFFFFFF)) # name hash
            writer.writeUInt(murmurhash_32(property_name.encode("utf-8"), 0xFFFFFFFF)) # name hash
            writer.writeUInt(properties_counter)
            if type(property_value) == list:
                writer.writeUInt(4)
                properties_counter += 16
            else:
                writer.writeUInt(1)
                properties_counter += 4

    for material_i, material_data in enumerate(material_datas):
        writer.writeUInt64At(material_offsets_list[material_i]["buffer_header_offset"], writer.tell())
        material_offsets_list[material_i]["buffers"] = []
        for buffer_data in material_data["buffers"]:
            buffer_strings_offsets = {}
            buffer_strings_offsets["buffer_type_offset"] = writer.tell()
            writer.writeUInt64(0)
            buffer_strings_offsets["buffer_type"] = buffer_data["buffer_type"]

            writer.writeUInt(murmurhash_32(buffer_data["buffer_type"].encode("utf-16LE"), 0xFFFFFFFF)) # name hash
            writer.writeUInt(murmurhash_32(buffer_data["buffer_type"].encode("utf-8"), 0xFFFFFFFF)) # name hash
            buffer_strings_offsets["file_path_offset"] = writer.tell()
            writer.writeUInt64(0)
            buffer_strings_offsets["file_path"] = buffer_data["buffer_file_path"]

            writer.writeUInt(buffer_data["unk1"])
            writer.writeUInt(buffer_data["unk2"])
            material_offsets_list[material_i]["buffers"].append(buffer_strings_offsets)

    for material_i, material_data in enumerate(material_datas):
        writer.writeUInt64At(material_offsets_list[material_i]["name_offset"], writer.tell())
        writer.writeStringUTF(material_data["material_name"])
        writer.writeUInt64At(material_offsets_list[material_i]["mmtr_path_offset"], writer.tell())
        writer.writeStringUTF(material_data["material_type"])
        
        
    for material_i, material_data in enumerate(material_datas):
        for texture_type, texture_path in material_data["material_texture_data"].items():
            writer.writeUInt64At(textures_offsets_list[material_i][texture_type]["texture_type_offset"], writer.tell())
            writer.writeStringUTF(texture_type)
            writer.writeUInt64At(textures_offsets_list[material_i][texture_type]["texture_path_offset"], writer.tell())
            writer.writeStringUTF(texture_path)

    for material_i, material_data in enumerate(material_datas):
        for property_name, property_value in material_data["material_property_data"].items():
            writer.writeUInt64At(properties_offsets_list[material_i][property_name]["property_name_offset"], writer.tell())
            writer.writeStringUTF(property_name)

    for material_i, material_data in enumerate(material_datas):
        for buffer_data in material_offsets_list[material_i]["buffers"]:
            writer.writeUInt64At(buffer_data["buffer_type_offset"], writer.tell())
            writer.writeStringUTF(buffer_data["buffer_type"])
            writer.writeUInt64At(buffer_data["file_path_offset"], writer.tell())
            writer.writeStringUTF(buffer_data["file_path"])

    property_array_offset = writer.tell()
    for material_i, material_data in enumerate(material_datas):
        writer.writeUInt64At(material_offsets_list[material_i]["properties_data_offset"], writer.tell())
        for property_name, property_value in material_data["material_property_data"].items():
            if type(property_value) == list:
                [writer.writeFloat(x) for x in property_value]
            else:
                writer.writeFloat(property_value)
        while writer.tell()%16 != property_array_offset%16:
            writer.writeUByte(0)

    return writer.data, beware
