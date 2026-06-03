This repository, Project-SprayLine, provides separate modules for the implementation of spraying lines at 輝創.
The folders include
1. Data: the collected data from the real production.
2. DataProcess: the services for data cleaning and preprocessing of collected data in CSV and Excel.
3. Database: the schema and services (with query, insert, and delete) for operating the database.
4. Omniverse: the services for interfacing Omniverse with the database
5. SprayLine: the ontology, knowledge, and rules
6. UserInterfaceDesign: the user interface accesses information from the database using web services.
7. Web-Services: the service for combining, synchronizing, classifying, and predicting.
   The functions support querying of current, past, and future states by batch and time.  

[20260601] updated
Add the five stages: sensing, identifying, inference, evaluation, and adaptation to the ontology 
1. The sensing stage has the end positions of a robot, flow and pressure of filters and nozzles, and an image of spraywidth.
2. The identification stage uses the sensing data to identify states of processing (normal, alarm, and fault), and states of robot, filter, and nozzle
3. The inference stage infers failure causes and responses of filter and quality (accepted, margin, and reject) based on identified states.
4. The evaluation stage evaluates spray width, filter, and nozzle (state and RUL), and quality based on the responses of causes.
5. The adaptation stage suggests component and process management with components and spray-path changed.
