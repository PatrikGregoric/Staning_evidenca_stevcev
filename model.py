from pickle import FALSE, TRUE
from bottleext import *
import psycopg2
import hashlib

import os
SERVER_PORT = os.environ.get('BOTTLE_PORT', 8080)
RELOADER = os.environ.get('BOTTLE_RELOADER', True)
DB_PORT = os.environ.get('POSTGRES_PORT', 5432)


from auth_public import *
baza = psycopg2.connect(database=db, host=host, user=user, password=password, port=DB_PORT)
cur=baza.cursor()

@route(/OPB/projektna_naloga/<filename>)
def banana(filename):
    return static_file(filename, root='./views')

def hashGesla(s):
    m = hashlib.sha256()
    m.update(s.encode("utf-8"))
    return m.hexdigest()

def preveri_uporab_ime(ime):
    cur.execute("SELECT uporabnisko_ime FROM oseba")
    a=cur.fetchall()
    for x in a:
        if x[0]==ime:
            return FALSE

def preveri(ime,geslo):
    cur.execute("SELECT uporabnisko_ime , geslo FROM oseba")
    a=cur.fetchall()
    for x in a:
        if x[0]==ime and x[1]==hashGesla(geslo):
            return TRUE

skrivnost="asdfafkl12345"

@get("/")
def prijavno():
    return template("prijava.html",uporabnisko_ime="",geslo="")

@post("/")
def prijava():
    uporabnisko_ime=request.forms.uporabnisko_ime
    geslo=request.forms.geslo
    print(geslo)
    if uporabnisko_ime=="" or geslo=="":
        return template("prijava.html",napaka="Prosimo izpolnite vsa polja",uporabnisko_ime=uporabnisko_ime,geslo=geslo)
    if not preveri(uporabnisko_ime,geslo):
        return template("prijava.html",napaka="Vaše uporabniško ime ali geslo ni pravilno",uporabnisko_ime=uporabnisko_ime,geslo=geslo)
    cur.execute("SELECT id,administrator FROM oseba WHERE uporabnisko_ime=%s",(uporabnisko_ime,))
    a=cur.fetchall()
    response.set_cookie("id_uporabnika",(str(a[0][0])),secret=skrivnost)
    response.set_cookie("administrator",(str(a[0][1])),secret=skrivnost)
    if a[0][1]==1:
        redirect(url("izbira_administrator"))
    else:
        redirect(url("izbira"))

@get('/odjava')
def odjava():
    response.delete_cookie('uporabnisko_ime')
    response.delete_cookie('administrator')
    redirect(url('prijavno'))


@get("/registracija")
def registracija():
    return template("registracija.html",ime="",uporabnisko_ime="",geslo="",tel="")

@post("/registracija")
def registracija():
    ime=request.forms.ime
    uporabnisko_ime=request.forms.uporabnisko_ime
    geslo=request.forms.geslo
    tel=request.forms.tel
    if ime=="" or uporabnisko_ime=="" or geslo=="" or tel=="": 
        return template("registracija.html", napaka="Prosimo izpolnite vsa polja",
        ime=ime, tel=tel, geslo=geslo, uporabnisko_ime=uporabnisko_ime)
    if preveri_uporab_ime(uporabnisko_ime)==FALSE:
        return template("registracija.html", napaka="To uporabniško ime je že zasedeno",
        ime=ime, tel=tel, geslo=geslo, uporabnisko_ime=uporabnisko_ime)
    if "Ž" in uporabnisko_ime or "ž" in uporabnisko_ime or "Š" in uporabnisko_ime or "š" in uporabnisko_ime or "Č" in uporabnisko_ime or "č" in uporabnisko_ime:
        return template("registracija.html", napaka="Uporabniško ime nesme vključevati šumnikov",
        ime=ime, tel=tel, geslo=geslo, uporabnisko_ime=uporabnisko_ime)
    if " " in uporabnisko_ime:
        return template("registracija.html", napaka="Uporabniško ime nesme vključevati presledkov",
        ime=ime, tel=tel, geslo=geslo, uporabnisko_ime=uporabnisko_ime)
    if " " in geslo:
        return template("registracija.html", napaka="Geslo nesme vključevati presledkov",
        ime=ime, tel=tel, geslo=geslo, uporabnisko_ime=uporabnisko_ime)
    if len(str(geslo))<5:
        return template("registracija.html", napaka="Geslo mora vsebovati vsaj pet znakov",
        ime=ime, tel=tel, geslo=geslo, uporabnisko_ime=uporabnisko_ime)
    if len(str(tel))<9 or len(str(tel))>9:
        return template("registracija.html", napaka="Prosimo vnesite resnično telefonsko številko",
        ime=ime, tel=tel, geslo=geslo, uporabnisko_ime=uporabnisko_ime)
    geslo=hashGesla(geslo)

    try:
        cur.execute("""INSERT INTO oseba (ime,telefon,geslo,uporabnisko_ime,administrator) 
            VALUES(%(ime)s,%(tel)s, %(geslo)s, %(uporabnisko_ime)s,%(administrator)s) RETURNING id""", 
            {"ime":ime,"tel":str(tel),"geslo":geslo,"uporabnisko_ime":uporabnisko_ime,"administrator":0})
        id_uporabnika, = cur.fetchone()
        response.set_cookie("id_uporabnika", id_uporabnika, secret=skrivnost)
        response.set_cookie("administrator", 0, secret=skrivnost)
        baza.commit()
    except psycopg2.DatabaseError as ex:
        baza.rollback()
        return template("registracija.html", napaka=f"Prišlo je do napake: {ex}",
        ime=ime, tel=tel, geslo=geslo, uporabnisko_ime=uporabnisko_ime)
    
    redirect(url("izbira"))

