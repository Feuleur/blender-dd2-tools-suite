import struct
import codecs
import json
from glob import glob
import os
import math
import numpy as np
import logging
logger = logging.getLogger("dd2_import")

class Reader():
    def __init__(self, data):
        self.offset = 0
        self.data = data

    def read(self, kind, size):
        result = struct.unpack(kind, self.data[self.offset:self.offset+size])[0]
        self.offset += size
        return result

    def seek(self, offset, start = None):
        if start is None:
            self.offset = offset
        else:
            self.offset += offset

    def readUInt(self):
        return self.read("I", 4)

    def readInt(self):
        return self.read("i", 4)

    def readUInt64(self):
        return self.read("Q", 8)

    def readHalf(self):
        return self.read("e", 2)

    def readFloat(self):
        return self.read("f", 4)

    def readShort(self):
        return self.read("h", 2)

    def readUShort(self):
        return self.read("H", 2)

    def readByte(self):
        return self.read("b", 1)

    def readBytes(self, size):
        return self.data[self.offset:self.offset + size]

    def readUByte(self):
        return self.read("B", 1)

    def readString(self):
        text = ""
        while True:
            char = self.readUByte()
            if char == 0:
                break
            else:
                text += chr(char)
        return text

    def readStringUTF(self):
        text = ""
        while True:
            char = self.readUShort()
            if char == 0:
                break
            else:
                text += chr(char)
        return text

    def allign_soft(self, size, shift=0):
        if (self.offset-shift)%size == 0:
            pass
        else:
            self.allign(size)

    def allign(self, size):
        self.offset = (int((self.offset)/size)*size)+size

    def tell(self):
        return self.offset

    def getSize(self):
        return len(self.data)

