// // ============================================================================
// // Модуль регионов: когда будет реализован эндпоинт GET /regions,
// // установить REGIONS_AVAILABLE = true и заменить заглушку fetchFn на реальный вызов.
// // Денормализация региона: после реализации модуля регионов добавить region_name
// // в BpCompanyResponseSchema на бэкенде (Правило №42) — тогда selectedLabel будет
// // отображать имя региона при редактировании.
// // ============================================================================

// import { useEffect, useMemo } from "react";
// import {
//   useForm,
//   Controller,
//   useWatch,
//   type FieldErrors,
// } from "react-hook-form";
// import { zodResolver } from "@hookform/resolvers/zod";
// import { z } from "zod";
// import { useQueryClient } from "@tanstack/react-query";
// import {
//   Loader2,
//   Check,
//   AlertCircle,
//   CheckCircle2,
//   PauseCircle,
// } from "lucide-react";
// import { useToast } from "@/components/ui/use-toast";
// import { Button } from "@/components/ui/button";
// import { Input } from "@/components/ui/input";
// import { Textarea } from "@/components/ui/textarea";
// import { Switch } from "@/components/ui/switch";
// import { Label } from "@/components/ui/label";
// import {
//   Dialog,
//   DialogContent,
//   DialogHeader,
//   DialogTitle,
//   DialogFooter,
// } from "@/components/ui/dialog";
// import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
// import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

// // ✅ Orval-хуки (Правило №9). Имена зависят от orval.config.ts —
// // после npm run generate:api сверьте фактические имена.
// import {
//   useCreateCompanyBusinessPartnersCompaniesPost,
//   useUpdateCompanyBusinessPartnersCompaniesCompanyIdPut,
// } from "@/api/generated/business-partners-companies/business-partners-companies";
// import { getSectionsSectionsGet } from "@/api/generated/sections/sections";
// import { useGetUserAuthUserGet } from "@/api/generated/authentication/authentication";
// import type { BpCompanyResponseSchema } from "@/api/generated/fastAPI.schemas";
// import {
//   ReferenceSelect,
//   type ReferenceItem,
// } from "@/lib/reusable/ReferenceSelect";

// // ⚠️ Зависимость от модуля регионов (см. спецификацию: data_sources.regions).
// // Если эндпоинт GET /regions ещё не реализован — установите false,
// // и поле «Регион» не будет рендериться (fallback_if_absent из спецификации).
// // НЕ заменяйте поле текстовым вводом.
// const REGIONS_AVAILABLE: boolean = false;

// // ✅ Правило №41: Zod-схема валидации
// const companyFormSchema = z.object({
//   // Вкладка «Реквизиты»
//   name: z.string().min(1, "Наименование обязательно"),
//   fullname: z.string().optional(),
//   inn: z
//     .string()
//     .refine((val) => val === "" || /^\d{10}$/.test(val), {
//       message: "ИНН юридического лица — 10 цифр",
//     })
//     .optional(),
//   kpp: z
//     .string()
//     .refine((val) => val === "" || /^\d{9}$/.test(val), {
//       message: "КПП — 9 цифр",
//     })
//     .optional(),
//   region_id: z.string().optional(),
//   is_customer: z.boolean().optional(),
//   is_supplier: z.boolean().optional(),
//   // Вкладка «Адреса и контакты»
//   address_legal: z.string().optional(),
//   address_fact: z.string().optional(),
//   phone: z.string().optional(),
//   email: z
//     .string()
//     .refine((val) => val === "" || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val), {
//       message: "Некорректный email",
//     })
//     .optional(),
//   contact: z.string().optional(),
//   // Вкладка «Документ» (контракт документа)
//   section_id: z.string().min(1, "Выберите раздел"),
//   doc_number: z.string().max(64, "Не более 64 символов").optional(),
//   doc_date: z.string().optional(),
// });

// type CompanyFormData = z.infer<typeof companyFormSchema>;

// // ✅ Правило №20: Константа для сброса формы
// const CREATE_DEFAULTS: CompanyFormData = {
//   name: "",
//   fullname: "",
//   inn: "",
//   kpp: "",
//   region_id: "",
//   is_customer: false,
//   is_supplier: false,
//   address_legal: "",
//   address_fact: "",
//   phone: "",
//   email: "",
//   contact: "",
//   section_id: "",
//   doc_number: "",
//   doc_date: "",
// };

