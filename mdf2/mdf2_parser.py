import struct
import os
from glob import glob
import json
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

    def readString(self, byte_n=1):
        text = ""
        while True:
            if byte_n == 1:
                char = self.readUByte()
            else:
                char = self.readUByte()
                _ = self.readUByte()
            if char == 0:
                break
            else:
                text += chr(char)
        return text

    def allign(self, size):
        self.offset = (int((self.offset)/size)*size)+size
        
    def tell(self):
        return self.offset
    
    def getSize(self):
        return len(self.data)

class Mdf2Parser():
    def __init__(self, path=None, data=None):
        self.path = path
        if data is None:
            with open(path, "rb") as file_in:
                data = file_in.read()
        self.bs = Reader(data)
        self.debug_data = {}

    def read(self):
        self.magic = self.bs.readUInt()
        if self.magic != 4605005:
            raise RuntimeError(str(self.path) + " is not a mdf2 file (magic = " + str(magic) + ")")
        unk0 = self.bs.readUShort()
        self.material_count = self.bs.readUShort()
        unk1 = self.bs.readUInt64()
        self.debug_data["magic"] = self.magic
        self.debug_data["material_count"] = self.material_count
        self.materials = {}
        material_infos = []
        for mat_i in range(self.material_count):
            material_info = {}
            material_info["name_offset"] = self.bs.readUInt64()
            material_info["name_hash"] = self.bs.readUInt()
            material_info["prop_size"] = self.bs.readUInt()
            material_info["prop_count"] = self.bs.readUInt()
            material_info["tex_count"] = self.bs.readUInt()
            material_info["buffer_count"] = self.bs.readUInt()
            material_info["buffer_count_2"] = self.bs.readUInt()
            material_info["shader_type"] = self.bs.readUInt()
            material_info["flag1"] = self.bs.readUByte()
            material_info["flag2"] = self.bs.readUByte()
            material_info["phong"] = self.bs.readUByte()
            material_info["flag3"] = self.bs.readUByte()
            material_info["unknown_hash1"] = self.bs.readUShort()
            material_info["unknown_hash2"] = self.bs.readUShort()
            material_info["unk2"] = self.bs.readUInt64()
            material_info["prop_headers_off"] = self.bs.readUInt64()
            material_info["tex_headers_off"] = self.bs.readUInt64()
            material_info["buffer_table_off"] = self.bs.readUInt64()
            material_info["main_prop_data_off"] = self.bs.readUInt64()
            material_info["mmtr_path_off"] = self.bs.readUInt64()
            material_info["unk3"] = self.bs.readUInt64()
            material_infos.append(material_info)

        for material_info in material_infos:
            self.bs.seek(material_info["name_offset"])
            material_info["mat_name"] = self.bs.readString(byte_n = 2)
            self.bs.seek(material_info["mmtr_path_off"])
            material_info["mmtr_path"] = self.bs.readString(byte_n = 2)
            self.bs.seek(material_info["tex_headers_off"])

            tex_infos = []
            for tex_i in range(material_info["tex_count"]):
                tex_info = {}
                tex_info["texture_type_off"] = self.bs.readUInt64()
                tex_info["utf16_mmh3_hash"] = self.bs.readUInt()
                tex_info["ascii_mmh3_hash"] = self.bs.readUInt()
                tex_info["file_path_off"] = self.bs.readUInt64()
                tex_info["unk"] = self.bs.readUInt64()
                tex_infos.append(tex_info)

            textures = {}
            for tex_info in tex_infos:
                self.bs.seek(tex_info["texture_type_off"])
                tex_info["texture_type"] = self.bs.readString(byte_n = 2)
                self.bs.seek(tex_info["file_path_off"])
                tex_info["file_path"] = self.bs.readString(byte_n = 2)
                textures[tex_info["texture_type"]] = tex_info["file_path"]
            material_info["textures"] = textures

            self.bs.seek(material_info["buffer_table_off"])
            buffer_infos = []
            for buffer_i in range(material_info["buffer_count"]):
                buffer_info = {}
                buffer_info["buffer_type_off"] = self.bs.readUInt64()
                buffer_info["utf16_mmh3_hash"] = self.bs.readUInt()
                buffer_info["ascii_mmh3_hash"] = self.bs.readUInt()
                buffer_info["file_path_off"] = self.bs.readUInt64()
                buffer_info["unk1"] = self.bs.readUInt()
                buffer_info["unk2"] = self.bs.readUInt()
                buffer_infos.append(buffer_info)

            buffers = {}
            for buffer_info in buffer_infos:
                self.bs.seek(buffer_info["buffer_type_off"])
                buffer_info["buffer_type"] = self.bs.readString(byte_n = 2)
                self.bs.seek(buffer_info["file_path_off"])
                buffer_info["file_path"] = self.bs.readString(byte_n = 2)
                buffers[buffer_info["buffer_type"]] = buffer_info["file_path"]
            material_info["buffers"] = buffer_infos

            self.bs.seek(material_info["prop_headers_off"])
            prop_infos = []
            for prop_i in range(material_info["prop_count"]):
                prop_info = {}
                prop_info["prop_name_off"] = self.bs.readUInt64()
                prop_info["utf16_mmh3_hash"] = self.bs.readUInt()
                prop_info["ascii_mmh3_hash"] = self.bs.readUInt()
                prop_info["prop_data_off"] = self.bs.readUInt()
                prop_info["param_count"] = self.bs.readUInt()
                prop_infos.append(prop_info)

            properties = {}
            for prop_info in prop_infos:

                self.bs.seek(prop_info["prop_name_off"])
                prop_info["prop_name"] = self.bs.readString(byte_n = 2)

                self.bs.seek(material_info["main_prop_data_off"] + prop_info["prop_data_off"])
                if prop_info["param_count"] == 1:
                    val = self.bs.readFloat()
                elif prop_info["param_count"] == 4:
                    val = [
                        self.bs.readFloat(),
                        self.bs.readFloat(),
                        self.bs.readFloat(),
                        self.bs.readFloat()
                    ]
                prop_info["value"] = val
                properties[prop_info["prop_name"]] = prop_info["value"]

            self.materials[material_info["mat_name"]] = {
                "mmtr_path":material_info["mmtr_path"],
                "textures":textures,
                "properties":properties,
                "shader_type":material_info["shader_type"],
                "flag1":material_info["flag1"],
                "flag2":material_info["flag2"],
                "phong":material_info["phong"],
                "flag3":material_info["flag3"],
                "unknown_hash1":material_info["unknown_hash1"],
                "unknown_hash2":material_info["unknown_hash2"],
                "material_info":material_info
            }


            #mat_start = self.bs.tell()
            #name_offset = self.bs.readUInt64()
            #name_hash = self.bs.readUInt()
            #prop_size = self.bs.readUInt()
            #prop_count = self.bs.readUInt()
            #tex_count = self.bs.readUInt()
            #unk = self.bs.readUInt64()
            #shader_type = self.bs.readUInt()
            #flag1 = self.bs.readUByte()
            #flag2 = self.bs.readUByte()
            #phong = self.bs.readUByte()
            #flag3 = self.bs.readUByte()
            #unknown_hash = self.bs.readUInt()
            #_ = self.bs.readUInt64()
            #prop_headers_off = self.bs.readUInt64()
            #tex_headers_off = self.bs.readUInt64()
            #buffer_table_off = self.bs.readUInt64()
            #main_prop_data_off = self.bs.readUInt64()
            #mmtr_path_off = self.bs.readUInt64()
            
            #self.bs.seek(name_offset)
            #mat_name = self.bs.readString(byte_n = 2)
            #self.bs.seek(mmtr_path_off)
            #mmtr_path = self.bs.readString(byte_n = 2)
            #self.bs.seek(tex_headers_off)
            #textures = {}
            #for tex_i in range(tex_count):
                #tex_start = self.bs.tell()
                #texture_type_off = self.bs.readUInt64()
                #utf16_mmh3_hash = self.bs.readUInt()
                #ascii_mmh3_hash = self.bs.readUInt()
                #file_path_off = self.bs.readUInt64()
                
                #unk = self.bs.readUInt64()
                
                #self.bs.seek(texture_type_off)
                #texture_type = self.bs.readString(byte_n = 2)
                
                #self.bs.seek(file_path_off)
                #file_path = self.bs.readString(byte_n = 2)
                #textures[texture_type] = file_path
                #self.bs.seek(tex_start + 32)
            
            #self.bs.seek(prop_headers_off)
            #properties = {}
            #for prop_i in range(prop_count):
                #prop_start = self.bs.tell()
                #prop_name_off = self.bs.readUInt64()
                #utf16_mmh3_hash = self.bs.readUInt()
                #ascii_mmh3_hash = self.bs.readUInt()
                #prop_data_off = self.bs.readUInt()
                #param_count = self.bs.readUInt()
                
                #self.bs.seek(prop_name_off)
                #prop_name = self.bs.readString(byte_n = 2)
                
                #self.bs.seek(main_prop_data_off + prop_data_off)
                #if param_count == 1:
                    #val = self.bs.readFloat()
                #elif param_count == 4:
                    #val = [
                        #self.bs.readFloat(),
                        #self.bs.readFloat(),
                        #self.bs.readFloat(),
                        #self.bs.readFloat()
                    #]
                #properties[prop_name] = val
                #self.bs.seek(prop_start + 24)
                
            #self.materials[mat_name] = {
                #"mmtr_path":mmtr_path,
                #"textures":textures,
                #"properties":properties,
                #"shader_type":shader_type,
                #"flag1":flag1,
                #"flag2":flag2,
                #"phong":phong,
                #"flag3":flag3
            #}
            #self.bs.seek(mat_start + 100)
        return self.materials

if __name__ == "__main__":
    pass
    #parser = MeshParser("./item_224/mod/item_224.mesh.2109148288")
    parser = Mdf2Parser("wp00_000.mdf2.40")
    #parser = Mdf2Parser(mdf2_file)
    data = parser.read()
    print(data)
