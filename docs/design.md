# Accessify

Accessify is a control interface for Spotify on Windows, designed to be accessible for screen reader users.  Until Spotify release an alternative to libspotify, it will use the standard Spotify Windows client for the actual playback of content.

## Features

### Search

High priority:

- Search for tracks, artists, albums and playlists.
- Play results continuously when one is selected for playback.
- Show the first 50 results by default, and fetch more as the user scrols down the list.

Medium priority:

- Cache results to speed up repeated searches.
- Store a history of previously performed searches and autocomplete as the user types.
- Opt to display saved albums/tracks at the top of search results.

Low priority:

- Bookmark favourite searchs for quick access.
- Give weights to autocomplete suggestions based on previous search frequency.
- Browse previous search history.
- Specify advanced search criteria in a dialog instead of using Spotify search modifiers e.g. artist and year directly.

Other ideas:

- Show frequently/recently played content first in results lists.
- Use croud-sourced data to provide search suggestions via an API.

### Playlist Management

Note: These features should be designed in line with how the Spotify playlists system works and is presented in their official apps.  Specifically:

- A playlist cannot be deleted or restored, only followed or unfollowed.
- The impression of playlist deletion in Spotify's own apps is achieved by unfollowing a playlist.
- When showing the list of a user's playlists within an official Spotify app, only followed ones are shown.

High priority:

- Create new playlists.
- List the playlists owned and followed by a user.
- Delete or rename user-owned playlists.
- Fetch and browse all tracks in a playlist.
- Remove tracks from a user-owned playlist.

Medium priority:

- Follow and unfollow other users' playlists.
- Filter or sort the tracks in a playlist.
- Reorder the tracks in user-owned playlists.
- Sort playlists into folders.
- Show a list of deleted playlists with the option to restore them (playlist recycle bin).

Low priority:

- Add labels to playlists e.g. instrumental, folk, exercise, shower.
- Set the public/collaborative flags and description for user-owned playlists.
- Replace tracks in a user-owned playlist.
- View previous snapshots for a playlist.

Other ideas:

<<<<<<< HEAD
- Copy/paste between playlists and other lists of content in the application (e.g. copy a search result onto a playlist) and cut/paste within the same playlist to reorder tracks.
- Create our own API for collaborating on a playlist as Spotify currently don't provide one.

### User Library

High priority:

- Save tracks and albums.
- List all saved tracks and albums.
- Remove saved tracks and albums.

Medium priority:

- Sort and filter saved tracks and albums.
- Browse a list of saved artists, made up of the artists for currently saved tracks and albums plus any artists the user follows.
- Browse a list of the user's recently played tracks.

Low priority:

- Browse a separate list of artists that the user follows.
- Follow/unfollow artists.
- Browse a list of the user's top artists or tracks.

### Browse

- Featured playlists.
- New releases.
- Categories and playlists for each category.

### Playback Control

High priority:

- Play/pause, previous/next track, seek backwards/forwards, volume up/down.
- Copy the Spotify URI for the currently playing track to the clipboard.
- Transfer playback to an alternative Spotify Connect device (Premium users only).
- Start playback of a given URI, handling both the standard URI format and HTTP/HTTPS links (open.spotify.com/play.spotify.com/etc).

Medium priority:

- Jump to time in currently playing track.
- Provide a Windows URI handler to play URIs from the Run dialog, web pages etc, intercepting Spotify's default handling.

Low priority:

- Copy the Spotify URI for the currently playing track to the clipboard including current playback position.

Other ideas:

- Shuffle and repeat.  Lots of details to be worked out, it might be best to wait until we have native playback capability to implement them.

=======
- Copy/paste between playlists and other lists of content in the application (e.g. copy a search result onto a playlist).
- Create our own API for collaborating on a playlist as Spotify currently don't provide one.

>>>>>>> 14a402986eed2b6294eea0d1ccc7dfa741e825e5
