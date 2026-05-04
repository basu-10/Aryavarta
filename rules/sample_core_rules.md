# FIXED core mechanics of the game

## Layout of the game world

- 50*50 grid map with player or monster controlled forts and random monster camps.
- kill monster camps to capture monsters and add them to your army.
- attack and capture empty or monster controlled forts to gain fort.


## Newly registered users start with a castle and a cache of resources

- they need to get their first fort by capturing it.
- to capture they need to train troops and send them to attack the fort.
- forts can be of varying difficulty(indicated by increasing number of stars)
- new players should only try to hit only level 1 forts.


## Core Game Elements

### Fort and Castle: Similarities

- Both Fort and Castle appear with a command centre prebuilt. There are 10 building slots per fort/castle. Command centre takes up 1 slot. User will fill up the rest 9 slots.
- The command centre is the heart of the mechanics - if its in broken state(can be repaired), troops cant be sent out.
  

### Fort and Castle: Differences

- Fort is acquired by players and can be lost.
- Castle is never lost.
- Castles can't be attacked.

### Fort and Castle: Buildings available

- canon, archer tower (these are not troops and cant be deployed in battle, they are just part of the fort defenses)
- mine, farm, lumber mill, merchant


## Attack 

- players cant attack a fort if the command centre is damaged, but they can repair it and then attack. This is why command centre is the deafult building in forts and castles and cant be removed.
- attack is turn based, each turn is 1 tick in game time.
- attacking a fort can also damage the buildings in the fort, which can be repaired by the owner.
- attacking a fort damages the command centre and if the atacker wins, he(new owner) needs to repair it before sending out troops from the captured fort. 
- a failed attack can also damage the command centre and other buildings, depending on the strength of the attack, which can be repaired by the old owner.

## Troops available

### Human troops (can be trained in forts and castles)

Melee, Ranged
archer, longbowmen
barbarian, hussar

### Monster troops (can be captured from monster camps or by attacking forts)

Melee, Ranged
Troll, Wraith
Goblin Brute, Harpy
Minotaur, Basilisk
Gargoyle, Manticore
Hydra, Siren
Behemoth, Chimera
Leviathan, Phoenix
Colossus, Thunderbird
Abyssal Titan, Void Drake
Demon, Pegasus
