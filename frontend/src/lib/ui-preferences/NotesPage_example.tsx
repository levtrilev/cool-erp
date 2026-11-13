// // frontend/src/core/notes/NotesPage.tsx (фрагменты замены)
// import { useTablePreferences } from "@/lib/ui-preferences/useTablePreferences";
// import type {
//   TableColumnStateSchema,
//   TablePreferenceSchema,
// } from "@/api/generated/coolERP.schemas";

// // Было: useGetUserAuthUserGet + userId + localStorage-хук — удалены.
// // Сервер сам определяет пользователя по сессии.

// const toStoredNotes = (state: NotesTableViewState): TablePreferenceSchema => ({
//   column_states: Object.fromEntries(
//     Object.entries(state.columnStates).map(([key, value]) => [
//       key,
//       { sort: value.sort, filter: value.filter },
//     ]),
//   ),
//   search: state.search,
//   page: state.page,
//   page_size: 15,
// });

// const fromStoredNotes = (
//   stored: TablePreferenceSchema | undefined,
//   defaults: NotesTableViewState,
// ): NotesTableViewState => {
//   if (stored === undefined) return defaults;
//   const columnStates = buildInitialColumnStates();
//   for (const column of SORT_FILTER_COLUMNS) {
//     const raw: TableColumnStateSchema | undefined =
//       stored.column_states[column.id];
//     if (raw) {
//       columnStates[column.id] = { sort: raw.sort, filter: raw.filter };
//     }
//   }
//   return {
//     columnStates,
//     search: stored.search,
//     searchInput: stored.search,
//     page: stored.page,
//   };
// };

// // Внутри компонента:
// const {
//   state: viewState,
//   setState: setViewState,
//   isRestored,
// } = useTablePreferences<NotesTableViewState>({
//   tableKey: "notes",
//   defaultState: NOTES_TABLE_DEFAULT_STATE,
//   toStored: toStoredNotes,
//   fromStored: fromStoredNotes,
// });