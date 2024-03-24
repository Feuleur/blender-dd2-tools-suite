import struct
import codecs
import json
from glob import glob
import os
import pdb
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

    def readString(self, size):
        text = ""
        for _ in range(size):
            char = self.readUShort()
            if char == 0:
                break
            text += chr(char)
        return text

    def allign_soft(self, size, shift=0):
        if (self.offset-shift)%size == 0:
            pass
        else:
            self.allign(size, shift)

    def allign(self, size, shift=0):
        self.offset = ((int((self.offset-shift)/size)*size)+size)+shift
        
    def tell(self):
        return self.offset
    
    def getSize(self):
        return len(self.data)



class ScnParser():
    def __init__(self, path = "", data = None, hashdict = None, hashdict_add = None):
        self.path = path
        with open(os.path.join(os.path.dirname(__file__), "rszdd2.json"), "r") as json_in:
            self.hashdict = json.load(json_in)
        with open(os.path.join(os.path.dirname(__file__), "rszdd2_add.json"), "r") as json_in:
            self.hashdict_add = json.load(json_in)
        if data is None:
            with open(self.path, "rb") as file_in:
                data = file_in.read()
        self.bs = Reader(data)
    
    def read(self):
        bs = self.bs
        magic = bs.readUInt()
        if magic != 5129043:
            raise RuntimeError(str(self.path) + " is not a scn file (magic = " + str(magic) + ")")
        infoCount = bs.readUInt()
        resourceCount = bs.readUInt()
        folderCount = bs.readUInt()
        prefabCount = bs.readUInt()
        userdataCount = bs.readUInt()
        folderInfoTbl = bs.readUInt64()
        resourceInfoTbl = bs.readUInt64()
        prefabInfoTbl = bs.readUInt64()
        userdataInfoTbl = bs.readUInt64()
        RSZ_offset = bs.readUInt64()
        
        #print("infoCount", infoCount, "resourceCount", resourceCount, "folderCount", folderCount, "prefabCount", prefabCount, "userdataCount", userdataCount)
        
        # GameObjects
        gobj_count = int((folderInfoTbl - (16*4))/32)
        gobj_dict = {}
        for gobj_i in range(gobj_count):
            gobj_uuid_1, gobj_uuid_2 = bs.readUInt64(), bs.readUInt64()
            gobj_id = bs.readUInt()
            gobj_parent_id = bs.readInt()
            gobj_component_count = bs.readUShort()
            _ = bs.readUShort()
            _ = bs.readUInt()
            gobj_dict[gobj_id] = {
                "gobj_id":gobj_id, 
                "gobj_i":gobj_i,
                "gobj_parent_id":gobj_parent_id, 
                "gobj_component_count":gobj_component_count
            }
        
        bs.seek(folderInfoTbl)
        folder_dict = {}
        for folder_i in range(folderCount):
            folder_id = bs.readUInt()
            folder_parent_id = bs.readUInt()
            folder_dict[folder_id] = {
                "folder_id":folder_id, 
                "folder_parent_id":folder_parent_id, 
            }
        
        bs.seek(RSZ_offset)
        RSZ_magic = bs.readUInt()
        RSZ_version = bs.readUInt()
        OBJ_count = bs.readUInt()
        TYPE_count = bs.readUInt()
        USRDATA_count = bs.readUInt()
        #print(RSZ_offset%16)
        #print(bs.tell(), RSZ_offset%16)
        bs.allign_soft(8, RSZ_offset%16)
        #bs.allign_soft(8)
        #print(bs.tell())
        TYPE_offset = RSZ_offset + bs.readUInt64()
        DATA_offset = RSZ_offset + bs.readUInt64()
        USRDATA_offset = RSZ_offset + bs.readUInt64()
        #print(TYPE_offset, DATA_offset, USRDATA_offset)
        #print(RSZ_version, OBJ_count, TYPE_count, USRDATA_count)
        OBJ_table = []
        # For some godforsaken reason the array indices sometimes start at 0, sometimes at 1
        for x in range(OBJ_count):
            OBJ_table.append(bs.readUInt()-1)
        gobj_dict_treated = {}
        for k,v in gobj_dict.items():
            if v["gobj_parent_id"] != -1:
                v["gobj_parent_id"] = OBJ_table[v["gobj_parent_id"]]
            else:
                v["gobj_parent_id"] = -1
            gobj_dict_treated[OBJ_table[k]] = v
        
        #gobj_dict_treated = {OBJ_table[k]:v for k,v in gobj_dict.items()}
        bs.seek(TYPE_offset)
        bs.seek(8, 0)
        TYPE_table = []
        for x in range(TYPE_count-1):
            #print(x)
            TYPE_table.append(hex(bs.readUInt())[2:])
            #print(TYPE_table[-1])
            bs.readUInt()
        print("TYPE_table = ", TYPE_table)
        bs.seek(DATA_offset)
        gameObject_datas = []
        current_gobject = None
        #print(gobj_dict_treated)
        
        for obj_i in range(TYPE_count-1)[:]:
            #print(OBJ_count)
            #print(obj_i)
            
            #print(gobj_dict)
            #
            if obj_i in gobj_dict_treated.keys():
                if current_gobject is not None:
                    gameObject_datas.append(current_gobject)
                current_gobject = {}
                if gobj_dict_treated[obj_i]["gobj_parent_id"] != -1 and gobj_dict_treated[obj_i]["gobj_parent_id"] in gobj_dict_treated.keys():
                    current_gobject["parent"] = gobj_dict_treated[gobj_dict_treated[obj_i]["gobj_parent_id"]]["gobj_i"]
                else:
                    current_gobject["parent"] = None
                #current_gobject["fields"] = {}
            current_object = {}
            #print(current_gobject)
            
            
            
            if TYPE_table[obj_i] not in self.hashdict.keys():
                logger.error("Unknown object encountered during scene parsing: " + TYPE_table[obj_i])
            
            obj_struct = self.hashdict[TYPE_table[obj_i]]
            current_object["name"] = obj_struct["name"]
            current_object["hash"] = TYPE_table[obj_i]
            print("TYPE_table = ", TYPE_table[obj_i])

            #print(obj_i, current_object["name"], current_object["hash"], bs.tell())
            #if current_gobject is not None and "object_name" in current_gobject:
                #if current_gobject["object_name"] == "v01a00_watermesh02":
                    #logger.error(current_object["name"] + " " + current_object["hash"])
                #print("name = ", current_gobject["object_name"])
            #else:
                #print("no name yet")
            #if obj_i in gobj_dict_treated.keys() and current_object["name"] != "via.GameObject":
                #logger.error("")
            #print(current_object)
            #print("A")
            fields = {}
            potential_rendered_object = False
            
            print(obj_struct)
            for field in obj_struct["fields"]:
                print("position ", hex(bs.tell()))
                print("field", field)
                size_array = 1
                if field["array"]:
                    bs.allign_soft(4)
                    size_array = bs.readUInt()
                    bs.allign_soft(field["align"])
                else:
                    bs.allign_soft(field["align"])
                print("size_array", size_array)
                content = {}
                for x in range(size_array):
                    bs.allign_soft(field["align"])
                    known_data = False
                    if TYPE_table[obj_i] in self.hashdict_add.keys():
                        print("TYPE_table[obj_i] = ", TYPE_table[obj_i])
                        # Read known data
                        if field["name"] in self.hashdict_add[TYPE_table[obj_i]].keys():
                            field_data = self.hashdict_add[TYPE_table[obj_i]][field["name"]]
                            for ftype, fname in zip(field_data["types"], field_data["names"]):
                                if ftype == "float":
                                    content[fname] = bs.readFloat()
                                elif ftype == "uint32":
                                    content[fname] = bs.readUInt()
                                elif ftype == "string":
                                    string_size = bs.readUInt()
                                    #print(string_size)
                                    content[fname] = bs.readString(string_size)
                                    #print(content[fname])
                            known_data = True
                    if not known_data:
                        # To skip datas that aren't in the known data
                        if field["type"] in ["String", "Resource"]:
                            string_size = bs.readUInt()
                            #print(string_size)
                            string = bs.readString(string_size)
                            if string.endswith(".mesh.2109148288"):
                                potential_rendered_object = True
                            print("   String = ", string)
                        else:
                            bs.seek(field["size"], 0)
                for k,v in content.items():
                    current_gobject[k] = v
            if potential_rendered_object:
                #logger.debug("Skipped object which contained a path to a mesh file " + current_object["name"])
                logger.error("Skipped object which contained a path to a mesh file " + current_object["name"])
            #print("B")
            print(current_gobject)
        gameObject_datas.append(current_gobject)
        return gameObject_datas

if __name__ == "__main__":
    parser = ScnParser(path="./farenvironment.scn.20")
    data = parser.read()
