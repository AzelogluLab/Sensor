from picamera import PiCamera #sudo raspiconfig --> enable camera, sudo apt-get install picamera 
import time               # sudo apt-get install time
import serial             # sudo apt-get install serial
import PySimpleGUI as sg  # sudo pip3 install pysimplegui; pip3 install -U numpy; pip3 install opencv-contrib-python;
#sudo apt-get install -y libatlas-base-dev libhdf5-dev libhdf5-serial-dev libatlas-base-dev libjasper-dev  libqtgui4  libqt4-test

import cv2    #pip3 install opencv-python
import numpy as np
import matplotlib.pyplot as plt  # pip3 install matplotlib; sudo apt-get install python3-gi-cairo
import tifffile as tf       # pip3 install tifffile 

from fractions import Fraction

#     sudo vcdbg set imx477_dpc 0      set color correction to 0 to enable access to pixels

class FS:
    usb = None
    USB_PORT = '/dev/ttyACM0'  #USB depends on Arduino model
    
    camera = PiCamera(sensor_mode=2) #2X2 binning, 0.1-50fps
    camera.resolution=(507,380)  # 8x8 binning 
    
    #define ROIs for inlet and outlet and background values as global variables 
    roi_in = None
    roi_out = None
    roi_bg = None

    inlet_cropped = None
    outlet_cropped = None
    
    background_r = None
    background_f = None
    
    #define datapoint arrays for mean brightness of inlet and outlet ROIs
    time = [] 
    inlet_brightness = []   #each are arrays at time = t, [FITC value, TRITC value] i.e [Inulin, Albumin] 
    outlet_brightness = []
    inlet_concentration = []
    outlet_concentration = []
    
    def connect(self):
        #connect to Arduino via Serial port 
        try:
            self.usb = serial.Serial(self.USB_PORT, baudrate=9600,timeout=0.1)
            print('Connected.')
        except:
            print('ERROR - Could not open serial port. Pleace check connection and/or permissions.')
        
      
    # mode for fluorescent imaging. fixed to ensure consistent imaging 
    def dark_mode(self):
        self.camera.framerate = 1
        self.camera.shutter_speed = 1000000
        self.camera.iso = 800
        self.camera.awb_mode = 'off'
        # gains imperically measured, can adjust 
        self.camera.awb_gains=(Fraction(2,1), Fraction(1, 1))
        
    def focus_mode(self):
        self.framerate = 0.0001
        self.camera.shutter_speed = 1
        self.camera.iso = 200
            
    def green_on(self):
        self.usb.write(str.encode('on_green'))
    def red_on(self):
        self.usb.write(str.encode('on_red'))
    def green_off(self):
        self.usb.write(str.encode('off_green'))
    def red_off(self):
        self.usb.write(str.encode('off_red'))
    def brightness(self, change):
        self.usb.write(str.encode('dim'))
        time.sleep(1.1)
        self.usb.write(str.encode(str(change)))
    def focus(self, change):
        self.usb.write(str.encode('motor'))
        time.sleep(1.1)
        self.usb.write(str.encode(str(change)))
    
    def get_background(self,dst):
        ## gets background value at each pixel for each pixel color (r, g) 
        # try catch to make sure ROI's are selected 
        '''
        try:
            len(self.roi_in)
            self.roi_in = list(self.roi_in)
        except:
            print('ERROR -- Please select inlet ROI.')
            return
        try:
            len(self.roi_out)
            self.roi_out = list(self.roi_out)
        except:
            print('ERROR -- Please select outlet ROI.')
            return
        '''
        
        # get background with green light on 
        time.sleep(1.1)
        self.green_on()
        time.sleep(4)
        adr = dst + '/fitc-background.tif'
        # take a raw rbg image into a numpy array for data collection
        fitc_image = self.take_pic()
        tf.imwrite(adr,fitc_image,photometric="rgb")
        self.background_f = fitc_image
        #l = fitc_image.shape[0]
        #w = fitc_image.shape[1]
        #self.background_f = fitc_image[:l,:w,1] ### DEBUGGED 

        # get background for red light 
        time.sleep(1.1)
        self.green_off()
        time.sleep(1.1)
        self.red_on()
        time.sleep(4)
        
        adr = dst + '/txrd-background.tif'
        # save texas red image to numpy array
        txrd_image = self.take_pic()
        tf.imwrite(adr,txrd_image,photometric="rgb")
        self.background_r = txrd_image
        #self.background_r=txrd_image[:l,:w,0] ### DEBUGGED
        
        time.sleep(1.1)
        self.red_off()
        time.sleep(1.1)
        
        
    def collect_data(self, dst, t):
        # dst = destination pathway for images, t = time
        # time resolution = 8 seconds
        # initialize data arrays [FITC, TXRD] for each time point
        #brightness is calculated by averaging the pixel values and subtracting any background 
        self.brightness(100)
        # make sure user has selected ROI
        try:
            len(self.roi_in)
            self.roi_in = list(self.roi_in)
        except:
            print('ERROR -- Please select inlet ROI.')
            return
        try:
            len(self.roi_out)
            self.roi_out = list(self.roi_out)
        except:
            print('ERROR -- Please select outlet ROI.')
            return
        try:
            len(self.background_f)
        except:
            print('ERROR -- Please select background')
        
        F_T_in = []
        F_T_out = []
        time.sleep(1.1)
        self.green_on()
        time.sleep(4)
        adr = dst + '/fitc-t' + str(t) 
        
        # take a raw rbg image into a numpy array for data collection
        fitc_image = self.take_pic()
        self.save_image(adr)
        adr = adr + '.tif'
        tf.imwrite(adr, fitc_image,photometric="rgb")
        
        # subtract fitc background values for numerical calculations
        fitc_image1 = fitc_image - self.background_f
        fitc_image1[fitc_image < self.background_f] = 0
        adr = dst + '/fitc-t' + str(t) + '-adjusted.tif'
        tf.imwrite(adr,fitc_image1,photometric="rgb")
        
        # get inlet values            
        self.inlet_cropped = fitc_image1[int(self.roi_in[1]):int(self.roi_in[1]+self.roi_in[3]), int(self.roi_in[0]):int(self.roi_in[0]+self.roi_in[2])]
        length = self.inlet_cropped.shape[0]
        width = self.inlet_cropped.shape[1]
        F_T_in.append(np.mean(self.inlet_cropped[:length,:width,1])) # isolate green pixel 
        
    
        # get outlet values             
        self.outlet_cropped = fitc_image1[int(self.roi_out[1]):int(self.roi_out[1]+self.roi_out[3]), int(self.roi_out[0]):int(self.roi_out[0]+self.roi_out[2])]
        #F_T_out.append(np.mean(self.outlet_cropped)-np.mean(self.background_cropped))
        length = self.outlet_cropped.shape[0]
        width = self.outlet_cropped.shape[1]
        F_T_out.append(np.mean(self.outlet_cropped[:length,:width,1])) # isolate green pixel 
       
        #print(self.outlet_cropped)
        
        # switch to red LED 
        time.sleep(1.1)
        self.green_off()
        time.sleep(1.1)
        self.red_on()
        time.sleep(4)

        adr = dst + '/txrd-t' + str(t)
        # save texas red image to numpy array
        txrd_image1 = self.take_pic()
        #save image as .tif
        self.save_image(adr)
        adr = adr + '.tif'
        tf.imwrite(adr, txrd_image1,photometric="rgb")
        
        # subtract background values for numerical calculations
        txrd_image = txrd_image1 - self.background_r
        txrd_image[txrd_image1 < self.background_r] = 0
        adr = dst + '/txrd-t' + str(t) + '-adjusted.tif'
        tf.imwrite(adr,txrd_image,photometric="rgb")
        
        # get inlet values            
        self.inlet_cropped = txrd_image[int(self.roi_in[1]):int(self.roi_in[1]+self.roi_in[3]), int(self.roi_in[0]):int(self.roi_in[0]+self.roi_in[2])]
        #F_T_in.append(np.mean(self.inlet_cropped)-np.mean(self.background_cropped))
        length = self.inlet_cropped.shape[0]
        width = self.inlet_cropped.shape[1]
        F_T_in.append(np.mean(self.inlet_cropped[:length,:width,0])) # isolate red pixel 
       
        # get outlet values             
        self.outlet_cropped = txrd_image[int(self.roi_out[1]):int(self.roi_out[1]+self.roi_out[3]), int(self.roi_out[0]):int(self.roi_out[0]+self.roi_out[2])]
        #F_T_out.append(np.mean(self.outlet_cropped)-np.mean(self.background_cropped))
        length = self.outlet_cropped.shape[0]
        width = self.outlet_cropped.shape[1]
        F_T_out.append(np.mean(self.outlet_cropped[:length,:width,0])) # isolate red pixel
        
        # add data to inlet and outlet data 
        self.inlet_brightness.append(F_T_in)
        self.outlet_brightness.append(F_T_out)
        
        #add to time array            
        self.time.append(t)
        self.red_off() 
            
    def user(self):
        # opens camera preview, allows user to select desired ROIs, allows user to start data collection
        try:
            self.camera.start_preview(fullscreen=False,window=(100,20,640,480))
            self.connect()
        except:
            print('Check camera connections.')
            return
        dst = ""
        time.sleep(1)
        
        layout = [
          [sg.Text('Light Control:')],
          [sg.Button('Red On'), sg.Button('Green On')],
          [sg.Button('Red Off'), sg.Button('Green Off')],[sg.Button('Dark Mode'),sg.Button('Focus Mode')],
          [sg.Text('Brightness Control: ')],[ sg.Button('Up'), sg.Button('Down')],
          [sg.Text('Focus Control:')],
          [sg.Button('Coarse Up'), sg.Button('Fine Up')],
          [sg.Button('Coarse Down'), sg.Button('Fine Down')],
          [sg.Text('ROI Selection:')],
          [sg.Text('Enter address you want to save all files to. EX: /home/pi/images/07-20-2021'),sg.Input(key='-ADR-')],
          [sg.Button('Select Inlet'), sg.Button('Select Outlet'),sg.Text('Press enter when ROI is selected.')],
          [sg.Button('Take Picture'),sg.Text('Enter filename:'),sg.Input(key='-IMG-')],[sg.Text('RUN:')],
          [sg.Text('How long do you want to run the sensor?'), sg.Input(key='-DUR-'), sg.Text('minutes.')],
          [sg.Text('How often do you want to sample? Every'), sg.Input(key='-FREQ-'), sg.Text('minutes.')],
          [sg.Button('Get Background'), sg.Button('Run Sensor'), sg.Button('Save Data')],
          [sg.Text(size=(40,1),key='-ERR-')],
          [sg.Button('Ok'), sg.Button('Quit')]]

        window = sg.Window('Fluorescence Sensor', layout)
        while True:
            # events are buttons pressed, values are dictionaries based on user input
            event, values = window.read()
            if event == sg.WINDOW_CLOSED or event == 'Quit':
                break
            elif event == 'Red On':
                self.red_on()
            elif event == 'Green On':
                self.green_on()
            elif event == 'Red Off':
                self.red_off()
            elif event == 'Green Off':
                self.green_off()
            elif event == 'Coarse Up':
                self.focus(100)
            elif event == 'Coarse Down':
                self.focus(-100)
            elif event == 'Fine Up':
                self.focus(5)
            elif event == 'Fine Down':
                self.focus(-5)
            elif event == 'Up':
                self.brightness(20)
            elif event == 'Down':
                self.brightness(-20)
            elif event == 'Dark Mode':
                self.dark_mode()
            elif event == 'Focus Mode':
                self.focus_mode()
            elif event == 'Take Picture':
                try:
                    img = str(values['-IMG-'])
                    self.save_image(img)
                except:
                    window['-ERR-'].update('ERROR. Please enter valid filename.')
                
            elif event == 'Select Inlet':
                try:
                    adr = str(values['-ADR-'])+'/ROI-selection-t0.png'
                    dst = str(values['-ADR-'])
                    self.camera.capture(adr)
                    
                    img = cv2.imread(adr)
                    fromCenter = False
                    cv2.resizeWindow('Select Inlet', 400, 800)
                    self.roi_in = cv2.selectROI('Select Inlet', img, fromCenter)
                

                    # work around for closing window without user
                    cv2.waitKey(1)
                    cv2.destroyAllWindows()
                                        
                    window['-ERR-'].update('Inlet Selected Successfully.')
                except:
                    window['-ERR-'].update('ERROR. Please enter valid photo address.')
                    
            elif event == 'Select Outlet':
                try:
                    adr = str(values['-ADR-'])+'/ROI-selection-t0.png' 
                    self.camera.capture(adr)
                    
                    img = cv2.imread(adr)
                    fromCenter = False
                    self.roi_out = cv2.selectROI('Select Outlet', img, fromCenter)
                    
                    # work around for closing window without user 
                    cv2.waitKey(1)
                    cv2.destroyAllWindows()
                    
                    window['-ERR-'].update('Outlet Selected Successfully.')
                                
                except:
                    window['-ERR-'].update('ERROR. Please enter valid photo address.')
            elif event == 'Get Background':
                self.get_background(values['-ADR-'])
            elif event == 'Run Sensor':
                # set camera to dark mode to see dim signal 
                self.dark_mode()
                t = 0
                time.sleep(0.2)
                self.green_off()
                time.sleep(1.1)
                self.red_off()
                
                ## FOR DEBUG
                x = int(values["-DUR-"])*60
                y = int(values["-FREQ-"])*60
                while(t<=x):
                    self.collect_data(values['-ADR-'],t)
                    time.sleep(y-15)
                    t+=y+15
                
                
                ## END DEBUG

                #try:
                   # x = int(values['-DUR-'])*60
                  #  y = int(values['-FREQ-'])*60
                        
                   # while(t<=x):
                     #   self.collect_data(values['-ADR-'],t)
                      #  time.sleep(y-15)
                      #  t+=y+15
                #except:
                   # window['-ERR-'].update('ERROR. Please enter an integer value for duration and sampling frequency.')
            
            elif event == "Save Data":
                try:
                    self.save_data(str(values['-ADR-']))
                except:
                    window['-ERR-'].update('ERROR. Please enter valid photo address.')
                 
        # turn off when window is closed          
        self.green_off()
        time.sleep(1.1)
        self.red_off()
        window.close()
        self.camera.close()
        try:
            self.save_data(dst)
        except:
            print("Data not saved. If you want to save your data, type 'f.save_data(*address*)' into shell.")
        
    # save data as a text file     
    def save_data(self, dst):
        ''' Saves brightness and concentration data into csv's'''
        # open a binary file in write mode
        #self.get_conc()
        f_in = self.to_arr(self.inlet_brightness,0)
        adr = str(dst) + '/inlet_fitc_intensity.csv'
        np.savetxt(adr, [f_in], delimiter=',', fmt = '%1.5f')
        r_in = self.to_arr(self.inlet_brightness,1)
        adr = str(dst) + '/inlet_txrd_intensity.csv'
        np.savetxt(adr, [r_in], delimiter=',', fmt = '%1.5f')
        f_out = self.to_arr(self.outlet_brightness,0)*1.44 # imperical adjustment + volume difference 
        adr = str(dst) + '/outlet_fitc_intensity.csv'
        np.savetxt(adr, [f_out], delimiter=',', fmt = '%1.5f')
        r_out = self.to_arr(self.outlet_brightness,1)*1.26 # imperical adjustment + volume difference 

        adr = str(dst) + '/outlet_txrd_intensity.csv'
        np.savetxt(adr, [r_out], delimiter=',', fmt = '%1.5f')
        adr = str(dst) + '/time.csv'
        t = np.array(self.time)
        np.savetxt(adr, [t], delimiter = ',',fmt = '%1.5f')
        
        f_in = self.to_arr(self.inlet_concentration,0)
        adr = str(dst) + '/inlet_fitc_concentration.csv'
        np.savetxt(adr, [f_in], delimiter=',', fmt = '%1.5f')
        f_out = self.to_arr(self.outlet_concentration,0)
        adr = str(dst) + '/outlet_fitc_concentration.csv'
        np.savetxt(adr, [f_out], delimiter=',', fmt = '%1.5f')
        r_in = self.to_arr(self.inlet_concentration,1)
        adr = str(dst) + '/inlet_txrd_concentration.csv'
        np.savetxt(adr, [r_in], delimiter=',', fmt = '%1.5f') 
        r_out = self.to_arr(self.outlet_concentration,1)
        adr = str(dst) + '/outlet_txrd_concentration.csv'
        np.savetxt(adr, [r_out], delimiter=',', fmt = '%1.5f') 
    
    def get_conc(self):
        '''converts pixel intensity value to estimated concentration of target molecules
        based on 4 paramater curve fit of calibration curve. each user must calibrate
        based on their own device. maintains structure of intensity array.'''
        for i in range(0,len(self.time)):
            temp = []
            f_val = self.inlet_brightness[i][0]
            t_val = self.inlet_brightness[i][1]
            # hard-coded numbers based on inverse of non-linear regression,
            # inlet 
            fitc_conc = -0.2143-np.log(np.divide(274.5-f_val,1.131*(f_val-2.975)))
            temp.append(fitc_conc)
            tr_conc = -0.6446-np.log((np.divide(236.7-t_val,1.097*(t_val-26.64))))
            temp.append(tr_conc)
            for j in range(0,len(temp)):
                print(temp[j])
                temp[j] = 10**temp[j]
            self.inlet_concentration.append(temp)
            #outlet
            temp = []
            f_val = self.outlet_brightness[i][0]
            t_val = self.outlet_brightness[i][1]
            fitc_conc = -0.2143-np.log(np.divide(274.5-f_val,1.131*(f_val-2.975)))
            temp.append(fitc_conc)
            tr_conc = -0.6446-np.log((np.divide(236.7-t_val,1.097*(t_val-26.64))))
            temp.append(tr_conc)
            for j in range(0,len(temp)):
                print(temp[j])
                temp[j] = 10**temp[j]
            #temp = np.log10(temp)
            self.outlet_concentration.append(temp)
            
    def take_pic(self):
        image = np.empty((384, 512, 3), dtype=np.uint8)
        self.camera.capture(image, 'rgb')
        image = image[:380, :507]
        return image
    
    def single_test(self,adr):
        adr = adr+'/ROI-selection.png' 
        self.camera.capture(adr)     
        img = cv2.imread(adr)
        fromCenter = False
        roi = cv2.selectROI('Select Background', img, fromCenter)
        cv2.waitKey(1)
        cv2.destroyAllWindows()
        
        self.green_on()
        time.sleep(2)
        fitc_image = self.take_pic()
        fitc_image1 = fitc_image - self.background_f
        fitc_image1[fitc_image < self.background_f] = 0
        cropped = fitc_image1[int(roi[1]):int(roi[1]+roi[3]), int(roi[0]):int(roi[0]+roi[2])]
        
        length = cropped.shape[0]
        width = cropped.shape[1]
        print('Green: ' + str(np.mean(cropped[:length,:width,1]))) # isolate green pixel
        
        time.sleep(1.1)
        self.green_off()
        time.sleep(1.1)
        self.red_on()
        time.sleep(2)
      
        txrd_image = self.take_pic()
        txrd_image1 = txrd_image - self.background_r 
        txrd_image1[txrd_image < self.background_r] = 0
        cropped = txrd_image1[int(roi[1]):int(roi[1]+roi[3]), int(roi[0]):int(roi[0]+roi[2])]
        
        print('Red: '+ str(np.mean(cropped[:length,:width,0]))) # isolate red pixel
        
        time.sleep(1.1)
        self.red_off()
        time.sleep(1.1)

    def save_image(self,adr):
        adr = adr + '.png'
        self.camera.capture(adr)
    
    def to_arr(self,arr,ind):
    # converts inlet and outlet brightness arrays into array compatible with easy graphing
        ret = []
        for i in range(0,len(arr)):
            ret.append(arr[i][ind])
        return np.array(ret)
        
    def plot(self):
    # plot inlet and outlet brightness against time
        #convert all data into numpy arrays of desired values (FITC and TXRD values in inlet vs. outlet) 
        fi = []
        y = np.array(self.time)
        for i in range(0,len(self.time)):
            fi.append(self.inlet_brightness[i][0])
        fi = np.array(fi)
        ti = []
        for i in range(0,len(self.time)):
            ti.append(self.inlet_brightness[i][1])
        ti = np.array(ti)
        fo = []
        for i in range(0,len(self.time)):
            fo.append(self.outlet_brightness[i][0])
        fo = np.array(fo)
        to = []
        for i in range(0,len(self.time)):
            fo.append(self.outlet_brightness[i][1])
        to = np.array(to)
        # plot all data on the same plot
        plt.plot(y, fi, label = "FITC Inlet Value",color='c')
        plt.xlabel('Time (s)')
        plt.ylabel('Average Pixel Value')
        plt.title('Average Pixel Value vs. Time')
        plt.plot(y,ti,label='Texas Red Inlet Value',color='m')
        plt.plot(y,fo,label='FITC Outlet Value',color='g')
        plt.plot(y,to,label='Texas Red Outlet Value',color='red')
        plt.legend(loc='upper right')
        # Display a figure.
        plt.show()
                                                                                                                                                                                                                                                 
if __name__ == '__main__':
#     #run user window automatically
    f = FS()
    #f.connect()
    f.user() 
    #f.camera.start_preview(fullscreen=False,window=(100,20,640,480))
    #f.dark_mode()
    #f.user()


    


