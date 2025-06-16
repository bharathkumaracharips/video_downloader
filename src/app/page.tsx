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

export default function Home() {
  const [url, setUrl] = useState("");
  const [formats, setFormats] = useState<Format[]>([]);
  const [title, setTitle] = useState("");
  const [selectedFormats, setSelectedFormats] = useState<string[]>([]);
  const [downloadedFiles, setDownloadedFiles] = useState<string[]>([]);
  const [mergePaths, setMergePaths] = useState({ video: "", audio: "", output: "" });
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(false);

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
    } catch (e: any) {
      setError(e.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="max-w-2xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">YouTube Downloader</h1>
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
        </div>
      )}
      {status && <div className="text-green-700 font-semibold mt-2">{status}</div>}
    </main>
  );
}
