from .db_conn import (
    SessionLocal,
)
from .models import SignedArtists
from .models import MajorLabels


class FetchDB:

    def __init__(self):
        pass

    def get_signed_artists(self):
        session = SessionLocal()

        try:
            artists = session.query(SignedArtists).all()
            signed = [artist.name for artist in artists]
            return signed

        except Exception as e:
            print(f"An error occurred: {e}")

        finally:
            session.close()

    def get_major_labels(self):
        session = SessionLocal()

        try:
            labels = session.query(MajorLabels).all()
            l = [label.name for label in labels]
            return l

        except Exception as e:
            print(f"An error occurred: {e}")

        finally:
            session.close()

    def insert_signed_artist(self, data):
        session = SessionLocal()
        try:
            for name in data:
                print(f"Inserting artist: {name}")
                existing_artist = (
                    session.query(SignedArtists).filter_by(name=name).first()
                )

                if existing_artist:
                    print(f"Artist {name} is already in the database.")
                    continue

                new_chart_entry = SignedArtists(
                    name=name,
                )
                session.add(new_chart_entry)

            session.commit()
            print("Data inserted successfully.")

        except Exception as e:
            session.rollback()
            print(f"An error occurred: {e}")
            raise e

        finally:
            session.close()

    def insert_major_label(self, data):
        session = SessionLocal()
        try:
            for name in data:
                print(f"Inserting label: {name}")
                existing_label = session.query(MajorLabels).filter_by(name=name).first()

                if existing_label:
                    print(f"Lable {name} is already in the database.")
                    continue

                new_chart_entry = MajorLabels(
                    name=name,
                )
                session.add(new_chart_entry)

            session.commit()
            print("Data inserted successfully.")

        except Exception as e:
            session.rollback()
            print(f"An error occurred: {e}")
            raise e

        finally:
            session.close()
