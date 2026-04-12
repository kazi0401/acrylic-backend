from songs.models import Song

# Example songs to add to the database
example_songs = [
    Song(title='Song 1', artist='Artist A', audience_size='1500', sports_audience_fit=75.0, track_virality=60.0, audio_file='path/to/audio1.mp3'),
    Song(title='Song 2', artist='Artist B', audience_size='<1000', sports_audience_fit=50.0, track_virality=30.0, audio_file='path/to/audio2.mp3'),
    Song(title='Song 3', artist='Artist C', audience_size='2000', sports_audience_fit=80.0, track_virality=90.0, audio_file='path/to/audio3.mp3'),
    Song(title='Song 4', artist='Artist D', audience_size='1200', sports_audience_fit=65.0, track_virality=40.0, audio_file='path/to/audio4.mp3'),
    Song(title='Song 5', artist='Artist E', audience_size='800', sports_audience_fit=55.0, track_virality=70.0, audio_file='path/to/audio5.mp3'),
]

# Save example songs to the database
for song in example_songs:
    song.save()