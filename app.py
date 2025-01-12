import sqlite3
from flask import Flask, render_template, redirect, url_for, request, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tajnebardzo'

db_path = 'plan_lekcji.db'

def wykonaj_zapytanie(query, args=(), jeden=False):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(query, args)
    wynik = cursor.fetchall()
    conn.commit()
    conn.close()
    return (wynik[0] if wynik else None) if jeden else wynik

def init_db():
    wykonaj_zapytanie('''CREATE TABLE IF NOT EXISTS uzytkownicy (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nazwa_uzytkownika TEXT UNIQUE NOT NULL,
                        haslo TEXT NOT NULL,
                        czy_admin INTEGER NOT NULL DEFAULT 0
                     )''')
    wykonaj_zapytanie('''CREATE TABLE IF NOT EXISTS plan (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        klasa TEXT NOT NULL,
                        dzien TEXT NOT NULL,
                        godzina TEXT NOT NULL,
                        przedmiot TEXT NOT NULL,
                        nauczyciel TEXT NOT NULL
                     )''')
def konflikt():
    konflikty = {}
    for dzien in DAYS:
        for godzina in TIMES:
            nauczyciele_w_godzinie = wykonaj_zapytanie(
                'SELECT nauczyciel FROM plan WHERE dzien = ? AND godzina = ? AND nauczyciel NOT LIKE "-"', (dzien, godzina)
            )
        
            nauczyciele_w_godzinie = [n[0] for n in nauczyciele_w_godzinie]
     
            for nauczyciel in nauczyciele_w_godzinie:
              
                if nauczyciele_w_godzinie.count(nauczyciel) > 1:
                    if dzien not in konflikty:
                        konflikty[dzien] = {}
                    if godzina not in konflikty[dzien]:
                        konflikty[dzien][godzina] = []
                    konflikty[dzien][godzina].append(nauczyciel)
    return konflikty

def stworz_domyslnego_admina():
        haslo_zaszyfrowane = generate_password_hash('admin')
        sprawdzanie = wykonaj_zapytanie('SELECT * FROM uzytkownicy WHERE nazwa_uzytkownika = ?', ('admin',))
        if not sprawdzanie:
            wykonaj_zapytanie('INSERT INTO uzytkownicy (nazwa_uzytkownika, haslo, czy_admin) VALUES (?, ?, ?)',('admin', haslo_zaszyfrowane, 1))
        print("Dodano domyślnego administratora: nazwa_uzytkownika='admin', haslo='admin'")




@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('panel_glowny'))
    return redirect(url_for('logowanie'))

@app.route('/logowanie', methods=['GET', 'POST'])
def logowanie():
    if request.method == 'POST':
        nazwa_uzytkownika = request.form['nazwa_uzytkownika']
        haslo = request.form['haslo']
        
        uzytkownik = wykonaj_zapytanie('SELECT * FROM uzytkownicy WHERE nazwa_uzytkownika = ?', (nazwa_uzytkownika,), jeden=True)
        if uzytkownik:
            haslo_zaszyfrowane = uzytkownik[2]
            if check_password_hash(haslo_zaszyfrowane, haslo):
                session['user_id'] = uzytkownik[0]
                session['czy_admin'] = bool(uzytkownik[3])
                flash('Zalogowano pomyślnie!')
                return redirect(url_for('panel_glowny'))
            else:
                flash('Nieprawidłowe hasło')
        else:
            flash('Użytkownik nie istnieje')
    return render_template('logowanie.html')


@app.route('/rejestracja', methods=['GET', 'POST'])
def rejestracja():
    if request.method == 'POST':
        nazwa_uzytkownika = request.form['nazwa_uzytkownika']
        haslo = request.form['haslo']
        haslo_zaszyfrowane = generate_password_hash(haslo)
        
       
        uzytkownik = wykonaj_zapytanie('SELECT * FROM uzytkownicy WHERE nazwa_uzytkownika = ?', (nazwa_uzytkownika,), jeden=True)
        if uzytkownik:
            flash('Użytkownik o podanej nazwie już istnieje')
        else:
            
            wykonaj_zapytanie('INSERT INTO uzytkownicy (nazwa_uzytkownika, haslo) VALUES (?, ?)', (nazwa_uzytkownika, haslo_zaszyfrowane))
            flash('Rejestracja zakończona sukcesem')
            return redirect(url_for('logowanie'))
    return render_template('rejestracja.html')

