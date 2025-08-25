import requests
import os
import subprocess
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import re
import uuid
from typing import Optional, Callable
import asyncio

# Headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/127.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site"
}

class M3U8Downloader:
    def __init__(self, progress_callback: Optional[Callable] = None):
        self.progress_callback = progress_callback
        self.headers = HEADERS.copy()

    def _log(self, message: str):
        """Log message with optional progress callback"""
        print(message)
        if self.progress_callback:
            self.progress_callback({"type": "log", "message": message})

    def _parse_m3u8(self, m3u8_url: str):
        """Parse M3U8 playlist and extract segments and encryption info"""
        self._log(f"[*] Fetching playlist from {m3u8_url}")

        try:
            resp = requests.get(m3u8_url, headers=self.headers, timeout=30)
            self._log(f"[*] Response status: {resp.status_code}")

            if resp.status_code == 401:
                self._log("[!] 401 Unauthorized - JWT token may have expired")
                self._log("[*] Attempting to extract token info...")

                # Try to extract and decode JWT token for debugging
                try:
                    import base64
                    import json
                    from urllib.parse import urlparse

                    # Extract JWT from URL path
                    path = urlparse(m3u8_url).path
                    if '/' in path:
                        potential_jwt = path.split('/')[1]  # Get the JWT part
                        if '.' in potential_jwt:  # JWT has dots
                            payload = potential_jwt.split('.')[1]
                            payload += '=' * (4 - len(payload) % 4)  # Add padding
                            decoded = json.loads(base64.b64decode(payload))

                            from datetime import datetime
                            exp_time = datetime.fromtimestamp(decoded.get('exp', 0))
                            current_time = datetime.now()

                            self._log(f"[*] Token expires at: {exp_time}")
                            self._log(f"[*] Current time: {current_time}")
                            self._log(f"[*] Token expired: {current_time > exp_time}")

                except Exception as e:
                    self._log(f"[*] Could not decode JWT: {e}")

            resp.raise_for_status()
            lines = resp.text.splitlines()

        except requests.exceptions.RequestException as e:
            self._log(f"[!] Request failed: {e}")
            raise

        # Parse M3U8 for segments and encryption info
        base_url = m3u8_url.rsplit("/", 1)[0]
        segments = []
        encryption_key = None
        encryption_iv = None

        for line in lines:
            if line.startswith("#EXT-X-KEY:"):
                # Parse encryption key info
                if "METHOD=AES-128" in line:
                    key_match = re.search(r'URI="([^"]+)"', line)
                    iv_match = re.search(r'IV=0x([0-9A-Fa-f]+)', line)

                    if key_match:
                        key_url = key_match.group(1)
                        self._log(f"[*] Found encryption key URL: {key_url}")
                        # Download encryption key
                        key_resp = requests.get(key_url, headers=self.headers)
                        key_resp.raise_for_status()
                        encryption_key = key_resp.content
                        self._log(f"[*] Downloaded encryption key ({len(encryption_key)} bytes)")

                    if iv_match:
                        encryption_iv = bytes.fromhex(iv_match.group(1))
                        self._log(f"[*] Found IV: {iv_match.group(1)}")

            elif line.endswith(".ts"):
                # Add segment URL
                segment_url = line if line.startswith("http") else f"{base_url}/{line}"
                segments.append(segment_url)

        self._log(f"[*] Found {len(segments)} segments.")
        if encryption_key:
            self._log(f"[*] Stream is encrypted with AES-128")

        return segments, encryption_key, encryption_iv

    def _download_and_decrypt_segment(self, url_and_index, encryption_key, encryption_iv, temp_dir):
        """Download and decrypt a single segment"""
        url, index = url_and_index
        filename = os.path.join(temp_dir, f"{index:03d}.ts")

        if os.path.exists(filename):
            return filename

        try:
            # Download encrypted segment
            r = requests.get(url, headers=self.headers, timeout=15)
            r.raise_for_status()
            encrypted_data = r.content

            if encryption_key:
                # Decrypt the segment
                # For AES-128, if no IV is specified, use the segment sequence number
                iv = encryption_iv if encryption_iv else index.to_bytes(16, byteorder='big')

                cipher = AES.new(encryption_key, AES.MODE_CBC, iv)
                decrypted_data = cipher.decrypt(encrypted_data)

                # Remove PKCS7 padding if present
                try:
                    decrypted_data = unpad(decrypted_data, AES.block_size)
                except ValueError:
                    # If unpadding fails, use raw decrypted data
                    pass

                with open(filename, "wb") as f:
                    f.write(decrypted_data)
            else:
                # No encryption, save as-is
                with open(filename, "wb") as f:
                    f.write(encrypted_data)

            return filename
        except Exception as e:
            self._log(f"[!] Failed to download segment {index}: {e}")
            return None

    async def download_m3u8(self, m3u8_url: str, output_path: str) -> str:
        """Download M3U8 stream and return the output file path"""
        download_id = str(uuid.uuid4())
        temp_dir = None

        try:
            # Create temporary directory for segments
            temp_dir = tempfile.mkdtemp(prefix=f"m3u8_{download_id}_")
            self._log(f"[*] Using temporary directory: {temp_dir}")

            # Parse M3U8 playlist
            segments, encryption_key, encryption_iv = self._parse_m3u8(m3u8_url)

            if not segments:
                raise Exception("No segments found in M3U8 playlist")

            # Download segments
            self._log("[*] Downloading and decrypting segments...")
            results = []
            failed_segments = []

            with ThreadPoolExecutor(max_workers=8) as executor:
                # Create list of (url, index) tuples for proper ordering
                url_index_pairs = [(url, i) for i, url in enumerate(segments)]
                futures = {executor.submit(self._download_and_decrypt_segment, pair, encryption_key, encryption_iv, temp_dir): pair for pair in url_index_pairs}

                completed = 0
                for future in as_completed(futures):
                    seg_file = future.result()
                    completed += 1

                    if self.progress_callback:
                        self.progress_callback({
                            "type": "progress",
                            "current": completed,
                            "total": len(segments),
                            "percentage": (completed / len(segments)) * 100
                        })

                    if seg_file:
                        results.append(seg_file)
                    else:
                        # Track failed segments for retry
                        url, index = futures[future]
                        failed_segments.append((url, index))

            self._log(f"[*] Successfully downloaded {len(results)} out of {len(segments)} segments")
            self._log(f"[*] Failed segments: {len(failed_segments)}")

            # Retry failed segments if any
            if failed_segments:
                results.extend(await self._retry_failed_segments(failed_segments, encryption_key, encryption_iv, temp_dir, segments))

            # Merge segments
            final_output = await self._merge_segments(results, output_path, temp_dir)

            return final_output

        except Exception as e:
            self._log(f"[!] Download failed: {e}")
            raise
        finally:
            # Cleanup temporary directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    self._log(f"[*] Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    self._log(f"[!] Failed to cleanup temp directory: {e}")

    async def _retry_failed_segments(self, failed_segments, encryption_key, encryption_iv, temp_dir, segments):
        """Retry downloading failed segments with different strategies"""
        self._log(f"[*] Retrying {len(failed_segments)} failed segments...")

        def download_and_decrypt_segment_retry(url_and_index, timeout=30):
            url, index = url_and_index
            filename = os.path.join(temp_dir, f"{index:03d}.ts")

            if os.path.exists(filename):
                return filename

            try:
                # Download with longer timeout
                r = requests.get(url, headers=self.headers, timeout=timeout)
                r.raise_for_status()
                encrypted_data = r.content

                if encryption_key:
                    # Decrypt the segment
                    iv = encryption_iv if encryption_iv else index.to_bytes(16, byteorder='big')
                    cipher = AES.new(encryption_key, AES.MODE_CBC, iv)
                    decrypted_data = cipher.decrypt(encrypted_data)

                    # Remove PKCS7 padding if present
                    try:
                        decrypted_data = unpad(decrypted_data, AES.block_size)
                    except ValueError:
                        pass

                    with open(filename, "wb") as f:
                        f.write(decrypted_data)
                else:
                    with open(filename, "wb") as f:
                        f.write(encrypted_data)

                return filename
            except Exception as e:
                self._log(f"[!] Retry failed for segment {index}: {e}")
                return None

        retry_results = []

        # First retry with longer timeout
        with ThreadPoolExecutor(max_workers=4) as executor:
            retry_futures = {executor.submit(download_and_decrypt_segment_retry, pair, 30): pair for pair in failed_segments}

            for future in as_completed(retry_futures):
                seg_file = future.result()
                if seg_file:
                    retry_results.append(seg_file)

        self._log(f"[*] First retry recovered {len(retry_results)} segments")

        # Second retry for still-failed segments
        still_failed = [pair for pair in failed_segments if not os.path.exists(os.path.join(temp_dir, f"{pair[1]:03d}.ts"))]

        if still_failed:
            self._log(f"[*] Second retry for {len(still_failed)} segments with 60s timeout...")
            with ThreadPoolExecutor(max_workers=2) as executor:
                retry_futures2 = {executor.submit(download_and_decrypt_segment_retry, pair, 60): pair for pair in still_failed}

                for future in as_completed(retry_futures2):
                    seg_file = future.result()
                    if seg_file:
                        retry_results.append(seg_file)

        self._log(f"[*] Total retry recovery: {len(retry_results)} segments")
        return retry_results

    async def _merge_segments(self, results, output_path, temp_dir):
        """Merge downloaded segments into final video file"""
        results.sort()  # Ensure proper order

        if not results:
            raise Exception("No segments available for merging")

        # Create temporary file list for ffmpeg
        files_list_path = os.path.join(temp_dir, "files.txt")
        with open(files_list_path, "w") as f:
            for seg in results:
                f.write(f"file '{os.path.abspath(seg)}'\n")

        # Analyze missing segments
        downloaded_indices = set()
        for seg_file in results:
            filename = os.path.basename(seg_file)
            index = int(filename.split('.')[0])
            downloaded_indices.add(index)

        # Merge with ffmpeg
        self._log("[*] Merging segments into final MP4...")
        try:
            result = subprocess.run([
                "ffmpeg", "-f", "concat", "-safe", "0",
                "-i", files_list_path, "-c", "copy", "-y", output_path
            ], capture_output=True, text=True, check=True)

            self._log("[✅] Successfully merged segments!")
            return output_path

        except subprocess.CalledProcessError as e:
            self._log(f"[!] FFmpeg error: {e.stderr}")
            # Try alternative merge method
            self._log("[*] Trying alternative merge method...")

            alt_output = output_path.replace('.mp4', '_alt.mp4')
            try:
                subprocess.run([
                    "ffmpeg", "-i", f"concat:{'|'.join(results)}",
                    "-c", "copy", "-y", alt_output
                ], check=True)
                self._log("[✅] Alternative merge completed!")
                return alt_output
            except subprocess.CalledProcessError as e2:
                raise Exception(f"Both merge methods failed: {e.stderr}, {e2}")

        except Exception as e:
            raise Exception(f"Merge failed: {e}")

# Convenience function for direct usage
async def download_m3u8_video(m3u8_url: str, output_path: str = "downloaded.mp4", progress_callback: Optional[Callable] = None) -> str:
    """Download M3U8 video with cleanup"""
    downloader = M3U8Downloader(progress_callback)
    return await downloader.download_m3u8(m3u8_url, output_path)


# For backward compatibility - if run as script
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python m3u8.py <m3u8_url> [output_file]")
        sys.exit(1)

    url = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else "downloaded.mp4"

    async def main():
        try:
            result = await download_m3u8_video(url, output)
            print(f"[✅] Download completed: {result}")
        except Exception as e:
            print(f"[!] Download failed: {e}")
            sys.exit(1)

    asyncio.run(main())