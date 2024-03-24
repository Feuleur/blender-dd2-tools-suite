import struct
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
    
    def readStringUTFAt(self, offset):
        previous_offset = self.tell()
        self.seek(offset)
        text = ""
        while True:
            char = self.readUShort()
            if char == 0:
                break
            else:
                text += chr(char)
        self.seek(previous_offset)
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

    def allign(self, size):
        self.offset = (int((self.offset)/size)*size)+size
        
    def tell(self):
        return self.offset
    
    def getSize(self):
        return len(self.data)

def convertBits(packedInt, numBits):
    return packedInt / (2**numBits-1)

def readPackedBitsVec3(packedInt, numBits):
    limit = 2**numBits-1
    x = ((packedInt >> 0) 		    & limit) / limit
    y = ((packedInt >> (numBits*1)) & limit) / limit
    z = ((packedInt >> (numBits*2)) & limit) / limit
    return [x, y, z]

def quat3_to_quat(quat3):
    w = abs(1-(quat3[0]**2 + quat3[1]**2 + quat3[2]**2))**0.5
    return [quat3[0], quat3[1], quat3[2], w]

def decode_value(bs, transf_name, compression, unpackValues, version):
    if transf_name=="loc" or transf_name=="scl":
        if compression == 0x00000:
            vec = [
                bs.readFloat(), 
                bs.readFloat(), 
                bs.readFloat()
            ]
        elif compression == 0x20000:
            rawVec = readPackedBitsVec3(bs.readUShort(), 5)
            if version <= 65:
                vec = [
                    (unpackValues["max"]["x"] * rawVec[0] + unpackValues["min"]["x"]), 
                    (unpackValues["max"]["y"] * rawVec[1] + unpackValues["min"]["z"]), 
                    (unpackValues["max"]["y"] * rawVec[2] + unpackValues["min"]["z"])
                ]
            else:
                vec = [
                    (unpackValues["max"]["x"] * rawVec[0] + unpackValues["max"]["w"]), 
                    (unpackValues["max"]["y"] * rawVec[1] + unpackValues["min"]["x"]), 
                    (unpackValues["max"]["y"] * rawVec[2] + unpackValues["min"]["y"])
                ]
        elif compression == 0x24000:
            x = y = z = unpackValues["max"]["x"] * convertBits(bs.readUShort(), 16) + unpackValues["max"]["y"]
            vec = [
                x, 
                y, 
                z
            ]
        elif compression == 0x44000:
            x = y = z = bs.readFloat()
            vec = [
                x, 
                y, 
                z
            ]
        elif compression == 0x40000 or (compression == 0x30000 and version <= 65):
            rawVec = readPackedBitsVec3(bs.readUInt(), 10)
            if version <= 65:
                vec = [
                    (unpackValues["max"]["x"] * rawVec[0] + unpackValues["min"]["x"]), 
                    (unpackValues["max"]["y"] * rawVec[1] + unpackValues["min"]["y"]), 
                    (unpackValues["max"]["z"] * rawVec[2] + unpackValues["min"]["z"])
                ]
            else:
                vec = [
                    (unpackValues["max"]["x"] * rawVec[0] + unpackValues["max"]["w"]), 
                    (unpackValues["max"]["y"] * rawVec[1] + unpackValues["min"]["x"]), 
                    (unpackValues["max"]["z"] * rawVec[2] + unpackValues["min"]["y"])
                ]
        elif compression == 0x70000:
            rawVec = readPackedBitsVec3(bs.readUInt64(), 21)
            vec = [
                (unpackValues["max"]["x"] * rawVec[0] + unpackValues["min"]["x"]), 
                (unpackValues["max"]["y"] * rawVec[1] + unpackValues["min"]["y"]), 
                (unpackValues["max"]["z"] * rawVec[2] + unpackValues["min"]["z"])
            ]
        elif compression == 0x80000:
            rawVec = readPackedBitsVec3(bs.readUInt64(), 21)
            vec = [
                (unpackValues["max"]["x"] * rawVec[0] + unpackValues["max"]["w"]), 
                (unpackValues["max"]["y"] * rawVec[1] + unpackValues["min"]["x"]), 
                (unpackValues["max"]["z"] * rawVec[2] + unpackValues["min"]["y"])
            ]
        elif (compression == 0x31000 and version <= 65) or (compression == 0x41000 and version >= 78): #LoadVector3sXAxis
            vec = [
                bs.readFloat(), 
                unpackValues["max"]["y"], 
                unpackValues["max"]["z"]
            ]
        elif (compression == 0x32000 and version <= 65) or (compression == 0x42000 and version >= 78): #LoadVector3sYAxis
            vec = [
                unpackValues["max"]["x"], 
                bs.readFloat(), 
                unpackValues["max"]["z"]
            ]
        elif (compression == 0x33000 and version <= 65) or (compression == 0x43000 and version >= 78): #LoadVector3sZAxis
            vec = [
                unpackValues["max"]["x"], 
                unpackValues["max"]["y"], 
                bs.readFloat()
            ]
        elif compression == 0x21000:
            vec = [
                unpackValues["max"]["x"] * convertBits(bs.readUShort(), 16) + unpackValues["max"]["y"], 
                unpackValues["max"]["z"], 
                unpackValues["max"]["w"]
            ]
        elif compression == 0x22000:
            vec = [
                unpackValues["max"]["y"], 
                unpackValues["max"]["x"] * convertBits(bs.readUShort(), 16) + unpackValues["max"]["z"], 
                unpackValues["max"]["w"]
            ]
        elif compression == 0x23000:
            vec = [
                unpackValues["max"]["y"], 
                unpackValues["max"]["z"], 
                unpackValues["max"]["x"] * convertBits(bs.readUShort(), 16) + unpackValues["max"]["w"]
            ]
        else:
            vec = [
                0.0, 0.0, 0.0
            ]
        return vec
    elif transf_name == "rot":
        if compression == 0x00000:
            vec_quat = [
                bs.readFloat(), 
                bs.readFloat(), 
                bs.readFloat(), 
                bs.readFloat()
            ]
        elif compression == 0xB0000 or compression == 0xC0000:
            vec_quat3 = [
                bs.readFloat(), 
                bs.readFloat(), 
                bs.readFloat()
            ]
            vec_quat = quat3_to_quat(vec_quat3)
        elif compression == 0x20000: #//LoadQuaternions5Bit RE3
            rawVec = readPackedBitsVec3(bs.readUShort(), 5)
            vec_quat3 = [
                (unpackValues["max"]["x"] * rawVec[0] + unpackValues["min"]["x"]), 
                (unpackValues["max"]["y"] * rawVec[1] + unpackValues["min"]["y"]), 
                (unpackValues["max"]["z"] * rawVec[2] + unpackValues["min"]["z"])
            ]
            vec_quat = quat3_to_quat(vec_quat3)
        elif compression == 0x21000:
            vec_quat3 = [
                (unpackValues["max"]["x"] * convertBits(bs.readUShort(), 16) + unpackValues["max"]["y"]), 
                0, 
                0
            ]
            vec_quat = quat3_to_quat(vec_quat3)
        elif compression == 0x22000:
            vec_quat3 = [
                0, 
                (unpackValues["max"]["x"] * convertBits(bs.readUShort(), 16) + unpackValues["max"]["y"]), 
                0
            ]
            vec_quat = quat3_to_quat(vec_quat3)
        elif compression == 0x23000:
            vec_quat3 = [
                0, 
                0, 
                (unpackValues["max"]["x"] * convertBits(bs.readUShort(), 16) + unpackValues["max"]["y"])
            ]
            vec_quat = quat3_to_quat(vec_quat3)
        elif compression == 0x30000 and version >= 78: #LoadQuaternions8Bit RE3
            rawVec = [convertBits(bs.readUByte(), 8), convertBits(bs.readUByte(), 8), convertBits(bs.readUByte(), 8)]
            vec_quat3 = [
                (unpackValues["max"]["x"] * rawVec[0] + unpackValues["min"]["x"]), 
                (unpackValues["max"]["y"] * rawVec[1] + unpackValues["min"]["y"]), 
                (unpackValues["max"]["z"] * rawVec[2] + unpackValues["min"]["z"])
            ]
            vec_quat = quat3_to_quat(vec_quat3)
        elif compression == 0x30000: 
            rawVec = readPackedBitsVec3(bs.readUShort(), 5)
            vec_quat3 = [
                (unpackValues["max"]["x"] * rawVec[0] + unpackValues["min"]["x"]), 
                (unpackValues["max"]["y"] * rawVec[1] + unpackValues["min"]["y"]), 
                (unpackValues["max"]["z"] * rawVec[2] + unpackValues["min"]["z"])
            ]
            vec_quat = quat3_to_quat(vec_quat3)
        elif compression == 0x31000 or compression == 0x41000:
            vec_quat3 = [
                (bs.readFloat()), 
                0.0, 
                0.0
            ]
            vec_quat = quat3_to_quat(vec_quat3)
        elif compression == 0x32000 or compression == 0x42000:
            vec_quat3 = [
                0.0, 
                (bs.readFloat()), 
                0.0
            ]
            vec_quat = quat3_to_quat(vec_quat3)
        elif compression == 0x33000 or compression == 0x43000:
            vec_quat3 = [
                0.0, 
                0.0, 
                (bs.readFloat())
            ]
            vec_quat = quat3_to_quat(vec_quat3)
        elif compression == 0x40000: #LoadQuaternions10Bit RE3
            rawVec = readPackedBitsVec3(bs.readUInt(), 10)
            vec_quat3 = [
                (unpackValues["max"]["x"] * rawVec[0] + unpackValues["min"]["x"]), 
                (unpackValues["max"]["y"] * rawVec[1] + unpackValues["min"]["y"]), 
                (unpackValues["max"]["z"] * rawVec[2] + unpackValues["min"]["z"])
            ]
            vec_quat = quat3_to_quat(vec_quat3)
        elif compression == 0x50000 and version <= 65:
            rawVec = [convertBits(bs.readUShort(), 16), convertBits(bs.readUShort(), 16), convertBits(bs.readUShort(), 16)]
            vec_quat3 = [
                unpackValues["max"]["x"] * rawVec[0] + unpackValues["min"]["x"], 
                unpackValues["max"]["y"] * rawVec[1] + unpackValues["min"]["y"], 
                unpackValues["max"]["z"] * rawVec[2] + unpackValues["min"]["z"]
            ]
            vec_quat = quat3_to_quat(vec_quat3)
        elif compression == 0x50000: #LoadQuaternions13Bit RE3
            rawBytes = [bs.readUByte(), bs.readUByte(), bs.readUByte(), bs.readUByte(), bs.readUByte()]
            retrieved = (rawBytes[0] << 32) | (rawBytes[1] << 24) | (rawBytes[2] << 16) | (rawBytes[3] << 8) | (rawBytes[4] << 0)
            rawVec = readPackedBitsVec3(retrieved, 13)
            vec_quat3 = [
                (unpackValues["max"]["x"] * rawVec[0] + unpackValues["min"]["x"]), 
                (unpackValues["max"]["y"] * rawVec[1] + unpackValues["min"]["y"]), 
                (unpackValues["max"]["z"] * rawVec[2] + unpackValues["min"]["z"])
            ]
            vec_quat = quat3_to_quat(vec_quat3)
        elif compression == 0x60000:
            rawVec = [convertBits(bs.readUShort(), 16), convertBits(bs.readUShort(), 16), convertBits(bs.readUShort(), 16)]
            vec_quat3 = [
                (unpackValues["max"]["x"] * rawVec[0] + unpackValues["min"]["x"]), 
                (unpackValues["max"]["y"] * rawVec[1] + unpackValues["min"]["y"]), 
                (unpackValues["max"]["z"] * rawVec[2] + unpackValues["min"]["z"])
            ]
            vec_quat = quat3_to_quat(vec_quat3)
        elif (compression == 0x70000 and version <= 65) or (compression == 0x80000 and version >= 78):
            rawVec = readPackedBitsVec3(bs.readUInt64(), 21)
            vec_quat3 = [
                (unpackValues["max"]["x"] * rawVec[0] + unpackValues["min"]["x"]), 
                (unpackValues["max"]["y"] * rawVec[1] + unpackValues["min"]["y"]), 
                (unpackValues["max"]["z"] * rawVec[2] + unpackValues["min"]["z"])
            ]
            vec_quat = quat3_to_quat(vec_quat3)
        elif compression == 0x70000 and version >= 78: 
            rawBytes = [bs.readUByte(), bs.readUByte(), bs.readUByte(), bs.readUByte(), bs.readUByte(), bs.readUByte(), bs.readUByte()]
            retrieved = (rawBytes[0] << 48) | (rawBytes[1] << 40) | (rawBytes[2] << 32) | (rawBytes[3] << 24) | (rawBytes[4] << 16) | (rawBytes[5] << 8) | (rawBytes[6] << 0)
            rawVec = readPackedBitsVec3(retrieved, 18)
            vec_quat3 = [
                (unpackValues["max"]["x"] * rawVec[0] + unpackValues["min"]["x"]), 
                (unpackValues["max"]["y"] * rawVec[1] + unpackValues["min"]["y"]), 
                (unpackValues["max"]["z"] * rawVec[2] + unpackValues["min"]["z"])
            ]
            vec_quat = quat3_to_quat(vec_quat3)
        else:
            vec_quat = [
                0.0, 0.0, 0.0, 1.0
            ]
        return vec_quat

