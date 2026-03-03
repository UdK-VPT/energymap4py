# Python API for EnergyMap - energymap4py

The objective of EnergyMap is to develop, establish and evaluate a database-supported multiuser/multisource application including an online platform for the creation of a building-specific digital heat register for the building stock of the state of Berlin. This is intended to create a maximum transparent data basis for the current spatially differentiated energy status of the building stock of the federal capital, which will be freely available to all social actors of the energy transition in the future as a planning basis in various levels of detail.

The combination of calculated building-specific heat demand values based on publicly available data with real "crowd sourcing" consumption data from individual buildings or properties - collected via an online platform - is intended to deliver scientifically and socially valuable results.

More information about the EnergyMap Berlin project under https://energymap-berlin.de.

![EnergyMap Berlin](https://github.com/UdK-VPT/energymap4py/blob/main/img/EnergyMap_Berlin.png)

Development of energymap4py starts here. We aim to build a Python wrapper for the node.js API that is also used in the EnergyMap WebAPP.

The API is structured into two major parts: The "data_access" part refers to function that provide access to pre-computed data from the EnergyMap Database. The part "ai_model" provides access to the AI-prognosis model for detailed paramerization of our EnergyMap AI building model.

The following notebooks show possible applications for the Python API:

* OSM.ipynb: the user can select a set of buildings within a map using a polyline or polygon tool and obtain values for building parameters and precalculated building energy demands from the EnergymMap database.
* PrognosisModel.ipynb: First, a building is selected from the EnergyMap database. Then, various parameters (input variables) of the building are changed (climate year, U-values of facades, windows, and roof) to analyze their impact on its annual heating demand. 
