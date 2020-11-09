from pathlib import Path
from rofi import Rofi

from util import get_current_track, add_icon_to_str, favorites_file
from spotify_item import Favorites, Track


def prompt_menu(question: str, no_first=True, str_yes="Yes", str_no="No"):
    r = Rofi(rofi_args=["-i"])

    str_yes = add_icon_to_str(str_yes, "object-select")
    str_no = add_icon_to_str(str_no, "window-close")

    options = [str_no, str_yes] if no_first else [str_yes, str_no]
    index, _ = r.select(question, options)
    if index == -1: return False
    return options[index] == str_yes


def play_menu(path: Path = favorites_file):
    favs = Favorites.from_file(path)

    favs.save_all_images()

    rofi = Rofi(rofi_args=["-no-sort", "-i", "-matching", "fuzzy"])
    index, key = rofi.select("Play", favs.get_display_list(detail=2),
                             key1=("Alt+Shift+Return", "Play without shuffle\n"),
                             key2=("Alt+Return", "Play with shuffle\n"),
                             key8=("Alt+p", "Search Spotify\n"),
                             key9=("Alt+X", "Remove from menu"))

    # escape key/exit was pressed
    if index == -1:
        return

    # search button pressed
    if key == 8:
        search_menu()
        return

    item = favs.items[index]

    # remove from menu
    if key == 9:
        remove = prompt_menu(f"Remove {repr(item)} from favorites?", no_first=True)
        if remove:
            favs.remove_item(item)
            favs.write()
        return

    # play without shuffle
    if key == 1:
        from util import set_shuffle
        set_shuffle(False)
    # play with shuffle
    elif key == 2:
        from util import set_shuffle
        set_shuffle(True)

    favs.bring_to_top(item)
    favs.write(path)

    item.play()


def save_menu():
    from collections import OrderedDict
    from spotify_item import SpotifyItem
    from util import my_playlists_file, notify_context

    rofi = Rofi(rofi_args=["-no-sort", "-i"])

    track: Track = get_current_track()

    options = OrderedDict()

    options[add_icon_to_str("Save Song", "emblem-favorite")] = track.save
    options[add_icon_to_str("Add song to playlist", "list-add")] = lambda: add_to_playlist_menu(my_playlists_file,
                                                                                                track)
    options[add_icon_to_str("Play track album", "media-playback-start")] = lambda: SpotifyItem.from_uri(
        track.uri).album.play()
    options[add_icon_to_str("Query context", "dialog-question")] = lambda: notify_context()
    options[add_icon_to_str("Remove song", "user-trash")] = track.unsave
    index, key = rofi.select("Music", list(options.keys()), message=rofi.escape(str(track)))

    # user escape/quit
    if index == -1:
        return

    # call the lambda at the chosen index
    list(options.values())[index]()


def add_to_playlist_menu(playlist_path: Path, track: Track):
    from spotify_item import Playlist

    pls = Favorites.from_file(playlist_path)

    pls.save_all_images()

    rofi = Rofi(rofi_args=["-no-sort", "-i"])
    index, key = rofi.select(f"Add \"{track}\" to playlist", pls.get_display_list(detail=0),
                             key9=("Alt-X", "Remove Playlist"))

    # escape key/exit was pressed
    if index == -1:
        return

    playlist = pls.items[index]

    # remove playlist
    if key == 9:
        remove = prompt_menu(f"Remove {playlist} from playlists?", no_first=True)
        if remove:
            pls.remove_item(playlist)
            pls.write(playlist_path)
        return

    if isinstance(playlist, Playlist):
        if prompt_menu(f"Add {track} to {playlist.name}?", no_first=False):
            playlist.add_item(track)


def search_menu():
    from spotify_search import play_search
    r = Rofi()

    play_search(r.text_entry("Play Song"))
