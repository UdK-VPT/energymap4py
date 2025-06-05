"""
ai_model.py includes functions to get a response from the EnergyMap Berlin ModelServer
which serves an AI prognosis model get heat consumption values for single buildings.
"""

from .data_access import get_response

model_api_url = 'https://energymap-berlin.de/model'

parameters = {
        "heated_area": {'name': 'heated_area', 'default': None},
        "year_of_construction": {'name': 'const_year', 'default': None},
        "refurbishment_variant": {'name': 'refurb_var', 'default': None},
        "building_type": {'name': 'bldg_type', 'default': 'GMH'},
        "climate_year": {'name': 'clim_year', 'default': None},
        "climate_scenario": {'name': 'clim_scen', 'default': None},
        "outwalls_window_uvalue": {'name': 'wall_win_uval', 'default': None},
        "outwalls_window_ratio": {'name': 'wall_win_rat', 'default': None},
        "outwalls_uvalue": {'name': 'wall_uval', 'default': None},
        "ground_shell_uvalue": {'name': 'ground_uval', 'default': None},
        "pitched_roof_uvalue": {'name': 'roof_uval', 'default': None},
        "pitched_roof_window_uvalue": {'name': 'roof_win_uval', 'default': None},
        "pitched_roof_window_ratio": {'name': 'roof_win_rat', 'default': None},
        "top_ceiling_window_uvalue": {'name': 'ceil_win_uval', 'default': None},
        "top_ceiling_uvalue": {'name': 'ceil_uval', 'default': None},
        "heater_efficiency": {'name': 'plant_eff', 'default': 0.93},
        "domestic_hot_water_demand": {'name': 'hwd', 'default': 25}
    }

def predict(uuid, **kwargs):
    url = f"{model_api_url}/nn?uuid={uuid}"
    for key in parameters:
        if key in kwargs:
            url += f"&{parameters[key]['name']}={kwargs[key]}"
        elif parameters[key]['default']:
            url += f"&{parameters[key]['name']}={parameters[key]['default']}"
    print(url)
    return get_response(url)
    