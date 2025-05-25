// src/ErrorPage.jsx
import React from "react";
import { Img } from "react-image";
import icon from "./assets/icon.png";

export default function ErrorPage({ message, onRetry }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-red-900 to-black p-8">
      <div className="w-50 h-50 mb-4 flex items-center justify-center mt-0">
        <Img
          src={icon}
          alt="Error Icon"
          className="w-full h-full object-contain brightness-125 contrast-75 drop-shadow-[0_0_10px_rgba(255,100,100,0.7)]" 
          style={{ filter: "drop-shadow(0 0 10px rgba(255, 100, 100, 0.7))" }}
          loader={<div className="w-full h-full bg-white/10 rounded-full" />}
          unloader={
            <div className="w-full h-full bg-red-500/30 rounded-full flex items-center justify-center text-white font-bold">
              !
            </div>
          }
        />
      </div>
      <h1 className="text-5xl font-bold text-white mb-4">Oops!</h1>
      <p className="text-lg text-red-300 mb-8">
        {message || "Something went wrong."}
      </p>
      <button
        onClick={onRetry}
        className="px-6 py-3 bg-white/20 hover:bg-white/30 text-white rounded-xl transition"
      >
        Try Again
      </button>
    </div>
  );
}