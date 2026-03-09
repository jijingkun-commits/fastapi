import type { Metadata } from "next";
import "./globals.css";
import { Noto_Sans_SC } from "next/font/google";
import React from "react";

const notoSansSC = Noto_Sans_SC({
  weight: ["400", "500", "600", "700"],
  preload: false,
  display: "swap",
  fallback: ["PingFang SC", "Hiragino Sans GB", "Microsoft YaHei UI", "sans-serif"],
  variable: "--font-sans-cjk",
});

export const metadata: Metadata = {
  title: "嘉银助手",
  description: "嘉银助手智能对话界面",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="cn" suppressHydrationWarning>
      <body className={`${notoSansSC.variable} antialiased`} suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