// interface EditCompanyModalProps {
//   open: boolean;
//   onOpenChange: (open: boolean) => void;
//   initialData: BpCompanyResponseSchema | null;
//   onSaved: (id: string, name: string) => Promise<void>;
//   /** ✅ Правило №39: режим только для чтения при блокировке */
//   readOnly?: boolean;
// }

// export function EditCompanyModal({
//   open,
//   onOpenChange,
//   initialData,
//   onSaved,
//   readOnly = false,
// }: EditCompanyModalProps) {
//   const queryClient = useQueryClient();
//   const { toast } = useToast();
//   const { data: userData } = useGetUserAuthUserGet();
//   const currentTenantId = userData?.data?.tenant_id;
//   const currentTenantName = userData?.data?.tenant_name;

//   const isEdit = !!initialData;

//   const {
//     control,
//     handleSubmit,
//     reset,
//     formState: { errors, isSubmitting },
//   } = useForm<CompanyFormData>({
//     resolver: zodResolver(companyFormSchema),
//     defaultValues: CREATE_DEFAULTS,
//   });

//   const createMutation = useCreateCompanyBusinessPartnersCompaniesPost();
//   const updateMutation =
//     useUpdateCompanyBusinessPartnersCompaniesCompanyIdPut();

//   // ✅ Правило №37: Синхронизация формы при открытии
//   useEffect(() => {
//     if (open) {
//       if (initialData) {
//         reset({
//           name: initialData.name,
//           fullname: initialData.fullname || "",
//           inn: initialData.inn || "",
//           kpp: initialData.kpp || "",
//           region_id: initialData.region_id || "",
//           is_customer: initialData.is_customer ?? false,
//           is_supplier: initialData.is_supplier ?? false,
//           address_legal: initialData.address_legal || "",
//           address_fact: initialData.address_fact || "",
//           phone: initialData.phone || "",
//           email: initialData.email || "",
//           contact: initialData.contact || "",
//           section_id: initialData.section_id,
//           doc_number: initialData.doc_number || "",
//           // ✅ Дата в формате YYYY-MM-DD для Input type="date"
//           doc_date: initialData.doc_date
//             ? new Date(initialData.doc_date).toISOString().split("T")[0]
//             : "",
//         });
//       } else {
//         reset(CREATE_DEFAULTS);
//       }
//     }
//   }, [open, initialData, reset]);

//   // ✅ Правило №20: при закрытии сброс формы
//   const handleOpenChange = (newOpen: boolean) => {
//     if (!newOpen) {
//       reset(CREATE_DEFAULTS);
//     }
//     onOpenChange(newOpen);
//   };

//   // ==========================================
//   // ИНДИКАТОРЫ ИЗМЕНЕНИЙ (спецификация: change_indicators)
//   // Поимённое сравнение с исходной карточкой (режим: field_by_field)
//   // ==========================================
//   const watchedValues = useWatch({ control });

//   const hasBasicsChanges = useMemo(() => {
//     if (!initialData) return isEdit ? false : true;
//     return (
//       (watchedValues.name || "") !== (initialData.name || "") ||
//       (watchedValues.fullname || "") !== (initialData.fullname || "") ||
//       (watchedValues.inn || "") !== (initialData.inn || "") ||
//       (watchedValues.kpp || "") !== (initialData.kpp || "") ||
//       (watchedValues.region_id || "") !== (initialData.region_id || "") ||
//       (watchedValues.is_customer ?? false) !==
//         (initialData.is_customer ?? false) ||
//       (watchedValues.is_supplier ?? false) !==
//         (initialData.is_supplier ?? false)
//     );
//   }, [watchedValues, initialData, isEdit]);

//   const hasContactsChanges = useMemo(() => {
//     if (!initialData) return isEdit ? false : true;
//     return (
//       (watchedValues.address_legal || "") !==
//         (initialData.address_legal || "") ||
//       (watchedValues.address_fact || "") !== (initialData.address_fact || "") ||
//       (watchedValues.phone || "") !== (initialData.phone || "") ||
//       (watchedValues.email || "") !== (initialData.email || "") ||
//       (watchedValues.contact || "") !== (initialData.contact || "")
//     );
//   }, [watchedValues, initialData, isEdit]);

