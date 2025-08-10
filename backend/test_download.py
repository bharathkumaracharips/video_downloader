#!/usr/bin/env python3
"""
Test script to verify video+audio merging functionality
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.downloader import downloader

async def test_video_merge():
    """Test video+audio merging with a sample YouTube video"""
    
    # Test URL - use a short video for testing
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll - short video
    
    print("🧪 Testing video+audio merge functionality...")
    print(f"📺 URL: {test_url}")
    
    try:
        # Test getting video info first
        print("\n1️⃣ Getting video info...")
        info = await downloader.get_video_info(test_url)
        print(f"✅ Title: {info.title}")
        print(f"✅ Duration: {info.duration} seconds")
        print(f"✅ Available formats: {len(info.formats)}")
        
        # Check for separate video and audio streams
        video_only = [f for f in info.formats if f.has_video and not f.has_audio]
        audio_only = [f for f in info.formats if f.has_audio and not f.has_video]
        combined = [f for f in info.formats if f.has_video and f.has_audio]
        
        print(f"📊 Video-only streams: {len(video_only)}")
        print(f"📊 Audio-only streams: {len(audio_only)}")
        print(f"📊 Combined streams: {len(combined)}")
        
        if video_only and audio_only:
            print("✅ Separate video+audio streams available - merge will be needed")
        else:
            print("ℹ️  Combined streams available - merge may not be needed")
        
        # Test download with merge
        print("\n2️⃣ Testing video download with merge...")
        
        def progress_callback(progress_data):
            if progress_data.get('progress', 0) > 0:
                print(f"📥 Progress: {progress_data['progress']:.1f}%")
        
        filename = await downloader.download_video_with_merge(
            test_url, 
            quality="best[height<=720]",  # 720p to ensure we get separate streams
            progress_callback=progress_callback
        )
        
        print(f"✅ Download completed: {filename}")
        
        # Check if file exists and get info
        if os.path.exists(filename):
            file_size = os.path.getsize(filename) / (1024 * 1024)  # MB
            print(f"✅ File size: {file_size:.2f} MB")
            print(f"✅ File extension: {os.path.splitext(filename)[1]}")
        else:
            print("❌ Downloaded file not found!")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_video_merge())