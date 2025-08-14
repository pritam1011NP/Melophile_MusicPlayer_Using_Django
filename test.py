#!/usr/bin/env python3
"""
Enhanced Synced Lyrics Fetcher for Melophile
Fetches precisely timed lyrics and formats them for your music player
"""

import syncedlyrics
import re
import json
import os
import sys
from datetime import datetime

class LyricsFetcher:
    def __init__(self):
        self.session_stats = {
            'total_searched': 0,
            'successful_fetches': 0,
            'failed_fetches': 0,
            'songs': []
        }
    
    def search_lyrics(self, artist, title, save_to_file=False, show_preview=True):
        """
        Search for synced lyrics with enhanced error handling and multiple fallbacks
        """
        print(f"\n{'='*60}")
        print(f"🎵 SEARCHING: {artist} - {title}")
        print(f"{'='*60}")
        
        self.session_stats['total_searched'] += 1
        
        # Try different query variations for better results
        queries = [
            f"{artist} {title}",
            f"{title} {artist}",
            f"{artist} - {title}",
            f'"{artist}" "{title}"',
            title,  # Sometimes just the title works better
            f"{title} lyrics"
        ]
        
        lrc_data = None
        successful_query = None
        
        for i, query in enumerate(queries, 1):
            print(f"📡 Attempt {i}/{len(queries)}: {query}")
            
            try:
                lrc_data = syncedlyrics.search(query)
                
                if lrc_data and len(lrc_data.strip()) > 50:  # Ensure substantial content
                    # Quick validation - check if it contains timestamp patterns
                    if re.search(r'\[\d+:\d+[\.\:]\d+\]', lrc_data):
                        print(f"✅ SUCCESS with query: {query}")
                        successful_query = query
                        break
                    else:
                        print(f"⚠️  Found text but no timestamps")
                        continue
                else:
                    print(f"❌ No results")
                    
            except Exception as e:
                print(f"💥 Error: {e}")
                continue
        
        if not lrc_data:
            print(f"\n❌ NO SYNCED LYRICS FOUND")
            print("💡 Try:")
            print("   • Check spelling of artist/title")
            print("   • Try alternative artist names")
            print("   • Some songs may not have synced lyrics available")
            self.session_stats['failed_fetches'] += 1
            self.session_stats['songs'].append({
                'artist': artist,
                'title': title,
                'status': 'failed',
                'reason': 'No synced lyrics found'
            })
            return None
        
        print(f"\n📊 Raw LRC Data: {len(lrc_data)} characters")
        if show_preview:
            print("📋 Preview:")
            lines = lrc_data.split('\n')[:5]
            for line in lines:
                if line.strip():
                    print(f"   {line}")
            if len(lrc_data.split('\n')) > 5:
                print(f"   ... and {len(lrc_data.split('\n'))-5} more lines")
        
        # Convert to JSON format
        json_data = self.convert_lrc_to_json(lrc_data)
        
        if not json_data:
            print("❌ Failed to parse LRC data")
            self.session_stats['failed_fetches'] += 1
            return None
        
        print(f"\n✅ CONVERSION SUCCESS: {len(json_data)} lyric lines")
        print(f"⏱️  Duration: {json_data[0]['time']} → {json_data[-1]['time']}")
        
        # Show sample lines
        if show_preview and len(json_data) >= 3:
            print("\n🎤 Sample Lyrics:")
            for i, line in enumerate(json_data[:3]):
                print(f"   [{line['time']}] {line['lyrics']}")
            if len(json_data) > 3:
                print(f"   ... and {len(json_data)-3} more lines")
        
        # Save to file if requested
        if save_to_file:
            filename = self.save_to_file(json_data, artist, title)
            print(f"💾 Saved to: {filename}")
        
        # Update stats
        self.session_stats['successful_fetches'] += 1
        self.session_stats['songs'].append({
            'artist': artist,
            'title': title,
            'status': 'success',
            'lines_count': len(json_data),
            'query_used': successful_query,
            'duration': f"{json_data[0]['time']} → {json_data[-1]['time']}"
        })
        
        return json_data
    
    def convert_lrc_to_json(self, lrc_data):
        """
        Enhanced LRC to JSON conversion with better timestamp handling
        """
        if not lrc_data:
            return []
        
        lines = lrc_data.split('\n')
        json_data = []
        
        # Enhanced patterns for different LRC timestamp formats
        patterns = [
            r'\[(\d+):(\d+)\.(\d+)\]\s*(.+)',      # [mm:ss.xx] text
            r'\[(\d+):(\d+):(\d+)\]\s*(.+)',       # [mm:ss:xx] text  
            r'\[(\d+):(\d+)\]\s*(.+)',             # [mm:ss] text
            r'\[(\d+):(\d+)\.(\d+)\](.+)',         # No space after bracket
            r'\[(\d{1,2}):(\d{2})\.(\d{2,3})\]\s*(.+)'  # More flexible digit matching
        ]
        
        metadata_patterns = [
            r'\[ar:(.+)\]',  # Artist
            r'\[ti:(.+)\]',  # Title
            r'\[al:(.+)\]',  # Album
            r'\[by:(.+)\]',  # Creator
            r'\[offset:(.+)\]'  # Offset
        ]
        
        metadata = {}
        processed_lines = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for metadata
            is_metadata = False
            for meta_pattern in metadata_patterns:
                meta_match = re.match(meta_pattern, line, re.IGNORECASE)
                if meta_match:
                    is_metadata = True
                    break
            
            if is_metadata:
                continue
            
            # Try to match timestamp patterns
            matched = False
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    groups = match.groups()
                    
                    try:
                        if len(groups) == 4 and groups[2].isdigit():  # Has centiseconds/milliseconds
                            minutes, seconds, subseconds, text = groups
                            # Handle both centiseconds (2 digits) and milliseconds (3 digits)
                            if len(subseconds) == 3:  # milliseconds
                                total_seconds = int(minutes) * 60 + int(seconds) + int(subseconds) / 1000
                            else:  # centiseconds
                                total_seconds = int(minutes) * 60 + int(seconds) + int(subseconds) / 100
                        else:  # No subseconds
                            minutes, seconds, text = groups[0], groups[1], groups[-1]
                            total_seconds = int(minutes) * 60 + int(seconds)
                        
                        # Format display time (mm:ss)
                        display_time = f"{int(minutes)}:{int(seconds):02d}"
                        
                        # Clean up text
                        text = text.strip()
                        
                        # Skip empty lyrics or common metadata indicators
                        if (text and 
                            not text.startswith('[') and 
                            text.lower() not in ['', '♪', '♫', '...', 'instrumental']):
                            
                            json_entry = {
                                "time": display_time,
                                "timestamp": round(total_seconds, 2),
                                "lyrics": text
                            }
                            json_data.append(json_entry)
                            processed_lines += 1
                        
                        matched = True
                        break
                        
                    except (ValueError, IndexError) as e:
                        print(f"⚠️  Error parsing line: {line} - {e}")
                        continue
            
            if not matched and line and not line.startswith('['):
                # Handle plain text lines (backup)
                if processed_lines == 0:  # Only if no timestamped lyrics found yet
                    print(f"⚠️  Found non-timestamped line: {line[:50]}...")
        
        # Sort by timestamp and remove duplicates
        json_data.sort(key=lambda x: x['timestamp'])
        
        # Remove duplicate timestamps (keep first occurrence)
        seen_timestamps = set()
        unique_data = []
        for item in json_data:
            if item['timestamp'] not in seen_timestamps:
                seen_timestamps.add(item['timestamp'])
                unique_data.append(item)
        
        print(f"🔧 Processed {processed_lines} lines, {len(unique_data)} unique entries")
        
        return unique_data
    
    def save_to_file(self, json_data, artist, title):
        """Save lyrics to a timestamped JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_artist = re.sub(r'[^\w\s-]', '', artist).strip().replace(' ', '_')
        safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
        
        filename = f"lyrics_{safe_artist}_{safe_title}_{timestamp}.json"
        
        # Create output directory if it doesn't exist
        os.makedirs('lyrics_output', exist_ok=True)
        filepath = os.path.join('lyrics_output', filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'artist': artist,
                    'title': title,
                    'fetched_at': datetime.now().isoformat(),
                    'total_lines': len(json_data)
                },
                'lyrics': json_data
            }, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def batch_search(self, songs_list):
        """Search lyrics for multiple songs"""
        print(f"\n🎼 BATCH MODE: Processing {len(songs_list)} songs")
        print("="*60)
        
        results = []
        
        for i, (artist, title) in enumerate(songs_list, 1):
            print(f"\n[{i}/{len(songs_list)}]")
            lyrics_data = self.search_lyrics(artist, title, show_preview=False)
            results.append({
                'artist': artist,
                'title': title,
                'lyrics': lyrics_data,
                'success': lyrics_data is not None
            })
            
            # Add small delay to be respectful to the API
            import time
            time.sleep(1)
        
        return results
    
    def print_django_format(self, json_data):
        """Print lyrics in format ready for Django admin"""
        print(f"\n{'='*60}")
        print("📋 COPY THIS TO YOUR DJANGO SONG'S LYRICS FIELD:")
        print('='*60)
        formatted_json = json.dumps(json_data, ensure_ascii=False, separators=(',', ':'))
        print(formatted_json)
        print('='*60)
        print("💡 Tip: Copy the text above and paste it directly into your Django admin lyrics field")
    
    def print_session_stats(self):
        """Print statistics for the current session"""
        stats = self.session_stats
        print(f"\n📊 SESSION STATISTICS:")
        print(f"{'='*40}")
        print(f"Total searches: {stats['total_searched']}")
        print(f"Successful: {stats['successful_fetches']}")
        print(f"Failed: {stats['failed_fetches']}")
        
        if stats['total_searched'] > 0:
            success_rate = (stats['successful_fetches'] / stats['total_searched']) * 100
            print(f"Success rate: {success_rate:.1f}%")
        
        if stats['songs']:
            print(f"\n📋 Song Results:")
            for song in stats['songs']:
                status_icon = "✅" if song['status'] == 'success' else "❌"
                print(f"  {status_icon} {song['artist']} - {song['title']}")
                if song['status'] == 'success':
                    print(f"     Lines: {song.get('lines_count', 'N/A')}")

def main():
    """Main interactive function"""
    fetcher = LyricsFetcher()
    
    print("🎵 Melophile SYNCED LYRICS FETCHER")
    print("="*50)
    print("This tool fetches precisely timed lyrics for your music player")
    print("Supports LRC format with exact timestamp synchronization")
    print()
    
    while True:
        print("\nChoose an option:")
        print("1. Search single song")
        print("2. Batch search (multiple songs)")
        print("3. Test with popular song")
        print("4. View session statistics")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == '1':
            artist = input("\n🎤 Enter artist name: ").strip()
            title = input("🎵 Enter song title: ").strip()
            
            if not artist or not title:
                print("❌ Please provide both artist and title!")
                continue
            
            save_file = input("💾 Save to file? (y/n): ").lower().strip() == 'y'
            lyrics_data = fetcher.search_lyrics(artist, title, save_to_file=save_file)
            
            if lyrics_data:
                fetcher.print_django_format(lyrics_data)
        
        elif choice == '2':
            print("\n📝 Enter songs (one per line, format: Artist - Title)")
            print("Press Enter twice when done:")
            
            songs = []
            while True:
                line = input().strip()
                if not line:
                    break
                
                if ' - ' in line:
                    artist, title = line.split(' - ', 1)
                    songs.append((artist.strip(), title.strip()))
                else:
                    print("⚠️  Invalid format. Use: Artist - Title")
            
            if songs:
                results = fetcher.batch_search(songs)
                
                print(f"\n🎯 BATCH RESULTS:")
                successful = [r for r in results if r['success']]
                for result in successful:
                    if result['lyrics']:
                        print(f"\n--- {result['artist']} - {result['title']} ---")
                        fetcher.print_django_format(result['lyrics'])
        
        elif choice == '3':
            test_songs = [
                ("The Weeknd", "Blinding Lights"),
                ("Ed Sheeran", "Shape of You"),
                ("Billie Eilish", "bad guy"),
                ("Post Malone", "Circles")
            ]
            
            print("\n🧪 Testing with popular songs...")
            song = test_songs[0]  # Default to first song
            
            print(f"Testing: {song[0]} - {song[1]}")
            lyrics_data = fetcher.search_lyrics(song[0], song[1])
            
            if lyrics_data:
                fetcher.print_django_format(lyrics_data)
        
        elif choice == '4':
            fetcher.print_session_stats()
        
        elif choice == '5':
            fetcher.print_session_stats()
            print("\n👋 Thanks for using Melophile Lyrics Fetcher!")
            break
        
        else:
            print("❌ Invalid choice. Please enter 1-5.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        print("Please report this issue!")