//   const hasDocumentChanges = useMemo(() => {
//     if (!initialData) return isEdit ? false : true;
//     const initialDocDate = initialData.doc_date
//       ? new Date(initialData.doc_date).toISOString().split("T")[0]
//       : "";
//     return (
//       (watchedValues.section_id || "") !== (initialData.section_id || "") ||
//       (watchedValues.doc_number || "") !== (initialData.doc_number || "") ||
//       (watchedValues.doc_date || "") !== initialDocDate
//     );
//   }, [watchedValues, initialData, isEdit]);

//   // ✅ Спецификация: has_any_changes.formula = "basics or contacts or document"
//   const hasAnyChanges: boolean =
//     hasBasicsChanges || hasContactsChanges || hasDocumentChanges;

//   // ==========================================
//   // СОХРАНЕНИЕ (спецификация: events + payload)
//   // ==========================================
//   const onSubmit = async (data: CompanyFormData) => {
//     // ✅ Правило №39: защита от сохранения в режиме только чтения
//     if (readOnly) return;

//     if (!currentTenantId) {
//       toast({
//         variant: "destructive",
//         title: "Ошибка",
//         description: "Не определена текущая организация",
//       });
//       return;
//     }

//     try {
//       if (isEdit && initialData) {
//         // ✅ Обновление с оптимистической блокировкой (Бэкенд Правило №40)
//         await updateMutation.mutateAsync({
//           companyId: initialData.id,
//           data: {
//             name: data.name,
//             fullname: data.fullname || null,
//             inn: data.inn || null,
//             kpp: data.kpp || null,
//             region_id: data.region_id || null,
//             is_customer: data.is_customer ?? false,
//             is_supplier: data.is_supplier ?? false,
//             address_legal: data.address_legal || null,
//             address_fact: data.address_fact || null,
//             phone: data.phone || null,
//             email: data.email || null,
//             contact: data.contact || null,
//             section_id: data.section_id,
//             doc_number: data.doc_number || null,
//             doc_date: data.doc_date || null,
//             // ✅ Обязательная ожидаемая версия (спецификация: payload.version)
//             // При редактировании организация НЕ отправляется (правило tenant_immutable)
//             version: initialData.version,
//           },
//         });

//         // ✅ Правило №24: строгий порядок действий
//         await queryClient.invalidateQueries({
//           queryKey: ["business-partners-companies"],
//         });
//         onOpenChange(false);
//         reset(CREATE_DEFAULTS);
//         await onSaved(initialData.id, data.name);
//       } else {
//         // ✅ Создание (спецификация: mutation_params.create)
//         const res = await createMutation.mutateAsync({
//           data: {
//             name: data.name,
//             fullname: data.fullname || null,
//             inn: data.inn || null,
//             kpp: data.kpp || null,
//             region_id: data.region_id || null,
//             is_customer: data.is_customer ?? false,
//             is_supplier: data.is_supplier ?? false,
//             address_legal: data.address_legal || null,
//             address_fact: data.address_fact || null,
//             phone: data.phone || null,
//             email: data.email || null,
//             contact: data.contact || null,
//             // ✅ Организация только при создании, из сессии
//             // (спецификация: payload.tenant_id)
//             tenant_id: currentTenantId,
//             section_id: data.section_id,
//             doc_number: data.doc_number || null,
//             doc_date: data.doc_date || null,
//             // author_id, created_by_user_id заполняет бэкенд из сессии
//           },
//         });

//         await queryClient.invalidateQueries({
//           queryKey: ["business-partners-companies"],
//         });
//         onOpenChange(false);
//         reset(CREATE_DEFAULTS);
//         const newId = res.data?.id || "";
//         await onSaved(newId, data.name);
//       }
//     } catch (error: unknown) {
//       // ✅ Правило №36: безопасная обработка ошибок
//       // ✅ Правило №39 + спецификация events.on_save_error: обработка 409 и 423
//       let message = "Не удалось сохранить компанию";
//       const err = error as {
//         response?: { status?: number; data?: { detail?: string } };
//       };
//       const status = err?.response?.status;
//       const detail = err?.response?.data?.detail;

//       if (status === 409) {
//         message = "Карточка изменена другим пользователем. Обновите данные.";
//       } else if (status === 423) {
//         message = "Карточка редактируется другим пользователем.";
//       } else if (detail) {
//         message = detail;
//       }

//       toast({
//         variant: "destructive",
//         title: "Ошибка сохранения",
//         description: message,
//       });
//     }
//   };

