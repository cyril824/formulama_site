import flask
from flask import Flask, request, jsonify, send_from_directory, abort, send_file, redirect
from flask_cors import CORS
import os 
from werkzeug.utils import secure_filename 
import urllib.parse
import base64 
import ssl
import subprocess
import sys
import time
import signal
import atexit

# Importe toutes les fonctions necessaires
from gestion_db import ajouter_document, recuperer_documents_par_categorie, supprimer_document, initialiser_base_de_donnees, recuperer_4_derniers_documents, diagnostiquer_fichiers_locaux, recuperer_tous_documents, recuperer_document_par_id, marquer_document_signe, marquer_document_rempli 

# 1. Configuration de l'application Flask
app = Flask(__name__, static_folder='.')
CORS(app) 

# Variables globales pour les processus
background_processes = []

def launch_background_services():
    """Lance les services particuliers et pro en arriere-plan"""
    global background_processes
    
    SITE_ROOT = os.path.dirname(os.path.abspath(__file__))
    SITE_PARENT = os.path.dirname(SITE_ROOT)  # Dossier 'site'
    PROJET_ROOT = os.path.dirname(SITE_PARENT)  # Dossier 'PROJET MINI ENTREPRISE'
    PARTICULIERS_DIR = os.path.join(PROJET_ROOT, 'formulama_particuliers')
    PRO_DIR = os.path.join(PROJET_ROOT, 'formulama_pro')
    
    print(f"[DEBUG] SITE_ROOT: {SITE_ROOT}")
    print(f"[DEBUG] SITE_PARENT: {SITE_PARENT}")
    print(f"[DEBUG] PROJET_ROOT: {PROJET_ROOT}")
    print(f"[DEBUG] PARTICULIERS_DIR: {PARTICULIERS_DIR}")
    print(f"[DEBUG] PRO_DIR: {PRO_DIR}")
    
    try:
        # Fichiers de logs pour chaque service
        particuliers_log_path = os.path.join(PARTICULIERS_DIR, 'service.log')
        pro_log_path = os.path.join(PRO_DIR, 'service.log')
        
        # Lancer formulama_particuliers avec redirection des logs
        with open(particuliers_log_path, 'w') as log_file:
            particuliers_process = subprocess.Popen(
                [sys.executable, 'backend/app_server.py'],
                cwd=PARTICULIERS_DIR,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL
            )
        background_processes.append(('PARTICULIERS', particuliers_process))
        print(f"[OK] Service PARTICULIERS lance (PID: {particuliers_process.pid})")
        print(f"     Logs: {particuliers_log_path}")
        
        # Petit delai
        time.sleep(2)
        
        # Lancer formulama_pro avec redirection des logs
        with open(pro_log_path, 'w') as log_file:
            pro_process = subprocess.Popen(
                [sys.executable, 'backend/app_server.py'],
                cwd=PRO_DIR,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL
            )
        background_processes.append(('PRO', pro_process))
        print(f"[OK] Service PRO lance (PID: {pro_process.pid})")
        print(f"     Logs: {pro_log_path}")
        
    except Exception as e:
        print(f"[ERREUR] Impossible de lancer les services en arriere-plan: {e}")
        import traceback
        traceback.print_exc()

def cleanup_processes():
    """Arrete les processus en arriere-plan"""
    for name, process in background_processes:
        if process and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()

# --- DÉFINITION DU CHEMIN DU DOSSIER DE DONNÉES ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SITE_ROOT = SCRIPT_DIR  # Dossier formulama_site
PROJET_ROOT = os.path.dirname(SITE_ROOT)  # Dossier site
PARENT_ROOT = os.path.dirname(PROJET_ROOT)  # Dossier PROJET MINI ENTREPRISE
FORMULAMA_VITE_ROOT = os.path.join(PARENT_ROOT, 'formulama_vite')
DATA_FOLDER_PATH = os.path.join(FORMULAMA_VITE_ROOT, 'data')
DIST_FOLDER_PATH = os.path.join(FORMULAMA_VITE_ROOT, 'dist')
SIGNATURES_FOLDER_PATH = os.path.join(DATA_FOLDER_PATH, 'signatures')
# Créer le dossier des signatures s'il n'existe pas
os.makedirs(SIGNATURES_FOLDER_PATH, exist_ok=True)
print(f"[app.py] SITE_ROOT: {SITE_ROOT}")
print(f"[app.py] FORMULAMA_VITE_ROOT: {FORMULAMA_VITE_ROOT}")
print(f"[app.py] DATA_FOLDER_PATH: {DATA_FOLDER_PATH}")
# ----------------------------------------------------

