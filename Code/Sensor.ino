#include <Wire.h>
#include <Adafruit_MotorShield.h>

int s;
Adafruit_MotorShield AFMS = Adafruit_MotorShield(); 
Adafruit_StepperMotor *myMotor = AFMS.getStepper(200, 1);


int green = 3; // green LED pin
int red = 5;   // red LED pin
int d = 200; // default brightness

// booleans true if respective LED is 'on' 
boolean r = false;
boolean g = false; 

int change = 0;
String command; 

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);    
  AFMS.begin();            // motor default frequency 1.6kHz  
  myMotor->setSpeed(200);   // can make faster 

  pinMode(green, OUTPUT); 
  pinMode(red, OUTPUT);
}

// need to add microswitch for end stop !!
void loop() {
  // put your main code here, to run repeatedly:
if(Serial.available()==1){ 
    command = Serial.readString();       
    if (command == "on_red"){
      analogWrite(red,d);
      r = true;
    }
    else if (command == "on_green"){
      analogWrite(green,d);
      g = true;
    }
    else if(command == "off_red"){
      analogWrite(red,0);
      r = false;
    }
    else if(command == "off_green"){
      analogWrite(green,0);
      g = false;
    }
    else if(command == "dim"){
        while(!Serial.available()){;}
        change = Serial.parseInt();
        if((d+change<=220)and(d+change>=0)){
          d += change;
          if(r){
            analogWrite(red,d);
            Serial.print(d);}
          if(g){
            analogWrite(green,d);;
            Serial.print(d);}
        }
    }
    else if(command == "motor"){
      while(!Serial.available()){;}
      change = Serial.parseInt();
        if(change>0){
          Serial.println(change);
          myMotor->step(change,FORWARD,MICROSTEP);
        }
       else if(change<0){
          Serial.println(change);
          change = abs(change);
          myMotor->step(change,BACKWARD,MICROSTEP);
       }
    }
  }
}
