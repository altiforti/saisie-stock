import os
import requests
from flask import Flask, request, jsonify, render_template, send_from_directory
from airtable import Airtable

# Configuration from Environment Variables
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID")
# Table name for stock entries
AIRTABLE_TABLE_NAME = os.environ.get("AIRTABLE_TABLE_NAME", "SAISIE DE LIVRES")
# Field names (ensure these match Airtable exactly)
FIELD_EAN = "EAN"
FIELD_ETAT = "ETAT"
FIELD_RAYON = "RAYON"
FIELD_SOUS_RAYON = "sous rayon"

# --- Airtable Client Initialization ---
try:
    airtable = Airtable(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME, api_key=AIRTABLE_API_KEY)
    # Basic check to see if connection seems okay (will fail later if keys/base/table are wrong)
    print(f"Airtable client initialized for table: {AIRTABLE_TABLE_NAME}")
except Exception as e:
    print(f"Error initializing Airtable client: {e}")
    airtable = None # Ensure airtable is None if init fails

# --- Flask App Initialization ---
app = Flask(__name__, static_folder="static", template_folder="static")

# --- Helper Function to get Airtable Field Options ---

def get_airtable_select_options(table_name, field_name):
    """
    Returns predefined lists for ETAT and RAYON.
    """
    if field_name == FIELD_ETAT:
        print(f"Returning predefined list for ", FIELD_ETAT, " in new order.") # Modifié pour éviter f-string complexe
        return ["EC", "BE", "TB", "CN", "NE"] # Ordre modifié ici
    elif field_name == FIELD_RAYON:
        print(f"Returning predefined list for ", FIELD_RAYON) # Modifié pour éviter f-string complexe
        # Liste fournie par l'utilisateur
        rayons = [
            "psychanalyse", "histoire", "Jeunesse", "psychologie", "Politinternatio", "art",
            "Sciencespol", "poesie", "Sociologie", "Objetscoll", "Cuisine", "Ethnologie",
            "Economie", "Philosophie", "musique", "Mer", "Quesaisje", "Poche",
            "Classiquespoche", "Esoterisme", "Essais", "Bouddhisme", "Religion", "Romans",
            "Bd", "photographie", "Dictionnaire", "critiqlitt", "Scolaire", "educ",
            "pochehistoire", "Poches", "pochessciences", "litterature", "Droit", "sf",
            "archeologie", "Regionalisme", "Medecine", "Animaux", "corresponda",
            "cinémaacteuramér", "style", "musiquechantgroupes", "Ecologiequotid",
            "bienetre", "Communisme", "sexualité", "politiqfra", "Sciences", "judaisme",
            "mondearabe", "romananglaisssol", "erotique", "Biographies", "Geographie",
            "collbouquins", "paysmonaco", "spiritualite", "greceantiq", "mythologie",
            "cinessais", "edition", "pleiade", "apprentissageanglais", "ange", "cinema",
            "folklore", "tablactusssol", "Architecture", "theatre", "revueslitt",
            "pedagogie", "tableactu", "medecinenaturelle", "savoirvivre", "paysafrique",
            "aviation", "vitrineregio", "justice", "linguistique", "jeandebonnot",
            "pochepolicier", "romanspolicierbroch", "theologie", "Pressejournalism",
            "biographie", "Sport", "bricolage", "Europe", "nationalisme", "Danse",
            "Techniques", "Espagne", "societe", "anthropologie", "latinpoche", "Jeux",
            "voyage", "femme", "adolescence", "pochepolitique", "autobiographie",
            "Communication", "antiquite", "Concours", "Guides", "algerie", "montagne",
            "lettres", "journauxsouvenirs", "asie", "entreprise", "maternité", "humour",
            "parentalite", "financepublique", "dietetique", "psychiatrie", "ameriquelatine",
            "Prostitution", "Acteurs", "grec", "puericulture", "vitrinefacecaisse",
            "Dictionnaires", "trains", "automoto", "francmaconnerie", "Brocante",
            "fantastique", "media", "Geopolitique", "Societessecretes",
            "francaispouretranger", "langue russe", "paris", "moyen orient", "fantasy",
            "revue philosophie", "pays", "templiers", "manga", "Viesquotidiennes",
            "Botanique", "Vin", "Graphologie", "Afriquedunord", "alchimie",
            "Bellesreliuresromanpop", "Objetscollectimbres", "languarabe",
            "editionoriginale", "methodenicois", "romanpopulaire", "VOalld", "astronomie",
            "philopolitique", "epistemologie", "englishbooks", "methodelangueital",
            "VOangloessais", "romanvoyage", "regionparis", "methodelangueespagnol",
            "champignon", "nature", "vousheros", "def", "Couple", "informatique",
            "Racisme", "biologie", "2dguerre", "DeGaulle", "classiqanglais",
            "sciencespolit", "chimie", "yoga", "methodelangue", "scolaireancien",
            "plantes", "peintresvallotton", "langnissart", "préhistoire",
            "relationsinternational"
        ]
        rayons.sort(key=str.lower) # Tri alphabétique insensible à la casse
        return rayons
    else:
        return []


