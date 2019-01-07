import os
import pprint
import json
import shutil
import zipfile
import base64
import tempfile

import aqt
import aqt.utils
import anki.utils
from aqt import mw

from .utils.pathlib_wrapper import Path
from .utils import utils

from .utils.constants import DECK_FILE_EXTENSION, MEDIA_SUBDIRECTORY_NAME, DECK_ZIP_EXTENSION
from .representation.deck import Deck

import requests 
from .thirdparty.uritemplate.template import URITemplate


class AnkiJsonExporter(object):
    def __init__(self, collection):
        self.collection = collection
        self.last_exported_count = 0

    @staticmethod
    def _get_filesystem_name(deck_name):
        """
        Get name that conforms to fs standards from deck name
        :param deck_name:
        :return:
        """
        for char in anki.utils.invalidFilenameChars + " ":
            deck_name = deck_name.replace(char, "_")

        return deck_name

    def export_deck_to_directory(self, deck_name, output_dir=Path("."), copy_media=True):
        deck_fsname = self._get_filesystem_name(deck_name)
        deck_directory = output_dir.joinpath(deck_fsname)

        deck_directory.mkdir(parents=True, exist_ok=True)

        deck = Deck.from_collection(mw.col, deck_name)
        self.last_exported_count = deck.get_note_count()

        deck_filename = deck_directory.joinpath(deck_fsname).with_suffix(DECK_FILE_EXTENSION)
        with deck_filename.open(mode='w', encoding="utf8") as deck_file:
            deck_file.write(json.dumps(deck,
                                       default=Deck.default_json,
                                       sort_keys=True,
                                       indent=4,
                                       ensure_ascii=False))

        self._save_changes()

        if copy_media:
            self._copy_media(deck, deck_directory)

        return deck_directory

    def _save_changes(self):
        """Save updates that were maid during the export. E.g. UUID fields"""
        # This saves decks and deck configurations
        self.collection.decks.save()
        self.collection.decks.flush()

        self.collection.models.save()
        self.collection.models.flush()

        # Notes?

    def _copy_media(self, deck, deck_directory):
        media_directory = deck_directory.joinpath(MEDIA_SUBDIRECTORY_NAME)

        media_directory.mkdir(parents=True, exist_ok=True)

        for file_src in deck.get_media_file_list():
            try:
                shutil.copy(os.path.join(self.collection.media.dir(), file_src),
                            str(media_directory.resolve()))
            except IOError as ioerror:
                print("Failed to copy a file {}. Full error: {}".format(file_src, ioerror))

    def export_deck_to_github(self, deck_name):
        deck_fsname = self._get_filesystem_name(deck_name)
        temp_directory = Path(tempfile.tempdir)
        deck_directory = self.export_deck_to_directory(deck_name, temp_directory)

        zip_filename = shutil.make_archive(deck_directory, DECK_ZIP_EXTENSION, deck_directory)
        self.upload_to_github(deck_fsname+".zip", zip_filename)
        utils.fs_remove(deck_directory)
        utils.fs_remove(Path(zip_filename))

    def upload_to_github(self, file_name, file_path):
        config = mw.addonManager.getConfig(__name__)
        repo = config["repo"]
        access_token = config["token"]
        file_link = 'https://api.github.com/repos/{0}/contents/{1}'.format(repo, file_name)

        r = requests.get(file_link)

        headers = {
            'Content-Type': 'application/gzip',
            'Authorization': 'Token {0}'.format(access_token)
        }

        with open(file_path, 'rb') as zip_file:
            encoded_string = base64.b64encode(zip_file.read()).decode('ascii')

        user = config.get('user', "Anonymous User")

        params = {
            "message": "Upload by {}".format(user),
            "content": encoded_string
        }
        

        if not "md5" in config:
            config["md5"] = {}        

        md5 = ""
        
        with zipfile.ZipFile(file_path) as zip_file:
            md5 = utils.md5_from_infolist(zip_file.infolist()) 
                
        if r.json()["url"] in config["md5"]:
            if config["md5"][r.json()["url"]] == md5:
                return
            
        if "sha" in r.json():
            sha = r.json()["sha"]
            params["sha"] = sha
            
        config["md5"][r.json()["url"]] = md5
            
        r = requests.put(
            file_link,
            headers = headers, 
            data = json.dumps(params)
        )       

        if "content" in r.json():
            if "sha" in r.json()["content"]:
                config["sha"][r.json()["content"]["url"]] = r.json()["content"]["sha"]

        mw.addonManager.writeConfig(__name__, config)
