#define pinCONTROL 12   // de pin waarmee we de RS 485 mee besturen (pin 18 fysiek)
// #define DEBUG
byte message[] = {0x00, 0x39, 0x39, 0x39, 0x30, 0x30, 0x32, 0x06, 0x30, 0x30, 0x2b, 0x33, 0x30, 0x30, 0x31, 0x04, 0x30, 0x30, 0x30, 0x04};

char MasterNode[4] = "211";
char myNodeID[4] = "652";

const byte pir1IntPin = 2;
const byte pir2IntPin = 3;
byte pir1Alert = 0;
byte pir1AlertRep = 0;
byte pir1AlertAck = 0;
byte pir2Alert = 0;
byte pir2AlertRep = 0;
byte pir2AlertAck = 0;

int deltaLDR = 200;
int ldr1Pin = 14;
int lastLDR1Value = 0;
int ldr2Pin = 15;
int lastLDR2Value = 0;

String readString;

void cbPir1Alert(){
  pir1Alert = 1;
}

void cbPir2Alert(){
  pir2Alert = 1;
}

void ValueToMessage(float Value) {
  // TODO: negatieve waarden
  int iLeft = (int)(Value);
  int iRight = 10000 * (Value - iLeft);

  String sLeft = String(iLeft);
  String sRight = String(iRight);

  if (iLeft > 99) {
    // value without decimal part
    char tmpBuffer[4];
    sLeft.toCharArray(tmpBuffer, sizeof(tmpBuffer));
    message[11] = 0x33;
    message[12] = tmpBuffer[0];
    message[13] = tmpBuffer[1];
    message[14] = tmpBuffer[2];
  }
  else if (iLeft > 9) {
    // two decimals, 1 fraction
    char tmpBuffer[3];
    sLeft.toCharArray(tmpBuffer, sizeof(tmpBuffer));
    message[11] = 0x32;
    message[12] = tmpBuffer[0];
    message[13] = tmpBuffer[1];
    // fraction
    char tmpBufferDec[2];
    sRight.toCharArray(tmpBufferDec, sizeof(tmpBufferDec));
    message[14] = tmpBufferDec[0];
  }
  else if (iLeft > 0) {
    // 1 decimals, 2 fraction
    char tmpBuffer[2];
    sLeft.toCharArray(tmpBuffer, sizeof(tmpBuffer));
    message[11] = 0x31;
    message[12] = tmpBuffer[0];
    // fraction
    char tmpBufferDec[3];
    sRight.toCharArray(tmpBufferDec, sizeof(tmpBufferDec));
    message[13] = tmpBufferDec[0];
    message[14] = tmpBufferDec[1];
  }
}

void InsertMessageChecksum() {
  // bereken checksum door message array pos 1 t/m. 15 op te tellen. Plaats het checksum getal in de message
  int iChecksum = 0;
  for (int i = 1; i < 16; i++) {
    iChecksum = iChecksum + message[i];
  } // for i

  char newChecksum[4];
  sprintf (newChecksum, "%03i", iChecksum);

  message[16] = newChecksum[0];
  message[17] = newChecksum[1];
  message[18] = newChecksum[2];
} // CalcMessageChecksum

void BoolValueToMessage(boolean Value) {
  message[10] = 0x2B;
  message[11] = 0x33;
  if (Value){
    message[12] = 0x30;
    message[13] = 0x30;
    message[14] = 0x31;
  }
  else{
    message[12] = 0x30;
    message[13] = 0x30;
    message[14] = 0x30;   
  }
}

void SendMessage() {
  InsertMessageChecksum();
  UCSR0A=UCSR0A |(1 << TXC0);
  digitalWrite(pinCONTROL,HIGH);
  delay(1);
  Serial.write(message, sizeof(message));
  while (!(UCSR0A & (1 << TXC0)));
  digitalWrite(pinCONTROL,LOW);
  delay(10);
}

