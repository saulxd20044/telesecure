import "./globals.css";

export const metadata = {
  title: "TeleSecure Dashboard",
  description: "Panel de control FreePBX",
};

export default function RootLayout({ children }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
