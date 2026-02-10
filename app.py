from flask import Flask, abort, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from PIL import Image
import os
from datetime import datetime, timedelta
import utenti_dao, film_dao, proiezioni_dao
import utenti_dao, film_dao, proiezioni_dao, tickets_dao
import sqlite3
from barcode import Code128
from barcode.writer import ImageWriter

# Configurazione upload immagini    
UPLOAD_FOLDER = 'static/images/posters'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SECRET_ADMIN_KEY = 'SONO UN ORGANIZZATORE'
app = Flask(__name__)
app.secret_key = 'chiave_sicura'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



@app.route('/')
def home():
    filter_day   = request.args.get('filter_day')
    filter_genre = request.args.get('filter_genre')
    films        = []

    # Prendo la lista dei generi per popolare il dropdown
    genres = film_dao.get_all_genres()

    if filter_day:
        # se c'è filtro per giorno → prendi solo quelle proiezioni
        rows = proiezioni_dao.get_proiezioni_by_date(filter_day)
        temp = {}
        for r in rows:
            r = dict(r)
            fid = r['film_id']
            # raggruppa per film
            if fid not in temp:
                temp[fid] = {
                    'id':              fid,
                    'title':           r['film_title'],
                    'poster_filename': r['poster_filename'],
                    'duration':        r['duration'],
                    'genre':           r['genre'],
                    'description':     r['description'],
                    'schedule':        { filter_day: [] }
                }
            temp[fid]['schedule'][filter_day].append(r)
        films = list(temp.values())

    else:
        # nessun filtro giorno prima tre giorni
        all_films = film_dao.get_all_films()
        for row in all_films:
            film = dict(row)
            proj_rows = proiezioni_dao.get_proiezioni_by_film(film['id'])
            schedule = {}
            for p in proj_rows:
                p = dict(p)
                schedule.setdefault(p['date'], []).append(p)
            film['schedule'] = schedule
            films.append(film)

    #  Applico il filtro per genere
    if filter_genre:
        filtered = []
        for f in films:
            if f['genre'] == filter_genre:
                filtered.append(f)
        films = filtered
    return render_template('home.html',films=films,filter_day=filter_day,filter_genre=filter_genre,genres=genres)


@app.route('/film/<int:id>')
def film_detail(id):
    film_row = film_dao.get_film_by_id(id)
    if not film_row:
        abort(404)
    film = dict(film_row)
    # Recupero le righe delle proiezioni dal DAO
    projection_rows = proiezioni_dao.get_proiezioni_by_film(id)
    projections = []
    # Itero su ogni riga, converto in dict e aggiungo alla lista
    for row in projection_rows:
        proj_dict = dict(row)
        projections.append(proj_dict)
    return render_template('film_detail.html', film=film, projections=projections)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        fn    = request.form.get('first_name', '').strip()
        ln    = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        pwd   = request.form.get('password', '')

        # Validazione campi obbligatori
        if not fn or not ln or not email or not pwd:
            app.logger.warning("Form inviato con campi mancanti.")
            flash('Tutti i campi sono obbligatori.', 'warning')
            return redirect(url_for('signup'))

        # Validazione formato email
        if '@' not in email or '.' not in email.split('@')[-1]:
            app.logger.warning("Form inviato con email non valida: %s", email)
            flash('Formato email non valido.', 'warning')
            return redirect(url_for('signup'))

        # Hash della password e creazione utente
        pwd_hash = generate_password_hash(pwd)
        is_admin = (request.form.get('secret_key', '') == SECRET_ADMIN_KEY)
        success  = utenti_dao.create_user(fn, ln, email, pwd_hash, is_admin)

        if not success:
            app.logger.warning("Tentativo di registrazione con email già registrata: %s", email)
            flash('Email già registrata.', 'danger')
            return redirect(url_for('signup'))

        app.logger.info("utente iscritto con successo: %s", email)
        flash('Registrazione avvenuta, ora puoi accedere', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        pwd   = request.form.get('password', '').strip()

        # Controllo campi vuoti
        if not email or not pwd:
            app.logger.warning("Login tentato con campi mancanti: email='%s', password fornita=%s", 
                               email, bool(pwd))
            flash('Inserisci sia email che password', 'warning')
            return redirect(url_for('login'))

        # Controllo formato email
        if '@' not in email or email.count('@') != 1:
            app.logger.warning("Login tentato con email non valida: %s", email)
            flash('Formato email non valido', 'warning')
            return redirect(url_for('login'))

        # Verifica credenziali
        user = utenti_dao.get_user_by_email(email)
        if user and check_password_hash(user.password_hash, pwd):
            app.logger.info("Utente autenticato con successo: %s", email)
            # popolo la sessione
            session['user_id']    = user.id
            session['first_name'] = user.first_name
            session['is_admin']   = user.is_admin
            return redirect(url_for('home'))
        else:
            app.logger.warning("Autenticazione fallita per email: %s", email)
            flash('Credenziali non valide', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))



