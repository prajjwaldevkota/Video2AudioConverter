import { AlertTriangle, RefreshCw, Home, Music, Sparkles, Zap } from "lucide-react";

export default function ErrorPage({ message = "Something went wrong", onRetry, onHome }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-800 relative overflow-hidden flex items-center justify-center">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-red-500/20 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-orange-500/20 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse delay-500"></div>
        
        {/* Floating music notes */}
        <div className="absolute top-20 left-20 animate-bounce delay-300">
          <Music className="w-6 h-6 text-white/20" />
        </div>
        <div className="absolute top-32 right-32 animate-bounce delay-700">
          <Sparkles className="w-4 h-4 text-purple-300/30" />
        </div>
        <div className="absolute bottom-32 left-32 animate-bounce delay-1000">
          <Zap className="w-5 h-5 text-blue-300/20" />
        </div>
      </div>

      <div className="relative z-10 text-center px-4 max-w-2xl mx-auto">
        {/* Error Icon with Pulsing Animation */}
        <div className="mb-8 relative">
          <div className="relative inline-flex items-center justify-center">
            <div className="absolute inset-0 bg-red-500/20 rounded-full blur-xl animate-pulse"></div>
            <div className="relative bg-white/10 backdrop-blur-xl border border-red-400/30 rounded-full p-8 shadow-2xl">
              <AlertTriangle className="w-16 h-16 text-red-400 animate-pulse" />
            </div>
          </div>
          
          {/* Ripple effect */}
          <div className="absolute inset-0 rounded-full border-2 border-red-400/20 animate-ping"></div>
          <div className="absolute inset-0 rounded-full border-2 border-red-400/10 animate-ping delay-300"></div>
        </div>

        {/* Error Title */}
        <div className="mb-6">
          <h1 className="text-5xl font-black mb-4 bg-gradient-to-r from-white via-red-200 to-orange-200 bg-clip-text text-transparent animate-pulse">
            Oops!
          </h1>
          <h2 className="text-2xl font-semibold text-white/90 mb-2">
            The beat stopped...
          </h2>
          <p className="text-lg text-white/70 font-light">
            Don't worry, we'll get your music flowing again
          </p>
        </div>

        {/* Error Message */}
        <div className="mb-8 bg-white/5 backdrop-blur-xl border border-red-400/20 rounded-2xl p-6 shadow-xl">
          <div className="flex items-center justify-center mb-3">
            <AlertTriangle className="w-5 h-5 text-red-400 mr-2 flex-shrink-0" />
            <span className="text-red-300 font-medium">Error Details</span>
          </div>
          <p className="text-white/80 text-base leading-relaxed">
            {message}
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
          {onRetry && (
            <button
              onClick={onRetry}
              className="group px-8 py-4 bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 text-white font-semibold rounded-2xl shadow-lg transform hover:scale-105 transition-all duration-300 flex items-center space-x-3"
            >
              <RefreshCw className="w-5 h-5 group-hover:rotate-180 transition-transform duration-500" />
              <span>Try Again</span>
            </button>
          )}
          
          {onHome && (
            <button
              onClick={onHome}
              className="group px-8 py-4 bg-white/10 hover:bg-white/20 backdrop-blur-xl border border-white/20 hover:border-white/30 text-white font-semibold rounded-2xl shadow-lg transform hover:scale-105 transition-all duration-300 flex items-center space-x-3"
            >
              <Home className="w-5 h-5 group-hover:scale-110 transition-transform duration-300" />
              <span>Go Home</span>
            </button>
          )}
        </div>

        {/* Helpful Tips */}
        <div className="mt-12 bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-xl">
          <h3 className="text-white font-semibold mb-4 flex items-center justify-center">
            <Sparkles className="w-4 h-4 mr-2 text-yellow-400" />
            Quick Fixes
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-white/70">
            <div className="flex flex-col items-center text-center p-3 bg-white/5 rounded-xl">
              <RefreshCw className="w-6 h-6 mb-2 text-blue-400" />
              <span className="font-medium text-white/90 mb-1">Refresh</span>
              <span>Try reloading the page</span>
            </div>
            <div className="flex flex-col items-center text-center p-3 bg-white/5 rounded-xl">
              <Zap className="w-6 h-6 mb-2 text-green-400" />
              <span className="font-medium text-white/90 mb-1">Connection</span>
              <span>Check your internet</span>
            </div>
            <div className="flex flex-col items-center text-center p-3 bg-white/5 rounded-xl">
              <Music className="w-6 h-6 mb-2 text-purple-400" />
              <span className="font-medium text-white/90 mb-1">Server</span>
              <span>Wait a moment & retry</span>
            </div>
          </div>
        </div>

        {/* Footer message */}
        <div className="mt-8 text-white/50 text-sm">
          <p>If the problem persists, please contact support</p>
        </div>
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

        .animate-fadeInUp {
          animation: fadeInUp 0.6s ease-out forwards;
        }
      `}</style>
    </div>
  );
}