@get("/izbira")
def izbira():
    cookie=request.get_cookie("id_uporabnika",secret=skrivnost)
    uporabnik=request.get_cookie("administrator",secret=skrivnost)
    if cookie is None:
        redirect(url('prijavno'))
    return template("izbira.html", uporabnik=uporabnik)

@get("/domov")
def domov():
    cur.execute("SELECT velikost,st_oseb,id_stevca,id_stavbe,vrednost,id_osebe FROM enota")
    a = cur.fetchall()
    cur.execute("SELECT id, ime_stavbe FROM stavba")
    b = cur.fetchall()
    cur.execute("SELECT id, vrsta FROM stevec")
    c = cur.fetchall()
    cur.execute("SELECT id, uporabnisko_ime FROM oseba")
    d = cur.fetchall()
    cookie=request.get_cookie("id_uporabnika",secret=skrivnost)
    if cookie is None:
        redirect(url('prijavno'))
    uporabnik=int(request.get_cookie("administrator",secret=skrivnost))
    return template("domov.html", enota=a, uporabnik=uporabnik, stavbe = dict(b), stevci = dict(c), d=dict(d))

@get("/izbira_administrator")
def izbira_administrator():
    cookie=request.get_cookie("id_uporabnika",secret=skrivnost)
    uporabnik=request.get_cookie("administrator",secret=skrivnost)
    if cookie is None:
        redirect(url('prijavno'))
    if int(uporabnik)==0:
        redirect(url('izbira'))
    return template("izbira_administrator.html", uporabnik=uporabnik)

@get("/dodaj")
def dodaj():
    cur.execute("SELECT id, vrsta FROM stevec")
    a=cur.fetchall()
    cur.execute("SELECT id, ime_stavbe FROM stavba")
    seznam_stavb=cur.fetchall()

    cookie=request.get_cookie("id_uporabnika",secret=skrivnost)
    if cookie is None:
        redirect(url('prijavno'))
    uporabnik=request.get_cookie("administrator",secret=skrivnost)
    print(uporabnik)

    return template("dodaj.html",stevecid=a,stavbaid=seznam_stavb, uporabnik=uporabnik, velikost=0, cena=0, st_oseb=0, stevec="", stavba="")

@post("/dodaj")
def dodaj():
    stevec=request.forms.stevec
    cena=request.forms.cena
    velikost=request.forms.velikost
    st_oseb=request.forms.st_oseb
    stavba=request.forms.stavba

    cur.execute("SELECT * FROM stevec")
    a=cur.fetchall()
    cur.execute("SELECT * FROM stavba")
    b=cur.fetchall()

    for x in a:
        if x[1]==stevec:
            stevec_id=x[0]

    
    for y in b:
        if y[0]==stavba:
            stavba_id=y[1]
            

    stavba="Izberite"
    if getattr(request.forms, "stavba{}".format(stevec)) !="Izberite":
        stavba=getattr(request.forms, "stavba{}".format(stevec))

    cookie=request.get_cookie("id_uporabnika",secret=skrivnost)
    if cookie is None:
        redirect(url('prijavno'))

    uporabnik=int(request.get_cookie("administrator",secret=skrivnost))
    cur.execute("SELECT * FROM stevec")
    a=cur.fetchall()
    cur.execute("SELECT * FROM stavba")
    seznam_stavb=cur.fetchall()

    if stavba=="Izberite" or stevec=="Izberite" or float(cena)==0 or float(velikost)==0 or float(st_oseb)==0:
        return template("dodaj.html",stevecid=a,stavbaid=seznam_stavb,napaka="Prosimo izpolnite vsa polja",uporabnik=uporabnik,stavba=stavba,
        stevec=stevec,cena=cena,velikost=velikost,st_oseb=st_oseb)
    try:
        cur.execute("INSERT INTO enota (id_stevca,vrednost,velikost,st_oseb,id_stavbe,id_osebe) VALUES(%s, %s, %s, %s, %s,%s)",
        (stevec_id,cena,velikost,st_oseb,stavba_id,cookie))
        baza.commit()
    except psycopg2.DatabaseError as ex:
        baza.rollback()
        return template("dodaj.html",stevecid=a,stavbaid=seznam_stavb,napaka=f"Prišlo je do napake: {ex}",uporabnik=uporabnik,stavba=stavba,
        stevec=stevec,cena=cena,velikost=velikost,st_oseb=st_oseb)
    if uporabnik==1:
        redirect(url("izbira_administrator"))
    if uporabnik==0:
        redirect(url("izbira"))



