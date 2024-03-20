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
        for mat_i in range(self.material_count):
            mat_start = self.bs.tell()
            name_offset = self.bs.readUInt64()
            name_hash = self.bs.readUInt()
            prop_size = self.bs.readUInt()
            prop_count = self.bs.readUInt()
            tex_count = self.bs.readUInt()
            unk = self.bs.readUInt64()
            shader_type = self.bs.readUInt()
            flag1 = self.bs.readUByte()
            flag2 = self.bs.readUByte()
            phong = self.bs.readUByte()
            flag3 = self.bs.readUByte()
            unknown_hash = self.bs.readUInt()
            _ = self.bs.readUInt64()
            prop_headers_off = self.bs.readUInt64()
            tex_headers_off = self.bs.readUInt64()
            string_table_off = self.bs.readUInt64()
            main_prop_data_off = self.bs.readUInt64()
            mmtr_path_off = self.bs.readUInt64()
            
            self.bs.seek(name_offset)
            mat_name = self.bs.readString(byte_n = 2)
            self.bs.seek(mmtr_path_off)
            mmtr_path = self.bs.readString(byte_n = 2)
            self.bs.seek(tex_headers_off)
            textures = {}
            for tex_i in range(tex_count):
                tex_start = self.bs.tell()
                texture_type_off = self.bs.readUInt64()
                utf16_mmh3_hash = self.bs.readUInt()
                ascii_mmh3_hash = self.bs.readUInt()
                file_path_off = self.bs.readUInt64()
                
                unk = self.bs.readUInt64()
                
                self.bs.seek(texture_type_off)
                texture_type = self.bs.readString(byte_n = 2)
                
                self.bs.seek(file_path_off)
                file_path = self.bs.readString(byte_n = 2)
                textures[texture_type] = file_path
                self.bs.seek(tex_start + 32)
            
            self.bs.seek(prop_headers_off)
            properties = {}
            for prop_i in range(prop_count):
                prop_start = self.bs.tell()
                prop_name_off = self.bs.readUInt64()
                utf16_mmh3_hash = self.bs.readUInt()
                ascii_mmh3_hash = self.bs.readUInt()
                prop_data_off = self.bs.readUInt()
                param_count = self.bs.readUInt()
                
                self.bs.seek(prop_name_off)
                prop_name = self.bs.readString(byte_n = 2)
                
                self.bs.seek(main_prop_data_off + prop_data_off)
                if param_count == 1:
                    val = self.bs.readFloat()
                elif param_count == 4:
                    val = [
                        self.bs.readFloat(),
                        self.bs.readFloat(),
                        self.bs.readFloat(),
                        self.bs.readFloat()
                    ]
                properties[prop_name] = val
                self.bs.seek(prop_start + 24)
                
            self.materials[mat_name] = {
                "mmtr_path":mmtr_path, 
                "textures":textures, 
                "properties":properties,
                "shader_type":shader_type,
                "flag1":flag1,
                "flag2":flag2,
                "phong":phong,
                "flag3":flag3
            }
            self.bs.seek(mat_start + 100)
        return self.materials

if __name__ == "__main__":
    pass
    #parser = MeshParser("./item_224/mod/item_224.mesh.2109148288")
    #parser = MeshParser("./000/mod/hm06_000.mesh.2109148288")
    #parser = Mdf2Parser(mdf2_file)
    #data = parser.read()
    #print(data)
