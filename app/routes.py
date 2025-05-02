import os
import sqlite3
import subprocess
import sys
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from io import BytesIO
import csv
from flask import send_file
from io import StringIO, BytesIO
import folium
from folium.plugins import HeatMap
from folium.plugins import MarkerCluster
import geopandas as gpd
import pandas as pd
import json
from app.conformita_utils import carica_etichette, confronta_tutti
from branca.colormap import linear

main = Blueprint("main", __name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "instance", "classificazioni.db")
IMG_DIR = os.path.join(BASE_DIR, "..", "data", "raw", "screenshots")
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/classifica", methods=["GET", "POST"])
def classifica():
    colori_path = os.path.join(BASE_DIR, "..", "instance", "etichette_colori.json")
    if os.path.exists(colori_path):
        with open(colori_path, "r", encoding="utf-8") as f:
            colori = json.load(f)
    else:
        colori = {}

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if request.method == "POST":
        # Aggiunta nuova etichetta
        if "nuova_etichetta" in request.form:
            nome = request.form["nuova_etichetta"].strip()
            descrizione = request.form["descrizione"].strip()
            if nome:
                try:
                    cur.execute(
                        "INSERT INTO etichette (nome, descrizione) VALUES (?, ?)",
                        (nome, descrizione),
                    )
                    conn.commit()
                    flash(f"Etichetta '{nome}' creata.", "success")
                except sqlite3.IntegrityError:
                    flash(f"L'etichetta '{nome}' esiste già.", "warning")
            return redirect(url_for("main.classifica"))

        # Etichettatura immagine
        elif "etichetta" in request.form:
            nome_file = request.form["nome_file"]
            etichetta = request.form["etichetta"]
            annotatore = request.form["annotatore"]
            session["annotatore"] = annotatore
            timestamp = datetime.now().isoformat()
            path = os.path.relpath(os.path.join("data/raw/screenshots", nome_file))

            cur.execute(
                """
                INSERT INTO immagini (nome_file, path, etichetta_utente, annotatore, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """,
                (nome_file, path, etichetta, annotatore, timestamp),
            )

            conn.commit()
            flash(f"Etichetta '{etichetta}' salvata per {nome_file}.", "success")
            return redirect(url_for("main.classifica"))

        # Rinomina etichetta
        elif "rinomina" in request.form:
            id_etichetta = request.form["id"]
            nuovo_nome = request.form["nome_mod"].strip()
            nuova_descrizione = request.form["descrizione_mod"].strip()
            try:
                cur.execute(
                    "UPDATE etichette SET nome = ?, descrizione = ? WHERE id = ?",
                    (nuovo_nome, nuova_descrizione, id_etichetta),
                )
                conn.commit()
                flash("Etichetta aggiornata con successo.", "success")
            except Exception as e:
                flash(f"Errore aggiornamento etichetta: {e}", "danger")
            return redirect(url_for("main.classifica"))

        # Salvataggio colori
        elif "salva_colori" in request.form:
            for key, value in request.form.items():
                if key.startswith("colore_"):
                    etichetta = key.replace("colore_", "")
                    colori[etichetta] = value.strip()
            with open(colori_path, "w", encoding="utf-8") as f:
                json.dump(colori, f, indent=2)
            flash("Colori aggiornati con successo!", "success")
            return redirect(url_for("main.classifica"))

    # Recupera tutte le etichette
    cur.execute("SELECT id, nome, descrizione FROM etichette ORDER BY nome")
    etichette = cur.fetchall()

    # Elenco immagini già etichettate
    cur.execute("SELECT nome_file FROM immagini")
    gia_etichettate = [row[0] for row in cur.fetchall()]

    # Trova immagine da etichettare
    tutte = [
        f for f in os.listdir(IMG_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    da_etichettare = [f for f in tutte if f not in gia_etichettate]
    immagine_corrente = da_etichettare[0] if da_etichettare else None

    conn.close()

    return render_template(
        "classifica.html",
        immagine=immagine_corrente,
        etichette=etichette,
        annotatore=session.get("annotatore", ""),
        colori=colori,
    )


@main.route("/etichette", methods=["GET", "POST"])
def etichette():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if request.method == "POST" and "nuova_etichetta" in request.form:
        nome = request.form["nuova_etichetta"].strip()
        descrizione = request.form["descrizione"].strip()
        if nome:
            try:
                cur.execute(
                    "INSERT INTO etichette (nome, descrizione) VALUES (?, ?)",
                    (nome, descrizione),
                )
                conn.commit()
                flash(f"Etichetta '{nome}' aggiunta con successo.", "success")
            except sqlite3.IntegrityError:
                flash(f"L'etichetta '{nome}' esiste già.", "warning")

    if request.method == "POST" and "rinomina" in request.form:
        id_etichetta = request.form["id"]
        nuovo_nome = request.form["nome_mod"]
        nuova_descrizione = request.form["descrizione_mod"]
        try:
            cur.execute(
                "UPDATE etichette SET nome = ?, descrizione = ? WHERE id = ?",
                (nuovo_nome, nuova_descrizione, id_etichetta),
            )
            conn.commit()
            flash("Etichetta aggiornata.", "success")
        except Exception as e:
            flash(f"Errore aggiornamento: {e}", "danger")

    cur.execute("SELECT id, nome, descrizione FROM etichette ORDER BY nome")
    etichette = cur.fetchall()
    conn.close()
    return render_template("etichette.html", etichette=etichette)


@main.route("/conformita", methods=["GET", "POST"])
def conformita():
    risultati = []
    etichette = carica_etichette()
    selezionata = ""
    threshold = 35
    limit = 100

    if request.method == "POST":
        selezionata = request.form.get("etichetta")
        threshold = int(request.form.get("threshold", 35))
        limit = int(request.form.get("limit", 100))
        risultati = confronta_tutti(selezionata, threshold, limit)

    return render_template(
        "conformita.html",
        risultati=risultati,
        etichette=etichette,
        selezionata=selezionata,
        threshold=threshold,
        limit=limit,
    )


@main.route("/dashboard")
def dashboard():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Carica tutte le etichette
    cur.execute("SELECT nome FROM etichette ORDER BY nome")
    etichette = [row[0] for row in cur.fetchall()]

    # Dizionario etichetta → immagini validate
    immagini_per_etichetta = {}
    for etichetta in etichette:
        cur.execute(
            """
            SELECT nome_file
            FROM immagini
            WHERE etichetta_utente = ?
              AND etichetta_modello_originale IS NOT NULL
              AND stato_validazione IN ('confermato', 'corretto')
            ORDER BY timestamp DESC
        """,
            (etichetta,),
        )
        immagini_per_etichetta[etichetta] = [row[0] for row in cur.fetchall()]

    # Totale immagini
    cur.execute("SELECT COUNT(*) FROM immagini")
    totale = cur.fetchone()[0]

    # Conteggi per validazione
    cur.execute("SELECT COUNT(*) FROM immagini WHERE stato_validazione = 'confermato'")
    confermate = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM immagini WHERE stato_validazione = 'corretto'")
    corrette = cur.fetchone()[0]

    viste = confermate + corrette

    perc_confermate = round((confermate / totale) * 100, 2) if totale else 0
    perc_corretta = round((corrette / totale) * 100, 2) if totale else 0
    perc_viste = round((viste / totale) * 100, 2) if totale else 0

    conn.close()

    return render_template(
        "dashboard.html",
        immagini_per_etichetta=immagini_per_etichetta,
        totale=totale,
        perc_confermate=perc_confermate,
        perc_corretta=perc_corretta,
        perc_viste=perc_viste,
    )


@main.route("/sqladmin", methods=["GET", "POST"])
def sqladmin():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    result = []
    columns = []
    error = ""
    sql = ""
    selected_table = request.args.get("table")

    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabelle = [row[0] for row in cur.fetchall()]

    if request.method == "POST":
        sql = request.form.get("sql_query", "").strip()
        session["last_sql"] = sql  # Memorizza la query per l'esportazione CSV
        try:
            cur.execute(sql)
            if sql.lower().startswith("select"):
                result = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
            else:
                conn.commit()
                flash("Query eseguita con successo.", "success")
        except Exception as e:
            error = str(e)

    conn.close()

    return render_template(
        "sqladmin.html",
        sql=sql,
        result=result,
        columns=columns,
        error=error,
        tabelle=tabelle,
    )


@main.route("/export_csv")
def export_csv():
    sql = session.get("last_sql", "")
    if not sql.lower().startswith("select"):
        flash("Solo query SELECT possono essere esportate.", "warning")
        return redirect(url_for("main.sqladmin"))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        headers = [description[0] for description in cur.description]

        # Genera CSV in memoria (in testo)
        csv_text = StringIO()
        writer = csv.writer(csv_text)
        writer.writerow(headers)
        writer.writerows(rows)

        # Codifica in bytes
        csv_bytes = BytesIO(csv_text.getvalue().encode("utf-8"))
        csv_bytes.seek(0)

        # Nome file con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"query_result_{timestamp}.csv"

        return send_file(
            csv_bytes, mimetype="text/csv", as_attachment=True, download_name=filename
        )

    except Exception as e:
        flash(f"Errore nell'esportazione CSV: {e}", "danger")
        return redirect(url_for("main.sqladmin"))
    finally:
        conn.close()


@main.route("/modello", methods=["GET", "POST"])
def modello():
    status_message = None
    output_text = None
    error_text = None

    if request.method == "POST":
        ml_dir = os.path.join(PROJECT_ROOT, "app", "ml")

        if "sync" in request.form:
            script_path = os.path.join(ml_dir, "sincronizza_immagini.py")
            action = "Sincronizzazione"
        elif "train" in request.form:
            script_path = os.path.join(ml_dir, "train_model.py")
            action = "Addestramento"
        elif "predict" in request.form:
            script_path = os.path.join(ml_dir, "predict.py")
            action = "Predizione"
        else:
            return redirect(url_for("main.modello"))

        try:
            result = subprocess.run(
                [sys.executable, script_path], capture_output=True, text=True
            )
            output_text = result.stdout
            error_text = result.stderr
            if result.returncode == 0:
                status_message = f"{action} completato con successo."
            else:
                status_message = f"Errore durante {action.lower()}."
        except Exception as e:
            status_message = f"Errore nell'esecuzione dello script: {e}"
            error_text = str(e)

    return render_template(
        "modello.html",
        status_message=status_message,
        output_text=output_text,
        error_text=error_text,
    )


# IMPORTIAMO LE FUNZIONI DI VALUTAZIONE
from tools.valuta_modello import valuta_modello
from tools.valuta_sift import valuta_accuracy_sift


# IMPORTIAMO LE FUNZIONI
from tools.valuta_modello import valuta_modello
from tools.valuta_sift import valuta_accuracy_sift
from tools.confronta_modelli import genera_grafico_confronto


@main.route("/validazione", methods=["GET", "POST"])
def validazione():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Variabili per mostrare risultati
    accuracy_modello = None
    report_modello = None
    accuracy_sift = None
    grafico_confronto_path = None

    # Gestione POST
    if request.method == "POST":
        if "set_threshold" in request.form:
            nuovo_threshold = int(request.form.get("new_threshold", 30))
            cur.execute(
                """
                UPDATE immagini
                SET conforme_sift = CASE
                    WHEN match_sift IS NOT NULL AND match_sift > ? THEN 1
                    ELSE 0
                END,
                threshold_sift = ?,
                timestamp_sift = ?
                WHERE match_sift IS NOT NULL
            """,
                (nuovo_threshold, nuovo_threshold, datetime.utcnow().isoformat()),
            )
            conn.commit()

        elif "conferma_o_cambia" in request.form:
            image_id = request.form.get("image_id")
            new_label = request.form.get("new_label")

            # Recupera l'etichetta predetta
            cur.execute(
                "SELECT etichetta_modello FROM immagini WHERE id = ?", (image_id,)
            )
            row = cur.fetchone()
            etichetta_modello = row[0] if row else None

            if new_label == etichetta_modello:
                # Conferma dell’etichetta predetta
                cur.execute(
                    """
                    UPDATE immagini
                    SET etichetta_utente = etichetta_modello,
                        stato_validazione = 'confermato'
                    WHERE id = ?
                """,
                    (image_id,),
                )
            else:
                # Correzione rispetto all’etichetta proposta
                cur.execute(
                    """
                    UPDATE immagini
                    SET etichetta_utente = ?,
                        stato_validazione = 'corretto'
                    WHERE id = ?
                """,
                    (new_label, image_id),
                )

            conn.commit()

        elif "valuta_modello" in request.form:
            accuracy_modello, report_modello = valuta_modello()

        elif "valuta_sift" in request.form:
            accuracy_sift = valuta_accuracy_sift()

        elif "confronta_modelli" in request.form:
            grafico_confronto_path = genera_grafico_confronto()

    # Caricamento etichette
    cur.execute("SELECT nome FROM etichette ORDER BY nome")
    etichette = [row[0] for row in cur.fetchall()]

    # Paginazione e filtro
    page = int(request.args.get("page", 1))
    label_filter = request.args.get("label_filter", "").strip()
    per_page = 20
    offset = (page - 1) * per_page

    if label_filter:
        cur.execute(
            """
            SELECT id, nome_file, path, etichetta_modello, confidence, conforme_sift, threshold_sift, match_sift
            FROM immagini
            WHERE etichetta_modello = ? AND etichetta_utente IS NULL
            LIMIT ? OFFSET ?
        """,
            (label_filter, per_page, offset),
        )
        immagini = cur.fetchall()

        cur.execute(
            """
            SELECT COUNT(*) FROM immagini
            WHERE etichetta_modello = ? AND etichetta_utente IS NULL
        """,
            (label_filter,),
        )
        row = cur.fetchone()
        total_images = row[0] if row else 0
    else:
        cur.execute(
            """
            SELECT id, nome_file, path, etichetta_modello, confidence, conforme_sift, threshold_sift, match_sift
            FROM immagini
            WHERE etichetta_modello IS NOT NULL AND etichetta_utente IS NULL
            LIMIT ? OFFSET ?
        """,
            (per_page, offset),
        )
        immagini = cur.fetchall()

        cur.execute(
            """
            SELECT COUNT(*) FROM immagini
            WHERE etichetta_modello IS NOT NULL AND etichetta_utente IS NULL
        """
        )
        row = cur.fetchone()
        total_images = row[0] if row else 0

    total_pages = (total_images + per_page - 1) // per_page

    conn.close()

    return render_template(
        "validazione.html",
        immagini=immagini,
        etichette=etichette,
        page=page,
        total_pages=total_pages,
        label_filter=label_filter,
        accuracy_modello=accuracy_modello,
        report_modello=report_modello,
        accuracy_sift=accuracy_sift,
        grafico_confronto_path=grafico_confronto_path,
    )


from folium.plugins import MarkerCluster


@main.route("/bi")
def bi():
    return render_template("bi.html")


import folium


@main.route("/bi/livello/<livello>", methods=["POST"])
def bi_livello(livello):
    import geopandas as gpd
    import pandas as pd
    import json
    import os
    import sqlite3
    import folium
    from branca.colormap import linear
    from flask import request, redirect, url_for, send_from_directory, render_template_string

    colore_path = os.path.join(BASE_DIR, "..", "instance", "etichette_colori.json")

    colori = {}
    if os.path.exists(colore_path):
        with open(colore_path, "r", encoding="utf-8") as f:
            colori = json.load(f)

    target_etichetta = request.form.get("etichetta", "design system").strip().lower()
    azione = request.form.get("azione", "genera")

    livelli_geo = {
        "comuni": {
            "geojson": "limits_IT_municipalities.geojson",
            "merge_key": "com_istat_code",
            "group_by": "istat",
            "label_key": "comune",
            "filename": "bi_comuni.html",
        },
        "province": {
            "geojson": "limits_IT_provinces.geojson",
            "merge_key": "prov_acr",
            "group_by": "provincia",
            "label_key": "prov_name",
            "filename": "bi_province.html",
        },
        "regioni": {
            "geojson": "limits_IT_regions.geojson",
            "merge_key": "reg_name",
            "group_by": "regione",
            "label_key": "reg_name",
            "filename": "bi_regioni.html",
        },
    }

    if livello not in livelli_geo:
        return "Livello non valido", 400

    cfg = livelli_geo[livello]
    output_map_path = os.path.join(BASE_DIR, "static", "bi", cfg["filename"])

    conn = sqlite3.connect(DB_PATH)
    full_df = pd.read_sql_query("SELECT * FROM immagini", conn)
    conn.close()

    # Statistiche globali
    totale = len(full_df)
    viste = full_df[full_df['etichetta_utente'].notnull()]
    confermate = full_df[full_df['etichetta_modello'] == full_df['etichetta_utente']]
    smentite = full_df[(full_df['etichetta_utente'].notnull()) & (full_df['etichetta_modello'] != full_df['etichetta_utente'])]
    perc_viste = len(viste) / totale * 100 if totale else 0
    perc_confermate = len(confermate) / totale * 100 if totale else 0
    perc_smentite = len(smentite) / totale * 100 if totale else 0

    # Etichette globali dinamiche
    dist = full_df['etichetta_modello'].str.lower().value_counts(normalize=True) * 100
    top_labels = dist.head(3).to_dict()
    top_labels_str = ", ".join([f'"{k}" ({v:.1f}%)' for k, v in top_labels.items()])

    # Analisi per regione
    reg_df = full_df[full_df['regione'].notnull()].copy()
    reg_df["regione"] = reg_df["regione"].str.strip().str.upper()
    reg_df["etichetta_modello"] = reg_df["etichetta_modello"].str.lower().str.strip()

    by_regione = reg_df.groupby("regione")
    regioni_conformi = by_regione.apply(lambda g: (g['etichetta_modello'] == target_etichetta).mean() * 100).reset_index(name="percentuale")
    regione_max = regioni_conformi.loc[regioni_conformi["percentuale"].idxmax()]['regione'] if not regioni_conformi.empty else "-"
    regione_min = regioni_conformi.loc[regioni_conformi["percentuale"].idxmin()]['regione'] if not regioni_conformi.empty else "-"

    altro = reg_df[reg_df["etichetta_modello"] == "altro"].groupby("regione").size()
    regione_altro = altro.idxmax() if not altro.empty else "-"

    top_reg = reg_df.groupby(["regione", "etichetta_modello"]).size().reset_index(name="count")
    top_per_label = top_reg.loc[top_reg.groupby("etichetta_modello")["count"].idxmax()]
    regione_top_per_label = {row['etichetta_modello']: row['regione'] for _, row in top_per_label.iterrows()}

    frammentata = reg_df.groupby("regione")["etichetta_modello"].nunique()
    regione_frammentata = frammentata.idxmax() if not frammentata.empty else "-"

    prov_df = full_df[full_df['provincia'].notnull()].copy()
    prov_df["provincia"] = prov_df["provincia"].str.strip().str.upper()
    prov_df["etichetta_modello"] = prov_df["etichetta_modello"].str.lower().str.strip()
    by_prov = prov_df.groupby("provincia")
    prov_conformi = by_prov.apply(lambda g: (g['etichetta_modello'] == target_etichetta).mean() * 100).reset_index(name="percentuale")
    provincia_max = prov_conformi.loc[prov_conformi["percentuale"].idxmax()]["provincia"] if not prov_conformi.empty else "-"
    provincia_min = prov_conformi.loc[prov_conformi["percentuale"].idxmin()]["provincia"] if not prov_conformi.empty else "-"

    testo = f"""
    <div class='alert alert-info shadow-sm'>
        Dall'analisi di <strong>{totale}</strong> immagini classificate emerge che il <strong>{perc_confermate:.1f}%</strong> delle previsioni è stato confermato dagli utenti, mentre il <strong>{perc_smentite:.1f}%</strong> è stato smentito. Inoltre, il <strong>{perc_viste:.1f}%</strong> delle immagini è stato elaborato manualmente.
        Le etichette più comuni sono: {top_labels_str}.
        La regione più conforme all'etichetta "<strong>{target_etichetta}</strong>" è <strong>{regione_max}</strong>, mentre quella meno conforme è <strong>{regione_min}</strong>. La regione più frammentata per varietà di etichette è <strong>{regione_frammentata}</strong>.
        """

    for et, reg in regione_top_per_label.items():
        if et != "altro":
            testo += f" La regione con più etichette \"{et}\" è <strong>{reg}</strong>."

    testo += f" La provincia più conforme è <strong>{provincia_max}</strong>, quella meno conforme è <strong>{provincia_min}</strong>.</div>"

    if azione == "seleziona" and os.path.exists(output_map_path):
        return render_template_string(testo + f'<iframe src="{{{{ url_for("static", filename="bi/{cfg["filename"]}") }}}}" style="width:100%; height:80vh; border:none;"></iframe>')

    # Proseguimento: caricamento geodati, calcolo percentuali e salvataggio mappa come prima
    geojson_path = os.path.join(BASE_DIR, "..", "app", "static", "geo", cfg["geojson"])

    df = full_df[[cfg['group_by'], 'etichetta_modello']].dropna()
    df.columns = ["area", "etichetta_modello"]
    df["area"] = df["area"].str.strip().str.upper()
    df["etichetta_modello"] = df["etichetta_modello"].str.strip().str.lower()

    totali = df.groupby("area").size().reset_index(name="totale")
    conformi = df[df["etichetta_modello"] == target_etichetta].groupby("area").size().reset_index(name="conformi")
    percentuali = pd.merge(totali, conformi, on="area", how="left").fillna(0)
    percentuali["percentuale"] = (percentuali["conformi"] / percentuali["totale"]) * 100

    geo = gpd.read_file(geojson_path)
    geo = geo.rename(columns={cfg["merge_key"]: "area"})
    geo["area"] = geo["area"].str.strip().str.upper()
    geo["geometry"] = geo["geometry"].simplify(0.001, preserve_topology=True)

    mappa_df = geo.merge(percentuali, on="area", how="left")

    domain_values = sorted(mappa_df["percentuale"].dropna().unique())
    if len(domain_values) < 2:
        domain_values = [0, 100]

    colormap = linear.Greens_09.scale(domain_values[0], domain_values[-1])
    colormap.caption = f"Conformità a '{target_etichetta}' (%)"

    m = folium.Map(location=[42.5, 12.5], zoom_start=6, tiles="cartodb positron")

    for _, row in mappa_df.iterrows():
        area = row["area"]
        percentuale = row["percentuale"]
        label = row.get(cfg["label_key"], area)

        if pd.notna(percentuale):
            colore = colormap(percentuale)
            tooltip_text = f"<b>{label}</b><br>Conformità '{target_etichetta}': {percentuale:.1f}%"
        else:
            colore = "#cccccc"
            tooltip_text = f"<b>{label}</b><br>Nessun dato"

        tooltip = folium.Tooltip(tooltip_text, sticky=True)

        geojson = folium.GeoJson(
            data=row["geometry"].__geo_interface__,
            style_function=lambda feat, colore=colore: {
                "fillColor": colore,
                "color": "black",
                "weight": 0.5,
                "fillOpacity": 0.7,
            },
            tooltip=tooltip,
        )
        geojson.add_to(m)

    colormap.add_to(m)
    os.makedirs(os.path.dirname(output_map_path), exist_ok=True)
    m.save(output_map_path)

    return render_template_string(testo + f'<iframe src="{{{{ url_for("static", filename="bi/{cfg["filename"]}") }}}}" style="width:100%; height:80vh; border:none;"></iframe>')


@main.route("/scraping", methods=["GET", "POST"])
def scraping():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    search_query = request.args.get("search", "").strip()
    page = int(request.args.get("page", 1))
    per_page = 40
    offset = (page - 1) * per_page

    if request.method == "POST":
        if "update_urls" in request.form:
            for key, value in request.form.items():
                if key.startswith("url_"):
                    nome_file = key.split("url_")[1]
                    cursor.execute(
                        "UPDATE immagini SET sito_web = ? WHERE nome_file = ?",
                        (value.strip(), nome_file),
                    )
            conn.commit()

        elif "start_scraping" in request.form:
            limit = int(request.form.get("scrape_limit"))
            conn.close()
            esegui_scraping(limit)
            return redirect(url_for("main.scraping"))

    if search_query:
        cursor.execute(
            "SELECT COUNT(*) FROM immagini WHERE nome_file LIKE ? OR sito_web LIKE ?",
            (f"%{search_query}%", f"%{search_query}%"),
        )
        total = cursor.fetchone()[0]
        cursor.execute(
            "SELECT nome_file, sito_web FROM immagini WHERE nome_file LIKE ? OR sito_web LIKE ? ORDER BY nome_file ASC LIMIT ? OFFSET ?",
            (f"%{search_query}%", f"%{search_query}%", per_page, offset),
        )
    else:
        cursor.execute("SELECT COUNT(*) FROM immagini")
        total = cursor.fetchone()[0]
        cursor.execute(
            "SELECT nome_file, sito_web FROM immagini ORDER BY nome_file ASC LIMIT ? OFFSET ?",
            (per_page, offset),
        )

    comuni = cursor.fetchall()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "scraping.html",
        comuni=comuni,
        page=page,
        total_pages=total_pages,
        search_query=search_query,
    )


@main.route("/clusterizza", methods=["GET", "POST"])
def clusterizza():
    from app.ml.unsupervised_clusterizzation import esegui_clusterizzazione
    import random
    from collections import defaultdict
    import numpy as np
    import sqlite3

    output = None
    errore = None
    cluster_samples = []

    # ↪️ Recupera parametri da form o usa default
    eps = float(request.form.get("eps", 2.5)) if request.method == "POST" else 2.5
    min_samples = (
        int(request.form.get("min_samples", 5)) if request.method == "POST" else 5
    )

    labels = None
    if request.method == "POST":
        try:
            labels = esegui_clusterizzazione(eps=eps, min_samples=min_samples)
            output = f"Clusterizzazione completata: {len(set(labels)) - (1 if -1 in labels else 0)} cluster trovati."
        except Exception as e:
            errore = str(e)

    # Carica immagini assegnate a cluster (escludendo outlier)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT cluster_dbscan, nome_file
        FROM immagini
        WHERE cluster_dbscan IS NOT NULL AND cluster_dbscan != -1
    """
    )
    rows = cur.fetchall()
    conn.close()

    # Costruisci dizionario cluster → immagini
    cluster_dict = defaultdict(list)
    for cluster_id, nome_file in rows:
        cluster_dict[cluster_id].append(nome_file)

    # Crea lista: (cluster_id, immagini campione, numero totale)
    cluster_samples = sorted(
        [
            (cid, random.sample(imgs, min(len(imgs), 30)), len(imgs))
            for cid, imgs in cluster_dict.items()
        ],
        key=lambda x: x[2],
        reverse=True,
    )

    # Conta gli outlier
    if labels is not None:
        num_outliers = int(np.count_nonzero(labels == -1))
    else:
        num_outliers = 0

    return render_template(
        "unsupervised_cluster.html",
        cluster_samples=cluster_samples,
        num_cluster=len(cluster_dict),
        num_outliers=num_outliers,
        eps=eps,
        min_samples=min_samples,
        errore=errore,
        output=output,
    )
