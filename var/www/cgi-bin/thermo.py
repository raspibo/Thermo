#!/usr/bin/env python3

"""
The MIT License (MIT)

Copyright (c) 2015 davide

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""

### Liberie
import time,os,json,redis,socket
import RPi.GPIO as GPIO
# Le mie librerie Json, Html, flt (Thermo(Redis))
import mjl, mhl, flt

# Nota: GPIO.BOARD utilizza il "connettore pin numero"
# Per esempio, per usare il GPIO22 si deve specificare il pin 15: GPIO.setup(15, GPIO.OUT)
GPIO.setmode(GPIO.BOARD)

### Parametri generali
ConfigFile="../conf/thermo.json"
FileCSV="../temperature.csv"
DirFile1w=["/sys/bus/w1/devices","w1_slave"]   # Directory e file di lettura sensori temperatura


# Ritorna il set point impostato per giorno/ora
def FindSetPoint():
    ## Calcolo del setpoint che e` nella programmazione settimanale
    Giorno=time.strftime("%w", time.localtime())    # 0 Domenica .. 6 Sabato
    Ora=time.strftime("%H", time.localtime())       # Le ore sono "01", "02", ... "24"
    # Mi serve una lista per la ricerca del giorno
    WeekDays=["domenica","lunedi","martedi","mercoledi","giovedi","venerdi","sabato"]
    # Prima trovo il nome
    SetPointName=MyDB.hget("temperature:cron:"+WeekDays[int(Giorno)],int(Ora))
    # Poi trovo il valore
    SetPointValue=MyDB.hget("temperature:setpoint",flt.Decode(SetPointName))
    # Poi trasformo in stringa
    SetPoint=flt.Decode(SetPointValue)
    return SetPoint

# Ritorna la temperatura del sensore di riferimento
def Temperatura():
    # Trovo il sensore di riferimento
    for i in MyDB.keys("sensore:temperatura:*"):
        j = flt.Decode(i)	# bin -> str , ed appoggio a variabile per comodita`
        ReadFileSensor=flt.ReadFile(DirFile1w[0]+"/"+j[20:]+"/"+DirFile1w[1])       # Leggo il file sonda
        if ReadFileSensor[36:39] == "YES":
            Temperatura=int(ReadFileSensor[69:])/1000
        else:
            Temperatura='err'
    return Temperatura

# Apre/legge un file e restituisce il contenuto
def ReadFile(Filename):
    if os.path.exists(Filename):
        FileTemp = open(Filename,"r")
        DataFile = FileTemp.read()
        FileTemp.close()
        return DataFile
    else:
        print ("Errore, manca il file", Filename)
        #exit()
        return "errore"

# Scrive un file
def WriteFileData(Filename,Dato):
    if not os.path.exists(Filename):
        FileTemp = open(Filename,"w")
        FileTemp.write(Dato)
        FileTemp.close()
    else:
        print ("Errore, il file", Filename,"esiste gia`.")
        exit()

# Aggiunge dati ad un file, aprendolo e richiudendolo
def AddFileData(Filename,Dato):
    if os.path.exists(Filename):
        FileTemp = open(Filename,"a")
        FileTemp.write(Dato)
        FileTemp.close()
    else:
        print ("Errore, manca il file", Filename)
        exit()

# Controlla una connessione di rete
def NetCheck(Hostname,Port):
    s = socket.socket()
    try:
        s.connect((Hostname,Port))
    except socket.error as msg:
        print("Non ho trovato/non mi collego a %s:%d.\nIl messaggio d\'errore e`: %s" % (Hostname, Port, msg))
        return False
    else:
        return True

# Funzione invio avvisi al database (Redis) server dei messaggi
def InviaAvviso(MsgID,Type,Desc,Value,UM,Date):
    Host=flt.Decode(MyDB.hget("redis:server:message","hostname"))
    Port=flt.Decode(MyDB.hget("redis:server:message","port"))
    Database=flt.Decode(MyDB.hget("redis:server:message","database"))
    Password=flt.Decode(MyDB.hget("redis:server:message","password"))
    if NetCheck(Host,Port):
        MyMsgDB = flt.OpenDB(Host,Port,Database,Password)
        MyMsgDB.hmset(MsgID, {"type": Type, "desc": Desc, "value": Value, "um": UM, "date": Date})
    else:
        print ("Non posso inviare l\'avviso a \"%s:%d\".\n" % (Hostname,Port))


# Apro il database Redis con l'istruzione della mia libreria
MyDB = flt.OpenDBFile(ConfigFile)


## Azzeramento e/o set delle variabili di processo
TempoCiclo=0
TempoGrafico=0
TempoInizioCiclo=TempoInizioGrafico=int(time.time())    # Tempo attuale
# Memoria di stato dell'uscita di comando "termostato" (0 off, 1 on)
OutputStateMemory=0
# Primo set point
SetPoint=FindSetPoint()


### Programma

try:
    while True: # ???
        ## Ciclo grafico
        # Aggiorna il file CSV delle temperature
        if int(time.time()) - TempoInizioGrafico > TempoGrafico:
            #
            # Scrivo il file temperature.csv
            # devo solo stare attento a on/man/antigelo/off per il set point
            # da decidere se inglobare il ciclo pid per risparmiare il ricalcolo di alcune variabili
            #
            # Una riga del CSV: "Data,SetPoint,Out,SensorePrincipale,SensoriExtra....."
            DataCSV=time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())
            #
            # Set point
            #SetPoint=FindSetPoint()    NON DOVREBBE SERVIRE PERCHE~ E~ CALCOLATO NEL PID
            #
            ## Calcolo dell'Uscita
            # Valore
            OutValue=flt.Decode(MyDB.hget("thermo:graph","outtemp"))
            # Se e` accesa .. oppure spenta ..
            if OutputStateMemory == 1:
                Output=OutValue
            else:
                Output="err"
            #
            ## Calcolo della sonda di temperatura principale
            SensorNthName=""
            # Prima devo trovare il sensore di riferimento
            for i in MyDB.keys("sensore:temperatura:*"):
                j = flt.Decode(i)	# bin -> str , ed appoggio a variabile per comodita`
                ReadFileSensor=ReadFile(DirFile1w[0]+"/"+j[20:]+"/"+DirFile1w[1])       # Leggo il file sonda
                if ReadFileSensor[36:39] == "YES":
                    ReadTemp=int(ReadFileSensor[69:])/1000
                else:
                    ReadTemp='err'
                if MyDB.get(j) == MyDB.hget("thermo:pid","sensor"):
                    Sensor1stName = ReadTemp
                else:
                    SensorNthName = SensorNthName+","+str(ReadTemp)
            #
            # Metto insieme le variabili trovate in una unica riga per l'inserimento nel CSV file
            RigaCSV=DataCSV+","+SetPoint+","+Output+","+str(Sensor1stName)
            if SensorNthName != "":
                RigaCSV=RigaCSV+SensorNthName
            #
            # Se non esiste, crea temperature.csv
            if not os.path.exists(FileCSV):
                Intestazione="Data,SetPoint,Out,"
                AltriSensori=""
                ## Aggiungo la temperatura di riferimento
                # Prima devo trovare il sensore di riferimento
                for i in MyDB.keys("sensore:temperatura:*"):
                    j = flt.Decode(i)	# bin -> str , ed appoggio a variabile per comodita`
                    if MyDB.get(j) == MyDB.hget("thermo:pid","sensor"):
                        k = flt.Decode(MyDB.hget("thermo:pid","sensor"))
                        Intestazione=Intestazione+k
                    else:
                        AltriSensori=AltriSensori+","+flt.Decode(MyDB.get(j))   # Memorizzo comunque il sensore trovato
                # Se sono stati trovati altri sensori, li aggiungo
                if AltriSensori != "":
                    Intestazione=Intestazione+AltriSensori
                WriteFileData(FileCSV,Intestazione)
                AddFileData(FileCSV,"\n")
            #
            AddFileData(FileCSV,RigaCSV)
            AddFileData(FileCSV,"\n")
            # ==============================
            # Alla fine devo sempre aggiornare i "tempi"
            TempoInizioGrafico = int(time.time())
            # MyDB.hget("thermo:graph","freqcheck") prendo il valore
            # flt.Decode(MyDB.hget("thermo:graph","freqcheck")) decodifico
            # int(flt.Decode(MyDB.hget("thermo:graph","freqcheck"))) trasformo in numero intero
            TempoGrafico=int(flt.Decode(MyDB.hget("thermo:graph","freqcheck")))*60      # moltiplico per 60 (secondi)
        #
        ## Ciclo PID
        # Controlla la temperatura e comanda l'uscita (Termostato)
        if int(time.time()) - TempoInizioCiclo > TempoCiclo:
            # Set uscita gpio
            Termostato=int(flt.Decode(MyDB.hget("thermo:pid","out")))
            GPIO.setup(Termostato, GPIO.OUT)
            if flt.Decode(MyDB.get("thermo:function")) == "off":
                # Mette ad off l'uscita e termina il ciclo
                GPIO.output(Termostato, False)
            else:
                # Set temperatura/e, messe qua perche` a monte verrebbero valutate inutilmente
                TemperaturaLetta=Temperatura()
                TemperaturaADD=flt.Decode(MyDB.hget("thermo:pid","tempadd"))
                TemperaturaSUB=flt.Decode(MyDB.hget("thermo:pid","tempsub"))
                if flt.Decode(MyDB.get("thermo:function")) == "on":
                    # Calcola set point
                    SetPoint=FindSetPoint()
                elif flt.Decode(MyDB.get("thermo:function")) == "manuale":
                    # Mette il Set point a manuale
                    SetPoint=flt.Decode(MyDB.hget("temperature:setpoint","manuale"))
                elif flt.Decode(MyDB.get("thermo:function")) == "antigelo":
                    # Mette il set poin ad antigelo
                    SetPoint=flt.Decode(MyDB.hget("temperature:setpoint","antigelo"))
                else:
                    SetPoint='err'
                    print("Selezione di funzionamento non valida o non presente")
                if SetPoint == 'err' or TemperaturaLetta == 'err':
                    print("Errore di lettura di una temperatura")
                    # Sta` robe e` da semplificare !!!!!
                    InviaAvviso("msg:thermo:ReadTemp:"+time.strftime("%Y%m%d%H%M%S",time.localtime()),"alert","Errore lettura temperatura: SetPoint, TemperaturaLetta",SetPoint+" "+TemperaturaLetta,"C",time.strftime("%Y/%m/%d %H:%M:%S",time.localtime()))
                else:
                    if (float(TemperaturaLetta) - float(TemperaturaADD)) > float(SetPoint):
                        GPIO.output(Termostato, False)
                    if (float(TemperaturaLetta) + float(TemperaturaSUB)) < float(SetPoint):
                        GPIO.output(Termostato, True)
            # Alla fine devo sempre aggiornare i "tempi"
            TempoInizioCiclo = int(time.time())
            # MyDB.hget("thermo:pid","freqcheck") prendo il valore
            # flt.Decode(MyDB.hget("thermo:pid","freqcheck")) decodifico
            # int(flt.Decode(MyDB.hget("thermo:pid","freqcheck"))) trasformo in numero intero
            TempoCiclo=int(flt.Decode(MyDB.hget("thermo:pid","freqcheck")))*60      # moltiplico per 60 (secondi)
            # E l'uscita
            OutputStateMemory=GPIO.input(Termostato)
        #
        # end try:
except KeyboardInterrupt:
    GPIO.cleanup()