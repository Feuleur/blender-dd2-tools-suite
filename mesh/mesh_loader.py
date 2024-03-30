import bpy
from mathutils import Euler, Matrix, Vector

import os
import math
import logging
logger = logging.getLogger("dd2_import")

from .mesh_parser import MeshParser

def load_mesh(filepath, collection = None, LOD=0, fix_rotation=False, obj_name="", connect_bones=False):
    parser = MeshParser(path=filepath)
    mesh_data = parser.read()

    file_name = os.path.basename(filepath)
    file_sname = file_name.split(".")
    if len(file_sname) == 3 and file_sname[1] == "mesh" and file_sname[2] == "231011879":
        file_name = file_sname[0]

    if collection is None:
        master_collection = bpy.context.scene.collection
        col = bpy.data.collections.new("Col_" + file_name)
        master_collection.children.link(col)
    else:
        col = collection

    returned_objects = []

    used_bones = []
    armature_object = None
    if mesh_data["bone_infos"] is not None:
        for bone in mesh_data["bone_infos"]:
            if bone["remap"] is not None and bone["name"] not in used_bones:
                used_bones.append(bone["name"])

        if obj_name != "":
            armature_name = "Armature_" + obj_name
        else:
            armature_name = "Armature_" + file_name
        armature_data = bpy.data.armatures.new(armature_name)
        armature_object = bpy.data.objects.new(armature_name, armature_data)
        armature_object.show_in_front = True
        armature_object.rotation_mode = "XYZ"
        if fix_rotation:
            armature_object.rotation_euler.rotate(Euler([math.radians(90),0,0]))
        col.objects.link(armature_object)
        bpy.context.view_layer.objects.active = armature_object
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        for bone_values in mesh_data["bone_infos"]:
            new_bone = armature_data.edit_bones.new(bone_values["name"])
            local_matrix = Matrix(bone_values["local_matrix"])
            local_matrix.transpose()
            new_bone.head = (0.0, 0.0, 0.0)
            new_bone.tail = (0.0, 0.2, 0.0)
            new_tfr = new_bone.matrix @ local_matrix
            if bone_values["parent"] != -1:
                new_bone.parent = armature_data.edit_bones[bone_values["parent"]]
                new_bone.matrix = new_bone.parent.matrix @ new_tfr
            else:
                new_bone.matrix = new_tfr
            new_bone["unknown_property"] = bone_values["unknown_property"]

        if connect_bones:
            for bone_i, bone_values in enumerate(mesh_data["bone_infos"]):
                new_bone = armature_data.edit_bones[bone_values["name"]]
                if new_bone.children is not None:
                    if len(new_bone.children) == 1 and (new_bone.children[0].head-new_bone.head).length > 0.0001:
                        new_bone.tail = new_bone.children[0].head
                    elif len(new_bone.children) == 0:
                        if new_bone.parent is not None:
                            parent_vector = new_bone.parent.tail - new_bone.parent.head
                            new_bone.tail = new_bone.head + (parent_vector.normalized()*(new_bone.head-new_bone.tail).length)
                    elif len(new_bone.children) > 1:
                        def recursive_seek_children(bone):
                            return 1+sum([recursive_seek_children(child) for child in bone.children])
                        best_child = None
                        best_child_score = 0
                        for child in new_bone.children:
                            if abs(new_bone.head.x) < 0.0001 and abs(child.head.x) > 0.0001:
                                continue
                            if (child.head-new_bone.head).length > 0.0001:
                                child_amount = recursive_seek_children(child)
                                if child_amount > best_child_score:
                                    best_child = child
                                    best_child_score = child_amount
                        if best_child is not None:
                            new_bone.tail = best_child.head
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        returned_objects.append(armature_object)

    if LOD is not None:
        LOD = min(LOD, len(mesh_data["LOD_infos"])-1)
        LOD_infos = [mesh_data["LOD_infos"][LOD]]
    else:
        LOD_infos = mesh_data["LOD_infos"]

    for LOD_info in LOD_infos:
        for group_i, group_info in enumerate(LOD_info["groups"]):
            for submesh_i, submesh_info in enumerate(group_info["submeshes_info"]):
                mesh_prefix = "LOD" + str(LOD_info["id"]) + "_G" + str(group_info["id"]) + "_S" + str(submesh_i)
                verts = submesh_info["pos"]
                edges = []
                faces = submesh_info["faces"]
                if obj_name != "":
                    meshName = mesh_prefix + "_" + obj_name
                else:
                    meshName = mesh_prefix + "_" + file_name
                mesh = bpy.data.meshes.new(meshName)  # add the new mesh
                obj = bpy.data.objects.new(mesh.name, mesh)
                col.objects.link(obj)
                obj.rotation_mode = "XYZ"
                mesh.from_pydata(verts, edges, faces)

                if armature_object is not None:
                    obj.parent = armature_object
                    armature_mod = obj.modifiers.new("Armature", 'ARMATURE')
                    armature_mod.object = armature_object
                else:
                    if fix_rotation:
                        obj.rotation_euler.rotate(Euler([math.radians(90),0,0]))

                material_name = obj_name + submesh_info["material"]
                if len(material_name) > 55:
                    #FUCK blender
                    material_name = "HASHED_" + str(abs(int(hash(material_name)))).zfill(20)
                if material_name not in bpy.data.materials:
                    mat = bpy.data.materials.new(name=material_name)
                else:
                    mat = bpy.data.materials[material_name]
                mesh.materials.append(mat)
                mat_slot = obj.material_slots[0]
                mat_slot.link = 'OBJECT'
                mat_slot.material = mat

                bpy.context.view_layer.objects.active = obj

                if "weights_names" in submesh_info.keys() and "weights_values" in submesh_info.keys():
                    vertex_weight_dict = {}
                    for bone_name in used_bones:
                        vertex_weight_dict[bone_name] = obj.vertex_groups.new(name=bone_name)
                    for vertice, weights_name, weights_value in zip(mesh.vertices, submesh_info["weights_names"], submesh_info["weights_values"]):
                        for weight_name, weight_value in zip(weights_name, weights_value):
                            if weight_value != 0.0:
                                vertex_weight_dict[weight_name].add([vertice.index], weight_value, 'REPLACE')

                if "shapekey_weights_names" in submesh_info.keys() and "shapekey_weights_values" in submesh_info.keys():
                    vertex_weight_dict = {}
                    for bone_name in used_bones:
                        vertex_weight_dict["SHAPEKEY_" + bone_name] = obj.vertex_groups.new(name="SHAPEKEY_" + bone_name)
                    for vertice, weights_name, weights_value in zip(mesh.vertices, submesh_info["shapekey_weights_names"], submesh_info["shapekey_weights_values"]):
                        for weight_name, weight_value in zip(weights_name, weights_value):
                            if weight_value != 0.0:
                                vertex_weight_dict["SHAPEKEY_" + weight_name].add([vertice.index], weight_value, 'REPLACE')
                
                if "uv1" in submesh_info.keys():
                    uv1_layer = mesh.uv_layers.new(name='UV1')
                    for face in mesh.polygons:
                        for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                            uv1_layer.data[loop_idx].uv = submesh_info["uv1"][vert_idx]

                if "uv2" in submesh_info.keys():
                    uv2_layer = mesh.uv_layers.new(name='UV2')
                    for face in mesh.polygons:
                        for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                            uv2_layer.data[loop_idx].uv = submesh_info["uv2"][vert_idx]

                if "normals" in submesh_info.keys():
                    if hasattr(mesh, 'create_normals_split'):
                        mesh.create_normals_split()
                    mesh.polygons.foreach_set("use_smooth", [True]*len(mesh.polygons))
                    mesh.normals_split_custom_set_from_vertices(submesh_info["normals"])
                    if hasattr(mesh, 'use_auto_smooth'):
                        mesh.use_auto_smooth = True
                    if hasattr(mesh, 'free_normals_split'):
                        mesh.free_normals_split()

                if "colors" in submesh_info.keys():
                    color_layer = mesh.color_attributes.new(
                        name="Attribute",
                        type='BYTE_COLOR',
                        domain='CORNER',
                    )
                    color_layer.name = "Attribute"
                    for face in mesh.polygons:
                        for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                            color_layer.data[loop_idx].color = [x/255.0 for x in submesh_info["colors"][vert_idx]]
                returned_objects.append(obj)
    return returned_objects
