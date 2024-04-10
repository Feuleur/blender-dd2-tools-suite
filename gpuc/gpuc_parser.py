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

class GpucParser():
    def __init__(self, path="", data=None):
        self.path = path
        if data is None:
            with open(path, "rb") as file_in:
                data = file_in.read()
        self.bs = Reader(data)

    def read(self):
        data = {}
        debug = {}
        self.magic = self.bs.readUInt()
        if self.magic != 1330398023:
            raise RuntimeError(str(self.path) + " is not a dd2 gpuc file (magic = " + str(self.magic) + ")")
        _ = self.bs.readUInt() # Some kind of hash, different for each file and crashes the game when set wrong, will probably be a massive pain
        _ = self.bs.readUInt64() # copy of offset_17?
        _ = self.bs.readUInt()

        vertice_count = self.bs.readUInt()
        face_count = self.bs.readUInt() #64/84
        edge_count = self.bs.readUInt() #244/316

        collision_edge_count = self.bs.readUInt() #108/146
        face_group_count = self.bs.readUInt() #7/8/9
        edge_group_count = self.bs.readUInt() #13/14/17
        collision_edge_group_count = self.bs.readUInt() #7/8

        bone_info_count = self.bs.readUInt() #1/3
        batch_info_count = self.bs.readUInt()
        _ = self.bs.readUInt() #1/3
        deform_count = self.bs.readUInt() #>500

        deform_size = self.bs.readUInt() #4/7
        original_vertex_count = self.bs.readUInt()
        _ = self.bs.readUInt() #2
        _ = self.bs.readUInt() #0

        _ = self.bs.readUInt() #0
        _ = self.bs.readUInt() #3
        _ = self.bs.readUInt() #0
        _ = self.bs.readUInt() #0

        _ = self.bs.readUInt() #0
        unk_float = self.bs.readFloat()
        _ = self.bs.readUInt() #16777233
        _ = self.bs.readUInt() #256

        _ = self.bs.readUInt() #copy of deform_size?
        _ = self.bs.readUInt() #0
        _ = self.bs.readUInt() #0
        _ = self.bs.readUInt() #0

        bbox_x_min = self.bs.readFloat()
        bbox_y_min = self.bs.readFloat()
        bbox_z_min = self.bs.readFloat()
        bbox_w_min = self.bs.readFloat()
        bbox_x_max = self.bs.readFloat()
        bbox_y_max = self.bs.readFloat()
        bbox_z_max = self.bs.readFloat()
        bbox_w_max = self.bs.readFloat()
        bbox = [[bbox_x_min, bbox_y_min, bbox_z_min], [bbox_x_max, bbox_y_max, bbox_z_max]]
        data["bbox"] = bbox


        vertice_offset = self.bs.readUInt64()
        face_offset = self.bs.readUInt64()

        edge_offset = self.bs.readUInt64()
        collision_edge_offset = self.bs.readUInt64()

        face_groups_offset = self.bs.readUInt64()
        edge_group_offset = self.bs.readUInt64()

        collision_edge_group_offset = self.bs.readUInt64()
        bone_info_offset = self.bs.readUInt64()

        batch_info_offset = self.bs.readUInt64()
        offset_09 = self.bs.readUInt64()

        offset_10 = self.bs.readUInt64()
        offset_11 = self.bs.readUInt64()

        offset_12 = self.bs.readUInt64()
        offset_13 = self.bs.readUInt64()

        offset_14 = self.bs.readUInt64()
        offset_15 = self.bs.readUInt64()

        offset_16 = self.bs.readUInt64()
        offset_17 = self.bs.readUInt64()

        deform_offset = self.bs.readUInt64()
        original_vertex_array_offset = self.bs.readUInt64()

        debug_vertice_offset = self.bs.readUInt64()
        debug_edge_offset = self.bs.readUInt64()


        # bone infos
        self.bs.seek(bone_info_offset)
        bone_infos = []
        for x in range(bone_info_count):
            bone_info = {}
            bone_info["hash_1"] = self.bs.readUInt() #Hash, probably of the bone name?
            bone_info["index_1"] = self.bs.readUInt() #increases for each instance
            bone_info["count_1"] = self.bs.readUInt() #Similar in the same file
            bone_info["count_2"] = self.bs.readUInt() #Similar in the same file
            bone_info["index_2"] = self.bs.readUInt() #Sometimes increases
            bone_info["hash_2"] = self.bs.readUInt() #Hash, sometimes at 0
            bone_info["null_1"] = self.bs.readUInt64() #0
            bone_info["null_2"] = self.bs.readUInt64() #0
            bone_info["unk_1"] = self.bs.readUInt64() #-1
            bone_info["unk_2"] = self.bs.readUInt64() #-1
            bone_info["null_3"] = self.bs.readUInt64() #0
            bone_infos.append(bone_info)

        # vertices
        self.bs.seek(vertice_offset)
        vertices = []
        for x in range(vertice_count):
            vertice = {}
            vertice["weight"] = self.bs.readFloat()
            vertice["radius"] = self.bs.readFloat()
            vertice["inverseMass"] = self.bs.readFloat()
            vertice["maxDistance"] = self.bs.readFloat()
            vertice["backstopRadius"] = self.bs.readFloat()
            vertice["plane_flags"] = self.bs.readUInt()
            vertice["sphere_flags"] = self.bs.readUInt()
            vertice["capsule_flags"] = self.bs.readUInt()
            vertice["part_id"] = self.bs.readUInt()
            vertice["config_id"] = self.bs.readUInt()
            vertice["controlPointIndices"] = [self.bs.readShort() for _ in range(4)]
            vertice["initialDistances"] = [self.bs.readUInt() for _ in range(4)]
            vertice["position"] = [self.bs.readFloat() for _ in range(3)]
            vertice["unk"] = [self.bs.readUInt() for _ in range(6)]
            vertices.append(vertice)
        data["vertices"] = vertices

        self.bs.seek(face_offset)
        faces = []
        for x in range(face_count):
            face = [self.bs.readUShort() for _ in range(3)]
            self.bs.readUShort()
            faces.append(face)
        data["faces"] = faces

        # edges
        self.bs.seek(edge_offset)
        edges = []
        for x in range(edge_count):
            edge = {}
            edge["indexA"] = self.bs.readUShort()
            edge["indexB"] = self.bs.readUShort()
            edge["restLength"] = self.bs.readFloat()
            edge["stiffness"] = self.bs.readUShort()/65535
            edge["stiffnessMultiplier"] = self.bs.readUShort()/65535
            edge["stretchLimit"] = self.bs.readUShort()/65535
            edge["compressionLimit"] = self.bs.readUShort()/65535
            edges.append(edge)
        data["edges"] = edges

        # collision edges
        self.bs.seek(collision_edge_offset)
        collision_edges = []
        for x in range(collision_edge_count):
            collision_edge = []
            collision_edge.append([self.bs.readUShort() for _ in range(2)])
            collision_edges.append(collision_edge)
        data["collision_edges"] = collision_edges

        self.bs.seek(face_groups_offset)
        face_groups = [self.bs.readUInt() for _ in range(face_group_count)]
        data["face_groups"] = face_groups

        self.bs.seek(edge_group_offset)
        edge_groups = [self.bs.readUInt() for _ in range(edge_group_count)]
        data["edge_groups"] = edge_groups

        self.bs.seek(collision_edge_group_offset)
        collision_edge_groups = [self.bs.readUInt() for _ in range(collision_edge_group_count)]
        data["collision_edge_groups"] = collision_edge_groups

        # batch infos
        self.bs.seek(batch_info_offset)
        batch_infos = []
        for x in range(batch_info_count):
            batch_info = {}
            batch_info["vertice_count"] = self.bs.readUInt()
            batch_info["face_count"] = self.bs.readUInt()
            batch_info["edge_count"] = self.bs.readUInt()
            batch_info["collision_edge_count"] = self.bs.readUInt()
            batch_info["face_group_count"] = self.bs.readUInt()
            batch_info["edge_group_count"] = self.bs.readUInt()
            batch_info["collision_edge_group_count"] = self.bs.readUInt()
            batch_info["deform_info_count"] = self.bs.readUInt()
            batch_info["point_face_contact_count"] = self.bs.readUInt()
            batch_info["edge_edge_contact_count"] = self.bs.readUInt()

            batch_info["vertice_offset"] = self.bs.readUInt()
            batch_info["face_offset"] = self.bs.readUInt()
            batch_info["edge_offset"] = self.bs.readUInt()
            batch_info["collision_edge_offset"] = self.bs.readUInt()
            batch_info["face_group_offset"] = self.bs.readUInt()
            batch_info["edge_group_offset"] = self.bs.readUInt()
            batch_info["collision_edge_group_offset"] = self.bs.readUInt()
            batch_info["deform_info_offset"] = self.bs.readUInt()
            batch_info["point_face_contact_offset"] = self.bs.readUInt()
            batch_info["edge_edge_contact_offset"] = self.bs.readUInt()
            batch_infos.append(batch_info)
        data["batch_infos"] = batch_infos

        self.bs.seek(offset_17)
        unk17 = [self.bs.readUInt() for _ in range(deform_count)]
        #print(np.mean(unk17))

        self.bs.seek(deform_offset)
        deforms = []
        for x in range(deform_count):
            deform = {}
            for face_i in range(deform_size):
                deform["unk_short_"+str(face_i)] = self.bs.readUShort()
                deform["face_idx_"+str(face_i)] = self.bs.readShort()
                deform["unk_int_"+str(face_i)] = self.bs.readUInt()
            deforms.append(deform)
        data["deforms"] = deforms

        self.bs.seek(original_vertex_array_offset)
        vertex_deform_references = []
        for x in range(original_vertex_count):
            vertex_deform_references.append(self.bs.readInt())
        data["vertex_deform_references"] = vertex_deform_references

        # debug vertices
        self.bs.seek(debug_vertice_offset)
        debug_vertices = []
        for x in range(vertice_count):
            debug_vertice = {}
            debug_vertice["massScale"] = self.bs.readFloat()
            debug_vertice["shearStiffness"] = self.bs.readFloat()
            debug_vertice["bendStiffness"] = self.bs.readFloat()
            debug_vertice["userColor"] = [self.bs.readFloat() for _ in range(3)]
            debug_vertices.append(debug_vertice)
        data["debug_vertices"] = debug_vertices

        # debug edges
        self.bs.seek(debug_edge_offset)
        debug_edges = []
        for x in range(edge_group_count):
            debug_edge = {}
            debug_edge["unk"] = [self.bs.readUInt() for _ in range(4)]
            debug_edges.append(debug_edge)
        data["debug_edges"] = debug_edges

        cloth_sims = []
        for batch_info in batch_infos:
            cloth_sim = {}
            cloth_sim["vertices"] = data["vertices"][batch_info["vertice_offset"]:batch_info["vertice_offset"]+batch_info["vertice_count"]]
            cloth_sim["faces"] = data["faces"][batch_info["face_offset"]:batch_info["face_offset"]+batch_info["face_count"]]
            cloth_sim["edges"] = data["edges"][batch_info["edge_offset"]:batch_info["edge_offset"]+batch_info["edge_count"]]
            ## I don't know how to use the rest
            cloth_sims.append(cloth_sim)

        return cloth_sims, data

if __name__ == "__main__":
    from glob import glob

    gpuc_files = ["helm_001_m.gpuc.231011972"]
    for gpuc_file in gpuc_files:
        parser = GpucParser(path=gpuc_file)
        cloth_sims, data = parser.read()