@app.route('/add_projection', methods=['GET','POST'])
def add_projection_select():
    if not session.get('is_admin'):
        flash('Accesso negato','danger'); return redirect(url_for('home'))
    if request.method=='POST':
        film_id = request.form.get('existing_film_id')
        if not film_id:
            flash('Devi selezionare un film','warning')
            return redirect(url_for('add_projection_select'))
        return redirect(url_for('add_projection_form', film_id=film_id))
    #Recupero le righe dal DAO
    film_rows = proiezioni_dao.get_films_with_proiezioni()
    films = []
    #Itero su ogni riga, converto in dict e la aggiunge
    for f in film_rows:
        film_dict = dict(f)
        films.append(film_dict)

    return render_template('add_projection_select.html', films=films)


@app.route('/add_projection/<int:film_id>', methods=['GET','POST'])
def add_projection_form(film_id):
    if not session.get('is_admin'):
        flash('Accesso negato','danger')
        return redirect(url_for('home'))

    film_row = film_dao.get_film_by_id(film_id)
    if not film_row:
        flash('Film non trovato','danger')
        return redirect(url_for('add_projection'))
    film = dict(film_row)

    fixed_days = ['2025-07-14','2025-07-15','2025-07-16','2025-07-17','2025-07-18','2025-07-19','2025-07-20']

    if request.method == 'POST':
        date = request.form.get('date')
        time = request.form.get('time')
        sala = request.form.get('sala')
        if not (date and time and sala):
            flash('Compila tutti i campi','warning')
            return redirect(url_for('add_projection_form', film_id=film_id))

        # Controllo sovrapposizione
        existing = proiezioni_dao.get_proiezioni_on_date_sala(date, sala)
        new_start = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        new_end   = new_start + timedelta(minutes=int(film['duration']))
        for r in existing:
            r = dict(r)
            exist_start = datetime.strptime(f"{date} {r['start_time']}", "%Y-%m-%d %H:%M")
            exist_end   = exist_start + timedelta(minutes=int(r['duration']))
            # se gli intervalli si intersecano
            if new_start < exist_end and exist_start < new_end:
                flash(f"La proiezione si sovrappone a '{r['film_title']}' "f"delle ore {r['start_time']}",'danger')
                return redirect(url_for('add_projection_form', film_id=film_id))

        # Inserisco la nuova proiezione
        proiezioni_dao.add_proiezione({
            'film_id':    film_id,
            'date':       date,
            'time':       time,
            'sala':       sala,
            'creator_id': session['user_id']
        })
        flash('Proiezione aggiunta con successo','success')
        return redirect(url_for('manage_projections'))

    return render_template('add_projection_form.html',film=film,fixed_days=fixed_days)


