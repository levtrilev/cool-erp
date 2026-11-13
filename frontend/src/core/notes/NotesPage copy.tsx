// import { useState, useEffect, useCallback, useMemo } from "react";
// import { useQueryClient } from "@tanstack/react-query";
// import {
//   Plus,
//   Trash2,
//   Search,
//   Loader2,
//   Lock,
//   Copy,
//   ChevronLeft,
//   ChevronRight,
//   ChevronsLeft,
//   ChevronsRight,
// } from "lucide-react";
// import { Button } from "@/components/ui/button";
// import { Input } from "@/components/ui/input";
// import {
//   Table,
//   TableBody,
//   TableCell,
//   TableHead,
//   TableHeader,
//   TableRow,
// } from "@/components/ui/table";
// import {
//   AlertDialog,
//   AlertDialogAction,
//   AlertDialogCancel,
//   AlertDialogContent,
//   AlertDialogDescription,
//   AlertDialogFooter,
//   AlertDialogHeader,
//   AlertDialogTitle,
// } from "@/components/ui/alert-dialog";
// import { Badge } from "@/components/ui/badge";
// import { useToast } from "@/components/ui/use-toast";
// import {
//   useGetNotesNotesGet,
//   useDeleteNoteNotesNoteIdDelete,
//   getNotesNotesGet,
//   useAcquireNoteLockNotesNoteIdLockPost,
//   useReleaseNoteLockNotesNoteIdLockDelete,
// } from "@/api/generated/notes/notes";
// import { NoteResponseSchema, NoteSortField, SortOrder } from "@/api/generated/coolERP.schemas";

// // import { EditNoteModal } from "./EditNoteModal";
// import { EditNoteModal } from "./EditNoteModalLite";
// import { useResizableColumns } from "@/components/hooks/useResizableColumns";
// import { DOC_STATUS_LABELS } from "./schemas";
// import {
//   ColumnHeaderMenu,
//   type ColumnDef,
//   type ColumnState,
//   type ColumnStates,
// } from "./ColumnHeaderMenu";

// // ✅ Типобезопасная карта: id колонки меню → enum-значение query-параметра.
// // Исключает касты: ключи ограничены перечислением колонок.
// const SORT_FIELD_BY_COLUMN: Record<string, NoteSortField> = {
//   title: NoteSortField.title,
//   doc_number: NoteSortField.doc_number,
//   doc_date: NoteSortField.doc_date,
//   doc_status: NoteSortField.doc_status,
//   section_name: NoteSortField.section_name,
//   updated_at: NoteSortField.updated_at,
// };

// // ============================================================
// // КОНФИГУРАЦИЯ КОЛОНОК МЕНЮ (сортировка/фильтрация на сервере)
// // ============================================================
// const SORT_FILTER_COLUMNS: ColumnDef[] = [
//   { id: NoteSortField.title, label: "Название", type: "string" },
//   { id: NoteSortField.doc_number, label: "Номер", type: "string" },
//   { id: NoteSortField.doc_date, label: "Дата", type: "date" },
//   {
//     id: NoteSortField.doc_status,
//     label: "Статус",
//     type: "select",
//     options: Object.entries(DOC_STATUS_LABELS).map(([value, label]) => ({
//       value,
//       label,
//     })),
//   },
//   { id: NoteSortField.section_name, label: "Раздел", type: "string" },
//   { id: NoteSortField.updated_at, label: "Обновлено", type: "date" },
// ];

// const COLUMNS = [
//   { id: "title", initialWidth: 250, minWidth: 150 },
//   { id: "doc_number", initialWidth: 120, minWidth: 80 },
//   { id: "doc_date", initialWidth: 120, minWidth: 80 },
//   { id: "doc_status", initialWidth: 130, minWidth: 100 },
//   { id: "section_name", initialWidth: 150, minWidth: 100 },
//   { id: "updated_at", initialWidth: 160, minWidth: 120 },
//   { id: "actions", initialWidth: 100, minWidth: 80 },
// ];

