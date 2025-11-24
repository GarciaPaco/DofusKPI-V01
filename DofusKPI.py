# Mon Script DofusKPI - Version GUI Sécurisée
import subprocess
import os
import pyautogui
import time
import pygetwindow as gw
from pynput import mouse
import sys 
import FreeSimpleGUI as sg
import threading
import traceback # Gardé pour un débogage facile

# --- CONFIGURATION (À MODIFIER PAR VOS VALEURS !) ---
LAUNCHER_PATH = r"C:\Jeux\Ankama\Ankama Launcher\Ankama Launcher.exe"
ANKAMA_LAUNCHER_WINDOW_TITLE = "Ankama Launcher"
LOAD_WAIT_TIME = 10 

# --- VARIABLES GLOBALES ---
last_position = None
mouse_listener = None 
GUI_ACTIVE = True

# --- CLASSE DE REDIRECTION DES LOGS (Optimisée pour la sécurité des threads) ---

class StreamToGUI(object):
    def __init__(self, window):
        self.window = window

    def write(self, text):
        # Envoie le texte à la boucle de la GUI via un événement sécurisé
        self.window.write_event_value('-LOGUPDATE-', text) 
        
    def flush(self):
        # Nécessaire pour les fonctions comme print(..., flush=True)
        pass 

# --- NOUVELLE FONCTION : BARRE DE PROGRESSION ---

def sleep_with_progress(duration, message="Chargement..."):
    """
    Simule time.sleep tout en affichant une barre de progression.
    """
    start_time = time.time()
    bar_length = 20
    
    while time.time() - start_time < duration:
        elapsed = time.time() - start_time
        remaining = duration - elapsed
        
        percent = elapsed / duration
        filled_length = int(round(bar_length * percent))
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        # Le "\r" fonctionne dans la console, et la GUI gère les mises à jour rapides
        print(f"\r{message} : [{bar}] {remaining:.1f}s restants", end='', flush=True)
        
        time.sleep(0.1) 
    
    print(f"\r{message} : [{'█' * bar_length}] 0.0s terminé.   ")

# --- FONCTIONS SYSTÈME (Lancement et Fenêtre) ---

