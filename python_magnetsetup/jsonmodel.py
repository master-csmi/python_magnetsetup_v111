from typing import List, Optional

import sys
import os
import json
import yaml

from .utils import Merge

def create_params(gdata: tuple, method_data: List[str], debug: bool=False):
    """
    Return params_dict, the dictionnary of section \"Parameters\" for JSON file.
    """

    # TODO: length data are written in mm should be in SI instead
    unit_Length = 1.e-3
    unit_Area = 1.e-6

    (NHelices, NRings, NChannels, Nsections, R1, R2, Z1, Z2, Zmin, Zmax, Dh, Sh) = gdata
    
    # Tini, Aini for transient cases??
    params_data = { 'Parameters': []}

    # for cfpdes only
    if method_data[0] == "cfpdes" and method_data[3] == "thmagel" :
        params_data['Parameters'].append({"name":"bool_laplace", "value":"1"})
        params_data['Parameters'].append({"name":"bool_dilatation", "value":"1"})

    # TODO : initialization of parameters with cooling model

    params_data['Parameters'].append({"name":"Tinit", "value":293})
    params_data['Parameters'].append({"name":"h", "value":58222.1})
    params_data['Parameters'].append({"name":"Tw", "value":290.671})
    params_data['Parameters'].append({"name":"dTw", "value":12.74})
    
    # params per cooling channels
    # h%d, Tw%d, dTw%d, Dh%d, Sh%d, Zmin%d, Zmax%d :

    # TODO: length data are written in mm should be in SI instead
    for i in range(NHelices+1):
        params_data['Parameters'].append({"name":"h%d" % i, "value":58222.1})
        params_data['Parameters'].append({"name":"Tw%d" % i, "value":290.671})
        params_data['Parameters'].append({"name":"dTw%d" % i, "value":12.74})
        params_data['Parameters'].append({"name":"Zmin%d" % i, "value":Zmin[i] * unit_Length})
        params_data['Parameters'].append({"name":"Zmax%d" % i, "value":Zmax[i] * unit_Length})
        params_data['Parameters'].append({"name":"Sh%d" % i, "value":Sh[i] * unit_Length})
        params_data['Parameters'].append({"name":"Dh%d" % i, "value":Dh[i] * unit_Area})

    # init values for U (Axi specific)
    if method_data[2] == "Axi":
        for i in range(NHelices):
            for j in range(Nsections[i]):
                params_data['Parameters'].append({"name":"U_H%d_Cu%d" % (i+1, j+1), "value":"1"})
        for i in range(NHelices):
            for j in range(Nsections[i]):
                params_data['Parameters'].append({"name":"N_H%d_Cu%d" % (i+1, j+1), "value":Nsections[i]})
    
    # TODO: CG: U_H%d%
    # TODO: HDG: U_H%d% if no ibc

    return params_data