//   const onInvalid = (formErrors: FieldErrors<CompanyFormData>) => {
//     console.warn("Ошибки валидации формы:", formErrors);
//     toast({
//       variant: "destructive",
//       title: "Ошибка заполнения формы",
//       description:
//         "Пожалуйста, проверьте правильность заполнения полей. Наименование и раздел обязательны.",
//     });
//   };

//   return (
//     <Dialog open={open} onOpenChange={handleOpenChange}>
//       <DialogContent
//         // className="max-h-[90vh] overflow-y-auto items-start pt-8"
//         className="max-h-[90vh] items-start pt-8"
//         style={{
//           width: "800px", // ✅ Постоянная ширина (не зависит от вкладки)
//           maxWidth: "800px", // ✅ Ограничение для адаптивности
//           minHeight: "600px", // ✅ Минимальная высота
//           height: "auto", // Высота адаптируется к содержимому
//         }}
//       >
//         {" "}
//         <DialogHeader>
//           <DialogTitle>
//             {/* ✅ Спецификация: titles */}
//             {readOnly
//               ? "Просмотр компании (только чтение)"
//               : isEdit
//                 ? `Редактирование компании: ${initialData?.name}`
//                 : "Новая компания"}
//           </DialogTitle>
//         </DialogHeader>
//         {/* ✅ Правило №39: предупреждение в режиме только чтения */}
//         {readOnly && (
//           <Alert variant="destructive">
//             <AlertCircle className="h-4 w-4" />
//             <AlertTitle>Карточка заблокирована</AlertTitle>
//             <AlertDescription>
//               Компания редактируется другим пользователем. Вы можете только
//               просматривать данные.
//             </AlertDescription>
//           </Alert>
//         )}
//         <form
//           onSubmit={handleSubmit(onSubmit, onInvalid)}
//           className="space-y-4"
//           id="company-form"
//         >
//           {/* Наименование (обязательное) */}
//           <div className="space-y-2">
//             <Label>
//               Наименование <span className="text-destructive">*</span>
//             </Label>
//             <Controller
//               name="name"
//               control={control}
//               render={({ field }) => (
//                 <Input
//                   {...field}
//                   placeholder="Например: ООО «Ромашка»"
//                   disabled={readOnly}
//                 />
//               )}
//             />
//             {errors.name && (
//               <p className="text-xs text-destructive">{errors.name.message}</p>
//             )}
//           </div>

//           <Tabs defaultValue="main" className="w-full">
//             <TabsList className="grid w-full grid-cols-3">
//               {/* Вкладка Основное с индикатором изменений */}
//               <TabsTrigger value="main" className="relative">
//                 Основное
//                 {hasBasicsChanges && (
//                   <span className="absolute -top-1 -right-1 text-amber-500 text-xl font-bold leading-none">
//                     *
//                   </span>
//                 )}
//               </TabsTrigger>
//               {/* Вкладка «Адреса и контакты» */}
//               <TabsTrigger value="contacts" className="relative">
//                 Адреса и контакты
//                 {hasContactsChanges && (
//                   <span className="absolute -top-1 -right-1 text-amber-500 text-xl font-bold leading-none">
//                     *
//                   </span>
//                 )}
//               </TabsTrigger>
//               {/* Вкладка «Документ» (поля контракта) */}
//               <TabsTrigger value="document" className="relative">
//                 Документ
//                 {hasDocumentChanges && (
//                   <span className="absolute -top-1 -right-1 text-amber-500 text-xl font-bold leading-none">
//                     *
//                   </span>
//                 )}
//               </TabsTrigger>
//             </TabsList>

//             {/* ═══════════════════════════════════════ */}
//             {/* ВКЛАДКА 1: РЕКВИЗИТЫ (спецификация: tabs.main) */}
//             {/* ═══════════════════════════════════════ */}
//             {/* <TabsContent value="main" className="space-y-4 mt-2"> */}
//             <TabsContent value="main" className="space-y-4 mt-0 min-h-[330px]">
//               {/* Полное наименование */}
//               <div className="space-y-2">
//                 <Label>Полное наименование</Label>
//                 <Controller
//                   name="fullname"
//                   control={control}
//                   render={({ field }) => (
//                     <Textarea
//                       {...field}
//                       placeholder="Полное юридическое наименование"
//                       rows={2}
//                       disabled={readOnly}
//                     />
//                   )}
//                 />
//                 {errors.fullname && (
//                   <p className="text-xs text-destructive">
//                     {errors.fullname.message}
//                   </p>
//                 )}
//               </div>

