# MIT License
#
# Copyright (c) 2021 Bosch Rexroth AG
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# This script was adapted from the sample projects in SDK V1.12.0 - RM21.11

import time
import typing
import threading
from threading import Lock

import flatbuffers
from comm.datalayer import Metadata, NodeClass, AllowedOperations, Reference

import ctrlxdatalayer
from ctrlxdatalayer.provider import Provider
from ctrlxdatalayer.client import Client
from ctrlxdatalayer.provider_node import ProviderNodeCallbacks, NodeCallback
from ctrlxdatalayer.variant import Result, Variant, VariantType

import sys
import usb.core
import usb.util
import usb.backend.libusb1

# ==========================================================
# LOGGING (thread-safe)
# ==========================================================
# Console only
# Python logging is thread-safe; we only format and route messages to console.

import logging

logger = logging.getLogger("joystick_provider")
logger.setLevel(logging.DEBUG)  # Global logger level

if not logger.handlers:
    # Console log format includes:
    # - timestamp
    # - log level
    # - process id
    # - thread name (important for multi-thread debugging)
    # - module name + line number
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | pid=%(process)d | %(threadName)s | %(module)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    ch = logging.StreamHandler()     # Console output
    ch.setLevel(logging.INFO)        # Change to DEBUG if you want to see everything
    ch.setFormatter(formatter)
    logger.addHandler(ch)



type_address_string = "types/datalayer/string"
type_address_bool8 = "types/datalayer/bool8"
type_address_float = "types/datalayer/float32"


