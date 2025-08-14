# models.py - Updated to handle both plain text and JSON lyrics
from django.db import models
import json
import re

class Song(models.Model):
    title = models.TextField()
    artist = models.TextField()
    image = models.ImageField()
    audio_file = models.FileField()
    audio_link = models.CharField(max_length=200, blank=True, null=True)
    lyrics = models.TextField(blank=True, null=True)  # Can store plain text or JSON
    duration = models.TextField(max_length=20)
    paginate_by = 2

    def get_formatted_lyrics(self):
        """Convert lyrics to the expected JSON format for the player"""
        if not self.lyrics:
            return "[]"
        
        # Try to parse as JSON first (if already formatted)
        try:
            parsed = json.loads(self.lyrics)
            if isinstance(parsed, list) and len(parsed) > 0:
                if isinstance(parsed[0], dict) and 'time' in parsed[0]:
                    return self.lyrics  # Already in correct format
        except (json.JSONDecodeError, KeyError):
            pass
        
        # Convert plain text or LRC format to JSON
        return self.convert_lyrics_to_json()
    
    def convert_lyrics_to_json(self):
        """Convert plain text or LRC format lyrics to JSON format"""
        if not self.lyrics:
            return "[]"
        
        lines = self.lyrics.strip().split('\n')
        formatted_lyrics = []
        current_time = 0
        
        # LRC format pattern [mm:ss.xx] text
        lrc_pattern = r'\[(\d+:\d+\.\d+)\]\s*(.+)'
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if it's LRC format
            lrc_match = re.match(lrc_pattern, line)
            if lrc_match:
                timestamp, text = lrc_match.groups()
                # Convert timestamp from mm:ss.xx to mm:ss
                time_parts = timestamp.split(':')
                minutes = int(time_parts[0])
                seconds = int(float(time_parts[1]))
                formatted_time = f"{minutes}:{seconds:02d}"
                
                formatted_lyrics.append({
                    "time": formatted_time,
                    "lyrics": text
                })
            else:
                # Plain text - assign approximate timestamps
                minutes = current_time // 60
                seconds = current_time % 60
                formatted_time = f"{minutes}:{seconds:02d}"
                
                formatted_lyrics.append({
                    "time": formatted_time,
                    "lyrics": line
                })
                current_time += 3  # 3 seconds per line
        
        return json.dumps(formatted_lyrics)
    
    def __str__(self):
        return self.title