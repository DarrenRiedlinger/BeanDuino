// this example is public domain. enjoy!
// www.ladyada.net/learn/sensors/thermocouple

#include <max6675.h>
#include <LiquidCrystal.h>
#include <Wire.h>
#include <PID.h>

#define RelayPin 7

int thermoDO = 4;
int thermoCS = 5;
int thermoCLK = 6;

MAX6675 thermocouple(thermoCLK, thermoCS, thermoDO);
int vccPin = 3;
int gndPin = 2;

LiquidCrystal lcd(8, 9, 10, 11, 12, 13);

// make a cute degree symbol
uint8_t degree[8]  = {140,146,146,140,128,128,128,128};

//PID Definitions
//Define Variables we'll be connecting to
double Setpoint, Input, Output;
double PVal = 10;
double IVal = 2;
double DVal = 0.05;
double RoR = 0; // Rate of rise (degree/min)
double last_sp_adj; // Time when we last adjusted the sp for RoR

//Specify the links and initial tuning parameters
PID myPID(&Input, &Output, &Setpoint, PVal, IVal, DVal, DIRECT);

int WindowSize = 1000;
unsigned long windowStartTime;


int displayUpdateFrequency = 1000;
unsigned long lastDisplayUpdate;

float time;

char serialType;
double serialVal;
double serialDiv;

void setup() {
  Serial.begin(9600);
  // use Arduino pins 
  pinMode(vccPin, OUTPUT); digitalWrite(vccPin, HIGH);
  pinMode(gndPin, OUTPUT); digitalWrite(gndPin, LOW);
  
  lcd.begin(16, 2);
  lcd.createChar(0, degree);

  // wait for MAX chip to stabilize
  delay(500);

  //##### 
  //Begin PID
  pinMode(RelayPin, OUTPUT);
  windowStartTime = lastDisplayUpdate = millis();        
  
  //initialize the variables we're linked to
  Setpoint = 0;

  //tell the PID to range between 0 and the full window size
  myPID.SetOutputLimits(0, WindowSize);

  //turn the PID on
  myPID.SetMode(AUTOMATIC);
}

void loop() {
  // Check to see if serial data is available.
  if (Serial.available() > 0)
  {
    // Read 1 char prefix indicating what type of data
    // we are recieving (temp setpoint, PID param, ect).
    serialType = Serial.read();
    // (Re)set the placeholder double to zero.
    serialVal = 0;
    // (Re)set the decimal power to 0.
    serialDiv = 0;
    // Append each byte to the serialVar integer.
    while(Serial.available() > 0)
    {
      //If we reach the decimal point
      if (Serial.peek() == '.')
      {
        (void) Serial.read(); // Discard the decimal place
        serialDiv = 10; // Set divider to the '10ths' digit
      }
      
      // Process non-fractional decimal places
      if (serialDiv == 0)
      {      
        serialVal *= 10;
        serialVal += (Serial.read() - '0');
      }
      // Process fractional decimals
      else
      {
        serialVal += ((Serial.read() - '0') / serialDiv);
        serialDiv *=10;
      }
   delay(1); // Give the AVR time to receive all bytes.
   }
   
   
   switch(serialType) 
   {
     case 'S':     
       Setpoint = serialVal;
       RoR = 0;
       break;
     case 'R':
       RoR = serialVal;
       last_sp_adj = millis();
       break;                 
     case 'P':
       PVal = serialVal;
       myPID.SetTunings(PVal, IVal, DVal);
       break;
     case 'I':
       IVal = serialVal;
       myPID.SetTunings(PVal, IVal, DVal);
       break;
     case 'D':
       DVal = serialVal;
       myPID.SetTunings(PVal, IVal, DVal);
       break;
    }
  } // End If (serial.available())
  
  if (RoR != 0)
  {
    Setpoint += RoR * ((millis() - last_sp_adj) / 60000);
    last_sp_adj = millis();
  }
  
  Input = thermocouple.readFarenheit();
  myPID.Compute();

  /************************************************
   * turn the output pin on/off based on pid output
   ************************************************/
  if(millis() - windowStartTime>WindowSize)
  { //time to shift the Relay Window
    windowStartTime += WindowSize;  
  }
  
  if(Output < millis() - windowStartTime) digitalWrite(RelayPin,LOW);
  else digitalWrite(RelayPin,HIGH);
  
  if(millis() - lastDisplayUpdate > displayUpdateFrequency)
  {
    lastDisplayUpdate = millis();
    
    time = lastDisplayUpdate * .001;
    Serial.print(time);
    Serial.print(' ');
    Serial.println(Input);
    
    // basic readout test, just print the current temp
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print(Setpoint);
    lcd.print("P ");
    lcd.print(Output);
    
    // go to line #1
    lcd.setCursor(0,1);
    lcd.print(Input);
    
  #if ARDUINO >= 100
    lcd.write((uint8_t)0);
  #else
    lcd.print(0, BYTE);
  #endif
    lcd.print("F ");
  }

delay(180);

}

