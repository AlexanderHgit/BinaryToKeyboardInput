import usb.core
import usb.util
import time
import sys
import libusb_package
from usb.backend import libusb1
import tkinter as tk

from functools import partial
import keyboard

# Set up the GUI window
windowWidth = 460
windowHeight = 350
window = tk.Tk()
window.title("Binary to keyboard input")
window.geometry('{}x{}'.format(windowWidth, windowHeight))
window.tk.call('tk', 'scaling', 3.0)

class cinput:
    packet = 0
    bit = 0
inputs = {}

# Device Variables
deviceVendorId = 0xffff
devicendPointroductId = 0xffff
device = None
backend = libusb1.get_backend()
endPoint = None
interface = None
endpointAddress = None
maxPacketSIze = None
deviceList = []

# Create a canvas and a scrollbar
canvas = tk.Canvas(window, width=windowWidth, height=windowHeight)
scrollbar = tk.Scrollbar(window, orient="vertical", command=canvas.yview)
scrollbar.pack(side="right", fill="y")
canvas.pack(side="left", fill="both", expand=True)
canvas.configure(yscrollcommand=scrollbar.set)
canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

# Create a frame inside the canvas
frame = tk.Frame(canvas)
canvas.create_window((windowWidth/2, 0), window=frame, anchor="n")

packet_list = []
bytes_used = []
bit_list = [0, 1, 2, 3, 4, 5, 6, 7]
extra_column = 0
current_row = 0

# USB interfacing functions
def findDevices():
    for devices in libusb_package.find(find_all=True):
        deviceList.append(devices)
    displayFoundDevices()

def select_device(devi):
    global device, endPoint, interface, endpointAddress, maxPacketSIze
    deviceVendorId = devi.idVendor
    devicendPointroductId = devi.idProduct
    print("selecting device")
    device = usb.core.find(idVendor=deviceVendorId, idProduct=devicendPointroductId)
    print("device selected")
    if device is None:
        print("Device not found")
        return
    endPoint = device[0].interfaces()[0].endpoints()[0]
   
    interface = device[0].interfaces()[0].bInterfaceNumber
    print("config")
    device.set_configuration()
    print("configured")
    endpointAddress = endPoint.bEndpointAddress
    maxPacketSIze = endPoint.wMaxPacketSize
    print(interface)
    for i in range(maxPacketSIze):
        packet_list.append(i)
    print(f"Selected device: {device}, Endpoint Address: {endpointAddress}, Packet Size: {maxPacketSIze}")
    read_and_display_data()

def select_interface(selectedInterface):
    global interface, endPoint, endpointAddress, maxPacketSIze
    interface = interface.bInterfaceNumber
    endPoint = interface.endpoints()[0]
    endpointAddress = endPoint.bEndpointAddress
    maxPacketSIze = endPoint.wMaxPacketSize
    print(f"Selected interface: {selectedInterface}, Endpoint Address: {endpointAddress}, Packet Size: {maxPacketSIze}")

# GUI functions

decimal_labels = []
binary_labels = []

def displayStartScreen():
    tk.Button(frame, text="Find Devices", command=findDevices, height=1, width=20).grid(pady=5)
    update_scroll_region()

def read_and_display_data():
    global decimal_labels, binary_labels
    destroyWidgets()
    decimal_labels = []
    binary_labels = []
    for i in range(maxPacketSIze):  # Display enough labels for all bytes in the packet
        dec_lbl = tk.Label(frame, text='0', height=1, width=4)
        dec_lbl.grid(column=0, row=i)
        decimal_labels.append(dec_lbl)

        bin_lbl = tk.Label(frame, text='0', height=1, width=10)
        bin_lbl.grid(column=1, row=i)
        binary_labels.append(bin_lbl)
        if i + 1 == maxPacketSIze:
            clicked_packet = tk.IntVar()
            clicked_packet.set(packet_list[0])
            clicked_bit = tk.IntVar()
            clicked_bit.set(bit_list[0])
            input_text = tk.StringVar()
            input_text.set("")
            tk.Label(frame, text="Select input", height=1, width=10).grid(column=0, row=i + 1)
            tk.Entry(frame, textvariable=input_text, font=('calibre', 10, 'normal')).grid(column=1, row=i + 1)
            tk.Label(frame, text="Byte:", height=1, width=10).grid(column=0, row=i + 2)
            tk.OptionMenu(frame, clicked_packet, *packet_list).grid(column=1, row=i + 2)
            tk.Label(frame, text="Bit:", height=1, width=10).grid(column=0, row=i + 3)
            tk.OptionMenu(frame, clicked_bit, *bit_list).grid(column=1, row=i + 3)
            tk.Button(frame, text="Add input", command=partial(add_input, clicked_packet, clicked_bit, input_text), height=1, width=20).grid(column=0, row=i + 4)
    update_scroll_region()

def displayFoundDevices():
    destroyWidgets()
    extra_column = 0
    current_row = 0
    for i, devi in enumerate(deviceList):
        current_row += 1
        tk.Button(frame, text="VendorId: " + str(devi.idVendor), command=partial(select_device, devi), height=1, width=20).grid(pady=5)

        if i % 4 == 0 and i > 3:
            extra_column += 2
            current_row = 0


    update_scroll_region()

def update_data_labels(data):
    for i, byte in enumerate(data):
        if i < len(decimal_labels):
            decimal_labels[i].config(text=str(byte))
            binary_labels[i].config(text=format(byte, '08b'))

# Input functions
def add_input(clicked_packet, clicked_bit, input_text):
    input_value = input_text.get()
    packet_value = clicked_packet.get()
    bit_value = clicked_bit.get()
    bytes_used.append(packet_value)
    inputs[(packet_value, bit_value)] = input_value
    print(inputs)

def do_inputs(packet):
    for byte in bytes_used:
        for bit in range(8):  # Iterate over all 8 bits
            inp = inputs.get((byte, bit))
            if inp is not None:
                if packet[byte] & (1 << bit) != 0:
                    keyboard.press(inp)
                else:
                    keyboard.release(inp)

def destroyWidgets():
    for widget in frame.winfo_children():
        widget.destroy()

def exit_program():
    window.destroy()

def update_scroll_region():
    frame.update_idletasks()
    canvas.configure(scrollregion=canvas.bbox("all"))

# Main Loop
displayStartScreen()
while True:
    if device is not None:
        try:
            data = device.read(endpointAddress, maxPacketSIze, timeout=1000)
            update_data_labels(data)
            do_inputs(data)
        except usb.core.USBError as e:
            if e.args == ('Operation timed out',):
                continue
            else:
                print(f"USBError: {e}")
                device = None

    window.update_idletasks()
    window.update()
    time.sleep(0.01)

print("Program exited")
