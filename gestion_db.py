import sqlite3
import datetime 
import os

# Chemin vers la base de données (chemin absolu pour éviter les problèmes relatifs)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SITE_ROOT = SCRIPT_DIR  # Dossier formulama_site
PROJET_ROOT = os.path.dirname(SITE_ROOT)  # Dossier site
PARENT_ROOT = os.path.dirname(PROJET_ROOT)  # Dossier PROJET MINI ENTREPRISE
FORMULAMA_VITE_ROOT = os.path.join(PARENT_ROOT, 'formulama_vite')
DB_NAME = os.path.join(FORMULAMA_VITE_ROOT, 'data', 'documents.db')

print(f"[gestion_db] SITE_ROOT: {SITE_ROOT}")
print(f"[gestion_db] FORMULAMA_VITE_ROOT: {FORMULAMA_VITE_ROOT}")
print(f"[gestion_db] DB_NAME: {DB_NAME}")
print(f"[gestion_db] DB exists: {os.path.exists(DB_NAME)}") 

def supprimer_document(doc_id: int):
    """
    Supprime un enregistrement de document de la base de données par son ID.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Requête DELETE : utilise l'ID pour identifier la ligne
        suppression_query = "DELETE FROM documents WHERE id = ?"
        
        cursor.execute(suppression_query, (doc_id,))
        conn.commit()
        
        # Vérifie si une ligne a été affectée (si l'ID existait)
        return cursor.rowcount > 0 

    except sqlite3.Error as e:
        print(f"[ERREUR] Erreur lors de la suppression du document ID {doc_id} : {e}")
        return False
    finally:
        if conn:
            conn.close()

def initialiser_base_de_donnees():
    """Crée le fichier DB et la table 'documents' s'ils n'existent pas."""
    conn = None
    try:
        # Assurez-vous que le répertoire 'data' existe
        os.makedirs(os.path.dirname(DB_NAME), exist_ok=True)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        creation_table_query = """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom_fichier TEXT NOT NULL,
            chemin_local TEXT NOT NULL,
            categorie TEXT NOT NULL,
            date_ajout DATETIME,
            is_signed BOOLEAN DEFAULT 0,
            is_filled BOOLEAN DEFAULT 0
        );
        """
        cursor.execute(creation_table_query)
        conn.commit()
        
        # Ajouter la colonne is_signed si elle n'existe pas
        cursor.execute("PRAGMA table_info(documents)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'is_signed' not in columns:
            cursor.execute("ALTER TABLE documents ADD COLUMN is_signed BOOLEAN DEFAULT 0")
            conn.commit()
            print("[OK] Colonne 'is_signed' ajoutée à la table 'documents'.")
        
        # Ajouter la colonne is_filled si elle n'existe pas
        if 'is_filled' not in columns:
            cursor.execute("ALTER TABLE documents ADD COLUMN is_filled BOOLEAN DEFAULT 0")
            conn.commit()
            print("[OK] Colonne 'is_filled' ajoutée à la table 'documents'.")
        
        print(f"[OK] Base de données '{DB_NAME}' initialisée avec succès.")

    except sqlite3.Error as e:
        print(f"[ERREUR] Erreur lors de l'initialisation de la base de données : {e}")
    except Exception as e:
        print(f"[ERREUR] Erreur système lors de l'initialisation : {e}")
    finally:
        if conn:
            conn.close()

def marquer_document_signe(doc_id: int):
    """Marque un document comme signé."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        update_query = "UPDATE documents SET is_signed = 1 WHERE id = ?"
        cursor.execute(update_query, (doc_id,))
        conn.commit()
        
        return cursor.rowcount > 0
    
    except sqlite3.Error as e:
        print(f"🛑 Erreur lors de la mise à jour du document ID {doc_id} : {e}")
        return False
    finally:
        if conn:
            conn.close()

