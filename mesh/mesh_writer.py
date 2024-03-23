import bpy
from mathutils import Matrix, Vector, Euler, Quaternion

import struct
import math
import time
import numpy as np
import logging
logger = logging.getLogger("dd2_import")

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

    def padUntilAlligned(self, size):
        for pad_i in range((size - (len(self.data)%size))%size):
            self.writeUByte(0)

def write_mesh(selected_objects):
    # Sanity checks
    # Bunch of janky filters to avoid crashing during the real export
    armatures = []
    objects = []
    obj_ids = []
    lods = []

    # Going over all objects in the collection, keeping the valid meshes and the armatures
    # This is mostly to force the user to check if their shit is correctly set, I could fix a lot of stuff myself but
    # that would imply modifying the user's scene, and I don't want to have that responsability
    for obj in selected_objects:
        try:
            if obj.type == "ARMATURE":
                armatures.append(obj)
            elif obj.type == "MESH":
                splitted_name = obj.name.split("_")
                if len(splitted_name) >= 3:
                    lod = int(splitted_name[0][len("LOD"):])
                    group = int(splitted_name[1][len("G"):])
                    submesh = int(splitted_name[2][len("S"):])
                    lods.append(lod)
                    # Check triangulation
                    for polygon in obj.data.polygons:
                        if len(polygon.loop_indices) != 3:
                            raise RuntimeError("Mesh is not triangulated! ")
                    # Check UV1
                    if len(obj.data.uv_layers) == 0:
                        raise RuntimeError("Mesh does not have UVs! ")
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
                                    raise RuntimeError("Mesh's UV islands aren't physically separated. .mesh files only support data attributed to vertices instead of face corners like in blender, so you'll have to split the vertices of each UV island. Do that by going in uv editing mode, selecting everything, F3->Seams from islands, selecting one of the seam in edit mode, Shift->G then \"seam\", and tapping \"V\" once.")
                    if len(obj.material_slots) == 1 and obj.material_slots != None:
                        material = obj.material_slots[0].name
                    else:
                        raise RuntimeError("Mesh has no material! ")
                    # Making sure there are no duplicates
                    obj_id = str(lod).zfill(3) + str(group).zfill(3) + str(submesh).zfill(3)
                    if obj_id not in obj_ids:
                        obj_ids.append(obj_id)
                        objects.append((lod, group, submesh, obj, material, obj.matrix_world, {x.index:x.name for x in obj.vertex_groups}))
                    else:
                        raise RuntimeError("Object of lod " + str(lod) + ", group " + str(group) + " and submesh " + str(submesh) + " found more than once! ")
                else:
                    raise RuntimeError("Could not find lod/group/submesh info in its name! ")
            else:
                raise RuntimeError("Not a mesh or armature! ")
        except Exception as e:
            logger.warning("Skipped object " + obj.name + ", reason = " + str(e))
            continue

    if len(objects) == 0:
        raise RuntimeError("No valid meshes found! ")

    #for lod_i in range(max(lods)+1):
        #if lod_i not in lods:
            #raise RuntimeError("Missing LoD: " + str(lod_i))

    if len(armatures) > 1:
        raise RuntimeError("More than one armature set of objects! ")

    # Create the LOD dictionnary
    LOD_datas = {}
    for object_tuple in objects:
        lod, group, submesh, obj, material, matrix, group_index = object_tuple
        if lod not in LOD_datas:
            LOD_datas[lod] = {"groups":{}}
        if group not in LOD_datas[lod]["groups"].keys():
            LOD_datas[lod]["groups"][group] = {"submeshes":{}}
        if submesh not in LOD_datas[lod]["groups"][group]["submeshes"].keys():
            LOD_datas[lod]["groups"][group]["submeshes"][submesh] = {
                "data":obj.data,
                "matrix":matrix,
                "group_index":group_index,
                "material":material
            }
    lod_list = list(LOD_datas.keys())
    lod_list.sort()
    best_lod = lod_list[0]
    LOD_datas = {i: LOD_datas[i] for i in lod_list}



    armature_data = None
    # Creating the armature dictionnary
    if len(armatures) == 1:
        armature_data = {"bones":{}}

        armature = armatures[0].data
        armature_data["data"] = armature
        armature_data["matrix"] = armatures[0].matrix_world

        for bone_i, bone in enumerate(armature.bones):
            armature_data["bones"][bone.name] = {
                "id":bone_i,
                "remap":None
            }

        for bone_i, bone in enumerate(armature.bones):
            # Parents
            if bone.parent is not None:
                armature_data["bones"][bone.name]["parent"] = bone.parent.name
            else:
                armature_data["bones"][bone.name]["parent"] = None
            # Children
            armature_data["bones"][bone.name]["children"] = []
            for child in bone.children:
                armature_data["bones"][bone.name]["children"].append(child.name)
            # Connexions
            if len(bone.children) > 0:
                armature_data["bones"][bone.name]["connexion"] = bone.children[0].name
            else:
                armature_data["bones"][bone.name]["connexion"] = None
            # Symmetries
            armature_data["bones"][bone.name]["symmetry"] = None
            if bone.name.startswith("R_") and not bone.name.endswith("_IK"):
                if "L_" + bone.name[2:] in armature_data["bones"].keys():
                    armature_data["bones"][bone.name]["symmetry"] = "L_" + bone.name[2:]
            if bone.name.startswith("L_") and not bone.name.endswith("_IK"):
                if "R_" + bone.name[2:] in armature_data["bones"].keys():
                    armature_data["bones"][bone.name]["symmetry"] = "R_" + bone.name[2:]
            # Siblings
            armature_data["bones"][bone.name]["sibling"] = None
            if bone.parent is not None:
                for child in bone.parent.children:
                    if child.name != bone.name and armature_data["bones"][bone.name]["id"] < armature_data["bones"][child.name]["id"]:
                        armature_data["bones"][bone.name]["sibling"] = child.name
                        break
        # Building the remap table, basically checking which bones are actually used
        # breaking the world record for nested for loops
        
        remap_bones = []
        for LOD_i, LOD_data in LOD_datas.items():
            for group in LOD_data["groups"].values():
                for submesh in group["submeshes"].values():
                    for vertice in submesh["data"].vertices:
                        for group in vertice.groups:
                            # If the group is actually mapped to a bone
                            if submesh["group_index"][group.group] in armature_data["bones"].keys():
                                if submesh["group_index"][group.group] not in remap_bones:
                                    #armature_data["bones"][submesh["group_index"][group.group]]["remap"] = len(armature_data["remap"])
                                    remap_bones.append(submesh["group_index"][group.group])
        
        armature_data["remap"] = []
        
        for bone_name, bone_data in armature_data["bones"].items():
            if bone_name in remap_bones:
                armature_data["bones"][bone_name]["remap"] = len(armature_data["remap"])
                armature_data["remap"].append(bone_name)
        for bone_remap_i, bone_remap in enumerate(armature_data["remap"]):
            armature_data["bones"][bone_remap]["remap"] = bone_remap_i
        if len(armature_data["remap"]) == 0:
            raise RuntimeError("No used bone found in the armature. ")

        for bone_name, bone_data in armature_data["bones"].items():
            if bone_data["remap"] is not None:
                armature_data["default_bone"] = bone_name
                break

    # Analysing the data
    max_UV_number = 0
    max_color_number = 0
    
    submeshes_count = 0
    materials = []
    for LOD_data in LOD_datas.values():
        for group in LOD_data["groups"].values():
            for submesh in group["submeshes"].values():
                if len(submesh["data"].uv_layers) > max_UV_number:
                    max_UV_number = len(submesh["data"].uv_layers)
                if len(submesh["data"].color_attributes) > max_color_number:
                    max_color_number = len(submesh["data"].color_attributes)
                submeshes_count += 1
                if submesh["material"] not in materials:
                    materials.append(submesh["material"])
    #bones + mats
    if armature_data is not None:
        node_count = len(materials) + len(armature_data["bones"])
    else:
        node_count = len(materials)

        
    
    unique_ids = set([x[3:] for x in obj_ids])

    buff_elems = []
    buff_elem_count = 0
    # position
    do_positions = True
    buff_elems.append((0, 12, "pos"))
    buff_elem_count += 1
    # normal
    do_normals = True
    buff_elems.append((1, 8, "normal"))
    buff_elem_count += 1
    # UV1
    do_uv1 = True
    buff_elems.append((2, 4, "UV1"))
    buff_elem_count += 1
    # UV2?
    if max_UV_number > 1:
        do_uv2 = True
        buff_elems.append((3, 4, "UV2"))
        buff_elem_count += 1
    else:
        do_uv2 = False
    # Weights?
    if armature_data is not None:
        do_weights = True
        buff_elems.append((4, 16, "weight"))
        buff_elem_count += 1
    else:
        do_weights = False
    # Vertex color?
    if max_color_number > 0:
        do_colors = True
        buff_elems.append((5, 4, "color"))
        buff_elem_count += 1
    else:
        do_colors = False


    writer = Writer()

    # File header
    writer.writeUInt(1213416781) # Magic
    writer.writeUInt(230517984) # Version
    filesize_off = writer.tell()
    writer.writeUInt(0) # File size
    writer.padUntilAlligned(16)
    flag = 128
    if armature_data is not None:
        flag |= 2
        if armature_data["remap"] is not None:
            flag |= 1
    #if wroggi:
        #flag |= 4

    writer.writeUByte(flag) # flags
    writer.writeUByte(130) #Nearly always 130
    writer.writeUShort(84) #Always 84
    writer.writeUShort(node_count) # Nodes
    writer.padUntilAlligned(8)

    # Offsets to the blocks


    writer.writeUInt64(0) #TODO

    lod_offset = writer.tell()
    writer.writeUInt64(0) # LOD offset

    shadow_lod_offset = writer.tell()
    writer.writeUInt64(0) # shadow LOD offset


    writer.writeUInt64(0) #TODO

    blendshape_offset = writer.tell()
    writer.writeUInt64(0) # shapekey offset


    writer.writeUInt64(0) #TODO

    buffer_header_offset = writer.tell()
    writer.writeUInt64(0) # buffer header offset


    writer.writeUInt64(0) #TODO


    writer.writeUInt64(0) #TODO

    bone_bounding_boxes_offset = writer.tell()
    writer.writeUInt64(0) # bone bounding boxes offset

    bones_offset = writer.tell()
    writer.writeUInt64(0) # bones offset

    material_indice_table_offset = writer.tell()
    writer.writeUInt64(0) # materialtable offset

    bone_indice_table_offset = writer.tell()
    writer.writeUInt64(0) # bone indice table offset


    writer.writeUInt64(0) #TODO

    names_offset = writer.tell()
    writer.writeUInt64(0) # names offset

    hash_offset = writer.tell()
    writer.writeUInt64(0) # hash offset

    element_header_offset_1 = writer.tell()
    writer.writeUInt64(0) # element header offset

    vertex_buffer_offset_1 = writer.tell()
    writer.writeUInt64(0) # vertex buffer offset


    writer.writeUInt64(0) #TODO


    ## X
    #occluder_offset = writer.tell()
    #writer.writeUInt64(0) # occluder offset

    ## X
    #normals_offset = writer.tell()
    #writer.writeUInt64(0) # normals offset

    ## X
    #group_pivot_offset = writer.tell()
    #writer.writeUInt64(0) # ? offset

    ## X
    #blendshapetable_offset = writer.tell()
    #writer.writeUInt64(0) # blendshapetable offset


    #print("Writing LOD block")
    # LOD block
    writer.writeUInt64At(lod_offset, writer.tell())
    writer.writeUByte(len(LOD_datas))
    writer.writeUByte(len(materials))
    writer.writeUByte(max_UV_number)
    writer.writeUByte(18)
    writer.writeUInt(len(unique_ids))
    min_x = 100000
    min_y = 100000
    min_z = 100000
    max_x = -100000
    max_y = -100000
    max_z = -100000
    for group in LOD_datas[best_lod]["groups"].values():
        for submesh in group["submeshes"].values():
            for vertice in submesh["data"].vertices:
                if vertice.co[0] > max_x:
                    max_x = vertice.co[0]
                if vertice.co[0] < min_x:
                    min_x = vertice.co[0]
                if vertice.co[1] > max_y:
                    max_y = vertice.co[1]
                if vertice.co[1] < min_y:
                    min_y = vertice.co[1]
                if vertice.co[2] > max_z:
                    max_z = vertice.co[2]
                if vertice.co[2] < min_z:
                    min_z = vertice.co[2]
    # Sphere
    sphere_x = min_x + ((max_x-min_x)/2.0)
    sphere_y = min_y + ((max_y-min_y)/2.0)
    sphere_z = min_z + ((max_z-min_z)/2.0)
    sphere_radius = np.linalg.norm(np.array([sphere_x-min_x, sphere_y-min_y, sphere_z-min_z]))
    writer.writeFloat(sphere_x)
    writer.writeFloat(sphere_y)
    writer.writeFloat(sphere_z)
    writer.writeFloat(sphere_radius)
    # BBox
    writer.writeFloat(min_x)
    writer.writeFloat(min_y)
    writer.writeFloat(min_z)
    writer.writeUInt(1)
    writer.writeFloat(max_x)
    writer.writeFloat(max_y)
    writer.writeFloat(max_z)
    writer.writeUInt(256)
    writer.writeUInt64(writer.tell()+8)
    LODheaders_offset = []
    for _ in range(len(LOD_datas)):
        LODheaders_offset.append(writer.tell())
        writer.writeUInt64(0)
    writer.padUntilAlligned(16)
    LODgroups_offset = []
    global_vertex_count = 0
    global_loops_count = 0
    lod_count = 0
    first_group_offset = None
    for LOD_i, LOD_data in LOD_datas.items():
        writer.writeUInt64At(LODheaders_offset[lod_count], writer.tell())
        if first_group_offset is None:
            first_group_offset = writer.tell()
        writer.writeUShort(len(LOD_data["groups"])) # number of groups
        writer.writeUShort(LOD_i) # LOD index
        writer.writeFloat(1000.0*(LOD_i+1)) # LOD distance?
        #writer.writeFloat(1.9262832403182983) # LOD distance?
        #writer.writeFloat(0.0) # LOD distance?
        LODgroups_offset = writer.tell()
        writer.writeUInt64(0) # Offset to groups pointers
        writer.padUntilAlligned(8)
        writer.writeUInt64At(LODgroups_offset, writer.tell())
        groups_offset = []
        for _ in LOD_data["groups"].values():
            groups_offset.append(writer.tell())
            writer.writeUInt64(0) # Offset to groups
        writer.padUntilAlligned(16)
        group_i = 0
        for group_id, group in LOD_data["groups"].items():
            writer.writeUInt64At(groups_offset[group_i], writer.tell())
            writer.writeUByte(group_id) # ID
            writer.writeUByte(len(group["submeshes"])) # Submeshes count
            writer.padUntilAlligned(8)
            vertex_count = 0
            loops_count = 0
            for submesh in group["submeshes"].values():
                vertex_count += len(submesh["data"].vertices)
                loops_count += len(submesh["data"].loops)
            writer.writeUInt(vertex_count)
            writer.writeUInt(loops_count)
            for submesh in group["submeshes"].values():
                writer.writeUShort(materials.index(submesh["material"]))
                writer.writeUShort(0) # Not dealing with that atm TODO
                writer.writeUInt(len(submesh["data"].loops))
                writer.writeUInt(global_loops_count)
                writer.writeUInt(global_vertex_count)
                writer.writeUInt64(0)
                global_vertex_count += len(submesh["data"].vertices)

                global_loops_count += len(submesh["data"].loops)
                if global_loops_count %2 == 1:
                    global_loops_count += 1
            group_i += 1
        lod_count += 1
    #writer.padUntilAlligned(16)
    

    # bones
    if armature_data is not None:
        writer.writeUInt64At(bones_offset, writer.tell())
        writer.writeUInt(len(armature_data["bones"]))
        writer.writeUInt(len(armature_data["remap"]))
        writer.writeUInt64(0)
        #writer.padUntilAlligned(16)
        bone_hierarchy_offset = writer.tell()
        writer.writeUInt64(0)
        local_coords_offset = writer.tell()
        writer.writeUInt64(0)
        global_coords_offset = writer.tell()
        writer.writeUInt64(0)
        inv_global_coords_offset = writer.tell()
        writer.writeUInt64(0)
        for remap in armature_data["remap"]:
            writer.writeUShort(armature_data["bones"][remap]["id"])
        writer.padUntilAlligned(16)
        writer.writeUInt64At(bone_hierarchy_offset, writer.tell())
        for bone_name, bone_data in armature_data["bones"].items():
            writer.writeUShort(bone_data["id"])
            if bone_data["parent"] is not None:
                writer.writeUShort(armature_data["bones"][bone_data["parent"]]["id"])
            else:
                writer.writeUShort(65535)
            if bone_data["sibling"] is not None:
                writer.writeUShort(armature_data["bones"][bone_data["sibling"]]["id"])
            else:
                writer.writeUShort(65535)
            if bone_data["connexion"] is not None:
                writer.writeUShort(armature_data["bones"][bone_data["connexion"]]["id"])
            else:
                writer.writeUShort(65535)
            if bone_data["symmetry"] is not None:
                writer.writeUShort(armature_data["bones"][bone_data["symmetry"]]["id"])
            else:
                writer.writeUShort(bone_data["id"])
            writer.padUntilAlligned(16)
        writer.writeUInt64At(local_coords_offset, writer.tell())
        matrix = armature_data["matrix"]
        rot4 = Matrix.Rotation(math.radians(-90.0), 4, 'X')
        scale_mat = Matrix.LocRotScale(None, None, matrix.to_scale())

        for bone_name, bone_data in armature_data["bones"].items():
            if bone_data["parent"] is None:
                local_mat = rot4 @ (matrix @ armature_data["data"].bones[bone_name].matrix_local)
            else:
                local_mat = scale_mat @ (armature_data["data"].bones[bone_data["parent"]].matrix_local.inverted() @ armature_data["data"].bones[bone_name].matrix_local)
            for mat_j in range(4):
                for mat_i in range(4):
                    writer.writeFloat(local_mat[mat_i][mat_j])
        writer.padUntilAlligned(16)
        writer.writeUInt64At(global_coords_offset, writer.tell())
        for bone_name, bone_data in armature_data["bones"].items():
            global_mat = rot4 @ (matrix @ (armature_data["data"].bones[bone_name].matrix_local))
            for mat_j in range(4):
                for mat_i in range(4):
                    writer.writeFloat(global_mat[mat_i][mat_j])
        writer.padUntilAlligned(16)
        writer.writeUInt64At(inv_global_coords_offset, writer.tell())
        for bone_name, bone_data in armature_data["bones"].items():
            global_mat_inv = rot4 @ (matrix @ (armature_data["data"].bones[bone_name].matrix_local.inverted()))
            for mat_j in range(4):
                for mat_i in range(4):
                    writer.writeFloat(global_mat_inv[mat_i][mat_j])
        writer.padUntilAlligned(16)

    node_counter = 0
    #print("Writing mat indices block")
    # material indices table
    writer.writeUInt64At(material_indice_table_offset, writer.tell())
    for mat_i in range(len(materials)):
        writer.writeUShort(node_counter)
        node_counter += 1
    writer.padUntilAlligned(16)

    #print("Writing bone indices block")
    # bone indices table
    if armature_data is not None:
        writer.writeUInt64At(bone_indice_table_offset, writer.tell())
        for bone_i in range(len(armature_data["bones"])):
            writer.writeUShort(node_counter)
            node_counter += 1
        writer.padUntilAlligned(16)

    # blendshape indices table



    #print("Writing name block")
    # Name table
    writer.writeUInt64At(names_offset, writer.tell())
    strings_offset = []
    if armature_data is None:
        for _ in range(len(materials)):
            strings_offset.append(writer.tell())
            writer.writeUInt64(0)
    else:
        for _ in range(len(materials) + len(armature_data["bones"].keys())):
            strings_offset.append(writer.tell())
            writer.writeUInt64(0)
    writer.padUntilAlligned(16)
    name_count = 0
    for mat_name in materials:
        writer.writeUInt64At(strings_offset[name_count], writer.tell())
        writer.writeString(mat_name)
        name_count += 1
    if armature_data is not None:
        for bone_name in armature_data["bones"].keys():
            writer.writeUInt64At(strings_offset[name_count], writer.tell())
            writer.writeString(bone_name)
            name_count += 1
    writer.padUntilAlligned(16)


    #print("Writing hash block")
    writer.writeUInt64At(hash_offset, writer.tell())
    writer.writeUInt(2745047434)
    writer.padUntilAlligned(16)

    #print("Writing bone bbox block")
    # bone bounding boxes
    if armature_data is not None:
        writer.writeUInt64At(bone_bounding_boxes_offset, writer.tell())
        writer.writeUInt64(len(armature_data["remap"]))
        writer.writeUInt64(writer.tell()+8)
        for bone_name in armature_data["remap"]:
            min_x = 100000.0
            min_y = 100000.0
            min_z = 100000.0
            max_x = -100000.0
            max_y = -100000.0
            max_z = -100000.0
            for LOD_i, LOD_data in LOD_datas.items():
                for group in LOD_data["groups"].values():
                    for submesh in group["submeshes"].values():
                        for vertice in submesh["data"].vertices:
                            in_group = False
                            for group in vertice.groups:
                                if submesh["group_index"][group.group] == bone_name:
                                    in_group = True
                                    break
                            if in_group:
                                if vertice.co[0] > max_x:
                                    max_x = vertice.co[0]
                                if vertice.co[0] < min_x:
                                    min_x = vertice.co[0]
                                if vertice.co[1] > max_y:
                                    max_y = vertice.co[1]
                                if vertice.co[1] < min_y:
                                    min_y = vertice.co[1]
                                if vertice.co[2] > max_z:
                                    max_z = vertice.co[2]
                                if vertice.co[2] < min_z:
                                    min_z = vertice.co[2]
            writer.writeFloat(min_x - armature_data["data"].bones[bone_name].head_local[0])
            writer.writeFloat(min_y - armature_data["data"].bones[bone_name].head_local[1])
            writer.writeFloat(min_z - armature_data["data"].bones[bone_name].head_local[2])
            writer.writeFloat(1.0)
            writer.writeFloat(max_x - armature_data["data"].bones[bone_name].head_local[0])
            writer.writeFloat(max_y - armature_data["data"].bones[bone_name].head_local[1])
            writer.writeFloat(max_z - armature_data["data"].bones[bone_name].head_local[2])
            writer.writeFloat(1.0)
        writer.padUntilAlligned(16)

    #print("Writing buffer header block")
    # Buffer header
    writer.writeUInt64At(buffer_header_offset, writer.tell())
    element_header_offset_2 = writer.tell()
    writer.writeUInt64(0)
    vertex_buffer_offset_2 = writer.tell()
    writer.writeUInt64(0)
    face_buffer_offset = writer.tell()
    writer.writeUInt64(0)
    #writer.padUntilAlligned(16)
    shapekey_buffer_reloffset = writer.tell()
    writer.writeUInt(0) # shapekey_buffer_reloffset
    face_buffer_reloffset = writer.tell()
    writer.writeUInt(0) # face_buffer_reloffset
    writer.writeUShort(len(buff_elems))
    writer.writeUShort(len(buff_elems))
    face_buffer_end_reloffset_1 = writer.tell()
    writer.writeUInt(0) # face_buffer_end_reloffset_1
    face_buffer_end_reloffset_2 = writer.tell()
    writer.writeUInt(0) # face_buffer_end_reloffset_2
    inverted_vertex_buffer_offset = writer.tell()
    #inverted_vertex_buffer_offset = writer.tell()
    writer.writeUInt(0) # WHY ?!?
    writer.writeUInt64(0)
    writer.writeUInt64(0)
    writer.writeUInt64At(element_header_offset_1, writer.tell())
    writer.writeUInt64(0)
    writer.writeUInt64(0)
    #writer.padUntilAlligned(16)

    writer.writeUInt64At(element_header_offset_2, writer.tell())
    buffer_count = 0
    for buff_elem in buff_elems:
        writer.writeUShort(buff_elem[0])
        writer.writeUShort(buff_elem[1])
        writer.writeUInt(buffer_count)
        buffer_count += global_vertex_count*buff_elem[1]

    # Vertex buffer
    vertex_buffer_start = writer.tell()
    writer.writeUInt64At(vertex_buffer_offset_1, writer.tell())
    writer.writeUInt64At(vertex_buffer_offset_2, writer.tell())
    writer.writeIntAt(inverted_vertex_buffer_offset, -writer.tell())

    positions = []
    normals = []
    uv1s = []
    uv2s = []
    weights = []
    colors = []
    faces = []

    for LOD_i, LOD_data in LOD_datas.items():
        for group in LOD_data["groups"].values():
            for submesh in group["submeshes"].values():
                for vertice in submesh["data"].vertices:
                    if do_positions:
                        world_co = submesh["matrix"] @ vertice.co
                        # Also switching Y and Z
                        positions.append(world_co[0])
                        positions.append(world_co[2])
                        positions.append(-world_co[1])

                    if do_weights:
                        all_groups = [[submesh["group_index"][group.group], int(round(group.weight*255))] for group in vertice.groups if group.group in submesh["group_index"].keys() and submesh["group_index"][group.group] in armature_data["bones"].keys()]
                        if len(all_groups) == 0:
                            all_groups.append([armature_data["default_bone"], 255])

                        all_groups.sort(key=lambda a: -a[1])
                        all_groups = all_groups[:8]
                        last_group = all_groups[-1][0]

                        total_weight = 0
                        for group_i, group in enumerate(all_groups):
                            total_weight += group[1]
                        total_weight_normalized = 0
                        for group_i, group in enumerate(all_groups):
                            group[1] = int(round((float(group[1]) / float(total_weight)) * 255))
                            total_weight_normalized += group[1]
                        weight_excess = 255-total_weight_normalized
                        all_groups[0][1] += weight_excess

                        while len(all_groups) < 8:
                            all_groups.append((last_group, 0))

                        for group in all_groups:
                            weights.append(armature_data["bones"][group[0]]["remap"])
                        for group in all_groups:
                            weights.append(group[1])

                #submesh["data"].calc_normals_split()
                submesh["data"].calc_tangents()
                rot_mat = submesh["matrix"].to_quaternion().to_matrix()
                encountered_none = False
                if do_normals:
                    normal_datas = [None]*len(submesh["data"].vertices)
                    tangent_datas = [None]*len(submesh["data"].vertices)
                    bitangent_signs = [None]*len(submesh["data"].vertices)
                    for loop in submesh["data"].loops:
                        normal_datas[loop.vertex_index] = rot_mat @ Vector([x if not math.isnan(x) else 0 for x in loop.normal])
                        tangent_datas[loop.vertex_index] = rot_mat @ Vector([x if not math.isnan(x) else 0 for x in loop.tangent])
                        bitangent_signs[loop.vertex_index] = loop.bitangent_sign
                    for normal_data, tangent_data, bitangent_sign in zip(normal_datas, tangent_datas, bitangent_signs):
                        if normal_data is not None:
                            normals.append(math.floor((normal_data[0]*1.0001)*127))
                            normals.append(math.floor((normal_data[2]*1.0001)*127))
                            normals.append(math.floor((-normal_data[1]*1.0001)*127))
                            normals.append(0)
                            normals.append(math.floor((tangent_data[0]*1.0001)*127))
                            normals.append(math.floor((tangent_data[2]*1.0001)*127))
                            normals.append(math.floor((-tangent_data[1]*1.0001)*127))
                            normals.append(math.floor((bitangent_sign*1.0001)*127))
                        else:
                            normals.append(127)
                            normals.append(0)
                            normals.append(0)
                            normals.append(0)
                            normals.append(127)
                            normals.append(0)
                            normals.append(0)
                            normals.append(127)

                uv1_datas = [None]*len(submesh["data"].vertices)
                uv2_datas = [None]*len(submesh["data"].vertices)
                color_datas = [None]*len(submesh["data"].vertices)
                face_counter = 0
                for face in submesh["data"].polygons:
                    for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                        if do_uv1:
                            if len(submesh["data"].uv_layers) > 0:
                                uv1_datas[vert_idx] = submesh["data"].uv_layers[0].data[loop_idx].uv
                            else:
                                uv1_datas[vert_idx] = [0.0, 0.0]
                        if do_uv2:
                            if len(submesh["data"].uv_layers) > 1:
                                uv2_datas[vert_idx] = submesh["data"].uv_layers[1].data[loop_idx].uv
                            else:
                                uv2_datas[vert_idx] = [0.0, 0.0]
                        if do_colors:
                            if len(submesh["data"].color_attributes) > 0:
                                color_datas[vert_idx] = submesh["data"].color_attributes[0].data[loop_idx].color
                            else:
                                color_datas[vert_idx] = [1, 1, 1, 1]
                        faces.append(vert_idx)
                        face_counter += 2
                if ((face_counter) / 6) % 2 != 0:
                    faces.append(0)
                if do_uv1:
                    for uv1_data in uv1_datas:
                        if uv1_data is not None:
                            uv1s.append(uv1_data[0])
                            uv1s.append(1.0-uv1_data[1])
                        else:
                            uv1s.append(0.0)
                            uv1s.append(1.0)
                if do_uv2:
                    for uv2_data in uv2_datas:
                        if uv2_data is not None:
                            uv2s.append(uv2_data[0])
                            uv2s.append(1.0-uv2_data[1])
                        else:
                            uv2s.append(0.0)
                            uv2s.append(1.0)
                if do_colors:
                    for color_data in color_datas:
                        if color_data is not None:
                            colors.append(int(round(color_data[0]*255.0)))
                            colors.append(int(round(color_data[1]*255.0)))
                            colors.append(int(round(color_data[2]*255.0)))
                            colors.append(255)
                        else:
                            colors.append(255)
                            colors.append(255)
                            colors.append(255)
                            colors.append(255)

    vertex_buffer_start = writer.tell()
    if do_positions:
        writer.writeFloats(positions)
    if do_normals:
        writer.writeBytes(normals)
    if do_uv1:
        writer.writeHalfs(uv1s)
    if do_uv2:
        writer.writeHalfs(uv2s)
    if do_weights:
        writer.writeUBytes(weights)
    if do_colors:
        writer.writeUBytes(colors)

    writer.padUntilAlligned(8)
    writer.padUntilAlligned(16)
    writer.writeUIntAt(face_buffer_reloffset, writer.tell() - vertex_buffer_start)
    #print("Writing face buffer block")
    # Face buffer
    writer.writeUInt64At(face_buffer_offset, writer.tell())
    face_buffer_start = writer.tell()
    writer.writeUShorts(faces)
    #writer.writeUIntAt(face_buffer_reloffset, writer.tell() - face_buffer_start)
    writer.writeUIntAt(face_buffer_end_reloffset_1, writer.tell() - vertex_buffer_start)
    writer.writeUIntAt(face_buffer_end_reloffset_2, writer.tell() - vertex_buffer_start)

    writer.padUntilAlligned(16)
    writer.writeUIntAt(shapekey_buffer_reloffset, writer.tell() - vertex_buffer_start)

    writer.writeUIntAt(filesize_off, len(writer.data))

    # Phew
    return writer.data
