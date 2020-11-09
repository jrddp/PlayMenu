#!/bin/env python3
from util import setup, get_args, add_uri_to_file


def add_uri_command(args):
    add_to_pls = args.use_playlists
    add_to_favs = not add_to_pls or args.use_favorites
    uris = args.uris

    for uri in uris:
        if uri in ('c', 'context'):
            from util import get_current_playback
            from spotify_item import SpotifyItem
            ctx: SpotifyItem
            _, ctx = get_current_playback()
            if ctx:
                uri = ctx.uri
            else:
                raise Exception("No context found!")

        if add_to_pls:
            from util import get_uri_type
            if (get_uri_type(uri) == "playlist"):
                add_uri_to_file(my_playlists_file, uri)
            else:
                raise Exception(f"Could not add uri to playlists: {uri} is not a playlist!")
        if add_to_favs:
            add_uri_to_file(favorites_file, uri)


if __name__ == '__main__':
    setup()

    args = get_args()

    action = args.action

    if action == "p" or action is None:
        from menus import play_menu
        play_menu()
    elif action == "s":
        from menus import save_menu
        save_menu()
    elif action == "a":
        from util import favorites_file, my_playlists_file
        add_uri_command(args=args)
    elif action == "sp":
        from menus import add_to_playlist_menu
        from util import my_playlists_file, get_current_track
        add_to_playlist_menu(my_playlists_file, get_current_track())