def create_materials(gdata: tuple, idata: Optional[List], confdata: dict, templates: dict, method_data: List[str], debug: bool = False):
    # TODO loop for Plateau (Axi specific)
    materials_dict = {}

    fconductor = templates["conductor"]
    finsulator = templates["insulator"]

    (NHelices, NRings, NChannels, Nsections, R1, R2, Z1, Z2, Zmin, Zmax, Dh, Sh) = gdata

    # Loop for Helix
    for i in range(NHelices):
        if method_data[2] == "3D":
            mdata = entry(fconductor, Merge({'name': "H%d" % (i+1), 'marker': "H%d_Cu" % (i+1)}, confdata["Helix"][i]["material"]) , debug)
            materials_dict["H%d" % (i+1)] = mdata["H%d" % (i+1)]

            if idata:
                for item in idata:
                    if item(0) == "Glue":
                        name = "Isolant%d" % (i+1)
                        mdata = entry(finsulator, Merge({'name': name, 'marker': "H%d_Isolant" % (i+1)}, confdata["Helix"][i]["insulator"]), debug)
                    else:
                        name = "Kaptons%d" % (i+1)
                        kapton_dict = { "name": "[\"Kapton%1%\"]", "index1": "0:%d" % item(1)}
                        mdata = entry(finsulator, Merge({'name': name, 'marker': kapton_dict}, confdata["Helix"][i]["insulator"]), debug)
                    materials_dict[name] = mdata[name]
        else:
            # section j==0:  treated as insulator in Axi
            mdata = entry(finsulator, Merge({'name': "H%d_Cu%d" % (i+1, 0)}, confdata["Helix"][i]["material"]), debug)
            materials_dict["H%d_Cu%d" % (i+1, 0)] = mdata["H%d_Cu%d" % (i+1, 0)]
        
            # load conductor template
            for j in range(1,Nsections[i]+1):
                mdata = entry(fconductor, Merge({'name': "H%d_Cu%d" % (i+1, j)}, confdata["Helix"][i]["material"]), debug)
                materials_dict["H%d_Cu%d" % (i+1, j)] = mdata["H%d_Cu%d" % (i+1, j)]

            # section j==Nsections+1:  treated as insulator in Axi
            mdata = entry(finsulator, Merge({'name': "H%d_Cu%d" % (i+1, Nsections[i]+1)}, confdata["Helix"][i]["material"]), debug)
            materials_dict["H%d_Cu%d" % (i+1, Nsections[i]+1)] = mdata["H%d_Cu%d" % (i+1, Nsections[i]+1)]

    # loop for Rings
    for i in range(NRings):
        if method_data[2] == "3D":
            mdata = entry(fconductor, Merge({'name': "R%d" % (i+1)}, confdata["Ring"][i]["material"]), debug)
        else:
            mdata = entry(finsulator, Merge({'name': "R%d" % (i+1)}, confdata["Ring"][i]["material"]), debug)
        materials_dict["R%d" % (i+1)] = mdata["R%d" % (i+1)]
        
    # Leads: 
    if method_data[2] == "3D" and confdata["Lead"]:
        mdata = entry(fconductor, Merge({'name': "iL1"}, confdata["Lead"][0]["material"]), debug)
        materials_dict["iL1"] = mdata["iL1"]

        mdata = entry(fconductor, Merge({'name': "oL2"}, confdata["Lead"][1]["material"]), debug)
        materials_dict["oL2"] = mdata["oL2"]

    return materials_dict


def create_bcs(boundary_meca: List, 
               boundary_maxwell: List,
               boundary_electric: List,
               gdata: tuple, confdata: dict, templates: dict, method_data: List[str], debug: bool = False):

    print("create_bcs from templates")
    electric_bcs_dir = { 'boundary_Electric_Dir': []} # name, value, vol
    electric_bcs_neu = { 'boundary_Electric_Neu': []} # name, value
    thermic_bcs_rob = { 'boundary_Therm_Robin': []} # name, expr1, expr2
    thermic_bcs_neu = { 'boundary_Therm_Neu': []} # name, value
    meca_bcs_dir = { 'boundary_Meca_Dir': []} # name, value
    maxwell_bcs_dir = { 'boundary_Maxwell_Dir': []} # name, value
    
    (NHelices, NRings, NChannels, Nsections, R1, R2, Z1, Z2, Zmin, Zmax, Dh, Sh) = gdata
    fcooling = templates["cooling"]
    
    for i in range(NChannels):
        # load insulator template for j==0
        mdata = entry(fcooling, {'i': i}, debug)
        thermic_bcs_rob['boundary_Therm_Robin'].append( Merge({"name": "Channel%d" % i}, mdata["Channel%d" % i]) )

    for bc in boundary_meca:
        meca_bcs_dir['boundary_Meca_Dir'].append({"name":bc, "value":"{0,0}"})

    for bc in boundary_maxwell:
        if method_data[2] == "3D":
            maxwell_bcs_dir['boundary_Maxwell_Dir'].append({"name":bc, "value":"{0,0}"})
        else:
            maxwell_bcs_dir['boundary_Maxwell_Dir'].append({"name":bc, "value":"0"})

    for bc in boundary_electric:
        electric_bcs_dir['boundary_Electric_Dir'].append({"name":bc[0], "value":bc[2]})
        

    if method_data[3] == "thelec":
        th_ = Merge(thermic_bcs_rob, thermic_bcs_neu)
        if method_data[2] == "Axi":
            return th_
        else:
            elec_ = Merge(electric_bcs_dir, electric_bcs_neu)
            return Merge(th_, elec_)
    elif method_data[3] == 'mag':
        return maxwell_bcs_dir
    elif method_data[3] == 'thmag':
        th_ = Merge(thermic_bcs_rob, thermic_bcs_neu)
        if method_data[2] == "Axi":
            return Merge(maxwell_bcs_dir, th_)
        else:
            elec_ = Merge(electric_bcs_dir, electric_bcs_neu)
            thelec_ = Merge(th_, elec_)
            return Merge(maxwell_bcs_dir, thelec_)
    else:
        th_ = Merge(thermic_bcs_rob, thermic_bcs_neu)
        elec_ = Merge(electric_bcs_dir, electric_bcs_neu)
        thelec_ = Merge(th_, elec_)
        thelecmeca_ = Merge(thelec_, meca_bcs_dir)
        return Merge(maxwell_bcs_dir, thelecmeca_)
            
    pass