@get("/dodaj_stavbo")
def dodaj_stavbo():
    cookie=request.get_cookie("id_uporabnika",secret=skrivnost)
    uporabnik=request.get_cookie("administrator",secret=skrivnost)
    if cookie is None:
        redirect(url('prijavno'))
    if int(uporabnik)==0:
        redirect(url('izbira'))
    return template("dodaj_stavbo.html", dodana_stavba="")

@post("/dodaj_stavbo")
def dodaj_stavbo():
    stavba=request.forms.dodana_stavba
    cur.execute("SELECT * FROM stavba")
    a=cur.fetchall()
    for x in a:
        if x[0]==stavba:
            return template("dodaj_stavbo.html",napaka="Ta stavba že obstaja", dodana_stavba=stavba) 
    
    if stavba=="":
        return template("dodaj_stavbo.html",napaka="Prosimo izpolnite vsa polja", dodana_stavba=stavba)

    if "Ž" in stavba or "ž" in stavba or "Š" in stavba or "š" in stavba or "Č" in stavba or "č" in stavba:
        return template("dodaj_stavbo.html", napaka="Ime stavbe nesme vključevati šumnikov", dodana_stavba=stavba)

    try:
        cur.execute("""INSERT INTO stavba VALUES(%(stavba)s) RETURNING ID""",
        {"stavba":stavba})
        baza.commit()
    except psycopg2.DatabaseError as ex:
        baza.rollback()
        return template("dodaj_stavbo.html",napaka=f"Prišlo je do napake: {ex}",
        dodana_stavba=stavba)
    
    redirect(url("izbira_administrator"))

@get("/dodaj_administratorja")
def dodaj_administratorja():
    cookie=request.get_cookie("id_uporabnika",secret=skrivnost)
    uporabnik=request.get_cookie("administrator",secret=skrivnost)
    if cookie is None:
        redirect(url('prijavno'))
    if int(uporabnik)==0:
        redirect(url('izbira'))
    
    cur.execute("SELECT uporabnisko_ime FROM oseba WHERE administrator=0")
    a=cur.fetchall()
    return template("dodaj_administratorja.html",seznam_oseb=a,oseba="")

@post("/dodaj_administratorja")
def dodaj_administratorja():
    oseba=request.forms.oseba
    cur.execute("SELECT uporabnisko_ime FROM oseba WHERE administrator=0")
    a=cur.fetchall()
    try:
        cur.execute("UPDATE oseba SET administrator = 1 WHERE uporabnisko_ime = %s",(oseba,))
        baza.commit()
    except psycopg2.DatabaseError as ex:
        baza.rollback()
        return template("dodaj_administratorja.html",seznam_oseb=a, napaka=f"Prišlo je do napake: {ex}",
        oseba=oseba)
        
    redirect(url("izbira_administrator"))

@get("/dodaj_stevec")
def dodaj_stevec():
    cookie=request.get_cookie("id_uporabnika",secret=skrivnost)
    uporabnik=request.get_cookie("administrator",secret=skrivnost)
    if cookie is None:
        redirect(url('prijavno'))
    if int(uporabnik)==0:
        redirect(url('izbira'))
    return template("dodaj_stevec.html", dodan_stevec="")

@post("/dodaj_stevec")
def dodaj_stevec():
    stevec=request.forms.dodan_stevec
    cur.execute("SELECT * FROM stevec")
    a=cur.fetchall()
    for x in a:
        if x[1]==stevec:
            return template("dodaj_stevec.html",napaka="Ta števec že obstaja", dodan_stevec=stevec) 
    
    if stevec=="":
        return template("dodaj_stevec.html",napaka="Prosimo izpolnite vsa polja", dodan_stevec=stevec)

    if "Ž" in stevec or "ž" in stevec or "Š" in stevec or "š" in stevec or "Č" in stevec or "č" in stevec:
        return template("dodaj_stevec.html", napaka="Ime števca nesme vključevati šumnikov", dodan_stevec=stevec)

    try:
        cur.execute("""INSERT INTO stevec (vrsta) VALUES(%(stevec)s)""",
        {"stevec": stevec})
        baza.commit()
    except psycopg2.DatabaseError as ex:
        baza.rollback()
        return template("dodaj_stevec.html",napaka=f"Prišlo je do napake: {ex}",
        dodan_stevec=stevec)
    
    redirect(url("izbira_administrator"))



run(host="localhost", port=SERVER_PORT, reloader=RELOADER)