from pathlib import Path
from typing import List

from util import get_spotify, play_uri, get_best_img_from_list, save_img_url, add_icon_to_str


class SpotifyItem:
    type: str = None
    _img_url: str = None

    def __init__(self, name: str, artists: list, uri: str, img_url: str = None):
        self.name = name
        self.artists = artists
        self.uri = uri
        self._img_url = img_url

    def get_id(self):
        return self.uri.split(":")[-1]

    def play(self):
        if self.uri:
            print(f"Playing {repr(self)}")
            play_uri(self.uri)
        else:
            raise Exception(f"No uri available for {self}")

    # cache_dir/id.jpg
    def get_img_path(self):
        from util import cache_dir, img_ext
        return cache_dir / f"{self.get_id()}.{img_ext}"

    def get_img_url(self):
        if not self._img_url and self.uri:
            images = self.get_data(self.uri)['images']
            best_img = get_best_img_from_list(images)
            if best_img:
                self._img_url = best_img['url']
        return self._img_url

    def is_img_saved(self):
        path = self.get_img_path()
        return path and path.exists()

    def save_img(self):
        img_url = self.get_img_url()
        if img_url:
            print(f"Saving image for {self}")
            save_img_url(self.get_img_url(), self.get_img_path())
        else:
            print(f"Could not find image url for {self}")

    def __str__(self) -> str:
        string = self.name
        if self.artists:
            string += f" by {', '.join(self.artists)}"
        return string

    def __repr__(self) -> str:
        return f"{self} ({self.type.title()})"

    # the string to be stored in a file when saving
    def to_file_entry(self):
        from util import file_delim

        return file_delim.join((self.type, self.name, ",".join(self.artists), self.uri)) + "\n"

    @staticmethod
    def from_file_entry(entry: str):
        from util import file_delim

        entry = entry.strip()
        fields = entry.split(file_delim)

        type = fields[0]
        name = fields[1]
        artists = fields[2].split(',') if fields[2] else []
        uri = fields[3]

        for _class in (Playlist, Album, Artist, Track):
            if _class.type == type:
                return _class(name=name, artists=artists, uri=uri)

    @staticmethod
    def from_uri(uri: str):
        from util import get_uri_type

        uri_type = get_uri_type(uri)
        for _class in (Playlist, Album, Artist, Track):
            if _class.type == uri_type:
                return _class.from_data(_class.get_data(uri))
        raise (TypeError(f"Invalid item type: {uri_type}"))

    @staticmethod
    def get_data(uri: str):
        uri_type = uri.split(':')[1]
        for _class in (Playlist, Album, Artist, Track):
            if _class.type == uri_type:
                return _class.get_data(uri)
        raise (TypeError(f"Invalid item type: {uri_type}"))


class Playlist(SpotifyItem):
    type = "playlist"

    def add_item(self, item: SpotifyItem):
        from util import notify_send, get_spotify

        if self.contains_uri(item.uri):
            notify_send(f"Playlist {self.name} already contains song\n{str(item)}")
        else:
            get_spotify().playlist_add_items(self.uri, [item.uri])
            notify_send(f"Added track to {self.name}\n{str(item)}", image=self.get_img_path())



    def get_items(self):
        from util import get_spotify
        spotify = get_spotify()
        data = spotify.playlist_items(self.uri)

        items: List[SpotifyItem] = []

        while True:
            for item in data['items']:
                item = item['track']
                if item:
                    items.append(Track.from_data(item))
            if data['next']:
                data = spotify.next(data)
            else:
                break

        return items

    def contains_uri(self, uri: str):
        from util import get_spotify
        spotify = get_spotify()
        data = spotify.playlist_items(self.uri)

        while True:
            for item in data['items']:
                item = item['track']
                if item:
                    item_uri = item['uri']
                    if item_uri == uri:
                        return True
            if data['next']:
                data = spotify.next(data)
            else:
                return False

    @staticmethod
    def from_data(data):
        img_url = None
        if 'images' in data:
            img_url = get_best_img_from_list(data['images'])['url']
        return Playlist(uri=data['uri'], name=data['name'], artists=[data['owner']['display_name']], img_url=img_url)

    @staticmethod
    def get_data(uri):
        return get_spotify().playlist(uri, fields="uri, name, owner, images")


