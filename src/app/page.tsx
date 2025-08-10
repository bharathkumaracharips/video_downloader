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

type DownloadMode = "video" | "audio" | "playlist" | "live";

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

  const API_BASE = "http://127.0.0.1:8000/api";

  // Fetch video/audio info
  const fetchVideoInfo = async () => {
    if (!url) return;

    setLoading(true);
    setError("");
    setVideoInfo(null);

    try {
      const endpoint = mode === "live" ? "live/info" : "video/info";
      const res = await fetch(`${API_BASE}/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });

      if (!res.ok) throw new Error("Failed to fetch video info");
      const data = await res.json();

      if (mode === "live") {
        setLiveInfo(data);
      } else {
        setVideoInfo(data);
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
      const res = await fetch(`${API_BASE}/video/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url,
          quality: selectedQuality,
          format_id: selectedFormat !== "auto" ? selectedFormat : null,
        }),
      });

      if (!res.ok) throw new Error("Download failed");
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
    if (!url || !selectedFrame) return;

    setLoading(true);
    setError("");
    setStatus("");

    try {
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
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
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
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2">
          {/* URL Input */}
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              YouTube URL
            </label>
            <div className="flex gap-2">
              <input
                className="flex-1 border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                type="text"
                placeholder="https://www.youtube.com/watch?v=..."
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
                  <div className="flex gap-4 mb-4">
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
                    className="w-full bg-green-600 text-white py-3 rounded-lg hover:bg-green-700 disabled:opacity-50"
                    onClick={downloadAudio}
                    disabled={loading}
                  >
                    {loading ? "Starting Download..." : "Download Audio"}
                  </button>
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
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
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
                            className={`h-2 rounded-full transition-all ${
                              download.progress > 90 ? "bg-purple-600" : "bg-blue-600"
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