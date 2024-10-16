import requests
from datetime import datetime, timedelta
import base64
from urllib.parse import urlencode
import time
import re
from pytz import timezone

pacific_tz = timezone("America/Los_Angeles")


class SpotifyAPI(object):
    access_token = None
    access_token_expires = datetime.now()
    access_token_did_expire = True
    client_id = None
    user_id = None
    client_secret = None
    oauth_token = None
    token_url = "https://accounts.spotify.com/api/token"
    redirect_uri = "http://localhost:8888/callback"

    refresh_token = None
    token_created_at = datetime.now()
    redirect_uri = "http://localhost:8888/callback"
    auth_code = "AQCDkqsbi-oT6fd6EXOM-AXDmERQgZJoQYvA2yemw7KdGK3pnGIigUrrffEBi24CkLvNYGz2kqNrzE8PeljqqWcEjyfeby0VTAJSRpd_aHeb1Scjw0KqiaSDK2AXwzbTfOhRJmhlX0uJWpZ5LjySKSrYODXDa_oa7A3QW4f4HJgnJ5fbTsrlYUnS6b-H6wgbfI5BkBehXTLB21dONqDHe9c3lTjBVI0ZDZ9bTokVw2HWr1j_t_VIw2nx_mGmuBoMHLbfWafXhmKzGA"
    access_token_p = None

    def __init__(self, client_id, user_id, client_secret, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_id = client_id
        self.user_id = user_id
        self.client_secret = client_secret
        self.velocity_df = []

    def get_client_credentials(self):
        """
        Returns a base64 encoded string
        """
        client_id = self.client_id
        client_secret = self.client_secret
        if client_secret == None or client_id == None:
            raise Exception("You must set client_id and client_secret")
        client_creds = f"{client_id}:{client_secret}"
        client_creds_b64 = base64.b64encode(client_creds.encode())
        return client_creds_b64.decode()

    def get_token_headers(self):
        client_creds_b64 = self.get_client_credentials()
        return {"Authorization": f"Basic {client_creds_b64}"}

    def get_token_data(self):
        return {"grant_type": "client_credentials"}

    def perform_auth(self):
        token_url = self.token_url
        token_data = self.get_token_data()
        token_headers = self.get_token_headers()
        r = requests.post(token_url, data=token_data, headers=token_headers)
        if r.status_code not in range(200, 299):
            raise Exception("Could not authenticate client.")
        data = r.json()
        now = datetime.now()
        access_token = data["access_token"]
        expires_in = data["expires_in"]
        expires = now + timedelta(seconds=expires_in)
        self.access_token = access_token
        self.access_token_expires = expires
        self.access_token_did_expire = expires < now
        return True

    def get_access_token(self):
        token = self.access_token
        expired = self.access_token_did_expire
        if token == None or expired:
            self.perform_auth()
            return self.get_access_token()
        return token

    def get_artist_copy(self, artist_name, coming_from, search_type="artist", offset=0):
        try:
            access_token = self.get_access_token()
            headers = {"Authorization": f"Bearer {access_token}"}
            endpoint = "https://api.spotify.com/v1/search"
            data = urlencode(
                {"q": artist_name, "type": search_type, "limit": 50, "offset": offset}
            )
            lookup_url = f"{endpoint}?{data}"

            with requests.get(lookup_url, headers=headers) as r:
                if r.status_code not in range(200, 299):
                    if r.status_code == 404:
                        time.sleep(10)
                        with requests.get(lookup_url, headers=headers) as retry_r:
                            if retry_r.status_code == 404:
                                return None
                    elif r.status_code == 400:
                        return None
                resp = r.json()

            def refine_artist_name(name, source):
                split_terms = {
                    "daily_chart": [
                        ", ",
                        " (",
                        " (@",
                        " featuring ",
                        " feat. ",
                        "Genius English Translations - ",
                        " X ",
                        " / ",
                    ],
                    "spotify": [", ", " (", " featuring ", "feat."],
                    "shazam": [", ", " & ", " X "],
                }
                for term in split_terms.get(source, []):
                    if term in name:
                        return name.split(term)[0]
                return name

            refined_name = refine_artist_name(artist_name, coming_from)

            if refined_name != artist_name:
                return self.get_artist_copy(
                    refined_name, coming_from, search_type, offset
                )

            for artist in resp.get("artists", {}).get("items", []):
                if (
                    artist_name.lower() == artist["name"].lower()
                    and artist["popularity"] > 5
                ):
                    artist_id = artist["id"]
                    albums_endpoint = f"https://api.spotify.com/v1/artists/{artist_id}/albums?include_groups=album,single"
                    with requests.get(albums_endpoint, headers=headers) as r_album:
                        albums_resp = r_album.json()

                    filtered_items = [
                        item
                        for item in albums_resp.get("items", [])
                        if item["artists"][0]["name"].lower() == artist_name.lower()
                    ]
                    if not filtered_items:
                        return ("Not On Spotify: Look Up", None)

                    latest_album = sorted(
                        filtered_items, key=lambda x: x["release_date"], reverse=True
                    )[0]
                    album_id = latest_album["id"]
                    album_endpoint = f"https://api.spotify.com/v1/albums/{album_id}"
                    with requests.get(
                        album_endpoint, headers=headers
                    ) as album_response:
                        album_data = album_response.json()

                    if "copyrights" in album_data and album_data["copyrights"]:
                        copyright = album_data["copyrights"][0]["text"]
                        url = album_data["artists"][0]["external_urls"]["spotify"]

                        return (copyright, url)
                    else:
                        return ("No Copyright Information", None)

        except Exception as e:
            print(f"Exception: {e}")
            time.sleep(30)
            return self.get_artist_copy(artist_name, coming_from, search_type, offset)

    def get_artist_copy_track(
        self,
        artist_name,
        track,
        coming_from,
        search_type="artist",
        offset=0,
    ):
        try:
            access_token = self.get_access_token()
            headers = {"Authorization": f"Bearer {access_token}"}
            endpoint = "https://api.spotify.com/v1/search"
            data = urlencode(
                {"q": artist_name, "type": search_type, "limit": 50, "offset": offset}
            )
            lookup_url = f"{endpoint}?{data}"

            with requests.get(lookup_url, headers=headers) as r:
                if r.status_code not in range(200, 299):
                    if r.status_code == 404:
                        time.sleep(10)
                        with requests.get(lookup_url, headers=headers) as retry_r:
                            if retry_r.status_code == 404:
                                return None
                    elif r.status_code == 400:
                        return None
                resp = r.json()

            def refine_artist_name(name, source):
                split_terms = {
                    "daily_chart": [
                        ", ",
                        " (",
                        " (@",
                        " featuring ",
                        " feat. ",
                        "Genius English Translations - ",
                        " X ",
                        " / ",
                    ],
                    "spotify": [", ", " (", " featuring ", "feat."],
                    "shazam": [", ", " & ", " X "],
                }
                for term in split_terms.get(source, []):
                    if term in name:
                        return name.split(term)[0]
                return name

            refined_name = refine_artist_name(artist_name, coming_from)

            if refined_name != artist_name:
                return self.get_artist_copy_track(
                    refined_name, coming_from, search_type, offset
                )

            for artist in resp.get("artists", {}).get("items", []):
                if artist_name.lower() == artist["name"].lower():
                    artist_id = artist["id"]
                    endpoint = f"https://api.spotify.com/v1/artists/{artist_id}/albums?include_groups=album,single"

                    all_albums = []
                    previous_length = 0

                    while endpoint:
                        r = requests.get(endpoint, headers=headers)

                        if r.status_code not in range(200, 299):
                            if r.status_code == 404:
                                time.sleep(10)
                                continue
                            elif r.status_code == 400:
                                print("Bad request")
                                break
                        resp = r.json()
                        items = resp.get("items", [])
                        all_albums.extend(items)

                        if len(all_albums) > 200:
                            artist_copy = self.get_artist_copy(artist_name, coming_from)
                            return artist_copy

                        if len(all_albums) == previous_length:
                            break

                        previous_length = len(all_albums)
                        endpoint = resp.get("next")

                        if not endpoint:
                            break

                    url = None
                    label = None
                    album_data = None
                    artist_url = None

                    for item in all_albums:
                        album_id = item["id"]
                        endpoint = (
                            f" https://api.spotify.com/v1/albums/{album_id}/tracks"
                        )
                        r = requests.get(endpoint, headers=headers)
                        resp = r.json()
                        found = False

                        for artist in item["artists"]:
                            if artist["name"].lower() == artist_name.lower():
                                artist_url = artist["external_urls"]["spotify"]

                        for song in resp["items"]:

                            if (
                                song["name"].lower().split(" (")[0]
                                == track.lower().split(" (")[0]
                            ):
                                url = song["external_urls"]["spotify"]
                                found = True
                                album_endpoint = (
                                    f"https://api.spotify.com/v1/albums/{album_id}"
                                )
                                with requests.get(
                                    album_endpoint, headers=headers
                                ) as album_response:
                                    album_data = album_response.json()

                                if (
                                    "copyrights" in album_data
                                    and album_data["copyrights"]
                                ):
                                    copyright = album_data["copyrights"][0]["text"]

                                    label = copyright
                                else:
                                    label = None
                                break
                        if found:
                            break
                    if url == None:
                        url = artist_url

                    if label == None:
                        filtered_items = [
                            item
                            for item in all_albums
                            if item["artists"][0]["name"].lower() == artist_name.lower()
                        ]
                        if not filtered_items:
                            return ("Not On Spotify: Look Up", None)

                        latest_album = sorted(
                            filtered_items,
                            key=lambda x: x["release_date"],
                            reverse=True,
                        )[0]

                        album_id = latest_album["id"]
                        album_endpoint = f"https://api.spotify.com/v1/albums/{album_id}"
                        with requests.get(
                            album_endpoint, headers=headers
                        ) as album_response:
                            album_data = album_response.json()

                        label = None

                        if "copyrights" in album_data and album_data["copyrights"]:
                            copyright = album_data["copyrights"][0]["text"]

                            label = copyright

                        else:
                            label = "No Copyright Information"

                    return (label, url)

        except Exception as e:
            print(f"Exception: {e}")
            time.sleep(30)
            return self.get_artist_copy(artist_name, coming_from, search_type, offset)

    def get_playlist_songs(
        self, id, chart, signed_artists, major_label, smart_partial_match
    ):

        access_token = self.get_access_token()

        headers = {"Authorization": f"Bearer {access_token}"}
        playlist_endpoint = f"https://api.spotify.com/v1/playlists/{id}/tracks"

        r = requests.get(playlist_endpoint, headers=headers).json()
        playlist_items = r["items"]

        url = f"https://api.spotify.com/v1/playlists/{id}/tracks"
        while url:
            r = requests.get(url, headers=headers).json()
            playlist_items = r["items"]

            for song in playlist_items:
                date = song["added_at"]
                artist_name = song["track"]["artists"][0]["name"]
                track_name = song["track"]["name"]

                dt_format = "%Y-%m-%dT%H:%M:%SZ"
                added_at = datetime.strptime(date, dt_format)
                time_frame = datetime.now(pacific_tz) - timedelta(days=1)

                if added_at >= time_frame:
                    if not list(
                        filter(
                            lambda x: (x.lower() == artist_name.lower()), signed_artists
                        )
                    ):

                        id = song["track"]["album"]["id"]
                        album_endpoint = f"https://api.spotify.com/v1/albums/{id}"
                        album = requests.get(album_endpoint, headers=headers).json()
                        copyright = album["copyrights"][0]["text"]
                        url = song["track"]["external_urls"]["spotify"]

                        year_pattern = r"202[0-4]"
                        if copyright:
                            if not re.search(year_pattern, copyright):
                                continue
                            else:

                                matched_labels = list(
                                    filter(
                                        lambda x: smart_partial_match(
                                            x, copyright.lower()
                                        ),
                                        major_label,
                                    )
                                )
                                if not matched_labels:
                                    print(artist_name, copyright)

                                    self.velocity_df.append(
                                        (
                                            chart,
                                            artist_name,
                                            track_name,
                                            url,
                                            copyright,
                                        )
                                    )

            url = r.get("next")

        return self.velocity_df
