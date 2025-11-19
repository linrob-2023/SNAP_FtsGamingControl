# ctrlX Data Layer Provider All Data

## Introduction

This Python app read the input from a USB cotrller and publisheds to the ctrlX Data Layer nodes representing different data types. 

## Function Description

When this app is started it connects to the ctrlX Data Layer and creates data nodes. 

The read data from the connected controller (Logitech Gamepad F710) throguh the connected USB dongle. The inputs are decoded and published into corresponding nodes on the datalayer.

## Implementation Description

__main.py__ starts the ctrlX Data Layer system and creates a mouse Objekt with the LibUSB Library to read the inputs. Furthermore, it establishes the IPC communication with the ctrlX Datalayer. 

The package __datalayerprovider__ contains the classes for data storage, configuration and ctrlX Data Layer handling.
the helper code __mouse_data__ contains the decodification of the read commands and the creation of the different node on the datalayer with the corresponding data types.

The snap was working on an ctrlX Core X7 with Ubuntu core20
This updated version is now working on ctrlX Core X7 with the firmware version ctrlX OS 2.2 (core22)

___

## License

SPDX-FileCopyrightText: Bosch Rexroth AG
SPDX-License-Identifier: MIT