// const buildInitialColumnStates = (): ColumnStates =>
//   Object.fromEntries(
//     SORT_FILTER_COLUMNS.map((c) => [c.id, { sort: null, filter: null }]),
//   );

// export const NotesPage = () => {
//   const { toast } = useToast();
//   const queryClient = useQueryClient();
//   const [page, setPage] = useState(1);
//   const [limit] = useState(15);
//   const [searchInput, setSearchInput] = useState("");
//   const [search, setSearch] = useState("");
//   const [isModalOpen, setIsModalOpen] = useState(false);
//   const [editingNote, setEditingNote] = useState<NoteResponseSchema | null>(
//     null,
//   );
//   const [deleteNoteId, setDeleteNoteId] = useState<string | null>(null);
//   const [highlightedNoteId, setHighlightedNoteId] = useState<string | null>(
//     null,
//   );
//   const [readOnly, setReadOnly] = useState(false);
//   const [readOnlyReason, setReadOnlyReason] = useState<string>("");

//   // ✅ Копирование (по образцу AdminRolesPage)
//   const [copyingNote, setCopyingNote] = useState<NoteResponseSchema | null>(
//     null,
//   );
//   const [isCopyOpen, setIsCopyOpen] = useState(false);

//   // ✅ Состояния меню колонок (сортировка/фильтры уходят на сервер)
//   const [columnStates, setColumnStates] = useState<ColumnStates>(
//     buildInitialColumnStates,
//   );

//   const { widths, handleMouseDown, resetWidths } = useResizableColumns(
//     COLUMNS,
//     "notes-table-widths",
//   );

//   // ✅ Производные значения через useMemo (Правило №46)
//   const sortColumnId = useMemo(
//     () =>
//       Object.keys(columnStates).find((id) => columnStates[id].sort !== null) ??
//       null,
//     [columnStates],
//   );
//   const sortDirection = sortColumnId
//     ? columnStates[sortColumnId].sort
//     : null;

//   const strFilter = useCallback(
//     (columnId: string): string | undefined => {
//       const value = columnStates[columnId]?.filter;
//       return typeof value === "string" && value.length > 0
//         ? value
//         : undefined;
//     },
//     [columnStates],
//   );

//   const hasActiveFiltersOrSort = useMemo(
//     () =>
//       sortColumnId !== null ||
//       Object.values(columnStates).some(
//         (s) => s.filter !== null && s.filter !== "",
//       ),
//     [columnStates, sortColumnId],
//   );

//   // ✅ Все параметры сортировки/фильтрации уходят на сервер
//   const { data, isLoading, refetch } = useGetNotesNotesGet({
//     skip: (page - 1) * limit,
//     limit,
//     search: search || undefined,
//     // ✅ Enum-значения вместо строковых литералов
//     sort_by: sortColumnId ? SORT_FIELD_BY_COLUMN[sortColumnId] : undefined,
//     sort_order: sortColumnId
//       ? sortDirection === "desc"
//         ? SortOrder.desc
//         : SortOrder.asc
//       : undefined,
//     filter_title: strFilter("title"),
//     filter_doc_number: strFilter("doc_number"),
//     filter_doc_date: strFilter("doc_date"),
//     filter_doc_status: strFilter("doc_status"),
//     filter_section_name: strFilter("section_name"),
//     filter_updated_at: strFilter("updated_at"),
//   });
//   const deleteMutation = useDeleteNoteNotesNoteIdDelete();
//   const acquireLockMutation = useAcquireNoteLockNotesNoteIdLockPost();
//   const releaseLockMutation = useReleaseNoteLockNotesNoteIdLockDelete();

//   const items = data?.data?.items ?? [];
//   const total = data?.data?.total ?? 0;
//   const totalPages = Math.max(1, Math.ceil(total / limit));

