// # arduinoHardware.ino for IoT Assignment CA2

#define LDRpin A0 // pin where we connected the LDR and the resistor

int LDRValue = 0;     // result of reading the analog pin
int ledPin = 13;                // choose the pin for the LED
int motionPin = 2;               // choose the input pin (for PIR sensor)
int pirState = LOW;             // we start, assuming no motion detected
int motionVal = 0;                    // variable for reading the pin status


void setup() {
  // put your setup code here, to run once:
  pinMode(ledPin, OUTPUT);      // declare LED as output
  pinMode(motionPin, INPUT);     // declare motion sensor as input
  Serial.begin(9600); // sets serial port for communication
}

void loop() {
  LDRValue = analogRead(LDRpin); // read the value from the LDR
//  Serial.println(LDRValue);      // print the value to the serial port
  motionVal = digitalRead(motionPin);  // read input value
  Serial.println(String(LDRValue) + "," + String(motionVal));
//  Serial.println(motionVal);
  if (motionVal == HIGH) {            // check if the input is HIGH
    
    if (LDRValue < 500){ // check LDRValue
      digitalWrite(ledPin, HIGH);  // turn LED ON
    } else { // end of LDRValue check
      digitalWrite(ledPin, LOW);
    }
    
  } else {
    digitalWrite(ledPin, LOW); // turn LED OFF
  }

  delay(1000); // delay 3s

} // end of loop
