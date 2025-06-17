"use client";
import React, { useState } from "react";

interface Format {
  format_id: string;
  ext: string;
  resolution: string;
  fps: string;
  type: string;
  note: string;
}

interface PlaylistVideo {
  id: string;
  title: string;
  index: number;
}

export default function Home() {
  const [mode, setMode] = useState<"single" | "playlist" | null>(null);

  // Single video states
  const [url, setUrl] = useState("");
  const [formats, setFormats] = useState<Format[]>([]);
  const [title, setTitle] = useState("");
  const [selectedFormats, setSelectedFormats] = useState<string[]>([]);
  const [downloadedFiles, setDownloadedFiles] = useState<string[]>([]);
  const [mergePaths, setMergePaths] = useState({ video: "", audio: "", output: "" });
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [mergeResult, setMergeResult] = useState<any>(null);

  // Playlist states
  const [playlistUrl, setPlaylistUrl] = useState("");
  const [playlistVideos, setPlaylistVideos] = useState<PlaylistVideo[]>([]);
  const [selectedPlaylistVideos, setSelectedPlaylistVideos] = useState<string[]>([]);
  const [playlistTitle, setPlaylistTitle] = useState("");
  const [playlistStatus, setPlaylistStatus] = useState<string>("");
  const [playlistError, setPlaylistError] = useState<string>("");
  const [playlistLoading, setPlaylistLoading] = useState(false);
  const [isAudioDownloading, setIsAudioDownloading] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState<{
    current: number;
    total: number;
    files: Array<{ filename: string; status: "success" | "error" }>;
  }>({ current: 0, total: 0, files: [] });

  const fetchFormats = async () => {
    setLoading(true);
    setError("");
    setFormats([]);
    setDownloadedFiles([]);
    setSelectedFormats([]);
    setStatus("");
    try {
      const res = await fetch("http://127.0.0.1:8000/list_formats", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      if (!res.ok) throw new Error("Failed to fetch formats");
      const data = await res.json();
      setFormats(data.formats);
      setTitle(data.title);
    } catch (e: any) {
      setError(e.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const handleFormatSelect = (fid: string) => {
    setSelectedFormats((prev) =>
      prev.includes(fid) ? prev.filter((f) => f !== fid) : [...prev, fid]
    );
  };

  const downloadSelected = async () => {
    setLoading(true);
    setError("");
    setStatus("");
    setDownloadedFiles([]);
    try {
      const res = await fetch("http://127.0.0.1:8000/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, format_ids: selectedFormats }),
      });
      if (!res.ok) throw new Error("Download failed");
      const data = await res.json();
      setDownloadedFiles(data.files);
      setStatus("Download complete!");
      if (data.files.length === 2) {
        setMergePaths({ video: data.files[0], audio: data.files[1], output: "merged.mp4" });
      }
    } catch (e: any) {
      setError(e.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const handleMerge = async () => {
    setLoading(true);
    setError("");
    setStatus("");
    setMergeResult(null);
    try {
      const res = await fetch("http://127.0.0.1:8000/merge", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_path: mergePaths.video,
          audio_path: mergePaths.audio,
          output_path: mergePaths.output,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Merge failed");
      setStatus(`Merge complete! Output: ${data.output}`);
      setMergeResult(data);
    } catch (e: any) {
      setError(e.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const fetchPlaylistVideos = async () => {
    setPlaylistLoading(true);
    setPlaylistError("");
    setPlaylistVideos([]);
    setSelectedPlaylistVideos([]);
    setPlaylistStatus("");
    try {
      const res = await fetch("http://127.0.0.1:8000/list_playlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: playlistUrl }),
      });
      if (!res.ok) throw new Error("Failed to fetch playlist");
      const data = await res.json();
      setPlaylistVideos(data.videos);
      setPlaylistTitle(data.title);
      setSelectedPlaylistVideos(data.videos.map((v: PlaylistVideo) => v.id));
    } catch (e: any) {
      setPlaylistError(e.message || "Unknown error");
    } finally {
      setPlaylistLoading(false);
    }
  };

  const handlePlaylistVideoSelect = (id: string) => {
    setSelectedPlaylistVideos((prev) =>
      prev.includes(id) ? prev.filter((v) => v !== id) : [...prev, id]
    );
  };

  const downloadPlaylistSelected = async () => {
    setPlaylistLoading(true);
    setPlaylistError("");
    setPlaylistStatus("");
    try {
      const res = await fetch("http://127.0.0.1:8000/download_playlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: playlistUrl, video_ids: selectedPlaylistVideos }),
      });
      if (!res.ok) throw new Error("Download failed");
      const data = await res.json();
      setPlaylistStatus("Playlist download complete!");
    } catch (e: any) {
      setPlaylistError(e.message || "Unknown error");
    } finally {
      setPlaylistLoading(false);
    }
  };

  const downloadPlaylistAudio = async () => {
    setPlaylistLoading(true);
    setIsAudioDownloading(true);
    setPlaylistError("");
    setPlaylistStatus("");
    setDownloadProgress({ current: 0, total: 0, files: [] });

    const encodedUrl = encodeURIComponent(playlistUrl);
    const eventSource = new EventSource(`http://127.0.0.1:8000/download_playlist_audio?url=${encodedUrl}`, {
      withCredentials: true
    });

    // Clean up function to properly close EventSource
    const cleanup = () => {
      if (eventSource) {
        eventSource.close();
      }
      setPlaylistLoading(false);
      setIsAudioDownloading(false);
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("Progress update:", data);
      } catch (error) {
        console.error("Error parsing message:", error);
      }
    };

    eventSource.addEventListener("total", (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        setDownloadProgress(prev => ({
          ...prev,
          total: data.total
        }));
      } catch (error) {
        console.error("Error parsing total event:", error);
        cleanup();
      }
    });

    eventSource.addEventListener("progress", (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        setDownloadProgress(prev => ({
          current: data.current,
          total: data.total,
          files: [...prev.files, { filename: data.filename, status: data.status }]
        }));
      } catch (error) {
        console.error("Error parsing progress event:", error);
        cleanup();
      }
    });

    eventSource.addEventListener("complete", (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        setPlaylistStatus("Playlist audio download complete!");
        cleanup();
      } catch (error) {
        console.error("Error parsing complete event:", error);
        cleanup();
      }
    });

    eventSource.addEventListener("error", (e: MessageEvent) => {
      try {
        if (e.data) {
          const data = JSON.parse(e.data);
          setPlaylistError(data.message || "Download failed");
        } else {
          setPlaylistError("Connection failed");
        }
      } catch (error) {
        console.error("Error parsing error event:", error);
        setPlaylistError("Connection failed");
      } finally {
        cleanup();
      }
    });

    eventSource.addEventListener("stopped", (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        setPlaylistStatus(data.message);
        cleanup();
      } catch (error) {
        console.error("Error parsing stopped event:", error);
        cleanup();
      }
    });

    // Handle connection errors
    eventSource.onerror = (error) => {
      console.error("EventSource failed:", error);
      setPlaylistError("Connection failed");
      cleanup();
    };

    // Clean up on component unmount
    return () => {
      cleanup();
    };
  };

  const stopDownload = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/stop_download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (!res.ok) throw new Error("Failed to stop download");
      setPlaylistStatus("Download stopped.");
    } catch (e: any) {
      setPlaylistError(e.message || "Unknown error");
    }
  };

  return (
    <main className="max-w-2xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">YouTube Downloader</h1>
      <div className="flex gap-4 mb-6">
        <button
          className={`px-4 py-2 rounded ${mode === "single" ? "bg-blue-700 text-white" : "bg-blue-100 text-blue-700"}`}
          onClick={() => setMode("single")}
        >
          Single Video Download
        </button>
        <button
          className={`px-4 py-2 rounded ${mode === "playlist" ? "bg-green-700 text-white" : "bg-green-100 text-green-700"}`}
          onClick={() => setMode("playlist")}
        >
          Playlist Download
        </button>
      </div>
      {mode === "single" && (
        <>
          <div className="mb-4">
            <input
              className="border p-2 w-full rounded"
              type="text"
              placeholder="Enter YouTube URL"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            <button
              className="mt-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              onClick={fetchFormats}
              disabled={loading || !url}
            >
              {loading ? "Loading..." : "Fetch Formats"}
            </button>
          </div>
          {error && <div className="text-red-600 mb-2">{error}</div>}
          {formats.length > 0 && (
            <div className="mb-4">
              <h2 className="font-semibold mb-2">Available Formats for: {title}</h2>
              <div className="overflow-x-auto">
                <table className="min-w-full border text-sm">
                  <thead>
                    <tr>
                      <th className="border px-2">Select</th>
                      <th className="border px-2">Format ID</th>
                      <th className="border px-2">Ext</th>
                      <th className="border px-2">Res</th>
                      <th className="border px-2">FPS</th>
                      <th className="border px-2">Type</th>
                      <th className="border px-2">Note</th>
                    </tr>
                  </thead>
                  <tbody>
                    {formats.map((f) => (
                      <tr key={f.format_id}>
                        <td className="border px-2 text-center">
                          <input
                            type="checkbox"
                            checked={selectedFormats.includes(f.format_id)}
                            onChange={() => handleFormatSelect(f.format_id)}
                          />
                        </td>
                        <td className="border px-2">{f.format_id}</td>
                        <td className="border px-2">{f.ext}</td>
                        <td className="border px-2">{f.resolution}</td>
                        <td className="border px-2">{f.fps}</td>
                        <td className="border px-2">{f.type}</td>
                        <td className="border px-2">{f.note}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <button
                className="mt-2 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                onClick={downloadSelected}
                disabled={loading || selectedFormats.length === 0}
              >
                {loading ? "Downloading..." : "Download Selected"}
              </button>
            </div>
          )}
          {downloadedFiles.length > 0 && (
            <div className="mb-4">
              <h2 className="font-semibold mb-2">Downloaded Files</h2>
              <ul className="list-disc ml-6">
                {downloadedFiles.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </div>
          )}
          {downloadedFiles.length === 2 && (
            <div className="mb-4 border-t pt-4">
              <h2 className="font-semibold mb-2">Merge Video & Audio</h2>
              <div className="flex flex-col gap-2">
                <input
                  className="border p-2 rounded"
                  type="text"
                  placeholder="Video file path"
                  value={mergePaths.video}
                  onChange={e => setMergePaths({ ...mergePaths, video: e.target.value })}
                />
                <input
                  className="border p-2 rounded"
                  type="text"
                  placeholder="Audio file path"
                  value={mergePaths.audio}
                  onChange={e => setMergePaths({ ...mergePaths, audio: e.target.value })}
                />
                <input
                  className="border p-2 rounded"
                  type="text"
                  placeholder="Output file name (e.g., merged.mp4)"
                  value={mergePaths.output}
                  onChange={e => setMergePaths({ ...mergePaths, output: e.target.value })}
                />
                <button
                  className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700"
                  onClick={handleMerge}
                  disabled={loading || !mergePaths.video || !mergePaths.audio || !mergePaths.output}
                >
                  {loading ? "Merging..." : "Merge"}
                </button>
              </div>
              {status && mergeResult?.download_url && (
                <a
                  href={`http://127.0.0.1:8000${mergeResult.download_url}`}
                  download
                  className="mt-4 inline-block px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Download Merged File
                </a>
              )}
            </div>
          )}
          {status && <div className="text-green-700 font-semibold mt-2">{status}</div>}
        </>
      )}
      {mode === "playlist" && (
        <>
          <div className="mb-4">
            <input
              className="border p-2 w-full rounded"
              type="text"
              placeholder="Enter YouTube Playlist URL"
              value={playlistUrl}
              onChange={(e) => setPlaylistUrl(e.target.value)}
            />
            <div className="flex gap-2">
              <button
                className="mt-2 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                onClick={fetchPlaylistVideos}
                disabled={playlistLoading || !playlistUrl}
              >
                {playlistLoading ? "Loading..." : "Fetch Playlist"}
              </button>
              <button
                className="mt-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                onClick={downloadPlaylistAudio}
                disabled={playlistLoading || !playlistUrl || isAudioDownloading}
              >
                {isAudioDownloading ? "Downloading Songs..." : "Download Songs (MP3)"}
              </button>
              {(playlistLoading || isAudioDownloading) && (
                <button
                  className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                  onClick={stopDownload}
                >
                  Stop Download
                </button>
              )}
            </div>
          </div>
          {playlistError && <div className="text-red-600 mb-2">{playlistError}</div>}
          {downloadProgress.total > 0 && (
            <div className="mt-4">
              <h3 className="font-semibold mb-2">Download Progress</h3>
              <div className="bg-gray-200 rounded-full h-4 mb-2">
                <div 
                  className="bg-blue-600 h-4 rounded-full transition-all duration-300"
                  style={{ width: `${(downloadProgress.current / downloadProgress.total) * 100}%` }}
                ></div>
              </div>
              <p className="text-sm text-gray-600 mb-2">
                Downloaded: {downloadProgress.current} / {downloadProgress.total}
              </p>
              {downloadProgress.files.length > 0 && (
                <div className="mt-2">
                  <h4 className="font-medium mb-1">Downloaded Files:</h4>
                  <div className="max-h-40 overflow-y-auto">
                    {downloadProgress.files.map((file, index) => (
                      <div 
                        key={index} 
                        className={`text-sm py-1 border-b ${
                          file.status === "error" ? "text-red-600" : "text-gray-800"
                        }`}
                      >
                        <span className="text-gray-600">{index + 1}/{downloadProgress.total}</span>
                        {" - "}
                        <span>{file.filename}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          {playlistVideos.length > 0 && (
            <div className="mb-4">
              <h2 className="font-semibold mb-2">Playlist: {playlistTitle}</h2>
              <div className="mb-2 text-sm text-gray-700">Default quality: <span className="font-mono">bestvideo+bestaudio/best</span></div>
              <div className="overflow-x-auto">
                <table className="min-w-full border text-sm">
                  <thead>
                    <tr>
                      <th className="border px-2">Select</th>
                      <th className="border px-2">Index</th>
                      <th className="border px-2">Title</th>
                    </tr>
                  </thead>
                  <tbody>
                    {playlistVideos.map((v) => (
                      <tr key={v.id}>
                        <td className="border px-2 text-center">
                          <input
                            type="checkbox"
                            checked={selectedPlaylistVideos.includes(v.id)}
                            onChange={() => handlePlaylistVideoSelect(v.id)}
                          />
                        </td>
                        <td className="border px-2">{v.index}</td>
                        <td className="border px-2">{v.title}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <button
                className="mt-2 px-4 py-2 bg-blue-700 text-white rounded hover:bg-blue-800"
                onClick={downloadPlaylistSelected}
                disabled={playlistLoading || selectedPlaylistVideos.length === 0}
              >
                {playlistLoading ? "Downloading..." : "Download Selected Videos"}
              </button>
            </div>
          )}
          {playlistStatus && <div className="text-green-700 font-semibold mt-2">{playlistStatus}</div>}
        </>
      )}
    </main>
  );
}
