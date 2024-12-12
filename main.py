import tkinter as tk
from tkinter import ttk
import serial.tools.list_ports
import threading
import struct
import serial
from influxdb_client import InfluxDBClient, Point, WritePrecision

class SerialReaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PGx Serial Reader")
        
        self.serial_port = None
        self.reading_thread = None
        self.reading = False
        
        self.create_widgets()
        self.update_ports()

        # InfluxDB connection
        self.client = InfluxDBClient.from_config_file("config.ini")
        self.write_api = self.client.write_api()

    def create_widgets(self):
        self.port_label = tk.Label(self.root, text="Select COM Port:")
        self.port_label.grid(row=0, column=0, padx=10, pady=10)

        self.port_var = tk.StringVar()
        self.port_dropdown = ttk.Combobox(self.root, textvariable=self.port_var)
        self.port_dropdown.grid(row=0, column=1, padx=10, pady=10)

        self.refresh_button = tk.Button(self.root, text="Refresh Ports", command=self.update_ports)
        self.refresh_button.grid(row=0, column=2, padx=10, pady=10)

        self.start_button = tk.Button(self.root, text="Start", command=self.start_reading)
        self.start_button.grid(row=1, column=0, padx=10, pady=10)

        self.stop_button = tk.Button(self.root, text="Stop", command=self.stop_reading)
        self.stop_button.grid(row=1, column=1, padx=10, pady=10)

    def update_ports(self):
        ports = serial.tools.list_ports.comports()
        self.port_dropdown['values'] = [port.device for port in ports]

    def start_reading(self):
        if not self.reading:
            self.serial_port = self.port_var.get()
            if self.serial_port:
                self.reading = True
                self.reading_thread = threading.Thread(target=self.read_serial_data, daemon=True)
                self.reading_thread.start()

    def stop_reading(self):
        self.reading = False
        if self.reading_thread:
            self.reading_thread.join()

    def write_to_influxdb(self, data):
        point = Point("pgxData")
        point.field('partectorNumber', data['partectorNumber'])
        point.field('partectorDiam', data['partectorDiam'])
        point.field('partectorMass', data['partectorMass'])
        point.field('grimmValue', data['grimmValue'])
        point.field('temperature', data['temperature'])
        point.field('humidity', data['humidity'])
        point.field('pressure', data['pressure'])
        point.field('altitude', data['altitude'])
        point.field('latitude', data['latitude'])
        point.field('longitude', data['longitude'])
        point.field('co2', data['co2'])
        self.write_api.write(bucket="pgx", org="umt", record=point, numeric_precision=6)

    def read_serial_data(self):
        ser = serial.Serial(self.serial_port, 115200)
        struct_format = '<2i8fH'
        while self.reading:
            if ser.in_waiting > 0:
                while ser.read() != b'<':
                    pass
                struct_size = struct.calcsize(struct_format)
                data = ser.read(struct_size)
                if ser.read() == b'>':
                    unpacked_data = struct.unpack(struct_format, data)
                    data_dict = {
                        'partectorNumber': unpacked_data[0],
                        'partectorDiam': unpacked_data[1],
                        'partectorMass': unpacked_data[2],
                        'grimmValue': unpacked_data[3],
                        'temperature': unpacked_data[4],
                        'humidity': unpacked_data[5],
                        'pressure': unpacked_data[6],
                        'altitude': unpacked_data[7],
                        'latitude': unpacked_data[8],
                        'longitude': unpacked_data[9],
                        'co2': unpacked_data[10]
                    }
                    self.write_to_influxdb(data_dict)
                    print(data_dict)
        ser.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialReaderApp(root)
    root.mainloop()