# --- Flask Routes ---

@app.route("/")
def index():
    """Serves the main HTML page."""
    return render_template("index.html")

@app.route("/static/<path:path>")
def send_static(path):
    """Serves static files (like CSS, JS, images)."""
    if path == "logo.jpeg":
        return send_from_directory("static", path)
    return send_from_directory("static", path)

@app.route("/get_stock_options", methods=["GET"])
def get_stock_options():
    """Endpoint to provide options for dropdowns."""
    try:
        rayon_options = get_airtable_select_options(AIRTABLE_TABLE_NAME, FIELD_RAYON)
        etat_options = get_airtable_select_options(AIRTABLE_TABLE_NAME, FIELD_ETAT)
        return jsonify({
            "rayons": rayon_options,
            "etats": etat_options
        })
    except Exception as e:
        print(f"Error in /get_stock_options: {e}")
        return jsonify({"rayons": [], "etats": ["EC", "BE", "TB", "CN", "NE"]}), 500 # Ordre modifié ici aussi pour le fallback


@app.route("/add_stock_entry", methods=["POST"])
def add_stock_entry():
    """Endpoint to add a new stock entry (EAN + batch info) to Airtable."""
    if not airtable:
        return jsonify({"message": "Erreur: Connexion Airtable non initialisée."}), 500

    data = request.get_json()
    if not data:
        return jsonify({"message": "Erreur: Aucune donnée reçue."}), 400

    ean = data.get("ean")
    rayon = data.get("rayon")
    etat = data.get("etat")
    sous_rayon = data.get("sous_rayon")

    if not ean or not rayon or not etat:
        return jsonify({"message": "Erreur: EAN, Rayon et État sont requis."}), 400

    if not (isinstance(ean, str) and len(ean) == 13 and ean.isdigit()):
         return jsonify({"message": f"Erreur: Format EAN invalide ({ean}). 13 chiffres attendus."}), 400

    record_data = {
        FIELD_EAN: ean,
        FIELD_RAYON: rayon,
        FIELD_ETAT: etat,
    }
    if sous_rayon:
        record_data[FIELD_SOUS_RAYON] = sous_rayon
    
    # Log the exact data being sent to Airtable
    print(f"DEBUG: Attempting to insert into Airtable: {record_data}")

    try:
        created_record = airtable.insert(record_data)
        # Correction de la f-string ici:
        print(f"Airtable record created: {created_record["id"]} for EAN {ean}")
        return jsonify({"message": f"EAN {ean} ajouté avec succès."}), 201

    except Exception as e:
        error_message = str(e)
        print(f"Error adding record to Airtable for EAN {ean}: {error_message}")
        if "NOT_FOUND" in error_message:
             return jsonify({"message": f"Erreur Airtable: Table ou Base non trouvée. Vérifiez la configuration."}), 500
        elif "AUTHENTICATION_REQUIRED" in error_message or "INVALID_API_KEY" in error_message:
             return jsonify({"message": f"Erreur Airtable: Clé API invalide ou manquante."}), 500
        elif "INVALID_REQUEST_UNKNOWN_FIELD_NAME" in error_message:
             unknown_field = error_message.split("name ")[-1].split("\'")[0] if "name \'" in error_message else "inconnu"
             return jsonify({"message": f"Erreur Airtable: Nom de champ invalide ({unknown_field}). Vérifiez les noms: {FIELD_EAN}, {FIELD_RAYON}, {FIELD_ETAT}, {FIELD_SOUS_RAYON}."}), 500
        elif "INVALID_VALUE_FOR_COLUMN" in error_message:
             return jsonify({"message": f"Erreur Airtable: Valeur invalide pour une colonne (probablement Rayon ou Etat). Vérifiez les options sélectionnées."}), 400
        else:
             return jsonify({"message": f"Erreur interne lors de l\`ajout à Airtable: {error_message}"}), 500


# --- Main Execution ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=False, host="0.0.0.0", port=port)


