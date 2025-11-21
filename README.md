# Python API for EnergyMap - energymap4py
Development of energymap4py starts here. We aim to build a Python wrapper for the node.js API that is also used in the EnergyMap WebAPP.

The API is structured into two major parts: The "data_access" part refers to function that provide access to pre-computed data from the EnergyMap Database. The part "ai_model" provides access to the AI-prognosis model for detailed paramerization of our EnergyMap AI building model.

The following notebooks show possible applications for the Python API:

* OSM.ipynb: the user can select a set of buildings within a map using a polyline or polygon tool and obtain values for building parameters and precalculated building energy demands from the EnergymMap database.
* PrognosisModel.ipynb: First, a building is selected from the EnergyMap database. Then, various parameters (input variables) of the building are changed (climate year, U-values of facades, windows, and roof) to analyze their impact on its annual heating demand. 
