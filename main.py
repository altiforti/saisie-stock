import os
import requests
from flask import Flask, request, jsonify, render_template, send_from_directory
from airtable import Airtable

# Configuration from Environment Variables
AIRTABLE_API_KEY = os.environ.get('AIRTABLE_API_KEY')
AIRTABLE_BASE_ID = os.environ.get('AIRTABLE_BASE_ID')
# Table name for stock entries
AIRTABLE_TABLE_NAME = os.environ.get('AIRTABLE_TABLE_NAME', 'SAISIE DE LIVRES')
# Field names (ensure these match Airtable exactly)
FIELD_EAN = 'EAN'
FIELD_ETAT = 'ETAT'
FIELD_RAYON = 'RAYON'
FIELD_SOUS_RAYON = 'sous rayon'

# --- Airtable Client Initialization ---
try:
    airtable = Airtable(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME, api_key=AIRTABLE_API_KEY)
    # Basic check to see if connection seems okay (will fail later if keys/base/table are wrong)
    print(f"Airtable client initialized for table: {AIRTABLE_TABLE_NAME}")
except Exception as e:
    print(f"Error initializing Airtable client: {e}")
    airtable = None # Ensure airtable is None if init fails

# --- Flask App Initialization ---
app = Flask(__name__, static_folder='static', template_folder='static')

# --- Helper Function to get Airtable Field Options ---
# NOTE: airtable-python-wrapper doesn't directly support getting field schema.
# We might need to use the Airtable REST API directly for this, or hardcode options.
# For now, we return predefined ETAT list and handle RAYON potentially failing.

def get_airtable_select_options(table_name, field_name):
    """
    Placeholder function. Ideally fetches options from Airtable Metadata API.
    Fallback: Return predefined list or empty list.
    """
    print(f"Attempting to get options for field '{field_name}'. NOTE: Dynamic fetching may require Metadata API access.")
    if field_name == FIELD_ETAT:
        # Use the list provided by the user
        print(f"Returning predefined list for '{FIELD_ETAT}'.")
        return ['EC', 'TB', 'BE', 'CN', 'NE']
    elif field_name == FIELD_RAYON:
        # We need the user to provide this list or confirm if it can be fetched another way.
        # For now, return empty and handle in frontend/backend.
        print(f"Warning: Could not dynamically fetch options for '{FIELD_RAYON}'. Returning empty list. Please check Airtable setup or provide the list manually.")
        return [] # Returning empty list - frontend needs to handle this
    else:
        return []


# --- Flask Routes ---

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    """Serves static files (like CSS, JS, images)."""
    # Ensure the logo file name matches what's in the static folder
    if path == 'logo.jpeg': # Assuming the renamed logo is used
        return send_from_directory('static', path)
    return send_from_directory('static', path)

@app.route('/get_stock_options', methods=['GET'])
def get_stock_options():
    """Endpoint to provide options for dropdowns."""
    try:
        rayon_options = get_airtable_select_options(AIRTABLE_TABLE_NAME, FIELD_RAYON)
        etat_options = get_airtable_select_options(AIRTABLE_TABLE_NAME, FIELD_ETAT)

        # If fetching failed for RAYON, the list will be empty.
        # The frontend JS should handle the empty list gracefully (e.g., show error).
        if not rayon_options:
            print("Rayon options list is empty. Frontend should display an error or guidance.")
            # Optionally, provide a default placeholder if needed by frontend logic
            # rayon_options = ["Erreur: Liste Rayons non trouvée"] 

        return jsonify({
            'rayons': rayon_options,
            'etats': etat_options
        })
    except Exception as e:
        print(f"Error in /get_stock_options: {e}")
        # Return empty lists or error state for frontend to handle
        # Still provide ETAT if possible, as it's predefined
        return jsonify({'rayons': [], 'etats': ['EC', 'TB', 'BE', 'CN', 'NE']}), 500


@app.route('/add_stock_entry', methods=['POST'])
def add_stock_entry():
    """Endpoint to add a new stock entry (EAN + batch info) to Airtable."""
    if not airtable:
        return jsonify({'message': 'Erreur: Connexion Airtable non initialisée.'}), 500

    data = request.get_json()
    if not data:
        return jsonify({'message': 'Erreur: Aucune donnée reçue.'}), 400

    ean = data.get('ean')
    rayon = data.get('rayon')
    etat = data.get('etat')
    sous_rayon = data.get('sous_rayon') # Optional field

    if not ean or not rayon or not etat:
        return jsonify({'message': 'Erreur: EAN, Rayon et État sont requis.'}), 400

    # Basic EAN validation (13 digits)
    if not (isinstance(ean, str) and len(ean) == 13 and ean.isdigit()):
         return jsonify({'message': f'Erreur: Format EAN invalide ({ean}). 13 chiffres attendus.'}), 400

    # Prepare record data, ensuring field names match Airtable exactly
    record_data = {
        FIELD_EAN: ean,
        FIELD_RAYON: rayon,
        FIELD_ETAT: etat,
    }
    # Add optional field only if provided and not empty
    if sous_rayon:
        record_data[FIELD_SOUS_RAYON] = sous_rayon

    try:
        # Check if EAN already exists (optional, depends on desired behavior)
        # You might want to allow duplicates for stock entry
        # existing_records = airtable.get_all(formula=f"{{{FIELD_EAN}}}='{ean}'")
        # if existing_records:
        #     return jsonify({'message': f'Avertissement: EAN {ean} existe déjà.'}), 409 # Conflict

        # Create new record
        created_record = airtable.insert(record_data)
        print(f"Airtable record created: {created_record['id']} for EAN {ean}")
        return jsonify({'message': f'EAN {ean} ajouté avec succès.'}), 201

    except Exception as e:
        error_message = str(e)
        print(f"Error adding record to Airtable for EAN {ean}: {error_message}")
        # Try to provide a more specific error if possible
        if "NOT_FOUND" in error_message:
             return jsonify({'message': f'Erreur Airtable: Table ou Base non trouvée. Vérifiez la configuration.'}), 500
        elif "AUTHENTICATION_REQUIRED" in error_message or "INVALID_API_KEY" in error_message:
             return jsonify({'message': f'Erreur Airtable: Clé API invalide ou manquante.'}), 500
        elif "INVALID_REQUEST_UNKNOWN_FIELD_NAME" in error_message:
             # Extract field name from error if possible for better debugging
             unknown_field = error_message.split("name '")[-1].split("' did not match")[0] if "name '" in error_message else "inconnu"
             return jsonify({'message': f'Erreur Airtable: Nom de champ invalide ({unknown_field}). Vérifiez les noms: {FIELD_EAN}, {FIELD_RAYON}, {FIELD_ETAT}, {FIELD_SOUS_RAYON}.'}), 500
        elif "INVALID_VALUE_FOR_COLUMN" in error_message:
             return jsonify({'message': f'Erreur Airtable: Valeur invalide pour une colonne (probablement Rayon ou Etat). Vérifiez les options sélectionnées.'}), 400
        else:
             return jsonify({'message': f'Erreur interne lors de l\`ajout à Airtable: {error_message}'}), 500


# --- Main Execution ---
if __name__ == '__main__':
    # Port configuration for local dev and Render.com compatibility
    port = int(os.environ.get('PORT', 5001))
    # Run on 0.0.0.0 to be accessible externally (required for Docker/Render)
    # Use debug=False for production/deployment
    app.run(debug=False, host='0.0.0.0', port=port)