//               {/* ИНН и КПП в две колонки */}
//               <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
//                 <div className="space-y-2">
//                   <Label>ИНН</Label>
//                   <Controller
//                     name="inn"
//                     control={control}
//                     render={({ field }) => (
//                       <Input
//                         {...field}
//                         placeholder="10 цифр для юрлица"
//                         disabled={readOnly}
//                       />
//                     )}
//                   />
//                   {errors.inn && (
//                     <p className="text-xs text-destructive">
//                       {errors.inn.message}
//                     </p>
//                   )}
//                 </div>
//                 <div className="space-y-2">
//                   <Label>КПП</Label>
//                   <Controller
//                     name="kpp"
//                     control={control}
//                     render={({ field }) => (
//                       <Input
//                         {...field}
//                         placeholder="9 цифр"
//                         disabled={readOnly}
//                       />
//                     )}
//                   />
//                   {errors.kpp && (
//                     <p className="text-xs text-destructive">
//                       {errors.kpp.message}
//                     </p>
//                   )}
//                 </div>
//               </div>

//               {/* Регион (справочник, опционально) */}
//               {/* ⚠️ Рендерится только при наличии модуля регионов (см. REGIONS_AVAILABLE) */}
//               {REGIONS_AVAILABLE && (
//                 <div className="space-y-2">
//                   <Label>Регион</Label>
//                   <Controller
//                     name="region_id"
//                     control={control}
//                     render={({ field }) => (
//                       <ReferenceSelect
//                         // eslint-disable-next-line @typescript-eslint/no-unused-vars
//                         fetchFn={async (params) => {
//                           // Адаптер под фактический эндпоинт модуля регионов
//                           // после его реализации
//                           return { items: [] as ReferenceItem[], total: 0 };
//                         }}
//                         queryKey={["regions", currentTenantId || ""]}
//                         value={field.value || ""}
//                         onValueChange={field.onChange}
//                         placeholder="Выберите регион..."
//                         selectedLabel={
//                           (
//                             initialData as BpCompanyResponseSchema & {
//                               region_name?: string;
//                             }
//                           )?.region_name ?? "Выберите регион..."
//                         }
//                         heading="Регионы"
//                         limit={50}
//                         disabled={readOnly}
//                       />
//                     )}
//                   />
//                   {errors.region_id && (
//                     <p className="text-xs text-destructive">
//                       {errors.region_id.message}
//                     </p>
//                   )}
//                 </div>
//               )}

//               {/* Флаги Клиент / Поставщик (Правило №34) */}
//               {/* Спецификация: бизнес-правило flags_independence — флаги независимы */}
//               <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
//                 <div className="flex items-center gap-3">
//                   <Controller
//                     name="is_customer"
//                     control={control}
//                     render={({ field }) => (
//                       <>
//                         <Switch
//                           id="is_customer"
//                           checked={field.value ?? false}
//                           onCheckedChange={field.onChange}
//                           disabled={readOnly}
//                         />
//                         <Label
//                           htmlFor="is_customer"
//                           className={`flex items-center gap-2 cursor-pointer font-medium transition-colors ${
//                             field.value
//                               ? "text-green-600 dark:text-green-400"
//                               : "text-muted-foreground"
//                           }`}
//                         >
//                           {field.value ? (
//                             <>
//                               <CheckCircle2 className="h-4 w-4" />
//                               Клиент
//                             </>
//                           ) : (
//                             <>
//                               <PauseCircle className="h-4 w-4" />
//                               Клиент
//                             </>
//                           )}
//                         </Label>
//                       </>
//                     )}
//                   />
//                 </div>
//                 <div className="flex items-center gap-3">
//                   <Controller
//                     name="is_supplier"
//                     control={control}
//                     render={({ field }) => (
//                       <>
//                         <Switch
//                           id="is_supplier"
//                           checked={field.value ?? false}
//                           onCheckedChange={field.onChange}
//                           disabled={readOnly}
//                         />
//                         <Label
//                           htmlFor="is_supplier"
//                           className={`flex items-center gap-2 cursor-pointer font-medium transition-colors ${
//                             field.value
//                               ? "text-green-600 dark:text-green-400"
//                               : "text-muted-foreground"
//                           }`}
//                         >
//                           {field.value ? (
//                             <>
//                               <CheckCircle2 className="h-4 w-4" />
//                               Поставщик
//                             </>
//                           ) : (
//                             <>
//                               <PauseCircle className="h-4 w-4" />
//                               Поставщик
//                             </>
//                           )}
//                         </Label>
//                       </>
//                     )}
//                   />
//                 </div>
//               </div>
//             </TabsContent>

