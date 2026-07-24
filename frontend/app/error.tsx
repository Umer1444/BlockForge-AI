"use client";

import { useEffect } from "react";
import { AlertCircle } from "lucide-react";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error("Global Error Boundary caught:", error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
      <div className="bg-red-500/10 p-4 rounded-full mb-6">
        <AlertCircle className="w-12 h-12 text-red-500" />
      </div>
      <h2 className="text-2xl font-bold mb-4 font-mono">Something went wrong!</h2>
      <p className="text-gray-400 mb-8 max-w-md">
        An unexpected error occurred while processing your request. Please try again or contact support if the issue persists.
      </p>
      <button
        onClick={() => reset()}
        className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
      >
        Try Again
      </button>
    </div>
  );
}
