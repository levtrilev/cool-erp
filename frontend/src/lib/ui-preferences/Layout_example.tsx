// // frontend/src/app/layout.tsx (фрагмент интеграции)
// import { cookies } from "next/headers";
// import { UiPreferencesProvider } from "@/lib/ui-preferences/UiPreferencesProvider";
// import {
//   NAV_LAYOUT_COOKIE,
//   THEME_COOKIE,
// } from "@/lib/ui-preferences/browserAppearance";

// export default async function RootLayout({
//   children,
// }: {
//   children: React.ReactNode;
// }) {
//   const cookieStore = await cookies();
//   const theme = cookieStore.get(THEME_COOKIE)?.value === "dark" ? "dark" : "light";
//   const navLayout =
//     cookieStore.get(NAV_LAYOUT_COOKIE)?.value === "topbar" ? "topbar" : "sidebar";

//   return (
//     <html
//       lang="ru"
//       className={theme}
//       data-nav-layout={navLayout}
//       suppressHydrationWarning
//     >
//       <body>
//         {/* Существующий QueryClientProvider остаётся обёрткой */}
//         <UiPreferencesProvider>{children}</UiPreferencesProvider>
//       </body>
//     </html>
//   );
// }