def marquer_document_rempli(doc_id: int):
    """Marque un document comme rempli."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        update_query = "UPDATE documents SET is_filled = 1 WHERE id = ?"
        cursor.execute(update_query, (doc_id,))
        conn.commit()
        
        return cursor.rowcount > 0
    
    except sqlite3.Error as e:
        print(f"🛑 Erreur lors de la mise à jour du document ID {doc_id} : {e}")
        return False
    finally:
        if conn:
            conn.close()

def ajouter_document(nom, chemin, categorie):
    """Ajoute un enregistrement de document."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        insertion_query = """
        INSERT INTO documents (nom_fichier, chemin_local, categorie, date_ajout)
        VALUES (?, ?, ?, ?)
        """
        data = (
            nom,
            chemin,
            categorie,
            # Correction de la syntaxe de datetime
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
        )

        # Exécute la requête
        cursor.execute(insertion_query, data)
        conn.commit()
        
        # Récupère l'ID du document inséré
        doc_id = cursor.lastrowid
        return doc_id

    except sqlite3.Error as e:
        print(f"🛑 Erreur lors de l'ajout du document '{nom}' : {e}")
        return False
    finally:
        if conn:
            conn.close()

def recuperer_documents_par_categorie(categorie):
    """Récupère tous les documents pour une catégorie donnée."""
    conn = None
    documents = []
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        select_query = """
        SELECT id, nom_fichier, chemin_local, categorie, date_ajout, is_signed, is_filled
        FROM documents
        WHERE categorie = ?
        ORDER BY date_ajout DESC
        """
        
        # Utilise la catégorie pour filtrer
        cursor.execute(select_query, (categorie,))
        documents = cursor.fetchall()

    except sqlite3.Error as e:
        print(f"🛑 Erreur lors de la récupération pour la catégorie '{categorie}' : {e}")
        
    finally:
        if conn:
            conn.close()
            
    return documents

def recuperer_document_par_id(doc_id):
    """Récupère un document spécifique par son ID"""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        select_query = """
        SELECT id, nom_fichier, chemin_local, categorie, date_ajout, is_signed, is_filled
        FROM documents
        WHERE id = ?
        """
        
        cursor.execute(select_query, (doc_id,))
        result = cursor.fetchone()
        
        if result:
            return dict(result)
        return None

    except sqlite3.Error as e:
        print(f"🛑 Erreur lors de la récupération du document {doc_id} : {e}")
        return None
        
    finally:
        if conn:
            conn.close()

def recuperer_tous_documents():
    """
    Récupère TOUS les documents de la base de données, peu importe la catégorie.
    """
    conn = None
    documents = []
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        select_query = """
        SELECT id, nom_fichier, chemin_local, categorie, date_ajout, is_signed, is_filled
        FROM documents
        ORDER BY date_ajout DESC
        """
        
        cursor.execute(select_query)
        documents = [dict(row) for row in cursor.fetchall()]

        return documents

    except sqlite3.Error as e:
        print(f"🛑 Erreur lors de la récupération de tous les documents : {e}")
        return []
    finally:
        if conn:
            conn.close()
            
    return documents

def recuperer_4_derniers_documents():
    """
    Récupère les 4 documents les plus récemment ajoutés, quelle que soit leur catégorie.
    Ceci est utilisé pour l'aperçu sur la page d'accueil (Dashboard).
    """
    conn = None
    documents = []
    try:
        conn = sqlite3.connect(DB_NAME)
        # Permet d'accéder aux colonnes par leur nom (comme un dictionnaire)
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()

        select_query = """
        SELECT id, nom_fichier, chemin_local, categorie, date_ajout, is_signed, is_filled
        FROM documents
        ORDER BY date_ajout DESC
        LIMIT 4
        """
        
        # Exécute la requête sans filtre spécifique
        cursor.execute(select_query)
        # Convertit les lignes (sqlite3.Row) en une liste de dictionnaires/objets
        documents = [dict(row) for row in cursor.fetchall()]

    except sqlite3.Error as e:
        print(f"🛑 Erreur lors de la récupération des 4 derniers documents : {e}")
        
    finally:
        if conn:
            conn.close()
            
    return documents


# --- NOUVELLE FONCTION DE DIAGNOSTIC ---
def diagnostiquer_fichiers_locaux(data_folder_path):
    """
    Liste les fichiers présents dans le dossier de données local.
    Ceci est utilisé pour vérifier la casse et l'existence des fichiers sur le serveur.
    """
    try:
        # Liste tous les fichiers et dossiers dans DATA_FOLDER_PATH
        all_items = os.listdir(data_folder_path)
        # Filtre pour ne garder que les fichiers (pas les dossiers) et les fichiers pertinents
        local_files = [item for item in all_items if os.path.isfile(os.path.join(data_folder_path, item)) and not item.startswith('.')]
        return {
            "dossier_recherche": data_folder_path,
            "fichiers_locaux": local_files,
            "statut": "SUCCÈS"
        }
    except FileNotFoundError:
        return {
            "dossier_recherche": data_folder_path,
            "fichiers_locaux": [],
            "statut": "ERREUR: Dossier de données introuvable par le serveur Python."
        }
    except Exception as e:
        return {
            "dossier_recherche": data_folder_path,
            "fichiers_locaux": [],
            "statut": f"ERREUR INCONNUE: {str(e)}"
        }
