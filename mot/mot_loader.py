import bpy
from mathutils import Quaternion, Vector
import logging
logger = logging.getLogger("dd2_import")

from .mot_parser import MotParser, MotListParser

def load_mot_data(mot_data, bones_baseposs, bones_baserots):
    mot_name = mot_data["name"]
    bone_infos = mot_data["bone_infos"]
    bones_actions = mot_data["bones_actions"]
    action = bpy.data.actions.new(mot_name)
    for bone_action in bones_actions:
        bone_name = bone_action["bone_name"]
        pos_keyframes = bone_action["pos"]
        rot_keyframes = bone_action["rot"]
        scl_keyframes = bone_action["scl"]
        
        loc_data_path = "pose.bones[\"" + bone_name + "\"].location"
        rot_data_path = "pose.bones[\"" + bone_name + "\"].rotation_quaternion"
        scl_data_path = "pose.bones[\"" + bone_name + "\"].scale"
        
        fcurve_loc_x = action.fcurves.new(data_path=loc_data_path, index=0)
        fcurve_loc_y = action.fcurves.new(data_path=loc_data_path, index=1)
        fcurve_loc_z = action.fcurves.new(data_path=loc_data_path, index=2)
        fcurve_rot_w = action.fcurves.new(data_path=rot_data_path, index=0)
        fcurve_rot_x = action.fcurves.new(data_path=rot_data_path, index=1)
        fcurve_rot_y = action.fcurves.new(data_path=rot_data_path, index=2)
        fcurve_rot_z = action.fcurves.new(data_path=rot_data_path, index=3)
        fcurve_scl_x = action.fcurves.new(data_path=scl_data_path, index=0)
        fcurve_scl_y = action.fcurves.new(data_path=scl_data_path, index=1)
        fcurve_scl_z = action.fcurves.new(data_path=scl_data_path, index=2)

        for time, values in pos_keyframes.items():
            #if time > mot_data["frame_count"]:
                #time = 0


            if bone_name in bones_baseposs:# and bone_action["pos_referential"] == "local":
                keyframe_pos = Vector([values[0], values[1], values[2]])
                keyframe_pos = keyframe_pos - Vector([bones_baseposs[bone_name][0], bones_baseposs[bone_name][1], bones_baseposs[bone_name][2]])
            else:
                keyframe_pos = Vector([values[0], values[1], values[2]])

            #keyframe_pos = Vector([values[0], values[1], values[2]])

            keyframe = fcurve_loc_x.keyframe_points.insert(frame=time,value=keyframe_pos[0])
            keyframe.handle_left_type = "VECTOR"
            keyframe.handle_right_type = "VECTOR"
            keyframe = fcurve_loc_y.keyframe_points.insert(frame=time,value=keyframe_pos[1])
            keyframe.handle_left_type = "VECTOR"
            keyframe.handle_right_type = "VECTOR"
            keyframe = fcurve_loc_z.keyframe_points.insert(frame=time,value=keyframe_pos[2])
            keyframe.handle_left_type = "VECTOR"
            keyframe.handle_right_type = "VECTOR"
        previous_quaternion = None
        for time, values in rot_keyframes.items():
            #if time > mot_data["frame_count"]:
                #time = 0
            #if bone_name in bones_baseposs and bone_action["rot_referential"] == "local":
            keyframe_rot = Quaternion([values[3], values[0], values[1], values[2]])
            if bone_name in bones_baserots:
                keyframe_rot.rotate(-bones_baserots[bone_name])
            #else:
                #keyframe_rot = Quaternion([values[3], values[0], values[1], values[2]])

            #keyframe_rot = Quaternion([values[3], values[0], values[1], values[2]])

            if previous_quaternion is not None:
                keyframe_rot.make_compatible(previous_quaternion)
            previous_quaternion = keyframe_rot.copy()
            keyframe = fcurve_rot_w.keyframe_points.insert(frame=time,value=keyframe_rot[0])
            keyframe.handle_left_type = "VECTOR"
            keyframe.handle_right_type = "VECTOR"
            keyframe = fcurve_rot_x.keyframe_points.insert(frame=time,value=keyframe_rot[1])
            keyframe.handle_left_type = "VECTOR"
            keyframe.handle_right_type = "VECTOR"
            keyframe = fcurve_rot_y.keyframe_points.insert(frame=time,value=keyframe_rot[2])
            keyframe.handle_left_type = "VECTOR"
            keyframe.handle_right_type = "VECTOR"
            keyframe = fcurve_rot_z.keyframe_points.insert(frame=time,value=keyframe_rot[3])
            keyframe.handle_left_type = "VECTOR"
            keyframe.handle_right_type = "VECTOR"
        for time, values in scl_keyframes.items():
            #if time > mot_data["frame_count"]:
                #time = 0
            keyframe = fcurve_scl_x.keyframe_points.insert(frame=time,value=values[0])
            keyframe.handle_left_type = "VECTOR"
            keyframe.handle_right_type = "VECTOR"
            keyframe = fcurve_scl_y.keyframe_points.insert(frame=time,value=values[1])
            keyframe.handle_left_type = "VECTOR"
            keyframe.handle_right_type = "VECTOR"
            keyframe = fcurve_scl_z.keyframe_points.insert(frame=time,value=values[2])
            keyframe.handle_left_type = "VECTOR"
            keyframe.handle_right_type = "VECTOR"

def load_motlist(filepath, armature):
    bones_baseposs = {}
    for bone in armature.bones:
        if bone.parent is not None:
            bones_baseposs[bone.name] = (bone.parent.matrix_local.inverted() @ bone.matrix_local).to_translation()
            #bones_baseposs[bone.name] = (bone.parent.matrix_local-bone.matrix_local).to_translation()
            #bones_baseposs[bone.name] = bone.matrix_local.to_translation()
    bones_baserots = {}
    for bone in armature.bones:
        if bone.parent is not None:
            inter_bone_rot_diff = bone.matrix.inverted().to_quaternion()
            bones_baserots[bone.name] = inter_bone_rot_diff.copy()
    parser = MotListParser(filepath)
    data = parser.read()
    for mot_data in data["mot_datas"]:
        logger.info("Loading mot " + mot_data["name"] + "... ")
        try:
            load_mot_data(mot_data, bones_baseposs, bones_baserots)
        except: 
            logger.error("Error while loading mot data" + mot_data["name"] + " of file " + str(filepath))
    
def load_mot(filepath, armature):
    bones_baseposs = {}
    for bone in armature.bones:
        if bone.parent is not None:
            bones_baseposs[bone.name] = (bone.parent.matrix_local.inverted() @ bone.matrix_local).to_translation()
            #bones_baseposs[bone.name] = (bone.parent.matrix_local.inverted() @ bone.matrix_local).inverted().to_translation()
            #bones_baseposs[bone.name] = (bone.parent.matrix_local-bone.matrix_local).to_translation()
            #bones_baseposs[bone.name] = bone.matrix_local.to_translation()
    bones_baserots = {}
    for bone in armature.bones:
        if bone.parent is not None:
            inter_bone_rot_diff = bone.matrix.inverted().to_quaternion()
            bones_baserots[bone.name] = inter_bone_rot_diff.copy()
    parser = MotParser(filepath)
    mot_data = parser.read()
    load_mot_data(mot_data, bones_baseposs, bones_baserots)
    
