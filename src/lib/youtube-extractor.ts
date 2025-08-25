/**
 * Client-side YouTube video information extractor
 * Runs in the user's browser to bypass YouTube's bot detection
 */

interface YouTubeVideoInfo {
  id: string;
  title: string;
  duration: number;
  uploader: string;
  thumbnail: string;
  formats: YouTubeFormat[];
  streamingData?: any;
}

interface YouTubeFormat {
  format_id: string;
  ext: string;
  resolution: string;
  fps: number;
  vcodec: string;
  acodec: string;
  filesize?: number;
  url?: string;
  has_video: boolean;
  has_audio: boolean;
  format_note: string;
  quality?: string;
}

class YouTubeExtractor {
  private static readonly INNERTUBE_API_KEY = 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8';
  private static readonly INNERTUBE_CONTEXT = {
    client: {
      clientName: 'WEB',
      clientVersion: '2.20231219.04.00',
      hl: 'en',
      gl: 'US',
      utcOffsetMinutes: 0,
    },
    user: {
      lockedSafetyMode: false,
    },
    request: {
      useSsl: true,
    },
  };

  static async extractVideoInfo(videoId: string): Promise<YouTubeVideoInfo> {
    console.log(`[YouTubeExtractor] Starting extraction for video ID: ${videoId}`);

    try {
      // Method 1: Try InnerTube API first (more reliable)
      console.log('[YouTubeExtractor] Trying InnerTube API...');
      const innerTubeInfo = await this.extractFromInnerTube(videoId);
      if (innerTubeInfo) {
        console.log('[YouTubeExtractor] InnerTube API succeeded');
        return innerTubeInfo;
      }

      // Method 2: Try to extract from embedded player
      console.log('[YouTubeExtractor] InnerTube failed, trying embed...');
      const embedInfo = await this.extractFromEmbed(videoId);
      if (embedInfo) {
        console.log('[YouTubeExtractor] Embed extraction succeeded');
        return embedInfo;
      }

      throw new Error('All extraction methods failed');
    } catch (error) {
      console.error('[YouTubeExtractor] All methods failed:', error);
      throw error;
    }
  }

  private static async extractFromEmbed(videoId: string): Promise<YouTubeVideoInfo | null> {
    try {
      // Create hidden iframe to extract player data
      const iframe = document.createElement('iframe');
      iframe.style.display = 'none';
      iframe.src = `https://www.youtube.com/embed/${videoId}?enablejsapi=1`;
      document.body.appendChild(iframe);

      return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          document.body.removeChild(iframe);
          resolve(null);
        }, 10000);

        iframe.onload = async () => {
          try {
            // Try to access iframe content (may be blocked by CORS)
            const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document;
            if (!iframeDoc) {
              clearTimeout(timeout);
              document.body.removeChild(iframe);
              resolve(null);
              return;
            }

            // Extract video info from iframe
            const scripts = iframeDoc.querySelectorAll('script');
            let playerData = null;

            for (const script of scripts) {
              const content = script.textContent || '';
              if (content.includes('var ytInitialPlayerResponse')) {
                const match = content.match(/var ytInitialPlayerResponse\s*=\s*({.+?});/);
                if (match) {
                  playerData = JSON.parse(match[1]);
                  break;
                }
              }
            }

            clearTimeout(timeout);
            document.body.removeChild(iframe);

            if (playerData) {
              resolve(this.parsePlayerResponse(playerData));
            } else {
              resolve(null);
            }
          } catch (error) {
            clearTimeout(timeout);
            document.body.removeChild(iframe);
            resolve(null);
          }
        };