//   // ✅ Обработчик меню колонки: одна сортировка на таблицу + сброс страницы
//   const handleColumnChange = useCallback(
//     (columnId: string, patch: Partial<ColumnState>) => {
//       setColumnStates((prev) => {
//         const next: ColumnStates = {
//           ...prev,
//           [columnId]: { ...prev[columnId], ...patch },
//         };
//         if (patch.sort !== undefined && patch.sort !== null) {
//           // Сортировка только по одной колонке одновременно
//           for (const key of Object.keys(next)) {
//             if (key !== columnId) {
//               next[key] = { ...next[key], sort: null };
//             }
//           }
//         }
//         return next;
//       });
//       setPage(1);
//     },
//     [],
//   );

//   const resetFiltersAndSort = useCallback(() => {
//     setColumnStates(buildInitialColumnStates());
//     setPage(1);
//   }, []);

//   // ============================================================
//   // ОБРАБОТЧИКИ (сохранение, удаление, блокировки, копирование)
//   // ============================================================
//   const handleSaved = useCallback(
//     async (id: string, title?: string) => {
//       await queryClient.invalidateQueries({ queryKey: ["notes"] });
//       await refetch();
//       const currentItems = data?.data?.items ?? [];
//       if (currentItems.some((item) => item.id === id)) {
//         setHighlightedNoteId(id);
//         setTimeout(() => setHighlightedNoteId(null), 3000);
//         toast({ title: "Успешно сохранено" });
//       } else {
//         try {
//           const fullList = await getNotesNotesGet({
//             limit: 1000,
//             skip: 0,
//             search: search || undefined,
//           });
//           const foundIndex = (fullList?.data?.items ?? []).findIndex(
//             (item) => item.id === id,
//           );
//           if (foundIndex !== -1) {
//             const targetPage = Math.ceil((foundIndex + 1) / limit);
//             setPage(targetPage);
//             setHighlightedNoteId(id);
//             setTimeout(() => setHighlightedNoteId(null), 3000);
//             toast({
//               title: "Сохранено",
//               description: `Запись «${title ?? ""}» на странице ${targetPage}`,
//             });
//           }
//         } catch (error: unknown) {
//           const err = error as { response?: { data?: { detail?: string } } };
//           toast({
//             variant: "destructive",
//             title: "Ошибка навигации",
//             description:
//               err?.response?.data?.detail || "Не удалось найти запись",
//           });
//         }
//       }
//     },
//     [data, limit, search, toast, refetch, queryClient],
//   );

//   const handleDelete = async () => {
//     if (!deleteNoteId) return;
//     try {
//       await deleteMutation.mutateAsync({ noteId: deleteNoteId });
//       await refetch();
//       setDeleteNoteId(null);
//       toast({ title: "Заметка удалена" });
//     } catch (error: unknown) {
//       const err = error as { response?: { data?: { detail?: string } } };
//       toast({
//         variant: "destructive",
//         title: "Ошибка удаления",
//         description: err?.response?.data?.detail || "Не удалось удалить",
//       });
//     }
//   };

//   const openEdit = async (item: NoteResponseSchema) => {
//     setEditingNote(item);
//     if (item.is_editing_locked) {
//       setReadOnly(true);
//       setReadOnlyReason(
//         "Документ редактируется другим пользователем. Вы можете только просматривать данные.",
//       );
//       setIsModalOpen(true);
//       return;
//     }
//     try {
//       await acquireLockMutation.mutateAsync({ noteId: item.id });
//       setReadOnly(false);
//       setReadOnlyReason("");
//       setIsModalOpen(true);
//     } catch (error: unknown) {
//       const err = error as {
//         response?: { status?: number; data?: { detail?: string } };
//       };
//       const status = err?.response?.status;
//       if (status === 403) {
//         setReadOnly(true);
//         setReadOnlyReason(
//           "У вас нет прав на изменение этого документа. Доступен только просмотр.",
//         );
//         setIsModalOpen(true);
//       } else if (status === 423) {
//         setReadOnly(true);
//         setReadOnlyReason(
//           "Документ редактируется другим пользователем. Открыт в режиме только для чтения.",
//         );
//         setIsModalOpen(true);
//         toast({
//           variant: "destructive",
//           title: "Документ занят",
//           description: "Документ редактируется другим пользователем.",
//         });
//       } else {
//         toast({
//           variant: "destructive",
//           title: "Ошибка блокировки",
//           description:
//             err?.response?.data?.detail || "Не удалось открыть документ",
//         });
//       }
//     }
//   };