//             {/* ═══════════════════════════════════════ */}
//             {/* ВКЛАДКА 2: АДРЕСА И КОНТАКТЫ (спецификация: tabs.contacts) */}
//             {/* ═══════════════════════════════════════ */}
//             {/* <TabsContent value="contacts" className="space-y-4 mt-2"> */}
//             <TabsContent value="contacts" className="space-y-4 mt-0 min-h-[330px]">
//               {/* Юридический адрес */}
//               <div className="space-y-2">
//                 <Label>Юридический адрес</Label>
//                 <Controller
//                   name="address_legal"
//                   control={control}
//                   render={({ field }) => (
//                     <Textarea
//                       {...field}
//                       rows={2}
//                       placeholder="Юридический адрес"
//                       disabled={readOnly}
//                     />
//                   )}
//                 />
//                 {errors.address_legal && (
//                   <p className="text-xs text-destructive">
//                     {errors.address_legal.message}
//                   </p>
//                 )}
//               </div>

//               {/* Фактический адрес */}
//               <div className="space-y-2">
//                 <Label>Фактический адрес</Label>
//                 <Controller
//                   name="address_fact"
//                   control={control}
//                   render={({ field }) => (
//                     <Textarea
//                       {...field}
//                       rows={2}
//                       placeholder="Фактический адрес"
//                       disabled={readOnly}
//                     />
//                   )}
//                 />
//                 {errors.address_fact && (
//                   <p className="text-xs text-destructive">
//                     {errors.address_fact.message}
//                   </p>
//                 )}
//               </div>

//               {/* Телефон и Email в две колонки */}
//               <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
//                 <div className="space-y-2">
//                   <Label>Телефон</Label>
//                   <Controller
//                     name="phone"
//                     control={control}
//                     render={({ field }) => (
//                       <Input
//                         {...field}
//                         placeholder="+7 (999) 123-45-67"
//                         disabled={readOnly}
//                       />
//                     )}
//                   />
//                   {errors.phone && (
//                     <p className="text-xs text-destructive">
//                       {errors.phone.message}
//                     </p>
//                   )}
//                 </div>
//                 <div className="space-y-2">
//                   <Label>Email</Label>
//                   <Controller
//                     name="email"
//                     control={control}
//                     render={({ field }) => (
//                       <Input
//                         {...field}
//                         placeholder="info@example.com"
//                         disabled={readOnly}
//                       />
//                     )}
//                   />
//                   {errors.email && (
//                     <p className="text-xs text-destructive">
//                       {errors.email.message}
//                     </p>
//                   )}
//                 </div>
//               </div>

//               {/* Контактное лицо */}
//               <div className="space-y-2">
//                 <Label>Контактное лицо</Label>
//                 <Controller
//                   name="contact"
//                   control={control}
//                   render={({ field }) => (
//                     <Input
//                       {...field}
//                       placeholder="ФИО, должность"
//                       disabled={readOnly}
//                     />
//                   )}
//                 />
//                 {errors.contact && (
//                   <p className="text-xs text-destructive">
//                     {errors.contact.message}
//                   </p>
//                 )}
//               </div>
//             </TabsContent>