@app.route('/manage_projections')
def manage_projections():
    if not session.get('is_admin'):
        flash('Accesso negato', 'danger')
        return redirect(url_for('home'))

    filter_day  = request.args.get('filter_day')
    filter_sala = request.args.get('filter_sala')

    if filter_day and filter_sala:
        rows = proiezioni_dao.get_proiezioni_by_date_and_sala(filter_day, filter_sala)
    elif filter_day:
        rows = proiezioni_dao.get_proiezioni_by_date(filter_day)
    elif filter_sala:
        rows = proiezioni_dao.get_proiezioni_by_sala(filter_sala)
    else:
        rows = proiezioni_dao.get_all_proiezioni()

    proiezioni = []
    for r in rows:
        p = dict(r)
        # se ci sono 0 biglietti venduti allora can_modify
        normal = tickets_dao.count_tickets_by_category(p['id'], 'Normale')
        vip    = tickets_dao.count_tickets_by_category(p['id'], 'VIP')
        p['can_modify'] = (normal + vip) == 0
        proiezioni.append(p)

    date_labels = {
        '2025-07-14': 'Lunedì 14‑7', '2025-07-15': 'Martedì 15‑7',
        '2025-07-16': 'Mercoledì 16‑7','2025-07-17': 'Giovedì 17‑7',
        '2025-07-18': 'Venerdì 18‑7','2025-07-19': 'Sabato 19‑7',
        '2025-07-20': 'Domenica 20‑7'
    }
    return render_template('proiezioni.html',proiezioni=proiezioni,filter_day=filter_day,filter_sala=filter_sala,date_labels=date_labels)


@app.route('/edit_projection/<int:id>', methods=['GET','POST'])
def edit_projection(id):
    if not session.get('is_admin'):
        flash('Accesso negato', 'danger')
        return redirect(url_for('home'))

    proj = proiezioni_dao.get_proiezione(id)
    if not proj:
        flash('Proiezione non trovata', 'danger')
        return redirect(url_for('manage_projections'))

    projection = dict(proj)
    film = dict(film_dao.get_film_by_id(projection['film_id']))

    if request.method == 'POST':
        # raccolta dati da form
        title       = request.form.get('title', '').strip()
        duration    = request.form.get('duration', '').strip()
        genre       = request.form.get('genre', '').strip()
        description = request.form.get('description', '').strip()
        date        = request.form.get('date', '').strip()
        time        = request.form.get('time', '').strip()
        sala        = request.form.get('sala', '').strip()

        # VALIDAZIONE CAMPI FILM 
        if not title or not duration or not genre or not description:
            app.logger.warning("Form inviato con campi dei film mancanti: %s, %s, %s, %s",title, duration, genre, description)
            flash('Tutti i dati del film sono obbligatori', 'warning')
            return redirect(url_for('edit_projection', id=id))

        if not duration.isdigit() or int(duration) <= 0:
            app.logger.warning("Form inviato con durata non valida: %s", duration)
            flash('Durata non valida', 'warning')
            return redirect(url_for('edit_projection', id=id))

        # VALIDAZIONE CAMPI PROIEZIONE 
        if not date or not time or not sala:
            app.logger.warning("Form inviato con campi delle proiezioni mancanti: %s, %s, %s",date, time, sala)
            flash('Data, ora e sala sono obbligatorie', 'warning')
            return redirect(url_for('edit_projection', id=id))

        # GESTIONE FILE IMMAGINE 
        poster_filename = request.form.get('existing_poster', '')
        poster_file = request.files.get('poster')
        if poster_file and allowed_file(poster_file.filename):
            img = Image.open(poster_file.stream)
            POSTER_MAX_WIDTH = 600
            w, h = img.size
            if w > POSTER_MAX_WIDTH:
                img = img.resize((POSTER_MAX_WIDTH, int(h * POSTER_MAX_WIDTH / w)), Image.Resampling.LANCZOS)
            ext = poster_file.filename.rsplit('.', 1)[1].lower()
            ts = int(datetime.now().timestamp())
            username = session.get('first_name', '').lower()
            poster_filename = f"{username}-{ts}.{ext}"
            save_path = f"static/images/posters/{poster_filename}"
            img.save(save_path)

        # CONTROLLO SOVRAPPOSIZIONE
        existing = proiezioni_dao.get_proiezioni_on_date_sala(date, sala)
        new_start = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        new_end   = new_start + timedelta(minutes=int(duration))
        for r in existing:
            if r['id'] == id:
                continue
            exist_start = datetime.strptime(f"{date} {r['start_time']}", "%Y-%m-%d %H:%M")
            exist_end   = exist_start + timedelta(minutes=int(r['duration']))
            if new_start < exist_end and exist_start < new_end:
                app.logger.warning("Overlap on edit: new %s-%s vs existing %s-%s",
                                   new_start, new_end, exist_start, exist_end)
                flash(f"La proiezione si sovrappone a '{r['film_title']}' delle ore {r['start_time']}",'danger')
                return redirect(url_for('edit_projection', id=id))

        # SALVA LE MODIFICHE
        film_dao.update_film(request.form['film_id'], {
            'title':           title,
            'duration':        duration,
            'genre':           genre,
            'description':     description,
            'poster_filename': poster_filename
        })

        proiezioni_dao.update_proiezione(id, {
            'film_id': request.form['film_id'],
            'date':     date,
            'time':     time,
            'sala':     sala
        })

        # nuova proiezione collegata 
        new_day  = request.form.get('new_date')
        new_time = request.form.get('new_time')
        new_room = request.form.get('new_sala')
        if new_day and new_time and new_room:
            proiezioni_dao.add_proiezione({
                'film_id':    request.form['film_id'],
                'date':       new_day,
                'time':       new_time,
                'sala':       new_room,
                'creator_id': session['user_id']
            })

        flash('Film e proiezioni aggiornati con successo', 'success')
        return redirect(url_for('manage_projections'))

    return render_template('edit_projection.html', projection=projection, film=film)


