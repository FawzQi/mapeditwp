import os
import sys
import webview

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

if __name__ == '__main__':
    # Locate the built index.html inside the dist folder
    html_path = get_resource_path(os.path.join('dist', 'index.html'))
    
    # Launch a native window
    window = webview.create_window(
        title='Map Configurator',
        url=html_path,
        width=1400,
        height=900,
        resizable=True
    )
    
    # Start webview loop
    webview.start()

# pyinstaller --onefile --add-data "dist:dist" app.py 
# run command above to create a single executable file that includes the dist folder with the built Svelte app.