class MeshParser():
    def __init__(self, path=None, data=None):
        self.path = path
        if data is None:
            with open(path, "rb") as file_in:
                data = file_in.read()
        self.bs = Reader(data)

    def read(self, LOD=0):
        debug = {}

        self.magic = self.bs.readUInt()
        self.version = self.bs.readUInt()
        if self.magic != 1213416781 or self.version != 230517984:
            raise RuntimeError(str(self.path) + " is not a dd2 mesh file (magic = " + str(self.magic) + ", version = " + str(self.version) + ")")

        self.file_size = self.bs.readUInt()
        self.bs.allign(16)
        flag_1 = debug["flag_1"] = self.bs.readUByte()
        flag_2 = debug["flag_2"] = self.bs.readUByte()
        _count = debug["_count"] = self.bs.readUShort()
        numnodes = self.bs.readUShort()
        self.bs.allign(8)


        unk1_offset = debug["unk1_offset"] = self.bs.readUInt64() #0
        lod_header_offset = debug["lod_header_offset"] = self.bs.readUInt64()
        lod_header_2_offset = debug["lod_header_2_offset"] = self.bs.readUInt64() #shadow LOD header?
        unk4_offset = debug["unk4_offset"] = self.bs.readUInt64() #0
        shapekey_offset = debug["shapekey_offset"] = self.bs.readUInt64()
        unk6_offset = debug["unk6_offset"] = self.bs.readUInt64()
        buffer_header_offset = debug["buffer_header_offset"] = self.bs.readUInt64()
        unk8_offset = debug["unk8_offset"] = self.bs.readUInt64() #0
        float_array_offset = debug["float_array_offset"] = self.bs.readUInt64()
        bone_bounding_boxes_offset = debug["bone_bounding_boxes_offset"] = self.bs.readUInt64()
        bones_offset = debug["bones_offset"] = self.bs.readUInt64()
        material_indice_table_offset = debug["material_indice_table_offset"] = self.bs.readUInt64()
        bone_indice_table_offset = debug["bone_indice_table_offset"] = self.bs.readUInt64()
        unk14_offset = debug["unk14_offset"] = self.bs.readUInt64()
        names_offset = debug["names_offset"] = self.bs.readUInt64()
        hash_offset = debug["hash_offset"] = self.bs.readUInt64() # Some hash(s)?
        element_header_offset = debug["element_header_offset"] = self.bs.readUInt64()
        vertex_buffer_offset = debug["vertex_buffer_offset"] = self.bs.readUInt64()
        sdftex_path_offset = debug["sdftex_path_offset"] = self.bs.readUInt64()

        if lod_header_offset == 0 or buffer_header_offset == 0 or material_indice_table_offset == 0 or names_offset == 0:
            raise NotImplementedError(str(self.path) + " is missing vital data for building a mesh object in blender (lod_header_offset = " + str(lod_header_offset) + ", buffer_header_offset = " + str(buffer_header_offset) + ", material_indice_table_offset = " + str(material_indice_table_offset) + ", names_offset = " + str(names_offset) + ")")


        # Float array
        float_array = debug["float_array"] = []
        if float_array_offset != 0:
            self.bs.seek(float_array_offset)
            float_array_size = self.bs.readUInt64()
            array_offset = self.bs.readUInt64()
            self.bs.seek(array_offset)
            float_array = debug["float_array"] = np.frombuffer(self.bs.readBytes(float_array_size), dtype=np.float32).tolist()
            self.bs.offset += float_array_size


        # SDFTEX PATH
        sdftex_path = ""
        if sdftex_path_offset != 0:
            self.bs.seek(sdftex_path_offset)
            sdftex_path = self.bs.readStringUTF()


        # LOD
        self.bs.seek(lod_header_offset)
        LOD_count = self.bs.readUByte()
        mat_count = self.bs.readUByte()
        UV_count = self.bs.readUByte()
        _ = self.bs.readUByte()
        total_submeshe_count = self.bs.readUInt()
        bounding_sphere_x = self.bs.readFloat()
        bounding_sphere_y = self.bs.readFloat()
        bounding_sphere_z = self.bs.readFloat()
        bounding_sphere_radius = self.bs.readFloat()
        bounding_box_x1 = self.bs.readFloat()
        bounding_box_y1 = self.bs.readFloat()
        bounding_box_z1 = self.bs.readFloat()
        _ = self.bs.readUInt()

        bounding_box_x2 = self.bs.readFloat()
        bounding_box_y2 = self.bs.readFloat()
        bounding_box_z2 = self.bs.readFloat()
        _ = self.bs.readUInt()
        #self.bs.allign(16)
        #_offset = self.bs.readUInt64()
        #_offset = self.bs.readUInt64()
        #_offset = self.bs.readUInt64()
        #_offset = self.bs.readUInt64()
        #_offset = self.bs.readUInt64()



        bounding_sphere = [[bounding_sphere_x, bounding_sphere_y, bounding_sphere_z, bounding_sphere_radius]]
        bounding_box = [[bounding_box_x1, bounding_box_y1, bounding_box_z1], [bounding_box_x2, bounding_box_y2, bounding_box_z2]]
        LOD_header_offset = self.bs.readUInt64()
        self.bs.seek(LOD_header_offset)
        LOD_offset_array = []
        for LOD_i in range(LOD_count):
            LOD_offset_array.append(self.bs.readUInt64())
        LOD_infos = []
        materials_idxs = []
        total_vertices = 0
        total_faces = 0
        LOD_0_total_vertices = 0
        for LOD_i, LOD_offset in enumerate(LOD_offset_array):

            self.bs.seek(LOD_offset)
            group_count = self.bs.readUShort()
            LOD_index = self.bs.readUShort()
            LOD_distance = self.bs.readFloat()
            group_array_offset = self.bs.readUInt64()
            self.bs.seek(group_array_offset)
            group_offsets = []
            for group_i in range(group_count):
                group_offsets.append(self.bs.readUInt64())
            group_infos = []
            for group_offset in group_offsets:
                #print(group_offset)
                self.bs.seek(group_offset)
                group_info = {}
                group_info["id"] = self.bs.readUByte()
                group_info["submesh_count"] = self.bs.readUByte()
                self.bs.readUShort()
                self.bs.readUInt()

                group_info["vertex_count"] = self.bs.readUInt()
                group_info["vertex_start"] = total_vertices
                #print(hex(self.bs.tell()), group_info["vertex_count"])
                total_vertices += group_info["vertex_count"]
                if LOD_index == 0:
                    LOD_0_total_vertices += group_info["vertex_count"]
                group_info["loop_count"] = self.bs.readUInt()
                total_faces += group_info["loop_count"]
                group_info["submeshes_info"] = []
                no_keep = False
                for submesh_i in range(group_info["submesh_count"]):
                    submesh_info = {}
                    submesh_info["material_idx"] = self.bs.readUShort()
                    materials_idxs.append(submesh_info["material_idx"])
                    submesh_info["wtf"] = self.bs.readUShort() #when that shit is set, it's like the vertices aren't in the file
                    if submesh_info["wtf"] != 0:
                        no_keep = True
                    submesh_info["loop_count"] = self.bs.readUInt()
                    submesh_info["loop_start"] = self.bs.readUInt()
                    submesh_info["vertex_start"] = self.bs.readUInt()
                    _ = self.bs.readUInt64()
                    _ = self.bs.readUInt()
                    if not no_keep:
                        group_info["submeshes_info"].append(submesh_info)
                if no_keep:
                    # Have to undo the previous work
                    total_faces -= group_info["loop_count"]
                    total_vertices -= group_info["vertex_count"]
                group_infos.append(group_info)
            LOD_infos.append({
                "id":LOD_index,
                "LOD_distance":LOD_distance,
                "groups":group_infos,
            })
        material_count = len(set(materials_idxs))
        # import json
        # print(json.dumps(LOD_infos, indent=4))

        # Names
        names = []
        self.bs.seek(names_offset)
        name_offset_array = []
        for node_i in range(numnodes):
            name_offset_array.append(self.bs.readUInt64())
        for name_offset in name_offset_array:
            self.bs.seek(name_offset)
            names.append(self.bs.readString())


        # Material indices
        material_indice_dict = {}
        material_indice_list = []
        self.bs.seek(material_indice_table_offset)
        for _ in range(material_count):
            mat_id = self.bs.readUShort()
            material_indice_dict[mat_id] = names[mat_id]
            material_indice_list.append(names[mat_id])
        #print(len(material_indice_list))
        #print(material_count)

        # Bones
        bone_infos = None
        if bones_offset != 0:
            self.bs.seek(bones_offset)
            bone_remap = []
            bone_count = self.bs.readUInt() # Bone count but we already have it
            bone_remap_count = self.bs.readUInt()
            _ = self.bs.readUInt64()
            bone_hierarchy_offset = self.bs.readUInt64()
            local_coords_offset = self.bs.readUInt64()
            global_coords_offset = self.bs.readUInt64()
            inv_global_coords_offset = self.bs.readUInt64()
            if bone_remap_count > 0:
                for _ in range(bone_remap_count):
                    bone_remap.append(self.bs.readUShort())
            else:
                bone_remap.append(0)
            self.bs.seek(bone_hierarchy_offset)
            if bone_count > 0:
                bone_infos = []
                for bone_i in range(bone_count):
                    bone_info = {}
                    bone_info["id"] = self.bs.readShort()
                    bone_info["parent"] = self.bs.readShort()
                    bone_info["sibling"] = self.bs.readShort()
                    bone_info["connexion"] = self.bs.readShort()
                    bone_info["symmetry"] = self.bs.readShort()
                    bone_info["unknown_property"] = self.bs.readShort()
                    if bone_info["id"] in bone_remap:
                        bone_info["remap"] = bone_remap.index(bone_info["id"])
                    else:
                        bone_info["remap"] = None
                    #_ = self.bs.readShort()
                    _ = self.bs.readShort()
                    _ = self.bs.readShort()
                    bone_infos.append(bone_info)

            self.bs.seek(local_coords_offset)
            for bone_i in range(bone_count):
                local_matrix = []
                local_matrix.append([self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat()])
                local_matrix.append([self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat()])
                local_matrix.append([self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat()])
                local_matrix.append([self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat()])
                bone_infos[bone_i]["local_matrix"] = local_matrix

            self.bs.seek(global_coords_offset)
            for bone_i in range(bone_count):
                global_matrix = []
                global_matrix.append([self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat()])
                global_matrix.append([self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat()])
                global_matrix.append([self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat()])
                global_matrix.append([self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat()])
                bone_infos[bone_i]["global_matrix"] = global_matrix

            self.bs.seek(inv_global_coords_offset)
            for bone_i in range(bone_count):
                inv_global_matrix = []
                inv_global_matrix.append([self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat()])
                inv_global_matrix.append([self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat()])
                inv_global_matrix.append([self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat()])
                inv_global_matrix.append([self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat()])
                bone_infos[bone_i]["inv_global_matrix"] = inv_global_matrix


        # Bone indices
        bone_indice_dict = {}
        if bone_indice_table_offset != 0:
            self.bs.seek(bone_indice_table_offset)
            for bone_i in range(bone_count):
                bone_id = self.bs.readUShort()
                bone_indice_dict[bone_id] = names[bone_id]
                bone_infos[bone_i]["name"] = names[bone_id]
            bone_indice_list = list(bone_indice_dict.values())


        ## Bone bounding boxes
        bbboxes = {}
        if bone_bounding_boxes_offset != 0:
            self.bs.seek(bone_bounding_boxes_offset)
            bbbox_count = self.bs.readUInt64()
            bbbox_array_offs = self.bs.readUInt64()
            self.bs.seek(bbbox_array_offs)


            for bbbox_i in range(bbbox_count):
                x1 = self.bs.readFloat()
                y1 = self.bs.readFloat()
                z1 = self.bs.readFloat()
                _ = self.bs.readFloat()
                x2 = self.bs.readFloat()
                y2 = self.bs.readFloat()
                z2 = self.bs.readFloat()
                _ = self.bs.readFloat()

                if len(bone_remap) == bbbox_count:
                    bbboxes[bone_indice_list[bone_remap[bbbox_i]]] = [
                        [x1, y1, z1],
                        [x2, y2, z2]
                    ]
                else:
                    bbboxes[bone_indice_list[bbbox_i]] = [
                        [x1, y1, z1],
                        [x2, y2, z2]
                    ]


        if shapekey_offset != 0:
            self.bs.seek(shapekey_offset)
            shapekey_amount = self.bs.readUInt64()
            shapekey_array_offset = self.bs.readUInt64()
            self.bs.seek(shapekey_array_offset)
            shapekey_infos = []
            for shapekey_i in range(shapekey_amount):
                shapekey_info = {}
                shapekey_info["data_offset"] = self.bs.readUInt64()
                shapekey_infos.append(shapekey_info)

            for shapekey_info in shapekey_infos:
                self.bs.seek(shapekey_info["data_offset"])
                shapekey_info["first_array_offset"] = self.bs.readUInt64()
                shapekey_info["second_array_offset"] = self.bs.readUInt64()

                self.bs.seek(shapekey_info["first_array_offset"])
                #print(LOD_0_total_vertices)
                shapekey_info["first_array"] = []
                for v_i in range(LOD_0_total_vertices):

                    v_idx = self.bs.readUShort()
                    unk = self.bs.readUShort()
                    shapekey_info["first_array"].append(v_idx)

                self.bs.seek(shapekey_info["second_array_offset"])
                for v_i in range(LOD_0_total_vertices):
                    v_idx = self.bs.readUShort()
                    unk = self.bs.readUShort()



        # Vertex data
        self.bs.seek(buffer_header_offset)
        element_header_offset = self.bs.readUInt64()
        vertex_buffer_offset = self.bs.readUInt64()
        shapekey_buffer_offset = self.bs.readUInt64()
        shapekey_buffer_reloffset = self.bs.readUInt()
        face_buffer_reloffset = self.bs.readUInt()
        elem_count = self.bs.readUShort()
        elem_count_2 = self.bs.readUShort()
        face_buffer_end_reloffset_1 = self.bs.readUInt()
        face_buffer_end_reloffset_2 = self.bs.readUInt()
        inverted_vertex_buffer_offset = self.bs.readUInt() #Uh? Wuh? Guh?
        shapekey_buffer_size = self.bs.readUInt()
        self.bs.seek(element_header_offset)
        elems_info = []
        for elem_i in range(elem_count):
            elem_info = {}
            elem_info["id"] = self.bs.readUShort()
            elem_info["size"] = self.bs.readUShort()
            elem_info["buffer_start"] = self.bs.readUInt()
            elems_info.append(elem_info)


        self.bs.seek(vertex_buffer_offset)
        #print(vertex_buffer_offset)
        pos_values = None
        normal_values = None
        uv1_values = None
        uv2_values = None
        weight_values = None
        color_values = None
        for elem_info in elems_info:

            if elem_info["id"] == 0: #POS
                self.bs.seek(vertex_buffer_offset + elem_info["buffer_start"])
                value_amount = total_vertices*3
                buffer_size = total_vertices*elem_info["size"]
                pos_values = np.array(struct.unpack(str(value_amount)+"f", self.bs.data[self.bs.offset:self.bs.offset+buffer_size])).reshape([total_vertices, -1])
            elif elem_info["id"] == 1: #NORMALS
                self.bs.seek(vertex_buffer_offset + elem_info["buffer_start"])
                value_amount = total_vertices*8
                buffer_size = total_vertices*elem_info["size"]
                normal_values = np.array(struct.unpack(str(value_amount)+"b", self.bs.data[self.bs.offset:self.bs.offset+buffer_size])).reshape([total_vertices, -1])
            elif elem_info["id"] == 2: #UV1
                self.bs.seek(vertex_buffer_offset + elem_info["buffer_start"])
                value_amount = total_vertices*2
                buffer_size = total_vertices*elem_info["size"]
                uv1_values = np.array(struct.unpack(str(value_amount)+"e", self.bs.data[self.bs.offset:self.bs.offset+buffer_size])).reshape([total_vertices, -1])
            elif elem_info["id"] == 3: #UV2
                self.bs.seek(vertex_buffer_offset + elem_info["buffer_start"])
                value_amount = total_vertices*2
                buffer_size = total_vertices*elem_info["size"]
                uv2_values = np.array(struct.unpack(str(value_amount)+"e", self.bs.data[self.bs.offset:self.bs.offset+buffer_size])).reshape([total_vertices, -1])
            elif elem_info["id"] == 4: #weights
                self.bs.seek(vertex_buffer_offset + elem_info["buffer_start"])
                value_amount = total_vertices*16
                buffer_size = total_vertices*elem_info["size"]
                weight_values = np.array(struct.unpack(str(value_amount)+"B", self.bs.data[self.bs.offset:self.bs.offset+buffer_size])).reshape([total_vertices, -1])
            elif elem_info["id"] == 5: #color

                self.bs.seek(vertex_buffer_offset + elem_info["buffer_start"])
                value_amount = total_vertices*4
                buffer_size = total_vertices*elem_info["size"]
                color_values = np.array(struct.unpack(str(value_amount)+"B", self.bs.data[self.bs.offset:self.bs.offset+buffer_size])).reshape([total_vertices, -1])
            self.bs.seek(vertex_buffer_offset + elem_info["buffer_start"] + buffer_size)


        self.bs.seek(vertex_buffer_offset + face_buffer_reloffset)
        face_buffer_offset = self.bs.tell()
        face_buffer_size = face_buffer_end_reloffset_1 - face_buffer_reloffset
        face_values = np.array(struct.unpack(str(face_buffer_size//2)+"H", self.bs.readBytes(face_buffer_size)))

        if shapekey_buffer_offset != 0:
            # There's a whole other weight array (that looks like an exact copy of the first one) at the end of the file, which is only there when the shapekeys(?) are activated
            # Need more examples to decide what to do with it

            self.bs.seek(shapekey_buffer_offset)
            value_amount = total_vertices*16
            buffer_size = total_vertices*16
            shapekey_weight_values = np.array(struct.unpack(str(value_amount)+"B", self.bs.data[self.bs.offset:self.bs.offset+buffer_size])).reshape([total_vertices, -1])

        for LOD_i, LOD_info in enumerate(LOD_infos):
            for group_i, group_info in enumerate(LOD_info["groups"]):
                for submesh_i, submesh_info in enumerate(group_info["submeshes_info"]):
                    face_start = submesh_info["loop_start"]//3
                    face_count = submesh_info["loop_count"]//3
                    vertex_start = submesh_info["vertex_start"]
                    if submesh_i != group_info["submesh_count"]-1:
                        vertex_count = group_info["submeshes_info"][submesh_i+1]["vertex_start"] - vertex_start
                    else:
                        vertex_count = group_info["vertex_start"] + group_info["vertex_count"] - vertex_start
                    if pos_values is not None:
                        LOD_infos[LOD_i]["groups"][group_i]["submeshes_info"][submesh_i]["pos"] = pos_values[vertex_start:vertex_start+vertex_count]
                    if normal_values is not None:
                        LOD_infos[LOD_i]["groups"][group_i]["submeshes_info"][submesh_i]["normals"] = normal_values[vertex_start:vertex_start+vertex_count,:3]/127.0
                    if uv1_values is not None:
                        LOD_infos[LOD_i]["groups"][group_i]["submeshes_info"][submesh_i]["uv1"] = np.stack([uv1_values[vertex_start:vertex_start+vertex_count,0], 1.0-uv1_values[vertex_start:vertex_start+vertex_count,1]]).transpose([1,0])
                    if uv2_values is not None:
                        LOD_infos[LOD_i]["groups"][group_i]["submeshes_info"][submesh_i]["uv2"] = np.stack([uv2_values[vertex_start:vertex_start+vertex_count,0], 1.0-uv2_values[vertex_start:vertex_start+vertex_count,1]]).transpose([1,0])
                    if weight_values is not None:
                        # Thank you stackoverflow
                        if bone_remap_count != 0:
                            #if bone_remap_count-1 < (weight_values[vertex_start:vertex_start+vertex_count,:8]).max():
                                #bone_mapping = {x["id"]:x["name"] for x in bone_infos}
                                #k = np.array(list(bone_mapping.keys()))
                                #v = np.array(list(bone_mapping.values()))
                                #mapping_arr = np.zeros(k.max()+1,dtype=v.dtype)
                                #mapping_arr[k] = v
                                #LOD_infos[LOD_i]["groups"][group_i]["submeshes_info"][submesh_i]["weights_names"] = mapping_arr[weight_values[vertex_start:vertex_start+vertex_count,:8]]
                                #LOD_infos[LOD_i]["groups"][group_i]["submeshes_info"][submesh_i]["weights_values"] = weight_values[vertex_start:vertex_start+vertex_count,8:]/255.0
                            #else:
                            bone_mapping = {}
                            for bone_i, bone_id in enumerate(bone_remap):
                                bone_mapping[bone_i] = bone_infos[bone_id]["name"]
                            k = np.array(list(bone_mapping.keys()))
                            v = np.array(list(bone_mapping.values()))
                            mapping_arr = np.zeros(k.max()+1,dtype=v.dtype)
                            mapping_arr[k] = v

                            weight_ids = weight_values[vertex_start:vertex_start+vertex_count,:8]
                            weight_force = weight_values[vertex_start:vertex_start+vertex_count,8:]
                            weight_force[weight_ids >= bone_remap_count] = 255
                            weight_ids[weight_ids >= bone_remap_count] = 0
                            LOD_infos[LOD_i]["groups"][group_i]["submeshes_info"][submesh_i]["weights_names"] = mapping_arr[weight_ids]
                            LOD_infos[LOD_i]["groups"][group_i]["submeshes_info"][submesh_i]["weights_values"] = weight_force/255.0
                            
                            if shapekey_buffer_offset != 0:
                                shapekey_weight_ids = shapekey_weight_values[vertex_start:vertex_start+vertex_count,:8]
                                shapekey_weight_force = shapekey_weight_values[vertex_start:vertex_start+vertex_count,8:]
                                shapekey_weight_force[shapekey_weight_ids >= bone_remap_count] = 255
                                shapekey_weight_ids[shapekey_weight_ids >= bone_remap_count] = 0
                                LOD_infos[LOD_i]["groups"][group_i]["submeshes_info"][submesh_i]["shapekey_weights_names"] = mapping_arr[shapekey_weight_ids]
                                LOD_infos[LOD_i]["groups"][group_i]["submeshes_info"][submesh_i]["shapekey_weights_values"] = shapekey_weight_force/255.0
                        else:
                            LOD_infos[LOD_i]["groups"][group_i]["submeshes_info"][submesh_i]["weights_names"] = np.array([bone_infos[0]["name"]]*weight_values.shape[0]*8).reshape([weight_values.shape[0], 8])
                            LOD_infos[LOD_i]["groups"][group_i]["submeshes_info"][submesh_i]["weights_values"] = np.ones([weight_values.shape[0], 8], dtype=weight_values.dtype)
                            
                            if shapekey_buffer_offset != 0:
                                LOD_infos[LOD_i]["groups"][group_i]["submeshes_info"][submesh_i]["shapekey_weights_names"] = np.array([bone_infos[0]["name"]]*shapekey_weight_values.shape[0]*8).reshape([shapekey_weight_values.shape[0], 8])
                                LOD_infos[LOD_i]["groups"][group_i]["submeshes_info"][submesh_i]["shapekey_weights_values"] = np.ones([shapekey_weight_values.shape[0], 8], dtype=shapekey_weight_values.dtype)
                    if color_values is not None:
                        LOD_infos[LOD_i]["groups"][group_i]["submeshes_info"][submesh_i]["colors"] = color_values[vertex_start:vertex_start+vertex_count]
                    LOD_infos[LOD_i]["groups"][group_i]["submeshes_info"][submesh_i]["faces"] = face_values[submesh_info["loop_start"]:submesh_info["loop_start"]+submesh_info["loop_count"]].reshape([-1,3])
                    LOD_infos[LOD_i]["groups"][group_i]["submeshes_info"][submesh_i]["material"] = material_indice_list[submesh_info["material_idx"]]



        return {
            "LOD_infos":LOD_infos,
            "bone_infos":bone_infos,
            "bbboxes":bbboxes,
            "float_array":float_array,
            "sdftex_path":sdftex_path,
            "bounding_box":bounding_box,
            "bounding_sphere":bounding_sphere,
            "debug":debug
        }

if __name__ == "__main__":
    #from glob import glob
    #mesh_files = glob("./natives/**/*.mesh.*", recursive=True)
    #parser = MeshParser("./item_224/mod/item_224.mesh.2109148288")
    #parser = MeshParser("./000/mod/hm06_000.mesh.2109148288")
    #mesh_file = "ch59_000.mesh.231011879"

    #for mesh_file in mesh_files:
    parser = MeshParser(mesh_file)
    data = parser.read()
    #print(bin(data["debug"]["flag_2"]), mesh_file)