# --- FONCTION UTILITAIRE POUR LE MIME TYPE ---
def get_mimetype(filename):
    """Détermine le MIME type basé sur l'extension du fichier."""
    if filename.lower().endswith('.pdf'):
        return 'application/pdf'
    elif filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        return 'image/' + filename.split('.')[-1]
    else:
        return 'application/octet-stream'


# --- FONCTION POUR SAUVEGARDER LA SIGNATURE ---
def save_signature(doc_id, signature_base64):
    """Sauvegarde la signature (base64 PNG) sur le disque."""
    try:
        # Supprimer le préfixe data:image/png;base64, si présent
        if 'base64,' in signature_base64:
            signature_base64 = signature_base64.split('base64,')[1]
        
        # Décoder et sauvegarder
        signature_binary = base64.b64decode(signature_base64)
        signature_path = os.path.join(SIGNATURES_FOLDER_PATH, f'{doc_id}.png')
        
        with open(signature_path, 'wb') as f:
            f.write(signature_binary)
        
        print(f"Signature sauvegardée: {signature_path}")
        return True
    except Exception as e:
        print(f"Erreur lors de la sauvegarde de la signature: {e}")
        return False


# ============================================
# ROUTES DU SITE (accueil, pages statiques)
# ============================================

@app.route('/')
def index():
    return send_from_directory('.', 'acceuil/acceuil.html')

@app.route('/accueil')
@app.route('/home')
def home():
    """Redirection vers l'accueil"""
    return send_from_directory('.', 'acceuil/acceuil.html')

@app.route('/selection')
def selection():
    """Page de sélection entre Particuliers et Professionnels"""
    return send_from_directory('.', 'selection/selection.html')

@app.route('/go-particuliers')
def go_particuliers():
    """Redirection vers l'application Particuliers"""
    return redirect('http://localhost:5000', code=302)

@app.route('/go-professionnels')
def go_professionnels():
    """Redirection vers l'application Professionnels"""
    return redirect('http://localhost:5001', code=302)

# Route pour l'application Formulama (Vite build)
@app.route('/app')
@app.route('/app/')
def formulama_app():
    return send_from_directory(DIST_FOLDER_PATH, 'index.html')

# Routes pour les assets Vite (priorité haute)
@app.route('/assets/<path:path>')
def serve_assets(path):
    return send_from_directory(os.path.join(DIST_FOLDER_PATH, 'assets'), path)

@app.route('/favicon.ico')
def serve_favicon():
    try:
        return send_from_directory(DIST_FOLDER_PATH, 'favicon.ico')
    except:
        return '', 204

@app.route('/app/<path:path>')
def formulama_app_files(path):
    # If the requested file exists in the dist folder serve it, otherwise
    # return index.html so the client-side router can handle the route.
    full_path = os.path.join(DIST_FOLDER_PATH, path)
    if os.path.exists(full_path) and not os.path.isdir(full_path):
        return send_from_directory(DIST_FOLDER_PATH, path)
    return send_from_directory(DIST_FOLDER_PATH, 'index.html')

@app.route('/<path:path>')
def serve_file(path):
    return send_from_directory('.', path)


# ============================================
# ROUTES API (documents et gestion)
# ============================================

# Point d'accès de base API
@app.route('/api/status')
def api_status():
    return jsonify({"status": "API Formulama active"}), 200

# Endpoint pour ajouter un document (Méthode POST)
@app.route('/api/documents/ajouter', methods=['POST'])
def api_ajouter_document():
    if 'file' not in request.files:
        return jsonify({"error": "Aucun fichier n'a été envoyé."}), 400
        
    f = request.files['file']
    categorie = request.form.get('categorie')
    
    if not categorie:
        return jsonify({"error": "Catégorie manquante."}), 400
    
    # Sécurisation du nom de fichier
    filename = secure_filename(f.filename)

    # 1. Sauvegarde physique du fichier dans le dossier /data
    file_path = os.path.join(DATA_FOLDER_PATH, filename)
    
    try:
        if not os.path.exists(DATA_FOLDER_PATH):
            os.makedirs(DATA_FOLDER_PATH) 
            
        f.save(file_path) 
        print(f"✅ Fichier sauvegardé physiquement à: {file_path}")
        
    except Exception as e:
        print(f"🛑 Erreur de sauvegarde du fichier: {e}")
        return jsonify({"error": f"Échec de la sauvegarde physique du fichier sur le serveur: {e}"}), 500

    # 2. Enregistrement dans la base de données
    simulated_path = f"//localhost/data/{filename}" 
    doc_id = ajouter_document(filename, simulated_path, categorie)
    
    if doc_id:
        return jsonify({"message": "Document et BDD mis à jour avec succès", "id": doc_id}), 201 
    else:
        return jsonify({"error": "Erreur lors de l'insertion dans la base de données"}), 500