//             {/* ═══════════════════════════════════════ */}
//             {/* ВКЛАДКА 3: ДОКУМЕНТ (поля контракта, авто для entity_kind: document) */}
//             {/* ═══════════════════════════════════════ */}
//             {/* <TabsContent value="document" className="space-y-4 mt-2"> */}
//             <TabsContent value="document" className="space-y-4 mt-0 min-h-[330px]">
//               {/* Организация: только чтение (спецификация: tenant_context) */}
//               <div className="space-y-2">
//                 <Label className="text-sm font-medium">Организация</Label>
//                 <div className="px-3 py-2 rounded-md border bg-muted/50 text-sm">
//                   {currentTenantName || "—"}
//                 </div>
//                 <p className="text-xs text-muted-foreground">
//                   {isEdit
//                     ? "Организация компании не меняется через эту форму."
//                     : "Компания будет создана для вашей организации."}
//                 </p>
//               </div>
//               {/* Раздел доступа (обязательный, контракт доступа) */}
//               <div className="space-y-2">
//                 <Label>
//                   Раздел доступа <span className="text-destructive">*</span>
//                 </Label>
//                 <Controller
//                   name="section_id"
//                   control={control}
//                   render={({ field }) => (
//                     <ReferenceSelect
//                       fetchFn={async (params) => {
//                         const response = await getSectionsSectionsGet({
//                           skip: params.skip,
//                           limit: params.limit,
//                           search: params.search,
//                           target_tenant_id: currentTenantId,
//                         });
//                         const items: ReferenceItem[] = (
//                           response?.data?.items ?? []
//                         ).map((item: unknown) => {
//                           const typedItem = item as {
//                             id: string;
//                             name: string;
//                             description?: string | null;
//                           };
//                           return {
//                             id: typedItem.id,
//                             name: typedItem.name,
//                             description: typedItem.description,
//                           };
//                         });
//                         return { items, total: response?.data?.total ?? 0 };
//                       }}
//                       queryKey={[
//                         "sections",
//                         "companies",
//                         currentTenantId || "",
//                       ]}
//                       value={field.value}
//                       onValueChange={field.onChange}
//                       placeholder="Выберите раздел..."
//                       // ✅ Правило №27 + №42: мгновенное отображение при редактировании
//                       selectedLabel={
//                         initialData?.section_name ?? "Выберите раздел..."
//                       }
//                       heading="Разделы доступа"
//                       limit={50}
//                       columns={[{ column: "description", label: "Описание" }]}
//                       disabled={readOnly}
//                     />
//                   )}
//                 />
//                 {errors.section_id && (
//                   <p className="text-xs text-destructive">
//                     {errors.section_id.message}
//                   </p>
//                 )}
//               </div>

//               {/* Номер и дата документа в две колонки */}
//               <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
//                 <div className="space-y-2">
//                   <Label>Номер документа</Label>
//                   <Controller
//                     name="doc_number"
//                     control={control}
//                     render={({ field }) => (
//                       <Input
//                         {...field}
//                         placeholder="Например: КМП-001"
//                         disabled={readOnly}
//                       />
//                     )}
//                   />
//                   {errors.doc_number && (
//                     <p className="text-xs text-destructive">
//                       {errors.doc_number.message}
//                     </p>
//                   )}
//                 </div>
//                 <div className="space-y-2">
//                   <Label>Дата документа</Label>
//                   <Controller
//                     name="doc_date"
//                     control={control}
//                     render={({ field }) => (
//                       <Input {...field} type="date" disabled={readOnly} />
//                     )}
//                   />
//                   {errors.doc_date && (
//                     <p className="text-xs text-destructive">
//                       {errors.doc_date.message}
//                     </p>
//                   )}
//                 </div>
//               </div>
//             </TabsContent>
//           </Tabs>

//           <DialogFooter>
//             <Button
//               type="button"
//               variant="outline"
//               className="min-w-24"
//               onClick={() => handleOpenChange(false)}
//             >
//               {/* ✅ Спецификация: actions.cancel.label_rules */}
//               {readOnly ? "Закрыть" : "Отмена"}
//             </Button>

//             {/* ✅ Спецификация: actions.save.hidden_when = read_only */}
//             {!readOnly && (
//               <Button
//                 type="submit"
//                 form="company-form"
//                 disabled={
//                   isSubmitting ||
//                   createMutation.isPending ||
//                   updateMutation.isPending ||
//                   // ✅ Спецификация: disabled_when = "not has_any_changes"
//                   // Для создания кнопка активна всегда (изменений ещё нет,
//                   // но валидация не пропустит пустые обязательные поля)
//                   (isEdit && !hasAnyChanges)
//                 }
//               >
//                 {(isSubmitting ||
//                   createMutation.isPending ||
//                   updateMutation.isPending) && (
//                   <Loader2 className="mr-2 h-4 w-4 animate-spin" />
//                 )}
//                 <Check className="mr-2 h-4 w-4" />
//                 {isEdit ? "Сохранить" : "Создать"}
//               </Button>
//             )}
//           </DialogFooter>
//         </form>
//       </DialogContent>
//     </Dialog>
//   );
// }
