# Mon Script DofusKPI - Version GUI Sécurisée
import subprocess
import os
import pyautogui
import time
import pygetwindow as gw
from pynput import mouse, keyboard
import sys 
import FreeSimpleGUI as sg
import threading
import traceback # Gardé pour un débogage facile

# --- CONFIGURATION (À MODIFIER PAR VOS VALEURS !) ---
DEFAULT_LAUNCHER_PATH = r"C:\Jeux\Ankama\Ankama Launcher\Ankama Launcher.exe"
ANKAMA_LAUNCHER_WINDOW_TITLE = "Ankama Launcher"
LOAD_WAIT_TIME = 10 
DOFUS_WINDOW_TITLE = "Dofus" # Titre de la fenêtre du jeu

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
        return True
    except Exception as e:
        print(f"⚠️ - Erreur lors du lancement de l'Ankama Launcher : {e}")
        return False
    
def wait_and_activate_window(titre_fenetre, timeout=30):
    """
    Attend qu'une fenêtre avec un titre spécifique apparaisse, puis l'active.
    Utilise une méthode robuste pour garantir que la fenêtre passe au premier plan.
    """
    print(f"⏳ - Attente de la fenêtre '{titre_fenetre}'...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        # On cherche une fenêtre qui COMMENCE PAR le titre donné, pour plus de flexibilité
        matching_window = None
        for window in gw.getAllWindows():
            if window.title.startswith(titre_fenetre):
                matching_window = window
                break # On a trouvé notre fenêtre, on sort de la boucle

        if matching_window:
            print(f"✅ - Fenêtre '{matching_window.title}' trouvée !")
            
            # --- Logique d'activation forcée ---
            if matching_window.isMinimized:
                print("...Restauration de la fenêtre minimisée...")
                matching_window.restore()
                time.sleep(0.5)

            matching_window.activate()
            time.sleep(0.5) # Laisse le temps à l'OS de réagir

            # Vérification et plan B si l'activation a échoué
            if gw.getActiveWindow() != matching_window:
                print("⚠️ - L'activation simple a échoué. Tentative d'activation forcée par clic...")
                try:
                    # Clic sur la barre de titre pour forcer le focus
                    pyautogui.click(matching_window.left + 100, matching_window.top + 10)
                except Exception as e:
                    print(f"❌ - Erreur lors du clic forcé : {e}")
            return matching_window
        time.sleep(0.5)
    print(f"❌ - Timeout : La fenêtre '{titre_fenetre}' n'est pas apparue après {timeout}s.")
    return None

def find_and_click_image(image_path, timeout=20, confidence=0.8):
    """
    Recherche une image à l'écran pendant un temps donné et clique dessus si elle est trouvée.
    """
    print(f"🔎 - Recherche de l'image '{image_path}'...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            coords = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)
            if coords:
                print(f"✅ - Image trouvée ! Clic aux coordonnées {coords}.")
                pyautogui.click(coords)
                return True
        except pyautogui.PyAutoGUIException:
            # Cette exception peut survenir si l'image n'est pas trouvée, on l'ignore et on réessaie.
            pass
        time.sleep(0.5)

    print(f"❌ - Timeout : Impossible de trouver l'image '{image_path}' après {timeout}s.")
    return False

def wait_for_image(image_path, timeout=20, confidence=0.8):
    """
    Recherche une image à l'écran pendant un temps donné et retourne True si elle est trouvée.
    """
    print(f"⏳ - Attente de l'image '{image_path}'...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # On utilise locateOnScreen qui est un peu plus rapide si on n'a pas besoin du centre
            if pyautogui.locateOnScreen(image_path, confidence=confidence):
                print(f"✅ - Image '{image_path}' trouvée !")
                return True
        except pyautogui.PyAutoGUIException:
            # Cette exception peut survenir si l'image n'est pas trouvée, on l'ignore et on réessaie.
            pass
        time.sleep(0.5)

    print(f"❌ - Timeout : Impossible de trouver l'image '{image_path}' après {timeout}s.")
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
    print("------------------------------------------")

    mouse_listener = mouse.Listener(on_click=on_click)
    mouse_listener.start()
    print("Chaque clic MOLETTE enregistrera la position du curseur.")

# --- LOGIQUE DU SCRIPT DANS UN THREAD ---

def script_logic(window, values):
    """Contient la logique principale de lancement et d'attente, exécutée dans un thread."""
    global mouse_listener
    
    try:
        # --- LOGIQUE DE DÉMARRAGE UNIFIÉE ---
        # On vérifie si le jeu est déjà lancé pour sauter les étapes du launcher
        dofus_window_exists = any(win.title.startswith(DOFUS_WINDOW_TITLE) for win in gw.getAllWindows())

        print("📈 - Démarrage de DofusKPI...")
        
        if not start_AnkamaLauncher(values['-LAUNCHER_PATH-']):
            return

        # On attend que le launcher soit prêt et on l'active
        if not wait_and_activate_window(ANKAMA_LAUNCHER_WINDOW_TITLE):
            return

        if not dofus_window_exists:
            print("\n🤖 --- DÉBUT DE L'AUTOMATISATION (via Launcher) --- 🤖")
            # 1. Chercher et cliquer sur le bouton "Jouer" du launcher
            if not find_and_click_image('images/jouer_launcher.png', confidence=0.8):
                print("⚠️ - Arrêt du script car le bouton 'Jouer' du launcher n'a pas été trouvé.")
                return
            # 2. Attendre que la fenêtre Dofus apparaisse et l'activer
            if not wait_and_activate_window(DOFUS_WINDOW_TITLE):
                return
        else:
            print("\n🤖 --- Dofus déjà lancé, activation et poursuite... --- 🤖")
            wait_and_activate_window(DOFUS_WINDOW_TITLE)

        # 4. Chercher et cliquer sur le bouton du personnage/serveur
        if not find_and_click_image('images/personnage_jouer.png', confidence=0.8):
            return

        # 5. Attendre l'arrivée en jeu en cherchant l'image d'une des cités
        print("\n⏳ - Attente de l'arrivée en jeu.")
        time.sleep(5)  # Pause initiale avant de commencer la recherche 
        print("\n⏳Recherche de l'image de la cité...")
    
        city_found = None
        start_time = time.time()
        timeout = 60
        while time.time() - start_time < timeout:
            
            if wait_for_image('images/bonta.png', confidence=0.7):
                city_found = 'bonta'
                break
            if wait_for_image('images/brakmar.png', confidence=0.7):
                city_found = 'brakmar'
                break
            time.sleep(0.5) # On attend un peu avant de réessayer

        if city_found == 'bonta':
            print("✅ - Arrivée en jeu confirmée (Bonta). Passage en mode solo.")
            pyautogui.press('space')
            time.sleep(0.5)
            pyautogui.write('/solo', interval=0.1)
            pyautogui.press('enter')
        elif city_found == 'brakmar':
            print("✅ - Arrivée en jeu confirmée (Brakmar). Passage en mode solo et voyage.")
            pyautogui.press('space')
            time.sleep(0.5)
            pyautogui.write('/solo', interval=0.1)
            pyautogui.press('enter')
            time.sleep(0.5) # Pause avant la commande de voyage
            pyautogui.write('/travel -26,38', interval=0.1)
            pyautogui.press('enter')
        else:
            print(f"⚠️ - Le personnage n'est pas arrivé en jeu après {timeout}s.")
            return # On arrête le script si aucune cité n'est trouvée

        # 6. Lancer l'écouteur de la souris pour les étapes suivantes
        print("\n✅ - Actions automatiques terminées.")
        start_mouse_listener()        
        
    except Exception as e:
        print("-" * 50)
        print(f"❌ ERREUR CRITIQUE DANS LE THREAD DE LOGIQUE : {e}")
        print(traceback.format_exc()) 
        print("-" * 50)


# --- EXÉCUTION PRINCIPALE (La GUI) --- 

def main():
    sg.theme('DarkAmber')
    
    # Variable pour éviter les doubles lancements
    script_started = False

    layout = [
        [sg.Text('DofusKPI - Interface de Contrôle', font=('Helvetica', 12, 'bold'))],
        [sg.Text('Chemin du Ankama Launcher :', size=(25,1), key='-PATH_TEXT-'), sg.Input(DEFAULT_LAUNCHER_PATH, key='-LAUNCHER_PATH-', size=(50,1), enable_events=True), sg.FileBrowse('Parcourir', key='-BROWSE-')],
        [sg.HSeparator()],
        [sg.Button('Démarrer DofusKPI', key='-DEMARRER-', size=(25, 2), button_color=('white', 'green'), visible=bool(DEFAULT_LAUNCHER_PATH))],
        [sg.Text('Console de log :')],
        [sg.Multiline(size=(80, 20), key='-LOG-', autoscroll=True, font=('Consolas', 10), expand_x=True, expand_y=True, disabled=True)],
        [sg.Button('STOP (Arrêt)', key='-STOP-', size=(20, 1), button_color=('white', 'firebrick3'), disabled=True), sg.Exit()]
    ]
    
    # --- Calcul de la position de la fenêtre ---
    # On récupère la taille de l'écran
    screen_width, screen_height = sg.Window.get_screen_size()
    # On estime la largeur de la fenêtre (à ajuster si besoin)
    window_width = 650 
    # On calcule la position X pour que la fenêtre soit à droite
    location_x = screen_width - window_width
    
    window = sg.Window('DofusKPI v0.1', layout, finalize=True, resizable=True, location=(location_x, 50))

    # Redirection de la sortie standard (print) vers la fenêtre
    redir = StreamToGUI(window)
    sys.stdout = redir
    sys.stderr = redir

    # --- Configuration du raccourci clavier d'arrêt ---
    def on_hotkey_stop():
        """Fonction appelée par le raccourci clavier. Envoie un événement à la GUI."""
        print("🔥 Raccourci d'arrêt d'urgence détecté !")
        window.write_event_value('-HOTKEY_STOP-', None)

    # On définit le raccourci et on démarre l'écouteur dans son propre thread
    hotkey_listener = keyboard.GlobalHotKeys({
        '<ctrl>+<alt>+s': on_hotkey_stop
    })
    hotkey_listener.start()
    print("ℹ️  Raccourci d'arrêt du script : Ctrl+Alt+C")

    # NOTE : On ne lance PLUS le thread ici automatiquement !

    global GUI_ACTIVE
    while True:
        event, values = window.read(timeout=100)
        
        if event == sg.WIN_CLOSED or event == 'Exit':
            break

        # --- Gestion de la visibilité du bouton Démarrer ---
        if event == '-LAUNCHER_PATH-':
            if values['-LAUNCHER_PATH-']: # Si le champ n'est pas vide
                window['-DEMARRER-'].update(visible=True)
            else: # Si le champ est vide
                window['-DEMARRER-'].update(visible=False)
            
        # --- Gestion du Démarrage ---
        if event == '-DEMARRER-' and not script_started:
            script_started = True
            # Mise à jour de l'interface
            window['-DEMARRER-'].update(disabled=True, text="En cours d'exécution...")
            window['-STOP-'].update(disabled=False)
            # On cache les éléments liés au chemin
            window['-PATH_TEXT-'].update(visible=False)
            window['-LAUNCHER_PATH-'].update(visible=False)
            window['-BROWSE-'].update(visible=False)

            print("\n" + "="*40)
            print("🚀 Lancement du script demandé par l'utilisateur...")
            print("="*40 + "\n")
            
            # Lancement du thread
            threading.Thread(target=script_logic, args=(window, values), daemon=True).start()

        # Gestion de l'affichage des logs
        if event == '-LOGUPDATE-':
            text_to_append = values['-LOGUPDATE-']
            window['-LOG-'].update(text_to_append, append=True)
            window['-LOG-'].Widget.see("end")
        
        if event == '-STOP-' or event == '-HOTKEY_STOP-':
            if event == '-HOTKEY_STOP-':
                print("\n🛑 Signal d'arrêt d'urgence (raccourci clavier) détecté. Arrêt du script...")
            else:
                print("\n🛑 Signal d'arrêt (bouton STOP) détecté. Arrêt du script...")
            break
            
    # --- Logique d'arrêt propre ---
    GUI_ACTIVE = False
    hotkey_listener.stop() # Arrête l'écouteur de raccourci clavier
    if mouse_listener and mouse_listener.is_alive():
        mouse_listener.stop()
        
    if last_position:
        x, y = last_position
        print(f"✅ - Dernière coordonnée capturée : X={x}, Y={y}.")
    
    print("\n🔚 Fermeture de la fenêtre.")
    
    # Restauration de la console standard avant de fermer
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    
    window.close()
    sys.exit(0)

if __name__ == "__main__":
    main()