def start_AnkamaLauncher(chemin_executable):
    try:
        if gw.getWindowsWithTitle(ANKAMA_LAUNCHER_WINDOW_TITLE):
            print(f"ℹ️  Le Launcher est déjà ouvert. Passage à l'activation.")
            return True
    except Exception as e:
        print(f"⚠️ Impossible de vérifier les fenêtres existantes : {e}")
        
    if not os.path.exists(chemin_executable):
        print(f"❌ - Le chemin spécifié n'existe pas : {chemin_executable} \nVeuillez le vérifier...")
        return False
    try:
        subprocess.Popen(
            chemin_executable,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print(f"✅ - Ankama Launcher lancé.")
        sleep_with_progress(LOAD_WAIT_TIME, "Attente du chargement du Launcher") 
        return True
    except Exception as e:
        print(f"⚠️ - Erreur lors du lancement de l'Ankama Launcher : {e}")
        return False
    
def activer_fenetre_AnkamaLauncher(titre_fenetre):
    try:
        fenetres = gw.getWindowsWithTitle(titre_fenetre)
        if fenetres:
            fenetre = fenetres[0]
            fenetre.activate() 
            print(f"✅ - Fenêtre '{titre_fenetre}' activée.")
            sleep_with_progress(1, "Finalisation de l'activation") 
            return True
        else:
            print(f"⚠️ - Aucune fenêtre trouvée avec le titre : {titre_fenetre}")
            return False
    except Exception as e:
        print(f"⚠️ - Erreur lors de l'activation de la fenêtre : {e}")
        return False

# --- FONCTIONS D'ÉCOUTE (PYNPUT) ---

def on_click(x, y, button, pressed):
    """
    Fonction de rappel. Enregistre et affiche la position au clic de la molette.
    """
    global last_position
    if pressed and button == mouse.Button.middle:
        last_position = (x, y)
        print("-" * 30)
        print(f"✅ - Coordonnées enregistrées : X={x}, Y={y}")
        print("-" * 30)
    return GUI_ACTIVE 

def start_mouse_listener():
    """Démarre l'écoute des événements de la souris en arrière-plan."""
    global mouse_listener
    print("\n--- MODE DÉBOGAGE ACTIF PERPÉTUEL ---")
    print("Chaque clic MOLETTE enregistrera la position.")
    print("------------------------------------------")
    
    mouse_listener = mouse.Listener(on_click=on_click)
    mouse_listener.start()
    print("Écouteur démarré.")

# --- LOGIQUE DU SCRIPT DANS UN THREAD ---

def script_logic(window):
    """Contient la logique principale de lancement et d'attente, exécutée dans un thread."""
    global mouse_listener
    
    try:
        print("📈 - Démarrage de DofusKPI...")
        
        if not start_AnkamaLauncher(LAUNCHER_PATH):
            return

        if not activer_fenetre_AnkamaLauncher(ANKAMA_LAUNCHER_WINDOW_TITLE):
            return
        
        start_mouse_listener()
        print("\nPrêt pour la capture. Appuyez sur 'STOP' pour passer à l'automatisation...")
        
    except Exception as e:
        print("-" * 50)
        print(f"❌ ERREUR CRITIQUE DANS LE THREAD DE LOGIQUE : {e}")
        print(traceback.format_exc()) 
        print("-" * 50)


# --- EXÉCUTION PRINCIPALE (La GUI) --- 

def main():
    sg.theme('DarkGrey9')
    
    layout = [
        [sg.Text('Console de débogage Dofus Automator')],
        [sg.Multiline(size=(80, 20), key='-LOG-', autoscroll=True, font=('Consolas', 10), expand_x=True, expand_y=True)],
        [sg.Button('STOP (Arrêt)', key='-STOP-', size=(20, 1)), sg.Exit()]
    ]
    
    window = sg.Window('Dofus Automator v0.2', layout, finalize=True, resizable=True)

    # 2. Redirection de la sortie standard (print) vers la fenêtre
    redir = StreamToGUI(window)
    sys.stdout = redir

    # 3. Lancement de la logique du script dans un thread séparé
    threading.Thread(target=script_logic, args=(window,), daemon=True).start()

    # 4. Boucle de gestion des événements de la GUI
    global GUI_ACTIVE
    while True:
        event, values = window.read(timeout=100) # Le timeout est important pour maintenir la réactivité
        
        if event == sg.WIN_CLOSED or event == 'Exit':
            break
            
        # Gère l'événement de mise à jour des logs
        if event == '-LOGUPDATE-':
            text_to_append = values['-LOGUPDATE-']
            # Utilise .print() pour gérer les couleurs et les sauts de ligne si nécessaire, ou update pour le texte brut.
            window['-LOG-'].update(text_to_append, append=True)
            window['-LOG-'].Widget.see("end") # Scrolle vers le bas
        
        if event == '-STOP-':
            print("\n🛑 Signal d'arrêt détecté. Arrêt de l'écouteur...")
            break
            
    # 5. Logique d'arrêt propre
    GUI_ACTIVE = False
    if mouse_listener and mouse_listener.is_alive():
        mouse_listener.stop()
        
    if last_position:
        x, y = last_position
        print(f"✅ - Dernière coordonnée capturée : X={x}, Y={y}. Prêt pour l'automatisation.")
    
    print("\n🔚 Fermeture de la fenêtre.")
    # On doit remettre sys.stdout à la console avant de fermer si l'on veut voir le dernier print
    sys.stdout = sys.__stdout__ 
    window.close()
    sys.exit(0)

if __name__ == "__main__":
    main()