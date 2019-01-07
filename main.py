from .utils.pathlib_wrapper import Path

from . import anki_exporter_wrapper  # Do not remove. To hook exporters list extension
from .anki_importer import AnkiJsonImporter
from .anki_exporter import AnkiJsonExporter
from .github.github_importer import GithubImporter

import aqt.utils
from aqt.utils import showInfo, showWarning, askUser
from aqt import mw, QApplication, QAction, QFileDialog, QInputDialog
from anki.hooks import addHook

def main():
    """
    Todo: Implement command line interface
    """


def on_import_action():
    directory_path = str(QFileDialog.getExistingDirectory(caption="Select Deck Directory"))
    if not directory_path:
        return

    import_directory = Path(directory_path)
    AnkiJsonImporter.import_deck(aqt.mw.col, import_directory)


def on_export_action():
    config = mw.addonManager.getConfig(__name__)
    if 'repo' in config:
        repo = config.get('repo')
    else:        
        repo, ok = QInputDialog.getText(None, 'Enter GitHub repository',
                                        'The Github Repo Path is not set. Please provide the repo path that you would like to sync with. \nPath:', text='<name>/<repository>')
        if repo and ok:
            config['repo'] = repo
            mw.addonManager.writeConfig(__name__, config)
    
    if 'token' in config:
        token = config.get('token')
    else:        
        token, ok = QInputDialog.getText(None, 'Enter GitHub token',
                                        'The Github Token is not set. It is essential for the sync function to work. \nToken:', text='00xxxxxxxxxxxxxxxxxxxx00')
        if token and ok:
            config['token'] = token
            mw.addonManager.writeConfig(__name__, config)
    
    if 'user' in config:
        user = config.get('user')
    else:        
        user, ok = QInputDialog.getText(None, 'Enter User Name',
                                        'The User Name is not set. But it really helps identify who made the changes on the collab anki. \nUser Name:', text='John Doe')
        if user and ok:
            config['user'] = user
            mw.addonManager.writeConfig(__name__, config)
            
    decks = mw.col.decks.all()
    uploaddecks = []
    for deck in decks:
        if 'crowdanki_uuid' in deck:
            uploaddecks.append(deck)
    if repo and decks and askUser("Downloading decks from {0}, proceed?".format(repo)):
        mw.progress.start(max=len(decks), min=0, immediate=True)
        QApplication.processEvents()
        importer = GithubImporter(aqt.mw.col)
        importer.download_and_import(repo)
        mw.progress.update()        
        mw.progress.finish()
    if repo and decks and askUser("Uploading {0} deck(s) to {1}, proceed?".format(len(uploaddecks), repo)):
        mw.progress.start(max=len(uploaddecks), min=0, immediate=True)
        QApplication.processEvents()
        exporter = AnkiJsonExporter(aqt.mw.col)
        for count, deck in enumerate(uploaddecks, 1):            
            QApplication.processEvents()
            if deck["id"] != 1:
                exporter.export_deck_to_github(deck["name"])
            mw.progress.update()
        
        mw.progress.finish()
        showInfo("Successfully Uploaded.")        

def anki_import_init():
    config = mw.addonManager.getConfig(__name__)
    if 'token' in config and 'repo' in config:
        text = "AnkiCollab: Sync with {}".format(config['repo'])
    else:
        text = "AnkiCollab: Setup Sync"
    github_import_action = QAction(text, mw)
    github_import_action.triggered.connect(on_export_action)

    # -2 supposed to give the separator after import/export section, so button should be at the end of this section
    mw.form.menuCol.insertActions(mw.form.menuCol.actions()[-2], [github_import_action])


def anki_init():
    if mw:
        anki_import_init()


if __name__ == "__main__":
    main()
else:
    anki_init()

"""
Warning:
Creation of collection has a side effect of changing current directory to ${collection_path}/collection.media
"""
