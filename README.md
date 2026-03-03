# EnergyMap Berlin project

The objective of EnergyMap is to develop, establish and evaluate a database-supported multiuser/multisource application including an online platform for the creation of a building-specific digital heat register for the building stock of the state of Berlin. This is intended to create a maximum transparent data basis for the current spatially differentiated energy status of the building stock of the federal capital, which will be freely available to all social actors of the energy transition in the future as a planning basis in various levels of detail.

The combination of calculated building-specific heat demand values based on publicly available data with real "crowd sourcing" consumption data from individual buildings or properties - collected via an online platform - is intended to deliver scientifically and socially valuable results.

More information about the EnergyMap Berlin project under https://energymap-berlin.de.

The easiest way to access EnergyMap Berlin's building and energy demand data is to use the web app via the URL https://energymap-berlin.de/map:  

![EnergyMap Berlin](https://github.com/UdK-VPT/energymap4py/blob/main/img/EnergyMap_Berlin.png)

The figure shows a city district marked in the web app consisting of 72 buildings for which a range of information, such as the total heated area or the total annual heating demand of all selected buildings, was determined for the standard scenario.  

# Python API for EnergyMap - energymap4py

The Python API enables access to the EnergyMap Berlin database server and the AI-based prognosis model for the heating demand predictions independent of the web app. For this purpose, we built a Python wrapper for the node.js API that is also used in the EnergyMap web app.

The API is structured into two major parts: The "data_access" part refers to function that provide access to pre-computed data from the EnergyMap Database. The “ai_model” part provides access to the AI-based prognosis model for the building specific annual heating energy demand. Here, various input parameters (features) can be set for every building in Berlin selected via its UUID (universally unique identifier), such as the climate year or the U-values of its opaque facade, windows, or roof. 

The following notebooks show twi different possible applications for the Python API:

* OSM.ipynb: the user can select a set of buildings within a map using a polyline or polygon tool and obtain values for building parameters and precalculated building energy demands from the EnergymMap database.

![EnergyMap Berlin Python Interface](https://github.com/UdK-VPT/energymap4py/blob/main/img/EnergyMap_Berlin_PythonInterface.png)

* PrognosisModel.ipynb: First, a building is selected from the EnergyMap database. Then, various parameters (input variables) of the building are changed (climate year, U-values of facades, windows, and roof) to analyze their impact on its annual heating demand. 

![EnergyMap Berlin Prognosis Model](https://github.com/UdK-VPT/energymap4py/blob/main/img/EnergyMap_Berlin_prognosis_model.png)