# Endpoint pour récupérer les 4 documents récents (DOIT ÊTRE AVANT LA ROUTE GÉNÉRIQUE)
@app.route('/api/documents/recents', methods=['GET'])
def api_recuperer_documents_recents():
    try:
        documents = recuperer_4_derniers_documents()
        return jsonify(documents), 200
    except Exception as e:
        print(f"Erreur lors de la récupération des documents récents: {e}")
        return jsonify({"error": "Erreur interne du serveur lors de la récupération des documents récents"}), 500

# Endpoint pour récupérer TOUS les documents
@app.route('/api/documents/all', methods=['GET'])
def api_recuperer_tous_documents():
    try:
        documents = recuperer_tous_documents()
        return jsonify(documents), 200
    except Exception as e:
        print(f"Erreur lors de la récupération de tous les documents: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500

# Endpoint pour récupérer les documents par catégorie (Méthode GET)
@app.route('/api/documents/<categorie>', methods=['GET'])
def api_recuperer_documents(categorie):
    documents = recuperer_documents_par_categorie(categorie)
    return jsonify(documents), 200

# Endpoint de diagnostic
@app.route('/api/documents/diagnostiquer-fichiers', methods=['GET'])
def api_diagnostiquer_fichiers():
    diagnostic_result = diagnostiquer_fichiers_locaux(DATA_FOLDER_PATH)
    return jsonify(diagnostic_result), 200

# ENDPOINT FINAL POUR CONSULTER LE FICHIER (CORRIGÉ POUR SÉCURITÉ)
@app.route('/api/documents/ouvrir/<filename>', methods=['GET'])
def api_ouvrir_document(filename):
    """
    Sert le fichier statique demandé à partir du dossier de données.
    """
    try:
        # Décodage de l'URL pour gérer les espaces (%20)
        decoded_filename = urllib.parse.unquote(filename)
        
        full_path = os.path.join(DATA_FOLDER_PATH, decoded_filename)
        
        print(f"\n--- DEBUG D'OUVERTURE ---")
        print(f"Fichier demandé (décodé) : {decoded_filename}")
        
        if not os.path.exists(full_path):
            print(f"ERREUR PHYSIQUE: Fichier introuvable à : {full_path}")
            abort(404) 

        print(f"Fichier trouvé : Tentative d'envoi.")
        
        # Utilise send_from_directory pour servir le fichier
        response = send_from_directory(
            directory=DATA_FOLDER_PATH,
            path=decoded_filename,
            as_attachment=False,
            mimetype=get_mimetype(decoded_filename)
        )
        
        # Supprime les en-têtes de sécurité qui bloquent l'iFrame
        response.headers['X-Frame-Options'] = 'ALLOWALL'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self' http://localhost:* https://localhost:*;"
        
        print(f"-------------------------\n")
        return response
    
    except Exception as e:
        print(f"Erreur générale lors de l'ouverture du document {filename}: {e}")
        return jsonify({"error": f"Erreur interne du serveur lors de l'ouverture: {e}"}), 500


# Endpoint pour marquer un document comme signé (Méthode PUT)
@app.route('/api/documents/<int:doc_id>/sign', methods=['PUT'])
def api_marquer_document_signe(doc_id):
    try:
        data = request.get_json() or {}
        signature_data = data.get('signatureData')
        
        # Marquer le document comme signé
        if marquer_document_signe(doc_id):
            # Sauvegarder la signature si fournie
            if signature_data:
                save_signature(doc_id, signature_data)
            return jsonify({"message": f"Document ID {doc_id} marqué comme signé."}), 200
        else:
            return jsonify({"error": f"Impossible de mettre à jour le document ID {doc_id}."}), 404
    except Exception as e:
        print(f"Erreur lors de la signature du document: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500

# Endpoint pour marquer un document comme rempli (Méthode PUT)
@app.route('/api/documents/<int:doc_id>/fill', methods=['PUT'])
def api_marquer_document_rempli(doc_id):
    try:
        # Marquer le document comme rempli
        if marquer_document_rempli(doc_id):
            return jsonify({"message": f"Document ID {doc_id} marqué comme rempli."}), 200
        else:
            return jsonify({"error": f"Impossible de mettre à jour le document ID {doc_id}."}), 404
    except Exception as e:
        print(f"Erreur lors du remplissage du document: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500

# Endpoint pour récupérer la signature d'un document
@app.route('/api/documents/<int:doc_id>/signature', methods=['GET'])
def api_get_signature(doc_id):
    try:
        signature_path = os.path.join(SIGNATURES_FOLDER_PATH, f'{doc_id}.png')
        if os.path.exists(signature_path):
            return send_file(signature_path, mimetype='image/png')
        else:
            return jsonify({"error": "Signature not found"}), 404
    except Exception as e:
        print(f"Erreur lors de la récupération de la signature: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500

# Endpoint pour supprimer un document (Méthode DELETE)
@app.route('/api/documents/<int:doc_id>', methods=['DELETE'])
def api_supprimer_document(doc_id):
    if supprimer_document(doc_id):
        return jsonify({"message": f"Document ID {doc_id} supprimé."}), 200
    else:
        return jsonify({"error": f"Impossible de supprimer le document ID {doc_id}. Introuvable ou erreur interne."}), 404

# Endpoint pour supprimer tous les documents (Méthode DELETE)
@app.route('/api/documents', methods=['DELETE'])
def api_supprimer_tous_documents():
    try:
        # Récupérer tous les documents
        from gestion_db import recuperer_tous_documents, supprimer_document
        documents = recuperer_tous_documents()
        
        # Supprimer chaque fichier du dossier /data
        for doc in documents:
            file_path = os.path.join(DATA_FOLDER_PATH, doc.get('nom_fichier'))
            if os.path.exists(file_path):
                os.remove(file_path)
            # Supprimer de la base de données
            supprimer_document(doc.get('id'))
        
        return jsonify({"message": "Tous les documents ont été supprimés"}), 200
    except Exception as e:
        print(f"Erreur lors de la suppression de tous les documents: {e}")
        return jsonify({"error": f"Erreur lors de la suppression: {e}"}), 500

# Endpoint pour prévisualiser un document
@app.route('/api/documents/preview/<int:doc_id>')
def api_preview_document(doc_id):
    """Retourne le fichier du document pour prévisualisation"""
    try:
        from gestion_db import recuperer_document_par_id
        
        # Récupérer le document depuis la base de données
        document = recuperer_document_par_id(doc_id)
        
        if not document or not document.get('nom_fichier'):
            return jsonify({"error": "Document non trouvé"}), 404
        
        # Utiliser le chemin absolu dans le dossier data
        filename = document.get('nom_fichier')
        file_path = os.path.join(DATA_FOLDER_PATH, filename)
        
        # Vérifier que le fichier existe
        if not os.path.exists(file_path):
            print(f"Fichier non trouvé à: {file_path}")
            return jsonify({"error": "Fichier non trouvé"}), 404
        
        # Déterminer le MIME type
        mimetype = get_mimetype(filename)
        
        print(f"Servant le document: {file_path} (MIME: {mimetype})")
        
        # Retourner le fichier avec les bons headers CORS
        response = send_from_directory(
            DATA_FOLDER_PATH, 
            filename,
            mimetype=mimetype
        )
        
        # Ajouter les headers CORS pour que react-pdf puisse charger
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Range'
        response.headers['Accept-Ranges'] = 'bytes'
        
        return response
    except Exception as e:
        print(f"Erreur lors de la récupération du document: {e}")
        return jsonify({"error": str(e)}), 500

# Endpoint pour servir directement les fichiers du dossier data
@app.route('/api/documents/file/<filename>')
def serve_document_file(filename):
    """Sert les fichiers du dossier data"""
    try:
        return send_from_directory(DATA_FOLDER_PATH, filename)
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier: {e}")
        return jsonify({"error": "Fichier non trouvé"}), 404


# Lancement du serveur
if __name__ == '__main__':
    # Enregistrer la fonction de cleanup pour arreter les processus a la fermeture
    atexit.register(cleanup_processes)
    
    initialiser_base_de_donnees()
    print(f"\n[INFO] Dossier de documents configure : {DATA_FOLDER_PATH}\n")
    
    print("=" * 60)
    print("LANCEMENT DE L'INFRASTRUCTURE FORMULAMA")
    print("=" * 60)
    
    # Lancer les services en arriere-plan
    print("\n[INFO] Lancement des services en arriere-plan...\n")
    launch_background_services()
    
    print("\n" + "=" * 60)
    print("[OK] TOUS LES SERVICES SONT LANCES")
    print("=" * 60)
    print("\nAcces aux services :")
    print("  - Site vitrine : http://localhost:8000")
    print("  - Particuliers : http://localhost:5000")
    print("  - Professionnels : http://localhost:5001")
    print("\nAppuyez sur Ctrl+C pour arreter tous les services.\n")
    
    # Lancement du serveur Flask sur le port 8000
    app.run(debug=True, host="0.0.0.0", port=8000)
