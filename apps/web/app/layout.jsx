import "./globals.css";

export const metadata = {
  title: "HuntFlow vNext",
  description: "Dual-track headhunter agent workbench"
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