//   const openCopy = (item: NoteResponseSchema) => {
//     setCopyingNote(item);
//     setIsCopyOpen(true);
//   };

//   const handleCopyModalOpenChange = (open: boolean) => {
//     setIsCopyOpen(open);
//     if (!open) {
//       setCopyingNote(null);
//     }
//   };

//   const handleModalClose = async (open: boolean) => {
//     if (!open && editingNote && !readOnly) {
//       try {
//         await releaseLockMutation.mutateAsync({ noteId: editingNote.id });
//       } catch {
//         // Игнорируем ошибки освобождения (таймаут всё равно снимет)
//       }
//     }
//     setIsModalOpen(open);
//     if (!open) {
//       setEditingNote(null);
//       setReadOnly(false);
//       setReadOnlyReason("");
//     }
//   };

//   useEffect(() => {
//     if (
//       highlightedNoteId &&
//       data?.data?.items?.some((i) => i.id === highlightedNoteId)
//     ) {
//       const timer = setTimeout(() => setHighlightedNoteId(null), 3000);
//       return () => clearTimeout(timer);
//     }
//   }, [data, highlightedNoteId]);

//   const openCreate = () => {
//     setEditingNote(null);
//     setReadOnly(false);
//     setIsModalOpen(true);
//   };

//   const formatDate = (iso: string | null | undefined): string => {
//     if (!iso) return "—";
//     return new Date(iso).toLocaleString("ru-RU", {
//       year: "numeric",
//       month: "2-digit",
//       day: "2-digit",
//       hour: "2-digit",
//       minute: "2-digit",
//     });
//   };

//   const formatDocDate = (iso: string | null | undefined): string => {
//     if (!iso) return "—";
//     return new Date(iso).toLocaleDateString("ru-RU");
//   };

//   // ✅ Рендер заголовка колонки с меню сортировки/фильтра
//   const renderSortableHeader = (columnId: string) => {
//     const col = SORT_FILTER_COLUMNS.find((c) => c.id === columnId);
//     if (!col) return null;
//     return (
//       <TableHead
//         style={{ width: widths[columnId as keyof typeof widths] }}
//         className="relative"
//       >
//         <ColumnHeaderMenu
//           column={col}
//           state={columnStates[columnId]}
//           onChange={handleColumnChange}
//         />
//         <div
//           className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
//           onMouseDown={(e) => handleMouseDown(columnId, e)}
//         />
//       </TableHead>
//     );
//   };

//   return (
//     <div className="p-6 space-y-4">
//       <div className="flex items-center justify-between">
//         <div>
//           <h1 className="text-2xl font-bold">Заметки</h1>
//           <p className="text-xs text-muted-foreground mt-0.5">
//             Всего: {total}
//           </p>
//         </div>
//         <div className="flex gap-2">
//           <Button variant="outline" size="sm" onClick={resetWidths}>
//             Сбросить ширину
//           </Button>
//           <Button
//             variant="outline"
//             size="sm"
//             onClick={resetFiltersAndSort}
//             disabled={!hasActiveFiltersOrSort}
//           >
//             Сбросить фильтры/сортировку
//           </Button>
//           <Button onClick={openCreate}>
//             <Plus className="h-4 w-4 mr-2" />
//             Создать заметку
//           </Button>
//         </div>
//       </div>

//       <form
//         onSubmit={(e) => {
//           e.preventDefault();
//           setSearch(searchInput);
//           setPage(1);
//         }}
//         className="flex gap-2"
//       >
//         <Input
//           value={searchInput}
//           onChange={(e) => setSearchInput(e.target.value)}
//           placeholder="Поиск по названию и содержимому..."
//           className="max-w-md"
//         />
//         <Button type="submit">
//           <Search className="h-4 w-4 mr-2" />
//           Найти
//         </Button>
//       </form>

