import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "JKN-Sentinel",
  description: "Setiap klaim harus mungkin terjadi dan wajar tagihannya",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="id" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