@app.route('/delete_projection/<int:id>')
def delete_projection(id):
    if not session.get('is_admin'):
        flash('Accesso negato','danger'); return redirect(url_for('home'))
    proiezioni_dao.delete_proiezione(id)
    flash('Proiezione eliminata','success')
    return redirect(url_for('manage_projections'))


@app.route('/add_film', methods=['GET', 'POST'])
def add_film():
    # Solo organizzatori
    if not session.get('is_admin'):
        flash('Accesso negato', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        # Raccolgo le proiezioni dal form
        duration_min = int(request.form['duration'])
        planned = []
        for i in range(1, 8):
            d = request.form.get(f'date{i}')
            t = request.form.get(f'time{i}')
            s = request.form.get(f'sala{i}')
            if d and t and s:
                planned.append((d, t, s))

        # Controllo sovrapposizioni
        safe = []
        conflicts = []
        for d, t, s in planned:
            existing = proiezioni_dao.get_proiezioni_on_date_sala(d, s)
            new_start = datetime.strptime(f"{d} {t}", "%Y-%m-%d %H:%M")
            new_end   = new_start + timedelta(minutes=duration_min)
            overlap = False
            for r in existing:
                r = dict(r)
                exist_start = datetime.strptime(f"{d} {r['start_time']}", "%Y-%m-%d %H:%M")
                exist_end   = exist_start + timedelta(minutes=int(r['duration']))
                if new_start < exist_end and exist_start < new_end:
                    overlap = True
                    conflicts.append((r['film_title'], r['start_time'], s))
                    break
            if not overlap:
                safe.append((d, t, s))

        # Se nessuna safe, blocco tutto
        if not safe:
            first = conflicts[0]
            flash(f"Tutte le proiezioni si sovrappongono: "f"prima sovrapposizione con '{first[0]}' alle {first[1]} in sala {first[2]}",'danger')
            return redirect(url_for('add_film'))

        # Upload locandina
        poster_file = request.files.get('poster')
        poster_filename = ''
        if poster_file and allowed_file(poster_file.filename):
            img = Image.open(poster_file.stream)
            MAX_W = 600
            w, h = img.size
            new_h = int(h * MAX_W / w)
            img.thumbnail((MAX_W, new_h), Image.Resampling.LANCZOS)
            ext = poster_file.filename.rsplit('.', 1)[1].lower()
            ts = int(datetime.now().timestamp())
            user = session['first_name'].lower()
            poster_filename = f"{user}-{ts}.{ext}"
            img.save(os.path.join(UPLOAD_FOLDER, poster_filename))

        # Creo il film
        film_data = {
            'title':           request.form['title'],
            'duration':        request.form['duration'],
            'genre':           request.form['genre'],
            'description':     request.form['description'],
            'poster_filename': poster_filename
        }
        film_id = film_dao.add_film(film_data)

        # Inseriscco solo le proiezioni safe
        for d, t, s in safe:
            proiezioni_dao.add_proiezione({
                'film_id':    film_id,
                'date':       d,
                'time':       t,
                'sala':       s,
                'creator_id': session['user_id']
            })

        #  Flash di warning per ogni conflitto
        for title, start, sala in conflicts:
            flash(f"Proiezione saltata per conflitto con '{title}' alle {start} in sala {sala}", 'warning')

        #  Conferma finale
        flash('Film e proiezioni aggiunti con successo', 'success')
        return redirect(url_for('manage_projections'))

    # mostro form
    return render_template('add_film.html')


@app.route('/buy_ticket/<int:proj_id>', methods=['GET','POST'])
def buy_ticket(proj_id):
    # solo utenti loggati non-admin
    if not session.get('user_id'):
        flash('Devi effettuare il login per comprare un biglietto','warning')
        return redirect(url_for('login'))
    if session.get('is_admin'):
        flash('Solo gli spettatori possono acquistare biglietti','danger')
        return redirect(url_for('home'))

    proj = proiezioni_dao.get_proiezione(proj_id)
    if not proj:
        flash('Proiezione non trovata', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        user_id  = session['user_id']
        category = request.form['category']
        quantity = int(request.form['quantity'])

        # Controllo che con quelli già acquistati non si superino i 3 biglietti
        already = tickets_dao.count_user_tickets(user_id, proj_id)
        if already + quantity > 3:
            flash(f'Hai già {already} biglietti, puoi acquistarne al massimo 3 in totale.', 'warning')
            return redirect(url_for('buy_ticket', proj_id=proj_id))
        
        disp_vip=12
        disp_norm=50
        if category == "VIP":
            sold=tickets_dao.count_tickets_by_category(proj_id,category)
            disp_vip=disp_vip-sold
            if disp_vip<quantity:
                flash(f'Biglietti VIP non disponibili, rimangono {disp_vip} biglietti', 'warning')
                return redirect(url_for('buy_ticket', proj_id=proj_id))

        elif category=="Normale":
            sold=tickets_dao.count_tickets_by_category(proj_id,category)
            disp_norm=disp_norm-sold
            if disp_norm<quantity:
                flash(f'Biglietti NORMALI non disponibili, rimangono {disp_norm} biglietti', 'warning')
                return redirect(url_for('buy_ticket', proj_id=proj_id))
        else:
            flash('Categoria non valida', 'danger')
            return redirect(url_for('buy_ticket', proj_id=proj_id))

        # Aggiunge i biglietti
        tickets_dao.add_ticket(user_id, proj_id, category, quantity)
        flash(f'{quantity} biglietto/i acquistato/i con successo!', 'success')
        return redirect(url_for('my_tickets'))

    return render_template('buy_ticket.html', proj=proj)


@app.route('/my_tickets')
def my_tickets():
    if not session.get('user_id'):
        flash('Devi effettuare il login','warning')
        return redirect(url_for('login'))

    raw = tickets_dao.get_tickets_by_user(session['user_id'])
    tickets = []
    now = datetime.now()
    for r in raw:
        t = dict(r)
        # calcolo se modificabile (>8h)
        proj_dt = datetime.strptime(f"{t['date']} {t['time']}", "%Y-%m-%d %H:%M")
        t['can_modify'] = (proj_dt - now) > timedelta(hours=8)
        tickets.append(t)

    return render_template('my_tickets.html', tickets=tickets)


@app.route('/modify_ticket/<int:ticket_id>', methods=['GET','POST'])
def modify_ticket(ticket_id):
    if not session.get('user_id'):
        flash('Devi effettuare il login','warning')
        return redirect(url_for('login'))

    ticket = tickets_dao.get_ticket_by_id(ticket_id)
    if not ticket or ticket['user_id'] != session['user_id']:
        abort(404)

    # proiezione corrente
    proj = proiezioni_dao.get_proiezione(ticket['projection_id'])
    if not proj:
        abort(404)

    # recupero TUTTE le proiezioni dello stesso film
    all_projs = proiezioni_dao.get_proiezioni_by_film(proj['film_id'])
    projections = [dict(p) for p in all_projs]

    proj_dt = datetime.strptime(f"{proj['date']} {proj['time']}", "%Y-%m-%d %H:%M")
    # blocco se mancano meno di 8h
    if (proj_dt - datetime.now()) <= timedelta(hours=8):
        flash('Non puoi più modificare questo biglietto','danger')
        return redirect(url_for('my_tickets'))

    if request.method=='POST':
        if 'update' in request.form:
            # Aggiorna categoria
            new_cat = request.form['category']
            tickets_dao.update_ticket_category(ticket_id, new_cat)
            # Eventuale cambio di proiezione
            new_proj_id = int(request.form['projection_id'])
            if new_proj_id != ticket['projection_id']:
                tickets_dao.update_ticket_projection(ticket_id, new_proj_id)

            flash('Biglietto aggiornato con successo','success')

        elif 'cancel' in request.form:
            tickets_dao.delete_ticket(ticket_id)
            flash('Prenotazione annullata','success')

        return redirect(url_for('my_tickets'))

    return render_template('modify_ticket.html',ticket=dict(ticket),proj=proj,projections=projections)


@app.route('/sales/<int:proj_id>')
def sales(proj_id):
    # Solo organizzatori
    if not session.get('is_admin'):
        flash('Accesso negato', 'danger')
        return redirect(url_for('home'))

    proj = proiezioni_dao.get_proiezione(proj_id)
    if not proj:
        abort(404)

    # Conto i biglietti venduti per categoria
    normal_tickets = tickets_dao.count_tickets_by_category(proj_id, 'Normale')
    vip_tickets    = tickets_dao.count_tickets_by_category(proj_id, 'VIP')
    total_tickets  = normal_tickets + vip_tickets

    # Calcolo percentuale venduti
    TOTAL_SEATS    = 15 + 50  # VIP + Normali
    percent_sold   = int((total_tickets / TOTAL_SEATS) * 100) if TOTAL_SEATS else 0
    
    # Ricavo totale
    total_revenue = normal_tickets * 8 + vip_tickets * 12
    return render_template('sales.html',proj=proj,normal_tickets=normal_tickets,vip_tickets=vip_tickets,total_tickets=total_tickets,total_revenue=total_revenue,percent_sold=percent_sold,total_seats=TOTAL_SEATS)



def generate_barcode_image(ticket_id):
    # creo l’oggetto barcode
    bc = Code128(str(ticket_id), writer=ImageWriter())
    # rendo immagine PIL
    pil_img = bc.render({'module_width': 0.2,'module_height': 15.0,'font_size': 10,'text_distance': 1})
    out_path = f"static/barcodes/{ticket_id}.png"
    pil_img.save(out_path, format='PNG')
    return f"barcodes/{ticket_id}.png"


@app.route('/view_ticket/<int:ticket_id>')
def view_ticket(ticket_id):
    if not session.get('user_id'):
        flash('Devi effettuare il login','warning')
        return redirect(url_for('login'))
    row = tickets_dao.get_ticket_by_id(ticket_id)
    if not row or row['user_id'] != session['user_id']:
        abort(404)
    ticket = dict(row)
    # prendo dati proiezione
    proj = proiezioni_dao.get_proiezione(ticket['projection_id'])
    # genero  il barcode
    barcode_relpath = generate_barcode_image(ticket_id)
    return render_template('view_ticket.html',ticket=ticket,proj=proj,barcode_filename=barcode_relpath)