#tmp = []
class MotParser():
    def __init__(self, path=None, data=None, motlist_offset=0):
        self.path = path
        self.motlist_offset = motlist_offset
        if data is None:
            with open(path, "rb") as file_in:
                data = file_in.read()
        self.bs = Reader(data)
    
    def read(self, bone_infos=None):
        #global tmp
        self.version = self.bs.readUInt()
        self.magic = self.bs.readUInt()
        if self.magic != 544501613 or self.version != 698:
            if self.path is not None:
                raise RuntimeError(str(self.path) + " is not a dd2 mot file (magic = " + str(self.magic) + ", version = " + str(self.version) + ")")
            else:
                raise RuntimeError("Data is not a dd2 mot file (magic = " + str(self.magic) + ", version = " + str(self.version) + ")")
        _zero = self.bs.readUInt()
        motfile_size = self.bs.readUInt()
        bone_info_offset = self.bs.readUInt64()
        clip_header_offset = self.bs.readUInt64()
        _zero = self.bs.readUInt64()
        _zero = self.bs.readUInt64()
        clip_files_offset = self.bs.readUInt64()
        jmap_path_offset = self.bs.readUInt64()
        UKN2_offset = self.bs.readUInt64()
        UKN3_offset = self.bs.readUInt64()
        _zero = self.bs.readUInt64()
        name_offset = self.bs.readUInt64()
        frame_count = self.bs.readFloat()
        is_loop = self.bs.readFloat()
        _zero = self.bs.readUInt()
        _frame_count = self.bs.readFloat()
        bone_count = self.bs.readUShort()
        bone_clips_count = self.bs.readUShort()
        clip_files_count = self.bs.readUByte()
        UKN2_count = self.bs.readUByte()
        _count = self.bs.readUByte()
        _ = self.bs.readUByte()
        FPS = self.bs.readUInt()
        self.bs.allign(16)
        
        # clip files
        #print(hex(clip_files_offset))
        #if clip_files_offset != 0:
            #self.bs.seek(clip_files_offset)
            #clip_file_offsets_array = []
            #for clip_file_i in range(clip_files_count):
                #clip_file_offsets_array.append(self.bs.readUInt64())
            
            #for clip_file_offset in clip_file_offsets_array:
                #self.bs.seek(clip_file_offset)
                #_ = self.bs.readUInt64()
                #clip_start = self.bs.readUInt64()
                #_offset = self.bs.readUInt64()
                #_ = self.bs.readUInt64()
                #clip_count = self.bs.readUInt()
                #_count = self.bs.readUInt()
                #_ = self.bs.readUInt64()
                #_ = self.bs.readUInt64()
                #_ = self.bs.readUInt64()
                #self.bs.seek(clip_start)
                #clip_magic = self.bs.readUInt()
                #clip_version = self.bs.readUInt()
                #_ = self.bs.readFloat()
                #UNKN_count_1 = self.bs.readUInt()
                #UNKN_count_2 = self.bs.readUInt()
                #UNKN_count_3 = self.bs.readUInt()
                #UNKN_offset_1 = self.bs.readUInt64()
                #UNKN_offset_2 = self.bs.readUInt64()
                #UNKN_offset_3 = self.bs.readUInt64()
                #UNKN_offset_4 = self.bs.readUInt64()
                #UNKN_offset_5 = self.bs.readUInt64()
                #UNKN_offset_6 = self.bs.readUInt64()
                #UNKN_offset_7 = self.bs.readUInt64()
                #UNKN_offset_8 = self.bs.readUInt64()
                #self.bs.seek(UNKN_offset_1)
                
                    
                #print(clip_count)
                
                
                #print(clip_magic, clip_version)
                #if clip_magic != 1346980931:
                    
        # jmap path
        if jmap_path_offset != 0:
            self.bs.seek(jmap_path_offset)
            jmap_path = self.bs.readStringUTF()
        
        ## Unknown float
        #if UKN3_offset != 0:
            #self.bs.seek(UKN3_offset)
            ##_float = self.bs.readFloat()
        
        # Name
        self.bs.seek(name_offset)
        name = self.bs.readStringUTF()

        # Bone info
        if bone_infos is None:
            self.bs.seek(bone_info_offset)
            array_offset = self.bs.readUInt64()
            array_size = self.bs.readUInt64()
            self.bs.seek(array_offset)
            self.bone_infos = {}
            for _ in range(array_size):

                #print(hex(self.motlist_offset+self.bs.tell()))
                bone_name_offset = self.bs.readUInt64()
                bone_parent_offset = self.bs.readUInt64()
                bone_connexion_offset = self.bs.readUInt64()
                _ = self.bs.readUInt64()
                bone_pos = [self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat()]
                bone_rot = [self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat(), self.bs.readFloat()]
                bone_id = self.bs.readUInt()
                bone_hash = self.bs.readUInt()
                _ = self.bs.readUInt64()
                bone_name = self.bs.readStringUTFAt(bone_name_offset)
                 #== "root":
                #print(bone_name, bone_hash)
                self.bone_infos[bone_hash] = {
                    "name":bone_name,
                    "pos":bone_pos, 
                    "rot":bone_rot,
                    "id":bone_id, 
                    "hash":bone_hash
                }
        else:
            # The bone info is given by the motlist
            self.bone_infos = bone_infos

        #print("")
        # Bone clips
        self.bs.seek(clip_header_offset)
        clip_infos = {}
        for _ in range(bone_clips_count):
            #print(hex(self.motlist_offset+self.bs.tell()))
            clip_id = self.bs.readUShort()
            clip_flags = self.bs.readUShort()
            clip_bone_hash = self.bs.readUInt()
            clip_offset = self.bs.readUInt()
            #print("    ", clip_flags, clip_bone_hash)
            clip_infos[clip_id] = {
                "clip_flags":clip_flags, 
                "clip_bone_hash":clip_bone_hash, 
                "clip_offset":clip_offset
            }
        bone_action_dict = {}
        for clip_id, clip_info in clip_infos.items():
            self.bs.seek(clip_info["clip_offset"])
            table = ["loc", "rot", "scl"]
            clip_data = {}
            for i in range(3):
                if clip_info["clip_flags"] & (2**i):
                    #print(hex(self.motlist_offset+self.bs.tell()))
                    flags = self.bs.readUInt()
                    keyCount = self.bs.readUInt()
                    frameIndOffs = self.bs.readUInt()
                    frameDataOffs = self.bs.readUInt()
                    unpackDataOffs = self.bs.readUInt()
                    #print("    ", flags, self.bone_infos[clip_info["clip_bone_hash"]]["name"], table[i])
                    clip_data[table[i]] = {
                        "flags":flags, 
                        "keyCount":keyCount, 
                        "frameIndOffs":frameIndOffs, 
                        "frameDataOffs":frameDataOffs, 
                        "unpackDataOffs":unpackDataOffs,
                    }
            bone_action_dict[clip_info["clip_bone_hash"]] = clip_data
        
        out_bone_action_dict = {}
        for bone_hash, clip_data in bone_action_dict.items():
            for transf_name, transf_data in clip_data.items():
                # Times
                self.bs.seek(transf_data["frameIndOffs"])
                time_compression = transf_data["flags"] >> 20
                time_list = []
                for _ in range(transf_data["keyCount"]):
                    if time_compression == 5:
                        time = self.bs.readUInt()
                    elif time_compression == 2:
                        time = self.bs.readUByte()
                    else:
                        time = self.bs.readUShort()
                    time_list.append(time)
                # Unpack data
                if transf_data["unpackDataOffs"]:
                    self.bs.seek(transf_data["unpackDataOffs"])
                    unpackMax = {"x":self.bs.readFloat(), "y":self.bs.readFloat(), "z":self.bs.readFloat(), "w":self.bs.readFloat()}
                    unpackMin = {"x":self.bs.readFloat(), "y":self.bs.readFloat(), "z":self.bs.readFloat(), "w":self.bs.readFloat()}
                else:
                    unpackMax = unpackMin = {"x":0.0, "y":0.0, "z":0.0, "w":0.0}
                unpackValues = {"max":unpackMax, "min":unpackMin}
                # Values
                self.bs.seek(transf_data["frameDataOffs"])
                value_compression = transf_data["flags"] & 0xFF000
                value_list = []
                for _ in range(transf_data["keyCount"]):
                    value_list.append(decode_value(self.bs, transf_name, value_compression, unpackValues, self.version))
                if bone_hash not in out_bone_action_dict.keys():
                    out_bone_action_dict[bone_hash] = {}
                out_bone_action_dict[bone_hash][transf_name] = {time:value for time, value in zip(time_list, value_list)}

                            #print("human_basic_angry_idle_loop L_LowerLip_03_Edge", frame_count)
                            #print(bin(transf_data["flags"])[2:].zfill(32), transf_name)
                        #if self.bone_infos[bone_hash]["name"] == "L_Chin_01":
                            #print("human_basic_angry_idle_loop L_Chin_01", frame_count)
                            #print(bin(transf_data["flags"])[2:].zfill(32), transf_name)
                #if name == "ch00_000_atk_NA_cling":
                    #if self.bone_infos[bone_hash]["name"] == "Hip":
                        #print("ch00_000_atk_NA_cling Hip", frame_count)
                        #print(bin(transf_data["flags"])[2:].zfill(32), transf_name)
                    #if self.bone_infos[bone_hash]["name"] == "root":
                        #print("ch00_000_atk_NA_cling root", frame_count)
                        #print(bin(transf_data["flags"])[2:].zfill(32), transf_name)
                #flag_index = {"loc":14, "rot":14, "scl":14}
                out_bone_action_dict[bone_hash][transf_name + "_referential"] = "global"
                out_bone_action_dict[bone_hash][transf_name + "_flags"] = bin(transf_data["flags"])[2:].zfill(32)
                #if name == "ch20_000_com_cliff_climb_cling":
                    #interest = "Hip"

                    #if transf_name == "rot" or transf_name == "loc":

                        #if self.bone_infos[bone_hash]["name"] == interest:
                            #print(interest)
                            #print(value_list[10])
                            ##print(["global", "local"][(transf_data["flags"] >> flag_index[transf_name]) & 1])
                            #print(transf_data["flags"], bin(transf_data["flags"])[2:].zfill(32))
                
                
        bone_actions = []
        for bone_hash, bone_transfs in out_bone_action_dict.items():
            if bone_hash in self.bone_infos:
                pos_keyframes = {}
                rot_keyframes = {}
                scl_keyframes = {}
                
                pos_referential = "global"
                rot_referential = "global"
                scl_referential = "global"
                pos_flags = ""
                rot_flags = ""
                scl_flags = ""

                if "loc" in bone_transfs.keys():
                    pos_keyframes = bone_transfs["loc"]
                    pos_referential = bone_transfs["loc_referential"]
                    pos_flags = bone_transfs["loc_flags"]
                if "rot" in bone_transfs.keys():
                    rot_keyframes = bone_transfs["rot"]
                    rot_referential = bone_transfs["rot_referential"]
                    rot_flags = bone_transfs["rot_flags"]
                if "scl" in bone_transfs.keys():
                    scl_keyframes = bone_transfs["scl"]
                    scl_referential = bone_transfs["scl_referential"]
                    scl_flags = bone_transfs["scl_flags"]
                
                bone_actions.append({
                        "bone_name": self.bone_infos[bone_hash]["name"], 
                        "pos":pos_keyframes,
                        "pos_referential":pos_referential,
                        "pos_flags":pos_flags,
                        "rot":rot_keyframes,
                        "rot_referential":rot_referential,
                        "rot_flags":rot_flags,
                        "scl":scl_keyframes,
                        "scl_referential":scl_referential,
                        "scl_flags":scl_flags
                    }
                )

        bone_infos_reformated = {}
        for bone_hash, bone_value in self.bone_infos.items():
            bone_infos_reformated[bone_value["name"]] = {
                "pos":bone_value["pos"], 
                "rot":bone_value["rot"]
            }
        #print([[len(bone_action["pos"]), len(bone_action["rot"]), len(bone_action["scl"])] for bone_action in bone_actions])
        #tmp.append(name, len())
        #print(bone_infos_reformated["Hip"])
        return {
            "name":name,
            "frame_count":frame_count,
            "bone_infos":bone_infos_reformated, 
            "bones_actions":bone_actions
        }

