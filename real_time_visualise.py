import sys, serial, re
from PyQt5 import QtWidgets
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore

# === CONFIG ===
SERIAL_PORT = 'COM4'  # Change to your port (Linux: '/dev/ttyUSB0')
BAUD_RATE = 9600
MAX_POINTS = 200      # Rolling window size
AVER_POINTS = 6
UPDATE_MS = 10        # Plot refresh rate (ms)

# === SETUP ===
app = QtWidgets.QApplication(sys.argv)
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)

# Create plot window
win = pg.GraphicsLayoutWidget(title="MPU-6500 Real-Time")
win.resize(800, 600)
win.show()

# Create 6 plots (3 accel + 3 gyro)
plots = []
curves = []
colors = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00', '#ffff33']
labels = ['Accel X', 'Accel Y', 'Accel Z', 'Gyro X', 'Gyro Y', 'Gyro Z']

for i in range(6):
    plot = win.addPlot(row=i//3, col=i%3, title=labels[i])
    plot.setLabel('left', 'Value')
    plot.setLabel('bottom', 'Samples')
    plot.addLegend()
    plot.enableAutoRange('xy', True)
    curve = plot.plot(pen=colors[i], name=labels[i])
    plots.append(plot)
    curves.append(curve)

# Data buffers
data = [[] for _ in range(6)]

def to_signed16(val):
    return val if val < 0x8000 else val - 0x10000

def parse_line(serial_y):
    """Parse 'S,ax,ay,az,gx,gy,gz' → list of 6 ints"""
    try:
        ax = to_signed16((serial_y[0] << 8) | serial_y[1]);
        
        # ax = to_signed16((serial_y[0] << 8) | serial_y[1])  # ✅
        ay = to_signed16((serial_y[2] << 8) | serial_y[3]);
        az = to_signed16((serial_y[4] << 8) | serial_y[5]);

        #temp = (serial_y[6] << 8) | serial_y[7]; # Optional

        gx = to_signed16((serial_y[8]  << 8) | serial_y[9]);
        gy = to_signed16((serial_y[10] << 8) | serial_y[11]);
        gz = to_signed16((serial_y[12] << 8) | serial_y[13]);
        return [ax,ay,az,gx,gy,gz]
    except:
        return None
    
def read_serial_y():
    try:
        # Wait for sync byte 0xAA
        if ser.in_waiting > 0:
            byte = ser.read(1)
            if byte == b'\xAA':
                # Read next 2 bytes for 10-bit value
                if ser.in_waiting >= 14:
                    data1 = ser.read(14)
                    if len(data1) == 14:
                        #adc_value = (data[0] << 8) | data[1]
                        ser.reset_input_buffer()
                        return data1
        return None
    except Exception as e:
        print(f"Serial error: {e}")
        return None

def update():
    # Read all available lines
    while ser.in_waiting:
        line = read_serial_y()
        values = parse_line(line)
        if values:
            for i in range(6):
                if len(data[i]) > AVER_POINTS:
                    data[i].append((values[i]+data[i][-1]+data[i][-2]+data[i][-3]+data[i][-4])/AVER_POINTS)
                else:
                    data[i].append(values[i])
                if len(data[i]) > MAX_POINTS:
                    data[i].pop(0)
    
    # Update all curves
    for i in range(6):
        curves[i].setData(data[i])
    
    # Auto-scale Y-axis every 2 seconds (optional)
    if update.counter % 200 == 0:
        for i, plot in enumerate(plots):
            if data[i]:
                #plot.setYRange(min(data[i]), max(data[i]), padding=0.1)
                plot.setYRange(-9000, 9000, padding=0.1)
    update.counter += 1
update.counter = 0

# Timer for smooth updates
timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(UPDATE_MS)

# Cleanup on exit
def close_event():
    ser.close()
    sys.exit()
win.closeEvent = lambda e: close_event()

sys.exit(app.exec_())