//       {isLoading ? (
//         <div className="flex items-center justify-center h-40">
//           <Loader2 className="h-6 w-6 animate-spin" />
//         </div>
//       ) : (
//         <div className="rounded-md border overflow-auto max-h-[calc(100vh-260px)]">
//           <Table className="table-fixed w-full">
//             <TableHeader className="sticky top-0 bg-background z-10 shadow-sm">
//               <TableRow className="h-10 hover:bg-transparent">
//                 {renderSortableHeader("title")}
//                 {renderSortableHeader("doc_number")}
//                 {renderSortableHeader("doc_date")}
//                 {renderSortableHeader("doc_status")}
//                 {renderSortableHeader("section_name")}
//                 {renderSortableHeader("updated_at")}
//                 <TableHead
//                   style={{ width: widths.actions }}
//                   className="relative"
//                 >
//                   Действия
//                 </TableHead>
//               </TableRow>
//             </TableHeader>
//             <TableBody>
//               {items.length === 0 ? (
//                 <TableRow>
//                   <TableCell
//                     colSpan={7}
//                     className="text-center py-8 text-muted-foreground"
//                   >
//                     {hasActiveFiltersOrSort || search
//                       ? "Нет записей, соответствующих условиям"
//                       : "Заметки не найдены"}
//                   </TableCell>
//                 </TableRow>
//               ) : (
//                 items.map((item) => (
//                   <TableRow
//                     key={item.id}
//                     className={
//                       highlightedNoteId === item.id
//                         ? "bg-yellow-100 dark:bg-yellow-900/30 transition-colors duration-300"
//                         : ""
//                     }
//                   >
//                     <TableCell
//                       style={{ width: widths.title }}
//                       className="py-1 align-top overflow-hidden"
//                     >
//                       <button
//                         type="button"
//                         onClick={() => openEdit(item)}
//                         className="text-left text-link hover:text-link-hover hover:underline underline-offset-2 font-medium cursor-pointer w-full truncate block focus:outline-none focus:ring-2 focus:ring-link focus:ring-offset-1 rounded-sm transition-colors"
//                         title={item.title}
//                       >
//                         {item.is_editing_locked && (
//                           <Lock className="inline h-3 w-3 mr-1 text-amber-500" />
//                         )}
//                         {item.title}
//                       </button>
//                     </TableCell>
//                     <TableCell
//                       style={{ width: widths.doc_number }}
//                       className="py-1 align-top overflow-hidden"
//                     >
//                       <div className="truncate">{item.doc_number ?? "—"}</div>
//                     </TableCell>
//                     <TableCell
//                       style={{ width: widths.doc_date }}
//                       className="py-1 align-top"
//                     >
//                       {formatDocDate(item.doc_date)}
//                     </TableCell>
//                     <TableCell
//                       style={{ width: widths.doc_status }}
//                       className="py-1 align-top"
//                     >
//                       <Badge variant="secondary">
//                         {DOC_STATUS_LABELS[item.doc_status] ?? item.doc_status}
//                       </Badge>
//                     </TableCell>
//                     <TableCell
//                       style={{ width: widths.section_name }}
//                       className="py-1 align-top overflow-hidden"
//                     >
//                       <div className="truncate">
//                         {(
//                           item as NoteResponseSchema & { section_name?: string }
//                         ).section_name ?? "—"}
//                       </div>
//                     </TableCell>
//                     <TableCell
//                       style={{ width: widths.updated_at }}
//                       className="py-1 align-top text-xs text-muted-foreground"
//                     >
//                       {formatDate(item.updated_at)}
//                     </TableCell>
//                     <TableCell
//                       style={{ width: widths.actions }}
//                       className="py-1 align-top"
//                     >
//                       <div className="flex gap-1">
//                         <Button
//                           variant="ghost"
//                           size="icon"
//                           className="h-7 w-7"
//                           onClick={() => openCopy(item)}
//                           title="Копировать"
//                         >
//                           <Copy className="h-4 w-4" />
//                         </Button>
//                         <Button
//                           variant="ghost"
//                           size="icon"
//                           className="h-7 w-7 text-destructive hover:text-destructive"
//                           onClick={() => setDeleteNoteId(item.id)}
//                           title="Удалить"
//                         >
//                           <Trash2 className="h-4 w-4" />
//                         </Button>
//                       </div>
//                     </TableCell>
//                   </TableRow>
//                 ))
//               )}
//             </TableBody>
//           </Table>
//         </div>
//       )}

