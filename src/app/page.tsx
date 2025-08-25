"use client";
import React, { useState, useEffect } from "react";

interface Format {
  format_id: string;
  ext: string;
  resolution: string;
  fps: number;
  vcodec: string;
  acodec: string;
  filesize: number;
  has_video: boolean;
  has_audio: boolean;
  format_note: string;
}

interface Frame {
  format_id: string;
  resolution: string;
  fps: number;
  codec: string;
  container: string;
  bitrate: number;
  filesize: number;
  filesize_mb: number;
  quality_score: number;
  has_audio: boolean;
  audio_codec: string;
  audio_bitrate: number;
}

interface VideoInfo {
  id: string;
  title: string;
  duration: number;
  uploader: string;
  thumbnail: string;
  formats: Format[];
  frames: Frame[];
}

interface PlaylistVideo {
  id: string;
  title: string;
  index: number;
  duration?: number;
}

interface DownloadProgress {
  download_id: string;
  status: string;
  progress: number;
  filename?: string;
  error?: string;
}

type DownloadMode = "video" | "audio" | "playlist" | "live" | "m3u8";

export default function Home() {
  const [mode, setMode] = useState<DownloadMode>("video");
  const [mounted, setMounted] = useState(false);

  // Common states
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  // Video/Audio states
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
  const [selectedQuality, setSelectedQuality] = useState("best");
  const [selectedFormat, setSelectedFormat] = useState("mp4");
  const [audioFormat, setAudioFormat] = useState("mp3");
  const [audioQuality, setAudioQuality] = useState("320");
  const [selectedFrame, setSelectedFrame] = useState<string | null>(null);
  const [mergeAudio, setMergeAudio] = useState(true);

  // Music download states
  const [downloadType, setDownloadType] = useState<"audio" | "music" | "sponsorblock">("sponsorblock");
  const [trimStart, setTrimStart] = useState<number | null>(null);
  const [trimEnd, setTrimEnd] = useState<number | null>(null);
  const [autoDetectMusic, setAutoDetectMusic] = useState(true);
  const [musicAnalysis, setMusicAnalysis] = useState<any>(null);

  // SponsorBlock states
  const [sponsorblockPreset, setSponsorblockPreset] = useState("music_clean");
  const [sponsorblockCategories, setSponsorblockCategories] = useState<any>(null);
  const [customRemoveCategories, setCustomRemoveCategories] = useState<string[]>([
    "sponsor", "intro", "outro", "selfpromo", "interaction", "music_offtopic"
  ]);

  // Queue states
  const [downloads, setDownloads] = useState<DownloadProgress[]>([]);
  const [queueStatus, setQueueStatus] = useState<any>(null);

  // Playlist states
  const [playlistVideos, setPlaylistVideos] = useState<PlaylistVideo[]>([]);
  const [selectedPlaylistVideos, setSelectedPlaylistVideos] = useState<string[]>([]);
  const [playlistTitle, setPlaylistTitle] = useState("");
  const [playlistMode, setPlaylistMode] = useState<"video" | "audio">("audio");

  // Live stream states
  const [liveInfo, setLiveInfo] = useState<any>(null);
  const [recordDuration, setRecordDuration] = useState<number | null>(null);

  // M3U8 states
  const [m3u8Filename, setM3u8Filename] = useState("");
  const [m3u8Progress, setM3u8Progress] = useState<any>(null);

  const API_BASE = "http://localhost:8000/api";

  // Fetch video/audio info
  const fetchVideoInfo = async () => {
    if (!url) return;

    setLoading(true);
    setError("");
    setVideoInfo(null);

    try {
      if (mode === "live") {
        // Use server-side extraction for live streams
        const res = await fetch(`${API_BASE}/live/info`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url }),
        });

        if (!res.ok) throw new Error("Failed to fetch live stream info");
        const data = await res.json();
        setLiveInfo(data);
      } else {
        // Try server-side browser extraction first for regular videos
        try {
          // Extract video ID from URL
          const videoIdMatch = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)/);

          if (videoIdMatch) {
            const videoId = videoIdMatch[1];
            setStatus("Extracting video info via browser method...");

            const res = await fetch(`${API_BASE}/browser/extract/${videoId}`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
            });

            if (res.ok) {
              const browserInfo = await res.json();

              // Convert browser format to expected format
              const convertedInfo = {
                id: browserInfo.id,
                title: browserInfo.title,
                duration: browserInfo.duration,
                uploader: browserInfo.uploader,
                thumbnail: browserInfo.thumbnail,
                formats: browserInfo.formats.map((f: any) => ({
                  format_id: f.format_id,
                  ext: f.ext,
                  resolution: f.resolution,
                  fps: f.fps,
                  vcodec: f.vcodec,
                  acodec: f.acodec,
                  filesize: f.filesize || 0,
                  has_video: f.has_video,
                  has_audio: f.has_audio,
                  format_note: f.format_note
                })),
                frames: browserInfo.formats.filter((f: any) => f.has_video).map((f: any) => ({
                  format_id: f.format_id,
                  resolution: f.resolution,
                  fps: f.fps,
                  codec: f.vcodec,
                  container: f.ext,
                  bitrate: 0,
                  filesize: f.filesize || 0,
                  filesize_mb: f.filesize ? Math.round(f.filesize / 1024 / 1024) : 0,
                  quality_score: 0,
                  has_audio: f.has_audio,
                  audio_codec: f.acodec,
                  audio_bitrate: 0
                })),
                _browserInfo: browserInfo // Store original browser info
              };

              setVideoInfo(convertedInfo);
              setStatus("Video info extracted successfully via browser method!");
              return;
            }
          }

          throw new Error("Browser extraction failed");
        } catch (browserError) {
          console.warn("Browser extraction failed, falling back to yt-dlp:", browserError);
          setStatus("Browser extraction failed, trying yt-dlp...");

          // Fallback to server-side yt-dlp extraction
          const res = await fetch(`${API_BASE}/video/info`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url }),
          });

          if (!res.ok) throw new Error("Failed to fetch video info");
          const data = await res.json();
          setVideoInfo(data);
        }
      }
    } catch (e: any) {
      setError(e.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  // Download functions
  const downloadVideo = async () => {
    if (!url) return;

    setLoading(true);
    setError("");
    setStatus("");

    try {
      // Try regular yt-dlp download first
      const res = await fetch(`${API_BASE}/video/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url,
          quality: selectedQuality,
          format_id: selectedFormat !== "auto" ? selectedFormat : null,
        }),
      });

      if (!res.ok) {
        // If yt-dlp fails, try browser-assisted download
        setStatus("yt-dlp failed, trying browser-assisted download...");

        if (videoInfo && (videoInfo as any)._browserInfo) {
          // Use browser info if available
          const browserInfo = (videoInfo as any)._browserInfo;

          // Find best format based on selected quality
          let selectedFormat = browserInfo.formats.find((f: any) =>
            f.has_video && f.has_audio && f.resolution.includes('720')
          ) || browserInfo.formats.find((f: any) => f.has_video && f.has_audio);

          if (!selectedFormat) {
            // Find best video + best audio
            const videoFormat = browserInfo.formats.find((f: any) => f.has_video && !f.has_audio);
            const audioFormat = browserInfo.formats.find((f: any) => f.has_audio && !f.has_video);

            if (videoFormat) {
              const browserRes = await fetch(`${API_BASE}/browser/download`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  video_info: browserInfo,
                  selected_format_id: videoFormat.format_id,
                  merge_audio: true,
                  audio_format_id: audioFormat?.format_id,
                }),
              });

              if (browserRes.ok) {
                const browserData = await browserRes.json();
                setStatus(`Browser download started: ${browserData.download_id}`);
                pollBrowserDownloadProgress(browserData.download_id);
                return;
              }
            }
          }
        }

        throw new Error("Both yt-dlp and browser download failed");
      }

      const data = await res.json();
      setStatus(`Download started: ${data.download_id}`);

      // Add to downloads list
      setDownloads(prev => [...prev, {
        download_id: data.download_id,
        status: data.status,
        progress: 0,
      }]);

    } catch (e: any) {
      setError(e.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const downloadAudio = async () => {
    if (!url) return;

    setLoading(true);
    setError("");
    setStatus("");

    try {
      const res = await fetch(`${API_BASE}/audio/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url,
          quality: audioQuality,
          format: audioFormat,
        }),
      });

      if (!res.ok) throw new Error("Download failed");
      const data = await res.json();
      setStatus(`Audio download started: ${data.download_id}`);

      setDownloads(prev => [...prev, {
        download_id: data.download_id,
        status: data.status,
        progress: 0,
      }]);

    } catch (e: any) {
      setError(e.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const downloadFrame = async () => {
    if (!url || !selectedFrame || !videoInfo) return;

    setLoading(true);
    setError("");
    setStatus("");

    try {
      // Check if we have browser-extracted info
      if ((videoInfo as any)._browserInfo) {
        setStatus("Using browser-assisted download...");

        // Find best audio format if merging is enabled
        let audioFormatId = null;
        if (mergeAudio) {
          const browserInfo = (videoInfo as any)._browserInfo;
          const audioFormats = browserInfo.formats.filter((f: any) => f.has_audio && !f.has_video);
          if (audioFormats.length > 0) {
            // Find best quality audio
            audioFormatId = audioFormats.reduce((best: any, current: any) => {
              if (!best) return current;
              if (current.filesize && best.filesize && current.filesize > best.filesize) {
                return current;
              }
              return best;
            }).format_id;
          }
        }

        const res = await fetch(`${API_BASE}/browser/download`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            video_info: (videoInfo as any)._browserInfo,
            selected_format_id: selectedFrame,
            merge_audio: mergeAudio,
            audio_format_id: audioFormatId,
          }),
        });

        if (!res.ok) throw new Error("Browser-assisted download failed");
        const data = await res.json();
        setStatus(`Browser download started: ${data.download_id}`);

        // Poll for progress
        pollBrowserDownloadProgress(data.download_id);
      } else {
        // Fallback to original method
        const res = await fetch(`${API_BASE}/video/download/frame`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            url,
            format_id: selectedFrame,
            merge_audio: mergeAudio,
          }),
        });

        if (!res.ok) throw new Error("Frame download failed");
        const data = await res.json();
        setStatus(`Frame downloaded successfully: ${data.filename}`);
      }

    } catch (e: any) {
      setError(e.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const pollBrowserDownloadProgress = async (downloadId: string) => {
    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE}/browser/status/${downloadId}`);
        if (res.ok) {
          const data = await res.json();

          if (data.status === "completed") {
            setStatus(`Download completed: ${data.output_file}`);
            return;
          } else if (data.status === "failed") {
            setError(`Download failed: ${data.error}`);
            return;
          }

          setStatus(data.message || `Status: ${data.status} (${data.progress}%)`);

          // Continue polling if still in progress
          if (data.status === "downloading" || data.status === "starting") {
            setTimeout(poll, 2000);
          }
        }
      } catch (e) {
        console.error("Failed to poll browser download progress:", e);
      }
    };

    poll();
  };

  // Music download functions
  const downloadMusic = async () => {
    if (!url) return;

    setLoading(true);
    setError("");
    setStatus("");

    try {
      const res = await fetch(`${API_BASE}/audio/download/music`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url,
          quality: audioQuality,
          format: audioFormat,
          trim_start: trimStart,
          trim_end: trimEnd,
          auto_detect_music: autoDetectMusic,
        }),
      });

      if (!res.ok) throw new Error("Music download failed");
      const data = await res.json();
      setStatus(`Music downloaded successfully: ${data.filename}`);

    } catch (e: any) {
      setError(e.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const downloadSponsorBlockMusic = async () => {
    if (!url) return;

    setLoading(true);
    setError("");
    setStatus("");

    try {
      // Get categories based on preset or custom selection
      let removeCategories = customRemoveCategories;
      if (sponsorblockCategories && sponsorblockPreset !== "custom") {
        const preset = sponsorblockCategories.presets[sponsorblockPreset];
        if (preset) {
          removeCategories = preset.remove;
        }
      }

      const res = await fetch(`${API_BASE}/audio/download/music/sponsorblock`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url,
          quality: audioQuality,
          format: audioFormat,
          remove_categories: removeCategories,
          mark_categories: [],
          sponsorblock_api: "https://sponsor.ajay.app"
        }),
      });

      if (!res.ok) throw new Error("SponsorBlock music download failed");
      const data = await res.json();
      setStatus(`Clean music downloaded successfully: ${data.filename}`);

    } catch (e: any) {
      setError(e.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const loadSponsorBlockCategories = async () => {
    try {
      const res = await fetch(`${API_BASE}/audio/sponsorblock/categories`);
      if (res.ok) {
        const data = await res.json();
        setSponsorblockCategories(data);
      }
    } catch (e) {
      console.error("Failed to load SponsorBlock categories:", e);
    }
  };

  const analyzeMusicContent = async () => {
    if (!url) return;

    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/audio/analyze/music`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });

      if (!res.ok) throw new Error("Analysis failed");
      const data = await res.json();
      setMusicAnalysis(data);

      // Auto-apply suggested trims
      if (data.suggested_trims) {
        setTrimStart(data.suggested_trims.intro_skip || null);
        setTrimEnd(data.suggested_trims.outro_skip || null);
      }

    } catch (e: any) {
      setError(e.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  // Playlist functions
  const fetchPlaylistInfo = async () => {
    if (!url) return;

    setLoading(true);
    setError("");
    setPlaylistVideos([]);

    try {
      const res = await fetch(`${API_BASE}/playlist/info`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });

      if (!res.ok) throw new Error("Failed to fetch playlist");
      const data = await res.json();
      setPlaylistVideos(data.videos);
      setPlaylistTitle(data.title);
      setSelectedPlaylistVideos(data.videos.map((v: PlaylistVideo) => v.id));
    } catch (e: any) {
      setError(e.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const downloadPlaylist = async () => {
    if (!url) return;

    setLoading(true);
    setError("");
    setStatus("");

    try {
      const res = await fetch(`${API_BASE}/playlist/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url,
          mode: playlistMode,
          video_ids: selectedPlaylistVideos,
          audio_format: audioFormat,
          audio_quality: audioQuality,
        }),
      });

      if (!res.ok) throw new Error("Download failed");
      const data = await res.json();
      setStatus(`Playlist download started: ${data.download_id}`);

    } catch (e: any) {
      setError(e.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  // Live stream functions
  const downloadLiveStream = async () => {
    if (!url) return;

    setLoading(true);
    setError("");
    setStatus("");

    try {
      const res = await fetch(`${API_BASE}/live/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url,
          quality: selectedQuality,
          duration: recordDuration,
          wait_for_live: true,
        }),
      });

      if (!res.ok) throw new Error("Download failed");
      const data = await res.json();
      setStatus(`Live stream download started: ${data.download_id}`);

    } catch (e: any) {
      setError(e.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  // M3U8 functions
  const downloadM3U8 = async () => {
    if (!url) return;

    setLoading(true);
    setError("");
    setStatus("");
    setM3u8Progress(null);

    try {
      const res = await fetch(`${API_BASE}/m3u8/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url,
          filename: m3u8Filename || undefined,
        }),
      });

      if (!res.ok) throw new Error("M3U8 download failed");
      const data = await res.json();
      setStatus(`M3U8 download started: ${data.download_id}`);

      // Start polling for progress
      pollM3U8Progress(data.download_id);

    } catch (e: any) {
      setError(e.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const pollM3U8Progress = async (downloadId: string) => {
    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE}/m3u8/status/${downloadId}`);
        if (res.ok) {
          const data = await res.json();
          setM3u8Progress(data);

          if (data.status === "completed") {
            setStatus(`M3U8 download completed: ${data.output_file}`);
            return;
          } else if (data.status === "failed") {
            setError(`M3U8 download failed: ${data.error}`);
            return;
          }

          // Continue polling if still in progress
          if (data.status === "downloading" || data.status === "starting") {
            setTimeout(poll, 2000);
          }
        }
      } catch (e) {
        console.error("Failed to poll M3U8 progress:", e);
      }
    };

    poll();
  };

  // Queue management
  const fetchQueueStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/queue/status`);
      if (res.ok) {
        const data = await res.json();
        setQueueStatus(data);
      }
    } catch (e) {
      console.error("Failed to fetch queue status:", e);
    }
  };

  const handlePlaylistVideoSelect = (id: string) => {
    setSelectedPlaylistVideos((prev) =>
      prev.includes(id) ? prev.filter((v) => v !== id) : [...prev, id]
    );
  };

  // Handle client-side mounting
  useEffect(() => {
    setMounted(true);
  }, []);

  // Fetch queue status periodically (only after mounting)
  useEffect(() => {
    if (!mounted) return;

    fetchQueueStatus();
    loadSponsorBlockCategories();
    const interval = setInterval(fetchQueueStatus, 2000);
    return () => clearInterval(interval);
  }, [mounted]);



  // Prevent hydration mismatch by not rendering until mounted
  if (!mounted) {
    return (
      <main className="max-w-6xl mx-auto p-6">
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-6 rounded-lg mb-6">
          <h1 className="text-3xl font-bold mb-2">Advanced YouTube Downloader</h1>
          <p className="text-blue-100">Loading...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="max-w-6xl mx-auto p-6">
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-6 rounded-lg mb-6">
        <h1 className="text-3xl font-bold mb-2">Advanced YouTube Downloader</h1>
        <p className="text-blue-100">Multi-mode downloader with yt-dlp integration</p>
      </div>

      {/* Mode Selection */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <button
          className={`p-4 rounded-lg border-2 transition-all ${mode === "video"
            ? "border-blue-500 bg-blue-50 text-blue-700"
            : "border-gray-200 hover:border-gray-300"
            }`}
          onClick={() => setMode("video")}
        >
          <div className="text-2xl mb-2">🎥</div>
          <div className="font-semibold">Video</div>
          <div className="text-sm text-gray-600">Up to 4K quality</div>
          <div className="text-xs text-blue-600 mt-1">Auto-merge</div>
        </button>

        <button
          className={`p-4 rounded-lg border-2 transition-all ${mode === "audio"
            ? "border-green-500 bg-green-50 text-green-700"
            : "border-gray-200 hover:border-gray-300"
            }`}
          onClick={() => setMode("audio")}
        >
          <div className="text-2xl mb-2">🎵</div>
          <div className="font-semibold">Audio</div>
          <div className="text-sm text-gray-600">Extract audio</div>
        </button>

        <button
          className={`p-4 rounded-lg border-2 transition-all ${mode === "playlist"
            ? "border-purple-500 bg-purple-50 text-purple-700"
            : "border-gray-200 hover:border-gray-300"
            }`}
          onClick={() => setMode("playlist")}
        >
          <div className="text-2xl mb-2">📋</div>
          <div className="font-semibold">Playlist</div>
          <div className="text-sm text-gray-600">Batch download</div>
        </button>

        <button
          className={`p-4 rounded-lg border-2 transition-all ${mode === "live"
            ? "border-red-500 bg-red-50 text-red-700"
            : "border-gray-200 hover:border-gray-300"
            }`}
          onClick={() => setMode("live")}
        >
          <div className="text-2xl mb-2">🔴</div>
          <div className="font-semibold">Live</div>
          <div className="text-sm text-gray-600">Record streams</div>
        </button>

        <button
          className={`p-4 rounded-lg border-2 transition-all ${mode === "m3u8"
            ? "border-orange-500 bg-orange-50 text-orange-700"
            : "border-gray-200 hover:border-gray-300"
            }`}
          onClick={() => setMode("m3u8")}
        >
          <div className="text-2xl mb-2">📺</div>
          <div className="font-semibold">M3U8</div>
          <div className="text-sm text-gray-600">HLS streams</div>
          <div className="text-xs text-orange-600 mt-1">AES-128</div>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2">
          {/* URL Input */}
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {mode === "m3u8" ? "M3U8 Stream URL" : "YouTube URL"}
            </label>
            <div className="flex gap-2">
              <input
                className="flex-1 border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                type="text"
                placeholder={mode === "m3u8" ? "https://example.com/stream.m3u8" : "https://www.youtube.com/watch?v=..."}
                value={url}
                onChange={(e) => setUrl(e.target.value)}
              />
              <button
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                onClick={fetchVideoInfo}
                disabled={loading || !url}
              >
                {loading ? "Loading..." : "Analyze"}
              </button>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
              {error}
            </div>
          )}

          {/* Status Display */}
          {status && (
            <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg mb-6">
              {status}
            </div>
          )}
          {/* Video Mode */}
          {mode === "video" && (
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
              <h2 className="text-xl font-semibold mb-4">Video Download - Available Frames</h2>

              {videoInfo && (
                <div className="mb-6">
                  <div className="flex gap-4 mb-6">
                    {videoInfo.thumbnail && (
                      <img
                        src={videoInfo.thumbnail}
                        alt="Thumbnail"
                        className="w-32 h-24 object-cover rounded"
                      />
                    )}
                    <div>
                      <h3 className="font-semibold text-lg">{videoInfo.title}</h3>
                      <p className="text-gray-600">by {videoInfo.uploader}</p>
                      <p className="text-gray-500 text-sm">
                        Duration: {Math.floor((videoInfo.duration || 0) / 60)}:{String((videoInfo.duration || 0) % 60).padStart(2, '0')}
                      </p>
                    </div>
                  </div>

                  {/* Frame Selection Options */}
                  <div className="mb-4">
                    <label className="flex items-center gap-2 mb-2">
                      <input
                        type="checkbox"
                        checked={mergeAudio}
                        onChange={(e) => setMergeAudio(e.target.checked)}
                        className="rounded"
                      />
                      <span className="text-sm font-medium text-gray-700">
                        Merge with best audio (recommended)
                      </span>
                    </label>
                  </div>

                  {/* Frames Table */}
                  {videoInfo.frames && videoInfo.frames.length > 0 && (
                    <div className="mb-6">
                      <h4 className="font-medium text-gray-900 mb-3">Available Video Frames:</h4>
                      <div className="overflow-x-auto">
                        <table className="min-w-full border border-gray-200 rounded-lg">
                          <thead className="bg-gray-50">
                            <tr>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Select</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Resolution</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">FPS</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Codec</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Container</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Bitrate</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Size</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Audio</th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            {videoInfo.frames.map((frame, index) => (
                              <tr
                                key={frame.format_id}
                                className={`hover:bg-gray-50 ${selectedFrame === frame.format_id ? 'bg-blue-50 border-blue-200' : ''}`}
                              >
                                <td className="px-4 py-3">
                                  <input
                                    type="radio"
                                    name="selectedFrame"
                                    value={frame.format_id}
                                    checked={selectedFrame === frame.format_id}
                                    onChange={(e) => setSelectedFrame(e.target.value)}
                                    className="text-blue-600"
                                  />
                                </td>
                                <td className="px-4 py-3 text-sm font-medium text-gray-900">
                                  {frame.resolution}
                                </td>
                                <td className="px-4 py-3 text-sm text-gray-500">
                                  {frame.fps ? `${frame.fps}fps` : 'N/A'}
                                </td>
                                <td className="px-4 py-3 text-sm text-gray-500">
                                  {frame.codec}
                                </td>
                                <td className="px-4 py-3 text-sm text-gray-500">
                                  {frame.container.toUpperCase()}
                                </td>
                                <td className="px-4 py-3 text-sm text-gray-500">
                                  {frame.bitrate ? `${Math.round(frame.bitrate)}k` : 'N/A'}
                                </td>
                                <td className="px-4 py-3 text-sm text-gray-500">
                                  {frame.filesize_mb ? `${frame.filesize_mb}MB` : 'N/A'}
                                </td>
                                <td className="px-4 py-3 text-sm">
                                  {frame.has_audio ? (
                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                      ✓ {frame.audio_codec}
                                    </span>
                                  ) : (
                                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                      Video Only
                                    </span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Download Button */}
                  <button
                    className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                    onClick={downloadFrame}
                    disabled={loading || !selectedFrame}
                  >
                    {loading ? "Downloading..." : selectedFrame ? `Download Selected Frame${mergeAudio ? ' + Audio' : ''}` : "Select a frame to download"}
                  </button>

                  {/* Info Box */}
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mt-4">
                    <div className="flex items-start gap-2">
                      <div className="text-blue-600 mt-0.5">📋</div>
                      <div className="text-sm text-blue-800">
                        <strong>Frame Selection:</strong> Choose the exact video quality and format you want.
                        {mergeAudio ? ' Audio will be automatically merged for the best experience.' : ' Video-only download without audio.'}
                        {(videoInfo as any)?._browserInfo && (
                          <div className="mt-2 text-green-700 font-medium">
                            🌐 Using browser-assisted extraction (bypasses YouTube restrictions)
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Audio Mode */}
          {mode === "audio" && (
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
              <h2 className="text-xl font-semibold mb-4">Audio Download</h2>

              {videoInfo && (
                <div className="mb-6">
                  <div className="flex gap-4 mb-6">
                    {videoInfo.thumbnail && (
                      <img
                        src={videoInfo.thumbnail}
                        alt="Thumbnail"
                        className="w-32 h-24 object-cover rounded"
                      />
                    )}
                    <div>
                      <h3 className="font-semibold text-lg">{videoInfo.title}</h3>
                      <p className="text-gray-600">by {videoInfo.uploader}</p>
                      <p className="text-gray-500 text-sm">
                        Duration: {Math.floor((videoInfo.duration || 0) / 60)}:{String((videoInfo.duration || 0) % 60).padStart(2, '0')}
                      </p>
                    </div>
                  </div>

                  {/* Download Type Selection */}
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Download Type
                    </label>
                    <div className="grid grid-cols-3 gap-2">
                      <button
                        className={`p-3 rounded-lg border-2 transition-all ${downloadType === "sponsorblock"
                          ? "border-blue-500 bg-blue-50 text-blue-700"
                          : "border-gray-200 hover:border-gray-300"
                          }`}
                        onClick={() => setDownloadType("sponsorblock")}
                      >
                        <div className="text-lg mb-1">🎯</div>
                        <div className="font-medium">SponsorBlock</div>
                        <div className="text-xs text-gray-600">Auto-remove segments</div>
                      </button>
                      <button
                        className={`p-3 rounded-lg border-2 transition-all ${downloadType === "music"
                          ? "border-green-500 bg-green-50 text-green-700"
                          : "border-gray-200 hover:border-gray-300"
                          }`}
                        onClick={() => setDownloadType("music")}
                      >
                        <div className="text-lg mb-1">🎵</div>
                        <div className="font-medium">Music</div>
                        <div className="text-xs text-gray-600">Manual trim</div>
                      </button>
                      <button
                        className={`p-3 rounded-lg border-2 transition-all ${downloadType === "audio"
                          ? "border-gray-500 bg-gray-50 text-gray-700"
                          : "border-gray-200 hover:border-gray-300"
                          }`}
                        onClick={() => setDownloadType("audio")}
                      >
                        <div className="text-lg mb-1">🔊</div>
                        <div className="font-medium">Full Audio</div>
                        <div className="text-xs text-gray-600">Complete audio</div>
                      </button>
                    </div>
                  </div>

                  {/* SponsorBlock Options */}
                  {downloadType === "sponsorblock" && sponsorblockCategories && (
                    <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                      <h4 className="font-medium text-blue-900 mb-3">🎯 SponsorBlock Settings</h4>

                      <div className="mb-3">
                        <label className="block text-sm font-medium text-blue-800 mb-2">
                          Cleaning Preset
                        </label>
                        <select
                          className="w-full border border-blue-300 rounded-lg px-3 py-2 text-sm"
                          value={sponsorblockPreset}
                          onChange={(e) => setSponsorblockPreset(e.target.value)}
                        >
                          {Object.entries(sponsorblockCategories.presets).map(([key, preset]: [string, any]) => (
                            <option key={key} value={key}>
                              {preset.name} - {preset.description}
                            </option>
                          ))}
                          <option value="custom">Custom Selection</option>
                        </select>
                      </div>

                      {sponsorblockPreset === "custom" && (
                        <div className="mb-3">
                          <label className="block text-sm font-medium text-blue-800 mb-2">
                            Categories to Remove
                          </label>
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            {Object.entries(sponsorblockCategories.categories).map(([key, category]: [string, any]) => (
                              <label key={key} className="flex items-center gap-2">
                                <input
                                  type="checkbox"
                                  checked={customRemoveCategories.includes(key)}
                                  onChange={(e) => {
                                    if (e.target.checked) {
                                      setCustomRemoveCategories([...customRemoveCategories, key]);
                                    } else {
                                      setCustomRemoveCategories(customRemoveCategories.filter(c => c !== key));
                                    }
                                  }}
                                  className="rounded"
                                />
                                <span className={category.recommended_for_music ? "text-blue-700" : "text-gray-600"}>
                                  {category.name}
                                  {category.recommended_for_music && " ⭐"}
                                </span>
                              </label>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="text-xs text-blue-600">
                        <strong>How it works:</strong> SponsorBlock uses community-submitted data to automatically identify and remove sponsors, intros, outros, and other non-music segments from videos.
                      </div>
                    </div>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Audio Format
                      </label>
                      <select
                        className="w-full border border-gray-300 rounded-lg px-3 py-2"
                        value={audioFormat}
                        onChange={(e) => setAudioFormat(e.target.value)}
                      >
                        <option value="mp3">MP3</option>
                        <option value="aac">AAC</option>
                        <option value="flac">FLAC</option>
                        <option value="opus">Opus</option>
                        <option value="wav">WAV</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Quality
                      </label>
                      <select
                        className="w-full border border-gray-300 rounded-lg px-3 py-2"
                        value={audioQuality}
                        onChange={(e) => setAudioQuality(e.target.value)}
                      >
                        <option value="best">Best</option>
                        <option value="320">320 kbps</option>
                        <option value="256">256 kbps</option>
                        <option value="192">192 kbps</option>
                        <option value="128">128 kbps</option>
                      </select>
                    </div>
                  </div>

                  <button
                    className={`w-full py-3 rounded-lg disabled:opacity-50 ${downloadType === "sponsorblock"
                        ? "bg-blue-600 hover:bg-blue-700 text-white"
                        : downloadType === "music"
                          ? "bg-green-600 hover:bg-green-700 text-white"
                          : "bg-gray-600 hover:bg-gray-700 text-white"
                      }`}
                    onClick={
                      downloadType === "sponsorblock"
                        ? downloadSponsorBlockMusic
                        : downloadType === "music"
                          ? downloadMusic
                          : downloadAudio
                    }
                    disabled={loading}
                  >
                    {loading ? "Processing..." :
                      downloadType === "sponsorblock" ? "🎯 Download Clean Music (SponsorBlock)" :
                        downloadType === "music" ? "🎵 Download Music (Smart Trim)" :
                          "🔊 Download Full Audio"}
                  </button>

                  {/* Info Box */}
                  <div className={`mt-4 p-3 rounded-lg border ${downloadType === "sponsorblock" ? "bg-blue-50 border-blue-200" :
                      downloadType === "music" ? "bg-green-50 border-green-200" :
                        "bg-gray-50 border-gray-200"
                    }`}>
                    <div className="flex items-start gap-2">
                      <div className="mt-0.5">
                        {downloadType === "sponsorblock" ? "🎯" :
                          downloadType === "music" ? "🎵" : "🔊"}
                      </div>
                      <div className={`text-sm ${downloadType === "sponsorblock" ? "text-blue-800" :
                          downloadType === "music" ? "text-green-800" :
                            "text-gray-800"
                        }`}>
                        {downloadType === "sponsorblock" ? (
                          <>
                            <strong>SponsorBlock Mode:</strong> Uses community data to automatically remove sponsors, intros, outros, and promotional content. Perfect for clean music downloads.
                          </>
                        ) : downloadType === "music" ? (
                          <>
                            <strong>Music Mode:</strong> Intelligent trimming to remove channel promotions and non-music content based on video analysis.
                          </>
                        ) : (
                          <>
                            <strong>Full Audio Mode:</strong> Downloads the complete audio track including any promotions, intros, or outros.
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
          {/* Playlist Mode */}
          {mode === "playlist" && (
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
              <h2 className="text-xl font-semibold mb-4">Playlist Download</h2>

              <div className="mb-4">
                <button
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                  onClick={fetchPlaylistInfo}
                  disabled={loading || !url}
                >
                  {loading ? "Loading..." : "Fetch Playlist"}
                </button>
              </div>

              {playlistVideos.length > 0 && (
                <div>
                  <div className="mb-4">
                    <h3 className="font-semibold text-lg mb-2">{playlistTitle}</h3>
                    <p className="text-gray-600 mb-4">{playlistVideos.length} videos</p>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Download Mode
                        </label>
                        <select
                          className="w-full border border-gray-300 rounded-lg px-3 py-2"
                          value={playlistMode}
                          onChange={(e) => setPlaylistMode(e.target.value as "video" | "audio")}
                        >
                          <option value="audio">Audio Only</option>
                          <option value="video">Video</option>
                        </select>
                      </div>

                      {playlistMode === "audio" && (
                        <>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                              Audio Format
                            </label>
                            <select
                              className="w-full border border-gray-300 rounded-lg px-3 py-2"
                              value={audioFormat}
                              onChange={(e) => setAudioFormat(e.target.value)}
                            >
                              <option value="mp3">MP3</option>
                              <option value="aac">AAC</option>
                              <option value="flac">FLAC</option>
                            </select>
                          </div>

                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                              Quality
                            </label>
                            <select
                              className="w-full border border-gray-300 rounded-lg px-3 py-2"
                              value={audioQuality}
                              onChange={(e) => setAudioQuality(e.target.value)}
                            >
                              <option value="320">320 kbps</option>
                              <option value="256">256 kbps</option>
                              <option value="192">192 kbps</option>
                            </select>
                          </div>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="mb-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium">Select Videos</span>
                      <div className="space-x-2">
                        <button
                          className="text-sm text-blue-600 hover:text-blue-800"
                          onClick={() => setSelectedPlaylistVideos(playlistVideos.map(v => v.id))}
                        >
                          Select All
                        </button>
                        <button
                          className="text-sm text-blue-600 hover:text-blue-800"
                          onClick={() => setSelectedPlaylistVideos([])}
                        >
                          Clear All
                        </button>
                      </div>
                    </div>

                    <div className="max-h-64 overflow-y-auto border border-gray-200 rounded-lg">
                      {playlistVideos.map((video) => (
                        <div key={video.id} className="flex items-center p-3 border-b border-gray-100 last:border-b-0">
                          <input
                            type="checkbox"
                            checked={selectedPlaylistVideos.includes(video.id)}
                            onChange={() => handlePlaylistVideoSelect(video.id)}
                            className="mr-3"
                          />
                          <div className="flex-1">
                            <div className="font-medium text-sm">{video.title}</div>
                            <div className="text-xs text-gray-500">#{video.index}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <button
                    className="w-full bg-purple-600 text-white py-3 rounded-lg hover:bg-purple-700 disabled:opacity-50"
                    onClick={downloadPlaylist}
                    disabled={loading || selectedPlaylistVideos.length === 0}
                  >
                    {loading ? "Starting Download..." : `Download ${selectedPlaylistVideos.length} ${playlistMode === "audio" ? "Songs" : "Videos"}`}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Live Stream Mode */}
          {mode === "live" && (
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
              <h2 className="text-xl font-semibold mb-4">Live Stream Recording</h2>

              {liveInfo && (
                <div className="mb-6">
                  <div className="flex gap-4 mb-4">
                    {liveInfo.thumbnail && (
                      <img
                        src={liveInfo.thumbnail}
                        alt="Thumbnail"
                        className="w-32 h-24 object-cover rounded"
                      />
                    )}
                    <div>
                      <h3 className="font-semibold text-lg">{liveInfo.title}</h3>
                      <p className="text-gray-600">by {liveInfo.uploader}</p>
                      <div className="flex items-center gap-2 mt-2">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${liveInfo.is_live
                          ? "bg-red-100 text-red-800"
                          : "bg-gray-100 text-gray-800"
                          }`}>
                          {liveInfo.is_live ? "🔴 LIVE" : "Not Live"}
                        </span>
                        {liveInfo.live_status && (
                          <span className="text-sm text-gray-500">
                            {liveInfo.live_status}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Quality
                      </label>
                      <select
                        className="w-full border border-gray-300 rounded-lg px-3 py-2"
                        value={selectedQuality}
                        onChange={(e) => setSelectedQuality(e.target.value)}
                      >
                        <option value="best">Best Quality</option>
                        <option value="best[height<=1080]">1080p</option>
                        <option value="best[height<=720]">720p</option>
                        <option value="best[height<=480]">480p</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Duration Limit (minutes)
                      </label>
                      <input
                        type="number"
                        className="w-full border border-gray-300 rounded-lg px-3 py-2"
                        placeholder="No limit"
                        value={recordDuration || ""}
                        onChange={(e) => setRecordDuration(e.target.value ? parseInt(e.target.value) * 60 : null)}
                      />
                    </div>
                  </div>

                  <button
                    className="w-full bg-red-600 text-white py-3 rounded-lg hover:bg-red-700 disabled:opacity-50"
                    onClick={downloadLiveStream}
                    disabled={loading}
                  >
                    {loading ? "Starting Recording..." : "Record Live Stream"}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* M3U8 Mode */}
          {mode === "m3u8" && (
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
              <h2 className="text-xl font-semibold mb-4">M3U8 Stream Download</h2>

              <div className="mb-6">
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Custom Filename (optional)
                  </label>
                  <input
                    type="text"
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-orange-500"
                    placeholder="my_video.mp4"
                    value={m3u8Filename}
                    onChange={(e) => setM3u8Filename(e.target.value)}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Leave empty for auto-generated filename with timestamp
                  </p>
                </div>

                <button
                  className="w-full bg-orange-600 text-white py-3 rounded-lg hover:bg-orange-700 disabled:opacity-50"
                  onClick={downloadM3U8}
                  disabled={loading || !url}
                >
                  {loading ? "Starting Download..." : "Download M3U8 Stream"}
                </button>

                {/* Progress Display */}
                {m3u8Progress && (
                  <div className="mt-4 p-4 bg-orange-50 border border-orange-200 rounded-lg">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-orange-800">
                        {m3u8Progress.status === "downloading" ? "📥 Downloading & Decrypting" :
                         m3u8Progress.status === "starting" ? "🚀 Starting..." :
                         m3u8Progress.status === "completed" ? "✅ Completed" :
                         m3u8Progress.status === "failed" ? "❌ Failed" : m3u8Progress.status}
                      </span>
                      <span className="text-sm text-orange-600">
                        {m3u8Progress.progress ? `${m3u8Progress.progress.toFixed(1)}%` : ""}
                      </span>
                    </div>

                    {m3u8Progress.progress > 0 && (
                      <div className="bg-orange-200 rounded-full h-2 mb-2">
                        <div
                          className="bg-orange-600 h-2 rounded-full transition-all"
                          style={{ width: `${m3u8Progress.progress}%` }}
                        />
                      </div>
                    )}

                    {m3u8Progress.message && (
                      <p className="text-xs text-orange-700 mt-2">
                        {m3u8Progress.message}
                      </p>
                    )}

                    {m3u8Progress.error && (
                      <p className="text-xs text-red-600 mt-2">
                        Error: {m3u8Progress.error}
                      </p>
                    )}
                  </div>
                )}

                {/* Info Box */}
                <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 mt-4">
                  <div className="flex items-start gap-2">
                    <div className="text-orange-600 mt-0.5">📺</div>
                    <div className="text-sm text-orange-800">
                      <strong>M3U8 Stream Downloader:</strong> Downloads HLS (HTTP Live Streaming) videos with automatic AES-128 decryption support.
                      Segments are downloaded in parallel, decrypted, and merged into a single MP4 file.
                      Temporary files are automatically cleaned up after completion.
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* System Status */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">System Status</h3>
              <button
                onClick={async () => {
                  try {
                    const res = await fetch(`${API_BASE}/system/cleanup`, { method: 'POST' });
                    if (res.ok) {
                      setStatus("System cleanup completed");
                    }
                  } catch (e) {
                    setError("Cleanup failed");
                  }
                }}
                className="px-2 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600"
              >
                🧹 Cleanup
              </button>
            </div>
            <div className="text-xs text-gray-600">
              <p>Click cleanup if downloads are failing or system seems slow</p>
            </div>
          </div>

          {/* Queue Status */}
          {queueStatus && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold mb-4">Queue Status</h3>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span>Active:</span>
                  <span className="font-medium text-blue-600">{queueStatus.active_downloads}</span>
                </div>
                <div className="flex justify-between">
                  <span>Pending:</span>
                  <span className="font-medium text-yellow-600">{queueStatus.pending_items}</span>
                </div>
                <div className="flex justify-between">
                  <span>Completed:</span>
                  <span className="font-medium text-green-600">{queueStatus.completed_items}</span>
                </div>
                <div className="flex justify-between">
                  <span>Failed:</span>
                  <span className="font-medium text-red-600">{queueStatus.failed_items}</span>
                </div>
              </div>
            </div>
          )}

          {/* Recent Downloads */}
          {downloads.length > 0 && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold mb-4">Recent Downloads</h3>
              <div className="space-y-3">
                {downloads.slice(-5).map((download) => (
                  <div key={download.download_id} className="border-b border-gray-100 pb-2 last:border-b-0">
                    <div className="flex justify-between items-center">
                      <div className="flex-1 min-w-0">
                        <span className="text-sm font-medium truncate block">
                          {download.filename || download.download_id}
                        </span>
                        {download.status === "downloading" && download.progress > 90 && (
                          <span className="text-xs text-blue-600">🔧 Merging video+audio...</span>
                        )}
                      </div>
                      <span className={`text-xs px-2 py-1 rounded-full ml-2 ${download.status === "completed"
                        ? "bg-green-100 text-green-800"
                        : download.status === "failed"
                          ? "bg-red-100 text-red-800"
                          : "bg-blue-100 text-blue-800"
                        }`}>
                        {download.status === "completed" ? "✅ Done" :
                          download.status === "failed" ? "❌ Failed" :
                            download.status === "downloading" ? "📥 Downloading" : download.status}
                      </span>
                    </div>
                    {download.progress > 0 && download.status === "downloading" && (
                      <div className="mt-2">
                        <div className="flex justify-between text-xs text-gray-500 mb-1">
                          <span>{download.progress.toFixed(1)}%</span>
                          <span>{download.progress > 90 ? "Merging..." : "Downloading..."}</span>
                        </div>
                        <div className="bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full transition-all ${download.progress > 90 ? "bg-purple-600" : "bg-blue-600"
                              }`}
                            style={{ width: `${download.progress}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Help */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold mb-4">Help</h3>
            <div className="text-sm text-gray-600 space-y-3">
              <div>
                <p><strong>🎥 Video:</strong> Download videos up to 4K quality</p>
                <p className="text-xs text-gray-500 ml-4">• Auto-merges separate video+audio streams</p>
                <p className="text-xs text-gray-500 ml-4">• Clean filenames without special characters</p>
              </div>
              <div>
                <p><strong>🎵 Audio:</strong> Extract audio in MP3, FLAC, AAC, etc.</p>
                <p className="text-xs text-gray-500 ml-4">• Up to 320kbps quality</p>
              </div>
              <div>
                <p><strong>📋 Playlist:</strong> Batch download entire playlists</p>
                <p className="text-xs text-gray-500 ml-4">• Select specific videos or download all</p>
              </div>
              <div>
                <p><strong>🔴 Live:</strong> Record live streams and premieres</p>
                <p className="text-xs text-gray-500 ml-4">• Wait for streams to start automatically</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}