        iframe.onerror = () => {
          clearTimeout(timeout);
          document.body.removeChild(iframe);
          resolve(null);
        };
      });
    } catch (error) {
      console.error('Embed extraction failed:', error);
      return null;
    }
  }

  private static async extractFromInnerTube(videoId: string): Promise<YouTubeVideoInfo | null> {
    try {
      console.log(`[InnerTube] Making request for video ${videoId}`);

      const response = await fetch(`https://www.youtube.com/youtubei/v1/player?key=${this.INNERTUBE_API_KEY}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Origin': 'https://www.youtube.com',
          'Referer': 'https://www.youtube.com/',
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        },
        body: JSON.stringify({
          context: this.INNERTUBE_CONTEXT,
          videoId: videoId,
          playbackContext: {
            contentPlaybackContext: {
              html5Preference: 'HTML5_PREF_WANTS',
            },
          },
        }),
      });

      console.log(`[InnerTube] Response status: ${response.status}`);

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`[InnerTube] API error: ${response.status} - ${errorText}`);
        throw new Error(`InnerTube API failed: ${response.status}`);
      }

      const data = await response.json();
      console.log('[InnerTube] Response received, parsing...');

      if (!data.videoDetails) {
        console.error('[InnerTube] No video details in response');
        return null;
      }

      const result = this.parsePlayerResponse(data);
      console.log(`[InnerTube] Parsed ${result.formats.length} formats`);
      return result;
    } catch (error) {
      console.error('[InnerTube] Extraction failed:', error);
      return null;
    }
  }

  private static parsePlayerResponse(playerResponse: any): YouTubeVideoInfo {
    const videoDetails = playerResponse.videoDetails;
    const streamingData = playerResponse.streamingData;

    if (!videoDetails) {
      throw new Error('No video details found');
    }

    const formats: YouTubeFormat[] = [];

    // Parse adaptive formats (video/audio separate)
    if (streamingData?.adaptiveFormats) {
      for (const format of streamingData.adaptiveFormats) {
        formats.push(this.parseFormat(format, 'adaptive'));
      }
    }

    // Parse progressive formats (video+audio combined)
    if (streamingData?.formats) {
      for (const format of streamingData.formats) {
        formats.push(this.parseFormat(format, 'progressive'));
      }
    }

    return {
      id: videoDetails.videoId,
      title: videoDetails.title,
      duration: parseInt(videoDetails.lengthSeconds) || 0,
      uploader: videoDetails.author,
      thumbnail: videoDetails.thumbnail?.thumbnails?.[0]?.url || '',
      formats: formats,
      streamingData: streamingData,
    };
  }

  private static parseFormat(format: any, type: 'adaptive' | 'progressive'): YouTubeFormat {
    const hasVideo = format.mimeType?.includes('video') || false;
    const hasAudio = format.mimeType?.includes('audio') || false;
    
    // Extract codec info
    const mimeMatch = format.mimeType?.match(/codecs="([^"]+)"/);
    const codecs = mimeMatch ? mimeMatch[1].split(', ') : [];
    
    let vcodec = 'none';
    let acodec = 'none';
    
    if (hasVideo && codecs.length > 0) {
      vcodec = codecs[0];
    }
    if (hasAudio) {
      acodec = codecs.length > 1 ? codecs[1] : codecs[0];
    }

    // Determine resolution
    let resolution = 'audio only';
    if (format.height && format.width) {
      resolution = `${format.width}x${format.height}`;
    } else if (format.height) {
      resolution = `${format.height}p`;
    }

    return {
      format_id: format.itag?.toString() || 'unknown',
      ext: this.getExtensionFromMime(format.mimeType),
      resolution: resolution,
      fps: format.fps || 0,
      vcodec: vcodec,
      acodec: acodec,
      filesize: format.contentLength ? parseInt(format.contentLength) : undefined,
      url: format.url,
      has_video: hasVideo,
      has_audio: hasAudio,
      format_note: `${type} - ${format.qualityLabel || format.audioQuality || 'unknown'}`,
      quality: format.qualityLabel || format.audioQuality,
    };
  }

  private static getExtensionFromMime(mimeType: string): string {
    if (!mimeType) return 'unknown';
    
    if (mimeType.includes('mp4')) return 'mp4';
    if (mimeType.includes('webm')) return 'webm';
    if (mimeType.includes('3gpp')) return '3gp';
    if (mimeType.includes('audio/mp4')) return 'm4a';
    if (mimeType.includes('audio/webm')) return 'webm';
    
    return 'unknown';
  }

  static extractVideoId(url: string): string | null {
    const patterns = [
      /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)/,
      /youtube\.com\/v\/([^&\n?#]+)/,
    ];

    for (const pattern of patterns) {
      const match = url.match(pattern);
      if (match) return match[1];
    }

    return null;
  }
}

export { YouTubeExtractor, type YouTubeVideoInfo, type YouTubeFormat };
