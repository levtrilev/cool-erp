// import { Check, Monitor, Moon, Sun } from "lucide-react";
// import { Button } from "@/components/ui/button";
// import {
//   DropdownMenu,
//   DropdownMenuContent,
//   DropdownMenuItem,
//   DropdownMenuLabel,
//   DropdownMenuSeparator,
//   DropdownMenuTrigger,
// } from "@/components/ui/dropdown-menu";
// import { useTheme } from "@/components/hooks/useTheme";
// import { LIGHT_PALETTES, DARK_PALETTES } from "@/components/theme/theme-context";

// export const ThemeToggle = () => {
//   const {
//     theme,
//     resolvedTheme,
//     lightPalette,
//     darkPalette,
//     setTheme,
//     setLightPalette,
//     setDarkPalette,
//   } = useTheme();

//   return (
//     <DropdownMenu>
//       <DropdownMenuTrigger asChild>
//         <Button variant="ghost" size="icon" title="Тема оформления">
//           {resolvedTheme === "dark" ? (
//             <Moon className="h-4 w-4" />
//           ) : (
//             <Sun className="h-4 w-4" />
//           )}
//         </Button>
//       </DropdownMenuTrigger>
//       <DropdownMenuContent align="end" className="w-64">
//         {/* Режимы */}
//         <DropdownMenuItem onClick={() => setTheme("light")}>
//           <Sun className="mr-2 h-4 w-4" />
//           Светлая
//           {theme === "light" && (
//             <Check className="ml-auto h-4 w-4 text-primary" />
//           )}
//         </DropdownMenuItem>
//         <DropdownMenuItem onClick={() => setTheme("dark")}>
//           <Moon className="mr-2 h-4 w-4" />
//           Тёмная
//           {theme === "dark" && (
//             <Check className="ml-auto h-4 w-4 text-primary" />
//           )}
//         </DropdownMenuItem>
//         <DropdownMenuItem onClick={() => setTheme("system")}>
//           <Monitor className="mr-2 h-4 w-4" />
//           Как в системе
//           {theme === "system" && (
//             <Check className="ml-auto h-4 w-4 text-primary" />
//           )}
//         </DropdownMenuItem>

//         {/* Светлые палитры */}
//         <DropdownMenuSeparator />
//         <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">
//           Светлая тема — палитра
//         </DropdownMenuLabel>
//         {LIGHT_PALETTES.map((p) => (
//           <DropdownMenuItem
//             key={p.id}
//             onClick={() => {
//               setTheme("light");
//               setLightPalette(p.id);
//             }}
//           >
//             <Sun className="mr-2 h-4 w-4" />
//             <span className="flex flex-col leading-tight">
//               <span>{p.label}</span>
//               <span className="text-xs text-muted-foreground">{p.hint}</span>
//             </span>
//             {lightPalette === p.id && (
//               <Check className="ml-auto h-4 w-4 text-primary" />
//             )}
//           </DropdownMenuItem>
//         ))}

//         {/* Тёмные палитры */}
//         <DropdownMenuSeparator />
//         <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">
//           Тёмная тема — палитра
//         </DropdownMenuLabel>
//         {DARK_PALETTES.map((p) => (
//           <DropdownMenuItem
//             key={p.id}
//             onClick={() => {
//               setTheme("dark");
//               setDarkPalette(p.id);
//             }}
//           >
//             <Moon className="mr-2 h-4 w-4" />
//             <span className="flex flex-col leading-tight">
//               <span>{p.label}</span>
//               <span className="text-xs text-muted-foreground">{p.hint}</span>
//             </span>
//             {darkPalette === p.id && (
//               <Check className="ml-auto h-4 w-4 text-primary" />
//             )}
//           </DropdownMenuItem>
//         ))}
//       </DropdownMenuContent>
//     </DropdownMenu>
//   );
// };