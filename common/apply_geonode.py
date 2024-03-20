import bpy

def apply_shellfur_geonode(obj):
    print(obj.name)
    if len(obj.material_slots) > 0 and obj.material_slots[0] is not None and obj.material_slots[0].material is not None:
        if "Fur_HeightMap" in obj.material_slots[0].material.keys():
            #if obj.material_slots[0].material["tVertexPositionMap__disclosure"] != "Assets\\default_tex\\null_black":
            if "null" not in obj.material_slots[0].material["Fur_HeightMap"].lower():
                shellfur_geonode = obj.modifiers.new("shellfur_geonode", 'NODES')
                bpy.context.view_layer.objects.active = obj
                #bpy.ops.object.modifier_move_up(modifier="shellfur_geonode")
                shellfur_geonode.node_group = bpy.data.node_groups["shellfur_geonode"]
                #vm_texture = obj.material_slots[0].material["tVertexPositionMap__disclosure"].split("\\")[-1] + ".tex"
                shellfur_geonode["Input_2"] = 5
                shellfur_geonode["Input_3"] = 0.01
                #ratio = sum([v.co[0]<0 for v in obj.data.vertices]) / len(obj.data.vertices)
                #if ratio > 0.9:
                    #vm_geonode["Input_4"] = True
            else:
                print("nope 3")
        else:
            print("nope 2")
    else:
        print("nope 1")

