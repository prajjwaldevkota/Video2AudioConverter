import { useState, useEffect } from "react";
import {
  Search,
  Download,
  Music,
  Settings,
  Sparkles,
  Zap,
  Crown,
  Radio,
  Info,
  AlertTriangle,
  X,
} from "lucide-react";
import ErrorPage from "./errorPage";

const URL = "https://video2audioconverter.onrender.com";

export default function App() {
  const [userInput, setUserInput] = useState("");
  const [videos, setVideos] = useState([]);
  const [format, setFormat] = useState("mp3");
  const [bitrate, setBitrate] = useState("320");
  const [method, setMethod] = useState("auto");
  const [isSearching, setIsSearching] = useState(false);
  const [downloadingVideos, setDownloadingVideos] = useState(new Set());
  const [, setAvailableFormats] = useState({});
  const [error, setError] = useState(null);
  const [showLosslessWarning, setShowLosslessWarning] = useState(false);
  const [pendingDownload, setPendingDownload] = useState(null);

  // Fetch available formats on component mount
  useEffect(() => {
    fetch(`${URL}/formats`)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
      })
      .then((data) => setAvailableFormats(data))
      .catch((err) => {
        console.error("Error fetching formats:", err);
        setError(
          "Failed to connect to server. Please check your connection and try again."
        );
      });
  }, []);

  const isLosslessFormat = (selectedFormat) => {
    return ["alac", "flac", "wav"].includes(selectedFormat);
  };

  const search = async () => {
    if (!userInput) return;
    setIsSearching(true);
    setError(null);

    try {
      const response = await fetch(
        `${URL}/search?query=${encodeURIComponent(userInput)}`
      );

      if (response.status === 404) {
        console.error("No results found");
      }

      if (!response.ok) {
        throw new Error(`Search failed with status: ${response.status}`);
      }
      const data = await response.json();
      if (!data || !Array.isArray(data)) {
        throw new Error("Invalid response format from server");
      }
      if (data.length === 0) {
        setError("No videos found. Try searching with different terms.");
        return;
      }
      setVideos(data);
    } catch (error) {
      console.error("Search error:", error);
      setError(error.message || "Search failed. Please try again.");
    } finally {
      setIsSearching(false);
    }
  };

  const handleDownload = async (videoUrl, videoTitle) => {
    // Check if format is lossless and show warning
    if (isLosslessFormat(format)) {
      setPendingDownload({ videoUrl, videoTitle });
      setShowLosslessWarning(true);
      return;
    }

    // Proceed with download directly for lossy formats
    await performDownload(videoUrl, videoTitle);
  };

  const performDownload = async (videoUrl, videoTitle) => {
    setDownloadingVideos((prev) => new Set([...prev, videoUrl]));

    try {
      const response = await fetch(
        `${URL}/download?url=${encodeURIComponent(
          videoUrl
        )}&format=${format}&bitrate=${bitrate}&method=${method}`
      );

      if (!response.ok) {
        throw new Error(`Download failed with status: ${response.status}`);
      }

      // Get the filename from the Content-Disposition header if available
      const contentDisposition = response.headers.get("Content-Disposition");
      let filename = `${videoTitle || "audio"}.${format}`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(
          /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/
        );
        if (filenameMatch) {
          filename = filenameMatch[1].replace(/['"]/g, "");
        }
      }

      // Create blob and download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Download error:", error);
      setError(error.message || "An error occurred during download.");
    } finally {
      setDownloadingVideos((prev) => {
        const newSet = new Set(prev);
        newSet.delete(videoUrl);
        return newSet;
      });
    }
  };

  const handleLosslessConfirm = () => {
    setShowLosslessWarning(false);
    if (pendingDownload) {
      performDownload(pendingDownload.videoUrl, pendingDownload.videoTitle);
      setPendingDownload(null);
    }
  };

  const handleLosslessCancel = () => {
    setShowLosslessWarning(false);
    setPendingDownload(null);
  };

  const formatDuration = (seconds) => {
    if (!seconds) return "";
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const getMethodInfo = (selectedMethod) => {
    const methodInfo = {
      auto: {
        icon: Sparkles,
        label: "Auto",
        description: "Smart selection based on format",
        color: "purple",
      },
      fast: {
        icon: Zap,
        label: "Fast",
        description: "Quick processing with yt-dlp",
        color: "blue",
      },
      quality: {
        icon: Crown,
        label: "Quality",
        description: "Best quality with FFmpeg",
        color: "yellow",
      },
      stream: {
        icon: Radio,
        label: "Stream",
        description: "Instant download start",
        color: "green",
      },
    };
    return methodInfo[selectedMethod] || methodInfo.auto;
  };

  const getFormatInfo = (selectedFormat) => {
    const formatInfo = {
      mp3: { quality: "Good", compatibility: "Universal", size: "Small" },
      aac: { quality: "Good", compatibility: "High", size: "Small" },
      alac: { quality: "Lossless", compatibility: "Apple", size: "Large" },
      flac: { quality: "Lossless", compatibility: "High", size: "Large" },
      wav: {
        quality: "Lossless",
        compatibility: "Universal",
        size: "Very Large",
      },
      ogg: { quality: "Good", compatibility: "Limited", size: "Small" },
    };
    return formatInfo[selectedFormat] || formatInfo.mp3;
  };

  const methodConfig = getMethodInfo(method);
  const MethodIcon = methodConfig.icon;

  if (error) {
    return (
      <ErrorPage
        message={error}
        onRetry={() => {
          setError(null);
          // Optionally reload the page or retry the last action
          window.location.reload();
        }}
        onHome={() => {
          setError(null);
          setVideos([]);
          setUserInput("");
        }}
      />
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-800 relative overflow-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-500/20 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-blue-500/20 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl animate-pulse delay-500"></div>
      </div>

      {/* Lossless Format Warning Modal */}
      {showLosslessWarning && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gradient-to-br from-orange-900/90 to-red-900/90 backdrop-blur-xl border border-orange-500/50 rounded-2xl p-8 max-w-md w-full shadow-2xl">
            <div className="flex items-center mb-6">
              <div className="flex-shrink-0">
                <AlertTriangle className="w-8 h-8 text-orange-400 mr-3" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-white mb-1">
                  Lossless Format Warning
                </h3>
                <p className="text-orange-200 text-sm">
                  {format.toUpperCase()} format selected
                </p>
              </div>
              <button
                onClick={handleLosslessCancel}
                className="ml-auto text-white/50 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4 mb-6">
              <div className="bg-orange-500/20 border border-orange-500/30 rounded-lg p-4">
                <h4 className="text-white font-semibold mb-2 flex items-center">
                  <Info className="w-4 h-4 mr-2" />
                  What to expect:
                </h4>
                <ul className="text-orange-100 text-sm space-y-2">
                  <li>
                    • <strong>Larger file sizes:</strong> 5-10x bigger than MP3
                  </li>
                  <li>
                    • <strong>Longer processing:</strong> 2-3x more time needed
                  </li>
                  <li>
                    • <strong>Higher bandwidth:</strong> Slower download speeds
                  </li>
                  <li>
                    • <strong>Perfect quality:</strong> No compression artifacts
                  </li>
                </ul>
              </div>

              <div className="text-center">
                <p className="text-white/70 text-sm">
                  Current selection:{" "}
                  <span className="font-semibold text-white">
                    {format.toUpperCase()}
                  </span>
                </p>
                <p className="text-orange-200 text-xs mt-1">
                  Estimated size:{" "}
                  {format === "wav"
                    ? "50-70MB"
                    : format === "flac"
                    ? "25-40MB"
                    : "30-50MB"}{" "}
                  per 5-minute song
                </p>
              </div>
            </div>

            <div className="flex space-x-3">
              <button
                onClick={handleLosslessCancel}
                className="flex-1 px-4 py-3 bg-white/10 border border-white/20 text-white font-medium rounded-xl hover:bg-white/20 transition-all duration-300"
              >
                Cancel
              </button>
              <button
                onClick={handleLosslessConfirm}
                className="flex-1 px-4 py-3 bg-gradient-to-r from-orange-500 to-red-600 hover:from-orange-600 hover:to-red-700 text-white font-semibold rounded-xl shadow-lg transform hover:scale-105 transition-all duration-300"
              >
                Continue Download
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen p-4 w-full">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center mb-4">
            <div className="relative">
              <Music className="w-12 h-12 text-white mr-3 sm:w-10 sm:h-10" />
              <Sparkles className="w-4 h-4 text-yellow-400 absolute -top-1 -right-1 animate-pulse" />
            </div>
            <h1 className="text-4xl font-black bg-gradient-to-r from-white via-purple-200 to-indigo-200 bg-clip-text text-transparent ">
              SoundScape Pro
            </h1>
          </div>
          <p className="text-xl text-white/70 font-light tracking-wide">
            Professional audio conversion with multiple quality options
          </p>
        </div>

        {/* Main Control Panel */}
        <div className="w-full max-w-6xl bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl shadow-2xl p-8 space-y-8 mb-12">
          {/* Search Section */}
          <div className="relative">
            <div className="flex items-center space-x-4">
              <div className="relative flex-1">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-white/50" />
                <input
                  className="w-full pl-12 pr-4 py-4 rounded-2xl bg-white/10 border border-white/20 backdrop-blur-sm placeholder-white/50 text-white text-lg focus:outline-none focus:ring-2 focus:ring-purple-400/50 focus:border-purple-400/50 transition-all duration-300"
                  placeholder="Search for your favorite tracks..."
                  value={userInput}
                  onChange={(e) => setUserInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && search()}
                />
              </div>
              <button
                onClick={search}
                disabled={isSearching}
                className="px-8 py-4 bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 disabled:from-gray-500 disabled:to-gray-600 text-white font-semibold rounded-2xl shadow-lg transform hover:scale-105 disabled:scale-100 transition-all duration-300 flex items-center space-x-2"
              >
                {isSearching ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    <span>Searching</span>
                  </>
                ) : (
                  <>
                    <Search className="w-5 h-5" />
                    <span>Search</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Advanced Settings Section */}
          <div className="bg-white/5 rounded-2xl p-6 border border-white/10">
            <div className="flex items-center mb-6">
              <Settings className="w-5 h-5 text-white/70 mr-2" />
              <h3 className="text-white font-semibold">
                Advanced Audio Settings
              </h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {/* Format Selection */}
              <div>
                <label className="block text-white/70 text-sm font-medium mb-2">
                  Audio Format
                </label>
                <select
                  className="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white focus:outline-none focus:ring-2 focus:ring-purple-400/50 transition-all duration-300"
                  value={format}
                  onChange={(e) => setFormat(e.target.value)}
                >
                  <option value="mp3" className="bg-gray-800">
                    MP3 - Universal
                  </option>
                  <option value="aac" className="bg-gray-800">
                    AAC - High Quality
                  </option>
                  <option value="alac" className="bg-gray-800">
                    ALAC - Apple Lossless
                  </option>
                  <option value="flac" className="bg-gray-800">
                    FLAC - Free Lossless
                  </option>
                  <option value="wav" className="bg-gray-800">
                    WAV - Uncompressed
                  </option>
                  <option value="ogg" className="bg-gray-800">
                    OGG - Open Source
                  </option>
                </select>
                <div className="mt-2 text-xs text-white/50">
                  Quality: {getFormatInfo(format).quality} • Size:{" "}
                  {getFormatInfo(format).size}
                </div>
              </div>

              {/* Bitrate Selection */}
              <div>
                <label className="block text-white/70 text-sm font-medium mb-2">
                  Bitrate Quality
                </label>
                <select
                  className="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white focus:outline-none focus:ring-2 focus:ring-purple-400/50 transition-all duration-300"
                  value={bitrate}
                  onChange={(e) => setBitrate(e.target.value)}
                  disabled={["alac", "flac", "wav"].includes(format)}
                >
                  {["128", "192", "256", "320"].map((b) => (
                    <option key={b} value={b} className="bg-gray-800">
                      {b} kbps{" "}
                      {b === "320"
                        ? "(Highest)"
                        : b === "128"
                        ? "(Fastest)"
                        : ""}
                    </option>
                  ))}
                </select>
                {["alac", "flac", "wav"].includes(format) && (
                  <div className="mt-2 text-xs text-white/50">
                    Lossless format - bitrate not applicable
                  </div>
                )}
              </div>

              {/* Processing Method */}
              <div>
                <label className="block text-white/70 text-sm font-medium mb-2">
                  Processing Method
                </label>
                <select
                  className="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white focus:outline-none focus:ring-2 focus:ring-purple-400/50 transition-all duration-300"
                  value={method}
                  onChange={(e) => setMethod(e.target.value)}
                >
                  <option value="auto" className="bg-gray-800">
                    Auto - Smart Selection
                  </option>
                  <option value="fast" className="bg-gray-800">
                    Fast - Quick Process
                  </option>
                  <option value="quality" className="bg-gray-800">
                    Quality - Best Audio
                  </option>
                  <option value="stream" className="bg-gray-800">
                    Stream - Instant Start
                  </option>
                </select>
                <div className="mt-2 flex items-center text-xs text-white/50">
                  <MethodIcon className="w-3 h-3 mr-1" />
                  {methodConfig.description}
                </div>
              </div>

              {/* Method Info Panel */}
              <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                <div className="flex items-center mb-2">
                  <MethodIcon
                    className={`w-4 h-4 mr-2 text-${methodConfig.color}-400`}
                  />
                  <span className="text-white text-sm font-medium">
                    {methodConfig.label} Mode
                  </span>
                </div>
                <p className="text-xs text-white/60 leading-relaxed">
                  {methodConfig.description}
                </p>
                <div className="mt-2 flex items-center text-xs text-white/40">
                  <Info className="w-3 h-3 mr-1" />
                  {method === "auto"
                    ? "Optimized for your format"
                    : method === "fast"
                    ? "~30% faster processing"
                    : method === "quality"
                    ? "Professional grade output"
                    : "Start download immediately"}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Results Grid */}
        {videos.length > 0 && (
          <div className="w-full max-w-none px-4">
            <h2 className="text-2xl font-bold text-white mb-6 text-center">
              Choose your tracks • {format.toUpperCase()} • {methodConfig.label}{" "}
              Mode
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6">
              {videos.map((v, index) => (
                <div
                  key={v.url}
                  className="group bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden shadow-xl hover:shadow-2xl transform hover:scale-105 transition-all duration-500"
                  style={{
                    animationDelay: `${index * 100}ms`,
                    animation: "fadeInUp 0.6s ease-out forwards",
                  }}
                >
                  <div className="relative overflow-hidden">
                    <img
                      src={v.thumbnail}
                      alt={v.title}
                      className="w-full h-48 object-cover transition-transform duration-500 group-hover:scale-110"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                    {v.duration && (
                      <div className="absolute bottom-2 right-2 bg-black/70 text-white text-xs px-2 py-1 rounded">
                        {formatDuration(v.duration)}
                      </div>
                    )}
                  </div>
                  <div className="p-6">
                    <h3 className="text-white font-semibold mb-4 line-clamp-2 leading-relaxed">
                      {v.title}
                    </h3>
                    <button
                      onClick={() => handleDownload(v.url, v.title)}
                      disabled={downloadingVideos.has(v.url)}
                      className="w-full py-3 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 disabled:from-gray-500 disabled:to-gray-600 text-white font-semibold rounded-xl shadow-lg transform hover:scale-105 disabled:scale-100 transition-all duration-300 flex items-center justify-center space-x-2"
                    >
                      {downloadingVideos.has(v.url) ? (
                        <>
                          <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                          <span>Processing...</span>
                        </>
                      ) : (
                        <>
                          <Download className="w-5 h-5" />
                          <span>Download {format.toUpperCase()}</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(30px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .line-clamp-2 {
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
      `}</style>
    </div>
  );
}