//       {/* ✅ Пагинация по образцу AdminRolesPage (Правило №15) */}
//       {totalPages > 1 && (
//         <div className="flex items-center justify-center gap-1 mt-3">
//           <Button
//             size="sm"
//             variant="outline"
//             className="h-8 w-8 p-0"
//             disabled={page === 1}
//             onClick={() => setPage(1)}
//           >
//             <ChevronsLeft className="h-4 w-4" />
//           </Button>
//           <Button
//             size="sm"
//             variant="outline"
//             className="h-8 w-8 p-0"
//             disabled={page === 1}
//             onClick={() => setPage(page - 1)}
//           >
//             <ChevronLeft className="h-4 w-4" />
//           </Button>
//           {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
//             let pageNum = i + 1;
//             if (totalPages > 5 && page > 3) pageNum = page - 2 + i;
//             if (pageNum > totalPages) return null;
//             return (
//               <Button
//                 key={pageNum}
//                 size="sm"
//                 variant={page === pageNum ? "default" : "outline"}
//                 className="h-8 w-8 p-0"
//                 onClick={() => setPage(pageNum)}
//               >
//                 {pageNum}
//               </Button>
//             );
//           })}
//           <Button
//             size="sm"
//             variant="outline"
//             className="h-8 w-8 p-0"
//             disabled={page === totalPages}
//             onClick={() => setPage(page + 1)}
//           >
//             <ChevronRight className="h-4 w-4" />
//           </Button>
//           <Button
//             size="sm"
//             variant="outline"
//             className="h-8 w-8 p-0"
//             disabled={page === totalPages}
//             onClick={() => setPage(totalPages)}
//           >
//             <ChevronsRight className="h-4 w-4" />
//           </Button>
//         </div>
//       )}

//       <EditNoteModal
//         open={isModalOpen}
//         onOpenChange={handleModalClose}
//         initialData={editingNote}
//         onSaved={handleSaved}
//         readOnly={readOnly}
//         readOnlyReason={readOnlyReason}
//       />

//       {/* ✅ Модалка копирования (по образцу AdminRolesPage) */}
//       {isCopyOpen && copyingNote && (
//         <EditNoteModal
//           key={`copy-${copyingNote.id}`}
//           open={isCopyOpen}
//           onOpenChange={handleCopyModalOpenChange}
//           initialData={null}
//           copyFromNote={copyingNote}
//           onSaved={handleSaved}
//         />
//       )}

//       <AlertDialog
//         open={!!deleteNoteId}
//         onOpenChange={(open) => !open && setDeleteNoteId(null)}
//       >
//         <AlertDialogContent>
//           <AlertDialogHeader>
//             <AlertDialogTitle>Удалить заметку?</AlertDialogTitle>
//             <AlertDialogDescription>
//               Заметка будет помечена как удалённая (мягкое удаление). Запись
//               останется в БД для аудита, но перестанет отображаться в списках.
//             </AlertDialogDescription>
//           </AlertDialogHeader>
//           <AlertDialogFooter>
//             <AlertDialogCancel>Отмена</AlertDialogCancel>
//             <AlertDialogAction
//               onClick={handleDelete}
//               disabled={deleteMutation.isPending}
//               className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
//             >
//               {deleteMutation.isPending ? (
//                 <Loader2 className="animate-spin mr-2 h-4 w-4" />
//               ) : (
//                 <Trash2 className="mr-2 h-4 w-4" />
//               )}
//               Удалить
//             </AlertDialogAction>
//           </AlertDialogFooter>
//         </AlertDialogContent>
//       </AlertDialog>
//     </div>
//   );
// };