class MouseData:

    def __init__(self, provider: Provider, client: Client,  addressRoot: str):

        # Store Provider + Client handles (Provider exposes nodes, Client could be used if needed)
        self.provider = provider
        self.client = client
        # Root path under which all variables will be registered
        self.addressRoot = addressRoot + "/"
        # Reader thread handle (USB read loop runs here to avoid blocking Data Layer callbacks)
        self._reader_thread = None

        # -----------------------------
        # Data Layer variables (Variants)
        # -----------------------------

        # Connection state of the USB controller
        self.controller_connected = Variant()
        self.controller_connected.set_bool8(False)
        data = self.create_metadata(type_address_bool8, "", "Controller connected", False)
        self.controller_connected_metadata = Variant()
        self.controller_connected_metadata.set_flatbuffers(data)
        
        # Raw/full byte array as string for debugging/inspection
        self.full_data = Variant()
        self.full_data.set_string("No data available")
        data = self.create_metadata(type_address_string, "", "Full controller data", False)
        self.full_data_metadata = Variant()
        self.full_data_metadata.set_flatbuffers(data)

        # Buttons / triggers (boolean flags)
        self.left_button = Variant()
        self.left_button.set_bool8(False)
        data = self.create_metadata(type_address_bool8, "", "Left trigger LB pressed down", False)
        self.left_button_metadata = Variant()
        self.left_button_metadata.set_flatbuffers(data)

        self.right_button = Variant()
        self.right_button.set_bool8(False)
        data = self.create_metadata(type_address_bool8, "", "Right trigger RB pressed down", False)
        self.right_button_metadata = Variant()
        self.right_button_metadata.set_flatbuffers(data)

        self.left_button_bottom = Variant()
        self.left_button_bottom.set_bool8(False)
        data = self.create_metadata(type_address_bool8, "", "Left trigger LT pressed down", False)
        self.left_button_bottom_metadata = Variant()
        self.left_button_bottom_metadata.set_flatbuffers(data)

        self.right_button_bottom = Variant()
        self.right_button_bottom.set_bool8(False)
        data = self.create_metadata(type_address_bool8, "", "Right trigger RT pressed down", False)
        self.right_button_bottom_metadata = Variant()
        self.right_button_bottom_metadata.set_flatbuffers(data)

        self.b_button = Variant()
        self.b_button.set_bool8(False)
        data = self.create_metadata(type_address_bool8, "", "B button pressed down", False)
        self.b_button_metadata = Variant()
        self.b_button_metadata.set_flatbuffers(data)

        self.y_button = Variant()
        self.y_button.set_bool8(False)
        data = self.create_metadata(type_address_bool8, "", "Y button pressed down", False)
        self.y_button_metadata = Variant()
        self.y_button_metadata.set_flatbuffers(data)

        self.x_button = Variant()
        self.x_button.set_bool8(False)
        data = self.create_metadata(type_address_bool8, "", "X button pressed down", False)
        self.x_button_metadata = Variant()
        self.x_button_metadata.set_flatbuffers(data)

        self.a_button = Variant()
        self.a_button.set_bool8(False)
        data = self.create_metadata(type_address_bool8, "", "A button pressed down", False)
        self.a_button_metadata = Variant()
        self.a_button_metadata.set_flatbuffers(data)

        self.up_cross_button = Variant()
        self.up_cross_button.set_bool8(False)
        data = self.create_metadata(type_address_bool8, "", "Up cross button pressed down", False) 
        self.up_cross_button_metadata = Variant()
        self.up_cross_button_metadata.set_flatbuffers(data)

        self.down_cross_button = Variant()
        self.down_cross_button.set_bool8(False)
        data = self.create_metadata(type_address_bool8, "", "Down cross button pressed down", False)
        self.down_cross_button_metadata = Variant()
        self.down_cross_button_metadata.set_flatbuffers(data)

        self.left_cross_button = Variant()
        self.left_cross_button.set_bool8(False)
        data = self.create_metadata(type_address_bool8, "", "Left cross button pressed down", False)
        self.left_cross_button_metadata = Variant()
        self.left_cross_button_metadata.set_flatbuffers(data)

        self.right_cross_button = Variant()
        self.right_cross_button.set_bool8(False)
        data = self.create_metadata(type_address_bool8, "", "Right cross button pressed down", False)
        self.right_cross_button_metadata = Variant()
        self.right_cross_button_metadata.set_flatbuffers(data)
        
        # Joystick axes (float values, scaled in range roughly [-1..+1])
        self.l_joystick_x = Variant()
        self.l_joystick_x.set_float32(0)
        data = self.create_metadata(type_address_float, "", "Left Joystick X: ", False)
        self.l_joystick_x_metadata = Variant()
        self.l_joystick_x_metadata.set_flatbuffers(data)

        self.l_joystick_y = Variant()
        self.l_joystick_y.set_float32(0)
        data = self.create_metadata(type_address_float, "", "Left Joystick Y:", False)
        self.l_joystick_y_metadata = Variant()
        self.l_joystick_y_metadata.set_flatbuffers(data)

        self.r_joystick_x = Variant()
        self.r_joystick_x.set_float32(0)
        data = self.create_metadata(type_address_float, "", "Right Joystick X: ", False)
        self.r_joystick_x_metadata = Variant()
        self.r_joystick_x_metadata.set_flatbuffers(data)

        self.r_joystick_y = Variant()
        self.r_joystick_y.set_float32(0)
        data = self.create_metadata(type_address_float, "", "Right Joystick Y:", False)
        self.r_joystick_y_metadata = Variant()
        self.r_joystick_y_metadata.set_flatbuffers(data)

        # -----------------------------
        # Provider node callbacks
        # -----------------------------
        # These callbacks handle read/metadata requests from Data Layer clients

        self.cbs = ProviderNodeCallbacks(
            self.__on_create,
            self.__on_remove,
            self.__on_browse,
            self.__on_read,
            self.__on_write,
            self.__on_metadata
        )
        # One ProviderNode instance is reused for all addresses, the callbacks route by suffix
        self.providerNode = ctrlxdatalayer.provider_node.ProviderNode(self.cbs)
    def start_reading_threaded(self):
         #Start the USB reading loop in a dedicated daemon thread (non-blocking for Data Layer)
        if self._reader_thread is None or not self._reader_thread.is_alive():
            self._reader_thread = threading.Thread(target=self.start_reading, daemon=True)
            self._reader_thread.start()
    def _set_safe_state(self, msg: str = "disconnected"):

        #Put all exposed Data Layer values into a defined safe state.
        #This is used on startup and on USB disconnect/errors.

        self.controller_connected.set_bool8(False)
        #self.full_data.set_string(msg)

        # Reset all buttons
        self.left_button.set_bool8(False)
        self.right_button.set_bool8(False)
        self.left_button_bottom.set_bool8(False)
        self.right_button_bottom.set_bool8(False)

        self.a_button.set_bool8(False)
        self.b_button.set_bool8(False)
        self.x_button.set_bool8(False)
        self.y_button.set_bool8(False)

        self.up_cross_button.set_bool8(False)
        self.down_cross_button.set_bool8(False)
        self.left_cross_button.set_bool8(False)
        self.right_cross_button.set_bool8(False)

        # Reset joystick axes
        self.l_joystick_x.set_float32(0.0)
        self.l_joystick_y.set_float32(0.0)
        self.r_joystick_x.set_float32(0.0)
        self.r_joystick_y.set_float32(0.0)
    def _cleanup_usb(self, dev, interface):
        #Release USB interface and dispose resources safely (ignore errors).
        try:
            usb.util.release_interface(dev, interface)
        except:
            logger.debug("release_interface failed", exc_info=True)
        try:
            usb.util.dispose_resources(dev)
        except:
            logger.debug("dispose_resources failed", exc_info=True)
    # Thanks to https://www.orangecoat.com/how-to/read-and-decode-data-from-your-mouse-using-this-pyusb-hack
    def start_reading(self):

        #####   Main USB reading loop   #####
        #   Connect to the USB device via libusb backend
        #   Repeatedly read reports
        #   Decode report bytes into Data Layer variables
        #   Handle disconnect/reconnect without blocking the Data Layer server thread
        #####################################

        # Initialize to a known safe state
        self._set_safe_state("starting...")
        
        # Thanks to https://github.com/pyusb/pyusb/pull/29#issue-21312683
        # Reference the libusb library explicitly to get access to hardware
        backend = usb.backend.libusb1.get_backend(
            find_library=lambda x: "/snap/sdk-py-provider-alldata/current/usr/lib/x86_64-linux-gnu/libusb-1.0.so.0")
      #for core20: find_library=lambda x: "/snap/sdk-py-provider-alldata/current/lib/aarch64-linux-gnu/libusb-1.0.so.0")
        #Full-path: libusb-1.0.so.0.3.0
        
        if backend is None:
            # No backend => cannot access USB hardware
            self._set_safe_state("libusb backend not found")
            logger.error("libusb backend not found")
            return
            
        interface = 0
        dev = None
        endpoint = None

        # Initial connect loop (legacy behavior): waits until device is present
        while dev is None:
            dev = usb.core.find(idVendor=0x046d, idProduct=0xc21f, backend=backend)
            if not dev:
                dev = usb.core.find(idVendor=0x046d, idProduct=0xc219, backend=backend)
            if not dev:
                # Device not found -> wait before retry
                logger.error("Device not found")
                time.sleep(5)

        # Select the interrupt endpoint used for reading reports
        try:
            endpoint = dev[0].interfaces()[0].endpoints()[0]
        except Exception:
            logger.error("USB initialization failed", exc_info=True)
        
        # Reset device and detach kernel driver if it currently owns the interface
        try:
            dev.reset()
        except:
            logger.error("Reset failed")

        try:
            if dev.is_kernel_driver_active(interface):
                try:
                    dev.detach_kernel_driver(interface)
                except:
                    logger.warning("Failed to detach kernel driver (initial)")
        except:
            logger.error("Kernel driver check failed")
        # Claim interface so we can read data
        try:
            usb.util.claim_interface(dev, interface)
        except:
            logger.error("USB interface claim failed (initial)")

        # Mark as connected for Data Layer clients
        self.controller_connected.set_bool8(True)

        # Endless loop to read in the data from the usb device more than once
        while True:

            # -------------------------------------------------
            # If device handle is None: attempt fast reconnect
            # -------------------------------------------------
            if dev is None:
                dev = usb.core.find(idVendor=0x046d, idProduct=0xc21f, backend=backend)
                if not dev:
                    dev = usb.core.find(idVendor=0x046d, idProduct=0xc219, backend=backend)

                if dev is None:
                    # No device present -> sleep shortly and retry (non-blocking overall)
                    logger.info("USB disconnected")
                    time.sleep(0.2)
                    continue

                # Device found again -> reset and re-claim interface
                try:
                    dev.reset()
                except:
                    logger.warning("Reset failed")
                
                
                # Rebuild endpoint reference (device object changed)
                try:
                    endpoint = dev[0].interfaces()[0].endpoints()[0]
                except:
                    # If we cannot access endpoint, go safe and retry
                    logger.error("Endpoint access failed after reconnect")
                    self._set_safe_state("endpoint error")
                    self._cleanup_usb(dev, interface)
                    dev = None
                    endpoint = None
                    time.sleep(0.2)
                    continue
                
                # Detach kernel driver if necessary
                try:
                    if dev.is_kernel_driver_active(interface):
                        try:
                            dev.detach_kernel_driver(interface)
                        except:
                            logger.warning("Failed to detach kernel driver (reconnect)")
                except:
                    logger.warning("is_kernel_driver_active check failed (reconnect)")

                
                # Claim interface again
                try:
                    usb.util.claim_interface(dev, interface)
                except:
                    logger.error("USB claim failed after reconnect")
                    self._set_safe_state("claim error")
                    self._cleanup_usb(dev, interface)
                    dev = None
                    endpoint = None
                    time.sleep(0.2)
                    continue

                # Reconnected
                self.controller_connected.set_bool8(True)
                #self.full_data.set_string("connected")
                continue
            try:
                # Read one report from the USB interrupt endpoint (timeout in ms)
                data = dev.read(endpoint.bEndpointAddress,endpoint.wMaxPacketSize, 500)

                # Store raw data for debugging / visualization
                #self.full_data.set_string(str(data))
                

                # Decoding of the mouse data array is specific to the mouse you use
                # To decode it yourself, just look at the data array and how the data changes if you e.g., move the mouse or press a button
                #Unable to use Case or match structure, due to older version of Python
                

                # -------------------------------------------------
                # Reset all button states before decoding current report
                # -------------------------------------------------
                self.left_button.set_bool8(False)
                self.right_button.set_bool8(False)
                self.right_button_bottom.set_bool8(False)
                self.left_button_bottom.set_bool8(False)
                self.b_button.set_bool8(False)
                self.y_button.set_bool8(False)
                self.x_button.set_bool8(False)
                self.a_button.set_bool8(False)
                self.up_cross_button.set_bool8(False)
                self.down_cross_button.set_bool8(False)
                self.left_cross_button.set_bool8(False)
                self.right_cross_button.set_bool8(False)

                # -------------------------------------------------
                # Decode button bits (device-specific mapping)
                # -------------------------------------------------
                clicked_button = int(data[3])
                if(clicked_button & 1):
                    self.left_button.set_bool8(True) 
                if(clicked_button & 2):
                    self.right_button.set_bool8(True)   
                if(clicked_button & 32):
                    self.b_button.set_bool8(True)
                if(clicked_button & 128):
                    self.y_button.set_bool8(True)  
                if(clicked_button & 64):
                    self.x_button.set_bool8(True)
                if(clicked_button & 16):
                    self.a_button.set_bool8(True)
                if (int(data[4]) & 31):
                    self.left_button_bottom.set_bool8(True)
                if (int(data[5]) & 29):
                    self.right_button_bottom.set_bool8(True)

                # D-pad (cross) bits
                clicked_cross_button = int(data[2])
                if (clicked_cross_button & 1):
                    self.up_cross_button.set_bool8(True)
                if (clicked_cross_button & 2):
                    self.down_cross_button.set_bool8(True)
                if (clicked_cross_button & 4):
                    self.left_cross_button.set_bool8(True)
                if (clicked_cross_button & 8):
                    self.right_cross_button.set_bool8(True)

                # -------------------------------------------------
                # Decode joysticks (scaled values, device-specific indices)
                # -------------------------------------------------
                l_joystick_x_scaled = (int(data[6])/128)-1
                #l_joystick_x_scaled = int(data[6])
                self.l_joystick_x.set_float32(float(l_joystick_x_scaled))

                l_joystick_y_scaled = (int(data[8])/128)-1
                #l_joystick_y_scaled = int(data[8])
                self.l_joystick_y.set_float32(float(l_joystick_y_scaled))

                r_joystick_x_scaled = (int(data[10])/128)-1 #Check Array Index for B Button
                #l_joystick_x_scaled = int(data[6])
                self.r_joystick_x.set_float32(float(r_joystick_x_scaled))

                r_joystick_y_scaled = (int(data[12])/128)-1 #Check Array Index for B Button
                #l_joystick_y_scaled = int(data[8])
                self.r_joystick_y.set_float32(float(r_joystick_y_scaled))



            except usb.core.USBError as e:

                # Normal timeout: no report received within timeout; keep looping
                if e.errno == 110:  # ETIMEDOUT
                    continue

                # Disconnect or I/O error: go safe, cleanup, and trigger reconnect logic
                if e.errno in (19, 5):  # ENODEV, EIO
                    logger.warning("USB disconnected")
                    self._set_safe_state("disconnected")
                    self._cleanup_usb(dev, interface)
                    dev = None
                    endpoint = None
                    time.sleep(0.2)
                    continue

                # Any other USBError: keep process alive, go safe and retry
                logger.error("USB Error")
                self._set_safe_state("usb error")
                self._cleanup_usb(dev, interface)
                dev = None
                endpoint = None
                time.sleep(0.2)
                continue

            
            except Exception:
                # Catch-all to prevent the provider process from crashing
                logger.error("Unexpected exception", exc_info=True)
                self._set_safe_state("usb error process crashed")
                self._cleanup_usb(dev, interface)
                dev = None
                endpoint = None
                time.sleep(0.2)
                continue

    def register_nodes(self):
        
        self.provider.register_node(
            self.addressRoot + "controller-connected", self.providerNode)
        self.provider.register_node(
            self.addressRoot + "full-data", self.providerNode)
        self.provider.register_node(
            self.addressRoot + "left-button", self.providerNode)
        self.provider.register_node(
            self.addressRoot + "right-button", self.providerNode)
        self.provider.register_node(
            self.addressRoot + "left-button-bottom", self.providerNode)
        self.provider.register_node(
            self.addressRoot + "right-button-bottom", self.providerNode)
        self.provider.register_node(
            self.addressRoot + "b-button", self.providerNode)
        self.provider.register_node(
            self.addressRoot + "y-button", self.providerNode)
        self.provider.register_node(
            self.addressRoot + "x-button", self.providerNode)
        self.provider.register_node(
            self.addressRoot + "a-button", self.providerNode)
        self.provider.register_node(
            self.addressRoot + "up-cross-button", self.providerNode)
        self.provider.register_node(
            self.addressRoot + "down-cross-button", self.providerNode)
        self.provider.register_node(
            self.addressRoot + "left-cross-button", self.providerNode)
        self.provider.register_node(
            self.addressRoot + "right-cross-button", self.providerNode)
        self.provider.register_node(
            self.addressRoot + "Left-Joystick-X", self.providerNode)
        self.provider.register_node(
            self.addressRoot + "Left-Joystick-Y", self.providerNode)
        self.provider.register_node(
            self.addressRoot + "Right-Joystick-X", self.providerNode)
        self.provider.register_node(
            self.addressRoot + "Right-Joystick-Y", self.providerNode)

        #print("INFO: MouseData Provider Nodes registered", flush=True)

    def create_metadata(self, typeAddress: str, unit: str, description: str, allowWrite : bool):

        # Create `FlatBufferBuilder`instance. Initial Size 1024 bytes (grows automatically if needed)
        builder = flatbuffers.Builder(1024)

        # Serialize AllowedOperations data
        AllowedOperations.AllowedOperationsStart(builder)
        AllowedOperations.AllowedOperationsAddRead(builder, True)
        AllowedOperations.AllowedOperationsAddWrite(builder, allowWrite)
        AllowedOperations.AllowedOperationsAddCreate(builder, False)
        AllowedOperations.AllowedOperationsAddDelete(builder, False)
        operations = AllowedOperations.AllowedOperationsEnd(builder)

        # Metadata description strings
        descriptionBuilderString = builder.CreateString(description)
        urlBuilderString = builder.CreateString("tbd")
        unitString = builder.CreateString(unit)

        # Store string parameter into builder
        readTypeBuilderString = builder.CreateString("readType")
        writeTypeBuilderString = builder.CreateString("writeType")
        #createTypeBuilderString = builder.CreateString("createType")
        targetAddressBuilderString = builder.CreateString(typeAddress)

        # Serialize Reference data (for read operation)
        Reference.ReferenceStart(builder)
        Reference.ReferenceAddType(builder, readTypeBuilderString)
        Reference.ReferenceAddTargetAddress(
            builder, targetAddressBuilderString)
        reference_read = Reference.ReferenceEnd(builder)

        # Serialize Reference data (for write operation)
        Reference.ReferenceStart(builder)
        Reference.ReferenceAddType(builder, writeTypeBuilderString)
        Reference.ReferenceAddTargetAddress(
            builder, targetAddressBuilderString)
        reference_write = Reference.ReferenceEnd(builder)

        # Serialize Reference data (for create operation)
        # Reference.ReferenceStart(builder)
        #Reference.ReferenceAddType(builder, createTypeBuilderString)
        #Reference.ReferenceAddTargetAddress(builder, targetAddressBuilderString)
        #reference_create = Reference.ReferenceEnd(builder)

        # Create FlatBuffer vector and prepend reference data. Note: Since we prepend the data, prepend them in reverse order.
        Metadata.MetadataStartReferencesVector(builder, 2)
        # builder.PrependSOffsetTRelative(reference_create)
        builder.PrependSOffsetTRelative(reference_write)
        builder.PrependSOffsetTRelative(reference_read)
        references = builder.EndVector(2)

        # Serialize Metadata data
        Metadata.MetadataStart(builder)
        Metadata.MetadataAddNodeClass(builder, NodeClass.NodeClass.Variable)
        Metadata.MetadataAddOperations(builder, operations)
        Metadata.MetadataAddDescription(builder, descriptionBuilderString)
        Metadata.MetadataAddDescriptionUrl(builder, urlBuilderString)
        Metadata.MetadataAddUnit(builder, unitString)

        # Metadata reference table
        Metadata.MetadataAddReferences(builder, references)
        metadata = Metadata.MetadataEnd(builder)

        # Closing operation
        builder.Finish(metadata)
        return builder.Output()


    def __on_create(self, userdata: ctrlxdatalayer.clib.userData_c_void_p, address: str, data: Variant, cb: NodeCallback):
        cb(Result.OK, None)

    def __on_remove(self, userdata: ctrlxdatalayer.clib.userData_c_void_p, address: str, cb: NodeCallback):
        # Not implemented because no wildcard is registered
        cb(Result.UNSUPPORTED, None)

    def __on_browse(self, userdata: ctrlxdatalayer.clib.userData_c_void_p, address: str, cb: NodeCallback):
        new_data = Variant()
        new_data.set_array_string([])
        cb(Result.OK, new_data)

    def __on_read(self, userdata: ctrlxdatalayer.clib.userData_c_void_p, address: str, data: Variant, cb: NodeCallback):

        if address.endswith("controller-connected"):
            cb(Result.OK, self.controller_connected)
            return
        
        if address.endswith("full-data"):
            cb(Result.OK, self.full_data)
            return

        if address.endswith("left-button"):
            cb(Result.OK, self.left_button)
            return
        if address.endswith("right-button"):
            cb(Result.OK, self.right_button)
            return
        if address.endswith("left-button-bottom"):
            cb(Result.OK, self.left_button_bottom)
            return
        if address.endswith("right-button-bottom"):
            cb(Result.OK, self.right_button_bottom)
            return
        if address.endswith("b-button"):
            cb(Result.OK, self.b_button)
            return
        if address.endswith("y-button"):
            cb(Result.OK, self.y_button)
            return
        if address.endswith("x-button"):
            cb(Result.OK, self.x_button)
            return
        if address.endswith("a-button"):
            cb(Result.OK, self.a_button)
            return
        if address.endswith("up-cross-button"):
            cb(Result.OK, self.up_cross_button)
            return
        if address.endswith("down-cross-button"):
            cb(Result.OK, self.down_cross_button)
            return
        if address.endswith("left-cross-button"):
            cb(Result.OK, self.left_cross_button)
            return
        if address.endswith("right-cross-button"):
            cb(Result.OK, self.right_cross_button)
            return
        if address.endswith("Left-Joystick-X"):
            cb(Result.OK, self.l_joystick_x)
            return
        if address.endswith("Left-Joystick-Y"):
            cb(Result.OK, self.l_joystick_y)
            return
        if address.endswith("Right-Joystick-X"):
            cb(Result.OK, self.r_joystick_x)
            return
        if address.endswith("Right-Joystick-Y"):
            cb(Result.OK, self.r_joystick_y)
            return

        cb(Result.INVALID_ADDRESS, None)

    def __on_write(self, userdata: ctrlxdatalayer.clib.userData_c_void_p, address: str, data: Variant, cb: NodeCallback):

        if data.get_type() != VariantType.STRING:
            cb(Result.TYPE_MISMATCH, None)
            return

        cb(Result.INVALID_ADDRESS, None)

    def __on_metadata(self, userdata: ctrlxdatalayer.clib.userData_c_void_p, address: str, cb: NodeCallback):
        
        if address.endswith("controller-connected"):
            cb(Result.OK, self.controller_connected_metadata)
            return

        if address.endswith("full-data"):
            cb(Result.OK, self.full_data_metadata)
            return

        if address.endswith("left-button"):
            cb(Result.OK, self.left_button_metadata)
            return

        if address.endswith("right-button"):
            cb(Result.OK, self.right_button_metadata)
            return
        
        if address.endswith("left-button-bottom"):
            cb(Result.OK, self.left_button_bottom_metadata)
            return

        if address.endswith("right-button-bottom"):
            cb(Result.OK, self.right_button_bottom_metadata)
            return

        if address.endswith("b-button"):
            cb(Result.OK, self.b_button_metadata)
            return
        
        if address.endswith("y-button"):
            cb(Result.OK, self.y_button_metadata)
            return
        
        if address.endswith("x-button"):
            cb(Result.OK, self.x_button_metadata)
            return

        if address.endswith("a-button"):
            cb(Result.OK, self.a_button_metadata)
            return

        if address.endswith("up-cross-button"):
            cb(Result.OK, self.up_cross_button_metadata)
            return

        if address.endswith("down-cross-button"):
            cb(Result.OK, self.down_cross_button_metadata)
            return

        if address.endswith("left-cross-button"):
            cb(Result.OK, self.left_cross_button_metadata)
            return

        if address.endswith("right-cross-button"):
            cb(Result.OK, self.right_cross_button_metadata)
            return
        
        if address.endswith("Left-Joystick-X"):
            cb(Result.OK, self.l_joystick_x_metadata)
            return

        if address.endswith("Left-Joystick-Y"):
            cb(Result.OK, self.l_joystick_y_metadata)
            return

        if address.endswith("Right-Joystick-X"):
            cb(Result.OK, self.r_joystick_x_metadata)
            return

        if address.endswith("Right-Joystick-Y"):
            cb(Result.OK, self.r_joystick_y_metadata)
            return
            
        cb(Result.OK, None)