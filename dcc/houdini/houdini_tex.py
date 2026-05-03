import hou
import os
import re

def create_karma_material_from_selection():
    selection = hou.selectedNodes()
    if not selection:
        hou.ui.displayMessage("Please SELECT 'Karma Material Builder' node first.")
        return

    # inside the selected node
    net = selection[0]
    
    # USER INPUT 
    texture_path = hou.ui.selectFile(
        title="Select ONE texture from your UDIM sequence",
        file_type=hou.fileType.Image,
        chooser_mode=hou.fileChooserMode.Read
    )

    if not texture_path or texture_path == "":
        return

    directory = os.path.dirname(texture_path)
    try:
        files = os.listdir(directory)
    except OSError:
        hou.ui.displayMessage("Could not read directory.")
        return

    # CORE NODES
    # Find or Create Shader
    shader = net.node("mtlxstandard_surface")
    if not shader:
        # check children 
        for child in net.children():
            if child.type().name() == "mtlxstandard_surface":
                shader = child
                break
    if not shader:
        shader = net.createNode("mtlxstandard_surface", "standard_surface")

    # Find or Create Collector (Material Output)
    material_out = net.node("Material_Outputs_and_AOVs")
    if not material_out:
        for child in net.children():
            # Check for various valid output types
            if child.type().name() in ["mtlxsurfacematerial", "collect", "usdmaterial"]:
                material_out = child
                break
    
    if not material_out:
        try:
            material_out = net.createNode("mtlxsurfacematerial", "Material_Outputs_and_AOVs")
            material_out.setInput(0, shader, 0)
        except:
            # Fallback
            material_out = net.createNode("collect", "Material_Output")
            material_out.setInput(0, shader, 0)

    # KEYWORD MAPPING 
    texture_map = {
        'base_color': ['diffuse', 'albedo', 'basecolor', 'diff', 'color', 'base'],
        'coat': ['clearcoat', 'coat'],
        'coat_roughness': ['clearcoat_roughness', 'coat_rough', 'gloss', 'clearcoat_gloss'],
        'transmission': ['transmission', 'trans'],
        'coat_IOR': ['clearcoat_ior', 'coat_ior', 'ior'],
        'specular_roughness': ['roughness', 'rough', 'rgh'],
        'specular': ['specular', 'spec'],
        'anisotropy': ['ani', 'anisotropy'],
        'metalness': ['metallic', 'metal', 'mtl'],
        'emission_color': ['emission', 'emissive', 'emit'],
        'subsurface_color': ['sss', 'subsurface'],
        'displacement': ['displacement', 'disp', 'height', 'heightmap', 'bump'],
        'sheen': ['sheen']
    }

    assigned_inputs = []
    created_nodes = [] 
    
    # UDIM Regex
    udim_pattern = re.compile(r"[._](1[0-9]{3})[._]")

    # ASSIGN TEXTURES
    for f in files:
        if f.startswith('.'): continue

        lower_name = f.lower()
        full_path = os.path.join(directory, f)
        
        # UDIM Replacement
        match = udim_pattern.search(f)
        if match:
            udim_num = match.group(1)
            full_path = full_path.replace(udim_num, "<UDIM>")

        # get input
        target_input = None
        for input_name, keywords in texture_map.items():
            if any(k in lower_name for k in keywords):
                target_input = input_name
                break
        
        if target_input and target_input not in assigned_inputs:
            
            # img node
            img = net.createNode("mtlximage", f"tex_{target_input}")
            img.parm("file").set(full_path)
            created_nodes.append(img)
            
            #WIRING 
            
            # Displacement
            if target_input == 'displacement':
                img.parm("signature").set("float")
                
                # check 4 existing disp
                disp = net.node("mtlxdisplacement")
                if not disp:
                    disp = net.createNode("mtlxdisplacement", "displacement_setup")
                
                disp.setInput(0, img, 0)
                disp.parm("scale").set(0.01)
                
                # wire 2 collector
                if material_out.type().name() == "Material_Outputs_and_AOVs":
                    material_out.setInput(1, disp, 0)
                elif material_out.type().name() == "usdmaterial":
                     material_out.setInput(1, disp, 0)
                
                created_nodes.append(disp)

            # Normal
            elif target_input == 'normal':
                img.parm("signature").set("vector3")
                
                nrm = net.createNode("mtlxnormalmap", "normal_map_setup")
                nrm.setInput(0, img, 0)
                
                # wire to shader 
                try:
                    idx = shader.inputIndex(target_input)
                    if idx == -1: idx = 40 
                    shader.setInput(idx, nrm, 0)
                except:
                    pass
                
                created_nodes.append(nrm)

            # Roughness / Metalness
            elif target_input in ['specular',  'metalness', 'specular_roughness']:
                img.parm("signature").set("float")
                try:
                    shader.setInput(shader.inputIndex(target_input), img, 0)
                except:
                    pass

            # Color / Emission
            else:
                img.parm("signature").set("color3")
                try:
                    shader.setInput(shader.inputIndex(target_input), img, 0)
                except:
                    pass
            
            assigned_inputs.append(target_input)

    net.layoutChildren(created_nodes)
    print("Texture setup complete on selected node.")

create_karma_material_from_selection()