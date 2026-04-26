# Asset IDs used by this project

### Troop / unit types

#### Human-only unit types

Defined in config.py under UNIT_STATS:

##### Melee Troops

Barbarian
Hussar

##### Ranged Troops

Archer
Longbowman

#### Monster-only unit types

Troll
Wraith

### Building types

Defined in config.py under BUILDING_PRODUCTION_RATE, BUILDING_BUILD_TIME, and BUILDING_BUILD_COST:

#### Resource-generating buildings

Farm
Lumber Mill
Merchant
Mine

##### Military buildings

Garrison
Stable

#### Defensive buildings

Cannon
Archer Tower

#### Default building type for all castles and forts:
(Auto Generated with fort(doesnt consume any resources or slot). User doesnt need to build it. It can however get detroyed and can be repaired to resume using it.)
Command Centre

### Map/location entity types

Used in the world model and DB code:

castle
fort
monster_camp


### Used by world_seeder.py for monster garrisons:

Troll
Wraith
