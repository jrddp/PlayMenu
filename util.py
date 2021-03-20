from configparser import ConfigParser
from pathlib import Path

cache_dir = Path.home() / ".cache" / "play-menu"
config_dir = Path.home() / ".config" / "play-menu"

favorites_file = config_dir / "favorites.txt"
my_playlists_file = config_dir / "my_playlists.txt"

file_delim = '\t'

config_file: Path = config_dir / "play-menu.conf"
oauth_file = cache_dir / "auth.json"

img_ext = "jpg"
img_res = (64, 64)

_spotify = None


def ensure_dir_exists(dir_path: Path):
    if not dir_path.exists():
        dir_path.mkdir()


def get_uri_from_url(url):
    spl = url.rsplit("/", 2)
    return "spotify:{}:{}".format(spl[-2], spl[-1])


def get_config():
    config = ConfigParser()
    if config_file.exists():
        config.read(config_file)
    else:
        gen_config(config)
    return config


def gen_config(config):
    client_id = input("Enter Spotify client id: ")
    client_secret = input("Enter Spotify client secret: ")
    config["Authentication"] = {"clientId": client_id, "clientSecret": client_secret}
    with config_file.open("w") as file:
        config.write(file)


def get_spotify():
    global _spotify
    if not _spotify:
        from spotipy import Spotify, SpotifyOAuth

        scopes = {"user-read-playback-state", "user-modify-playback-state", "user-follow-modify", "user-library-read",
                  "user-library-modify", "user-modify-playback-state", "playlist-modify-public",
                  "playlist-modify-private"}

        config = get_config()
        client_id = config["Authentication"]["clientId"]
        client_secret = config["Authentication"]["clientSecret"]

        o_auth = SpotifyOAuth(client_id=client_id, client_secret=client_secret,
                              redirect_uri="http://localhost:8080/callback", scope=" ".join(scopes),
                              cache_path=oauth_file)
        _spotify = Spotify(oauth_manager=o_auth)
    return _spotify


def get_spotify_dbus_object():
    import dbus
    session_bus = dbus.SessionBus()
    # gets spotify as a remote proxy object
    return session_bus.get_object(
        "org.mpris.MediaPlayer2.spotify",
        "/org/mpris/MediaPlayer2")


def play_uri(uri):
    import dbus
    player_interface = dbus.Interface(get_spotify_dbus_object(), "org.mpris.MediaPlayer2.Player")
    player_interface.OpenUri(uri)


def set_shuffle(state: bool):
    get_spotify().shuffle(state)


def get_current_track():
    import dbus
    from spotify_item import Album, Track

    spotify_dbus = get_spotify_dbus_object()
    metadata = spotify_dbus.Get("org.mpris.MediaPlayer2.Player", "Metadata", dbus_interface=dbus.PROPERTIES_IFACE)

    def from_metadata(key: str):
        value = metadata[dbus.String(key)]
        if isinstance(value, dbus.Array):
            return [str(v) for v in value]
        return str(value)

    img_url = from_metadata('mpris:artUrl')

    album = Album(name=from_metadata('xesam:album'), artists=from_metadata('xesam:albumArtist'), uri=None,
                  img_url=img_url)
    track = Track(name=from_metadata('xesam:title'), artists=from_metadata('xesam:artist'),
                  uri=from_metadata('mpris:trackid'), album=album, img_url=img_url)

    return track


# tuple(track, context)
def get_current_playback():
    from spotify_item import SpotifyItem, Track

    data = get_spotify().current_playback()
    if not data: return None, None

    item_data = data['item']
    context_data = data['context']

    item: Track = Track.from_data(item_data) if item_data else None
    context: SpotifyItem = SpotifyItem.from_uri(context_data['uri']) if context_data else None

    return item, context


# returns the smallest image above img_res (based on width)
def get_best_img_from_list(images: list):
    if not images: return None
    if len(images) == 1: return images[0]
    images = filter(lambda img: img['width'] > img_res[0], images)
    return min(images, key=lambda img: img['width'])


def get_uri_type(uri: str):
    return uri.split(':')[-2]


def save_img_url(img_url: str, img_path: Path):
    from PIL import Image
    from urllib import request

    img = Image.open(request.urlretrieve(img_url)[0])
    img = img.resize(img_res)
    img.save(img_path)


def add_icon_to_str(string: str, icon: str):
    return f"{string}\0icon\x1f{icon}"


def setup():
    ensure_dir_exists(config_dir)
    ensure_dir_exists(cache_dir)


def get_args():
    from argparse import ArgumentParser
    parser = ArgumentParser(description="Manage Spotify using Rofi")
    subparsers = parser.add_subparsers(title="actions", dest="action")

    subparsers.add_parser("p", description="Open play menu", help="Open play menu")
    subparsers.add_parser("s", description="Open save menu", help="Open save menu")
    subparsers.add_parser("sp", description="Open add-to-playlist menu", help="Open add-to-playlist menu")

    add_subparser = subparsers.add_parser("a", description="Add uri to file", help="Add uri")

    add_subparser.add_argument("-f", "--favorites", help="Use favorites file", action='store_true',
                               dest="use_favorites")
    add_subparser.add_argument("-p", "--playlists", help="Use playlists file", action='store_true',
                               dest="use_playlists")
    add_subparser.add_argument("uris", nargs='+',
                               help="Spotify URI, use 'context' or 'c' to add the current Spotify context")

    return parser.parse_args()


def add_uri_to_file(file_path: Path, uri: str):
    from spotify_item import Favorites
    favs = Favorites.from_file(file_path)
    favs.add_uri(uri)
    favs.write(file_path)
    print(f"Added {uri} to {file_path}")


def notify_send(message: str, image: Path = None):
    import subprocess
    command = ['notify-send', message]
    if image:
        command.extend(['-i', str(image)])
    subprocess.Popen(command)


def notify_context():
    from spotify_item import Track, SpotifyItem

    track: Track
    context: SpotifyItem

    track, context = get_current_playback()

    if context:
        context.save_img()

    notify_send(f"Spotify context:\n{repr(context)}", image=context.get_img_path() if context else None)
