import struct
import math
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
    
    def addbytes(self, bytes_):
        self.data += bytes_
    
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

def write_tex(texture_data):
    
    # I don't want to deal with this nightmare
    if texture_data["width"] != texture_data["height"]:
        raise RuntimeError("Not a square texture")
    if texture_data["width"] & (texture_data["width"]-1) != 0:
        raise RuntimeError("Texture width isn't a power of 2")
    if texture_data["height"] & (texture_data["height"]-1) != 0:
        raise RuntimeError("Texture height isn't a power of 2")

    mip_count = 0
    mip_acc_size = 0
    mip_local_offsets = {}
    mip_side = texture_data["width"]
    while mip_side >= 8:
        mip_local_offsets[mip_side] = mip_acc_size
        mip_acc_size += mip_side*mip_side*4
        mip_side = int(round(mip_side/2))
        mip_count += 1
    mip_header_size = mip_count*16
    
    writer = Writer()
    writer.writeUInt(5784916)
    writer.writeUInt(760230703)
    writer.writeUShort(texture_data["width"])
    writer.writeUShort(texture_data["height"])
    writer.writeUShort(1) #?
    writer.writeUByte(1) # Image number
    writer.writeUByte(mip_header_size) # mip header size
    if texture_data["space"] == "sRGB":
        writer.writeUInt(29) # R8G8B8A8_UNORM_SRGB
    else:
        writer.writeUInt(28) # R8G8B8A8_UNORM
    writer.writeUInt(4294967295)
    writer.writeUInt(0)
    writer.writeUByte(0)
    writer.writeUByte(5) # flags probably
    writer.writeUShort(0)
    writer.writeUInt64(0)
        
    mip_offsets = {x[0]:writer.tell() + mip_header_size + x[1] for x in mip_local_offsets.items()}
    mip_count = 0
    for mip_side, mip_offset in mip_offsets.items():
        writer.writeUInt64(mip_offset)
        writer.writeUInt(mip_side*4)
        writer.writeUInt(mip_side*mip_side*4)
    
    for mip_count in range(len(mip_offsets)):
        #arr = (np.array(texture_data["data"]).reshape([-1,4])[::(2**(2*mip_count))] * 255.0).astype(np.uint8)
        arr = (np.array(texture_data["data"]).reshape([texture_data["width"], texture_data["height"], 4])[::(2**mip_count), ::(2**mip_count)] * 255.0).astype(np.uint8)

        writer.addbytes(arr.tobytes())
    
    return writer.data