class MotListParser():
    def __init__(self, path=None, data=None):
        self.path = path
        if data is None:
            with open(path, "rb") as file_in:
                data = file_in.read()
        self.bs = Reader(data)
    
    def read(self):
        self.version = self.bs.readUInt()
        self.magic = self.bs.readUInt()
        if self.magic != 1953721453 or self.version != 751:
            raise RuntimeError(str(self.path) + " is not a dd2 motlist file (magic = " + str(self.magic) + ", version = " + str(self.version) + ")")
        self.bs.allign(16)
        headers_offset = self.bs.readUInt64()
        ID_offset = self.bs.readUInt64()
        name_offset = self.bs.readUInt64()
        self.bs.allign(16)
        mot_count = self.bs.readUInt()
        
        motlist_data = {}
        
        # Name
        self.bs.seek(name_offset)
        self.name = self.bs.readStringUTF()
        
        mot_datas = []
        self.bs.seek(headers_offset)
        bone_infos = None
        encountered_mots = []
        warning_count = 0
        for _ in range(mot_count)[:]:
            mot_offset = self.bs.readUInt64()
            if mot_offset in encountered_mots:
                continue
            else:
                encountered_mots.append(mot_offset)
            try:
                parser = MotParser(path=None, data=self.bs.data[mot_offset:], motlist_offset=mot_offset)
                mot_datas.append(parser.read(bone_infos))
                if bone_infos is None:
                    bone_infos = parser.bone_infos
                #break
            except Exception as e:
                if "not a dd2 mot file" in str(e):
                    if warning_count == 0:
                        logger.warning("Could not read mot data inside motlist file (reason = " + str(e) + "). Following warning will be suppressed.")
                    warning_count += 1
                else:
                    raise e
        if warning_count > 1:
            logger.warning(str(warning_count) + " warnings were generated during import.")

        return {
            "name":self.name,
            "mot_datas":mot_datas
        }

if __name__ == "__main__":
    import json
    #parser = MeshParser("./item_224/mod/item_224.mesh.2109148288")
    #parser = MotListParser("./ch53_001_fac_basic.motlist.751")
    parser = MotListParser("ch20_000_com.motlist.751")
    #parser = MotListParser("./ch00_000_atk.motlist.751")
    #parser = MotListParser(mot_file)
    data = parser.read()
    #print(json.dumps(data, indent=4))