def create_json(jsonfile: str, mdict: dict, mmat: dict, mpost: dict, templates: dict, method_data: List[str], debug: bool = False):
    """
    Create a json model file
    """

    print("create_json=", jsonfile)
    data = entry(templates["model"], mdict, debug)
    
    # material section
    if "Materials" in data:
        for key in mmat:
            data["Materials"][key] = mmat[key]
    else:
        data["Materials"] = mmat
    
    # postprocess
    if debug: print("flux")
    flux_data = mpost["flux"]
    add = data["PostProcess"]["heat"]["Measures"]["Statistics"]
    odata = entry(templates["flux"], flux_data, debug)
    for md in odata["Flux"]:
        data["PostProcess"]["heat"]["Measures"]["Statistics"][md] = odata["Flux"][md]
    
    if debug: print("meanT_H")
    meanT_data = mpost["meanT_H"] # { "meanT_H": [] }
    add = data["PostProcess"]["heat"]["Measures"]["Statistics"]
    odata = entry(templates["stats"][0], meanT_data, debug)
    for md in odata["Stats_T"]:
        data["PostProcess"]["heat"]["Measures"]["Statistics"][md] = odata["Stats_T"][md]

    if debug: print("power_H")
    section = "electric"
    if method_data[0] == "cfpdes" and method_data[2] == "Axi": section = "heat" 
    powerH_data = mpost["power_H"] # { "Power_H": [] }
    add = data["PostProcess"][section]["Measures"]["Statistics"]
    odata = entry(templates["stats"][1], powerH_data, debug)
    for md in odata["Stats_Power"]:
        data["PostProcess"]["heat"]["Measures"]["Statistics"][md] = odata["Stats_Power"][md]
    
    mdata = json.dumps(data, indent = 4)

    # print("corrected data:", re.sub(r'},\n					    	}\n', '}\n}\n', data))
    # data = re.sub(r'},\n					    	}\n', '}\n}\n', data)
    with open(jsonfile, "x") as out:
        out.write(mdata)
    pass

def entry(template: str, rdata: dict, debug: bool = False):
    import chevron
    import re
    
    if debug:
        print("entry/loading %s" % str(template), type(template))
        print("entry/rdata:", rdata)
    with open(template, "r") as f:
        jsonfile = chevron.render(f, rdata)
    jsonfile = jsonfile.replace("\'", "\"")
    if debug:
        print("entry/jsonfile:", jsonfile)
        print("corrected:", re.sub(r'},\n[\t ]+}\n', '}\n}\n', jsonfile))

    corrected = re.sub(r'},\n[\t ]+}\n', '}\n}\n', jsonfile)
    mdata = json.loads(corrected)
    if debug:
        print("entry/data (json):\n", mdata)
   
    return mdata
