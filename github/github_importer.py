try:
    from urllib.request import urlopen
    from urllib.error import HTTPError, URLError
except ImportError:
    from urllib2 import urlopen, HTTPError, URLError
import ssl
import requests 

import zipfile
import tempfile
from io import BytesIO
import os
import json

from ..utils import utils
from ..utils.pathlib_wrapper import Path
from ..anki_importer import AnkiJsonImporter

import aqt.utils

from aqt import QInputDialog
from aqt import mw

class GithubImporter(object):
    """
    Provides functionality of installing shared deck from Github, by entering User and Repository names
    """

    def __init__(self, collection):
        self.collection = collection

    @staticmethod
    def on_github_import_action(collection):
        github_importer = GithubImporter(collection)
        github_importer.import_from_github()

    def import_from_github(self):
        repo, ok = QInputDialog.getText(None, 'Enter GitHub repository',
                                        'Path:', text='<name>/<repository>')
        if repo and ok:
            self.download_and_import(repo)

    @staticmethod
    def on_github_import_auto(collection):
        github_importer = GithubImporter(collection)
        config = mw.addonManager.getConfig(__name__)
        repos = config['Repo']
        for repo in repos:
            github_importer.download_and_import(repo)
            
    @staticmethod
    def on_github_export_auto(collection):
        aqt.utils.showWarning("Error")
        anki_json_exporter = AnkiJsonExporter(collection)
        
    def download_and_import(self, repo):
        
        config = mw.addonManager.getConfig(__name__)

        if not "sha" in config:
            config["sha"] = {}
            mw.addonManager.writeConfig(__name__, config)
        
        if not "md5" in config:
            config["md5"] = {}
            mw.addonManager.writeConfig(__name__, config)
            
        repo_link = 'https://api.github.com/repos/{0}/contents/'.format(repo)
        
        r = requests.get(repo_link)

        for link in r.json():
            if link["type"] != "file":
                continue
            if link["url"] in config["sha"]:
                if config["sha"][link["url"]] == link["sha"]:
                    continue
            # verified unmatching sha in valid file, now download.
            
            try:
                context = ssl._create_unverified_context()     # uncompresses repo
                response = urlopen(link["download_url"], context=context)
                response_sio = BytesIO(response.read())
                deck_name = link["path"].split(".")[0]
                deck_directory = Path(tempfile.tempdir).joinpath(deck_name)
                with zipfile.ZipFile(response_sio) as zip_file:
                    md5 = utils.md5_from_infolist(zip_file.infolist()) 
                    zip_file.extractall(str(deck_directory))

                AnkiJsonImporter.import_deck(self.collection, deck_directory, congrat=False)
                                
                utils.fs_remove(deck_directory) # cleanup

                config["sha"][link["url"]] = link["sha"]
                config["md5"][link["url"]] = md5
                mw.addonManager.writeConfig(__name__, config)   # successful import

            except (URLError, HTTPError, OSError) as error:
                aqt.utils.showWarning("Error while trying to get deck(s) from Github: {}".format(error))
                raise

