# Sensor
Holds 3D models and code for glomerular basement membrane on chip functional assay. 

**3D Printable Parts**
Includes all .stl files ready for 3D printing. Also includes .f3z file which enables editing of the intitial project in Fusion 360. 

**Laser-Cuttable Parts** 
Includes all .dxf files ready for laser cutting in mm scale. Also includes .f3z file which enables editing of the intial proejct in Fusion 360. 

**CODE**  
Sensor.ino 
Script used to control Arduino operations: LED operation, stage movement via stepper motor, PWM brightness control. 

Sensor.py
Script used to automate data collection and enable manual control of sensor. Operates with Raspberry Pi. Includes camera visualization and stabilization and graphical user interface. Prior to use, several packages must be downloaded. In terminal, call these commands:
    # enable access to HQ camera
    sudo raspiconfig --> enable camera  
    
    # download appropriate packages
    sudo apt-get install -y picamera time serial libatlas-base-dev libhdf5-dev libhdf5-serial-dev libatlas-base-dev libjasper-dev  libqtgui4  libqt4-test python3-gi-cairo
    
    # download appropriate packages
    sudo pip3 install pyseimplegui numpy opencv-contrib-python opencv-python       matplotlib tifffile 
    
    # set color correction to 0 and enable access to pixels 
    sudo vcdbg set imx477_dpc 0  
    