@app.route('/panel_glowny', methods=['GET', 'POST'])
def panel_glowny():
    if 'user_id' not in session:
        return redirect(url_for('logowanie'))

    wybrana_klasa = request.form.get('klasa', CLASSES[0]) if request.method == 'POST' else CLASSES[0]
    plan = wykonaj_zapytanie('SELECT * FROM plan WHERE klasa = ?', (wybrana_klasa,))
    konfliktowo = konflikt()


    return render_template('panel_glowny.html', plan=plan, klasy=CLASSES, wybrana_klasa=wybrana_klasa, konflikty=konfliktowo)

@app.route('/admin/edytuj', methods=['GET', 'POST'])
def edytuj_plan():
    if not session.get('czy_admin'):
        return redirect(url_for('panel_glowny'))

    if request.method == 'POST':
        klasa = request.form['klasa']
        dzien = request.form['dzien']
        godzina = request.form['godzina']
        nowy_nauczyciel = request.form['nauczyciel']

        if nowy_nauczyciel == "Brak zajęć":
            nowy_przedmiot = "Brak zajęć"
            nowy_nauczyciel = "-"
        else:
            nauczyciel_przedmiot = {
                "Anna Kowalska": "Matematyka",
                "Jan Nowak": "Język polski",
                "Maria Wiśniewska": "Historia",
                "Tomasz Zieliński": "Przyroda",
                "Ewa Nowak": "WF"
            }
            nowy_przedmiot = nauczyciel_przedmiot.get(nowy_nauczyciel, "")
            

        wykonaj_zapytanie(
            'UPDATE plan SET nauczyciel = ?, przedmiot = ? WHERE klasa = ? AND dzien = ? AND godzina = ?',
            (nowy_nauczyciel, nowy_przedmiot, klasa, dzien, godzina)
        )
        flash('Nauczyciel i przedmiot zostały zaktualizowane')
        return redirect(url_for('edytuj_plan'))

    plan = wykonaj_zapytanie('SELECT * FROM plan')
    dostepni_nauczyciele = {}
    for dzien in DAYS:
        for godzina in TIMES:
            zajeci = wykonaj_zapytanie(
                'SELECT nauczyciel FROM plan WHERE dzien = ? AND godzina = ?', (dzien, godzina)
            )
            zajeci = [n[0] for n in zajeci]
            dostepni_nauczyciele[(dzien, godzina)] = [n for n in TEACHERS if n not in zajeci] + ["Brak zajęć"]
    konfliktowo = konflikt()
    return render_template('edytuj_plan.html', plan=plan, dostepni_nauczyciele=dostepni_nauczyciele, konflikty=konfliktowo)

@app.route('/wyloguj')
def wyloguj():
    session.clear()
    return redirect(url_for('logowanie'))

@app.route('/admin/generuj', methods=['GET', 'POST'])
def generuj_plan():
    if not session.get('czy_admin'):
        return redirect(url_for('panel_glowny'))
    if request.method == 'POST':
        wykonaj_zapytanie('DELETE FROM plan')

        nauczyciel_przedmiot = {
            "Anna Kowalska": "Matematyka",
            "Jan Nowak": "Język polski",
            "Maria Wiśniewska": "Historia",
            "Tomasz Zieliński": "Przyroda",
            "Ewa Nowak": "WF"
        }

        for dzien in DAYS:
            for godzina in TIMES:
                for klasa in CLASSES:
                    przedmiot = SUBJECTS[(hash(klasa + dzien + godzina) % len(SUBJECTS))]
                    for n, p in nauczyciel_przedmiot.items():
                        if p == przedmiot:
                            nauczyciel = n
                            break
                    if nauczyciel:
                        wykonaj_zapytanie('INSERT INTO plan (klasa, dzien, godzina, przedmiot, nauczyciel) VALUES (?, ?, ?, ?, ?)',
                                          (klasa, dzien, godzina, przedmiot, nauczyciel))
        flash('Plan lekcji został wygenerowany pomyślnie')
        return redirect(url_for('panel_glowny'))
    return render_template('generuj.html')

TEACHERS = ["Anna Kowalska", "Jan Nowak", "Maria Wiśniewska", "Tomasz Zieliński", "Ewa Nowak"]
SUBJECTS = ["Matematyka", "Język polski", "Historia", "Przyroda", "WF"]
DAYS = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek"]
TIMES = ["8:00", "9:00", "10:00", "11:00", "12:00"]
CLASSES = ["1A", "2A", "3A"]

if __name__ == '__main__':
    init_db()
    stworz_domyslnego_admina()
    app.run(debug=False)
