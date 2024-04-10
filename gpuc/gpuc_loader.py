import bpy
from mathutils import Euler, Matrix, Vector

import os
import math
import logging
logger = logging.getLogger("dd2_import")

from .gpuc_parser import GpucParser

def load_gpuc(filepath, collection = None, fix_rotation=False):
    parser = GpucParser(path=filepath)
    cloth_sims, data = parser.read()

    file_name = os.path.basename(filepath)
    file_sname = file_name.split(".")
    if len(file_sname) == 3 and file_sname[1] == "gpuc" and file_sname[2] == "231011972":
        file_name = file_sname[0]

    if collection is None:
        master_collection = bpy.context.scene.collection
        col = bpy.data.collections.new("Col_" + file_name)
        master_collection.children.link(col)
    else:
        col = collection

    returned_objects = []

    for cloth_sim_i, cloth_sim in enumerate(cloth_sims):


        mesh_prefix = "GPUC_" + str(cloth_sim_i)
        verts = [x["position"] for x in cloth_sim["vertices"]]
        edges = []
        faces = cloth_sim["faces"]
        meshName = mesh_prefix + "_" + file_name
        mesh = bpy.data.meshes.new(meshName)  # add the new mesh
        obj = bpy.data.objects.new(mesh.name, mesh)
        col.objects.link(obj)
        obj.rotation_mode = "XYZ"
        obj.display_type = "WIRE"
        mesh.from_pydata(verts, edges, faces)
        if fix_rotation:
            obj.rotation_euler.rotate(Euler([math.radians(90),0,0]))

        weigths = [x["weight"] for x in cloth_sim["vertices"]]
        weight_group = obj.vertex_groups.new(name="weight")
        for weight, vertice in zip(weigths, mesh.vertices):
            weight_group.add([vertice.index], weight, 'REPLACE')

        radiuss = [x["radius"] for x in cloth_sim["vertices"]]
        radius_group = obj.vertex_groups.new(name="radius")
        for radius, vertice in zip(radiuss, mesh.vertices):
            radius_group.add([vertice.index], radius, 'REPLACE')

        restlength = mesh.attributes.new(name="restLength", type="FLOAT", domain="EDGE")
        #print(restlength.data)
        #stiffness = mesh.attributes.new(name="stiffness", type="FLOAT", domain="EDGE")
        #print(restlength.data)
        #stiffnessMultiplier = mesh.attributes.new(name="stiffnessMultiplier", type="FLOAT", domain="EDGE")
        #print(restlength.data)
        #stretchLimit = mesh.attributes.new(name="stretchLimit", type="FLOAT", domain="EDGE")
        #print(restlength.data)
        #compressionLimit = mesh.attributes.new(name="compressionLimit", type="FLOAT", domain="EDGE")
        #print(restlength.data)

        edges_dict = {(str(min(x["indexA"], x["indexB"])).zfill(10) + "_" + str(max(x["indexA"], x["indexB"])).zfill(10)):x for x in cloth_sim["edges"]}
        for edge in mesh.edges:
            vertices = (str(min(edge.vertices[0], edge.vertices[1])).zfill(10) + "_" + str(max(edge.vertices[0], edge.vertices[1])).zfill(10))
            if vertices in edges_dict.keys():

                restlength.data[edge.index].value = edges_dict[vertices]["restLength"]
                #stiffness.data[edge.index].value = edges_dict[vertices]["stiffness"]
                #stiffnessMultiplier.data[edge.index].value = edges_dict[vertices]["stiffnessMultiplier"]
                #stiffnessMultiplier.data[edge.index].value = edges_dict[vertices]["stretchLimit"]
                #compressionLimit.data[edge.index].value = edges_dict[vertices]["compressionLimit"]
            else:
                logger.warning("AAAAAAAA")
        returned_objects.append(obj)
    return returned_objects
