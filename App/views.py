# views.py - Complete updated version with lyrics functionality
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import re
import requests
from .models import Song

def index(request):
    """Main view to display songs with pagination"""
    paginator = Paginator(Song.objects.all(), 1)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Add formatted lyrics to each song object
    for song in page_obj:
        song.formatted_lyrics = song.get_formatted_lyrics()
    
    context = {"page_obj": page_obj}
    return render(request, "index.html", context)

@csrf_exempt
@require_http_methods(["POST"])
def fetch_lyrics(request):
    """AJAX endpoint to fetch synced lyrics for a song"""
    try:
        data = json.loads(request.body)
        artist = data.get('artist', '').strip()
        title = data.get('title', '').strip()
        song_id = data.get('song_id')
        
        if not artist or not title:
            return JsonResponse({
                'success': False,
                'message': 'Artist and title are required'
            })
        
        print(f"Fetching lyrics for: {artist} - {title}")
        
        # Try to fetch synced lyrics
        lyrics_data = get_synced_lyrics(artist, title)
        
        if lyrics_data and len(lyrics_data) > 0:
            # Save to database if song_id provided
            if song_id:
                try:
                    song = Song.objects.get(id=song_id)
                    song.lyrics = json.dumps(lyrics_data, ensure_ascii=False)
                    song.save()
                    print(f"Lyrics saved to database for song ID: {song_id}")
                except Song.DoesNotExist:
                    print(f"Song with ID {song_id} not found")
                except Exception as e:
                    print(f"Error saving lyrics: {e}")
            
            return JsonResponse({
                'success': True,
                'lyrics': lyrics_data,
                'message': f'Found {len(lyrics_data)} synced lyric lines'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'No synced lyrics found for this song. Try checking the spelling or try a different song.'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        })
    except Exception as e:
        print(f"Error in fetch_lyrics: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Error fetching lyrics: {str(e)}'
        })

def get_synced_lyrics(artist, title):
    """Fetch synced lyrics using syncedlyrics library"""
    try:
        import syncedlyrics
        
        # Try different query variations for better results
        queries = [
            f"{artist} {title}",
            f"{title} {artist}",
            f"{artist} - {title}",
            title  # Sometimes just the title works better
        ]
        
        lrc_lyrics = None
        for query in queries:
            print(f"Trying query: {query}")
            try:
                lrc_lyrics = syncedlyrics.search(query)
                if lrc_lyrics and len(lrc_lyrics.strip()) > 100:  # Ensure we got substantial lyrics
                    print(f"Success with query: {query}")
                    break
            except Exception as e:
                print(f"Query '{query}' failed: {e}")
                continue
        
        if lrc_lyrics:
            print(f"Raw LRC data length: {len(lrc_lyrics)} characters")
            return convert_lrc_to_json(lrc_lyrics)
        else:
            print("No LRC lyrics found with any query variation")
            return None
            
    except ImportError:
        print("syncedlyrics library not installed. Install with: pip install syncedlyrics")
        return None
    except Exception as e:
        print(f"Error fetching synced lyrics: {e}")
        return None

def convert_lrc_to_json(lrc_data):
    """Convert LRC format to JSON for the player with precise timing"""
    if not lrc_data:
        return []
    
    lines = lrc_data.split('\n')
    json_data = []
    
    # Enhanced LRC patterns to handle different timestamp formats
    patterns = [
        r'\[(\d+):(\d+)\.(\d+)\]\s*(.+)',  # [mm:ss.xx] text
        r'\[(\d+):(\d+):(\d+)\]\s*(.+)',   # [mm:ss:xx] text  
        r'\[(\d+):(\d+)\]\s*(.+)'          # [mm:ss] text
    ]
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        matched = False
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                groups = match.groups()
                
                if len(groups) == 4 and '.' in groups[2]:  # mm:ss.xx format
                    minutes, seconds, centiseconds, text = groups
                    total_seconds = int(minutes) * 60 + int(seconds) + int(centiseconds) / 100
                    display_time = f"{minutes}:{seconds.zfill(2)}"
                elif len(groups) == 4:  # mm:ss:xx format (alternative)
                    minutes, seconds, subseconds, text = groups
                    total_seconds = int(minutes) * 60 + int(seconds) + int(subseconds) / 100
                    display_time = f"{minutes}:{seconds.zfill(2)}"
                else:  # mm:ss format
                    minutes, seconds, text = groups
                    total_seconds = int(minutes) * 60 + int(seconds)
                    display_time = f"{minutes}:{seconds.zfill(2)}"
                
                # Clean up the text and skip empty lines
                text = text.strip()
                if text and not text.startswith('['):  # Skip metadata lines
                    json_entry = {
                        "time": display_time,
                        "timestamp": total_seconds,
                        "lyrics": text
                    }
                    json_data.append(json_entry)
                
                matched = True
                break
    
    # Sort by timestamp to ensure correct order
    json_data.sort(key=lambda x: x['timestamp'])
    
    print(f"Converted {len(json_data)} lyric lines from LRC format")
    if json_data:
        print(f"First line: {json_data[0]}")
        print(f"Last line: {json_data[-1]}")
    
    return json_data

# Optional: View to manually update lyrics for a specific song
def update_song_lyrics(request, song_id):
    """Manual lyrics update view (for admin use)"""
    if request.method == 'POST':
        try:
            song = Song.objects.get(id=song_id)
            lyrics_data = get_synced_lyrics(song.artist, song.title)
            
            if lyrics_data:
                song.lyrics = json.dumps(lyrics_data, ensure_ascii=False)
                song.save()
                return JsonResponse({
                    'success': True,
                    'message': f'Updated lyrics for "{song.title}" by {song.artist}',
                    'lyrics_count': len(lyrics_data)
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'No synced lyrics found'
                })
                
        except Song.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Song not found'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

# Optional: Bulk update all songs without lyrics
def bulk_update_lyrics(request):
    """Update lyrics for all songs that don't have them (admin only)"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Admin access required'})
    
    songs_without_lyrics = Song.objects.filter(lyrics__isnull=True) | Song.objects.filter(lyrics='')
    updated_count = 0
    failed_songs = []
    
    for song in songs_without_lyrics:
        try:
            lyrics_data = get_synced_lyrics(song.artist, song.title)
            if lyrics_data:
                song.lyrics = json.dumps(lyrics_data, ensure_ascii=False)
                song.save()
                updated_count += 1
                print(f"Updated: {song.artist} - {song.title}")
            else:
                failed_songs.append(f"{song.artist} - {song.title}")
        except Exception as e:
            failed_songs.append(f"{song.artist} - {song.title} (Error: {e})")
    
    return JsonResponse({
        'success': True,
        'updated_count': updated_count,
        'total_songs': songs_without_lyrics.count(),
        'failed_songs': failed_songs[:10]  # Limit to first 10 failures
    })