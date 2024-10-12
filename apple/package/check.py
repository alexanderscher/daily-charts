import re


def smart_partial_match(label, text):
    # Normalize the text to lower case for case-insensitive matching
    normalized_text = text.lower()
    normalized_label = label.lower()
    pattern = r"(?:^|\s|,|/)" + re.escape(normalized_label) + r"(?:\s*[/,]\s*|\s|$)"

    return re.search(pattern, normalized_text) is not None


def check_prod(songs, artists, looped_song, looped_artist):
    def normalize_name_primary(name):
        """Normalize the name by removing common substrings and special characters."""
        name = name.strip().lower()
        name = name.split(" feat")[0].split(" ft")[0].split(" featuring")[0]
        name = name.split(" (")[0].split(" &")[0].split(", ")[0]
        name = name.replace("'", "").replace("’", "").replace(".", "")
        return name

    def normalize_name_secondary(name):
        """Normalize name by attempting to extract information after 'feat', 'ft', or 'featuring'."""
        parts = name.strip().lower().split()
        for i, part in enumerate(parts):
            if part in ["feat", "ft", "featuring"]:
                if i + 1 < len(parts):
                    return (
                        " ".join(parts[i + 1 :])
                        .replace("'", "")
                        .replace("’", "")
                        .replace(".", "")
                    )
        return name

    looped_song = normalize_name_primary(looped_song)
    looped_artist = normalize_name_primary(looped_artist)

    if looped_artist == "mgk":
        looped_artist = "machine gun kelly"

    found = False
    for song, artist in zip(songs, artists):
        song = normalize_name_primary(song)
        artist = normalize_name_primary(artist)

        if looped_song == song and looped_artist == artist:
            print(f"Found song: {song} by {artist}")
            found = True
            break

    if not found:
        looped_song = normalize_name_secondary(looped_song)
        looped_artist = normalize_name_secondary(looped_artist)
        for song, artist in zip(songs, artists):
            song = normalize_name_secondary(song)
            artist = normalize_name_secondary(artist)
            if looped_song == song and looped_artist == artist:
                print(f"Found song (secondary): {song} by {artist}")
                found = True
                break

    return found


passed = ["still over it"]


def check_prod_albums(songs, artists, looped_song, looped_artist):
    def normalize(name):
        name = name.strip().lower().replace("'", "").replace("’", "").replace(".", "")
        for delimiter in [" feat", " (", " &", " ,"]:
            name = name.split(delimiter)[0]
        return name

    if looped_artist.lower() == "mgk":
        looped_artist = "machine gun kelly"

    chart_song = normalize(looped_song)
    chart_artist = normalize(looped_artist)

    for song, artist in zip(songs, artists):
        if " - single" in song.lower():
            continue

        song_normalized = normalize(song)
        artist_normalized = normalize(artist)

        if song_normalized in chart_song and artist_normalized in chart_artist:
            if any(normalize(album) == chart_song for album in passed):
                return False
            print(f"Found album: {song} in {chart_song} - {artist} in {chart_artist}")
            return True

    return False
