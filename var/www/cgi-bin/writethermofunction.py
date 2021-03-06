#!/usr/bin/env python3

# Questo file legge il file di configurazione,
# trova e modifica il parametro eseguendo il rispettivo "write*.py"

# Serve per la parte di gestione html in python
import cgi
import cgitb

# Abilita gli errori al server web/http
cgitb.enable()

# Le mie librerie Json, Html, flt (Thermo(Redis))
import mjl, mhl, flt

import redis

# Parametri generali
TestoPagina="Configurazione/Selezione funzionamento"
ConfigFile="../conf/thermo.json"
#WriteFile="/cgi-bin/writethermofunction.py"
# Redis "key"
RedisKey = "thermo:function"

# Apro il database Redis con l'istruzione della mia libreria
MyDB = flt.OpenDBFile(ConfigFile)

# Start web page - Uso l'intestazione "web" della mia libreria
print (mhl.MyHtml())
print (mhl.MyHtmlHead())

# Scrivo il Titolo/Testo della pagina
print ("<h1>","<center>",TestoPagina,"</center>","</h1>")
print ("<hr/>","<br/>")
# Eventuale help/annotazione
#print ("Ho lasciato la possibilita` di lasciare vuota la password","<hr/>","<br/>")

form=cgi.FieldStorage()

if RedisKey not in form:
    print ("<h3>Manca il valore: </h3>",RedisKey)
else:
    MyDB.set(RedisKey,cgi.escape(form[RedisKey].value))

print ("<h2>Dati inseriti/modificati:</h2>")
print ("<br>")
print ("<table border=\"1\" cellspacing=\"0\" cellpadding=\"3\">")
print ("<tr>")
print ("<td>")
print (RedisKey)
print ("</td>")
print ("<td>")
print (MyDB.get(RedisKey))
print ("</td>")
print ("</tr>")
print ("</table>")



# End web page
print (mhl.MyHtmlBottom())