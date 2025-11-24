import tkinter as tk
import sys

try:
    # Tente de créer une fenêtre Tkinter minimale
    root = tk.Tk()
    root.title("Test Tkinter Réussi")
    label = tk.Label(root, text="Tkinter fonctionne correctement dans ce Venv.")
    label.pack()
    print("✅ Tkinter a démarré la boucle de la GUI. La fenêtre devrait apparaître.")
    root.mainloop() 
except Exception as e:
    # Si cette erreur se produit, Tkinter est manquant ou corrompu
    print(f"❌ Échec du test Tkinter : {e}")
    print("\nLe problème est que votre Venv n'a pas accès au support GUI (Tkinter).")
    sys.exit(1)