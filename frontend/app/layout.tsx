import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BlockForge AI – Video Watermark Removal Studio",
  description:
    "GPU-accelerated AI video processing studio. Remove watermarks, objects, and enhance video quality with state-of-the-art inpainting models.",
  keywords: ["video processing", "AI", "watermark removal", "inpainting", "GPU"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="mc-bg-stone min-h-screen antialiased">{children}</body>
    </html>
  );
}
