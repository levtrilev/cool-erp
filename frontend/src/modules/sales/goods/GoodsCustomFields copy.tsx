// // frontend/src/modules/sales/goods/GoodsCustomFields.tsx (новый файл)
// import { useCallback } from "react";
// import type { Control, FieldErrors, UseFormSetValue } from "react-hook-form";
// import { Controller } from "react-hook-form";
// import { Input } from "@/components/ui/input";
// import { Label } from "@/components/ui/label";
// import { Textarea } from "@/components/ui/textarea";
// import { ReferenceSelect } from "@/lib/reusable/ReferenceSelect";
// import { getSectionsSectionsGet } from "@/api/generated/sections/sections";
// import {
//   getSalesItemTypesSalesItemTypesGet,
//   getSalesItemTypeSalesItemTypesItemTypeIdGet,
// } from "@/api/generated/sales-item-types/sales-item-types";
// import type { GoodFormData } from "./schemas";

// interface GoodsCustomFieldsProps {
//   control: Control<GoodFormData>;
//   errors: FieldErrors<GoodFormData>;
//   readOnly: boolean;
//   /** Запись в форму из бизнес-логики (автозаполнение base_uom). */
//   setValue: UseFormSetValue<GoodFormData>;
//   /** Денормализованные имена для selectedLabel (Правила №27, №42). */
//   sectionName?: string;
//   itemTypeName?: string;
// }

// /** Бизнес-поля вкладки «Основное» карточки товара. */
// export const GoodsCustomFields = ({
//   control,
//   errors,
//   readOnly,
//   setValue,
//   sectionName,
//   itemTypeName,
// }: GoodsCustomFieldsProps) => {
//   // ✅ P2: base_uom заполняется из выбранного типа номенклатуры
//   const syncBaseUom = useCallback(
//     (itemTypeId: string): void => {
//       if (!itemTypeId) {
//         setValue("base_uom", "");
//         return;
//       }
//       void (async () => {
//         try {
//           const response = await getSalesItemTypeSalesItemTypesItemTypeIdGet(itemTypeId);
//           setValue("base_uom", response?.data?.base_uom ?? "");
//         } catch {
//           // Тип недоступен — base_uom остаётся прежним
//         }
//       })();
//     },
//     [setValue],
//   );

//   return (
//     <div className="space-y-4">
//       <div className="grid grid-cols-2 gap-4">
//         <div className="space-y-2">
//           <Label htmlFor="good-name">
//             Название <span className="text-destructive">*</span>
//           </Label>
//           <Controller
//             name="name"
//             control={control}
//             render={({ field }) => (
//               <Input
//                 id="good-name"
//                 {...field}
//                 placeholder="Например: Ноутбук Dell XPS 15"
//                 maxLength={255}
//                 disabled={readOnly}
//               />
//             )}
//           />
//           {errors.name && (
//             <p className="text-xs text-destructive">{errors.name.message}</p>
//           )}
//         </div>

//         {/* ✅ P1: раздел обязателен и виден на «Основное» */}
//         <div className="space-y-2">
//           <Label>
//             Раздел <span className="text-destructive">*</span>
//           </Label>
//           <Controller
//             name="section_id"
//             control={control}
//             render={({ field }) => (
//               <ReferenceSelect
//                 fetchFn={async (params) => {
//                   const response = await getSectionsSectionsGet({
//                     skip: params.skip,
//                     limit: params.limit,
//                     search: params.search,
//                   });
//                   const items = (response?.data?.items ?? []).map((item) => ({
//                     id: item.id,
//                     name: item.name,
//                   }));
//                   return { items, total: response?.data?.total ?? 0 };
//                 }}
//                 queryKey={["sections", "active"]}
//                 value={field.value}
//                 onValueChange={field.onChange}
//                 placeholder="Выберите раздел..."
//                 selectedLabel={sectionName ?? "Выберите раздел..."}
//                 heading="Разделы"
//                 limit={50}
//                 disabled={readOnly}
//               />
//             )}
//           />
//           {errors.section_id && (
//             <p className="text-xs text-destructive">
//               {errors.section_id.message}
//             </p>
//           )}
//         </div>
//       </div>

//       <div className="space-y-2">
//         <Label htmlFor="good-description">Описание</Label>
//         <Controller
//           name="description"
//           control={control}
//           render={({ field }) => (
//             <Textarea
//               id="good-description"
//               {...field}
//               value={field.value ?? ""}
//               placeholder="Описание товара..."
//               rows={3}
//               disabled={readOnly}
//             />
//           )}
//         />
//         {errors.description && (
//           <p className="text-xs text-destructive">{errors.description.message}</p>
//         )}
//       </div>

//       <div className="grid grid-cols-2 gap-4">
//         <div className="space-y-2">
//           <Label>Тип номенклатуры</Label>
//           <Controller
//             name="item_type_id"
//             control={control}
//             render={({ field }) => (
//               <ReferenceSelect
//                 fetchFn={async (params) => {
//                   const response = await getSalesItemTypesSalesItemTypesGet({
//                     skip: params.skip,
//                     limit: params.limit,
//                     search: params.search,
//                   });
//                   const items = (response?.data?.items ?? []).map((item) => ({
//                     id: item.id,
//                     name: item.name,
//                   }));
//                   return { items, total: response?.data?.total ?? 0 };
//                 }}
//                 queryKey={["sales-item-types"]}
//                 value={field.value ?? ""}
//                 onValueChange={(value) => {
//                   field.onChange(value);
//                   syncBaseUom(value);
//                 }}
//                 placeholder="Выберите тип номенклатуры..."
//                 selectedLabel={itemTypeName ?? "Выберите тип номенклатуры..."}
//                 heading="Типы номенклатуры"
//                 limit={50}
//                 disabled={readOnly}
//               />
//             )}
//           />
//         </div>

//         <div className="space-y-2">
//           <Label htmlFor="good-base-uom">Единица измерения основная</Label>
//           <Controller
//             name="base_uom"
//             control={control}
//             render={({ field }) => (
//               <Input
//                 id="good-base-uom"
//                 {...field}
//                 value={field.value ?? ""}
//                 placeholder="—"
//                 maxLength={64}
//                 // ✅ P2: поле только для чтения, заполняется из типа
//                 disabled
//               />
//             )}
//           />
//           <p className="text-xs text-muted-foreground">
//             Заполняется автоматически из выбранного типа номенклатуры
//           </p>
//         </div>
//       </div>
//     </div>
//   );
// };