class Album(SpotifyItem):
    type = "album"

    @staticmethod
    def from_data(data: dict):
        img_url = None
        artists = [artist['name'] for artist in data['artists']]
        if 'images' in data:
            best_img = get_best_img_from_list(data['images'])
            if best_img:
                img_url = best_img['url']
        return Album(uri=data.get('uri'), name=data['name'], artists=artists, img_url=img_url)

    @staticmethod
    def get_data(uri):
        return get_spotify().album(uri)


class Artist(SpotifyItem):
    type = "artist"

    @staticmethod
    def from_data(data):
        img_url = None
        if 'images' in data:
            img_url = get_best_img_from_list(data['images'])['url']
        return Artist(uri=data['uri'], name=data['name'], artists=[], img_url=img_url)

    @staticmethod
    def get_data(uri):
        return get_spotify().artist(uri)


class Track(SpotifyItem):
    type = "track"

    def __init__(self, name: str, artists: list, uri: str, img_url: str = None, album: Album = None):
        super().__init__(name, artists, uri, img_url)
        self.album = album

    def save(self):
        from util import notify_send

        spotify = get_spotify()
        if self.is_saved():
            notify_send(f"Song already saved:\n{self}")
        else:
            spotify.current_user_saved_tracks_add([self.uri])
            notify_send(f"Saved song:\n{self}")

    def unsave(self):
        from util import notify_send

        spotify = get_spotify()
        if not self.is_saved():
            notify_send(f"Cannot remove song:\n{self}\nSong is not saved")
        else:
            spotify.current_user_saved_tracks_delete([self.uri])
            notify_send(f"Removed song:\n{self}")

    def is_saved(self):
        return get_spotify().current_user_saved_tracks_contains([self.uri])[0]

    def get_img_url(self):
        if not self._img_url:
            images = get_spotify().album(self.uri)['images']
            self._img_url = get_best_img_from_list(images)['url']
        return self._img_url

    def get_img_path(self):
        if self.album and self.album.uri:
            return self.album.get_img_path()
        return super().get_img_path()

    @staticmethod
    def from_data(data):
        img_url = None
        album = None
        if 'album' in data:
            album = Album.from_data(data['album'])
            img_url = album.get_img_url()
        artists = [artist['name'] for artist in data['artists']]
        return Track(uri=data['uri'], name=data['name'], artists=artists, img_url=img_url, album=album)

    @staticmethod
    def get_data(uri):
        return get_spotify().track(uri)


# manages lists of SpotifyItems
class Favorites:

    def __init__(self, items: List[SpotifyItem]):
        self.items = items

    def add_item(self, item):
        self.items.append(item)

    def add_uri(self, uri: str):
        # allows usage with uri
        duplicates = filter(lambda item: item.uri == uri, self.items)
        for dupe in duplicates:
            print(f"Found duplicate: {dupe}")
            self.remove_item(dupe)

        item = SpotifyItem.from_uri(uri)
        self.add_item(item)
        if not item.is_img_saved(): item.save_img()

    def remove_item(self, item):
        print(f"Removing {item}")
        self.items.remove(item)

    def play_random(self):
        import random
        random.choice(self.items).play()

    def bring_to_top(self, item: SpotifyItem):
        self.items.insert(0, self.items.pop(self.items.index(item)))

    # saves images of all items if they aren't already in cache
    def save_all_images(self):
        for item in self.items:
            if not item.is_img_saved():
                item.save_img()

    # dictionary from str(item) to item for rofi menus
    # detail: 2: include name, type and artist
    #         1: include name and artist
    #         0: include name
    def get_display_list(self, detail=2):
        if detail == 0:
            to_str = lambda s: s.name
        elif detail == 1:
            to_str = lambda s: str(s)
        else:
            to_str = lambda s: repr(s)
        return [add_icon_to_str(to_str(item), item.get_img_path()) for item in
                self.items]

    def write(self, file_path: Path):
        with file_path.open("w") as f:
            f.writelines([item.to_file_entry() for item in self.items])

    @staticmethod
    def from_file(file_path: Path):

        favs = Favorites([])
        if file_path.exists():
            with file_path.open("r") as f:
                for line in f:
                    favs.add_item(SpotifyItem.from_file_entry(line))

        return favs

    # will attempt to grab uris no matter what format the file is in
    @staticmethod
    def from_file_advanced_detect(file_path: Path):
        import re
        regex = re.compile(r"spotify:[a-z]*:[a-zA-Z0-9]+")

        favs = Favorites([])
        with file_path.open("r") as f:
            for line in f:
                for uri in regex.findall(line):
                    favs.add_uri(uri)

        return favs