void setup() {
  message[1] = MasterNode[0];
  message[2] = MasterNode[1];
  message[3] = MasterNode[2];
  
  message[4] = myNodeID[0];
  message[5] = myNodeID[1];
  message[6] = myNodeID[2];
  // RS485 control
  pinMode(pinCONTROL,OUTPUT);
  digitalWrite(pinCONTROL,LOW);
  
  Serial.begin(9600);
  #ifdef DEBUG
    Serial.print("NodeID: ");
    Serial.write(myNodeID, sizeof(myNodeID));
    Serial.println("."); 
  #endif

  pinMode(pir1IntPin, INPUT);
  pinMode(pir2IntPin, INPUT);
  attachInterrupt(digitalPinToInterrupt(pir1IntPin), cbPir1Alert, FALLING);
  attachInterrupt(digitalPinToInterrupt(pir2IntPin), cbPir2Alert, FALLING);

  lastLDR1Value = analogRead(ldr1Pin);
  lastLDR2Value = analogRead(ldr2Pin);
  
  #ifdef DEBUG
    Serial.println("Init done!"); 
  #endif
}

void loop() {
  char str[19];   // de hele inkomende message
  byte byte_receive;
  int iCalcChecksum;
  byte state = 0;
  char toNodeID[4];
  char readChecksum[4];

  // check for incoming messages
  int i = 0;
  if (Serial.available()) {
    state = 0;
    iCalcChecksum = 0;
    delay(50); // allows all serial sent to be received together
    while (Serial.available()) {
      byte_receive = Serial.read();
      readString += byte_receive;
      if (byte_receive == 00) {
        state = 1;
      }
      if ( (state == 1) && (i < 20) ) {
        str[i++] = byte_receive; 
        if (i < 17) {
          iCalcChecksum = iCalcChecksum + byte_receive;
        }
      }
    }
    str[i++] = '\0';
  }
  // Do Pull Messages 
  if (i > 19) {  // some hope for a incoming message...
    readChecksum[0] = str[16];
    readChecksum[1] = str[17];
    readChecksum[2] = str[18];
    readChecksum[3] = '\0';
    String sReadChar (readChecksum);
    
    toNodeID[0] = str[1];
    toNodeID[1] = str[2];
    toNodeID[2] = str[3];
    toNodeID[3] = '\0';

#ifdef DEBUG
    Serial.print("read Checksum: ");
    Serial.println(readChecksum);

    Serial.print("calculated checksum: ");
    Serial.println(iCalcChecksum);
    
    Serial.print("toNodeID: ");
    Serial.println(toNodeID);
#endif
    String sToNodeID(toNodeID);
    String sMyNodeID(myNodeID);
    if (sReadChar.toInt() == iCalcChecksum) {
      // valid checksum
      if ( (sToNodeID == sMyNodeID) ) {
        // voor onze node
        char nodeFunc[3];
        nodeFunc[0]=str[8];
        nodeFunc[1]=str[9];
        nodeFunc[2]='\0';
        String sNodeFunc(nodeFunc);
    
        char nodeValue[4];
        nodeValue[0]=str[12];
        nodeValue[1]=str[13];
        nodeValue[2]=str[14];
        nodeValue[3]='\0';
        String sNodeValue(nodeValue);
        if (str[7] == 5) {  
#ifdef DEBUG
          Serial.println("message ENQ!");
          Serial.print("functie: ");
          Serial.println(sNodeFunc);
#endif          
          if (sNodeFunc=="01"){
            message[7] = 0x05;  // QoS=1, need ack
            message[8] = 0x30;
            message[9] = 0x31;  // pirState is function 01 
            BoolValueToMessage(!digitalRead(pir1IntPin));
            SendMessage();
            pir1AlertRep=1;
          }else if (sNodeFunc=="02"){  
            message[7] = 0x05;  
            message[8] = 0x30;
            message[9] = 0x32;  
            BoolValueToMessage(!digitalRead(pir2IntPin));
            SendMessage();
            pir2AlertRep=1; 
          }
          else if (sNodeFunc=="03"){
            // LDR beneden
            message[7] = 0x06;  
            message[8] = 0x30;
            message[9] = 0x33; 
            int iLDRValue = analogRead(ldr1Pin);
            ValueToMessage(iLDRValue);
          }else if (sNodeFunc=="04"){
            // LDR boven
            message[7] = 0x06;  
            message[8] = 0x30;
            message[9] = 0x33;
            int iLDRValue = analogRead(ldr2Pin);
            ValueToMessage(iLDRValue);
          }
        } // if ENQ  
        else if (str[7] == 6) {
#ifdef DEBUG
          Serial.println("message ACK!");
#endif
          if (sNodeFunc=="01"){
            pir1AlertAck=1; // TODO time out retry
          } else if (sNodeFunc=="02"){
            pir2AlertAck=1; // TODO time out retry
          }
        } // msg ACK
        else if (str[7] == 0x15) {
#ifdef DEBUG
          Serial.println("message NACK!");
#endif
          // re send
          SendMessage();
        } // if NACK
      } // if this node
    } // if checksum
  } // if i > 19

  // read analog LDR values
  // TODO make generic
  int iCurrLDRValue = analogRead(ldr1Pin);
#ifdef DEBUG
  Serial.print("Current LDR light: ");
  Serial.print(iCurrLDRValue);
  Serial.print(" , last value: ");
  Serial.print(lastLDR1Value);
  Serial.print(" , (iCurrLDRValue-deltaLDR): ");
  Serial.println((iCurrLDRValue-deltaLDR));
#endif
delay(1000);
  if ((iCurrLDRValue) < (lastLDR1Value-deltaLDR)){
    // state change: much less light
    message[7] = 0x06;  // QOS: fire once and forget
    message[8] = 0x30;
    message[9] = 0x33;  // LDR = func 03
    ValueToMessage(iCurrLDRValue);
    SendMessage();
  }else if (iCurrLDRValue > (lastLDR1Value+deltaLDR)){
    // state change: much more light
    message[7] = 0x06;  // QOS: fire once and forget
    message[8] = 0x30;
    message[9] = 0x33;  // LDR = func 03
    ValueToMessage(iCurrLDRValue);
    SendMessage();
  }
  lastLDR1Value = iCurrLDRValue;
  iCurrLDRValue = analogRead(ldr2Pin);
  if ((lastLDR2Value) < (iCurrLDRValue-deltaLDR)){
    // state change: much less light
    message[7] = 0x06;  // QOS: fire once and forget
    message[8] = 0x30;
    message[9] = 0x34;  // LDR = func 03
    ValueToMessage(iCurrLDRValue);
    SendMessage();
  }else if (iCurrLDRValue > (lastLDR2Value+deltaLDR)){
    // state change: much more light
    message[7] = 0x06;  // QOS: fire once and forget
    message[8] = 0x30;
    message[9] = 0x34;  // LDR = func 03
    ValueToMessage(iCurrLDRValue);
    SendMessage();
  }
  lastLDR2Value = iCurrLDRValue;

  // Checking states & Push messages
  if (pir1Alert){
    if (!pir1AlertRep){
      message[7] = 0x05;  // QoS=1, need ack
      message[8] = 0x30;
      message[9] = 0x31;  // pirState is function 01 
      BoolValueToMessage(true);
      SendMessage();
      pir1AlertRep=1;
    }
    if (digitalRead(pir1IntPin)){ // nc PIR switch dus high is geen alarm
      pir1Alert=0;
      pir1AlertRep=0;
    }
  }
  if (pir2Alert){
    if (!pir2AlertRep){
      message[7] = 0x05;  // QoS=1, need ack
      message[8] = 0x30;
      message[9] = 0x32;  // pirState is function 01 
      BoolValueToMessage(true);
      SendMessage();
      pir2AlertRep=1;
    }
    if (digitalRead(pir2IntPin)){ // nc PIR switch dus high is geen alarm
      pir2Alert=0;
      pir2AlertRep=0;
    }
  }
}






